from sportoto.current_list import load_current_list, save_current_list


def test_current_list_round_trip(tmp_path):
    path = tmp_path / "current.json"
    # Loader is safe on missing local snapshot.
    assert load_current_list(path) == []
