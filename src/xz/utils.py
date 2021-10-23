from bisect import bisect_right, insort_right
from collections.abc import MutableMapping


class FloorDict(MutableMapping):
    """A dict where keys are int, and accessing a key will use the closest lower one.

    Differences from dict:
     - keys must be int
     - obj[key] will return the value whose key is the closest one which is lower or equal to key
     - obj[key, True] will return the real index of the value in the form (index, obj[key])
    """

    def __init__(self):
        self._dict = {}
        self._keys = []  # sorted

    def __repr__(self):
        return f"FloorDict<{self._dict!r}>"

    def __iter__(self):
        return iter(self._keys)

    def __reversed__(self):
        return reversed(self._keys)

    def __len__(self):
        return len(self._keys)

    def _key_index(self, key):
        index = bisect_right(self._keys, key) - 1
        if index < 0:
            raise KeyError(key)
        return index

    def __getitem__(self, key):
        with_index = False
        if isinstance(key, tuple) and len(key) == 2:
            key, with_index = key
        if not isinstance(key, int):
            raise TypeError("Invalid key")
        index = self._keys[self._key_index(key)]
        value = self._dict[index]
        if with_index:
            return (index, value)
        return value

    def __setitem__(self, key, value):
        if not isinstance(key, int):
            raise TypeError("Invalid key")
        if key not in self._dict:  # prevent duplicates in _keys
            insort_right(self._keys, key)
        self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]
        # the key is an exact index (otherwise KeyError raised on last line)
        self._keys.pop(self._key_index(key))

    @property
    def last_key(self):
        if not self._keys:
            raise KeyError("dictionary is empty")
        return self._keys[-1]

    @property
    def last_item(self):
        return self._dict[self.last_key]


def parse_mode(mode):
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


def proxy_property(attribute, proxy):
    """Create a property that is a proxy to an attribute of an attribute.

    Example:

        class Foo:
            proxy = Something()
            bar = proxy_property("baz", "proxy")

        foo = Foo()

        then foo.bar would be proxied to foo.proxy.baz

    If attribute is "a" and proxy is "b", it proxies to ".a.b".

    If the proxy is None, then use a local value instead,
    which acts as a temporary storage in the meanwhile.
    """
    not_proxied_value = None

    def getter(obj):
        dest = getattr(obj, proxy)
        if dest is None:
            return not_proxied_value
        return getattr(dest, attribute)

    def setter(obj, value):
        dest = getattr(obj, proxy)
        if dest is None:
            nonlocal not_proxied_value
            not_proxied_value = value
        else:
            setattr(dest, attribute, value)

    return property(fget=getter, fset=setter)
