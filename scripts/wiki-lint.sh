#!/bin/bash
# Comprehensive wiki health check
# Checks: statistics, orphan pages, index coverage, stale pages,
#         inferred/uncertain annotations, potential duplicates

WIKI_PATH="${LLM_WIKI_PATH:-$HOME/wiki}"

if [ ! -d "$WIKI_PATH" ]; then
    echo "Error: Wiki not found at $WIKI_PATH"
    echo "Set LLM_WIKI_PATH or create a wiki with wiki-init"
    exit 1
fi

echo "Wiki Health Check"
echo "================="
echo ""

# ── Statistics ──────────────────────────────────────────
SOURCES=$(find "$WIKI_PATH/sources" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
ENTITIES=$(find "$WIKI_PATH/entities" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
CONCEPTS=$(find "$WIKI_PATH/concepts" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
ANALYSIS=$(find "$WIKI_PATH/analysis" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
TOTAL=$((SOURCES + ENTITIES + CONCEPTS + ANALYSIS))

echo "📊 Statistics"
echo "   Sources: $SOURCES"
echo "   Entities: $ENTITIES"
echo "   Concepts: $CONCEPTS"
echo "   Analysis: $ANALYSIS"
echo "   Total: $TOTAL"
echo ""

# ── Orphan Pages ────────────────────────────────────────
ORPHAN_COUNT=0
echo "🔗 Orphan Pages (no [[links]] pointing to them)..."
for dir in sources entities concepts analysis; do
    for file in "$WIKI_PATH/$dir"/*.md 2>/dev/null; do
        [ -f "$file" ] || continue
        page_name=$(basename "$file" .md)
        # Search for wikilinks to this page (excluding the page itself)
        links=$(grep -rl "\[\[$page_name\]\]" "$WIKI_PATH" 2>/dev/null | grep -v "$file" | wc -l | tr -d ' ')
        if [ "$links" -eq 0 ]; then
            echo "   ⚠️  Orphan: $dir/$page_name.md"
            ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
        fi
    done
done
if [ "$ORPHAN_COUNT" -eq 0 ]; then
    echo "   ✅ No orphan pages found"
fi
echo ""

# ── Index Coverage ──────────────────────────────────────
MISSING_INDEX=0
echo "📋 Index Coverage..."
indexed_pages=$(grep -o '\[\[.*\]\]' "$WIKI_PATH/index.md" 2>/dev/null | sed 's/\[\[\(.*\)\]\]/\1/' | sort -u)
for dir in sources entities concepts analysis; do
    for file in "$WIKI_PATH/$dir"/*.md 2>/dev/null; do
        [ -f "$file" ] || continue
        page_name=$(basename "$file" .md)
        if ! echo "$indexed_pages" | grep -qF "$page_name"; then
            echo "   ⚠️  Not in index: $dir/$page_name.md"
            MISSING_INDEX=$((MISSING_INDEX + 1))
        fi
    done
done
if [ "$MISSING_INDEX" -eq 0 ]; then
    echo "   ✅ All pages indexed"
fi
echo ""

# ── Confidence Annotations ──────────────────────────────
INFERRED_COUNT=0
UNCERTAIN_COUNT=0
echo "🏷️  Confidence Annotations..."
for dir in sources entities concepts analysis; do
    for file in "$WIKI_PATH/$dir"/*.md 2>/dev/null; do
        [ -f "$file" ] || continue
        # Count inferred annotations
        inf=$(grep -c '(inferred)' "$file" 2>/dev/null || true)
        if [ "$inf" -gt 0 ]; then
            page_name=$(basename "$file" .md)
            echo "   🟡 $dir/$page_name.md: $inf inferred relation(s)"
            INFERRED_COUNT=$((INFERRED_COUNT + inf))
        fi
        # Count uncertain annotations
        unc=$(grep -c '(uncertain)' "$file" 2>/dev/null || true)
        if [ "$unc" -gt 0 ]; then
            page_name=$(basename "$file" .md)
            echo "   🔴 $dir/$page_name.md: $unc uncertain relation(s)"
            UNCERTAIN_COUNT=$((UNCERTAIN_COUNT + unc))
        fi
    done
done
echo "   Total: $INFERRED_COUNT inferred, $UNCERTAIN_COUNT uncertain"
if [ "$INFERRED_COUNT" -eq 0 ] && [ "$UNCERTAIN_COUNT" -eq 0 ]; then
    echo "   ℹ️  No confidence annotations found (all relations are implicitly EXTRACTED)"
    echo "   💡 Tip: Add (inferred) or (uncertain) after [[wikilinks]] for LLM-inferred relations"
fi
echo ""

# ── Stale Pages (30+ days since last update) ────────────
STALE_COUNT=0
echo "📅 Stale Pages (not updated in 30+ days)..."
if command -v python3 &>/dev/null; then
    python3 - "$WIKI_PATH" <<'PYEOF'
import os, sys, re
from datetime import datetime, timedelta, timezone

wiki_path = sys.argv[1]
cutoff = datetime.now(timezone.utc) - timedelta(days=30)
fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
count = 0

for subdir in ["sources", "entities", "concepts", "analysis"]:
    dir_path = os.path.join(wiki_path, subdir)
    if not os.path.isdir(dir_path):
        continue
    for fname in sorted(os.listdir(dir_path)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(dir_path, fname)
        try:
            text = open(fpath, encoding="utf-8").read()
        except OSError:
            continue
        m = fm_re.match(text)
        if not m:
            continue
        for line in m.group(1).splitlines():
            line = line.strip().lower()
            if line.startswith("updated:"):
                val = line.split(":", 1)[1].strip()
                try:
                    dt = datetime.fromisoformat(val)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    age = (datetime.now(timezone.utc) - dt).days
                    if age >= 30:
                        name = fname[:-3]
                        print(f"   ⚠️  {subdir}/{name}.md: {age} days old")
                        count += 1
                except (ValueError, TypeError):
                    pass
                break

if count == 0:
    print("   ✅ No stale pages")
PYEOF
else
    echo "   ⏭️  Skipped (python3 required for date parsing)"
fi
echo ""

# ── Potential Duplicates ────────────────────────────────
echo "🔄 Potential Duplicate Pages (similar names)..."
DUPE_COUNT=0
if command -v python3 &>/dev/null; then
    python3 - "$WIKI_PATH" <<'PYEOF'
import os, sys
from difflib import SequenceMatcher

wiki_path = sys.argv[1]
pages = []
for subdir in ["sources", "entities", "concepts", "analysis"]:
    dir_path = os.path.join(wiki_path, subdir)
    if not os.path.isdir(dir_path):
        continue
    for fname in sorted(os.listdir(dir_path)):
        if fname.endswith(".md"):
            name = fname[:-3]
            pages.append((name, subdir))

count = 0
checked = set()
for i, (name_a, dir_a) in enumerate(pages):
    for j, (name_b, dir_b) in enumerate(pages):
        if i >= j:
            continue
        pair = (name_a, name_b)
        if pair in checked:
            continue
        checked.add(pair)
        # Only compare pages in the same category
        if dir_a != dir_b:
            continue
        ratio = SequenceMatcher(None, name_a.lower(), name_b.lower()).ratio()
        if ratio >= 0.8 and name_a.lower() != name_b.lower():
            print(f"   ⚠️  Similar ({ratio:.0%}): {dir_a}/{name_a}.md ↔ {dir_b}/{name_b}.md")
            count += 1

if count == 0:
    print("   ✅ No potential duplicates found")
PYEOF
else
    echo "   ⏭️  Skipped (python3 required for fuzzy matching)"
fi
echo ""

# ── Graph Status ────────────────────────────────────────
echo "🕸️  Knowledge Graph..."
if [ -f "$WIKI_PATH/graph.json" ]; then
    graph_age=$(python3 -c "
import json, os, time
p = '$WIKI_PATH/graph.json'.replace("'", '')
age = time.time() - os.path.getmtime(p)
hours = age / 3600
if hours < 1:
    print(f'{int(age/60)} minutes ago')
elif hours < 24:
    print(f'{hours:.1f} hours ago')
else:
    print(f'{hours/24:.1f} days ago')
" 2>/dev/null)
    nodes=$(python3 -c "import json; d=json.load(open('$WIKI_PATH/graph.json')); print(d.get('stats',{}).get('nodes','?'))" 2>/dev/null)
    edges=$(python3 -c "import json; d=json.load(open('$WIKI_PATH/graph.json')); print(d.get('stats',{}).get('edges','?'))" 2>/dev/null)
    comms=$(python3 -c "import json; d=json.load(open('$WIKI_PATH/graph.json')); print(d.get('stats',{}).get('communities','?'))" 2>/dev/null)
    echo "   graph.json: $nodes nodes, $edges edges, $comms communities"
    echo "   Last built: $graph_age"
    if [ -f "$WIKI_PATH/GRAPH_REPORT.md" ]; then
        echo "   GRAPH_REPORT.md: ✅ exists"
    else
        echo "   GRAPH_REPORT.md: ❌ missing (run: wiki-graph.py --report)"
    fi
else
    echo "   graph.json: ❌ not found (run: wiki-graph.py --report)"
fi
echo ""

# ── Summary ─────────────────────────────────────────────
ISSUES=$((ORPHAN_COUNT + MISSING_INDEX + STALE_COUNT + DUPE_COUNT))
echo "═════════════════"
if [ "$ISSUES" -eq 0 ]; then
    echo "✅ Wiki is healthy! No issues found."
else
    echo "⚠️  Found $ISSUES issue(s) that may need attention"
fi
