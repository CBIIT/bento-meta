"""Value-set composition objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento_meta.objects import ValueSet


class CompositionOp(str, Enum):
    """Operations supported by value-set composition."""

    UNION = "Union"


@dataclass(frozen=True)
class VSCompositionStep:
    """One ordered operation in a value-set composition."""

    value_set: ValueSet
    op: CompositionOp = CompositionOp.UNION


@dataclass
class VSComposition:
    """An ordered value-set composition recipe."""

    steps: list[VSCompositionStep] = field(default_factory=list)