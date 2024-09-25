import sys

sys.path.insert(0, ".")
sys.path.insert(0, "..")

import pytest
from bento_meta.entity import ArgError, CollValue, Entity


class TestEntity(Entity):
    attspec = {"a": "simple", "b": "object", "c": "collection"}
    mapspec_ = {
        "label": "test",
        "relationship": {
            "b": {"rel": ":has_object>", "end_cls": "entity"},
            "c": {"rel": ":has_object>", "end_cls": "entity"},
        },
        "property": {"a": "a"},
    }

    def __init__(self, init=None) -> None:
        super().__init__(init)


def test_create_entity() -> None:
    assert Entity()


def test_entity_attrs() -> None:
    assert TestEntity.attspec == {"a": "simple", "b": "object", "c": "collection"}
    ent = TestEntity()
    val = TestEntity()
    ent.a = 1
    ent.b = val
    assert ent.a == 1
    assert ent.b == val
    with pytest.raises(AttributeError, match="attribute 'frelb' neither"):
        ent.frelb = 42
    with pytest.raises(AttributeError, match="attribute 'frelb' neither"):
        f = ent.frelb
    with pytest.raises(ArgError, match=".*is not an Entity subclass"):
        ent.b = {"plain": "dict"}


def test_entity_init() -> None:
    val = TestEntity({"a": 10})
    col = {}
    good = {"a": 1, "b": val, "c": col, "d": "ignored"}
    bad = {"a": val, "b": val, "c": col, "d": "ignored"}
    ent = TestEntity(init=good)
    with pytest.raises(ArgError, match=".*is not a simple scalar"):
        TestEntity(init=bad)


def test_entity_belongs() -> None:
    e = TestEntity()
    ee = TestEntity()
    cc = CollValue({}, owner=e, owner_key="c")
    e.c = cc
    cc["k"] = ee
    assert e.c == cc
    assert e.c["k"] == ee


def test_get_attr_dict() -> None:
    """Test get_attr_dict method for different attribute types."""
    ent = TestEntity()
    ent.a = True
    assert ent.get_attr_dict() == {"a": "True"}
    ent.a = False
    assert ent.get_attr_dict() == {"a": "False"}
    ent.a = 42
    assert ent.get_attr_dict() == {"a": "42"}
    ent.a = 0
    assert ent.get_attr_dict() == {"a": "0"}
    ent.a = 4.2
    assert ent.get_attr_dict() == {"a": "4.2"}
    ent.a = 0.0
    assert ent.get_attr_dict() == {"a": "0.0"}
    ent.a = "abc"
    assert ent.get_attr_dict() == {"a": "abc"}
    ent.a = ""
    assert ent.get_attr_dict() == {"a": ""}
    ent.a = None
    assert ent.get_attr_dict() == {}
    ent.b = TestEntity()
    assert ent.get_attr_dict() == {}
    ent.c = CollValue({}, owner=ent, owner_key="c")
    assert ent.get_attr_dict() == {}
