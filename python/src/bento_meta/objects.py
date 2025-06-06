"""
bento_meta.objects
==================

This module contains the subclasses of :class:`Entity` which are used
in representing the models contained in the `MDB <https://github.com/CBIIT/bento-mdf>`_.

"""

from __future__ import annotations

import sys

sys.path.append("..")
from copy import deepcopy
from typing import TYPE_CHECKING
from warnings import warn

from bento_meta.entity import Entity

if TYPE_CHECKING:
    import neo4j


def mergespec(
    clsname: str,
    attspec: dict[str, str],
    mapspec: dict[str, str | dict[str, str]],
) -> tuple[dict[str, str], dict[str, str | dict[str, str]]]:
    """
    Merge subclass attribute and mapping specification dicts with the base class's.

    Not for human consumption.
    """
    spec = deepcopy(attspec)
    spec.update(Entity.attspec_)
    mo = deepcopy(Entity.mapspec_)
    if "label" in mapspec:
        mo["label"] = mapspec["label"]
    if "key" in mapspec:
        mo["key"] = mapspec["key"]
    if "property" in mapspec:
        mo["property"].update(mapspec["property"])
    if "relationship" in mapspec:
        mo["relationship"].update(mapspec["relationship"])
    mo["relationship"]["_next"]["end_cls"] = {clsname}
    mo["relationship"]["_prev"]["end_cls"] = {clsname}
    return (spec, mo)


class Node(Entity):
    """Subclass that models a data node."""

    attspec_ = {
        "handle": "simple",
        "model": "simple",
        "nanoid": "simple",
        "version": "simple",
        "concept": "object",
        "props": "collection",
    }
    mapspec_ = {
        "label": "node",
        "key": "handle",
        "property": {
            "handle": "handle",
            "model": "model",
            "nanoid": "nanoid",
            "version": "version",
        },
        "relationship": {
            "concept": {"rel": ":has_concept>", "end_cls": "Concept"},
            "props": {"rel": ":has_property>", "end_cls": "Property"},
            "tags": {"rel": ":has_tag>", "end_cls": "Tag"},
        },
    }
    (attspec, _mapspec) = mergespec("Node", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Node | None = None) -> None:
        """Initialize a `Node` instance."""
        super().__init__(init=init)

    @property
    def annotations(self):
        """
        If the `Node` is annotated by `Term`s via a `Concept`,
        return the `Term`s
        """
        if self.concept:
            return self.concept.terms
        return None

    def get_key_prop(self) -> Property | list[Property] | None:
        """
        Return the `Property` entity with `is_key=True` for this `Node` if it exists.

        If multiple key props exist, return a list of them; if none exist, return None.
        """
        if not self.props.values():
            warn("No properties found for Node - returning None", stacklevel=2)
            return None
        keys = [p for p in self.props.values() if p.is_key]
        if not keys:
            warn("No key properties found for Node - returning None", stacklevel=2)
            return None
        if len(keys) == 1:
            return keys[0]
        warn("Multiple key properties found for Node - returning all", stacklevel=2)
        return keys


class Property(Entity):
    """Subclass that models a property of a node or relationship (edge)."""

    pvt_attr = Entity.pvt_attr + ["value_types"]
    attspec_ = {
        "handle": "simple",
        "model": "simple",
        "nanoid": "simple",
        "version": "simple",
        "value_domain": "simple",
        "units": "simple",
        "pattern": "simple",
        "item_domain": "simple",
        "is_required": "simple",
        "is_key": "simple",
        "is_nullable": "simple",
        "is_deprecated": "simple",
        "is_strict": "simple",
        "concept": "object",
        "value_set": "object",
        "_parent_handle": "simple",
        "version": "simple",
    }
    mapspec_ = {
        "label": "property",
        "key": "handle",
        "property": {
            "handle": "handle",
            "model": "model",
            "nanoid": "nanoid",
            "value_domain": "value_domain",
            "pattern": "pattern",
            "units": "units",
            "item_domain": "item_domain",
            "is_required": "is_required",
            "is_key": "is_key",
            "is_nullable": "is_nullable",
            "is_deprecated": "is_deprecated",
            "is_strict": "is_strict",
            "_parent_handle": "_parent_handle",
            "version": "version",
        },
        "relationship": {
            "concept": {"rel": ":has_concept>", "end_cls": "Concept"},
            "value_set": {"rel": ":has_value_set>", "end_cls": "ValueSet"},
            "tags": {"rel": ":has_tag>", "end_cls": "Tag"},
        },
    }
    (attspec, _mapspec) = mergespec("Property", attspec_, mapspec_)
    defaults = {"value_domain": "TBD"}

    def __init__(self, init: dict | neo4j.graph.Node | Property | None = None) -> None:
        """Initialize a `Property` instance."""
        super().__init__(init=init)
        self.value_types = []

    @property
    def annotations(self):
        """If the `Property` is annotated by `Term`s via a `Concept`, return the `Term`s."""
        if self.concept:
            return self.concept.terms
        return None

    @property
    def terms(self):
        """
        If the `Property` has a ``value_set`` domain, return the `Term` objects
        of its `ValueSet`
        """
        if self.value_set:
            return self.value_set.terms
        return None

    @property
    def values(self):
        """
        If the `Property` as a ``value_set`` domain, return its term values as a list of str.
        :return: list of term values
        :rtype: list
        """
        if self.value_set:
            return [self.terms[x].value for x in self.terms]


class Edge(Entity):
    """Subclass that models a relationship between model nodes."""

    defaults = {
        "multiplicity": "many_to_many",
    }
    attspec_ = {
        "handle": "simple",
        "model": "simple",
        "nanoid": "simple",
        "version": "simple",
        "multiplicity": "simple",
        "is_required": "simple",
        "src": "object",
        "dst": "object",
        "concept": "object",
        "props": "collection",
        "version": "simple",
    }
    mapspec_ = {
        "label": "relationship",
        "key": "handle",
        "property": {
            "handle": "handle",
            "model": "model",
            "nanoid": "nanoid",
            "multiplicity": "multiplicity",
            "is_required": "is_required",
            "version": "version",
        },
        "relationship": {
            "src": {"rel": ":has_src>", "end_cls": "Node"},
            "dst": {"rel": ":has_dst>", "end_cls": "Node"},
            "concept": {"rel": ":has_concept>", "end_cls": "Concept"},
            "props": {"rel": ":has_property>", "end_cls": "Property"},
            "tags": {"rel": ":has_tag>", "end_cls": "Tag"},
        },
    }
    (attspec, _mapspec) = mergespec("Edge", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Edge | None = None) -> None:
        """Initialize an `Edge` instance."""
        super().__init__(init=init)

    @property
    def annotations(self):
        """
        If the `Edge` is annotated by `Term`s via a `Concept`,
        return the `Term`s
        """
        if self.concept:
            return self.concept.terms
        return None

    @property
    def triplet(self):
        """
        A 3-tuple that fully qualifies the edge: ``(edge.handle, src.handle, dst.handle)``
        ``src`` and ``dst`` attributes must be set.
        """
        if self.handle and self.src and self.dst:
            return (self.handle, self.src.handle, self.dst.handle)


class Term(Entity):
    """Subclass that models a term from a terminology."""

    attspec_ = {
        "handle": "simple",
        "value": "simple",
        "nanoid": "simple",
        "origin_id": "simple",
        "origin_version": "simple",
        "origin_definition": "simple",
        "origin_name": "simple",
        "concept": "object",
        "origin": "object",
    }
    mapspec_ = {
        "label": "term",
        # note using 'value' as the key in terms collections may break silently
        # if the terms are coming from different origins, but use the same
        # value (string representation in data) - i.e., value is not necessarily
        # unique - should be the nanoid of the term.
        "key": "value",
        "property": {
            "handle": "handle",
            "value": "value",
            "nanoid": "nanoid",
            "origin_id": "origin_id",
            "origin_version": "origin_version",
            "origin_definition": "origin_definition",
            "origin_name": "origin_name",
        },
        "relationship": {
            "concept": {"rel": ":represents>", "end_cls": "Concept"},
            "origin": {"rel": ":has_origin>", "end_cls": "Origin"},
            "tags": {"rel": ":has_tag>", "end_cls": "Tag"},
        },
    }
    (attspec, _mapspec) = mergespec("Term", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Term | None = None) -> None:
        """Initialize a `Term` instance."""
        super().__init__(init=init)


# for ValueSet - updating terms prop should dirty the connected Property
# (from Bento::Meta), signal need to refresh. Engineer so this happens
# here (__setattr__ override), not in Entity
class ValueSet(Entity):
    """
    Subclass that models an enumerated set of :class:`Property` values.
    Essentially a container for :class:`Term` instances.
    """

    attspec_ = {
        "handle": "simple",
        "nanoid": "simple",
        "url": "simple",
        "path": "simple",
        "prop": "object",
        "origin": "object",
        "terms": "collection",
    }
    mapspec_ = {
        "label": "value_set",
        "property": {
            "handle": "handle",
            "url": "url",
            "path": "path",
            "nanoid": "nanoid",
        },
        "relationship": {
            "prop": {"rel": "<:has_value_set", "end_cls": "Property"},
            "terms": {"rel": ":has_term>", "end_cls": "Term"},
            "origin": {"rel": ":has_origin>", "end_cls": "Origin"},
            "tags": {"rel": ":has_tag>", "end_cls": "Tag"},
        },
    }
    (attspec, _mapspec) = mergespec("ValueSet", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | ValueSet | None = None) -> None:
        """Initialize a `ValueSet` instance."""
        super().__init__(init=init)

    # @property
    # def dirty(self):
    #   return self.pvt.dirty
    # @dirty.setter
    # def dirty(self, value):
    #   print("Dirty, dirty value set!")
    #   self.pvt.dirty = value
    #   if self.prop and value != 0:
    #     self.prop.dirty=1
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name == "dirty":
            if self.prop and value != 0:
                self.prop.dirty = 1


class Concept(Entity):
    """Subclass that models a semantic concept."""

    attspec_ = {"terms": "collection"}
    mapspec_ = {
        "label": "concept",
        "relationship": {
            "terms": {"rel": "<:represents", "end_cls": "Term"},
            "tags": {"rel": ":has_tag>", "end_cls": "Tag"},
        },
    }
    (attspec, _mapspec) = mergespec("Concept", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Concept | None = None) -> None:
        """Initialize a `Concept` instance."""
        super().__init__(init=init)


class Predicate(Entity):
    """Subclass that models a semantic link between concepts."""

    attspec_ = {"handle": "simple", "subject": "object", "object": "object"}
    mapspec_ = {
        "label": "predicate",
        "key": "handle",
        "property": {
            "handle": "handle",
        },
        "relationship": {
            "subject": {"rel": ":has_subject>", "end_cls": "Concept"},
            "object": {"rel": ":has_object>", "end_cls": "Concept"},
            "tags": {"rel": ":has_tag>", "end_cls": "Tag"},
        },
    }
    (attspec, _mapspec) = mergespec("Predicate", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Predicate | None = None) -> None:
        super().__init__(init=init)


class Origin(Entity):
    """Subclass that models a :class:`Term` 's authoritative source."""

    attspec_ = {
        "url": "simple",
        "is_external": "simple",
        "name": "simple",
        "nanoid": "simple",
    }
    mapspec_ = {
        "label": "origin",
        "key": "name",
        "property": {
            "name": "name",
            "url": "url",
            "is_external": "is_external",
            "nanoid": "nanoid",
        },
        "relationship": {"tags": {"rel": ":has_tag>", "end_cls": "Tag"}},
    }
    (attspec, _mapspec) = mergespec("Origin", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Origin | None = None) -> None:
        """Initialize an `Origin` instance."""
        super().__init__(init=init)


class Tag(Entity):
    """Subclass that allows simple key-value tagging of a model at arbitrary points."""

    attspec_ = {"key": "simple", "value": "simple", "_parent": "object"}
    mapspec_ = {
        "label": "tag",
        "key": "key",
        "property": {"key": "key", "value": "value"},
        "relationship": {"_parent": {"rel": "<:has_tag", "end_cls": "Entity"}},
    }
    (attspec, _mapspec) = mergespec("Tag", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Tag | None = None) -> None:
        super().__init__(init=init)


class Model(Entity):
    """Subclass with information regarding data model."""

    attspec_ = {
        "handle": "simple",
        "name": "simple",
        "repository": "simple",
        "nanoid": "simple",
        "version": "simple",
        "is_latest_version": "simple",
    }
    mapspec_ = {
        "label": "model",
        "key": "handle",
        "property": {
            "handle": "handle",
            "name": "name",
            "repository": "repository",
            "version": "version",
            "is_latest_version": "is_latest_version",
        },
    }
    (attspec, _mapspec) = mergespec("Model", attspec_, mapspec_)
    defaults = {"is_latest_version": False}

    def __init__(self, init: dict | neo4j.graph.Node | Model | None = None) -> None:
        """Initialize a `Model` instance."""
        super().__init__(init=init)
