#!/usr/bin/env python3
"""Default values and validation for scene objects."""

import logging
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Default values
DEFAULT_ROOM_SIZE = [600.0, 800.0, 350.0]
DEFAULT_ROOM_POSITION = [0.0, 0.0, 0.0]
DEFAULT_ROOM_ROTATION = [0.0, 0.0, 0.0]
DEFAULT_MAP_PATH = "/Game/BlockOutBuilder/Generated/BlockOutScene"

DEFAULT_OBJECT_POSITION = [0.0, 0.0, 0.0]
DEFAULT_OBJECT_ROTATION = [0.0, 0.0, 0.0]
DEFAULT_OBJECT_SCALE = [1.0, 1.0, 1.0]
DEFAULT_OBJECT_PARENT = "living_room"

# Light-specific defaults
DEFAULT_LIGHT_INTENSITY = 3000.0
DEFAULT_LIGHT_COLOR = [1.0, 1.0, 1.0]

# Furniture-specific defaults
DEFAULT_FURNITURE_MATERIAL = "wood"
DEFAULT_FURNITURE_MESH = "cube"


def apply_defaults(scene_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply default values to scene data ensuring all required fields are present.
    
    Args:
        scene_data: Raw scene data dictionary
        
    Returns:
        Scene data with all defaults applied
        
    Raises:
        ValueError: If scene_data is missing required top-level keys
    """
    if not isinstance(scene_data, dict):
        raise ValueError("Scene data must be a dictionary")
    
    # Validate required keys
    if 'rooms' not in scene_data:
        raise ValueError("Scene data must contain 'rooms' key")
    if 'objects' not in scene_data:
        raise ValueError("Scene data must contain 'objects' key")
    
    # Apply map default
    scene_data.setdefault('map', DEFAULT_MAP_PATH)
    
    # Apply room defaults
    for room in scene_data['rooms']:
        _apply_room_defaults(room)
    
    # Apply object defaults
    for obj in scene_data['objects']:
        _apply_object_defaults(obj)
    
    logger.info("Applied defaults to %d rooms and %d objects", 
                len(scene_data['rooms']), len(scene_data['objects']))
    
    return scene_data


def _apply_room_defaults(room: Dict[str, Any]) -> None:
    """Apply default values to a room object.
    
    Args:
        room: Room dictionary to modify in-place
    """
    room.setdefault('size', DEFAULT_ROOM_SIZE.copy())
    room.setdefault('position', DEFAULT_ROOM_POSITION.copy())
    room.setdefault('rotation', DEFAULT_ROOM_ROTATION.copy())
    room.setdefault('map', DEFAULT_MAP_PATH)
    
    # Ensure doorways list exists
    if 'doorways' not in room:
        room['doorways'] = []


def _apply_object_defaults(obj: Dict[str, Any]) -> None:
    """Apply default values to an object based on its type.
    
    Args:
        obj: Object dictionary to modify in-place
    """
    # Basic object defaults
    if obj.get('position') is None:
        obj['position'] = DEFAULT_OBJECT_POSITION.copy()
    else:
        obj.setdefault('position', DEFAULT_OBJECT_POSITION.copy())
    
    if obj.get('rotation') is None:
        obj['rotation'] = DEFAULT_OBJECT_ROTATION.copy()
    else:
        obj.setdefault('rotation', DEFAULT_OBJECT_ROTATION.copy())
    
    if obj.get('scale') is None:
        obj['scale'] = DEFAULT_OBJECT_SCALE.copy()
    else:
        obj.setdefault('scale', DEFAULT_OBJECT_SCALE.copy())
    
    obj.setdefault('parent', DEFAULT_OBJECT_PARENT)
    
    # Remove null values that shouldn't be there
    if obj.get('rotation_quat') is None:
        obj.pop('rotation_quat', None)
    
    # Ensure required fields exist
    if 'name' not in obj:
        obj['name'] = f"unnamed_{obj.get('type', 'object')}"
    if 'id' not in obj:
        obj['id'] = f"{obj['name']}_001"
    
    # Type-specific defaults
    object_type = obj.get('type', '').lower()
    
    if _is_light_type(object_type):
        _apply_light_defaults(obj)
    elif _is_furniture_type(object_type):
        _apply_furniture_defaults(obj)
    else:
        _apply_generic_defaults(obj)


def _is_light_type(object_type: str) -> bool:
    """Check if object type is a light source.
    
    Args:
        object_type: Type string to check
        
    Returns:
        True if object is a light type
    """
    light_types = {
        'light', 'lamp', 'pointlight', 'directionallight', 
        'spotlight', 'skylight', 'rocket_lamp'
    }
    return object_type in light_types


def _is_furniture_type(object_type: str) -> bool:
    """Check if object type is furniture.
    
    Args:
        object_type: Type string to check
        
    Returns:
        True if object is furniture
    """
    furniture_types = {
        'table', 'chair', 'bed', 'sofa', 'desk', 'wardrobe',
        'bedside_table', 'coffee_table', 'bookshelf', 'cabinet'
    }
    return object_type in furniture_types


def _apply_light_defaults(obj: Dict[str, Any]) -> None:
    """Apply defaults specific to light objects.
    
    Args:
        obj: Light object dictionary to modify
    """
    obj.setdefault('intensity', DEFAULT_LIGHT_INTENSITY)
    obj.setdefault('color', DEFAULT_LIGHT_COLOR.copy())
    
    # Light-specific mesh and material defaults
    # Don't add mesh_type for rocket_lamp as it has custom creation function
    if obj.get('type') != 'rocket_lamp':
        obj.setdefault('mesh_type', 'cylinder')
        obj.setdefault('material_type', 'metal')
    
    # Special handling for rocket lamps
    if obj.get('type') == 'rocket_lamp':
        obj.setdefault('intensity', 5000.0)
        obj.setdefault('color', [1.0, 0.8, 0.6])
        obj.setdefault('material_type', 'metal')  # Material is OK, just not mesh_type


def _apply_furniture_defaults(obj: Dict[str, Any]) -> None:
    """Apply defaults specific to furniture objects.
    
    Args:
        obj: Furniture object dictionary to modify
    """
    obj.setdefault('mesh_type', DEFAULT_FURNITURE_MESH)
    obj.setdefault('material_type', DEFAULT_FURNITURE_MATERIAL)
    
    # Furniture-specific positioning
    if obj.get('type') in ['table', 'desk', 'bedside_table']:
        # Tables should be at appropriate height
        if obj['position'][2] == 0.0:
            obj['position'][2] = 37.5  # Half of standard 75cm table height
    
    elif obj.get('type') == 'bed':
        # Beds should be at appropriate height
        if obj['position'][2] == 0.0:
            obj['position'][2] = 25.0  # Half of standard 50cm bed height
    
    elif obj.get('type') in ['chair', 'sofa']:
        # Seating should be at appropriate height
        if obj['position'][2] == 0.0:
            obj['position'][2] = 40.0  # Half of standard 80cm seat height


def _apply_generic_defaults(obj: Dict[str, Any]) -> None:
    """Apply defaults for generic objects.
    
    Args:
        obj: Generic object dictionary to modify
    """
    obj.setdefault('mesh_type', 'cube')
    obj.setdefault('material_type', 'default')


def validate_scene_data(scene_data: Dict[str, Any]) -> List[str]:
    """Validate scene data and return list of issues found.
    
    Args:
        scene_data: Scene data to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    issues = []
    
    # Check top-level structure
    if not isinstance(scene_data, dict):
        issues.append("Scene data must be a dictionary")
        return issues
    
    if 'rooms' not in scene_data:
        issues.append("Missing 'rooms' key")
    elif not isinstance(scene_data['rooms'], list):
        issues.append("'rooms' must be a list")
    
    if 'objects' not in scene_data:
        issues.append("Missing 'objects' key")
    elif not isinstance(scene_data['objects'], list):
        issues.append("'objects' must be a list")
    
    # Validate rooms
    for i, room in enumerate(scene_data.get('rooms', [])):
        room_issues = _validate_room(room, i)
        issues.extend(room_issues)
    
    # Validate objects
    for i, obj in enumerate(scene_data.get('objects', [])):
        obj_issues = _validate_object(obj, i)
        issues.extend(obj_issues)
    
    return issues


def _validate_room(room: Dict[str, Any], index: int) -> List[str]:
    """Validate a single room object.
    
    Args:
        room: Room dictionary to validate
        index: Room index for error messages
        
    Returns:
        List of validation errors
    """
    issues = []
    prefix = f"Room {index}"
    
    if not isinstance(room, dict):
        issues.append(f"{prefix}: must be a dictionary")
        return issues
    
    # Check required fields
    if 'name' not in room:
        issues.append(f"{prefix}: missing 'name' field")
    
    # Check size format
    if 'size' in room:
        if not isinstance(room['size'], list) or len(room['size']) != 3:
            issues.append(f"{prefix}: 'size' must be a list of 3 numbers")
        elif not all(isinstance(x, (int, float)) for x in room['size']):
            issues.append(f"{prefix}: 'size' values must be numbers")
    
    # Check position format
    if 'position' in room:
        if not isinstance(room['position'], list) or len(room['position']) != 3:
            issues.append(f"{prefix}: 'position' must be a list of 3 numbers")
        elif not all(isinstance(x, (int, float)) for x in room['position']):
            issues.append(f"{prefix}: 'position' values must be numbers")
    
    return issues


def _validate_object(obj: Dict[str, Any], index: int) -> List[str]:
    """Validate a single object.
    
    Args:
        obj: Object dictionary to validate
        index: Object index for error messages
        
    Returns:
        List of validation errors
    """
    issues = []
    prefix = f"Object {index}"
    
    if not isinstance(obj, dict):
        issues.append(f"{prefix}: must be a dictionary")
        return issues
    
    # Check required fields
    required_fields = ['name', 'id', 'type']
    for field in required_fields:
        if field not in obj:
            issues.append(f"{prefix}: missing required field '{field}'")
    
    # Check position format
    if 'position' in obj:
        if not isinstance(obj['position'], list) or len(obj['position']) != 3:
            issues.append(f"{prefix}: 'position' must be a list of 3 numbers")
        elif not all(isinstance(x, (int, float)) for x in obj['position']):
            issues.append(f"{prefix}: 'position' values must be numbers")
    
    # Check rotation format
    if 'rotation' in obj:
        if not isinstance(obj['rotation'], list) or len(obj['rotation']) != 3:
            issues.append(f"{prefix}: 'rotation' must be a list of 3 numbers")
        elif not all(isinstance(x, (int, float)) for x in obj['rotation']):
            issues.append(f"{prefix}: 'rotation' values must be numbers")
    
    # Check scale format
    if 'scale' in obj:
        if not isinstance(obj['scale'], list) or len(obj['scale']) != 3:
            issues.append(f"{prefix}: 'scale' must be a list of 3 numbers")
        elif not all(isinstance(x, (int, float)) for x in obj['scale']):
            issues.append(f"{prefix}: 'scale' values must be numbers")
    
    # Check light properties
    if _is_light_type(obj.get('type', '')):
        if 'intensity' in obj and not isinstance(obj['intensity'], (int, float)):
            issues.append(f"{prefix}: 'intensity' must be a number")
        
        if 'color' in obj:
            if not isinstance(obj['color'], list) or len(obj['color']) != 3:
                issues.append(f"{prefix}: 'color' must be a list of 3 numbers")
            elif not all(isinstance(x, (int, float)) for x in obj['color']):
                issues.append(f"{prefix}: 'color' values must be numbers")
    
    return issues

