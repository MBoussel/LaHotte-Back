"""Extraction sécurisée des métadonnées produit depuis une URL publique."""
import ipaddress
import json
import logging
import socket
from contextlib import closing
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/produits", tags=["produits"])
logger = logging.getLogger(__name__)

MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
TIMEOUT = httpx.Timeout(8.0, connect=4.0)


class ProductUrlRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=500)


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metadata = {}
        self.title_parts = []
        self.jsonld_blocks = []
        self.image_candidates = []
        self.in_title = False
        self.in_jsonld = False
        self.current_jsonld = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        tag = tag.lower()
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if key and content and key not in self.metadata:
                self.metadata[key] = content
        elif tag == "title":
            self.in_title = True
        elif tag == "script" and "ld+json" in values.get("type", "").lower():
            self.in_jsonld = True
            self.current_jsonld = []
        elif tag == "img":
            self.image_candidates.append(values)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.in_jsonld:
            self.jsonld_blocks.append("".join(self.current_jsonld))
            self.current_jsonld = []
            self.in_jsonld = False

    def handle_data(self, data):
        if self.in_title and data.strip():
            self.title_parts.append(data.strip())
        if self.in_jsonld:
            self.current_jsonld.append(data)


def _jsonld_product_images(value):
    """Yield images only from schema.org Product objects."""
    if isinstance(value, list):
        for item in value:
            yield from _jsonld_product_images(item)
        return
    if not isinstance(value, dict):
        return

    types = value.get("@type", [])
    if isinstance(types, str):
        types = [types]
    if any(str(item).lower() == "product" for item in types):
        images = value.get("image", [])
        if isinstance(images, (str, dict)):
            images = [images]
        if isinstance(images, list):
            for image in images:
                if isinstance(image, str):
                    yield image
                elif isinstance(image, dict):
                    candidate = image.get("url") or image.get("contentUrl")
                    if isinstance(candidate, str):
                        yield candidate

    # Product may be nested in @graph, mainEntity, or other schema wrappers.
    for key, nested in value.items():
        if key in {"image", "logo", "thumbnailUrl"}:
            continue
        if isinstance(nested, (dict, list)):
            yield from _jsonld_product_images(nested)


def _first_srcset_url(srcset):
    if not isinstance(srcset, str) or not srcset.strip():
        return None
    # The first srcset entry is normally the smallest candidate; src is
    # preferred separately when available.
    return srcset.split(",")[0].strip().split()[0] if srcset.strip() else None


def _extract_product_gallery_image(candidates):
    """Conservative fallback: select an explicitly identified product image."""
    ranked = []
    for attrs in candidates:
        context = " ".join(
            str(attrs.get(key, "")) for key in ("alt", "class", "id", "data-testid", "itemprop")
        ).lower()
        if any(word in context for word in ("logo", "banner", "sprite", "icon", "payment")):
            continue
        if not any(word in context for word in ("product", "gallery", "pdp", "carousel", "product-image")):
            continue
        src = (
            attrs.get("src")
            or attrs.get("data-src")
            or attrs.get("data-original")
            or attrs.get("data-lazy-src")
            or _first_srcset_url(attrs.get("srcset"))
        )
        if src:
            # Images with descriptive alt text are more likely to be the
            # actual item than decorative gallery placeholders.
            ranked.append((bool(attrs.get("alt", "").strip()), src))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else None


def _parse_public_url(raw_url: str) -> httpx.URL:
    try:
        url = httpx.URL(raw_url.strip())
        if url.scheme not in ("http", "https") or not url.host:
            raise ValueError("scheme or host")
        if url.username or url.password:
            raise ValueError("credentials")
        expected_port = 443 if url.scheme == "https" else 80
        if url.port not in (None, expected_port):
            raise ValueError("port")
        host = url.host.rstrip(".").lower()
        if (
            host in {"localhost", "localhost.localdomain"}
            or host.endswith(".localhost")
            or host.endswith(".local")
        ):
            raise ValueError("local host")

        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            records = socket.getaddrinfo(
                host, expected_port, type=socket.SOCK_STREAM
            )
            addresses = list({
                ipaddress.ip_address(record[4][0]) for record in records
            })

        if not addresses or any(not address.is_global for address in addresses):
            raise ValueError("non-public address")
        return url
    except (ValueError, OSError, httpx.InvalidURL):
        raise HTTPException(
            status_code=400,
            detail="Cette adresse n'est pas une URL publique valide.",
        )


def _build_pinned_request(client: httpx.Client, raw_url: str, headers: dict):
    """Résout le domaine puis connecte HTTPX directement à l'IP vérifiée.

    L'en-tête Host et le SNI TLS conservent le nom de domaine d'origine.
    Ainsi, la connexion ne refait pas de résolution DNS susceptible de
    pointer vers une adresse privée (DNS rebinding).
    """
    url = _parse_public_url(raw_url)
    host = url.host.rstrip(".").lower()
    port = url.port or (443 if url.scheme == "https" else 80)
    try:
        literal_ip = ipaddress.ip_address(host)
        is_ip_literal = True
        addresses = [literal_ip]
    except ValueError:
        is_ip_literal = False
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = sorted(
            {
                ipaddress.ip_address(record[4][0]) for record in records
            },
            # Les environnements Render ne garantissent pas une sortie IPv6.
            # Essayer IPv4 en premier évite de choisir arbitrairement une IPv6
            # inaccessible alors qu'une adresse IPv4 publique est disponible.
            key=lambda address: (address.version != 4, address.compressed),
        )

    if not addresses or any(not address.is_global for address in addresses):
        raise HTTPException(
            status_code=400,
            detail="Cette adresse n'est pas une URL publique valide.",
        )

    # Une seule IP contrôlée est utilisée pour cette requête réseau.
    pinned_url = url.copy_with(host=addresses[0].compressed)
    request_headers = dict(headers)
    request_headers["Host"] = url.netloc.decode("ascii") if isinstance(url.netloc, bytes) else str(url.netloc)
    request = client.build_request("GET", pinned_url, headers=request_headers)

    if not is_ip_literal:
        request.extensions["sni_hostname"] = host.encode("idna")
    return request


def _validate_public_image_url(raw_url: str) -> str:
    url = _parse_public_url(raw_url)
    return str(url)


def _read_limited(response: httpx.Response) -> bytes:
    chunks = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > MAX_HTML_BYTES:
            raise HTTPException(
                status_code=413,
                detail="La page produit est trop volumineuse.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/extraire-image")
def extract_product_image(
    payload: ProductUrlRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Récupère l'image Open Graph/Twitter d'une page produit publique."""
    current_url = str(_parse_public_url(payload.url))
    # Certains sites Shopify filtrent les agents automatisés trop explicites.
    # On utilise des en-têtes de navigateur classiques, sans contourner
    # authentification, CAPTCHA ou autre contrôle d'accès.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    try:
        with httpx.Client(
            timeout=TIMEOUT,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            html = None
            for redirect_count in range(MAX_REDIRECTS + 1):
                request = _build_pinned_request(client, current_url, headers)
                # httpx.Response n'est pas un context manager. On ferme explicitement
                # le flux, y compris en cas de redirection ou d'erreur.
                with closing(client.send(request, stream=True)) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location or redirect_count >= MAX_REDIRECTS:
                            raise HTTPException(
                                status_code=422,
                                detail="Trop de redirections sur cette page produit.",
                            )
                        current_url = urljoin(current_url, location)
                        continue

                    if response.status_code != 200:
                        logger.warning(
                            "Product image extraction: upstream HTTP %s (host=%s)",
                            response.status_code,
                            httpx.URL(current_url).host,
                        )
                        detail = (
                            "Le site marchand refuse la récupération automatique "
                            "de sa page (accès refusé)."
                            if response.status_code in (401, 403, 429)
                            else "La page produit n'est pas accessible."
                        )
                        raise HTTPException(status_code=422, detail=detail)
                    content_type = response.headers.get("content-type", "").lower()
                    if (
                        "text/html" not in content_type
                        and "application/xhtml+xml" not in content_type
                    ):
                        logger.warning(
                            "Product image extraction: unexpected content type %r (host=%s)",
                            content_type[:100],
                            httpx.URL(current_url).host,
                        )
                        raise HTTPException(
                            status_code=422,
                            detail="Cette adresse ne mène pas à une page produit HTML.",
                        )
                    html = _read_limited(response)
                    break

        if html is None:
            raise HTTPException(
                status_code=422,
                detail="Impossible de lire cette page produit.",
            )

        parser = MetadataParser()
        parser.feed(html.decode("utf-8", errors="replace"))
        # 1. Social metadata remains the most direct product-image signal.
        image = (
            parser.metadata.get("og:image")
            or parser.metadata.get("og:image:secure_url")
            or parser.metadata.get("twitter:image")
            or parser.metadata.get("twitter:image:src")
        )

        # 2. Product JSON-LD is common on Shopify, WooCommerce and major
        # retailers. Parse only images attached to schema.org Product nodes.
        if not image:
            for block in parser.jsonld_blocks:
                try:
                    structured_data = json.loads(block)
                except (json.JSONDecodeError, TypeError):
                    continue
                image = next(_jsonld_product_images(structured_data), None)
                if image:
                    break

        # 3. Last resort: use an image explicitly marked as part of a product
        # gallery. Avoid taking the first arbitrary <img> (often a logo/banner).
        if not image:
            image = _extract_product_gallery_image(parser.image_candidates)

        if not image:
            raise HTTPException(
                status_code=404,
                detail="Aucune photo automatique trouvée sur cette page.",
            )

        image_url = _validate_public_image_url(urljoin(current_url, image))
        title = (
            parser.metadata.get("og:title")
            or parser.metadata.get("twitter:title")
            or " ".join(parser.title_parts)
        )[:200]
        return {"photo_url": image_url, "titre": title or None}
    except HTTPException:
        raise
    except (httpx.HTTPError, UnicodeError, ValueError, OSError) as exc:
        # Ne jamais journaliser l'URL complète : elle peut contenir des
        # paramètres de suivi ou des données privées.
        logger.warning(
            "Product image extraction failed: %s (host=%s)",
            type(exc).__name__,
            httpx.URL(current_url).host,
        )
        raise HTTPException(
            status_code=422,
            detail="Impossible d'extraire la photo de cette page produit.",
        )
