#!/usr/bin/env python3
"""Storacha cross-cutting query tool.

Layer 5 of the knowledge system — answers structural questions that require
joining data across the 3 scanner JSON files (api-surface-map, infrastructure-map,
product-map).

Usage:
    python tools/query.py capability blob/add
    python tools/query.py capability --repo upload-service
    python tools/query.py impact indexing-service
    python tools/query.py impact @storacha/capabilities
    python tools/query.py infra freeway
    python tools/query.py infra --type dynamodb
    python tools/query.py graph upload-service
    python tools/query.py graph --from freeway --to indexing-service
    python tools/query.py product "Upload Platform"
    python tools/query.py repo piri
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Data loading & index building
# ---------------------------------------------------------------------------

def load_json(name):
    with open(BASE / name) as f:
        return json.load(f)


def build_indexes(api, infra, product):
    ix = {}

    # capability -> list of {repo, file, export_name, with}
    ix["cap_defs"] = defaultdict(list)
    for c in api.get("capability_catalog", []):
        ix["cap_defs"][c["can"]].append(c)

    # repo -> capabilities defined
    ix["repo_caps"] = defaultdict(list)
    for c in api.get("capability_catalog", []):
        ix["repo_caps"][c["repo"]].append(c)

    # repo -> capability handlers
    ix["repo_handlers"] = {}
    for repo, data in api.get("per_repo", {}).items():
        ix["repo_handlers"][repo] = data.get("capability_handlers", [])

    # repo -> ucanto connections (outbound service calls)
    ix["repo_connections"] = {}
    for repo, data in api.get("per_repo", {}).items():
        ix["repo_connections"][repo] = data.get("ucanto_connections", [])

    # repo -> entry points
    ix["repo_entries"] = {}
    for repo, data in api.get("per_repo", {}).items():
        ix["repo_entries"][repo] = data.get("entry_points", [])

    # service graph edges
    ix["graph_edges"] = api.get("service_graph", [])

    # graph adjacency: from -> [edges]
    ix["graph_from"] = defaultdict(list)
    ix["graph_to"] = defaultdict(list)
    for e in ix["graph_edges"]:
        ix["graph_from"][e["from"]].append(e)
        ix["graph_to"][e["to"]].append(e)

    # infra summary: category -> {resource -> [repos]}
    ix["infra_summary"] = infra.get("summary", {})

    # infra per_repo: repo -> [resources]
    ix["infra_repo"] = infra.get("per_repo", {})

    # sql schemas
    ix["sql_schemas"] = infra.get("sql_schemas", [])

    # product map: product_name -> product data
    ix["products"] = {}
    for p in product.get("products", []):
        ix["products"][p["product_name"]] = p

    # repo -> product membership
    ix["repo_product"] = {}
    for p in product.get("products", []):
        for r in p.get("repos", []):
            ix["repo_product"][r["name"]] = p["product_name"]

    # all repos from product map (with full info)
    ix["all_repos"] = {}
    for p in product.get("products", []):
        for r in p.get("repos", []):
            ix["all_repos"][r["name"]] = r
    for r in product.get("standalone", []):
        ix["all_repos"][r["name"]] = r

    # downstream consumers
    ix["downstream"] = product.get("downstream_consumers", [])

    # package -> publishing repos
    ix["pkg_publishers"] = defaultdict(list)
    for p in product.get("products", []):
        for r in p.get("repos", []):
            for pkg in r.get("publishes", []):
                ix["pkg_publishers"][pkg].append(r["name"])

    # repo -> deps (same + cross product)
    ix["repo_deps"] = {}
    for p in product.get("products", []):
        for r in p.get("repos", []):
            ix["repo_deps"][r["name"]] = {
                "same": r.get("depends_on_same_product", []),
                "cross": r.get("depends_on_cross_product", []),
            }

    # reverse deps: repo -> repos that depend on it
    ix["repo_rdeps"] = defaultdict(set)
    for p in product.get("products", []):
        for r in p.get("repos", []):
            for dep in r.get("depends_on_same_product", []) + r.get("depends_on_cross_product", []):
                ix["repo_rdeps"][dep].add(r["name"])

    return ix


# ---------------------------------------------------------------------------
# Query implementations
# ---------------------------------------------------------------------------

def query_capability(ix, args):
    """Look up a capability or list capabilities for a repo."""
    if "--repo" in args:
        repo = args[args.index("--repo") + 1]
        return _cap_by_repo(ix, repo)
    else:
        cap_name = args[0]
        return _cap_by_name(ix, cap_name)


def _cap_by_name(ix, cap_name):
    lines = [f"## Capability: `{cap_name}`\n"]

    # Find definitions (exact + prefix match)
    defs = ix["cap_defs"].get(cap_name, [])
    if not defs:
        # Try substring match
        defs = [c for can, cs in ix["cap_defs"].items() for c in cs
                if cap_name in can]
    if not defs:
        return f"No capability matching `{cap_name}` found."

    lines.append("### Defined in\n")
    lines.append("| Repo | Export | With | File |")
    lines.append("|------|--------|------|------|")
    for d in defs:
        w = d.get("with", "")[:40]
        lines.append(f"| {d['repo']} | {d['export_name']} | `{w}` | `{d['file']}` |")

    # Find handlers
    handlers = []
    for repo, hs in ix["repo_handlers"].items():
        for h in hs:
            ref = h.get("capability_ref", "")
            # Match: exact cap name in ref, or export_name in ref
            if cap_name in ref or any(d["export_name"] in ref for d in defs):
                handlers.append({"repo": repo, **h})

    if handlers:
        lines.append("\n### Handled by\n")
        lines.append("| Repo | Pattern | Capability Ref | File |")
        lines.append("|------|---------|---------------|------|")
        for h in handlers:
            lines.append(f"| {h['repo']} | {h['pattern']} | {h['capability_ref']} | `{h['file']}` |")

    # Find service graph edges involving this capability
    edges = [e for e in ix["graph_edges"]
             if cap_name in e.get("capability", "") or
             any(d["export_name"] in e.get("capability", "") for d in defs)]
    if edges:
        lines.append("\n### Service Graph Edges\n")
        lines.append("| From | To | Via | Capability |")
        lines.append("|------|----|----|-----------|")
        for e in edges:
            lines.append(f"| {e['from']} | {e['to']} | {e['via']} | {e.get('capability', '')} |")

    return "\n".join(lines)


def _cap_by_repo(ix, repo):
    lines = [f"## Capabilities for repo: `{repo}`\n"]

    caps = ix["repo_caps"].get(repo, [])
    if caps:
        lines.append("### Defined\n")
        lines.append("| Capability | Export | File |")
        lines.append("|-----------|--------|------|")
        for c in caps:
            lines.append(f"| `{c['can']}` | {c['export_name']} | `{c['file']}` |")

    handlers = ix["repo_handlers"].get(repo, [])
    if handlers:
        lines.append("\n### Handlers\n")
        lines.append("| Pattern | Capability Ref | File |")
        lines.append("|---------|---------------|------|")
        for h in handlers:
            lines.append(f"| {h.get('pattern', '')} | {h.get('capability_ref', '')} | `{h.get('file', '?')}` |")

    conns = ix["repo_connections"].get(repo, [])
    if conns:
        lines.append("\n### Outbound Connections\n")
        lines.append("| To | Via | Capability |")
        lines.append("|----|-----|-----------|")
        for c in conns:
            lines.append(f"| {c.get('to', '')} | {c.get('via', '')} | {c.get('capability', '')} |")

    if not caps and not handlers and not conns:
        lines.append("No capabilities found for this repo.")

    return "\n".join(lines)


def query_impact(ix, args):
    """Show what depends on a repo or package."""
    name = " ".join(args)
    lines = [f"## Impact Analysis: `{name}`\n"]

    # Check if it's a package name (starts with @)
    if name.startswith("@"):
        return _impact_package(ix, name, lines)
    else:
        return _impact_repo(ix, name, lines)


def _impact_package(ix, pkg, lines):
    publishers = ix["pkg_publishers"].get(pkg, [])
    if publishers:
        lines.append(f"**Published by:** {', '.join(publishers)}\n")

    # Find repos that depend on publishers
    dependents = set()
    for pub in publishers:
        dependents.update(ix["repo_rdeps"].get(pub, set()))

    if dependents:
        lines.append("### Repos depending on publishers\n")
        lines.append("| Repo | Role | Language |")
        lines.append("|------|------|----------|")
        for d in sorted(dependents):
            info = ix["all_repos"].get(d, {})
            lines.append(f"| {d} | {info.get('role', '?')} | {info.get('language', '?')} |")

    # Check downstream consumers
    downstream = [d for d in ix["downstream"]
                  if any(p in d.get("note", "") for p in publishers)]
    if downstream:
        lines.append("\n### Downstream consumers at risk\n")
        for d in downstream:
            lines.append(f"- **{d['repo']}** ({d['product']}): {d['note']}")

    if not publishers:
        lines.append(f"Package `{pkg}` not found in product map publishes.")

    return "\n".join(lines)


def _impact_repo(ix, repo, lines):
    info = ix["all_repos"].get(repo, {})
    if info:
        lines.append(f"**Role:** {info.get('role', '?')} | **Language:** {info.get('language', '?')}")
        product = ix["repo_product"].get(repo)
        if product:
            lines.append(f"**Product:** {product}")
        deploy = info.get("deploy_target")
        if deploy:
            lines.append(f"**Deploy:** {deploy}")
        lines.append("")

    # Dependencies
    deps = ix["repo_deps"].get(repo, {})
    same = deps.get("same", [])
    cross = deps.get("cross", [])
    if same or cross:
        lines.append("### Depends on\n")
        if same:
            lines.append(f"**Same product:** {', '.join(same)}")
        if cross:
            lines.append(f"**Cross product:** {', '.join(cross)}")
        lines.append("")

    # Reverse deps
    rdeps = ix["repo_rdeps"].get(repo, set())
    if rdeps:
        lines.append("### Depended on by\n")
        lines.append("| Repo | Role |")
        lines.append("|------|------|")
        for r in sorted(rdeps):
            role = ix["all_repos"].get(r, {}).get("role", "?")
            lines.append(f"| {r} | {role} |")
        lines.append("")

    # Capabilities exposed
    caps = ix["repo_caps"].get(repo, [])
    if caps:
        lines.append(f"### Capabilities ({len(caps)} defined)\n")
        for c in caps:
            lines.append(f"- `{c['can']}` ({c['export_name']})")
        lines.append("")

    # Service graph edges
    out_edges = ix["graph_from"].get(repo, [])
    in_edges = ix["graph_to"].get(repo, [])
    if out_edges or in_edges:
        lines.append(f"### Service graph ({len(out_edges)} out, {len(in_edges)} in)\n")
        if out_edges:
            lines.append("**Calls →**")
            for e in out_edges:
                lines.append(f"- → {e['to']} via {e['via']} ({e.get('capability', '')})")
        if in_edges:
            lines.append("**Called by ←**")
            for e in in_edges:
                lines.append(f"- ← {e['from']} via {e['via']} ({e.get('capability', '')})")
        lines.append("")

    # Infrastructure
    infra = ix["infra_repo"].get(repo, [])
    if infra:
        lines.append(f"### Infrastructure ({len(infra)} resources)\n")
        by_type = defaultdict(list)
        for r in infra:
            by_type[r["type"]].append(r)
        for t, resources in sorted(by_type.items()):
            names = [r.get("name") or r.get("driver") or r.get("table_name") or "?" for r in resources]
            lines.append(f"- **{t}** ({len(resources)}): {', '.join(names[:5])}" +
                        (f" +{len(names)-5} more" if len(names) > 5 else ""))
        lines.append("")

    # Published packages
    publishes = info.get("publishes", [])
    if publishes:
        lines.append("### Publishes\n")
        for p in publishes:
            lines.append(f"- `{p}`")

    if not info:
        lines.append(f"Repo `{repo}` not found in product map.")

    return "\n".join(lines)


def query_infra(ix, args):
    """Show infrastructure for a repo or filter by type."""
    if "--type" in args:
        infra_type = args[args.index("--type") + 1].lower()
        return _infra_by_type(ix, infra_type)
    else:
        repo = args[0]
        return _infra_by_repo(ix, repo)


def _infra_by_repo(ix, repo):
    lines = [f"## Infrastructure: `{repo}`\n"]
    resources = ix["infra_repo"].get(repo, [])
    if not resources:
        return f"No infrastructure found for repo `{repo}`."

    by_type = defaultdict(list)
    for r in resources:
        by_type[r["type"]].append(r)

    for t in sorted(by_type):
        lines.append(f"### {t} ({len(by_type[t])})\n")
        lines.append("| Name | File |")
        lines.append("|------|------|")
        for r in by_type[t]:
            name = r.get("name") or r.get("driver") or r.get("table_name") or "?"
            lines.append(f"| {name} | `{r.get('file', '?')}` |")
        lines.append("")

    # SQL schemas for this repo
    schemas = [s for s in ix["sql_schemas"] if s.get("repo") == repo]
    if schemas:
        lines.append(f"### SQL Tables ({len(schemas)})\n")
        for s in schemas:
            cols = ", ".join(f"{c['name']} {c['type']}" for c in s.get("columns", []))
            lines.append(f"- **{s['table_name']}**: {cols}")
            lines.append(f"  File: `{s.get('file', '?')}`")
        lines.append("")

    return "\n".join(lines)


def _infra_by_type(ix, infra_type):
    """Find all services using a given infra type (dynamodb, s3, redis, etc.)."""
    lines = [f"## Infrastructure type: `{infra_type}`\n"]

    # Search summary categories (case-insensitive substring match)
    found = False
    for cat, resources in ix["infra_summary"].items():
        if infra_type in cat.lower():
            found = True
            lines.append(f"### {cat}\n")
            lines.append("| Resource | Repos |")
            lines.append("|----------|-------|")
            for name, repos in sorted(resources.items()):
                lines.append(f"| {name} | {', '.join(repos)} |")
            lines.append("")

    # Also search per_repo by type field
    type_repos = defaultdict(list)
    for repo, resources in ix["infra_repo"].items():
        for r in resources:
            if infra_type in r.get("type", "").lower():
                type_repos[repo].append(r)

    if type_repos:
        found = True
        lines.append(f"### Per-repo resources matching `{infra_type}`\n")
        lines.append("| Repo | Count | Resources |")
        lines.append("|------|-------|-----------|")
        for repo in sorted(type_repos):
            resources = type_repos[repo]
            names = [r.get("name") or r.get("driver") or "?" for r in resources[:3]]
            suffix = f" +{len(resources)-3} more" if len(resources) > 3 else ""
            lines.append(f"| {repo} | {len(resources)} | {', '.join(names)}{suffix} |")

    if not found:
        lines.append(f"No infrastructure matching `{infra_type}` found.")

    return "\n".join(lines)


def query_graph(ix, args):
    """Show service graph edges for a repo or find paths between two repos."""
    if "--from" in args and "--to" in args:
        src = args[args.index("--from") + 1]
        dst = args[args.index("--to") + 1]
        return _graph_path(ix, src, dst)
    else:
        repo = args[0]
        return _graph_repo(ix, repo)


def _graph_repo(ix, repo):
    lines = [f"## Service Graph: `{repo}`\n"]

    out = ix["graph_from"].get(repo, [])
    inc = ix["graph_to"].get(repo, [])

    if out:
        lines.append(f"### Outbound ({len(out)} edges)\n")
        lines.append("| To | Via | Capability |")
        lines.append("|----|-----|-----------|")
        for e in out:
            lines.append(f"| {e['to']} | {e['via']} | {e.get('capability', '')} |")
        lines.append("")

    if inc:
        lines.append(f"### Inbound ({len(inc)} edges)\n")
        lines.append("| From | Via | Capability |")
        lines.append("|------|----|-----------|")
        for e in inc:
            lines.append(f"| {e['from']} | {e['via']} | {e.get('capability', '')} |")

    if not out and not inc:
        lines.append(f"No service graph edges found for `{repo}`.")

    return "\n".join(lines)


def _graph_path(ix, src, dst):
    """BFS to find paths between two services in the service graph."""
    lines = [f"## Path: `{src}` → `{dst}`\n"]

    # BFS
    visited = {src}
    queue = [(src, [src])]
    paths = []

    while queue and len(paths) < 5:
        node, path = queue.pop(0)
        for edge in ix["graph_from"].get(node, []):
            next_node = edge["to"]
            if next_node == dst:
                paths.append(path + [f"--({edge['via']}: {edge.get('capability', '')})-->", dst])
            elif next_node not in visited:
                visited.add(next_node)
                queue.append((next_node, path + [f"--({edge['via']}: {edge.get('capability', '')})-->", next_node]))

    if paths:
        lines.append(f"Found {len(paths)} path(s):\n")
        for i, p in enumerate(paths, 1):
            lines.append(f"**Path {i}:** {' '.join(p)}")
    else:
        # Check direct edges in both directions
        direct = [e for e in ix["graph_edges"]
                  if (e["from"] == src and e["to"] == dst) or
                     (e["from"] == dst and e["to"] == src)]
        if direct:
            lines.append("Direct edges found:\n")
            for e in direct:
                lines.append(f"- {e['from']} → {e['to']} via {e['via']} ({e.get('capability', '')})")
        else:
            lines.append(f"No path found between `{src}` and `{dst}`.")

    return "\n".join(lines)


def query_product(ix, args):
    """Show product details."""
    name = " ".join(args)

    # Fuzzy match product name
    match = None
    for pname, pdata in ix["products"].items():
        if name.lower() in pname.lower():
            match = pdata
            break

    if not match:
        products = list(ix["products"].keys())
        return f"No product matching `{name}`. Available:\n" + "\n".join(f"- {p}" for p in products)

    lines = [f"## Product: {match['product_name']}\n"]
    lines.append(f"**Repos:** {match['repo_count']} | **Languages:** {', '.join(match.get('languages', []))} | **Size:** {match.get('total_size_mb', '?')} MB\n")

    lines.append("### Repos\n")
    lines.append("| Repo | Role | Language | Deploy | Monorepo |")
    lines.append("|------|------|----------|--------|----------|")
    for r in match.get("repos", []):
        mono = "Yes" if r.get("is_monorepo") else ""
        lines.append(f"| {r['name']} | {r.get('role', '?')} | {r.get('language', '?')} | {r.get('deploy_target') or '-'} | {mono} |")

    # Downstream consumers for this product
    downstream = [d for d in ix["downstream"]
                  if match["product_name"][:20].lower() in d.get("product", "").lower()]
    if downstream:
        lines.append(f"\n### Downstream Consumers ({len(downstream)})\n")
        for d in downstream:
            lines.append(f"- **{d['repo']}** ({d['product']}): {d['note']}")

    return "\n".join(lines)


def query_repo(ix, args):
    """Comprehensive repo overview: product, caps, infra, deps, graph."""
    repo = args[0]
    lines = [f"## Repo: `{repo}`\n"]

    info = ix["all_repos"].get(repo, {})
    if not info:
        return f"Repo `{repo}` not found."

    # Basic info
    lines.append(f"**Role:** {info.get('role', '?')} | **Language:** {info.get('language', '?')} | **Deploy:** {info.get('deploy_target') or 'none'}")
    product = ix["repo_product"].get(repo)
    if product:
        lines.append(f"**Product:** {product}")
    if info.get("description"):
        lines.append(f"**Description:** {info['description']}")
    lines.append("")

    # Dependencies
    deps = ix["repo_deps"].get(repo, {})
    same = deps.get("same", [])
    cross = deps.get("cross", [])
    if same or cross:
        lines.append("### Dependencies\n")
        if same:
            lines.append(f"**Same product:** {', '.join(same)}")
        if cross:
            lines.append(f"**Cross product:** {', '.join(cross)}")
        lines.append("")

    # Reverse deps
    rdeps = ix["repo_rdeps"].get(repo, set())
    if rdeps:
        lines.append(f"### Depended on by ({len(rdeps)} repos)\n")
        lines.append(", ".join(sorted(rdeps)))
        lines.append("")

    # Capabilities
    caps = ix["repo_caps"].get(repo, [])
    handlers = ix["repo_handlers"].get(repo, [])
    if caps or handlers:
        lines.append(f"### Capabilities ({len(caps)} defined, {len(handlers)} handled)\n")
        if caps:
            for c in caps:
                lines.append(f"- `{c['can']}` → `{c['file']}`")
        if handlers:
            lines.append("\n**Handlers:**")
            for h in handlers:
                lines.append(f"- {h.get('capability_ref', h.get('pattern', '?'))} → `{h.get('file', '?')}`")
        lines.append("")

    # Service graph
    out = ix["graph_from"].get(repo, [])
    inc = ix["graph_to"].get(repo, [])
    if out or inc:
        lines.append(f"### Service Graph ({len(out)} out, {len(inc)} in)\n")
        for e in out:
            lines.append(f"- → {e['to']} ({e['via']}: {e.get('capability', '')})")
        for e in inc:
            lines.append(f"- ← {e['from']} ({e['via']}: {e.get('capability', '')})")
        lines.append("")

    # Infrastructure
    infra = ix["infra_repo"].get(repo, [])
    if infra:
        by_type = defaultdict(list)
        for r in infra:
            by_type[r["type"]].append(r)
        lines.append(f"### Infrastructure ({len(infra)} resources)\n")
        for t in sorted(by_type):
            names = [r.get("name") or r.get("driver") or r.get("table_name") or "?" for r in by_type[t]]
            lines.append(f"- **{t}**: {', '.join(names)}")
        lines.append("")

    # SQL schemas
    schemas = [s for s in ix["sql_schemas"] if s.get("repo") == repo]
    if schemas:
        lines.append(f"### SQL Tables ({len(schemas)})\n")
        for s in schemas:
            cols = ", ".join(f"{c['name']} {c['type']}" for c in s.get("columns", []))
            lines.append(f"- **{s['table_name']}**: {cols}")

    # Published packages
    publishes = info.get("publishes", [])
    if publishes:
        lines.append("\n### Publishes\n")
        for p in publishes:
            lines.append(f"- `{p}`")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "capability": ("capability <name> | --repo <repo>", query_capability),
    "impact": ("impact <repo-or-package>", query_impact),
    "infra": ("infra <repo> | --type <type>", query_infra),
    "graph": ("graph <repo> | --from <a> --to <b>", query_graph),
    "product": ("product <name>", query_product),
    "repo": ("repo <name>", query_repo),
}


def usage():
    lines = ["Usage: python tools/query.py <command> [args]\n", "Commands:"]
    for cmd, (desc, _) in COMMANDS.items():
        lines.append(f"  {desc}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(usage())
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}\n{usage()}")
        sys.exit(1)

    if not args:
        print(f"Command `{cmd}` requires arguments.\nUsage: {COMMANDS[cmd][0]}")
        sys.exit(1)

    # Load data
    api = load_json("api-surface-map.json")
    infra = load_json("infrastructure-map.json")
    product = load_json("product-map.json")

    ix = build_indexes(api, infra, product)

    _, handler = COMMANDS[cmd]
    result = handler(ix, args)
    print(result)


if __name__ == "__main__":
    main()
