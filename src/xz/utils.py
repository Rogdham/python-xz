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
