from sportoto.real_training import HistoricalMatch, build_training_frame, parse_mackolik_archive


def test_build_training_frame_creates_real_labels():
    matches = [
        HistoricalMatch("01/01/25", "A", "B", 2, 0, "test"),
        HistoricalMatch("02/01/25", "B", "A", 1, 1, "test"),
        HistoricalMatch("03/01/25", "A", "B", 0, 3, "test"),
    ]
    frame = build_training_frame(matches)
    assert len(frame) == 3
    assert set(frame["actual_1x2"]) == {0, 1, 2}
    assert set(frame["actual_ou"]) == {0, 1}


def test_parse_empty_mackolik():
    assert parse_mackolik_archive("<html><body></body></html>") == []
