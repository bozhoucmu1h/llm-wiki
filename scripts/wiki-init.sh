#!/bin/bash
# Initialize a new LLM wiki

set -e

WIKI_PATH="${1:-$HOME/wiki}"
WIKI_NAME="${2:-My Wiki}"
WIKI_TOPIC="${3:-General knowledge base}"
WIKI_SCOPE="${4:-Anything of interest}"

if [ -d "$WIKI_PATH" ]; then
    echo "Error: $WIKI_PATH already exists"
    exit 1
fi

echo "Creating wiki at $WIKI_PATH..."

# Create directory structure
mkdir -p "$WIKI_PATH"/{raw/{articles,papers,images,other},sources,entities,concepts,analysis,output,.cache}

# Get templates directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$(dirname "$SCRIPT_DIR")/templates"

# Create HERMES.md from template
sed -e "s/{WIKI_NAME}/$WIKI_NAME/g" \
    -e "s/{WIKI_TOPIC}/$WIKI_TOPIC/g" \
    -e "s/{WIKI_SCOPE}/$WIKI_SCOPE/g" \
    -e "s/{CUSTOM_RULES}/None yet/g" \
    "$TEMPLATES_DIR/HERMES.md.tpl" > "$WIKI_PATH/HERMES.md"

# Create index.md from template
sed -e "s/{WIKI_NAME}/$WIKI_NAME/g" \
    -e "s/{DATE}/$(date +%Y-%m-%d)/g" \
    "$TEMPLATES_DIR/index.md.tpl" > "$WIKI_PATH/index.md"

# Create log.md from template with init entry
sed -e "s/{WIKI_NAME}/$WIKI_NAME/g" \
    -e "s/YYYY-MM-DD HH:MM/$(date '+%Y-%m-%d %H:%M')/g" \
    "$TEMPLATES_DIR/log.md.tpl" > "$WIKI_PATH/log.md"

echo "Wiki created successfully!"
echo ""
echo "Directory structure:"
find "$WIKI_PATH" -type d | head -20
echo ""
echo "Next steps:"
echo "1. Open $WIKI_PATH in Obsidian (optional)"
echo "2. Tell Hermes: 'Ingest [source] into the wiki'"
echo "3. Set environment variable: export LLMS_WIKI_PATH=$WIKI_PATH"
