from __future__ import annotations
from typing import TYPE_CHECKING, Any, ClassVar
from dataclasses import dataclass, field
from enum import Enum
from bento_meta.objects import ValueSet

class CompositionOp(str, Enum):
    """Supported value-set composition operations."""

    UNION = "Union"

@dataclass(frozen=True)
class VSCompositionStep:
    """One union operand referencing an exact EDP version."""

    operator: CompositionOperator
    value_set: ValueSet


@dataclass
class VSComposition:
    """A value-set composition recipe."""

    steps: list[VSCompositionStep] = field(default_factory=list)

