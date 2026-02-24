#!/usr/bin/env python3
"""
Product Map Scanner

Discovers from source code:
- Language (JS/Go/Python/other)
- Deploy target (CF Worker, SST, Docker, Lambda, none)
- Published packages (npm, Go modules)
- Dependencies (same-product, cross-product)
- Role classification
- Monorepo detection

Groups repos into products based on domain knowledge + dependency analysis.

Run: python3 aidev/scripts/scan_products.py
From: project root (parent of aidev/)
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# aidev/scripts/ -> aidev/ -> project root
AIDEV_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = AIDEV_DIR.parent
REPOS_DIR = PROJECT_ROOT  # repos are siblings of aidev/
OUTPUT_DIR = AIDEV_DIR / "data"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DROP_REPOS = {"resteep", "stubble", "dashboard-demo-clone"}

# ──────────────────────────────────────────────────────────
# Product groupings (domain knowledge)
# ──────────────────────────────────────────────────────────

PRODUCT_GROUPS = {
    "Upload Platform": {
        "repos": ["upload-service", "w3up", "w3infra"],
        "description": "Core upload API, client SDK, and infrastructure",
    },
    "Gateway & Retrieval": {
        "repos": ["freeway", "gateway-lib", "blob-fetcher", "hoverboard", "w3link"],
        "description": "IPFS gateway, content serving, blob fetching",
    },
    "Content Routing": {
        "repos": ["indexing-service", "content-claims", "storetheindex"],
        "description": "Content indexing, claims, IPNI integration",
    },
    "Storage Node": {
        "repos": ["piri", "piri-signing-service", "storoku"],
        "description": "Decentralized storage node, PDP proofs, provisioning",
    },
    "Filecoin Pipeline": {
        "repos": ["filecoin-services", "w3filecoin-infra", "data-segment", "fr32-sha2-256-trunc254-padded-binary-tree-multihash"],
        "description": "Filecoin deal making, CommP computation, aggregation",
    },
    "UCAN Framework": {
        "repos": ["ucanto", "go-ucanto"],
        "description": "UCAN-based RPC framework (JS + Go)",
    },
    "Shared Libraries": {
        "repos": ["go-libstoracha", "capabilities-go"],
        "description": "Go shared libraries for Storacha ecosystem",
    },
    "Identity & Auth": {
        "repos": ["ucan-kms", "delegator"],
        "description": "Encryption key management, delegation service",
    },
    "Data Structures": {
        "repos": ["pail", "go-pail", "w3clock"],
        "description": "Merkle clock, Pail CRDT, distributed data structures",
    },
    "Egress & Billing": {
        "repos": ["etracker", "egress-consumer"],
        "description": "Egress tracking, usage metering, billing",
    },
    "Developer Tools": {
        "repos": ["console-toolkit", "debugger", "dashboard", "tg-miniapp"],
        "description": "Developer console, debugging tools, dashboard",
    },
    "AI & Integrations": {
        "repos": ["eliza", "ai-integrations"],
        "description": "AI agent integrations",
    },
    "Documentation & Community": {
        "repos": ["docs", "specs", "RFC", "awesome-storacha"],
        "description": "Specifications, documentation, community resources",
    },
    "Infrastructure Libraries": {
        "repos": ["car-block-validator", "ipfs-car", "carstream",
                  "go-block", "go-metadata", "go-piece", "go-storethemeta",
                  "sha256-multihash", "ipni-publisher"],
        "description": "Low-level content-addressing, CAR handling, IPLD utilities",
    },
    "Legacy & Migration": {
        "repos": ["add-to-web3", "w3name", "reads", "dagula", "workers",
                  "bluesky-backup-webapp-server", "guppy", "forgectl",
                  "admin", "agent-store-migration"],
        "description": "Legacy services, migration tools, deprecated repos",
    },
}


def read_file_safe(path, max_bytes=100000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)
    except Exception:
        return ""


def detect_language(repo_path):
    """Detect primary language from repo files."""
    has_go_mod = (repo_path / "go.mod").exists()
    has_pkg_json = (repo_path / "package.json").exists()

    go_files = list(repo_path.glob("**/*.go"))[:5]
    js_files = list(repo_path.glob("**/*.js"))[:5]
    ts_files = list(repo_path.glob("**/*.ts"))[:5]

    if has_go_mod or len(go_files) > 0:
        if has_pkg_json or len(js_files) + len(ts_files) > 0:
            return "JS+Go"
        return "Go"
    if has_pkg_json or len(ts_files) > 0:
        return "TypeScript" if len(ts_files) > len(js_files) else "JavaScript"
    return "Other"


def detect_deploy_target(repo_path):
    """Detect deployment target."""
    if (repo_path / "wrangler.toml").exists() or (repo_path / "wrangler.json").exists():
        return "Cloudflare Worker"
    if (repo_path / "sst.config.ts").exists() or (repo_path / "sst.config.js").exists():
        return "SST (AWS)"
    if (repo_path / "Dockerfile").exists():
        return "Docker"
    if any(repo_path.glob("**/serverless.yml")):
        return "Serverless"
    if any(repo_path.glob("**/*.tf")):
        return "Terraform"
    return None


def detect_monorepo(repo_path):
    """Check if repo is a monorepo."""
    pkg_json_path = repo_path / "package.json"
    if pkg_json_path.exists():
        try:
            pkg = json.loads(read_file_safe(str(pkg_json_path)))
            if "workspaces" in pkg:
                return True
        except Exception:
            pass
    if (repo_path / "pnpm-workspace.yaml").exists():
        return True
    if (repo_path / "lerna.json").exists():
        return True
    return False


def find_published_packages(repo_path):
    """Find npm packages published from this repo."""
    packages = []
    for pkg_json_path in repo_path.rglob("package.json"):
        # Skip node_modules
        if "node_modules" in str(pkg_json_path):
            continue
        try:
            pkg = json.loads(read_file_safe(str(pkg_json_path)))
            name = pkg.get("name", "")
            private = pkg.get("private", False)
            if name and not private and name.startswith("@"):
                packages.append(name)
        except Exception:
            pass

    # Go modules
    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        content = read_file_safe(str(go_mod))
        match = re.search(r'^module\s+(\S+)', content, re.MULTILINE)
        if match:
            packages.append(match.group(1))

    return sorted(set(packages))


def find_dependencies(repo_path):
    """Find all dependency package names."""
    deps = set()

    # JS dependencies
    for pkg_json_path in repo_path.rglob("package.json"):
        if "node_modules" in str(pkg_json_path):
            continue
        try:
            pkg = json.loads(read_file_safe(str(pkg_json_path)))
            for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                for dep_name in pkg.get(dep_type, {}):
                    if dep_name.startswith(("@storacha/", "@web3-storage/", "@ucanto/",
                                           "@ipld/", "@ipfs-shipyard/")):
                        deps.add(dep_name)
        except Exception:
            pass

    # Go dependencies
    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        content = read_file_safe(str(go_mod))
        for match in re.finditer(r'(github\.com/storacha/\S+)', content):
            mod = match.group(1).split('@')[0]
            deps.add(mod)
        for match in re.finditer(r'(github\.com/web3-storage/\S+)', content):
            mod = match.group(1).split('@')[0]
            deps.add(mod)

    return sorted(deps)


def detect_role(name, repo_path, language, deploy_target, packages):
    """Classify repo role."""
    if any(repo_path.glob("**/*.md")) and not any(repo_path.glob("**/*.js")) and not any(repo_path.glob("**/*.go")):
        return "documentation"

    if deploy_target == "Cloudflare Worker":
        return "service (CF Worker)"
    if deploy_target == "SST (AWS)":
        return "infrastructure + service"
    if deploy_target == "Docker":
        return "service (containerized)"

    if packages and all(p.startswith("@") for p in packages):
        return "library"
    if any(repo_path.glob("**/cli*")) or any(repo_path.glob("**/bin/*")):
        return "CLI tool"

    if language == "Go" and (repo_path / "cmd").exists():
        return "service (Go)"
    if language == "Go":
        return "library (Go)"

    return "library"


def get_repo_size_mb(repo_path):
    """Rough repo size in MB (excluding .git and node_modules)."""
    total = 0
    for f in repo_path.rglob("*"):
        if ".git" in f.parts or "node_modules" in f.parts:
            continue
        if f.is_file():
            total += f.stat().st_size
    return round(total / 1024 / 1024, 1)


def get_description(repo_path):
    """Get repo description from package.json or README."""
    pkg_json_path = repo_path / "package.json"
    if pkg_json_path.exists():
        try:
            pkg = json.loads(read_file_safe(str(pkg_json_path)))
            desc = pkg.get("description", "")
            if desc:
                return desc[:200]
        except Exception:
            pass

    readme = repo_path / "README.md"
    if readme.exists():
        content = read_file_safe(str(readme), max_bytes=2000)
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        if lines:
            return lines[0][:200]

    return ""


def main():
    print("=" * 70)
    print("  PRODUCT MAP SCANNER")
    print("  Classifying repos into products with metadata")
    print("=" * 70)

    # Build reverse lookup: repo_name -> product_name
    repo_to_product = {}
    for product_name, info in PRODUCT_GROUPS.items():
        for rname in info["repos"]:
            repo_to_product[rname] = product_name

    # Scan all repos
    all_repos = {}
    repo_dirs = sorted([d for d in REPOS_DIR.iterdir() if d.is_dir() and d.name not in DROP_REPOS])

    for i, rp in enumerate(repo_dirs):
        name = rp.name
        sys.stdout.write(f"\r   [{i+1}/{len(repo_dirs)}] {name:40s}")
        sys.stdout.flush()

        language = detect_language(rp)
        deploy_target = detect_deploy_target(rp)
        is_monorepo = detect_monorepo(rp)
        packages = find_published_packages(rp)
        deps = find_dependencies(rp)
        role = detect_role(name, rp, language, deploy_target, packages)
        description = get_description(rp)

        all_repos[name] = {
            "name": name,
            "language": language,
            "deploy_target": deploy_target,
            "is_monorepo": is_monorepo,
            "publishes": packages,
            "all_deps": deps,
            "role": role,
            "description": description,
        }

    print(f"\n\n   Scanned {len(all_repos)} repos")

    # Build package -> publisher mapping
    pkg_publisher = {}
    for name, info in all_repos.items():
        for pkg in info["publishes"]:
            pkg_publisher[pkg] = name

    # Classify dependencies as same-product or cross-product
    for name, info in all_repos.items():
        product = repo_to_product.get(name)
        same_product_repos = set()
        cross_product_repos = set()

        if product:
            same_product_names = set(PRODUCT_GROUPS[product]["repos"])
        else:
            same_product_names = set()

        for dep_pkg in info["all_deps"]:
            publisher = pkg_publisher.get(dep_pkg)
            if publisher and publisher != name:
                if publisher in same_product_names:
                    same_product_repos.add(publisher)
                else:
                    cross_product_repos.add(publisher)

        info["depends_on_same_product"] = sorted(same_product_repos)
        info["depends_on_cross_product"] = sorted(cross_product_repos)
        del info["all_deps"]  # Remove raw deps from output

    # Build products
    products = []
    categorized_repos = set()

    for product_name, pinfo in PRODUCT_GROUPS.items():
        repos = []
        languages = set()
        for rname in pinfo["repos"]:
            if rname in all_repos:
                repos.append(all_repos[rname])
                languages.add(all_repos[rname]["language"])
                categorized_repos.add(rname)

        if repos:
            products.append({
                "product_name": product_name,
                "description": pinfo["description"],
                "repo_count": len(repos),
                "languages": sorted(languages),
                "repos": repos,
            })

    # Standalone repos (not in any product group)
    standalone = []
    for name, info in sorted(all_repos.items()):
        if name not in categorized_repos:
            standalone.append(info)

    # Downstream consumers (repos that depend on core but aren't core)
    core_products = {"Upload Platform", "UCAN Framework", "Shared Libraries"}
    core_repos = set()
    for p in core_products:
        if p in PRODUCT_GROUPS:
            core_repos.update(PRODUCT_GROUPS[p]["repos"])

    downstream = []
    for name, info in all_repos.items():
        if name not in core_repos:
            cross_deps = info.get("depends_on_cross_product", [])
            core_deps = [d for d in cross_deps if d in core_repos]
            if core_deps:
                product = repo_to_product.get(name, "standalone")
                downstream.append({
                    "repo": name,
                    "product": product,
                    "note": f"depends on core: {', '.join(core_deps)}",
                })

    # Output
    output = {
        "products": products,
        "standalone": standalone,
        "downstream_consumers": downstream,
        "meta": {
            "total_repos": len(all_repos),
            "products": len(products),
            "standalone": len(standalone),
            "downstream_consumers": len(downstream),
        },
    }

    with open(OUTPUT_DIR / "product-map.json", "w") as f:
        json.dump(output, f, indent=2, default=list)

    # Summary
    print("\n" + "=" * 70)
    print(f"  Products: {len(products)}")
    print(f"  Standalone repos: {len(standalone)}")
    print(f"  Downstream consumers: {len(downstream)}")
    print(f"  Total repos: {len(all_repos)}")
    print(f"\n  Output: {OUTPUT_DIR / 'product-map.json'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
