"""
bento_meta.tf_objects

This module contains subclasses of :class:`Entity` that persist and organize
the representation of data transformations between model Properties.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING
from .entity import Entity
from .objects import mergespec

if TYPE_CHECKING:
    import neo4j


class Transform(Entity):
    """Subclass that models a data transformation between Properties"""
    attspec_ = {
        "handle": "simple",
        "version": "simple",
        "nanoid": "simple",
        "source": "simple",
        "first_step": "object",
        "last_step": "object",
        "input_props": "collection",
        "output_props": "collection",
        }
    mapspec_ = {
        "label": "transform",
        "key": "handle",
        "property": {
            "handle": "handle",
            "version": "version",
            "nanoid": "nanoid",
            "source": "source",
        },
        "relationship": {
            "input_props": {"rel": "<:value_as_tf_input", "end_cls": "Property"},
            "output_props": {"rel": ":tf_output_as_value", "end_cls": "Property"},
            "first_step": {"rel": "first_tf_step", "end_cls": "TfStep"},
            "last_step": {"rel": "last_tf_step", "end_cls": "TfStep"},
        }
    }
    (attspec, _mapspec) = mergespec("Transform", attspec_, mapspec_)

    def __init__(self, init: dict | neo4j.graph.Node | Transform | None = None) -> None:
        """Initialize a `Transform` instance."""
        super().__init__(init=init)


    @property
    def steps(self):
        ret = []
        s = self.first_step
        while s is not None:
            ret.append(s)
            s = s.next_step
        return ret

class TfStep(Entity):
    """
    Subclass that models a data transformation calculation step in a transform
    workflow
    """
    attspec_ = {
        "package": "simple",
        "version": "simple",
        "entrypoint": "simple",
        "params_json": "simple",
        "input_type": "simple",
        "output_type": "simple",
        "params_type": "simple",
        "next_step": "object",
    }
    mapspec_ = {
        "label": "tf_step",
        "key": "nanoid",
        "property": {
            "package": "package",
            "version": "version",
            "entrypoint": "entrypoint",
            "params_json": "params_json",
            "input_type": "input_type",
            "output_type": "output_type",
            "params_type": "params_type",
            },
        "relationship": {
            "next_step": {"rel": ":next_tf_step>", "end_cls": "TfStep"}
        },
    }
    (attspec, _mapspec) = mergespec("TfSpec", attspec_, mapspec_)
    
    def __init__(self, init: dict | neo4j.graph.Node | TfStep | None = None) -> None:
        """Initialize a `Transform` instance."""
        super().__init__(init=init)

    @property
    def params(self) -> dict | list:
        """
        This property is the python object represented by the JSON string
        contained in 'params_json' (if any)
        """
        if self.params_json is not None:
            return json.loads(self.params_json)
        return
