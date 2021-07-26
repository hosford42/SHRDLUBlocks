# SHRDLU Blocks

This package is a rough approximation of the blocks environment originally used
by Terry Winograd's SHDRLU program. It is meant to provide a simple means for 
evaluating and testing natural language understanding systems. Hooking into the
environment is a matter of defining a single callback function and passing it 
into the framework.

![Screenshot](https://raw.githubusercontent.com/hosford42/SHRDLUBlocks/master/images/SHRDLU%20Blocks%20Demo%20(Cropped).png)


## Usage

```python3
"""SHRDLU Blocks app template"""

from typing import Optional

import pygame

from shrdlu_blocks.control import Controller
from shrdlu_blocks.viewer import Viewer


def callback(controller: Controller, text: str) -> Optional[str]:
    """This is where you hook your logic into the system."""
    # 1) Attempt to understand the text. 
    # 2) Determine an appropriate sequence of actions to perform.
    # 3) Perform the actions by calling the public methods of the controller.
    # 4) Return the text response.
    ...


def main():
    # Initialize pygame.
    pygame.init()

    # Create a pygame display canvas.
    screen_info = pygame.display.Info()
    screen_width = screen_info.current_w
    screen_height = screen_info.current_h
    screen = pygame.display.set_mode((screen_width // 2, screen_height // 2))
    
    # Run a scene viewer with the callback we defined.
    Viewer(screen, callback=callback).run()


if __name__ == '__main__':
    main()
```

## The Simulated Environment

The simulated environment is accessed through the controller object passed to
your callback. The controller is meant to be the sole access point for your NLU
system to interact with the environment on behalf of the user. It provides an 
*intentionally* limited interface for querying and acting upon the scene.

### Scenes

The simulated environment consists of an arbitrary collection of stateful, 
spatially arranged objects collectively referred to as a 'scene'.  

### Object Positions

Every object in the scene has an associated point in scene referred to as its 
position. The object's point of support -- the point on its bottom which is 
directly below its center of mass -- always coincides precisely with its
position.

### The Grasper

All actions on the scene are mediated by one or more grasper objects. A grasper
can only pick up a single object at a time. It can only set an object down in a 
place where the object will be supported. Attempting to drop an object with the
grasper raised, or with the grasper lowered in a place where the object
cannot be placed, will result in an exception.

### Object IDs

The controller identifies objects using unique integer indices of type 
`ObjectID`. Limited search capabilities are also provided in order to identify 
the object IDs of objects present in the scene. The controller requires that
objects always be referenced by their IDs, and only returns object IDs, never
actual objects, from queries. This is to ensure that an object's state is never
modified directly by the client, preventing the circumvention of the rules of
the simulation.

### Object Tags

Every object has an associated metadata key/value mapping referred to as the
object's "tags". Except for a few specific exceptions, these are static, 
arbitrary data points attached to the object during scene creation. Tags serve
as a means for searching through and identifying the objects in the scene. Tags
cannot be directly modified or overwritten; those whose values can change are
always modified indirectly by actions performed by the controller.

Tags with constant values that are accessed directly by the controller include:
* `obj_id` An integer value of type `ObjectID` which serves to uniquely 
  identify the object.
* `kind` A string value which indicates the type of the object. The particular
  values that the controller finds interesting are `'grasper'` and `'box'`.
* `graspable` A boolean value which indicates whether the grasper can pick up
  the object under the appropriate conditions.
* `can_support` A boolean value indicating whether this object can support 
  other objects placed on top of it.
* `min_x` An optional floating point value associated with the grasper. 
  Indicates the minimum value of the x coordinate for positions the grasper can
  be moved to.
* `max_x` An optional floating point value associated with the grasper. 
  Indicates the maximum value of the x coordinate for positions the grasper can
  be moved to.
* `min_y` An optional floating point value associated with the grasper. 
  Indicates the minimum value of the y coordinate for positions the grasper can
  be moved to.
* `max_y` An optional floating point value associated with the grasper. 
  Indicates the maximum value of the y coordinate for positions the grasper can
  be moved to.

Tags whose values are updated by the controller include:
* `closed` A boolean flag associated with the grasper indicating whether the
  grasper's 'hand' is closed.
* `grasped` An optional `ObjectID` associated with the grasper indicating the 
  object currently grasped by the grasper.
* `lowered` A boolean flag associated with the grasper indicating whether the
  grasper has been lowered. The grasper must be lowered to grasp or release an
  object.
* `grasped_by` An optional `ObjectID` associated with any object indicating the
  grasper currently grasping it.
* `resting_on` An optional `ObjectID` associated with any object indicating the
  object it is directly resting on.
  
### Controllers

#### Controller Properties

* `default_grasper` The `ObjectID` of default grasper. When a method is called
  which makes reference to a grasper, and no grasper was indicated through the
  arguments passed to the method, this is the grasper that will be used.

#### Controller Query Methods

* `find_objects` Return an iterator over all the objects in the scene that have
  the specifically requested metadata tag values.
* `get_grasped_object` Return the `ObjectID` of the object currently held by 
  the grasper.
* `get_object_position` Return the spatial position of the object's support
  point.
* `get_object_tag` Return the value of a metadata tag associated with the 
  object.
* `iter_object_tags` Return an iterator over all the tag/value metadata pairs
  associated with the object.
* `grasper_is_closed` Return whether the grasper is currently closed.
* `grasper_is_lowered` Return whether the grasper is currently lowered.

#### Controller Action Methods

* `close_grasper` Close the grasper. Under the appropriate conditions, this 
  will also cause the grasper to grasp an object.
* `lower_grasper` Lower the grasper until contact is made with an object or the
  grasper is maximally extended. If the grasper is grasping an object, the 
  object will be lowered with it.
* `move_grasper` Move the grasper to the indicated (x, y) coordinates. If the
  grasper is grasping an object, the object will be carried with it.
* `open_grasper` Open the grasper. Under the appropriate conditions, this will
  also cause the grasper to release an object it has grasped. 
* `raise_grasper` Raise the grasper. If the grasper is grasping an object, the
  object will be raised with it.

## Links to Resources

* [The Wikipedia page for SHRDLU](https://en.wikipedia.org/wiki/SHRDLU)
* [Terry Winograd's SHRDLU page](https://hci.stanford.edu/winograd/shrdlu/)
* [SHRDLU's source code](http://hci.stanford.edu/~winograd/shrdlu/code/)
* [Procedures as a Representation for Data in a Computer Program for 
  Understanding Natural Language](https://hci.stanford.edu/winograd/shrdlu/AITR-235.pdf)
* [3D Graphics with Pygame (Tutorial)](https://www.petercollingridge.co.uk/tutorials/3d/pygame/)
