import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException

from app.routers.produits import (
    MetadataParser,
    _build_pinned_request,
    _parse_public_url,
    ProductUrlRequest,
    extract_product_image,
)


def dns_record(ip: str, port: int = 443):
    import socket
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))


class ProductUrlSecurityTests(unittest.TestCase):
    @patch("app.routers.produits.socket.getaddrinfo")
    def test_domain_request_is_pinned_to_the_validated_ip(self, getaddrinfo):
        getaddrinfo.return_value = [dns_record("93.184.216.34")]
        with httpx.Client() as client:
            request = _build_pinned_request(
                client,
                "https://example.com/product/123",
                {"User-Agent": "LaHotteTest/1.0"},
            )

        self.assertEqual(request.url.host, "93.184.216.34")
        self.assertEqual(request.headers["host"], "example.com")
        self.assertEqual(request.extensions["sni_hostname"], b"example.com")
        self.assertEqual(getaddrinfo.call_count, 2)

    @patch("app.routers.produits.socket.getaddrinfo")
    def test_private_dns_result_is_rejected(self, getaddrinfo):
        getaddrinfo.return_value = [dns_record("127.0.0.1", 80)]
        with self.assertRaises(HTTPException):
            _parse_public_url("http://example.test/product")

    @patch("app.routers.produits.socket.getaddrinfo")
    def test_implicit_https_port_is_accepted(self, getaddrinfo):
        getaddrinfo.return_value = [dns_record("93.184.216.34")]
        url = _parse_public_url("https://example.com/product")
        self.assertEqual(url.scheme, "https")

    def test_metadata_parser_reads_open_graph_image_and_title(self):
        parser = MetadataParser()
        parser.feed(
            '<html><head><meta property="og:image" content="https://cdn.example.com/p.jpg">'
            '<meta property="og:title" content="Un cadeau"></head></html>'
        )
        self.assertEqual(parser.metadata["og:image"], "https://cdn.example.com/p.jpg")
        self.assertEqual(parser.metadata["og:title"], "Un cadeau")

    @patch("app.routers.produits.socket.getaddrinfo")
    @patch("app.routers.produits.httpx.Client")
    def test_extract_endpoint_closes_httpx_stream_response(self, client_class, getaddrinfo):
        getaddrinfo.return_value = [dns_record("93.184.216.34")]

        html = (
            b'<html><head>'
            b'<meta property="og:image" content="https://cdn.example.com/gift.jpg">'
            b'<meta property="og:title" content="Un cadeau">'
            b'</head></html>'
        )

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "text/html; charset=utf-8"}
            closed = False

            def iter_bytes(self):
                yield html

            def close(self):
                self.closed = True

        response = FakeResponse()

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def build_request(self, method, url, headers):
                return object()

            def send(self, request, stream=False):
                return response

        client_class.return_value = FakeClient()

        result = extract_product_image(
            ProductUrlRequest(url="https://example.com/product"),
            current_user=object(),
        )

        self.assertEqual(result["photo_url"], "https://cdn.example.com/gift.jpg")
        self.assertEqual(result["titre"], "Un cadeau")
        self.assertTrue(response.closed)


if __name__ == "__main__":
    unittest.main()
