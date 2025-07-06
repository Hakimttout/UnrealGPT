#!/usr/bin/env python3
"""Scene generation from natural language prompts."""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, model_validator

from defaults import apply_defaults

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise EnvironmentError("OPENAI_API_KEY not found in environment")

CLIENT = OpenAI(api_key=API_KEY)

# Default values
DEFAULT_ROOM_SIZE = [400.0, 500.0, 300.0]
DEFAULT_POSITION = [0.0, 0.0, 0.0]
DEFAULT_PARENT = "living_room"
DEFAULT_MAP_PATH = "/Game/BlockOutBuilder/Generated/BlockOutScene"


class Room(BaseModel):
    """Room configuration with dimensions and position."""
    
    model_config = {"arbitrary_types_allowed": True, "extra": "forbid"}
    
    name: str
    size: List[float] = Field(default_factory=lambda: DEFAULT_ROOM_SIZE.copy())
    position: Optional[List[float]] = Field(default_factory=lambda: DEFAULT_POSITION.copy())
    doorways: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class Object3D(BaseModel):
    """3D object with position, rotation, and material properties."""
    
    name: str
    id: str
    type: str
    position: List[float] = Field(default_factory=lambda: DEFAULT_POSITION.copy())
    rotation: Optional[List[float]] = None
    rotation_quat: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    intensity: Optional[float] = None
    color: Optional[List[float]] = None
    mesh_type: Optional[str] = None
    material_type: Optional[str] = None
    parent: Optional[str] = DEFAULT_PARENT

    @model_validator(mode="after")
    def validate_rotation(self) -> "Object3D":
        """Ensure only one rotation format is used."""
        if self.rotation and self.rotation_quat:
            raise ValueError("Use either 'rotation' or 'rotation_quat', not both")
        if self.rotation and len(self.rotation) != 3:
            raise ValueError("'rotation' must contain exactly 3 values")
        if self.rotation_quat and len(self.rotation_quat) != 4:
            raise ValueError("'rotation_quat' must contain exactly 4 values")
        return self


class Scene(BaseModel):
    """Complete scene with map path, rooms, and objects."""
    
    map: str = DEFAULT_MAP_PATH
    rooms: List[Room]
    objects: List[Object3D]


def create_function_schema() -> Dict[str, Any]:
    """Create the function schema for structured output."""
    return {
    "name": "generate_scene_json",
        "description": "Generate structured 3D scene data",
    "parameters": {
        "type": "object",
        "properties": {
                "map": {"type": "string", "description": "Unreal Engine map path"},
            "rooms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "size": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                                "description": "Dimensions [width, depth, height] in cm"
                        },
                        "position": {
                            "type": "array",
                            "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            "description": "Position [x, y, z] in cm"
                        },
                        "doorways": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                        "type": {"type": "string"},
                                    "position": {
                                        "type": "array",
                                        "items": {"type": "number"},
                                            "minItems": 3,
                                            "maxItems": 3
                                    },
                                    "rotation": {
                                        "type": "array",
                                        "items": {"type": "number"},
                                            "minItems": 3,
                                            "maxItems": 3
                                    }
                                },
                                "required": ["type", "position", "rotation"]
                                }
                        }
                    },
                    "required": ["name", "size", "position"]
                }
            },
            "objects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                            "name": {"type": "string"},
                            "id": {"type": "string"},
                            "type": {"type": "string"},
                        "position": {
                            "type": "array",
                            "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3
                        },
                        "rotation": {
                            "type": "array",
                            "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3
                        },
                        "rotation_quat": {
                            "type": "array",
                            "items": {"type": "number"},
                                "minItems": 4,
                                "maxItems": 4
                        },
                        "scale": {
                            "type": "array",
                            "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3
                        },
                            "intensity": {"type": "number"},
                        "color": {
                            "type": "array",
                            "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3
                        },
                        "mesh_type": {
                            "type": "string",
                                "enum": ["cube", "cylinder", "sphere", "plane"]
                        },
                        "material_type": {
                            "type": "string",
                                "enum": ["wood", "metal", "fabric", "glass", "plastic", "default"]
                        },
                            "parent": {"type": "string"}
                    },
                    "required": ["name", "id", "type"]
                }
            }
        },
        "required": ["rooms", "objects"]
    }
}


def create_system_prompt() -> str:
    """Create the system prompt for the 3D scene generation."""
    return """You are an expert 3D scene generator. Your task is to create a detailed JSON representation of a 3D scene based on user prompts.

CRITICAL RULES:
1. ROOM NAMING: Use the EXACT room name from the user prompt. If they say "loft", create a room named "loft", NOT "living_room".
2. PARENT REFERENCES: Always use exact IDs for parent references, never names.
3. OBJECT CLASSIFICATION: Skylights are OBJECTS, not rooms. They should be in the "objects" array.
4. SPECIAL OBJECTS: rocket_lamp should have NO "mesh_type" field at all - it has a custom creation function.
5. COMPLETE OBJECTS: Include ALL mentioned objects. If "rocket lamp on bedside table" is mentioned, include BOTH objects.

REQUIRED JSON STRUCTURE:
{
  "map_path": "/Game/Maps/GeneratedScene",
  "rooms": [
    {
      "name": "exact_room_name_from_prompt",
      "id": "exact_room_name_from_prompt",
      "size": [width, length, height],
      "position": [x, y, z],
      "rotation": [pitch, yaw, roll]
    }
  ],
  "objects": [
    {
      "name": "object_name",
      "id": "object_name_1",
      "type": "object_type",
      "parent": "exact_room_id_or_object_id",
      "position": [x, y, z],
      "rotation": [pitch, yaw, roll],
      "scale": [x, y, z],
      "mesh_type": "cube|cylinder|sphere|plane", // OMIT entirely for rocket_lamp
      "material_type": "wood|metal|plastic|glass|fabric"
    }
  ]
}

POSITIONING RULES:
- Room: 600x800x350 cm at [0,0,0]
- Furniture positioning: Place furniture AWAY from corners, in the center areas
- Table height: Tables should be at z=37.5 (half of 75cm standard table height)
- Lamp positioning: Lamps on tables should be at [0, 0, 50] relative to table (50cm above table surface)
- Skylight positioning: Skylights should be INSIDE the room at z=175 (middle height), not at ceiling level
- Avoid corners: Don't place furniture at extreme negative positions like [-250, 0, 0]

GOOD POSITIONING EXAMPLES:
- Bedside table: {"position": [100, 200, 37.5]} // Well inside the room, at proper height
- Rocket lamp on table: {"position": [0, 0, 50]} // 50cm above table surface
- Skylight inside room: {"position": [300, 400, 175]} // Inside room at middle height

SPECIAL OBJECT EXAMPLES:
- Bedside table: {"name": "bedside_table", "id": "bedside_table_1", "type": "furniture", "parent": "loft", "position": [100, 200, 37.5], "mesh_type": "cube", "material_type": "wood"}
- Rocket lamp: {"name": "rocket_lamp", "id": "rocket_lamp_1", "type": "rocket_lamp", "parent": "bedside_table_1", "position": [0, 0, 50], "material_type": "metal", "intensity": 3000.0, "color": [1.0, 1.0, 1.0]} // NO mesh_type!

PARENT-CHILD EXAMPLES:
- bedside_table with parent "loft" → "parent": "loft"
- rocket_lamp on bedside_table → "parent": "bedside_table_1"

LIGHTING:
- Add "intensity": 3000.0 and "color": [1.0, 1.0, 1.0] for light objects
- Skylights: type="skylight", mesh_type="plane", material_type="glass"

MATERIALS:
- Furniture: wood
- Lamps: metal (but NO mesh_type for rocket_lamp)
- Skylights: glass
- Walls: concrete"""


def call_language_model(prompt: str) -> Dict[str, Any]:
    """Generate scene data from natural language prompt."""
    try:
        response = CLIENT.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": create_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            functions=[create_function_schema()],
            function_call={"name": "generate_scene_json"}
        )

        function_call = response.choices[0].message.function_call
        if not function_call:
            raise ValueError("No function call in response")

        return json.loads(function_call.arguments)
        
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON response: %s", e)
        raise
    except Exception as e:
        logger.error("Language model error: %s", e)
        raise


def parse_rooms_from_prompt(prompt: str) -> List[Room]:
    """Extract room requirements from prompt."""
    try:
        response = CLIENT.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Analyze the prompt and determine room requirements.
Return JSON with rooms array. Each room needs: name, size [w,d,h], position [x,y,z].

Examples:
- "loft" → [{"name": "loft", "size": [800, 1000, 350], "position": [0, 0, 0]}]
- "apartment" → [{"name": "living_room", "size": [600, 800, 350], "position": [0, 0, 0]}, 
                  {"name": "bedroom", "size": [500, 600, 350], "position": [610, 0, 0]}]"""
                },
                {"role": "user", "content": f"Create rooms for: {prompt}"}
            ],
            response_format={"type": "json_object"}
        )
        
        response_data = json.loads(response.choices[0].message.content)
        rooms = []
        
        for room_data in response_data.get("rooms", []):
            room = Room(
                name=room_data.get("name", "room"),
                size=room_data.get("size", DEFAULT_ROOM_SIZE.copy()),
                position=room_data.get("position", DEFAULT_POSITION.copy()),
                doorways=[]
            )
            rooms.append(room)
        
        logger.info("Parsed %d rooms: %s", len(rooms), [r.name for r in rooms])
        return rooms
        
    except Exception as e:
        logger.warning("Room parsing failed: %s. Using default loft", e)
        return [Room(name="loft", size=[800.0, 1000.0, 350.0], position=[0.0, 0.0, 0.0])]


def create_room_connections(rooms: List[Room]) -> List[Dict[str, Any]]:
    """Create doorway connections between adjacent rooms."""
    connections = []
    
    for i, room1 in enumerate(rooms):
        for room2 in rooms[i+1:]:
            connection = _try_create_connection(room1, room2)
            if connection:
                connections.append(connection)
                logger.info("Connected %s to %s", room1.name, room2.name)
    
    return connections


def _try_create_connection(room1: Room, room2: Room) -> Optional[Dict[str, Any]]:
    """Try to create a connection between two rooms if they're adjacent."""
    pos1 = room1.position or DEFAULT_POSITION
    size1 = room1.size or DEFAULT_ROOM_SIZE
    pos2 = room2.position or DEFAULT_POSITION
    size2 = room2.size or DEFAULT_ROOM_SIZE
    
    # Check horizontal adjacency
    if abs((pos1[0] + size1[0]) - pos2[0]) < 20:
        y_overlap = _calculate_overlap(pos1[1], pos1[1] + size1[1], pos2[1], pos2[1] + size2[1])
        if y_overlap > 100:  # Enough space for door
            door_x = pos1[0] + size1[0]
            door_y = (max(pos1[1], pos2[1]) + min(pos1[1] + size1[1], pos2[1] + size2[1])) / 2
            return _create_doorway_connection(room1, room2, [door_x, door_y, 0.0])
    
    # Check vertical adjacency
    if abs((pos1[1] + size1[1]) - pos2[1]) < 20:
        x_overlap = _calculate_overlap(pos1[0], pos1[0] + size1[0], pos2[0], pos2[0] + size2[0])
        if x_overlap > 100:  # Enough space for door
            door_x = (max(pos1[0], pos2[0]) + min(pos1[0] + size1[0], pos2[0] + size2[0])) / 2
            door_y = pos1[1] + size1[1]
            return _create_doorway_connection(room1, room2, [door_x, door_y, 0.0])
    
    return None


def _calculate_overlap(start1: float, end1: float, start2: float, end2: float) -> float:
    """Calculate overlap between two 1D ranges."""
    return max(0, min(end1, end2) - max(start1, start2))


def _create_doorway_connection(room1: Room, room2: Room, position: List[float]) -> Dict[str, Any]:
    """Create doorway objects for both rooms."""
    doorway1 = {
        "type": "doorway",
        "position": position,
        "rotation": [0.0, 0.0, 0.0],
        "connects_to": room2.name
    }
    
    doorway2 = {
        "type": "doorway", 
        "position": position,
        "rotation": [0.0, 0.0, 0.0],
        "connects_to": room1.name
    }
    
    if room1.doorways is None:
        room1.doorways = []
    if room2.doorways is None:
        room2.doorways = []

    room1.doorways.append(doorway1)
    room2.doorways.append(doorway2)

    return {
        "room1": room1.name,
        "room2": room2.name,
        "door_position": position
    }


def create_rocket_lamp(room_name: str, parent_obj: Optional[str] = None) -> Dict[str, Any]:
    """Create a rocket-shaped lamp with appropriate positioning."""
    position = [0.0, 0.0, 50.0] if parent_obj else [200.0, 250.0, 150.0]
    
    return {
        "name": f"{room_name}_rocket_lamp",
        "id": "rocket_lamp_1",
        "type": "rocket_lamp",
        "position": position,
        "rotation": [0.0, 0.0, 0.0],
        "scale": [0.3, 0.3, 1.0],
        "intensity": 5000,
        "color": [1.0, 0.8, 0.6],
        "mesh_type": "cylinder",
        "material_type": "metal",
        "parent": parent_obj or room_name
    }


def create_lighting_for_room(room_name: str, room_position: List[float], 
                           room_size: List[float], prompt_text: str = "") -> List[Dict[str, Any]]:
    """Create appropriate lighting for a room."""
    lights = []
    
    # Always add directional light
    lights.append({
        "name": f"{room_name}_directional_light",
        "id": f"directional_light_{room_name}",
        "type": "directionallight",
        "position": [
            room_position[0] + room_size[0] / 2,
            room_position[1] + room_size[1] / 2,
            room_position[2] + room_size[2] + 200,
        ],
        "rotation": [-45.0, 45.0, 0.0],
        "intensity": 8.0,
        "color": [1.0, 1.0, 0.9],
        "parent": room_name,
    })
        
    # Add skylight if requested
    if "skylight" in prompt_text.lower():
        lights.append({
            "name": f"{room_name}_skylight",
            "id": f"skylight_{room_name}",
            "type": "skylight",
            "position": [
                room_position[0] + room_size[0] / 2,
                room_position[1] + room_size[1] / 2,
                room_position[2] + room_size[2],
            ],
            "rotation": [0.0, 0.0, 0.0],
            "intensity": 15.0,
            "color": [0.8, 0.9, 1.0],
            "parent": room_name,
        })
    
    return lights


def save_scene_data(scene_data: Dict[str, Any], output_path: str) -> None:
    """Save scene data to JSON file."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(scene_data, f, indent=2)
        logger.info("Scene saved to %s", output_path)
    except IOError as e:
        logger.error("Failed to save scene: %s", e)
        raise


def main() -> None:
    """Main entry point for scene generation."""
    if len(sys.argv) < 2:
        logger.error("Usage: python parse_prompt.py <prompt>")
        sys.exit(1)

    prompt = sys.argv[1]
    logger.info("Processing prompt: %s", prompt)
    
    try:
        # Generate scene data
        scene_data = call_language_model(prompt)
        logger.info("Generated scene with %d rooms and %d objects", 
                   len(scene_data.get('rooms', [])), len(scene_data.get('objects', [])))
        
        # Apply defaults
        scene_data = apply_defaults(scene_data)
        
        # Save output
        save_scene_data(scene_data, "demo/scene.json")
        save_scene_data(scene_data, "demo/scene_updated.json")
        
        # Output for shell script
        print(json.dumps(scene_data, indent=2))
        
    except Exception as e:
        logger.error("Scene generation failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
