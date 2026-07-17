"""Author: Dev2 | Date: 2026-07-16 | Purpose: Serve the production SPA locally with route fallback."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


class SpaRequestHandler(SimpleHTTPRequestHandler):
    """Return index.html for client-side routes while preserving asset 404 errors."""

    def send_head(self):  # type: ignore[no-untyped-def]
        request_path = urlparse(self.path).path
        target = Path(self.translate_path(request_path))

        if not target.exists() and not Path(request_path).suffix:
            self.path = "/index.html"

        return super().send_head()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local static server for the IT Platform SPA")
    parser.add_argument("--directory", required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()

    handler = lambda *handler_args, **handler_kwargs: SpaRequestHandler(  # noqa: E731
        *handler_args,
        directory=args.directory,
        **handler_kwargs,
    )
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"IT Platform available at http://{args.bind}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
