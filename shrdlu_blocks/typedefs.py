"""Simple type definitions with no dependencies."""

from typing import NamedTuple


__all__ = ['UnmetConditionError', 'ObjectID', 'Color']


class UnmetConditionError(Exception):
    """A required condition for a command or query issued to a controller was
    not met."""


class ObjectID(int):
    """A unique identifier for each object in a scene."""


# An RGB-formatted color specifier.
Color = NamedTuple('Color', [('red', int), ('green', int), ('blue', int)])
