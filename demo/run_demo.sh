#!/bin/bash

# =============================================================================
# UnrealGPT Demo Script - Complete Pipeline
# =============================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEMO_PROMPT="Give me a cosy loft with a skylight and put a rocket-shaped lamp on the bedside table."
SCENE_JSON="scene.json"
UNREAL_PROJECT_PATH=""  # Will be set by user
UNREAL_ENGINE_PATH=""   # Will be set by user

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_ROOT/src"
UNREAL_DIR="$PROJECT_ROOT/unreal"
DEMO_DIR="$PROJECT_ROOT/demo"

echo -e "${BLUE}=== UnrealGPT Demo Pipeline ===${NC}"
echo -e "${BLUE}Target prompt: ${NC}$DEMO_PROMPT"
echo ""

# =============================================================================
# Step 1: Check Dependencies
# =============================================================================

echo -e "${YELLOW}Step 1: Checking dependencies...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

# Check pip packages
echo "Checking Python packages..."
python3 -c "import openai, dotenv, pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Missing required Python packages${NC}"
    echo "Please install: pip install openai python-dotenv pydantic"
    exit 1
fi

# Check OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f "$PROJECT_ROOT/.env" ]; then
        source "$PROJECT_ROOT/.env"
    fi
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${RED}Error: OPENAI_API_KEY not found${NC}"
        echo "Please set your OpenAI API key in .env file or environment variable"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Dependencies check passed${NC}"

# =============================================================================
# Step 2: Generate Scene JSON
# =============================================================================

echo -e "${YELLOW}Step 2: Generating scene JSON from prompt...${NC}"

cd "$SRC_DIR"
python3 parse_prompt.py "$DEMO_PROMPT" > "$DEMO_DIR/$SCENE_JSON"

if [ $? -eq 0 ] && [ -f "$DEMO_DIR/$SCENE_JSON" ]; then
    echo -e "${GREEN}✓ Scene JSON generated successfully${NC}"
    echo "Generated file: $DEMO_DIR/$SCENE_JSON"
else
    echo -e "${RED}Error: Failed to generate scene JSON${NC}"
    exit 1
fi

# =============================================================================
# Step 3: Validate Scene JSON
# =============================================================================

echo -e "${YELLOW}Step 3: Validating scene JSON...${NC}"

# Basic JSON validation
python3 -c "
import json
import sys
try:
    with open('$DEMO_DIR/$SCENE_JSON', 'r') as f:
        data = json.load(f)
    print('✓ Valid JSON structure')
    
    # Check required fields
    if 'rooms' in data and 'objects' in data:
        print(f'✓ Found {len(data[\"rooms\"])} rooms and {len(data[\"objects\"])} objects')
    else:
        print('✗ Missing required fields (rooms/objects)')
        sys.exit(1)
        
except Exception as e:
    print(f'✗ JSON validation failed: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Scene JSON validation passed${NC}"
else
    echo -e "${RED}Error: Scene JSON validation failed${NC}"
    exit 1
fi

# =============================================================================
# Step 4: Setup Unreal Engine Paths
# =============================================================================

echo -e "${YELLOW}Step 4: Setting up Unreal Engine paths...${NC}"

# Try to auto-detect Unreal Engine
if [ -z "$UNREAL_ENGINE_PATH" ]; then
    # Common installation paths
    UNREAL_PATHS=(
        "/Applications/UE_5.6/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
        "/Applications/UE_5.5/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
        "/Applications/UE_5.4/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
        "/Users/Shared/Epic Games/UE_5.6/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
    )
    
    for path in "${UNREAL_PATHS[@]}"; do
        if [ -f "$path" ]; then
            UNREAL_ENGINE_PATH="$path"
            echo "Auto-detected Unreal Engine at: $path"
            break
        fi
    done
fi

# Prompt user if not found
if [ -z "$UNREAL_ENGINE_PATH" ] || [ ! -f "$UNREAL_ENGINE_PATH" ]; then
    echo -e "${YELLOW}Please enter the path to your Unreal Engine executable:${NC}"
    echo "Example: /Applications/UE_5.6/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
    read -p "Unreal Engine path: " UNREAL_ENGINE_PATH
    
    if [ ! -f "$UNREAL_ENGINE_PATH" ]; then
        echo -e "${RED}Error: Unreal Engine executable not found at: $UNREAL_ENGINE_PATH${NC}"
        exit 1
    fi
fi

# Prompt for project path
if [ -z "$UNREAL_PROJECT_PATH" ]; then
    echo -e "${YELLOW}Please enter the path to your Unreal project (.uproject file):${NC}"
    echo "Example: /Users/username/Documents/Unreal Projects/MyProject/MyProject.uproject"
    read -p "Project path: " UNREAL_PROJECT_PATH
    
    if [ ! -f "$UNREAL_PROJECT_PATH" ]; then
        echo -e "${RED}Error: Unreal project file not found at: $UNREAL_PROJECT_PATH${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Unreal Engine paths configured${NC}"

# =============================================================================
# Step 5: Build Scene in Unreal Engine
# =============================================================================

echo -e "${YELLOW}Step 5: Building scene in Unreal Engine...${NC}"

# Prepare the log file path
LOG_FILE="$DEMO_DIR/unreal_build.log"

# Prepare the command with optimized parameters
UNREAL_COMMAND="\"$UNREAL_ENGINE_PATH\" \"$UNREAL_PROJECT_PATH\" -run=pythonscript -script=\"$UNREAL_DIR/BuildScene.py $DEMO_DIR/$SCENE_JSON\" -nullrhi -nosound -stdout -abslog=\"$LOG_FILE\""

echo "Executing Unreal Engine command..."
echo "Command: $UNREAL_COMMAND"
echo "Log file: $LOG_FILE"

# Execute the command
eval $UNREAL_COMMAND

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Scene built successfully in Unreal Engine${NC}"
else
    echo -e "${RED}Error: Failed to build scene in Unreal Engine${NC}"
    echo "Check the Unreal Engine output log for details: $LOG_FILE"
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}Last 20 lines of log:${NC}"
        tail -20 "$LOG_FILE"
    fi
    exit 1
fi

# =============================================================================
# Demo Complete
# =============================================================================

echo ""
echo -e "${GREEN}=== Demo Pipeline Complete! ===${NC}"
echo -e "${GREEN}✓ Prompt processed${NC}"
echo -e "${GREEN}✓ Scene JSON generated${NC}"
echo -e "${GREEN}✓ Scene built in Unreal Engine${NC}"
echo ""
echo -e "${BLUE}Generated files:${NC}"
echo "- Scene JSON: $DEMO_DIR/$SCENE_JSON"
echo "- Unreal Scene: Built in your Unreal project"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Open your Unreal project"
echo "2. Navigate to the generated level"
echo "3. Explore your cosy loft with skylight and rocket lamp!"
echo ""
echo -e "${YELLOW}Tip: You can modify the DEMO_PROMPT variable in this script to test different prompts${NC}"
