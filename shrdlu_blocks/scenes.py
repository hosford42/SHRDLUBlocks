"""Functionality pertaining to the arrangement and state of objects within the
simulated environment."""

import time
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional, Iterator

from shrdlu_blocks.geometry import PolygonalShape, Point, inside_triangle, make_grasper, \
    make_table, make_block, make_pyramid, make_box
from shrdlu_blocks.typedefs import ObjectID, Color


__all__ = ['PhysicalObject', 'Scene', 'make_standard_scene']


@dataclass
class PhysicalObject:
    """A physical object that can appear within a scene."""

    # The shape of the object. Points in the shape are positioned relative to
    # the shape's center of mass.
    shape: PolygonalShape

    # The color of the object.
    color: Color

    # The position of the object's center of mass within the scene.
    position: Point

    # Metadata attached to the object.
    tags: Dict[str, Any]

    def __str__(self) -> str:
        kind = 'object'
        obj_id = None
        attributes = []
        for key, value in sorted(self.tags.items()):
            if key == 'kind':
                kind = value
            elif key == 'obj_id':
                obj_id = value
            elif isinstance(value, bool):
                if value:
                    attributes.append(key)
            elif isinstance(value, str):
                if value not in attributes:
                    attributes.append(value)
            elif value is not None:
                attributes.append('%s=%r' % (key, value))
        if obj_id is None:
            return kind + '[' + ','.join(attributes) + ']'
        else:
            return kind + '#' + str(obj_id) + '[' + ','.join(attributes) + ']'

    def find_highest_point(self) -> Optional[Point]:
        """Return the highest salient point of the object, or None if the
        object contains no salient points."""
        if self.tags.get('kind', None) == 'box':
            # Boxes get special treatment. We ignore their sides.
            highest_point = self.position
        else:
            highest_point = max(self.shape.iter_salient_points(), key=lambda p: p.z, default=None)
        if highest_point is None:
            return None
        return self.position + highest_point

    def is_below_point(self, point: Point) -> bool:
        """Return whether any part of the object is directly underneath the
        given point."""
        relative_position = point - self.position
        point_projection = Point(relative_position.x, relative_position.y, 0)
        for surface in self.shape.surfaces:
            surface_projection = sorted({Point(p.x, p.y, 0) for p in surface.iter_salient_points()},
                                        key=lambda p: tuple(p))
            # Find any triangle that contains the point.
            for index1, a in enumerate(surface_projection):
                for index2 in range(index1 + 1, len(surface_projection)):
                    b = surface_projection[index2]
                    for index3 in range(index2 + 1, len(surface_projection)):
                        c = surface_projection[index3]
                        if inside_triangle(point_projection, (a, b, c)):
                            return True
        return False

    def can_support(self, obj: 'PhysicalObject') -> bool:
        """Return whether this object can support the other given their current
        (x, y) coordinates. (The relative elevation, z, is ignored.)"""
        if not self.tags.get('can_support', False):
            return False
        kind = self.tags.get('kind', None)
        if kind == 'box':
            # Boxes get special treatment; we cannot set something down if it would land on the side
            # of the box.
            return all(self.is_below_point(obj.position + point)
                       for point in obj.shape.iter_salient_points())
        return self.is_below_point(obj.position)


@dataclass
class Scene:
    """An arrangement of objects within a larger space."""

    # The objects appearing in the scene.
    objects: Tuple[PhysicalObject, ...]

    # Metadata attached to the scene.
    tags: Dict[str, Any]

    def find_objects(self, **tags) -> Iterator[PhysicalObject]:
        """Return an iterator over all objects whose tag values precisely match
        the provided keyword arguments. If no keyword arguments are provided,
        an iterator over all objects is returned."""
        for obj in self.objects:
            if all(obj.tags.get(key, None) == value for key, value in tags.items()):
                yield obj


def make_standard_scene() -> Scene:
    """Construct the standard scene and return it. The standard scene is an
    approximation of the initial arrangement of objects as appearing in the
    original SHDRLU program."""

    grasper = PhysicalObject(
        make_grasper(0.05, 1),
        Color(230, 230, 0),
        Point(0, 0, 0.5),
        dict(kind='grasper', color='yellow', graspable=False, can_support=False)
    )

    table = PhysicalObject(
        make_table(1, 1),
        Color(0, 0, 0),
        Point(0, 0, 0),
        dict(kind='table', color='black', graspable=False, can_support=True)
    )

    big_red_block = PhysicalObject(
        make_block(0.15, 0.15, 0.15),
        Color(255, 0, 0),
        Point(-0.3, 0.1, 0),
        dict(kind='block', size='big', height='tall', width='wide', color='red', graspable=True,
             can_support=True, resting_on=table)
    )

    small_red_block = PhysicalObject(
        make_block(0.1, 0.1, 0.08),
        Color(255, 0, 0),
        Point(-0.25, -0.2, 0),
        dict(kind='block', size='small', height='short', width='narrow', color='red',
             graspable=True, can_support=True, resting_on=table)
    )

    small_green_pyramid = PhysicalObject(
        make_pyramid(0.1, 0.1, 0.08),
        Color(0, 255, 0),
        Point(-0.25, -0.2, 0.08),
        dict(kind='pyramid', size='small', height='short', width='narrow', color='green',
             graspable=True, can_support=False, resting_on=small_red_block)
    )

    medium_sized_green_block = PhysicalObject(
        make_block(0.15, 0.15, 0.1),
        Color(0, 255, 0),
        Point(-0.3, 0.05, 0.15),
        dict(kind='block', size='medium', height='medium', width='wide', color='green',
             graspable=True, can_support=True, resting_on=big_red_block)
    )

    tall_blue_block = PhysicalObject(
        make_block(0.15, 0.15, 0.2),
        Color(0, 0, 255),
        Point(-0.1, 0.4, 0),
        dict(kind='block', size='big', height='tall', width='medium', color='blue', graspable=True,
             can_support=True, resting_on=table)
    )

    big_green_block = PhysicalObject(
        make_block(0.2, 0.2, 0.15),
        Color(0, 255, 0),
        Point(0.1, -0.15, 0),
        dict(kind='block', size='big', height='tall', width='wide', color='green', graspable=True,
             can_support=True, resting_on=table)
    )

    tall_red_pyramid = PhysicalObject(
        make_pyramid(0.1, 0.1, 0.2),
        Color(255, 0, 0),
        Point(0.15, -0.1, 0.15),
        dict(kind='pyramid', size='medium', height='tall', width='narrow', color='red',
             graspable=True, can_support=False, resting_on=big_green_block)
    )

    big_white_box = PhysicalObject(
        make_box(0.35, 0.35, 0.2),
        Color(255, 255, 255),
        Point(0.25, 0.25, 0),
        dict(kind='box', size='big', height='medium', width='wide', color='white', graspable=False,
             can_support=True, resting_on=table)
    )

    wide_blue_pyramid = PhysicalObject(
        make_pyramid(0.15, 0.15, 0.1),
        Color(0, 0, 255),
        Point(0.25, 0.25, 0),
        dict(kind='pyramid', size='medium', height='medium', width='medium', color='blue',
             graspable=True, can_support=False, resting_on=big_white_box)
    )

    objects = [
        grasper,
        table,
        big_red_block,
        small_red_block,
        small_green_pyramid,
        medium_sized_green_block,
        tall_blue_block,
        big_green_block,
        tall_red_pyramid,
        big_white_box,
        wide_blue_pyramid,
    ]
    for index, obj in enumerate(objects):
        obj.tags['obj_id'] = ObjectID(index)
    for obj in objects:
        resting_on = obj.tags.get('resting_on', None)
        if resting_on is not None:
            assert isinstance(resting_on, PhysicalObject)
            obj.tags['resting_on'] = resting_on.tags['obj_id']
    return Scene(tuple(objects), dict(created=time.time()))
