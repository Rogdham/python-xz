from itertools import permutations, product
import sys
from typing import Tuple

try:
    from typing import get_args
except ImportError:
    pass

import pytest

from xz.typing import _XZModesBinaryType, _XZModesTextType
from xz.utils import parse_mode

VALID_MODES = {
    "".join(sorted(case[0] + extra)): case
    for case in [
        ("r", True, False),
        ("r+", True, True),
        ("w", False, True),
        ("w+", True, True),
        ("x", False, True),
        ("x+", True, True),
    ]
    for extra in ("", "b")
}


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="Literal or get_args not supported",
)
def test_known_valid_modes_binary() -> None:
    assert sorted(
        "".join(sorted(mode)) for mode in get_args(_XZModesBinaryType)
    ) == sorted(VALID_MODES)


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="Literal or get_args not supported",
)
def test_known_valid_modes_text() -> None:
    assert sorted(
        "".join(sorted(mode.replace("t", ""))) for mode in get_args(_XZModesTextType)
    ) == sorted(mode for mode in VALID_MODES if "b" not in mode)


@pytest.mark.parametrize(
    "mode, expected",
    [pytest.param(mode, expected, id=mode) for mode, expected in VALID_MODES.items()],
)
def test_parse_mode_valid(mode: str, expected: Tuple[str, bool, bool]) -> None:
    for parts in permutations(mode):
        mode_permuted = "".join(parts)
        assert parse_mode(mode_permuted) == expected, mode_permuted


@pytest.mark.parametrize(
    "mode",
    [
        "".join(mode_parts)
        for mode_parts in product(*((c, "") for c in "arwx+tb"))
        if "".join(sorted(mode_parts)) not in VALID_MODES
    ]
    + [mode * 2 for mode in VALID_MODES],
)
def test_parse_mode_invalid(mode: str) -> None:
    for parts in permutations(mode):
        mode_permuted = "".join(parts)
        with pytest.raises(ValueError):
            parse_mode(mode_permuted)
