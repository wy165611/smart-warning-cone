"""python -m sentinel"""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from sentinel.api import create_app
from sentinel.mqtt_bridge import start_mqtt


def main(app: FastAPI | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    application = app or create_app()
    start_mqtt(application)
    settings = application.state.settings
    uvicorn.run(application, host=settings.http_host, port=settings.http_port)


if __name__ == "__main__":
    main()
