"""The implementation of the physics of the simulated environment."""

from typing import Optional, Any, Dict, Iterator, Tuple

from shrdlu_blocks.geometry import Point
from shrdlu_blocks.scenes import Scene, PhysicalObject
from shrdlu_blocks.typedefs import UnmetConditionError, ObjectID


__all__ = ['Controller']


class Controller:
    """The controller, through which all queries and commands between the AI
    and the simulated environment must pass."""

    # IMPORTANT: Public methods must *never* accept or return mutable Scene components. The entire
    #            point of this class is to ensure that the information and control flows between the
    #            environment and AI controller are constrained. If the simulated environment is
    #            unconstrained, it doesn't provide a useful test environment for the AI controller.

    def __init__(self, scene: Scene, grasper_distance_tolerance: float = 0.000001):
        self._scene = scene
        self._grasper_distance_tolerance = grasper_distance_tolerance
        self._default_grasper: Optional[PhysicalObject] = None
        self._grasper_cache: Dict[ObjectID, PhysicalObject] = {}

    @property
    def default_grasper(self) -> Optional[ObjectID]:
        """The default grasper that is used when no grasper is specified in
        calls to methods which require one."""
        if self._default_grasper is None:
            return None
        return self._default_grasper.tags.get('obj_id', None)

    @default_grasper.setter
    def default_grasper(self, grasper_id: ObjectID) -> None:
        """The default grasper that is used when no grasper is specified in
        calls to methods which require one."""
        self._default_grasper = self._require_grasper(grasper_id)

    def grasper_is_closed(self, grasper_id: ObjectID = None) -> bool:
        """Query whether the grasper is closed. Returns a boolean value."""
        return self._require_grasper(grasper_id).tags.get('closed', False)

    def grasper_is_lowered(self, grasper_id: ObjectID = None) -> bool:
        """Query whether the grasper is lowered. Returns a boolean value."""
        return self._require_grasper(grasper_id).tags.get('lowered', False)

    def get_grasped_object(self, grasper_id: ObjectID = None) -> Optional[ObjectID]:
        """Query which object is currently grasped by the grasper. Returns the
        object ID of the grasped object, or None if no object is currently
        grasped."""
        return self._require_grasper(grasper_id).tags.get('grasped', None)

    def close_grasper(self, grasper_id: ObjectID = None) -> None:
        """Attempt to close the grasper. If the grasper is resting on a
        graspable object and is situated at its center of mass, the grasper
        will begin grasping the object."""
        grasper = self._require_grasper(grasper_id)
        del grasper_id
        if grasper.tags.get('closed', False):
            raise UnmetConditionError('Grasper is not open.')
        if grasper.tags.get('lowered', False):
            # Find out if the grasper was lowered onto a graspable object.
            # If so, make it grasp the object.
            resting_on_id = grasper.tags.get('resting_on', None)
            if resting_on_id:
                resting_on = self._require_specific_object(resting_on_id)
                if resting_on.tags.get('graspable', False):
                    grasper.tags['grasped'] = resting_on_id
                    resting_on.tags['grasped_by'] = grasper.tags.get('obj_id', None)
        grasper.tags['closed'] = True

    def open_grasper(self, grasper_id: ObjectID = None) -> None:
        """Attempt to open the grasper. If the grasper is holding an object and
        the object is supported, the object will be released."""
        grasper = self._require_grasper(grasper_id)
        del grasper_id
        if not grasper.tags.get('closed', False):
            raise UnmetConditionError('Grasper is not closed.')
        grasped_obj_id = grasper.tags.get('grasped', None)
        if grasped_obj_id is not None:
            grasped_obj = self._require_specific_object(grasped_obj_id)
            if not grasper.tags.get('lowered', False):
                raise UnmetConditionError('Grasper must be lowered first when holding an object.')
            # If an object was grasped, we have to be above another object that can support it.
            resting_on_id = grasped_obj.tags.get('resting_on', None)
            if resting_on_id is None:
                raise UnmetConditionError('Object must be lowered onto another object that can '
                                          'support it in order to be dropped.')
            resting_on = self._require_specific_object(resting_on_id)
            if not resting_on.can_support(grasped_obj):
                raise UnmetConditionError('Object must be lowered onto another object that can '
                                          'support it in order to be dropped.')
            assert grasped_obj.tags.get('grasped_by', None) == grasper.tags.get('obj_id', None)
            # Let go of the object.
            grasped_obj.tags['grasped_by'] = None
            grasper.tags['grasped'] = None
        grasper.tags['closed'] = False

    def move_grasper(self, x: float = None, y: float = None, grasper_id: ObjectID = None) -> None:
        """Attempt to move the grasper to a new (x, y) coordinate. One or both
        coordinates must be specified. If either coordinate is omitted, its
        current value will be assumed."""
        if x is not None and not isinstance(x, (int, float)):
            raise TypeError(x)
        if y is not None and not isinstance(y, (int, float)):
            raise TypeError(y)
        grasper = self._require_grasper(grasper_id)
        del grasper_id
        if grasper.tags.get('lowered', False):
            raise UnmetConditionError('Grasper must be raised before it can be moved.')
        if x is None and y is None:
            raise UnmetConditionError('No position specified.')
        if x is not None and not grasper.tags.get('min_x', x) <= x <= grasper.tags.get('max_x', x):
            raise UnmetConditionError('The grasper cannot move there.')
        if y is not None and not grasper.tags.get('min_y', y) <= y <= grasper.tags.get('max_y', y):
            raise UnmetConditionError('The grasper cannot move there.')
        old_x, old_y, old_z = grasper.position
        grasper.position = Point(old_x if x is None else x, old_y if y is None else y, old_z)
        grasped_obj_id = grasper.tags.get('grasped', None)
        if grasped_obj_id is not None:
            grasped_obj = self._require_specific_object(grasped_obj_id)
            highest_point = grasped_obj.find_highest_point()
            height = highest_point.z - grasped_obj.position.z
            grasped_obj.position = grasper.position - Point(0, 0, height)

    def lower_grasper(self, grasper_id: ObjectID = None) -> None:
        """Attempt to lower the grasper. The grasper will be lowered until it
        or the object it is holding is resting on an object below it, or until
        the grasper is maximally extended, whichever comes first. (The grasper
        can be extended down to 'ground level', where the z coordinate is zero,
        and no further.)"""
        grasper = self._require_grasper(grasper_id)
        del grasper_id
        if grasper.tags.get('lowered', False):
            raise UnmetConditionError('Grasper is not raised.')
        target, target_height = self._find_object_below_grasper(grasper)
        grasped_obj_id = grasper.tags.get('grasped', None)
        if grasped_obj_id is None:
            # Set the grasper's position so that the grasper is resting on whatever object is below
            # it.
            grasper.position = Point(grasper.position.x,
                                     grasper.position.y,
                                     target_height)
            if target:
                x_displacement, y_displacement = (target.position - grasper.position)[:2]
                distance = (x_displacement ** 2 + y_displacement ** 2) ** 0.5
                if distance <= self._grasper_distance_tolerance:
                    grasper.tags['resting_on'] = target.tags.get('obj_id', None)
        else:
            # Set the grasper's position so that the grasped object is resting on whatever object is
            # below it. Remember to update both the grasper's and the object's positions.
            grasped_obj = self._require_specific_object(grasped_obj_id)
            highest_point = grasped_obj.find_highest_point()
            height = highest_point.z - grasped_obj.position.z
            grasper.position = Point(grasper.position.x, grasper.position.y, target_height + height)
            grasped_obj.position = Point(grasper.position.x, grasper.position.y, target_height)
            if target:
                grasped_obj.tags['resting_on'] = target.tags.get('obj_id', None)
        grasper.tags['lowered'] = True

    def raise_grasper(self, grasper_id: ObjectID = None) -> None:
        """Attempt to raise the grasper. The grasper will be raised until it
        and the object it is holding, if any, are high enough to safely clear
        all objects in the scene."""
        grasper = self._require_grasper(grasper_id)
        del grasper_id
        if not grasper.tags.get('lowered', False):
            raise UnmetConditionError('Grasper is not lowered.')
        minimum_height = self._find_highest_stable_point() + 0.1
        grasped_obj_id = grasper.tags.get('grasped', None)
        if grasped_obj_id is None:
            grasper.position = Point(grasper.position.x, grasper.position.y, minimum_height)
            grasper.tags['resting_on'] = None
        else:
            grasped_obj = self._require_specific_object(grasped_obj_id)
            grasped_obj.position = Point(grasper.position.x, grasper.position.y, minimum_height)
            highest_point = grasped_obj.find_highest_point()
            grasper.position = Point(grasper.position.x, grasper.position.y, highest_point.z)
            grasped_obj.tags['resting_on'] = None
        grasper.tags['lowered'] = False

    def find_objects(self, **tags) -> Iterator[ObjectID]:
        """Query the objects in the scene. An iterator will be returned over
        all objects in the scene whose tag values match the given keyword
        arguments exactly. If no keyword arguments are provided, an iterator
        over all objects in the scene will be returned."""
        for obj in self._scene.find_objects(**tags):
            obj_id = obj.tags.get('obj_id', None)
            if obj_id is not None:
                yield obj_id

    def get_object_tag(self, obj_id: ObjectID, tag: str, default: Any = None) -> Any:
        """Query the value of an object's tag. If the object does not have a
        value for the given tag, the default is returned."""
        return self._require_specific_object(obj_id).tags.get(tag, default)

    def iter_object_tags(self, obj_id: ObjectID) -> Iterator[Tuple[str, Any]]:
        """Query the tag key/value pairs associated with the object."""
        yield  from self._require_specific_object(obj_id).tags.items()

    def get_object_position(self, obj_id: ObjectID) -> Point:
        """Query the position of an object in the scene."""
        return self._require_specific_object(obj_id).position

    def _get_specific_grasper(self, grasper_id: ObjectID) -> Optional[PhysicalObject]:
        """Return the specific grasper indicated by the given grasper ID. If no
        such grasper exists, return None."""
        if not isinstance(grasper_id, int):
            raise TypeError(grasper_id)
        if grasper_id in self._grasper_cache:
            return self._grasper_cache[grasper_id]
        grasper = self._get_specific_object(grasper_id)
        if grasper is None:
            return None
        if grasper.tags.get('kind', None) != 'grasper':
            raise UnmetConditionError("Object is not a grasper.")
        self._grasper_cache[grasper_id] = grasper
        if self._default_grasper is None:
            self._default_grasper = grasper
        return grasper

    def _get_grasper(self, grasper_id: ObjectID = None) -> Optional[PhysicalObject]:
        """If a grasper ID is provided, return that specific grasper.
        Otherwise, return the default grasper. If the default grasper is not
        set, set it to an arbitrary grasper first. If no graspers exist in the
        scene, or the specific grasper requested does not exist, return None."""
        if grasper_id is not None:
            if not isinstance(grasper_id, int):
                raise TypeError(grasper_id)
            return self._get_specific_grasper(grasper_id)
        if self._default_grasper is not None:
            return self._default_grasper
        for grasper in self._scene.find_objects(kind='grasper'):
            self._default_grasper = grasper
            return grasper
        return None

    def _require_grasper(self, grasper_id: ObjectID = None) -> PhysicalObject:
        """If a grasper ID is provided, return that specific grasper.
        Otherwise, return the default grasper. If the default grasper is not
        set, set it to an arbitrary grasper first. If no graspers exist in the
        scene, or the specific grasper requested does not exist, raise an
        exception."""
        if grasper_id is not None and not isinstance(grasper_id, int):
            raise TypeError(grasper_id)
        grasper = self._get_grasper(grasper_id)
        if grasper is None:
            raise UnmetConditionError('Grasper not found.')
        return grasper

    def _get_specific_object(self, obj_id: ObjectID) -> Optional[PhysicalObject]:
        """Return the specific object indicated by the given object ID. If no
        such object exists, return None."""
        if not isinstance(obj_id, int):
            raise TypeError(obj_id)
        for obj in self._scene.find_objects(obj_id=obj_id):
            return obj
        return None

    def _require_specific_object(self, obj_id: ObjectID) -> PhysicalObject:
        """Return the specific object indicated by the given object ID. If no
        such object exists, raise an exception."""
        if not isinstance(obj_id, int):
            raise TypeError(obj_id)
        obj = self._get_specific_object(obj_id)
        if obj is None:
            raise UnmetConditionError('Object not found.')
        return obj

    def _find_object_below_grasper(self, grasper: PhysicalObject) \
            -> Tuple[Optional[PhysicalObject], float]:
        """Find the highest object directly below the grasper. Return a tuple
        of the form (obj, dist), where obj is the object identified and dist is
        the vertical distance from the grasper to the highest point of the
        object. If no object is found below the grasper, return (None, 0)."""
        if not isinstance(grasper, PhysicalObject):
            raise TypeError(grasper)
        # Find the object the grasper is above, if any, and its height above ground level.
        target = None
        target_height = 0
        for obj in self._scene.objects:
            if not (obj.tags.get('grasped_by', None) is None and
                    obj.is_below_point(grasper.position)):
                continue
            obj_height = obj.find_highest_point().z
            if target_height <= obj_height:
                target = obj
                target_height = obj_height
        return target, target_height

    def _find_highest_stable_point(self) -> float:
        """Find the highest point of the highest stably positioned object. An
        object is considered stably positioned if it is either immovable or
        resting on another stably positioned object."""
        result = 0
        for obj in self._scene.objects:
            if obj.tags.get('kind') == 'grasper' or obj.tags.get('grasped_by', None) is not None:
                continue
            obj_result = obj.find_highest_point()
            if obj_result is not None and obj_result.z > result:
                result = obj_result.z
        return result
