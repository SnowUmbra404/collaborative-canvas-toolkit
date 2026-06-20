from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class PixelCell:
    x: float
    y: float
    color: str


@dataclass(frozen=True)
class Stroke:
    points: tuple
    color: str
    width: int


@dataclass(frozen=True)
class Shape:
    id: str
    kind: str
    x: float
    y: float
    w: float
    h: float
    color: str


Drawable = Union[PixelCell, Stroke, Shape]


@dataclass
class Scene:
    width: int
    height: int
    drawables: list[Drawable]
