"""Functionality for viewing and interacting with a scene."""
import logging
import textwrap
import threading
import time
from collections import deque
from typing import Optional, Tuple, Callable, List, Any

import pygame.display
from shrdlu_blocks.control import Controller
from shrdlu_blocks.geometry import Point
from shrdlu_blocks.scenes import Scene, make_standard_scene
from shrdlu_blocks.typedefs import Color

__all__ = ['Viewer']


LOGGER = logging.getLogger(__name__)


ResponseCallback = Callable[[Controller, str], str]


class Viewer:
    """An interactive scene viewer.

    The viewer provides a fixed-perspective view of the scene. The user can
    type text into the viewer. When the user hits return, the text is submitted
    to a callback, along with a controller associated with the displayed scene.
    The callback can then interact with the scene via the controller based on
    the text entered by the user.
    """

    def __init__(self, screen, title: str = None, callback: ResponseCallback = None,
                 initial_output: str = None):
        self._screen = screen
        self._width = self._screen.get_width()
        self._height = self._screen.get_height()

        self._callback = callback
        self._title = title
        self._zoom = min(self._width, self._height) / 2
        self._screen_center = Point(self._width / 2, 0, self._height / 2)
        self._center_adjustment_ratio = min(self._width, self._height) * 0.01
        self._zoom_adjustment_ratio = 5 / 4
        self._view_center = Point(0, 0, 0)
        self._x_axis = Point(1, 0, 0)
        self._y_axis = Point(0, 1, 0)
        self._z_axis = Point(0, 0, 1)
        self._wall_color = Color(255, 255, 255)
        self._y_to_x_bleed_rate = 0.2
        self._y_to_z_bleed_rate = 0.2

        if title:
            pygame.display.set_caption(title)

        self._scene: Optional[Scene] = make_standard_scene()
        self._controller = Controller(self._scene)

        self._text_height = 25
        self._input_text_color = Color(0, 0, 0)
        self._output_text_color = Color(0, 0, 255)
        self._font = pygame.font.Font(None, self._text_height)
        self._output_text_box = pygame.Rect(0.0, self._height - 2 * self._text_height,
                                            self._width, self._text_height)
        self._input_text_box = pygame.Rect(0.0, self._height - self._text_height,
                                           self._width, self._text_height)
        self._initial_output = initial_output or ''
        self._output_text = self._initial_output
        self._input_text = ''
        self._input_enabled = True

        self._highlight_flash_seconds = 0.5

        self._input_available = threading.Event()
        self._input_queue = deque()
        self._output_queue = deque()

    @property
    def scene(self) -> Optional[Scene]:
        """The scene displayed by the viewer."""
        return self._scene

    @scene.setter
    def scene(self, scene: Optional[Scene]) -> None:
        """The scene displayed by the viewer."""
        self._scene = scene
        self._controller = None if scene is None else Controller(scene)
        self._input_text = ''
        self._output_text = self._initial_output

    @property
    def title(self) -> Optional[str]:
        """The title for the viewer window."""
        return self._title

    @title.setter
    def title(self, value: Optional[str]) -> None:
        """The title for the viewer window."""
        if self._title != value:
            pygame.display.set_caption(value or '')
            self._title = value

    @property
    def callback(self) -> Optional[Callable[[Controller, str], str]]:
        """The callback for handling text input to the viewer."""
        return self._callback

    @callback.setter
    def callback(self, value: Optional[Callable[[Controller, str], str]]) -> None:
        """The callback for handling text input to the viewer."""
        self._callback = value

    @property
    def input_available(self) -> bool:
        """Whether there is input from the user currently waiting to be processed."""
        return bool(self._input_queue)

    def wait_for_input(self, timeout: float = None) -> None:
        """Wait for an input to become available."""
        if not self._input_queue:
            self._input_available.wait(timeout)
        self._input_available.clear()

    def get_input(self) -> Optional[str]:
        """Get the next input from the user."""
        if self._input_queue:
            return self._input_queue.popleft()
        return None

    def send_output(self, text: str) -> None:
        """Show an output to the user."""
        LOGGER.info("Output received asynchronously:\n%s", text)
        self._output_queue.append(text)

    def move_camera(self, relative_position: Point) -> None:
        self._view_center += relative_position

    def adjust_zoom(self, relative_zoom: float) -> None:
        self._zoom *= relative_zoom

    def run(self):
        try:
            while self.handle_events():
                self.display_scene()
                self.display_input_text_box()
                self.display_output_text_box()
                pygame.display.flip()
        except pygame.error as e:
            # Silence a couple of harmless exceptions that can happen when we quit from
            # another thread.
            e_str = str(e)
            if 'video system not initialized' in e_str or 'display Surface quit' in e_str:
                return
            raise

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif self._scene and self._input_enabled and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    input_text = self._input_text
                    self._input_text = ''
                    if self._callback:
                        thread = threading.Thread(target=self._run_callback, args=(input_text,))
                        thread.start()
                    else:
                        self._input_queue.append(input_text)
                        self._input_available.set()
                elif event.key == pygame.K_BACKSPACE:
                    self._input_text = self._input_text[:-1]
                else:
                    self._input_text += event.unicode
        if self._output_queue:
            self._output_text = self._output_queue.popleft()
            LOGGER.info("Displaying output:\n%s", self._output_text)
        return True

    def display_scene(self) -> None:
        highlighting_active = int(time.time() / self._highlight_flash_seconds) % 2
        self._screen.fill(self._wall_color)
        if not self._scene:
            return
        polygons = []
        for obj in self._scene.objects:
            transformed_shape = self._screen_center - self._view_center + \
                                (obj.position + obj.shape) * self._zoom
            if highlighting_active and obj.tags.get('highlight', False):
                color = obj.tags.get('highlight_color', None)
                if color is None:
                    # If no color specified, choose a suitable one automatically.
                    r, g, b = obj.color
                    color = Color(255 * (r < 128), 255 * (g < 128), 255 * (b < 255))
            else:
                color = obj.color
            for surface in transformed_shape.surfaces:
                remaining_edges = set(surface.edges)
                edge = remaining_edges.pop()
                points = [edge.start, edge.end]
                while remaining_edges:
                    for edge in remaining_edges:
                        if edge.start == points[-1]:
                            points.append(edge.end)
                            remaining_edges.remove(edge)
                            break
                        elif edge.end == points[-1]:
                            points.append(edge.start)
                            remaining_edges.remove(edge)
                            break
                    else:
                        assert not remaining_edges, remaining_edges
                polygons.append((color, points))
        polygons.sort(key=lambda polygon: tuple(sorted(((point.y, -point.x, -point.z)
                                                        for point in polygon[1]),
                                                       reverse=True)),
                      reverse=True)
        for color, points in polygons:
            points = [self._map_point_to_screen(point) for point in points]
            if len(points) > 2:
                pygame.draw.polygon(self._screen, color, points)
                pygame.draw.polygon(self._screen, (0, 0, 0), points, width=1)
            else:
                assert len(points) == 2
                pygame.draw.aaline(self._screen, color, points[0], points[1])

    def display_output_text_box(self):
        width, height, surfaces = self._wrap_text(self._output_text, self._output_text_color)
        self._output_text_box.w = width
        self._output_text_box.h = height
        self._output_text_box.top = self._input_text_box.top - height
        for cumulative_height, surface in surfaces:
            self._screen.blit(surface, (self._output_text_box.x + 5,
                                        self._output_text_box.y + 5 + cumulative_height))

    def display_input_text_box(self):
        width, height, surfaces = self._wrap_text(self._input_text, self._input_text_color)
        self._input_text_box.w = width
        self._input_text_box.h = height
        self._input_text_box.top = self._height - height
        self._output_text_box.top = self._input_text_box.top - self._input_text_box.h
        for cumulative_height, surface in surfaces:
            self._screen.blit(surface, (self._input_text_box.x + 5,
                                        self._input_text_box.y + 5 + cumulative_height))

    def _map_point_to_screen(self, point: Point) -> Tuple[float, float]:
        x, y, z = point
        screen_x = x + self._y_to_x_bleed_rate * y
        screen_y = self._height - (z + self._y_to_z_bleed_rate * y)
        return screen_x, screen_y

    def _wrap_text(self, text: str, color: Color) -> Tuple[int, int, List[Tuple[int, Any]]]:
        lines = [line for line in text.splitlines(keepends=False) if line.strip()]
        if not lines:
            lines.append('')
        text_surfaces = [self._font.render(line, True, color) for line in lines]
        max_width = max((surface.get_width() for surface in text_surfaces), default=0) + 10

        # Progressively reduce line width until the wrapped lines fit inside the window.
        line_width = max((len(line) for line in lines), default=0)
        while max_width > self._width:
            line_width -= 1
            text_surfaces = []
            for original_line in lines:
                for line in textwrap.wrap(original_line, width=line_width):
                    text_surfaces.append(self._font.render(line, True, color))
            max_width = max((surface.get_width() for surface in text_surfaces), default=0) + 10

        cumulative_height = [0]
        for surface in text_surfaces:
            cumulative_height.append(cumulative_height[-1] + 5 + surface.get_height())
        total_height = cumulative_height[-1] + 5

        return max_width, total_height, list(zip(cumulative_height, text_surfaces))

    def _run_callback(self, input_text: str) -> None:
        self._input_enabled = False
        for line in input_text.splitlines(keepends=False):
            LOGGER.info('Input:\n%s', line)
        # noinspection PyBroadException
        try:
            assert self._controller is not None
            output_text = self._callback(self._controller, input_text)
            if output_text and not isinstance(output_text, str):
                raise TypeError(output_text)
            if output_text is None:
                LOGGER.info('No synchronous output.')
            else:
                LOGGER.info('Output received synchronously:\n%s', output_text)
            if output_text is not None:
                self._output_queue.append(output_text)
        except Exception:
            LOGGER.exception("Error in callback:")
        finally:
            self._input_enabled = True
