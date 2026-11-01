from sentinel.dedupe import SeqFilter


def test_first_packet_with_seq_zero_is_accepted_and_duplicate_dropped() -> None:
    seen = SeqFilter()
    assert seen.accept(1, 0) is True
    assert seen.accept(1, 0) is False


def test_late_relay_copy_is_dropped_but_restart_is_accepted() -> None:
    seen = SeqFilter()
    assert seen.accept(1, 1000)
    assert seen.accept(1, 1001)
    assert not seen.accept(1, 1000)  # 中继副本迟到
    assert seen.accept(1, 5)  # 相差超过窗口：对方重启
    assert seen.accept(2, 1000)  # 不同发送者互不影响


def test_all_256_node_ids_are_independent() -> None:
    seen = SeqFilter()
    for node in range(256):
        assert seen.accept(node, 7)
    for node in range(256):
        assert not seen.accept(node, 7)
