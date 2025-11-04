from __future__ import annotations

"""smart_ocr包的命令行入口，支持直接通过`python -m smart_ocr`运行服务。"""

import uvicorn

from smart_ocr.app import app


def main():
    """启动Uvicorn服务器以运行Smart OCR服务。"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        lifespan="on",
        log_level="info",
    )


if __name__ == "__main__":
    main()
