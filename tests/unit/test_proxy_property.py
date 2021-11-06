from typing import Optional

from xz.utils import proxy_property


class Dest:
    abc = "012"


class Src:
    proxy: Optional[Dest] = None
    xyz = proxy_property("abc", "proxy")


def test_direct() -> None:
    dest = Dest()
    src = Src()

    # not proxied
    assert src.xyz is None  # default value

    src.xyz = "345"
    assert src.xyz == "345"
    assert dest.abc == "012"  # unchanged

    # proxied
    src.proxy = dest

    assert src.xyz == "012"  # get initial value back from proxy

    src.xyz = "678"
    assert src.xyz == "678"
    assert dest.abc == "678"  # changed
