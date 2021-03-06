from typing import Dict

import pytest

from xz.utils import FloorDict


def expect_floor_dict(floordict: FloorDict[str], items: Dict[int, str]) -> None:
    sorted_keys = sorted(items)
    assert len(floordict) == len(items)
    assert list(floordict) == sorted_keys
    assert list(floordict.keys()) == sorted_keys
    assert list(floordict.values()) == [items[key] for key in sorted_keys]
    assert list(floordict.items()) == [(key, items[key]) for key in sorted_keys]
    # pylint: disable=protected-access
    assert floordict._keys == sorted_keys
    assert floordict._dict == items


def test_empty() -> None:
    floordict = FloorDict[str]()

    expect_floor_dict(floordict, {})

    with pytest.raises(KeyError):
        floordict[0]  # pylint: disable=pointless-statement
    with pytest.raises(KeyError):
        floordict[42]  # pylint: disable=pointless-statement
    with pytest.raises(KeyError):
        floordict.last_key  # pylint: disable=pointless-statement
    with pytest.raises(KeyError):
        floordict.last_item  # pylint: disable=pointless-statement


def test_normal() -> None:
    floordict = FloorDict[str]()
    floordict[10] = "ten"
    floordict[50] = "fifty"
    with pytest.raises(TypeError):
        floordict["wrong type"] = "wrong type"  # type: ignore[index]

    expect_floor_dict(floordict, {10: "ten", 50: "fifty"})

    assert floordict[10] == "ten"
    assert floordict.last_key == 50
    assert floordict.last_item == "fifty"

    assert floordict[42] == "ten"
    assert floordict.get_with_index(42) == (10, "ten")

    assert floordict[50] == "fifty"
    assert floordict[1337] == "fifty"
    assert floordict.get(0) is None
    with pytest.raises(KeyError):
        floordict[0]  # pylint: disable=pointless-statement
    assert floordict.get(7) is None
    with pytest.raises(KeyError):
        floordict[7]  # pylint: disable=pointless-statement
    with pytest.raises(KeyError):
        floordict[-42]  # pylint: disable=pointless-statement
    with pytest.raises(TypeError):
        # pylint: disable=pointless-statement
        floordict["wrong type"]  # type: ignore[index]


def test_override() -> None:
    floordict = FloorDict[str]()
    floordict[10] = "ten"
    floordict[20] = "twenty"
    floordict[30] = "thirty"

    expect_floor_dict(floordict, {10: "ten", 20: "twenty", 30: "thirty"})

    floordict[20] = "two-ten"
    assert floordict[15] == "ten"
    assert floordict[20] == "two-ten"
    assert floordict[25] == "two-ten"
    assert floordict[50] == "thirty"

    expect_floor_dict(floordict, {10: "ten", 20: "two-ten", 30: "thirty"})


def test_del() -> None:
    floordict = FloorDict[str]()
    floordict[10] = "ten"
    floordict[20] = "twenty"
    floordict[30] = "thirty"
    assert floordict[20] == "twenty"
    assert floordict[22] == "twenty"
    expect_floor_dict(floordict, {10: "ten", 20: "twenty", 30: "thirty"})

    del floordict[20]
    assert floordict[20] == "ten"
    assert floordict[22] == "ten"
    expect_floor_dict(floordict, {10: "ten", 30: "thirty"})

    with pytest.raises(KeyError):
        del floordict[20]
    with pytest.raises(KeyError):
        del floordict[40]


def test_pop() -> None:
    floordict = FloorDict[str]()
    floordict[10] = "ten"
    floordict[20] = "twenty"
    floordict[30] = "thirty"
    assert floordict[25] == "twenty"
    expect_floor_dict(floordict, {10: "ten", 20: "twenty", 30: "thirty"})

    with pytest.raises(KeyError):
        floordict.pop(25)

    assert floordict.pop(20) == "twenty"
    expect_floor_dict(floordict, {10: "ten", 30: "thirty"})
    assert floordict[25] == "ten"


def test_values() -> None:
    floordict = FloorDict[str]()
    expected = {}
    for i in range(50):
        floordict[i * 2] = str(i * 2)
        expected[i * 2] = str(i * 2)
        expect_floor_dict(floordict, expected)
        for j in range(100):
            value = min(i * 2, j - (j % 2))
            assert floordict[j] == str(value)
            assert floordict.get_with_index(j) == (value, str(value))
