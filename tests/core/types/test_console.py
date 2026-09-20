from pygpt_net.core.types.console import Color


def test_console_colors_are_ansi_sequences():
    assert Color.BOLD == "\033[1m"
    assert Color.ENDC == "\033[0m"
    assert Color.FAIL.startswith("\033[")
    assert Color.WARNING.startswith("\033[")
