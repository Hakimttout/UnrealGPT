#!/usr/bin/env python3
"""Scene building automation for Unreal Engine 5.6."""

import json
import logging
import pathlib
import sys
from typing import Any, Dict, List, Optional, Type, Union

import unreal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Unreal Engine constants
ATTACH_KEEP_WORLD = unreal.AttachmentRule.KEEP_WORLD
ATTACH_KEEP_RELATIVE = unreal.AttachmentRule.KEEP_RELATIVE
ATTACH_SNAP_TO_TARGET = unreal.AttachmentRule.SNAP_TO_TARGET

# Basic asset paths
BASIC_ASSETS = {
    "cube": "/Engine/BasicShapes/Cube.Cube",
    "plane": "/Engine/BasicShapes/Plane.Plane",
    "cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
    "sphere": "/Engine/BasicShapes/Sphere.Sphere"
}

# Basic material paths
BASIC_MATERIALS = {
    "floor": "/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial",
    "wall": "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial",
    "wood": "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial",
    "metal": "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial",
    "fabric": "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial",
    "glass": "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial",
    "plastic": "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial",
    "default": "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial"
}

# Object design mapping
OBJECT_DESIGN_MAP = {
    # Furniture
    "bed": {"mesh": "cube", "material": "fabric", "description": "Rectangular bed"},
    "table": {"mesh": "cube", "material": "wood", "description": "Wooden table"},
    "chair": {"mesh": "cube", "material": "wood", "description": "Simple chair"},
    "couch": {"mesh": "cube", "material": "fabric", "description": "Soft couch"},
    "sofa": {"mesh": "cube", "material": "fabric", "description": "Comfortable sofa"},
    "wardrobe": {"mesh": "cube", "material": "wood", "description": "Tall wardrobe"},
    "bookshelf": {"mesh": "cube", "material": "wood", "description": "Book storage"},
    "desk": {"mesh": "cube", "material": "wood", "description": "Work desk"},
    "bedside_table": {"mesh": "cube", "material": "wood", "description": "Bedside table"},
    "coffee_table": {"mesh": "cube", "material": "wood", "description": "Coffee table"},
    
    # Lighting
    "lamp": {"mesh": "cylinder", "material": "metal", "description": "Cylindrical lamp"},
    "rocket_lamp": {"mesh": "cylinder", "material": "metal", "description": "Rocket-shaped lamp"},
    "skylight": {"mesh": "plane", "material": "glass", "description": "Rectangular skylight window"},
    "directionallight": {"mesh": "plane", "material": "default", "description": "Directional light source"},
    
    # Decorative objects
    "vase": {"mesh": "cylinder", "material": "default", "description": "Decorative vase"},
    "plant": {"mesh": "cylinder", "material": "default", "description": "Potted plant"},
    "picture": {"mesh": "plane", "material": "default", "description": "Wall picture"},
    "mirror": {"mesh": "plane", "material": "metal", "description": "Reflective mirror"},
    "clock": {"mesh": "cylinder", "material": "default", "description": "Wall clock"},
    
    # Architectural elements
    "floor": {"mesh": "cube", "material": "floor", "description": "Room floor"},
    "wall": {"mesh": "cube", "material": "wall", "description": "Room wall"},
    "ceiling": {"mesh": "cube", "material": "default", "description": "Room ceiling"},
    "door": {"mesh": "cube", "material": "wood", "description": "Room door"},
    "window": {"mesh": "cube", "material": "glass", "description": "Room window"},
    "doorway": {"mesh": "cube", "material": "default", "description": "Room opening"},
    
    # Default fallback
    "default": {"mesh": "cube", "material": "default", "description": "Generic object"}
}

# Default values
DEFAULT_ROOM_MARGIN = 50.0
DEFAULT_LIGHT_INTENSITY = 3000.0
DEFAULT_LIGHT_COLOR = [1.0, 1.0, 1.0]
DEFAULT_MAP_PATH = "/Game/BlockOutBuilder/Generated/BlockOutScene"


def log_message(message: str, *args: Any) -> None:
    """Log an info message to Unreal Engine console."""
    formatted_msg = f"[BuildScene] {message % args if args else message}"
    unreal.log(formatted_msg)


def log_warning(message: str, *args: Any) -> None:
    """Log a warning message to Unreal Engine console."""
    formatted_msg = f"[BuildScene] {message % args if args else message}"
    unreal.log_warning(formatted_msg)


def log_error(message: str, *args: Any) -> None:
    """Log an error message to Unreal Engine console."""
    formatted_msg = f"[BuildScene] {message % args if args else message}"
    unreal.log_error(formatted_msg)


def get_level_editor_subsystem() -> unreal.LevelEditorSubsystem:
    """Get the level editor subsystem."""
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def open_level(map_path: str) -> None:
    """Open or create the specified level.
    
    Args:
        map_path: Path to the map to open
    """
    try:
        level_subsystem = get_level_editor_subsystem()
        # Create a new level instead of trying to load existing one
        level_subsystem.new_level(map_path)
        log_message("Created new level %s", map_path)
    except Exception as e:
        log_error("Failed to create level %s: %s", map_path, e)
        raise


def save_current_level(target_map_path: str = DEFAULT_MAP_PATH) -> None:
    """Save the current level.
    
    Args:
        target_map_path: Path where to save the level
    """
    try:
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor_subsystem.get_editor_world()
        
        # Always save to the target path
        if unreal.EditorLoadingAndSavingUtils.save_map(world, target_map_path):
            log_message("Level saved as: %s", target_map_path)
        else:
            log_error("Failed to save level to %s", target_map_path)
            # Try alternative save method
            if unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False):
                log_message("Level saved using alternative method")
            else:
                log_warning("Failed to save level using any method")
    except Exception as e:
        log_error("Error saving level: %s", e)
        raise


def attach_actor(child: unreal.Actor, parent: unreal.Actor, use_relative_position: bool = True) -> None:
    """Attach child actor to parent actor.
    
    Args:
        child: Child actor to attach
        parent: Parent actor to attach to
        use_relative_position: Whether to use relative positioning
    """
    try:
        if use_relative_position:
            # Use relative positioning - child keeps its current position relative to parent
            child.attach_to_actor(
                parent_actor=parent,
                socket_name="",
                location_rule=ATTACH_KEEP_RELATIVE,
                rotation_rule=ATTACH_KEEP_RELATIVE,
                scale_rule=ATTACH_KEEP_RELATIVE,
                weld_simulated_bodies=False,
            )
        else:
            # Use world positioning - child keeps its absolute world position
            child.attach_to_actor(
                parent_actor=parent,
                socket_name="",
                location_rule=ATTACH_KEEP_WORLD,
                rotation_rule=ATTACH_KEEP_WORLD,
                scale_rule=ATTACH_KEEP_WORLD,
                weld_simulated_bodies=False,
            )
        log_message("Attached %s to %s", child.get_actor_label(), parent.get_actor_label())
    except Exception as e:
        log_error("Failed to attach %s to %s: %s", 
                 child.get_actor_label(), parent.get_actor_label(), e)


def assign_mesh_to_actor(actor: unreal.StaticMeshActor, mesh_path: str) -> None:
    """Assign a static mesh to an actor.
    
    Args:
        actor: Actor to assign mesh to
        mesh_path: Path to the mesh asset
    """
    try:
        mesh = unreal.load_asset(mesh_path)
        if not mesh:
            log_warning("Could not load mesh: %s", mesh_path)
            return
            
        static_mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if static_mesh_comp:
            static_mesh_comp.set_static_mesh(mesh)
            log_message("Assigned mesh %s to %s", mesh_path, actor.get_actor_label())
        else:
            log_warning("No StaticMeshComponent found on %s", actor.get_actor_label())
    except Exception as e:
        log_error("Error assigning mesh %s: %s", mesh_path, e)


def assign_material_to_actor(actor: unreal.StaticMeshActor, material_path: str) -> None:
    """Assign a material to an actor.
    
    Args:
        actor: Actor to assign material to
        material_path: Path to the material asset
    """
    try:
        material = unreal.load_asset(material_path)
        if not material:
            log_warning("Could not load material: %s", material_path)
            return
            
        static_mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if static_mesh_comp:
            static_mesh_comp.set_material(0, material)
            log_message("Assigned material %s to %s", material_path, actor.get_actor_label())
        else:
            log_warning("No StaticMeshComponent found on %s", actor.get_actor_label())
    except Exception as e:
        log_error("Error assigning material %s: %s", material_path, e)


def get_object_design(obj_type: str, obj_name: str) -> Dict[str, str]:
    """Determine the best mesh and material for an object.
    
    Args:
        obj_type: Type of the object
        obj_name: Name of the object
        
    Returns:
        Dictionary with mesh, material, and description
    """
    obj_type = obj_type.lower()
    obj_name = obj_name.lower()
    
    # Direct type mapping
    if obj_type in OBJECT_DESIGN_MAP:
        return OBJECT_DESIGN_MAP[obj_type]
    
    # Smart name-based detection
    name_mappings = {
        "lamp": "lamp",
        "light": "lamp",
        "rocket": "rocket_lamp",
        "table": "table",
        "bed": "bed",
        "couch": "couch",
        "sofa": "sofa",
        "wardrobe": "wardrobe",
        "closet": "wardrobe",
        "plant": "plant",
        "vase": "vase",
        "picture": "picture",
        "painting": "picture",
        "mirror": "mirror",
        "clock": "clock",
        "door": "door",
        "window": "window"
    }
    
    for keyword, design_key in name_mappings.items():
        if keyword in obj_name:
            return OBJECT_DESIGN_MAP[design_key]
    
    return OBJECT_DESIGN_MAP["default"]


def create_transform(position: List[float], rotation: List[float], 
                    scale: List[float]) -> unreal.Transform:
    """Create an Unreal Transform from position, rotation, and scale.
    
    Args:
        position: [x, y, z] position
        rotation: [pitch, yaw, roll] rotation in degrees or [x, y, z, w] quaternion
        scale: [x, y, z] scale factors
        
    Returns:
        Unreal Transform object
    """
    location = unreal.Vector(position[0], position[1], position[2])
    
    # Handle rotation
    if len(rotation) == 3:
        rotator = unreal.Rotator(rotation[0], rotation[1], rotation[2])
    elif len(rotation) == 4:
        quat = unreal.Quat(rotation[0], rotation[1], rotation[2], rotation[3])
        rotator = quat.rotator()
    else:
        log_warning("Invalid rotation format: %s, using default", rotation)
        rotator = unreal.Rotator(0, 0, 0)
    
    scale_vector = unreal.Vector(scale[0], scale[1], scale[2])
    
    return unreal.Transform(location, rotator, scale_vector)


def spawn_actor(actor_class: Type[unreal.Actor], transform: unreal.Transform,
                label: Optional[str] = None) -> unreal.Actor:
    """Spawn an actor in the world.
    
    Args:
        actor_class: Class of actor to spawn
        transform: Transform for the actor
        label: Optional label for the actor
        
    Returns:
        Spawned actor
    """
    try:
        location = transform.translation
        rotation = transform.rotation.rotator()
        
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class, location, rotation
        )
        actor.set_actor_scale3d(transform.scale3d)
        
        if label:
            actor.set_actor_label(label, True)
            
        return actor
    except Exception as e:
        log_error("Failed to spawn actor %s: %s", actor_class.__name__, e)
        raise


def apply_object_design(actor: unreal.StaticMeshActor, obj_type: str, 
                       obj_name: str, obj_data: Optional[Dict[str, Any]] = None) -> None:
    """Apply mesh and material design to an actor.
    
    Args:
        actor: Actor to apply design to
        obj_type: Type of object
        obj_name: Name of object
        obj_data: Optional object data with overrides
    """
    design = get_object_design(obj_type, obj_name)
    
    # Override mesh type if specified
    if obj_data and obj_data.get("mesh_type"):
        mesh_type = obj_data["mesh_type"]
        if mesh_type in BASIC_ASSETS:
            design["mesh"] = mesh_type
            log_message("Overriding mesh for '%s' to %s", obj_name, mesh_type)
    
    # Override material type if specified
    if obj_data and obj_data.get("material_type"):
        material_type = obj_data["material_type"]
        if material_type in BASIC_MATERIALS:
            design["material"] = material_type
            log_message("Overriding material for '%s' to %s", obj_name, material_type)
    
    # Assign mesh and material
    mesh_path = BASIC_ASSETS[design["mesh"]]
    material_path = BASIC_MATERIALS[design["material"]]
    
    assign_mesh_to_actor(actor, mesh_path)
    assign_material_to_actor(actor, material_path)
    
    log_message("Applied design to '%s': %s", obj_name, design["description"])


def create_rocket_lamp(name: str, transform: unreal.Transform, 
                      obj_data: Optional[Dict[str, Any]] = None) -> unreal.Actor:
    """Create a rocket-shaped lamp with multiple components.
    
    Args:
        name: Name for the lamp
        transform: Transform for the lamp
        obj_data: Optional object data
        
    Returns:
        Main parent actor
    """
    try:
        # Create main parent actor (invisible base) at the specified transform position
        parent_actor = spawn_actor(unreal.StaticMeshActor, transform, f"{name}_base")
        parent_location = parent_actor.get_actor_location()
        
        # Create all components with relative positioning to the parent
        components = []
        
        # --- PARAMETERS -------------------------------------------------------
        body_scale = [0.3, 0.3, 0.8]
        nose_scale = [0.2, 0.2, 0.3]
        fin_scale  = [0.1, 0.1, 0.2]
        cylinder_half_height = 50.0  # UU (UE default cylinder 100 high)
        cube_half_height     = 50.0  # UU 

        body_half_height = cylinder_half_height * body_scale[2]
        nose_half_height = cylinder_half_height * nose_scale[2]
        fin_half_height  = cube_half_height     * fin_scale[2]

        # ----------------- BODY --------------------------------------------
        body_transform = create_transform([0, 0, 0], [0, 0, 0], body_scale)
        body = spawn_actor(unreal.StaticMeshActor, body_transform, f"{name}_body")
        assign_mesh_to_actor(body, BASIC_ASSETS["cylinder"])
        assign_material_to_actor(body, BASIC_MATERIALS["metal"])
        attach_actor(body, parent_actor, use_relative_position=True)
        body.set_actor_relative_location(unreal.Vector(0, 0, body_half_height), False, False)
        components.append(body)

        # ----------------- NOSE --------------------------------------------
        nose_transform = create_transform([0, 0, 0], [0, 0, 0], nose_scale)
        nose = spawn_actor(unreal.StaticMeshActor, nose_transform, f"{name}_nose")
        assign_mesh_to_actor(nose, BASIC_ASSETS["cylinder"])
        assign_material_to_actor(nose, BASIC_MATERIALS["metal"])
        attach_actor(nose, parent_actor, use_relative_position=True)
        nose.set_actor_relative_location(unreal.Vector(0, 0, body_half_height*2 + nose_half_height), False, False)
        components.append(nose)

        # ----------------- FINS --------------------------------------------
        fin_positions_xy = [[15, 0], [-15, 0], [0, 15], [0, -15]]
        for i, (fx, fy) in enumerate(fin_positions_xy):
            fin_transform = create_transform([0, 0, 0], [0, 0, 0], fin_scale)
            fin = spawn_actor(unreal.StaticMeshActor, fin_transform, f"{name}_fin_{i}")
            assign_mesh_to_actor(fin, BASIC_ASSETS["cube"])
            assign_material_to_actor(fin, BASIC_MATERIALS["metal"])
            attach_actor(fin, parent_actor, use_relative_position=True)
            fin.set_actor_relative_location(unreal.Vector(fx, fy, fin_half_height), False, False)
            components.append(fin)
        
        # ----------------- LIGHT ------------------------------------------
        if obj_data and obj_data.get("intensity"):
            light_actor = configure_light_component(parent_actor, obj_data)
            if light_actor:
                attach_actor(light_actor, parent_actor, use_relative_position=True)
                light_actor.set_actor_relative_location(unreal.Vector(0, 0, body_half_height*2 + 50), False, False)
                components.append(light_actor)
        
        log_message("Created rocket lamp: %s with %d components at position [%s, %s, %s]", 
                   name, len(components), parent_location.x, parent_location.y, parent_location.z)
        return parent_actor
        
    except Exception as e:
        log_error("Failed to create rocket lamp %s: %s", name, e)
        raise


def configure_light_component(actor: unreal.Actor, obj_data: Dict[str, Any]) -> Optional[unreal.Actor]:
    """Configure light component on an actor.
    
    Args:
        actor: Actor to add light to
        obj_data: Object data with light properties
        
    Returns:
        Created light actor or None if failed
    """
    try:
        # For StaticMeshActor, we need to use a different approach
        # Create a separate light actor instead of adding component
        intensity = obj_data.get("intensity", DEFAULT_LIGHT_INTENSITY)
        color = obj_data.get("color", DEFAULT_LIGHT_COLOR)
        
        # Get actor location for light positioning
        actor_location = actor.get_actor_location()
        light_location = unreal.Vector(
            actor_location.x, 
            actor_location.y, 
            actor_location.z + 50.0  # Slightly above the actor
        )
        
        # Create point light actor
        light_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PointLight, 
            light_location, 
            unreal.Rotator(0, 0, 0)
        )
        
        if light_actor:
            # Set light properties
            light_component = light_actor.get_component_by_class(unreal.PointLightComponent)
            if light_component:
                light_component.set_intensity(intensity)
                light_color = unreal.LinearColor(color[0], color[1], color[2], 1.0)
                light_component.set_light_color(light_color)
                
                # Set light actor label
                light_actor.set_actor_label(f"{actor.get_actor_label()}_Light", True)
                
                log_message("Created separate light actor for %s (intensity: %s, color: %s)", 
                           actor.get_actor_label(), intensity, color)
                return light_actor
            else:
                log_warning("Could not find PointLightComponent on created light actor")
                return None
        else:
            log_warning("Failed to create light actor for %s", actor.get_actor_label())
            return None
        
    except Exception as e:
        log_error("Failed to configure light for %s: %s", actor.get_actor_label(), e)
        return None


def validate_object_position(obj_pos: List[float], room_data: Dict[str, Any], 
                           margin: float = DEFAULT_ROOM_MARGIN) -> List[float]:
    """Validate and adjust object position within room bounds.
    
    Args:
        obj_pos: Object position [x, y, z]
        room_data: Room data with size and position
        margin: Margin from room edges
        
    Returns:
        Validated position
    """
    room_pos = room_data.get("position", [0, 0, 0])
    room_size = room_data.get("size", [600, 800, 350])
    
    # Calculate room bounds
    min_x = room_pos[0] + margin
    max_x = room_pos[0] + room_size[0] - margin
    min_y = room_pos[1] + margin
    max_y = room_pos[1] + room_size[1] - margin
    
    # Clamp position within bounds
    validated_pos = [
        max(min_x, min(max_x, obj_pos[0])),
        max(min_y, min(max_y, obj_pos[1])),
        obj_pos[2]  # Don't clamp Z
    ]
    
    if validated_pos != obj_pos:
        log_message("Adjusted object position from %s to %s", obj_pos, validated_pos)
    
    return validated_pos


def create_room_geometry(room_data: Dict[str, Any]) -> List[unreal.Actor]:
    """Create floor, walls, and ceiling for a room.
    
    Args:
        room_data: Room configuration data
        
    Returns:
        List of created actors
    """
    actors = []
    room_name = room_data.get("name", "room")
    room_pos = room_data.get("position", [0, 0, 0])
    room_size = room_data.get("size", [600, 800, 350])
    
    try:
        # Create floor
        floor_transform = create_transform(
            [room_pos[0] + room_size[0]/2, room_pos[1] + room_size[1]/2, room_pos[2]],
            [0, 0, 0],
            [room_size[0]/100, room_size[1]/100, 0.1]
        )
        floor = spawn_actor(unreal.StaticMeshActor, floor_transform, f"{room_name}_floor")
        apply_object_design(floor, "floor", f"{room_name}_floor")
        actors.append(floor)
        
        # Create walls (4 walls)
        wall_configs = [
            # Front wall
            {
                "pos": [room_pos[0] + room_size[0]/2, room_pos[1], room_pos[2] + room_size[2]/2],
                "scale": [room_size[0]/100, 0.1, room_size[2]/100],
                "name": f"{room_name}_wall_front"
            },
            # Back wall
            {
                "pos": [room_pos[0] + room_size[0]/2, room_pos[1] + room_size[1], room_pos[2] + room_size[2]/2],
                "scale": [room_size[0]/100, 0.1, room_size[2]/100],
                "name": f"{room_name}_wall_back"
            },
            # Left wall
            {
                "pos": [room_pos[0], room_pos[1] + room_size[1]/2, room_pos[2] + room_size[2]/2],
                "scale": [0.1, room_size[1]/100, room_size[2]/100],
                "name": f"{room_name}_wall_left"
            },
            # Right wall
            {
                "pos": [room_pos[0] + room_size[0], room_pos[1] + room_size[1]/2, room_pos[2] + room_size[2]/2],
                "scale": [0.1, room_size[1]/100, room_size[2]/100],
                "name": f"{room_name}_wall_right"
            }
        ]
        
        for wall_config in wall_configs:
            wall_transform = create_transform(wall_config["pos"], [0, 0, 0], wall_config["scale"])
            wall = spawn_actor(unreal.StaticMeshActor, wall_transform, wall_config["name"])
            apply_object_design(wall, "wall", wall_config["name"])
            actors.append(wall)
        
        # Create ceiling
        ceiling_transform = create_transform(
            [room_pos[0] + room_size[0]/2, room_pos[1] + room_size[1]/2, room_pos[2] + room_size[2]],
            [0, 0, 0],
            [room_size[0]/100, room_size[1]/100, 0.1]
        )
        ceiling = spawn_actor(unreal.StaticMeshActor, ceiling_transform, f"{room_name}_ceiling")
        apply_object_design(ceiling, "ceiling", f"{room_name}_ceiling")
        actors.append(ceiling)
        
        log_message("Created room geometry for %s", room_name)
        return actors
        
    except Exception as e:
        log_error("Failed to create room geometry for %s: %s", room_name, e)
        raise


def create_scene_object(obj_data: Dict[str, Any], rooms: List[Dict[str, Any]], 
                       actor_registry: Optional[Dict[str, unreal.Actor]] = None) -> unreal.Actor:
    """Create a scene object from object data.
    
    Args:
        obj_data: Object configuration data
        rooms: List of room data for validation
        actor_registry: Registry of already created actors for parent lookup
        
    Returns:
        Created actor
    """
    try:
        obj_name = obj_data.get("name", "unnamed")
        obj_type = obj_data.get("type", "default")
        obj_pos = obj_data.get("position", [0, 0, 0])
        obj_rot = obj_data.get("rotation", [0, 0, 0])
        obj_scale = obj_data.get("scale", [1, 1, 1])
        
        # Handle null values
        if obj_pos is None:
            obj_pos = [0, 0, 0]
        if obj_rot is None:
            obj_rot = [0, 0, 0]
        if obj_scale is None:
            obj_scale = [1, 1, 1]
        
        # Calculate absolute position if object has a parent
        parent_name = obj_data.get("parent", "")
        absolute_pos = obj_pos.copy()
        
        # Check if parent is a room or an object
        parent_is_room = parent_name in [room.get("name", "") for room in rooms]
        
        # If parent exists and is not a room, we'll create the object at origin
        # and let the attachment handle positioning
        if parent_name and actor_registry and parent_name in actor_registry and not parent_is_room:
            # For objects with non-room parents, create at origin
            # The attachment process will handle the relative positioning
            absolute_pos = [0, 0, 0]
            log_message("Object %s has non-room parent %s, creating at origin for relative positioning", 
                       obj_name, parent_name)
        else:
            # Find parent room for position validation
            parent_room = None
            for room in rooms:
                room_name = room.get("name", "")
                # Try exact match first, then partial match
                if room_name == parent_name or parent_name.lower() in room_name.lower():
                    parent_room = room
                    break
            
            # Validate position ONLY if parent is actually a room
            if parent_room:
                absolute_pos = validate_object_position(absolute_pos, parent_room)
        
        # Create transform with absolute position
        transform = create_transform(absolute_pos, obj_rot, obj_scale)
        
        # OLD special handling for skylights disabled ----------------------
        if False and (obj_type == "skylight" or "skylight" in obj_name.lower()):
            # Create SkyLight actor for proper lighting
            skylight_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.SkyLight, 
                transform.translation, 
                transform.rotation.rotator()
            )
            
            if skylight_actor:
                skylight_actor.set_actor_label(obj_name, True)
                
                # Configure skylight properties
                skylight_component = skylight_actor.get_component_by_class(unreal.SkyLightComponent)
                if skylight_component:
                    intensity = obj_data.get("intensity", DEFAULT_LIGHT_INTENSITY)
                    color = obj_data.get("color", DEFAULT_LIGHT_COLOR)
                    
                    skylight_component.set_intensity(intensity / 1000.0)  # SkyLight uses different scale
                    light_color = unreal.LinearColor(color[0], color[1], color[2], 1.0)
                    skylight_component.set_light_color(light_color)
                    
                    log_message("Created SkyLight actor for %s (intensity: %s, color: %s)", 
                               obj_name, intensity, color)
                else:
                    log_warning("Could not find SkyLightComponent on created SkyLight actor")
                
                # Try to find and attach to ceiling if parent is a room
                if parent_name and parent_name in [room.get("name", "") for room in rooms]:
                    # Find the ceiling actor
                    ceiling_name = f"{parent_name}_ceiling"
                    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
                    ceiling_actor = None
                    for actor in all_actors:
                        if actor.get_actor_label() == ceiling_name:
                            ceiling_actor = actor
                            break
                    
                    if ceiling_actor:
                        # Position skylight at ceiling level
                        ceiling_pos = ceiling_actor.get_actor_location()
                        skylight_pos = unreal.Vector(
                            absolute_pos[0], 
                            absolute_pos[1], 
                            ceiling_pos.z
                        )
                        skylight_actor.set_actor_location(skylight_pos, False, False)
                        attach_actor(skylight_actor, ceiling_actor, use_relative_position=True)
                        log_message("Attached skylight to ceiling at [%s, %s, %s]", 
                                   skylight_pos.x, skylight_pos.y, skylight_pos.z)
                    else:
                        log_warning("Could not find ceiling actor %s for skylight attachment", ceiling_name)
                
                return skylight_actor
            else:
                log_warning("Failed to create SkyLight actor for %s", obj_name)
                # Fallback to regular actor
                pass
        
        # Special handling for rocket lamps
        if obj_type == "rocket_lamp" or "rocket" in obj_name.lower():
            return create_rocket_lamp(obj_name, transform, obj_data)
        
        # Create standard actor
        actor = spawn_actor(unreal.StaticMeshActor, transform, obj_name)
        apply_object_design(actor, obj_type, obj_name, obj_data)

        # NEW skylight handling: attach panel to ceiling and add light
        if obj_type == "skylight":
            parent_room_name = parent_name if parent_name else ""
            if parent_room_name in [room.get("name", "") for room in rooms]:
                ceiling_name = f"{parent_room_name}_ceiling"
                all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
                ceiling_actor = None
                for a in all_actors:
                    if a.get_actor_label() == ceiling_name:
                        ceiling_actor = a
                        break
                if ceiling_actor:
                    ceiling_pos = ceiling_actor.get_actor_location()
                    # Position skylight at ceiling height keeping X,Y
                    new_pos = unreal.Vector(absolute_pos[0], absolute_pos[1], ceiling_pos.z)
                    actor.set_actor_location(new_pos, False, False)
                    attach_actor(actor, ceiling_actor, use_relative_position=True)
                    # Center panel exactly on ceiling pivot
                    actor.set_actor_relative_location(unreal.Vector(0, 0, 0), False, False)
                    log_message("Attached skylight panel to ceiling at [%s, %s, %s]", new_pos.x, new_pos.y, new_pos.z)
            # Add point light to the panel
            if obj_data.get("intensity") is not None:
                light_actor = configure_light_component(actor, obj_data)
                if light_actor:
                    # Reattach to panel and offset 50uu below ceiling
                    attach_actor(light_actor, actor, use_relative_position=True)
                    light_actor.set_actor_relative_location(unreal.Vector(0, 0, -50.0), False, False)
                    log_message("Added light to skylight panel")

        # Configure light if needed for non-skylight objects
        if obj_data.get("intensity") is not None:
            configure_light_component(actor, obj_data)
        
        # Flush vertical alignment for rocket lamp (and other children if needed)
        if "rocket_lamp" in obj_name.lower():
            try:
                child_center, child_extent = actor.get_actor_bounds(False)
                parent_center, parent_extent = parent_actor.get_actor_bounds(False)
                child_bottom_z = child_center.z - child_extent.z
                parent_top_z   = parent_center.z + parent_extent.z
                z_offset = parent_top_z - child_bottom_z
                if abs(z_offset) > 0.1:
                    # Move the child upward/downward by z_offset
                    actor.add_actor_world_offset(unreal.Vector(0, 0, z_offset), False)
                    log_message("Adjusted %s by %.2f uu to rest on %s", actor.get_actor_label(), z_offset, parent_actor.get_actor_label())
            except Exception as e:
                log_warning("Failed rocket lamp vertical alignment: %s", e)
        
        return actor
        
    except Exception as e:
        log_error("Failed to create object %s: %s", obj_data.get("name", "unnamed"), e)
        raise


def refresh_editor_viewport():
    """Force refresh of the Unreal Editor viewport and level editor after building the scene."""
    try:
        # Get the level editor subsystem
        level_editor_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        
        # Toggle game view to force refresh (using the modern approach)
        level_editor_subsystem.editor_set_game_view(False)
        level_editor_subsystem.editor_set_game_view(True)
        level_editor_subsystem.editor_set_game_view(False)
        
        # Refresh the content browser by scanning asset paths synchronously
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        asset_registry.scan_paths_synchronous(["/Game/"], True)
        
        print("[BuildScene] Refreshed editor viewport and level")
    except Exception as e:
        print(f"[BuildScene] Failed to refresh editor viewport: {e}")


def build_scene(scene_data: Dict[str, Any]) -> None:
    """Build the complete scene from scene data.
    
    Args:
        scene_data: Complete scene configuration
    """
    try:
        # Open level
        map_path = scene_data.get("map", DEFAULT_MAP_PATH)
        open_level(map_path)
        
        # Create rooms
        rooms = scene_data.get("rooms", [])
        room_actors = []
        
        for room_data in rooms:
            room_geometry = create_room_geometry(room_data)
            room_actors.extend(room_geometry)
        
        log_message("Created %d rooms with %d actors", len(rooms), len(room_actors))
        
        # Create objects
        objects = scene_data.get("objects", [])
        object_actors = []
        actor_registry = {}  # Keep track of created actors by ID
        
        for obj_data in objects:
            try:
                actor = create_scene_object(obj_data, rooms, actor_registry)
                object_actors.append(actor)
                # Register actor by its ID for parent-child relationships
                obj_id = obj_data.get("id", obj_data.get("name", ""))
                if obj_id:
                    actor_registry[obj_id] = actor
            except Exception as e:
                log_error("Failed to create object %s: %s", obj_data.get("name", "unnamed"), e)
                continue

        log_message("Created %d objects", len(object_actors))
        
        # Apply parent-child relationships
        for obj_data in objects:
            try:
                parent_id = obj_data.get("parent", "")
                obj_id = obj_data.get("id", obj_data.get("name", ""))
                
                # Skip if no parent or if parent is a room name
                if not parent_id or parent_id in [room.get("name", "") for room in rooms]:
                    continue

                # Find parent and child actors
                parent_actor = actor_registry.get(parent_id)
                child_actor = actor_registry.get(obj_id)
                
                if parent_actor and child_actor:
                    # Get the relative position from the object data
                    child_relative_pos = obj_data.get("position", [0, 0, 0])
                    
                    # Attach child actor first, then set its relative offset as defined in JSON
                    attach_actor(child_actor, parent_actor, use_relative_position=True)
                    
                    # Appliquer la position relative voulue
                    child_actor.set_actor_relative_location(
                        unreal.Vector(child_relative_pos[0], child_relative_pos[1], child_relative_pos[2]),
                        False, False
                    )
                    
                    # (On ne fait plus de déplacement absolu préalable)
                    
                    # Handle light components for the child actor
                    light_actor_name = f"{child_actor.get_actor_label()}_Light"
                    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
                    for actor in all_actors:
                        if actor.get_actor_label() == light_actor_name:
                            # Attach light to child actor first (keep current relative offset)
                            attach_actor(actor, child_actor, use_relative_position=True)
                            # Pour les objets standards, placer la lumière 50 uu au-dessus
                            if "rocket_lamp" not in child_actor.get_actor_label().lower():
                                actor.set_actor_relative_location(unreal.Vector(0, 0, 50.0), False, False)
                            break
                    
                    log_message("Attached %s to %s at relative position [%s, %s, %s]", 
                               child_actor.get_actor_label(), 
                               parent_actor.get_actor_label(),
                               child_relative_pos[0], child_relative_pos[1], child_relative_pos[2])
                else:
                    if not parent_actor:
                        log_warning("Parent actor not found for %s (parent: %s)", 
                                   obj_data.get("name", ""), parent_id)
                    if not child_actor:
                        log_warning("Child actor not found for %s", obj_data.get("name", ""))
                        
            except Exception as e:
                log_error("Failed to apply parent-child relationship for %s: %s", 
                         obj_data.get("name", ""), e)
                continue
        
        # Save level
        save_current_level(map_path)
        
        # Force refresh of the editor viewport
        refresh_editor_viewport()
        
        log_message("Scene build completed successfully")
        
    except Exception as e:
        log_error("Scene build failed: %s", e)
        raise


def load_scene_file(file_path: str) -> Dict[str, Any]:
    """Load scene data from JSON file.
    
    Args:
        file_path: Path to the scene JSON file
        
    Returns:
        Scene data dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        log_message("Loaded scene file: %s", file_path)
        return scene_data
        
    except FileNotFoundError:
        log_error("Scene file not found: %s", file_path)
        raise
    except json.JSONDecodeError as e:
        log_error("Invalid JSON in scene file %s: %s", file_path, e)
        raise
    except Exception as e:
        log_error("Failed to load scene file %s: %s", file_path, e)
        raise


def main() -> None:
    """Main entry point for the scene builder."""
    try:
        # Determine scene file path
        if len(sys.argv) > 1:
            scene_file = sys.argv[1]
        else:
            # Try default location
            scene_file = "demo/scene.json"
            if not pathlib.Path(scene_file).exists():
                log_error("No scene file specified and default not found")
                log_error("Usage: BuildScene.py <scene.json>")
                return
        
        # Load and build scene
        scene_data = load_scene_file(scene_file)
        build_scene(scene_data)
        
        log_message("Scene building completed successfully")
        
    except Exception as e:
        log_error("Scene building failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
