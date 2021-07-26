"""
A simple demo of the environment.

Usage:
    python3 -m shrdlu_blocks.demo

The environment will be displayed in a graphics window. The user can type
various commands into the graphics window to query the scene and control the
grasper. Type `help` to get a list of commands.
"""

import ast
import io
import sys
import traceback

import pygame.display

from shrdlu_blocks.control import Controller
from shrdlu_blocks.typedefs import UnmetConditionError, ObjectID
from shrdlu_blocks.scenes import make_standard_scene, PhysicalObject
from shrdlu_blocks.viewer import Viewer


__all__ = ['demo']


def demo_callback(controller: Controller, command: str) -> str:
    """Parse and execute the command."""
    if command == 'exit':
        pygame.quit()
        sys.exit(0)
    output_buffer = io.StringIO()
    if command == 'help':
        print("Commands:", file=output_buffer)
        print("    help", file=output_buffer)
        print("    exit", file=output_buffer)
        for name in dir(controller):
            if not name.startswith('_'):
                print("    " + name, file=output_buffer)
        return output_buffer.getvalue()
    pieces = command.split()
    command = pieces.pop(0)
    if not command:
        return output_buffer.getvalue()
    if '.' in command or command.startswith('_') or command not in dir(controller):
        print("ERROR: Invalid command", file=output_buffer)
        return output_buffer.getvalue()
    # noinspection PyBroadException
    try:
        args = []
        for piece in pieces:
            try:
                arg = ast.literal_eval(piece)
            except ValueError:
                arg = piece
            args.append(arg)
        result = getattr(controller, command)(*args)
        if result is None:
            pass
        elif isinstance(result, str) or not hasattr(result, '__iter__'):
            print(repr(result), file=output_buffer)
        else:
            object_count = len(list(controller.find_objects()))
            for item in result:
                if ('objects' in command and isinstance(item, int) and
                        0 <= item < object_count):
                    tags = dict(controller.iter_object_tags(ObjectID(item)))
                    # Cheat just a little by constructing a mock object with the tags so we can use
                    # the __str__() method it defines.
                    # noinspection PyTypeChecker
                    mock_obj = PhysicalObject(None, None, None, tags)
                    print(str(mock_obj), file=output_buffer)
                else:
                    print(repr(item), file=output_buffer)
    except UnmetConditionError as e:
        print(e, file=output_buffer)
    except Exception:
        traceback.print_exc(file=output_buffer)
    return output_buffer.getvalue()


def demo():
    """
    Let the user play around with the standard scene using programmatic
    instructions passed directly to the controller.

    The environment will be displayed in a graphics window. The user can type
    various commands into the graphics window to query the scene and control
    the grasper. Type `help` to get a list of commands.
    """

    pygame.init()

    screen_info = pygame.display.Info()
    screen_width = screen_info.current_w
    screen_height = screen_info.current_h
    screen = pygame.display.set_mode((screen_width // 2, screen_height // 2))

    Viewer(screen, "SHRDLU Blocks Demo", demo_callback).run()


if __name__ == '__main__':
    demo()
