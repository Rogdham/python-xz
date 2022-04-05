from typing import Optional

import pytest

from xz.utils import AttrProxy


class Dest:
    abc = "012"


class Src:
    proxy: Optional[Dest] = None
    abc = AttrProxy[str]("proxy")


def test_direct() -> None:
    dest = Dest()
    src = Src()

    # not proxied
    with pytest.raises(AttributeError) as exc_info:
        src.abc  # pylint: disable=pointless-statement
    assert (
        str(exc_info.value)
        == "'Src' object has not attribute 'abc' until its attribute 'proxy' is defined"
    )

    src.abc = "345"
    assert src.abc == "345"
    assert dest.abc == "012"  # unchanged

    # proxied
    src.proxy = dest

    assert src.abc == "012"  # get initial value back from proxy

    src.abc = "678"
    assert src.abc == "678"
    assert dest.abc == "678"  # changed
