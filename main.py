from __future__ import annotations

"""Smart OCR 服务的入口模块，用于启动Uvicorn服务器。"""

import uvicorn

from smart_ocr.app import app


def run():
    """启动Uvicorn服务器并运行FastAPI应用。"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        lifespan="on",
        log_level="info",
    )


if __name__ == "__main__":
    run()
