#!/usr/bin/env python3
"""
wiki-graph.py — Build a knowledge graph from an llm-wiki knowledge base.

Scans markdown files with YAML frontmatter and [[wikilinks]], producing
a graph.json file and (optionally) a GRAPH_REPORT.md summary.

Usage:
    wiki-graph.py [--wiki-path PATH] [--report] [--force]
    wiki-graph.py --help

Environment:
    LLM_WIKI_PATH   Override default wiki root (~/wiki).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "2.0"

SCANNED_SUBDIRS = ["sources", "entities", "concepts", "analysis"]

FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n",
    re.DOTALL,
)

WIKILINK_RE = re.compile(
    r"\[\[(.+?)\]\]\s*(?:\((inferred|uncertain)\))?",
)

HELP_TEXT = """\
wiki-graph.py — Build a knowledge graph from an llm-wiki knowledge base.

USAGE
    wiki-graph.py [OPTIONS]

OPTIONS
    --wiki-path, -w PATH   Root of the wiki directory.
                            Default: $LLM_WIKI_PATH or ~/wiki
    --report, -r           Also generate GRAPH_REPORT.md.
    --force, -f            Rebuild graph even if nothing changed.
    --help, -h             Show this help message.

DESCRIPTION
    Scans all .md files in sources/, entities/, concepts/, and analysis/
    subdirectories.  Extracts YAML frontmatter metadata and [[wikilinks]]
    to produce:

      <wiki-root>/graph.json              — the knowledge graph.
      <wiki-root>/.cache/graph_hash.json  — file hashes for freshness checks.

    When --report is given a GRAPH_REPORT.md is also written to the wiki root.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wiki_path_default() -> str:
    """Return the wiki root path from env or fallback."""
    return os.environ.get("LLM_WIKI_PATH", os.path.expanduser("~/wiki"))


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Parse a minimal YAML frontmatter block.

    Only understands scalar values and simple lists (inline bracket syntax
    or dash-prefixed items). Returns an empty dict on failure.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    meta: Dict[str, Any] = {}

    # First pass: key: value pairs
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        # Strip surrounding quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        # Inline list: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1]
            meta[key] = [v.strip().strip("\"'") for v in inner.split(",") if v.strip()]
        else:
            meta[key] = val

    # Second pass: collect dash-prefixed list items for known list keys
    if "tags" not in meta:
        tag_lines: List[str] = []
        in_tags = False
        for line in body.splitlines():
            stripped = line.strip()
            # Detect tags: heading or key
            if re.match(r"^tags\s*:", stripped, re.IGNORECASE):
                in_tags = True
                continue
            if in_tags and stripped.startswith("- "):
                tag_lines.append(stripped[2:].strip().strip("\"'"))
            elif in_tags and stripped and not stripped.startswith("-"):
                in_tags = False
        if tag_lines:
            meta["tags"] = tag_lines

    return meta


def parse_wikilinks(text: str) -> List[Tuple[str, str, str]]:
    """Extract (target, confidence, evidence) from [[wikilinks]].

    confidence is one of EXTRACTED, INFERRED, AMBIGUOUS.
    evidence is a short context string around the link.
    """
    results: List[Tuple[str, str, str]] = []
    for m in WIKILINK_RE.finditer(text):
        target = m.group(1).strip()
        annot = m.group(2)
        if annot == "inferred":
            confidence = "INFERRED"
        elif annot == "uncertain":
            confidence = "AMBIGUOUS"
        else:
            confidence = "EXTRACTED"
        # Build evidence: up to 40 chars before and after the match
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 40)
        evidence = text[start:end].replace("\n", " ").strip()
        results.append((target, confidence, evidence))
    return results


def file_sha256(path: str) -> str:
    """Return hex SHA-256 digest of a file, or empty string on error."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def iso_now() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

class WikiGraph:
    """Build a knowledge graph from wiki markdown files."""

    def __init__(self, wiki_root: str):
        self.wiki_root = Path(wiki_root).resolve()
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, str]] = []
        self.adj: Dict[str, Set[str]] = defaultdict(set)
        self.communities: List[Dict[str, Any]] = []
        self.hubs: List[Dict[str, Any]] = []
        self._node_community: Dict[str, int] = {}
        self._edge_set: Set[Tuple[str, str, str]] = set()  # dedup

    # -- scanning -----------------------------------------------------------

    def scan(self) -> None:
        """Walk scanned subdirectories and populate nodes/edges."""
        for subdir in SCANNED_SUBDIRS:
            dir_path = self.wiki_root / subdir
            if not dir_path.is_dir():
                continue
            # Derive page type: sources->source, entities->entity, etc.
            page_type = subdir[:-1] if subdir.endswith("s") else subdir
            for md_file in sorted(dir_path.glob("*.md")):
                self._process_file(md_file, page_type)

        self._compute_degrees()
        self._detect_communities()
        self._compute_hubs()

    def _process_file(self, path: Path, page_type: str) -> None:
        """Parse a single markdown file and extract node + edges."""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        meta = parse_frontmatter(text)
        name = path.stem  # filename without extension

        self.nodes[name] = {
            "type": meta.get("type", page_type),
            "path": str(path.relative_to(self.wiki_root)),
            "created": meta.get("created", ""),
            "updated": meta.get("updated", ""),
            "tags": meta.get("tags", []),
            "in_degree": 0,
            "out_degree": 0,
        }

        # Content starts after frontmatter
        content = FRONTMATTER_RE.sub("", text, count=1)
        for target, confidence, evidence in parse_wikilinks(content):
            edge_key = (name, target, confidence)
            if edge_key in self._edge_set:
                continue
            self._edge_set.add(edge_key)
            self.edges.append({
                "source": name,
                "target": target,
                "confidence": confidence,
                "evidence": evidence,
            })
            self.adj[name].add(target)
            # Register the target node if it doesn't exist yet (it may be
            # an unwritten page or live outside the scanned directories).
            if target not in self.nodes:
                self.nodes[target] = {
                    "type": "unknown",
                    "path": "",
                    "created": "",
                    "updated": "",
                    "tags": [],
                    "in_degree": 0,
                    "out_degree": 0,
                }

    # -- degrees ------------------------------------------------------------

    def _compute_degrees(self) -> None:
        """Calculate in_degree and out_degree for every node."""
        for node in self.nodes:
            self.nodes[node]["in_degree"] = 0
            self.nodes[node]["out_degree"] = 0
        for edge in self.edges:
            src, tgt = edge["source"], edge["target"]
            if src in self.nodes:
                self.nodes[src]["out_degree"] += 1
            if tgt in self.nodes:
                self.nodes[tgt]["in_degree"] += 1

    # -- community detection ------------------------------------------------

    def _detect_communities(self) -> None:
        """Find communities via connected components, splitting large ones."""
        visited: Set[str] = set()
        all_nodes = set(self.nodes.keys())

        # Build undirected adjacency
        undirected: Dict[str, Set[str]] = defaultdict(set)
        for node in all_nodes:
            undirected[node]  # ensure every node has an entry
        for edge in self.edges:
            undirected[edge["source"]].add(edge["target"])
            undirected[edge["target"]].add(edge["source"])

        # BFS to find connected components
        components: List[Set[str]] = []
        for node in sorted(all_nodes):
            if node in visited:
                continue
            comp: Set[str] = set()
            queue = deque([node])
            while queue:
                cur = queue.popleft()
                if cur in visited:
                    continue
                visited.add(cur)
                comp.add(cur)
                for nb in undirected.get(cur, set()):
                    if nb not in visited:
                        queue.append(nb)
            components.append(comp)

        # Split large components using approximate betweenness
        final_components: List[Set[str]] = []
        for comp in components:
            if len(comp) <= 20:
                final_components.append(comp)
            else:
                parts = self._split_component(comp, undirected)
                final_components.extend(parts)

        # Build community data structures
        self.communities = []
        self._node_community = {}
        for idx, members in enumerate(final_components):
            label = self._community_label(members)
            member_list = sorted(members)
            self.communities.append({
                "id": idx,
                "label": label,
                "members": member_list,
            })
            for m in member_list:
                self._node_community[m] = idx

    def _split_component(
        self,
        comp: Set[str],
        undirected: Dict[str, Set[str]],
        max_attempts: int = 5,
    ) -> List[Set[str]]:
        """Recursively split a large component using BFS betweenness."""
        parts: List[Set[str]] = [comp]
        for _ in range(max_attempts):
            largest = max(parts, key=len)
            if len(largest) <= 20:
                break
            bridge = self._find_bridge_node(largest, undirected)
            if bridge is None:
                break
            # Remove bridge and re-run connected components within 'largest'
            visited: Set[str] = set()
            sub_parts: List[Set[str]] = []
            for node in sorted(largest):
                if node == bridge or node in visited:
                    continue
                subset: Set[str] = set()
                queue = deque([node])
                while queue:
                    cur = queue.popleft()
                    if cur in visited or cur == bridge:
                        continue
                    visited.add(cur)
                    subset.add(cur)
                    for nb in undirected.get(cur, set()):
                        if nb in largest and nb not in visited and nb != bridge:
                            queue.append(nb)
                if subset:
                    sub_parts.append(subset)
            # Bridge itself becomes its own tiny community
            sub_parts.append({bridge})
            parts.remove(largest)
            parts.extend(sub_parts)
        return parts

    def _find_bridge_node(
        self,
        comp: Set[str],
        undirected: Dict[str, Set[str]],
    ) -> Optional[str]:
        """Approximate betweenness: find the node whose removal most
        increases BFS distances between sampled node pairs."""
        node_list = list(comp)
        if len(node_list) < 2:
            return None

        # Candidates: nodes with fewest internal connections (likely bridges)
        candidates = sorted(
            node_list,
            key=lambda n: len(undirected.get(n, set()) & comp),
        )[: min(10, len(node_list))]

        best_node: Optional[str] = None
        best_score = -1.0

        for candidate in candidates:
            total_dist = 0
            pairs = 0
            # Sample source-target pairs for efficiency
            sources = node_list[:10]
            targets = node_list[-10:]
            for s in sources:
                for t in targets:
                    if s == candidate or t == candidate:
                        continue
                    dist = self._bfs_distance(
                        s, t, comp, undirected, exclude={candidate}
                    )
                    if dist is not None:
                        total_dist += dist
                        pairs += 1
            if pairs > 0:
                avg = total_dist / pairs
                if avg > best_score:
                    best_score = avg
                    best_node = candidate

        return best_node

    @staticmethod
    def _bfs_distance(
        start: str,
        end: str,
        comp: Set[str],
        undirected: Dict[str, Set[str]],
        exclude: Optional[Set[str]] = None,
    ) -> Optional[int]:
        """BFS shortest path distance, optionally excluding nodes."""
        if start == end:
            return 0
        visited: Set[str] = {start}
        queue: deque[Tuple[str, int]] = deque([(start, 0)])
        while queue:
            cur, dist = queue.popleft()
            for nb in undirected.get(cur, set()):
                if nb not in comp or (exclude and nb in exclude) or nb in visited:
                    continue
                if nb == end:
                    return dist + 1
                visited.add(nb)
                queue.append((nb, dist + 1))
        return None  # unreachable

    def _community_label(self, members: Set[str]) -> str:
        """Suggest a label from the most-connected member."""
        if not members:
            return "empty"
        best = max(
            members,
            key=lambda n: (
                self.nodes[n].get("in_degree", 0)
                + self.nodes[n].get("out_degree", 0)
            ),
        )
        return best

    # -- hubs ---------------------------------------------------------------

    def _compute_hubs(self) -> None:
        """Identify top 10 nodes by total degree."""
        scored = []
        for name, info in self.nodes.items():
            total = info.get("in_degree", 0) + info.get("out_degree", 0)
            scored.append((total, name, info.get("type", "unknown")))
        scored.sort(key=lambda x: (-x[0], x[1]))
        self.hubs = [
            {"name": name, "connections": total, "type": ntype}
            for total, name, ntype in scored[:10]
        ]

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to a JSON-compatible dict."""
        return {
            "version": VERSION,
            "generated": iso_now(),
            "stats": {
                "nodes": len(self.nodes),
                "edges": len(self.edges),
                "communities": len(self.communities),
            },
            "nodes": self.nodes,
            "edges": self.edges,
            "communities": self.communities,
            "hub_nodes": self.hubs,
        }

    # -- node_community map accessor ----------------------------------------

    @property
    def node_community_map(self) -> Dict[str, int]:
        """Mapping from node name to community id."""
        return self._node_community

    # -- hash cache ---------------------------------------------------------

    def compute_hashes(self) -> Dict[str, str]:
        """Return {relative_path: sha256} for all scanned files."""
        hashes: Dict[str, str] = {}
        for subdir in SCANNED_SUBDIRS:
            dir_path = self.wiki_root / subdir
            if not dir_path.is_dir():
                continue
            for md_file in dir_path.glob("*.md"):
                rel = str(md_file.relative_to(self.wiki_root))
                hashes[rel] = file_sha256(str(md_file))
        return hashes

    def hashes_changed(self, old_hashes: Dict[str, str]) -> bool:
        """True if any file hash differs from cached version."""
        current = self.compute_hashes()
        if set(current.keys()) != set(old_hashes.keys()):
            return True
        for path, h in current.items():
            if h != old_hashes.get(path):
                return True
        return False


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_report(graph: WikiGraph, wiki_root: Path) -> str:
    """Build the GRAPH_REPORT.md content string."""
    lines: List[str] = []
    lines.append("# Knowledge Graph Report")
    lines.append("")
    lines.append(f"_Generated: {iso_now()}_")
    lines.append("")

    # -- 1. Overview --------------------------------------------------------
    n_nodes = len(graph.nodes)
    n_edges = len(graph.edges)
    n_communities = len(graph.communities)

    conf_counts: Dict[str, int] = defaultdict(int)
    for e in graph.edges:
        conf_counts[e["confidence"]] += 1

    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **Nodes**: {n_nodes}")
    lines.append(f"- **Edges**: {n_edges}")
    lines.append(f"- **Communities**: {n_communities}")
    lines.append("- **Confidence breakdown**:")
    for conf in ("EXTRACTED", "INFERRED", "AMBIGUOUS"):
        cnt = conf_counts.get(conf, 0)
        pct = (cnt / n_edges * 100) if n_edges else 0
        lines.append(f"  - {conf}: {cnt} ({pct:.1f}%)")
    lines.append("")

    # -- 2. Hub Nodes -------------------------------------------------------
    lines.append("## Hub Nodes")
    lines.append("")
    if graph.hubs:
        for hub in graph.hubs:
            lines.append(
                f"- [[{hub['name']}]] "
                f"({hub['connections']} connections, type: {hub['type']})"
            )
    else:
        lines.append("_No hub nodes found._")
    lines.append("")

    # -- 3. Communities -----------------------------------------------------
    lines.append("## Communities")
    lines.append("")
    if graph.communities:
        for comm in graph.communities:
            members = comm["members"]
            label = comm["label"]
            if len(members) > 3:
                lines.append(f"### {label} ({len(members)} members)")
            else:
                lines.append(f"### Community {comm['id']} ({len(members)} members)")
            lines.append("")
            for m in members:
                ntype = graph.nodes.get(m, {}).get("type", "unknown")
                lines.append(f"- [[{m}]] ({ntype})")
            lines.append("")
    else:
        lines.append("_No communities detected._")
        lines.append("")

    # -- 4. Unexpected Connections ------------------------------------------
    lines.append("## Unexpected Connections")
    lines.append("")
    lines.append("_Cross-community edges (nodes in different communities):_")
    lines.append("")
    cmap = graph.node_community_map
    cross: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    for edge in graph.edges:
        src_comm = cmap.get(edge["source"])
        tgt_comm = cmap.get(edge["target"])
        if (
            src_comm is not None
            and tgt_comm is not None
            and src_comm != tgt_comm
        ):
            pair = tuple(sorted([edge["source"], edge["target"]]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                cross.append(edge)
    # Show up to 10
    for edge in cross[:10]:
        lines.append(
            f"- [[{edge['source']}]] -> [[{edge['target']}]] "
            f"({edge['confidence']})"
        )
    if not cross:
        lines.append("_No cross-community edges found._")
    elif len(cross) > 10:
        lines.append(f"_... and {len(cross) - 10} more._")
    lines.append("")

    # -- 5. Orphan Nodes ----------------------------------------------------
    lines.append("## Orphan Nodes")
    lines.append("")
    orphans = [
        name
        for name, info in graph.nodes.items()
        if info.get("in_degree", 0) == 0 and info.get("out_degree", 0) == 0
    ]
    if orphans:
        for o in sorted(orphans):
            ntype = graph.nodes[o].get("type", "unknown")
            lines.append(f"- [[{o}]] ({ntype})")
    else:
        lines.append("_No orphan nodes._")
    lines.append("")

    # -- 6. Suggested Questions ---------------------------------------------
    lines.append("## Suggested Questions")
    lines.append("")
    questions: List[str] = []

    # From cross-community edges
    for edge in cross[:3]:
        questions.append(
            f"How does [[{edge['source']}]] relate to [[{edge['target']}]]?"
        )

    # From hub connections
    for hub in graph.hubs[:2]:
        hub_name = hub["name"]
        neighbors = graph.adj.get(hub_name, set())
        if neighbors:
            nb = next(iter(sorted(neighbors)))
            questions.append(
                f"What role does [[{hub_name}]] play in "
                f"relation to [[{nb}]]?"
            )

    if not questions:
        questions.append(
            "Consider adding more [[wikilinks]] between pages "
            "to enrich the graph."
        )

    for i, q in enumerate(questions[:5], 1):
        lines.append(f"{i}. {q}")
    lines.append("")

    # -- 7. Stale Pages -----------------------------------------------------
    lines.append("## Stale Pages")
    lines.append("")
    lines.append("_Pages not updated in 30+ days:_")
    lines.append("")
    now = datetime.now(timezone.utc)
    stale: List[Tuple[str, int, str]] = []
    for name, info in graph.nodes.items():
        updated_str = info.get("updated", "")
        if not updated_str:
            continue
        try:
            updated_dt = datetime.fromisoformat(updated_str)
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=timezone.utc)
            age = (now - updated_dt).days
            if age >= 30:
                stale.append((name, age, info.get("type", "unknown")))
        except (ValueError, TypeError):
            continue
    stale.sort(key=lambda x: -x[1])
    if stale:
        for name, age, ntype in stale:
            lines.append(f"- [[{name}]] ({age} days old, type: {ntype})")
    else:
        lines.append("_No stale pages detected._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for wiki-graph.py."""
    parser = argparse.ArgumentParser(
        prog="wiki-graph.py",
        add_help=False,
        description="Build a knowledge graph from an llm-wiki knowledge base.",
    )
    parser.add_argument(
        "--wiki-path", "-w",
        default=wiki_path_default(),
        help="Root of the wiki directory (default: $LLM_WIKI_PATH or ~/wiki)",
    )
    parser.add_argument(
        "--report", "-r",
        action="store_true",
        help="Also generate GRAPH_REPORT.md",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Rebuild even if nothing changed",
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Show help message",
    )

    args = parser.parse_args(argv)

    if args.help:
        print(HELP_TEXT)
        return 0

    wiki_root = Path(args.wiki_path).resolve()

    if not wiki_root.is_dir():
        print(f"Error: wiki root not found: {wiki_root}", file=sys.stderr)
        return 1

    # -- freshness check ----------------------------------------------------
    cache_dir = wiki_root / ".cache"
    cache_file = cache_dir / "graph_hash.json"
    old_hashes: Dict[str, str] = {}

    if not args.force and cache_file.is_file():
        try:
            old_hashes = json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            old_hashes = {}

    if not args.force and old_hashes:
        tmp_graph = WikiGraph(str(wiki_root))
        if not tmp_graph.hashes_changed(old_hashes):
            print("Graph is up to date. Use --force to rebuild.")
            # Still generate report if requested and graph.json exists
            if args.report:
                graph_path = wiki_root / "graph.json"
                if graph_path.is_file():
                    g = WikiGraph(str(wiki_root))
                    try:
                        gdata = json.loads(graph_path.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError) as exc:
                        print(
                            f"Error reading graph.json for report: {exc}",
                            file=sys.stderr,
                        )
                        return 1
                    g.nodes = gdata.get("nodes", {})
                    g.edges = gdata.get("edges", [])
                    g.communities = gdata.get("communities", [])
                    g.hubs = gdata.get("hub_nodes", [])
                    g.adj = defaultdict(set)
                    for e in g.edges:
                        g.adj[e["source"]].add(e["target"])
                    g._node_community = {}
                    for idx, comm in enumerate(g.communities):
                        for m in comm.get("members", []):
                            g._node_community[m] = idx
                    report = generate_report(g, wiki_root)
                    report_path = wiki_root / "GRAPH_REPORT.md"
                    report_path.write_text(report, encoding="utf-8")
                    print(f"Report written: {report_path}")
            return 0

    # -- build graph --------------------------------------------------------
    print(f"Scanning wiki: {wiki_root}")
    graph = WikiGraph(str(wiki_root))
    graph.scan()

    if not graph.nodes:
        print("Warning: no nodes found. Wiki may be empty.", file=sys.stderr)

    graph_data = graph.to_dict()
    graph_path = wiki_root / "graph.json"
    graph_path.write_text(
        json.dumps(graph_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Graph written: {graph_path}")
    print(
        f"  {graph_data['stats']['nodes']} nodes, "
        f"{graph_data['stats']['edges']} edges, "
        f"{graph_data['stats']['communities']} communities"
    )

    # -- hash cache ---------------------------------------------------------
    cache_dir.mkdir(parents=True, exist_ok=True)
    hashes = graph.compute_hashes()
    cache_file.write_text(
        json.dumps(hashes, indent=2, sort_keys=True), encoding="utf-8"
    )

    # -- optional report ----------------------------------------------------
    if args.report:
        report = generate_report(graph, wiki_root)
        report_path = wiki_root / "GRAPH_REPORT.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"Report written: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
