from sportoto.cli import build_parser


def test_advanced_backtest_command_is_available():
    args = build_parser().parse_args(["advanced-backtest", "--input", "data/advanced.json"])
    assert args.command == "advanced-backtest"
    assert args.input == "data/advanced.json"
