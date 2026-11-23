"""Extraction sécurisée des métadonnées produit depuis une URL publique."""
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/produits", tags=["produits"])

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
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag.lower() == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if key and content and key not in self.metadata:
                self.metadata[key] = content
        elif tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title and data.strip():
            self.title_parts.append(data.strip())


def _parse_public_url(raw_url: str) -> httpx.URL:
    try:
        url = httpx.URL(raw_url.strip())
        if url.scheme not in ("http", "https") or not url.host:
            raise ValueError("scheme or host")
        if url.username or url.password:
            raise ValueError("credentials")
        expected_port = 443 if url.scheme == "https" else 80
        if url.port != expected_port:
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
    port = url.port
    try:
        literal_ip = ipaddress.ip_address(host)
        addresses = [literal_ip]
    except ValueError:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = list({
            ipaddress.ip_address(record[4][0]) for record in records
        })

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

    if not isinstance(literal_ip if "literal_ip" in locals() else None, ipaddress.IPv4Address) and not isinstance(
        literal_ip if "literal_ip" in locals() else None, ipaddress.IPv6Address
    ):
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
    headers = {
        "User-Agent": "LaHotteProductPreview/1.0 (+https://lahotte.gazggul.ovh)",
        "Accept": "text/html,application/xhtml+xml",
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
                with client.send(request, stream=True) as response:
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
                        raise HTTPException(
                            status_code=422,
                            detail="La page produit n'est pas accessible.",
                        )
                    content_type = response.headers.get("content-type", "").lower()
                    if (
                        "text/html" not in content_type
                        and "application/xhtml+xml" not in content_type
                    ):
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
        image = (
            parser.metadata.get("og:image")
            or parser.metadata.get("og:image:secure_url")
            or parser.metadata.get("twitter:image")
            or parser.metadata.get("twitter:image:src")
        )
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
    except (httpx.HTTPError, UnicodeError, ValueError, OSError):
        raise HTTPException(
            status_code=422,
            detail="Impossible d'extraire la photo de cette page produit.",
        )
