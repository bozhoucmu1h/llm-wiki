#!/usr/bin/env python3
"""
wiki-query.py — Query the llm-wiki knowledge graph.

Provides several query modes for exploring the graph built by wiki-graph.py.
Auto-generates the graph if graph.json is missing or stale (>24h old).

Usage:
    wiki-query.py path <nodeA> <nodeB>
    wiki-query.py neighbors <node>
    wiki-query.py community <node>
    wiki-query.py hubs
    wiki-query.py search <keyword>
    wiki-query.py --help

Environment:
    LLM_WIKI_PATH   Override default wiki root (~/wiki).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "2.0"
MAX_GRAPH_AGE_SECONDS = 24 * 3600  # 24 hours

HELP_TEXT = """\
wiki-query.py — Query the llm-wiki knowledge graph.

USAGE
    wiki-query.py [OPTIONS] <mode> [arguments...]

MODES
    path <nodeA> <nodeB>
        Find the shortest path between two wiki pages. Prints each hop
        with edge confidence.

    neighbors <node>
        List all pages directly connected to a node (inbound + outbound),
        grouped by confidence level.

    community <node>
        Show all members of the same community as the given node.

    hubs
        Show the top 10 hub nodes from the graph.

    search <keyword>
        Find nodes whose name contains the keyword (case-insensitive)
        and show their connections.

OPTIONS
    --wiki-path, -w PATH
        Root of the wiki directory.
        Default: $LLM_WIKI_PATH or ~/wiki
    --no-auto-build
        Do not auto-run wiki-graph.py if graph.json is missing or stale.
    --help, -h
        Show this help message.

EXAMPLES
    wiki-query.py path "Machine Learning" "Neural Networks"
    wiki-query.py neighbors "Python"
    wiki-query.py community "Docker"
    wiki-query.py hubs
    wiki-query.py search "react"

NOTES
    If graph.json does not exist or is older than 24 hours, wiki-graph.py
    is automatically run to rebuild it.  Use --no-auto-build to disable.
"""

# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

class Colors:
    """ANSI color codes, disabled when stdout is not a TTY."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    _enabled: bool = os.isatty(sys.stdout.fileno())

    @classmethod
    def enable(cls) -> None:
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        cls._enabled = False

    @classmethod
    def wrap(cls, text: str, code: str) -> str:
        if cls._enabled:
            return f"{code}{text}{cls.RESET}"
        return text


def color(text: str, code: str) -> str:
    """Apply an ANSI color code if stdout is a TTY."""
    return Colors.wrap(text, code)


# Confidence -> color mapping
CONF_COLORS: Dict[str, str] = {
    "EXTRACTED": Colors.GREEN,
    "INFERRED": Colors.YELLOW,
    "AMBIGUOUS": Colors.RED,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wiki_path_default() -> str:
    """Return the wiki root path from env or fallback."""
    return os.environ.get("LLM_WIKI_PATH", os.path.expanduser("~/wiki"))


def graph_age_seconds(graph_path: Path) -> Optional[float]:
    """Return age of graph.json in seconds, or None if it doesn't exist."""
    if not graph_path.is_file():
        return None
    try:
        stat = graph_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).total_seconds()
    except OSError:
        return None


def ensure_graph(wiki_root: Path, no_auto_build: bool = False) -> bool:
    """Ensure graph.json exists and is fresh. Returns True on success."""
    graph_path = wiki_root / "graph.json"

    if not graph_path.is_file():
        if no_auto_build:
            print(
                "Error: graph.json not found. "
                "Run wiki-graph.py first to build the graph.",
                file=sys.stderr,
            )
            return False
        print("graph.json not found. Building graph...")
        return _run_wiki_graph(wiki_root)

    age = graph_age_seconds(graph_path)
    if age is not None and age > MAX_GRAPH_AGE_SECONDS:
        if no_auto_build:
            print(
                f"Warning: graph.json is {age / 3600:.1f} hours old. "
                "Consider running wiki-graph.py to update it.",
                file=sys.stderr,
            )
            return True
        print(
            f"graph.json is {age / 3600:.1f} hours old. Rebuilding graph..."
        )
        return _run_wiki_graph(wiki_root)

    return True


def _run_wiki_graph(wiki_root: Path) -> bool:
    """Run wiki-graph.py as a subprocess. Returns True on success."""
    # Find wiki-graph.py next to this script
    this_script = Path(__file__).resolve()
    graph_script = this_script.parent / "wiki-graph.py"
    if not graph_script.is_file():
        print(
            f"Error: {graph_script} not found. Cannot auto-build graph.",
            file=sys.stderr,
        )
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(graph_script), "--wiki-path", str(wiki_root)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"wiki-graph.py failed:\n{result.stderr}", file=sys.stderr)
            return False
        if result.stdout.strip():
            print(result.stdout.strip())
        return True
    except subprocess.TimeoutExpired:
        print("Error: wiki-graph.py timed out.", file=sys.stderr)
        return False
    except OSError as exc:
        print(f"Error running wiki-graph.py: {exc}", file=sys.stderr)
        return False


def load_graph(wiki_root: Path) -> Optional[Dict[str, Any]]:
    """Load and return graph.json data, or None on failure."""
    graph_path = wiki_root / "graph.json"
    try:
        return json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error reading graph.json: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Graph query engine
# ---------------------------------------------------------------------------

class GraphQuery:
    """Query engine for the wiki knowledge graph."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.nodes: Dict[str, Dict[str, Any]] = data.get("nodes", {})
        self.edges: List[Dict[str, Any]] = data.get("edges", [])
        self.communities: List[Dict[str, Any]] = data.get("communities", [])
        self.hubs: List[Dict[str, Any]] = data.get("hub_nodes", [])
        # Build adjacency structures
        self._adj_out: Dict[str, Set[str]] = defaultdict(set)
        self._adj_in: Dict[str, Set[str]] = defaultdict(set)
        self._adj_all: Dict[str, Set[str]] = defaultdict(set)
        self._edge_details: Dict[Tuple[str, str], List[Dict[str, Any]]] = (
            defaultdict(list)
        )
        for edge in self.edges:
            src, tgt = edge["source"], edge["target"]
            self._adj_out[src].add(tgt)
            self._adj_in[tgt].add(src)
            self._adj_all[src].add(tgt)
            self._adj_all[tgt].add(src)
            self._edge_details[(src, tgt)].append(edge)
        # Build node -> community mapping
        self._node_community: Dict[str, int] = {}
        for comm in self.communities:
            for m in comm.get("members", []):
                self._node_community[m] = comm["id"]

    # -- query methods ------------------------------------------------------

    def find_path(self, node_a: str, node_b: str) -> Optional[List[Dict]]:
        """BFS shortest path between two nodes.

        Returns a list of step dicts [{node, confidence}, ...] or None.
        """
        if node_a == node_b:
            return [{"node": node_a, "confidence": ""}]

        visited: Set[str] = {node_a}
        # Queue entries: (current_node, path_so_far)
        queue: deque[Tuple[str, List[Dict]]] = deque(
            [(node_a, [{"node": node_a, "confidence": ""}])]
        )
        while queue:
            cur, path = queue.popleft()
            for nb in sorted(self._adj_all.get(cur, set())):
                if nb in visited:
                    continue
                visited.add(nb)
                # Determine edge confidence
                conf = self._edge_confidence(cur, nb)
                new_path = path + [{"node": nb, "confidence": conf}]
                if nb == node_b:
                    return new_path
                queue.append((nb, new_path))
        return None

    def _edge_confidence(self, src: str, tgt: str) -> str:
        """Get the confidence for an edge between src and tgt."""
        details = self._edge_details.get((src, tgt), [])
        if not details:
            details = self._edge_details.get((tgt, src), [])
        if details:
            # Prefer EXTRACTED over INFERRED over AMBIGUOUS
            for pref in ("EXTRACTED", "INFERRED", "AMBIGUOUS"):
                for d in details:
                    if d.get("confidence") == pref:
                        return pref
        return "EXTRACTED"

    def neighbors(
        self, node: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get neighbors grouped by confidence.

        Returns {confidence: [{name, direction}, ...]}.
        """
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        seen: Set[str] = set()

        # Outbound edges
        for edge in self._edge_details.get((node, ""), []):
            pass
        for edge in self.edges:
            if edge["source"] == node and edge["target"] not in seen:
                seen.add(edge["target"])
                grouped[edge["confidence"]].append(
                    {"name": edge["target"], "direction": "outbound"}
                )
            elif edge["target"] == node and edge["source"] not in seen:
                seen.add(edge["source"])
                grouped[edge["confidence"]].append(
                    {"name": edge["source"], "direction": "inbound"}
                )

        # Also catch targets with no matching edge entry
        for tgt in self._adj_out.get(node, set()):
            if tgt not in seen:
                seen.add(tgt)
                grouped["EXTRACTED"].append(
                    {"name": tgt, "direction": "outbound"}
                )
        for src in self._adj_in.get(node, set()):
            if src not in seen:
                seen.add(src)
                grouped["EXTRACTED"].append(
                    {"name": src, "direction": "inbound"}
                )

        return dict(grouped)

    def community_of(self, node: str) -> Optional[Dict[str, Any]]:
        """Return the community dict for a node, or None."""
        cid = self._node_community.get(node)
        if cid is None:
            return None
        for comm in self.communities:
            if comm["id"] == cid:
                return comm
        return None

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """Find nodes whose name contains the keyword (case-insensitive).

        Returns list of {name, type, connections}.
        """
        keyword_lower = keyword.lower()
        results = []
        for name, info in self.nodes.items():
            if keyword_lower in name.lower():
                connections = (
                    info.get("in_degree", 0) + info.get("out_degree", 0)
                )
                results.append(
                    {
                        "name": name,
                        "type": info.get("type", "unknown"),
                        "connections": connections,
                    }
                )
        results.sort(key=lambda x: (-x["connections"], x["name"]))
        return results


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def fmt_node(name: str, ntype: str = "") -> str:
    """Format a node name with type hint."""
    if ntype:
        return f"{color(name, Colors.CYAN)} ({color(ntype, Colors.DIM)})"
    return color(name, Colors.CYAN)


def fmt_conf(conf: str) -> str:
    """Format a confidence level with color."""
    c = CONF_COLORS.get(conf, Colors.WHITE)
    return color(conf, c)


def fmt_bold(text: str) -> str:
    return color(text, Colors.BOLD)


def fmt_dim(text: str) -> str:
    return color(text, Colors.DIM)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_path(gq: GraphQuery, node_a: str, node_b: str) -> int:
    """Handle the 'path' query mode."""
    # Check nodes exist
    missing = []
    if node_a not in gq.nodes:
        missing.append(node_a)
    if node_b not in gq.nodes:
        missing.append(node_b)
    if missing:
        print(
            f"Error: node(s) not found: {', '.join(missing)}", file=sys.stderr
        )
        print("Use 'search' to find matching node names.", file=sys.stderr)
        return 1

    path = gq.find_path(node_a, node_b)
    if path is None:
        print(f"No path found between {node_a} and {node_b}.")
        print("These nodes may be in disconnected communities.")
        return 0

    print(f"Shortest path: {len(path) - 1} hop(s)")
    print()
    for i, step in enumerate(path):
        if i == 0:
            print(f"  {fmt_node(step['node'])}")
        else:
            conf = step["confidence"]
            print(f"  {fmt_dim('->')} [{fmt_conf(conf)}] {fmt_node(step['node'])}")
    return 0


def cmd_neighbors(gq: GraphQuery, node: str) -> int:
    """Handle the 'neighbors' query mode."""
    if node not in gq.nodes:
        print(f"Error: node '{node}' not found.", file=sys.stderr)
        print("Use 'search' to find matching node names.", file=sys.stderr)
        return 1

    info = gq.nodes[node]
    grouped = gq.neighbors(node)
    total = sum(len(v) for v in grouped.values())

    print(f"Neighbors of {fmt_node(node, info.get('type', ''))}: {total}")
    print()

    if not grouped:
        print("  No connections found.")
        return 0

    for conf in ("EXTRACTED", "INFERRED", "AMBIGUOUS"):
        items = grouped.get(conf, [])
        if not items:
            continue
        print(f"  {fmt_conf(conf)} ({len(items)}):")
        for item in items:
            ntype = gq.nodes.get(item["name"], {}).get("type", "")
            arrow = "->" if item["direction"] == "outbound" else "<-"
            print(f"    {fmt_dim(arrow)} {fmt_node(item['name'], ntype)}")
        print()

    return 0


def cmd_community(gq: GraphQuery, node: str) -> int:
    """Handle the 'community' query mode."""
    if node not in gq.nodes:
        print(f"Error: node '{node}' not found.", file=sys.stderr)
        print("Use 'search' to find matching node names.", file=sys.stderr)
        return 1

    comm = gq.community_of(node)
    if comm is None:
        print(f"Node '{node}' is not in any community (orphan node).")
        return 0

    label = comm.get("label", f"Community {comm['id']}")
    members = comm.get("members", [])
    print(f"Community: {fmt_bold(label)} ({len(members)} members)")
    print()
    for m in sorted(members):
        ntype = gq.nodes.get(m, {}).get("type", "unknown")
        marker = " *" if m == node else ""
        print(f"  {fmt_node(m, ntype)}{marker}")
    if node in [m for m in members]:
        print()
        print("  * = queried node")
    return 0


def cmd_hubs(gq: GraphQuery) -> int:
    """Handle the 'hubs' query mode."""
    if not gq.hubs:
        print("No hub nodes found (graph may be empty).")
        return 0

    print(f"Top {len(gq.hubs)} hub nodes:")
    print()
    for i, hub in enumerate(gq.hubs, 1):
        name = hub.get("name", "unknown")
        conns = hub.get("connections", 0)
        ntype = hub.get("type", "unknown")
        print(
            f"  {i:2}. {fmt_node(name, ntype)} "
            f"{fmt_dim(f'({conns} connections)')}"
        )
    return 0


def cmd_search(gq: GraphQuery, keyword: str) -> int:
    """Handle the 'search' query mode."""
    results = gq.search(keyword)
    if not results:
        print(f"No nodes matching '{keyword}'.")
        return 0

    print(f"Nodes matching '{fmt_bold(keyword)}': {len(results)}")
    print()
    for r in results:
        name = r["name"]
        ntype = r["type"]
        conns = r["connections"]
        print(
            f"  {fmt_node(name, ntype)} "
            f"{fmt_dim(f'({conns} connections)')}"
        )
        # Show direct neighbors
        nbrs = sorted(gq._adj_all.get(name, set()))[:5]
        if nbrs:
            print(f"    {fmt_dim('links to:')} "
                  + f"{fmt_dim(', ')}".join(
                      gq.nodes.get(n, {}).get("type", "?") + "/" + n
                      for n in nbrs
                  ))
            remaining = len(gq._adj_all.get(name, set())) - len(nbrs)
            if remaining > 0:
                print(f"    {fmt_dim(f'... and {remaining} more')}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for wiki-query.py."""
    parser = argparse.ArgumentParser(
        prog="wiki-query.py",
        add_help=False,
        description="Query the llm-wiki knowledge graph.",
    )
    parser.add_argument(
        "--wiki-path", "-w",
        default=wiki_path_default(),
        help="Root of the wiki directory (default: $LLM_WIKI_PATH or ~/wiki)",
    )
    parser.add_argument(
        "--no-auto-build",
        action="store_true",
        help="Do not auto-run wiki-graph.py if graph.json is missing/stale",
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Show help message",
    )
    # Accept remaining args as: mode [args...]
    parser.add_argument("mode", nargs="?", default=None, help="Query mode")
    parser.add_argument("args", nargs="*", help="Mode arguments")

    args = parser.parse_args(argv)

    if args.help:
        print(HELP_TEXT)
        return 0

    if args.mode is None:
        print("Error: no query mode specified.", file=sys.stderr)
        print("Run with --help for usage information.", file=sys.stderr)
        return 1

    mode = args.mode.lower()
    mode_args = args.args

    wiki_root = Path(args.wiki_path).resolve()

    # -- validate mode arguments --------------------------------------------
    if mode == "path" and len(mode_args) != 2:
        print(
            "Error: 'path' mode requires exactly 2 arguments: "
            "<nodeA> <nodeB>",
            file=sys.stderr,
        )
        return 1
    elif mode == "neighbors" and len(mode_args) != 1:
        print(
            "Error: 'neighbors' mode requires exactly 1 argument: <node>",
            file=sys.stderr,
        )
        return 1
    elif mode == "community" and len(mode_args) != 1:
        print(
            "Error: 'community' mode requires exactly 1 argument: <node>",
            file=sys.stderr,
        )
        return 1
    elif mode == "hubs" and mode_args:
        print(
            "Error: 'hubs' mode takes no arguments.",
            file=sys.stderr,
        )
        return 1
    elif mode == "search" and len(mode_args) != 1:
        print(
            "Error: 'search' mode requires exactly 1 argument: <keyword>",
            file=sys.stderr,
        )
        return 1
    elif mode not in ("path", "neighbors", "community", "hubs", "search"):
        print(f"Error: unknown mode '{mode}'.", file=sys.stderr)
        print(
            "Valid modes: path, neighbors, community, hubs, search",
            file=sys.stderr,
        )
        return 1

    # -- ensure graph -------------------------------------------------------
    if not wiki_root.is_dir():
        print(f"Error: wiki root not found: {wiki_root}", file=sys.stderr)
        return 1

    if not ensure_graph(wiki_root, no_auto_build=args.no_auto_build):
        return 1

    # -- load graph ---------------------------------------------------------
    data = load_graph(wiki_root)
    if data is None:
        return 1

    gq = GraphQuery(data)

    # -- dispatch -----------------------------------------------------------
    if mode == "path":
        return cmd_path(gq, mode_args[0], mode_args[1])
    elif mode == "neighbors":
        return cmd_neighbors(gq, mode_args[0])
    elif mode == "community":
        return cmd_community(gq, mode_args[0])
    elif mode == "hubs":
        return cmd_hubs(gq)
    elif mode == "search":
        return cmd_search(gq, mode_args[0])

    return 1  # unreachable


if __name__ == "__main__":
    sys.exit(main())
