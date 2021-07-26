"""Functionality pertaining to the geometry of objects."""

import math
from abc import ABC, abstractmethod
from typing import Tuple, TypeVar, Generic, Callable, Type, Iterator, Iterable, Union


__all__ = ['GeometricObject', 'Point', 'Edge', 'PolygonalSurface', 'PolygonalShape',
           'make_table', 'make_box', 'make_block', 'make_pyramid', 'make_grasper',
           'triangle_area', 'inside_triangle']


Element = TypeVar('Element')
Self = TypeVar('Self')


class GeometricObject(Generic[Element], ABC):
    """Base class for geometric objects -- points, edges, surfaces, and shapes.

    Geometric objects are immutable, hashable, comparable, iterable, and
    indexable."""

    @classmethod
    @abstractmethod
    def _from_elements(cls: Type[Self], elements: Iterable[Element]) -> Self:
        raise NotImplementedError()

    @abstractmethod
    def _get_elements(self) -> Tuple[Element, ...]:
        raise NotImplementedError()

    def apply_elementwise_transform(self: Self, transform: Callable[[Element], Element]) -> Self:
        """Construct a new object of the same type by applying the same
        transform individually to each element."""
        return self._from_elements(transform(element) for element in self._get_elements())

    def iter_salient_points(self: Self) -> Iterator['Point']:
        """Iterate over the salient points in the object. Salient points are
        points that are explicitly mentioned in the object's structure, e.g.,
        the start and end of an edge."""
        for element in self._get_elements():
            yield from element.iter_salient_points()

    def __repr__(self) -> str:
        return type(self).__name__ + repr(self._get_elements())

    def __hash__(self) -> int:
        return hash(self._get_elements())

    def __eq__(self, other: 'GeometricObject') -> bool:
        if type(self) != type(other):
            return NotImplemented
        return self._get_elements() == other._get_elements()

    def __ne__(self, other: 'GeometricObject') -> bool:
        return not self == other

    def __iter__(self) -> Iterator[Element]:
        return iter(self._get_elements())

    def __len__(self) -> int:
        return len(self._get_elements())

    def __contains__(self, item: Element) -> bool:
        return item in self._get_elements()

    def __getitem__(self, index: int) -> Element:
        return self._get_elements()[index]

    def __add__(self: Self, other: 'Point') -> Self:
        return self.apply_elementwise_transform(lambda e: e + other)

    def __radd__(self: Self, other: 'Point') -> Self:
        return self.__add__(other)

    def __sub__(self: Self, other: 'Point') -> Self:
        return self.apply_elementwise_transform(lambda e: e - other)

    def __rsub__(self: Self, other: 'Point') -> Self:
        return self.apply_elementwise_transform(lambda e: other - e)

    def __mul__(self: Self, other: float) -> Self:
        return self.apply_elementwise_transform(lambda e: e * other)

    def __rmul__(self: Self, other: float) -> Self:
        return self.__mul__(other)

    def __truediv__(self: Self, other: float) -> Self:
        return self.apply_elementwise_transform(lambda e: e / other)

    def scale(self: Self, factor: float, center: 'Point' = None) -> Self:
        """Scale the object by the given factor. If center is provided, it is
        treated as the point whose position is invariant under the scaling
        transformation. If center is not provided, the origin is assumed."""
        if center:
            return center + factor * (self - center)
        else:
            return factor * self


class Point(GeometricObject[float]):
    """An arbitrary point in 3D space."""

    def __init__(self, x: float, y: float, z: float):
        self._x = x
        self._y = y
        self._z = z
        self._elements = (x, y, z)

    @property
    def x(self) -> float:
        """The coordinate of the point along the x dimension, which is negative
        to the left and positive to the right."""
        return self._x

    @property
    def y(self) -> float:
        """The coordinate of the point along the y dimension, which is positive
        in the direction the viewer is facing and negative behind the viewer."""
        return self._y

    @property
    def z(self) -> float:
        """The coordinate of the point along the z dimension, which is positive
        above 'ground level' and negative below it."""
        return self._z

    @classmethod
    def _from_elements(cls: Type[Self], elements: Iterable[float]) -> Self:
        return Point(*elements)

    def _get_elements(self) -> Tuple[float, ...]:
        return self._elements

    def iter_salient_points(self: Self) -> Iterator['Point']:
        """Iterate over the salient points in the object. Salient points are
        points that are explicitly mentioned in the object's structure, e.g.,
        the start and end of an edge."""
        yield self

    def __neg__(self) -> 'Point':
        return Point(-self.x, -self.y, -self.z)

    def __abs__(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def __add__(self, other: 'Point') -> 'Point':
        if not isinstance(other, Point):
            return NotImplemented
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Point') -> 'Point':
        if not isinstance(other, Point):
            return NotImplemented
        return Point(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other: Union[float, 'Point']) -> 'Point':
        if isinstance(other, (int, float)):
            return Point(self.x * other, self.y * other, self.z * other)
        elif isinstance(other, Point):
            return Point(self.x * other.x, self.y * other.y, self.z * other.z)
        else:
            return NotImplemented

    def __truediv__(self, other: Union[float, 'Point']) -> 'Point':
        if isinstance(other, (int, float)):
            return Point(self.x / other, self.y / other, self.z / other)
        elif isinstance(other, Point):
            return Point(self.x / other.x, self.y / other.y, self.z / other.z)
        else:
            return NotImplemented


class Edge(GeometricObject[Point]):
    """An arbitrary line segment in 3D space."""

    def __init__(self, start: Point, end: Point):
        self._start = start
        self._end = end
        self._elements = (start, end)

    @property
    def start(self) -> Point:
        """The point where the edge starts."""
        return self._start

    @property
    def end(self) -> Point:
        """The point where the edge ends."""
        return self._end

    @classmethod
    def _from_elements(cls: Type[Self], elements: Iterable[Point]) -> Self:
        return Edge(*elements)

    def _get_elements(self) -> Tuple[Point, Point]:
        return self._elements


class PolygonalSurface(GeometricObject[Edge]):
    """An arbitrary 2D polygon in 3D space.

    NOTE: The coplanarity of the points is assumed rather than validated by
          this class."""

    def __init__(self, edges: Tuple[Edge, ...]):
        self._edges = edges

    def __repr__(self) -> str:
        return type(self).__name__ + '(' + repr(self._edges) + ')'

    @property
    def edges(self) -> Tuple[Edge, ...]:
        """The edges of this surface."""
        return self._edges

    @classmethod
    def _from_elements(cls: Type[Self], elements: Iterable[Edge]) -> Self:
        return PolygonalSurface(tuple(elements))

    def _get_elements(self) -> Tuple[Edge, ...]:
        return self._edges


class PolygonalShape(GeometricObject[PolygonalSurface]):
    """An arbitrary 3D polygonal shape in 3D space.

    NOTE: Self-consistency is assumed rather than validated by this class."""

    def __init__(self, surfaces: Tuple[PolygonalSurface, ...]):
        self._surfaces = surfaces

    def __repr__(self) -> str:
        return type(self).__name__ + '(' + repr(self._surfaces) + ')'

    @property
    def surfaces(self) -> Tuple[PolygonalSurface, ...]:
        """The surfaces of this shape."""
        return self._surfaces

    @classmethod
    def _from_elements(cls: Type[Self], elements: Iterable[PolygonalSurface]) -> Self:
        return PolygonalShape(tuple(elements))

    def _get_elements(self) -> Tuple[PolygonalSurface, ...]:
        return self._surfaces


def make_block(width: float, depth: float, height: float) -> PolygonalShape:
    """Construct a PolygonalShape representing a box (a cuboid/rectangular
    prism) and return it."""
    left = -width / 2
    right = width / 2
    front = -depth / 2
    back = depth / 2
    top = height
    bottom = 0
    x_span = (left, right)
    y_span = (front, back)
    z_span = (bottom, top)
    corners = []
    for x in x_span:
        for y in y_span:
            for z in z_span:
                corners.append(Point(x, y, z))
    assert len(corners) == 8
    edges = []
    for index, point1 in enumerate(corners):
        for point2 in corners[index + 1:]:
            adjacent = sum(coord1 != coord2 for coord1, coord2 in zip(point1, point2)) == 1
            if adjacent:
                edges.append(Edge(point1, point2))
    assert len(edges) == 12
    surfaces = []
    for x in x_span:
        selected_edges = tuple(edge for edge in edges if edge.start[0] == edge.end[0] == x)
        assert len(selected_edges) == 4, (x, selected_edges)
        surface = PolygonalSurface(selected_edges)
        surfaces.append(surface)
    for y in y_span:
        selected_edges = tuple(edge for edge in edges if edge.start[1] == edge.end[1] == y)
        assert len(selected_edges) == 4
        surface = PolygonalSurface(selected_edges)
        surfaces.append(surface)
    for z in z_span:
        selected_edges = tuple(edge for edge in edges if edge.start[2] == edge.end[2] == z)
        assert len(selected_edges) == 4
        surface = PolygonalSurface(selected_edges)
        surfaces.append(surface)
    assert len(surfaces) == 6
    return PolygonalShape(tuple(surfaces))


def make_box(width: float, depth: float, height: float) -> PolygonalShape:
    """Construct a PolygonalShape representing an open-topped box (a
    cuboid/rectangular prism minus the top surface) and return it."""
    left = -width / 2
    right = width / 2
    front = -depth / 2
    back = depth / 2
    top = height
    bottom = 0
    x_span = (left, right)
    y_span = (front, back)
    z_span = (bottom, top)
    corners = []
    for x in x_span:
        for y in y_span:
            for z in z_span:
                corners.append(Point(x, y, z))
    assert len(corners) == 8
    edges = []
    for index, point1 in enumerate(corners):
        for point2 in corners[index + 1:]:
            adjacent = sum(coord1 != coord2 for coord1, coord2 in zip(point1, point2)) == 1
            if adjacent:
                edges.append(Edge(point1, point2))
    assert len(edges) == 12
    surfaces = []
    for x in x_span:
        selected_edges = tuple(edge for edge in edges if edge.start[0] == edge.end[0] == x)
        assert len(selected_edges) == 4
        surface = PolygonalSurface(selected_edges)
        surfaces.append(surface)
    for y in y_span:
        selected_edges = tuple(edge for edge in edges if edge.start[1] == edge.end[1] == y)
        assert len(selected_edges) == 4
        surface = PolygonalSurface(selected_edges)
        surfaces.append(surface)
    selected_edges = tuple(edge for edge in edges if edge.start[2] == edge.end[2] == bottom)
    assert len(selected_edges) == 4
    surface = PolygonalSurface(selected_edges)
    surfaces.append(surface)
    assert len(surfaces) == 5
    return PolygonalShape(tuple(surfaces))


def make_pyramid(width: float, depth: float, height: float) -> PolygonalShape:
    """Construct a PolygonalShape representing a rectangular pyramid and return
    it."""
    left = -width / 2
    right = width / 2
    front = -depth / 2
    back = depth / 2
    top = height
    bottom = 0
    x_span = (left, right)
    y_span = (front, back)
    bottom_corners = []
    for x in x_span:
        for y in y_span:
            bottom_corners.append(Point(x, y, bottom))
    assert len(bottom_corners) == 4
    peak = Point(sum(x_span) / 2, sum(y_span) / 2, top)
    bottom_edges = []
    for index, point1 in enumerate(bottom_corners):
        for point2 in bottom_corners[index + 1:]:
            adjacent = sum(coord1 != coord2 for coord1, coord2 in zip(point1, point2)) == 1
            if adjacent:
                bottom_edges.append(Edge(point1, point2))
    assert len(bottom_edges) == 4
    side_edges = [Edge(corner, peak) for corner in bottom_corners]
    assert len(side_edges) == 4
    bottom_surface = PolygonalSurface(tuple(bottom_edges))
    side_surfaces = []
    for bottom_edge in bottom_edges:
        edges = [bottom_edge]
        for side_edge in side_edges:
            if side_edge.start in bottom_edge:
                edges.append(side_edge)
        assert len(edges) == 3
        side_surface = PolygonalSurface(tuple(edges))
        side_surfaces.append(side_surface)
    assert len(side_surfaces) == 4
    return PolygonalShape(tuple([bottom_surface] + side_surfaces))


def make_table(width: float, depth: float) -> PolygonalShape:
    """Construct a PolygonalShape representing the surface of a table (i.e. a
    flat rectangular surface) and return it."""
    left = -width / 2
    right = width / 2
    front = -depth / 2
    back = depth / 2
    bottom = 0
    x_span = (left, right)
    y_span = (front, back)
    corners = []
    for x in x_span:
        for y in y_span:
            corners.append(Point(x, y, bottom))
    assert len(corners) == 4
    edges = []
    for index, point1 in enumerate(corners):
        for point2 in corners[index + 1:]:
            adjacent = sum(coord1 != coord2 for coord1, coord2 in zip(point1, point2)) == 1
            if adjacent:
                edges.append(Edge(point1, point2))
    assert len(edges) == 4, edges
    surface = PolygonalSurface(tuple(edges))
    return PolygonalShape((surface,))


def make_grasper(width: float, height: float) -> PolygonalShape:
    """Construct a PolygonalShape representing a grasper (a mechanical 'hand'
    suspended from a rod or wire) and return it."""
    left = -width / 2
    right = width / 2
    front = -width / 2
    back = width / 2
    top = height
    bottom = 0
    claw_edge1 = Edge(
        Point(left, 0, 0),
        Point(right, 0, 0)
    )
    claw_edge2 = Edge(
        Point(0, front, 0),
        Point(0, back, 0)
    )
    arm_edge = Edge(
        Point(0, 0, bottom),
        Point(0, 0, top)
    )
    return PolygonalShape(
        (PolygonalSurface((claw_edge1,)),
         PolygonalSurface((claw_edge2,)),
         PolygonalSurface((arm_edge,)))
    )


def triangle_area(triangle: Tuple[Point, Point, Point]) -> float:
    """Return the area of a triangle formed by three points in 3D space."""
    a, b, c = triangle
    ab = b - a
    ac = c - a
    return 0.5 * math.sqrt((ab.y * ac.z - ab.z * ac.y) ** 2 +
                           (ab.z * ac.x - ab.x * ac.z) ** 2 +
                           (ab.x * ac.y - ab.y * ac.x) ** 2)


def inside_triangle(point: Point, triangle: Tuple[Point, Point, Point],
                    tolerance: float = 0.001) -> bool:
    """Return whether the given 3D point falls on (or close to) a triangle in
    3D space."""
    abc_area = triangle_area(triangle)
    a, b, c = triangle
    pbc_area = triangle_area((point, b, c))
    apc_area = triangle_area((a, point, c))
    abp_area = triangle_area((a, b, point))
    return abc_area * (1 + tolerance) >= pbc_area + apc_area + abp_area
