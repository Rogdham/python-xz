from bisect import bisect_right, insort_right
import sys
from typing import Any, Dict, Generic, List, Tuple, TypeVar, cast

if sys.version_info >= (3, 9):  # pragma: no cover
    from collections.abc import Iterator, MutableMapping
else:  # pragma: no cover
    from typing import Iterator, MutableMapping


T = TypeVar("T")


class FloorDict(MutableMapping[int, T]):
    """A dict where keys are int, and accessing a key will use the closest lower one.

    Differences from dict:
     - keys must be int
     - obj[key] will return the value whose key is the closest one which is lower or equal to key
    """

    def __init__(self) -> None:
        self._dict: Dict[int, T] = {}
        self._keys: List[int] = []  # sorted

    def __repr__(self) -> str:
        return f"FloorDict<{self._dict!r}>"

    def __iter__(self) -> Iterator[int]:
        return iter(self._keys)

    def __reversed__(self) -> Iterator[int]:
        return reversed(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def _key_index(self, key: int) -> int:
        index = bisect_right(self._keys, key) - 1
        if index < 0:
            raise KeyError(key)
        return index

    def get_with_index(self, key: int) -> Tuple[int, T]:
        if not isinstance(key, int):
            raise TypeError("Invalid key")
        index = self._keys[self._key_index(key)]
        value = self._dict[index]
        return (index, value)

    def __getitem__(self, key: int) -> T:
        return self.get_with_index(key)[1]

    def __setitem__(self, key: int, value: T) -> None:
        if not isinstance(key, int):
            raise TypeError("Invalid key")
        if key not in self._dict:  # prevent duplicates in _keys
            insort_right(self._keys, key)
        self._dict[key] = value

    def __delitem__(self, key: int) -> None:
        del self._dict[key]
        # the key is an exact index (otherwise KeyError raised on last line)
        self._keys.pop(self._key_index(key))

    @property
    def last_key(self) -> int:
        if not self._keys:
            raise KeyError("dictionary is empty")
        return self._keys[-1]

    @property
    def last_item(self) -> T:
        return self._dict[self.last_key]


def parse_mode(mode: str) -> Tuple[str, bool, bool]:
    """Parse a mode used in open.

    Order is not considered at all.
    Binary flag (b) is ignored.
    Valid modes are: r, r+, w, w+, x, x+.

    Return a tuple (nomalized, is_read, is_write).
    """
    mode_set = set(mode)
    if len(mode_set) != len(mode):
        raise ValueError(f"invalid mode: {mode}")
    mode_plus = "+" in mode_set
    mode_set -= {"b", "+"}
    mode_base = mode_set.pop() if mode_set else "invalid"
    if mode_set or mode_base not in "rwx":
        raise ValueError(f"invalid mode: {mode}")
    if mode_plus:
        return (f"{mode_base}+", True, True)
    return (mode_base, mode_base == "r", mode_base != "r")


class AttrProxy(Generic[T]):
    """Create a descriptor that is a proxy to the same attribute of an attribute.

    Example:

        class Foo:
            proxy = Something()
            bar = AttrProxy("proxy")

        foo = Foo()

        then foo.bar would be proxied to foo.proxy.bar

    If the proxy value is None, then use a local value instead,
    which acts as a temporary storage in the meanwhile.
    """

    # Typing note
    #
    # There is no typing enforced to make sure that the proxy attribute
    # on the attribute exists and is of type T.
    # We just trust that the user-provided T is right.
    #
    # This explains the use of Any everywhere
    #

    attribute: str
    not_proxied_value: T

    def __init__(self, proxy: str) -> None:
        self.proxy = proxy

    def __set_name__(self, klass: Any, name: str) -> None:
        self.attribute = name

    def __get__(self, instance: Any, klass: Any) -> T:
        dest = getattr(instance, self.proxy)
        if dest is None:
            try:
                return self.not_proxied_value
            except AttributeError as ex:
                raise AttributeError(
                    f"'{klass.__name__}' object has not attribute '{self.attribute}'"
                    f" until its attribute '{self.proxy}' is defined"
                ) from ex
        return cast(T, getattr(dest, self.attribute))

    def __set__(self, instance: Any, value: T) -> None:
        dest = getattr(instance, self.proxy)
        if dest is None:
            self.not_proxied_value = value
        else:
            setattr(dest, self.attribute, value)
