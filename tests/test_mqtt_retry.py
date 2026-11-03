from sentinel.mqtt_bridge import serve_mqtt


def test_mqtt_loop_waits_after_refused_connect_and_unexpected_exit() -> None:
    sleeps: list[int] = []
    attempts = {"n": 0}

    def connect() -> None:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise OSError("refused")
        raise RuntimeError("broker dropped")

    serve_mqtt(connect, sleeps.append, cycles=2)
    assert attempts["n"] == 2
    assert sleeps == [3, 3]
