from __future__ import annotations

import uvicorn

from smart_ocr.app import app


def run():
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        lifespan="on",
        log_level="info",
    )


if __name__ == "__main__":
    run()
