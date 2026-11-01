"""订阅 cone/#，写入 SQLite。连接失败在后台重试，不挡住网页。"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import closing

import paho.mqtt.client as mqtt
from fastapi import FastAPI

from sentinel.db import connect
from sentinel.ingest import ingest

logger = logging.getLogger("sentinel.mqtt")


def start_mqtt(app: FastAPI) -> mqtt.Client:
    settings = app.state.settings
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(
        client: mqtt.Client,
        userdata: object,
        flags: object,
        reason_code: object,
        properties: object = None,
    ) -> None:
        logger.info("MQTT connected %s", reason_code)
        client.subscribe("cone/#")

    def on_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        try:
            with app.state.db_lock, closing(connect(settings.db_path)) as conn, conn:
                error = ingest(conn, msg.topic, msg.payload, time.time())
            if error:
                logger.warning("bad msg %s: %s", msg.topic, error)
        except Exception:
            logger.exception("mqtt handler failed on %s", msg.topic)

    client.on_connect = on_connect
    client.on_message = on_message

    def _loop() -> None:
        while True:
            try:
                client.connect(settings.mqtt_host, settings.mqtt_port, 30)
                client.loop_forever()
            except OSError as exc:
                logger.warning("MQTT connect failed, retry in 3s: %s", exc)
                time.sleep(3)

    threading.Thread(target=_loop, name="mqtt", daemon=True).start()
    return client
