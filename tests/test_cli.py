from sportoto.cli import build_parser


def test_refresh_sources_command_is_available():
    args = build_parser().parse_args(["refresh-sources", "--date", "2026-08-21"])
    assert args.command == "refresh-sources"
    assert args.date == "2026-08-21"
