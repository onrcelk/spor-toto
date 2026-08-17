from sportoto.cli import build_parser


def test_advanced_statsbomb_command_is_available():
    args = build_parser().parse_args(["advanced-statsbomb", "--url", "https://example.test/events.json"])
    assert args.command == "advanced-statsbomb"
    assert args.url.endswith("events.json")
