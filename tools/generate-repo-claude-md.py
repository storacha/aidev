#!/usr/bin/env python3
"""
Generate minimal CLAUDE.md files for repos that don't have one.

Scans repos/storacha/ for directories, identifies which lack a CLAUDE.md,
and generates one using metadata from package.json/go.mod, README.md,
CI workflows, and data/product-map.json.

Usage:
    python tools/generate-repo-claude-md.py             # Generate for all missing
    python tools/generate-repo-claude-md.py --repo NAME # Generate for specific repo
    python tools/generate-repo-claude-md.py --dry-run   # Print without writing
    python tools/generate-repo-claude-md.py --list-missing  # List repos that need CLAUDE.md
"""

import argparse
import json
import os
import re
import sys

# --- Paths ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
REPOS_DIR = os.path.join(ROOT_DIR, "repos", "storacha")
PRODUCT_MAP_PATH = os.path.join(ROOT_DIR, "data", "product-map.json")


# --- Product map loading ---

def load_product_map():
    """Load and index the product map by repo name."""
    if not os.path.exists(PRODUCT_MAP_PATH):
        print(f"Warning: {PRODUCT_MAP_PATH} not found, skipping product metadata")
        return {}

    with open(PRODUCT_MAP_PATH, "r") as f:
        data = json.load(f)

    index = {}

    # Index repos from products
    for product in data.get("products", []):
        product_name = product["product_name"]
        for repo in product.get("repos", []):
            index[repo["name"]] = {
                "product": product_name,
                "product_description": product.get("description", ""),
                "language": repo.get("language", ""),
                "deploy_target": repo.get("deploy_target"),
                "is_monorepo": repo.get("is_monorepo", False),
                "publishes": repo.get("publishes", []),
                "role": repo.get("role", ""),
                "description": repo.get("description", ""),
                "depends_on_same_product": repo.get("depends_on_same_product", []),
                "depends_on_cross_product": repo.get("depends_on_cross_product", []),
            }

    # Index standalone repos
    for repo in data.get("standalone", []):
        index[repo["name"]] = {
            "product": "Standalone",
            "product_description": "",
            "language": repo.get("language", ""),
            "deploy_target": repo.get("deploy_target"),
            "is_monorepo": repo.get("is_monorepo", False),
            "publishes": repo.get("publishes", []),
            "role": repo.get("role", ""),
            "description": repo.get("description", ""),
            "depends_on_same_product": repo.get("depends_on_same_product", []),
            "depends_on_cross_product": repo.get("depends_on_cross_product", []),
        }

    return index


# --- Repo metadata extraction ---

def read_file_safe(path, max_bytes=50000):
    """Read a file, returning empty string if it doesn't exist."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes)
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return ""


def detect_language(repo_dir):
    """Detect primary language from project files."""
    has_package_json = os.path.exists(os.path.join(repo_dir, "package.json"))
    has_go_mod = os.path.exists(os.path.join(repo_dir, "go.mod"))
    has_tsconfig = os.path.exists(os.path.join(repo_dir, "tsconfig.json"))

    if has_go_mod and has_package_json:
        return "JS+Go"
    elif has_go_mod:
        return "Go"
    elif has_tsconfig:
        return "TypeScript"
    elif has_package_json:
        return "JavaScript"
    else:
        return "Unknown"


def parse_package_json(repo_dir):
    """Parse package.json for scripts, description, name, exports."""
    path = os.path.join(repo_dir, "package.json")
    content = read_file_safe(path)
    if not content:
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    return {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "scripts": data.get("scripts", {}),
        "main": data.get("main", ""),
        "exports": data.get("exports", {}),
        "bin": data.get("bin", {}),
        "dependencies": list(data.get("dependencies", {}).keys()),
        "devDependencies": list(data.get("devDependencies", {}).keys()),
        "workspaces": data.get("workspaces", []),
    }


def parse_go_mod(repo_dir):
    """Parse go.mod for module name and key dependencies."""
    path = os.path.join(repo_dir, "go.mod")
    content = read_file_safe(path)
    if not content:
        return None

    module_name = ""
    go_version = ""
    deps = []

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("module "):
            module_name = line[len("module "):].strip()
        elif line.startswith("go "):
            go_version = line[len("go "):].strip()
        elif line.startswith("github.com/storacha/") or line.startswith("github.com/ipfs/") or line.startswith("github.com/ipld/"):
            dep = line.split()[0] if line.split() else ""
            if dep:
                deps.append(dep)

    return {
        "module": module_name,
        "go_version": go_version,
        "storacha_deps": deps,
    }


def parse_makefile(repo_dir):
    """Parse Makefile for build/test/lint targets."""
    path = os.path.join(repo_dir, "Makefile")
    content = read_file_safe(path)
    if not content:
        return None

    targets = {}
    current_target = None
    for line in content.split("\n"):
        # Match target lines like "build:" or ".PHONY: build"
        target_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*):', line)
        if target_match and not line.startswith(".PHONY"):
            current_target = target_match.group(1)
            targets[current_target] = []
        elif current_target and line.startswith("\t"):
            targets[current_target].append(line.strip())

    return targets


def extract_readme_overview(repo_dir, repo_name):
    """Extract a 2-3 sentence overview from README.md."""
    path = os.path.join(repo_dir, "README.md")
    content = read_file_safe(path, max_bytes=10000)
    if not content:
        return ""

    lines = content.split("\n")
    sentences = []

    # Skip badges, HTML tags, empty lines, and headings at the start
    collecting = False
    for line in lines:
        stripped = line.strip()

        # Skip empty lines, badges, HTML, and headings until we find prose
        if not collecting:
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("[![") or stripped.startswith("!["):
                continue
            if stripped.startswith("<") and not stripped.startswith("<a"):
                continue
            if stripped.startswith(">"):
                # Blockquote — might be a description, use it
                text = stripped.lstrip("> ").strip()
                if text and len(text) > 10:
                    sentences.append(text)
                    collecting = True
                continue
            # Found a prose line
            collecting = True

        if collecting:
            if not stripped:
                # End of paragraph
                if sentences:
                    break
                continue
            if stripped.startswith("#"):
                # Hit a new heading, stop
                if sentences:
                    break
                continue
            if stripped.startswith("```"):
                if sentences:
                    break
                continue
            if stripped.startswith("[![") or stripped.startswith("!["):
                continue
            if stripped.startswith("<") and ">" in stripped and not stripped.startswith("<a"):
                continue
            sentences.append(stripped)

    if not sentences:
        return ""

    # Join and truncate to ~2-3 sentences
    text = " ".join(sentences)
    # Try to cut at sentence boundaries
    parts = re.split(r'(?<=[.!?])\s+', text)
    result = ""
    for part in parts[:3]:
        if len(result) + len(part) > 300:
            break
        result = (result + " " + part).strip() if result else part

    return result if result else text[:300]


def extract_ci_commands(repo_dir):
    """Extract build/test/lint commands from CI workflow files."""
    workflows_dir = os.path.join(repo_dir, ".github", "workflows")
    if not os.path.isdir(workflows_dir):
        return {}

    commands = {"build": [], "test": [], "lint": []}

    try:
        for fname in os.listdir(workflows_dir):
            if not fname.endswith((".yml", ".yaml")):
                continue
            content = read_file_safe(os.path.join(workflows_dir, fname))
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("run:"):
                    continue
                cmd = stripped[len("run:"):].strip().strip('"').strip("'")
                cmd_lower = cmd.lower()
                if "test" in cmd_lower or "go test" in cmd_lower:
                    commands["test"].append(cmd)
                elif "build" in cmd_lower or "go build" in cmd_lower:
                    commands["build"].append(cmd)
                elif "lint" in cmd_lower or "eslint" in cmd_lower or "golangci-lint" in cmd_lower:
                    commands["lint"].append(cmd)
    except OSError:
        pass

    return commands


# --- Build/test/lint command resolution ---

def resolve_commands(language, pkg_json, go_mod, makefile_targets, ci_commands):
    """Determine the best build, test, and lint commands for the repo."""
    build_cmd = ""
    test_cmd = ""
    lint_cmd = ""

    if language in ("JavaScript", "TypeScript", "JS+Go"):
        if pkg_json:
            scripts = pkg_json.get("scripts", {})

            # Detect package manager
            pkg_manager = "npm"
            # (We just default to npm; could check for lockfiles but keep it simple)

            if "build" in scripts:
                build_cmd = f"{pkg_manager} run build"
            if "test" in scripts:
                test_cmd = f"{pkg_manager} test"
            if "lint" in scripts:
                lint_cmd = f"{pkg_manager} run lint"
            elif "check" in scripts:
                lint_cmd = f"{pkg_manager} run check"

    if language in ("Go", "JS+Go"):
        if makefile_targets:
            if "build" in makefile_targets:
                build_cmd = build_cmd or "make build"
            if "test" in makefile_targets:
                test_cmd = test_cmd or "make test"
            if "lint" in makefile_targets:
                lint_cmd = lint_cmd or "make lint"

        # Fallback to standard Go commands
        if not test_cmd:
            test_cmd = "go test ./..."
        if not build_cmd and go_mod:
            build_cmd = "go build ./..."

    # Try CI commands as fallback
    if not test_cmd and ci_commands.get("test"):
        test_cmd = ci_commands["test"][0]
    if not build_cmd and ci_commands.get("build"):
        build_cmd = ci_commands["build"][0]
    if not lint_cmd and ci_commands.get("lint"):
        lint_cmd = ci_commands["lint"][0]

    return build_cmd, test_cmd, lint_cmd


# --- Key abstractions extraction ---

def extract_key_abstractions(repo_dir, language, pkg_json, go_mod):
    """Extract top exports/types/packages from manifest files."""
    abstractions = []

    if pkg_json:
        # Published package name
        name = pkg_json.get("name", "")
        if name:
            abstractions.append(f"Package: `{name}`")

        # Bin commands
        bin_cmds = pkg_json.get("bin", {})
        if isinstance(bin_cmds, dict) and bin_cmds:
            cmds = ", ".join(f"`{k}`" for k in bin_cmds.keys())
            abstractions.append(f"CLI commands: {cmds}")

        # Workspaces (monorepo)
        workspaces = pkg_json.get("workspaces", [])
        if workspaces:
            if isinstance(workspaces, list) and len(workspaces) <= 5:
                ws = ", ".join(f"`{w}`" for w in workspaces)
                abstractions.append(f"Workspaces: {ws}")
            elif isinstance(workspaces, list):
                abstractions.append(f"Monorepo with {len(workspaces)} workspaces")

    if go_mod:
        module = go_mod.get("module", "")
        if module:
            abstractions.append(f"Module: `{module}`")

        # List top-level Go packages
        try:
            entries = os.listdir(repo_dir)
            go_packages = []
            for entry in sorted(entries):
                entry_path = os.path.join(repo_dir, entry)
                if os.path.isdir(entry_path) and not entry.startswith("."):
                    # Check if it has .go files
                    try:
                        has_go = any(f.endswith(".go") for f in os.listdir(entry_path))
                        if has_go:
                            go_packages.append(entry)
                    except OSError:
                        pass
            if go_packages and len(go_packages) <= 10:
                pkgs = ", ".join(f"`{p}/`" for p in go_packages)
                abstractions.append(f"Packages: {pkgs}")
            elif go_packages:
                abstractions.append(f"{len(go_packages)} Go packages")
        except OSError:
            pass

    return abstractions


# --- CLAUDE.md generation ---

def generate_claude_md(repo_name, repo_dir, product_info):
    """Generate CLAUDE.md content for a repo."""

    # Gather all metadata
    language = detect_language(repo_dir)
    pkg_json = parse_package_json(repo_dir)
    go_mod = parse_go_mod(repo_dir)
    makefile_targets = parse_makefile(repo_dir)
    ci_commands = extract_ci_commands(repo_dir)

    # Use product map info to enrich/override
    pm_language = ""
    pm_role = ""
    pm_product = ""
    pm_description = ""
    pm_publishes = []
    pm_deploy_target = None

    if product_info:
        pm_language = product_info.get("language", "")
        pm_role = product_info.get("role", "")
        pm_product = product_info.get("product", "")
        pm_description = product_info.get("description", "")
        pm_publishes = product_info.get("publishes", [])
        pm_deploy_target = product_info.get("deploy_target")

    # Prefer detected language, fall back to product map
    if language == "Unknown" and pm_language:
        language = pm_language

    # Get overview from README
    readme_overview = extract_readme_overview(repo_dir, repo_name)

    # If README overview is poor, try product map description
    if not readme_overview or len(readme_overview) < 15:
        # Clean up product map description (some have markdown/HTML junk)
        desc = pm_description.strip()
        if desc and not desc.startswith("<") and not desc.startswith("[![") and len(desc) > 10:
            readme_overview = desc

    if not readme_overview:
        readme_overview = f"{repo_name} repository."

    # Resolve commands
    build_cmd, test_cmd, lint_cmd = resolve_commands(
        language, pkg_json, go_mod, makefile_targets, ci_commands
    )

    # Build Quick Reference line
    quick_ref_parts = []
    quick_ref_parts.append(f"**Language:** {language}")
    if build_cmd:
        quick_ref_parts.append(f"**Build:** `{build_cmd}`")
    if test_cmd:
        quick_ref_parts.append(f"**Test:** `{test_cmd}`")
    if lint_cmd:
        quick_ref_parts.append(f"**Lint:** `{lint_cmd}`")
    quick_ref_line = " | ".join(quick_ref_parts)

    # Extract key abstractions
    abstractions = extract_key_abstractions(repo_dir, language, pkg_json, go_mod)

    # Add publishes from product map
    if pm_publishes and not any("Package:" in a for a in abstractions):
        if len(pm_publishes) <= 5:
            pkgs = ", ".join(f"`{p}`" for p in pm_publishes)
            abstractions.append(f"Publishes: {pkgs}")
        else:
            abstractions.append(f"Publishes {len(pm_publishes)} packages")

    # Add role/product context
    context_parts = []
    if pm_product and pm_product != "Standalone":
        context_parts.append(f"**Product group:** {pm_product}")
    if pm_role:
        context_parts.append(f"**Role:** {pm_role}")
    if pm_deploy_target:
        context_parts.append(f"**Deploy target:** {pm_deploy_target}")

    # --- Assemble the CLAUDE.md ---
    lines = []
    lines.append(f"# {repo_name}")
    lines.append("")
    lines.append("## Overview")
    lines.append(readme_overview)
    lines.append("")

    lines.append("## Quick Reference")
    lines.append(f"- {quick_ref_line}")
    lines.append("")

    if abstractions:
        lines.append("## Key Abstractions")
        for item in abstractions:
            lines.append(f"- {item}")
        lines.append("")

    if context_parts:
        lines.append("## Context")
        for part in context_parts:
            lines.append(f"- {part}")
        lines.append("")

    lines.append("## Conventions")
    lines.append("Follow conventions from the root [CLAUDE.md](../../CLAUDE.md).")
    lines.append("")

    return "\n".join(lines)


# --- Main ---

def get_all_repos():
    """Get all repo directory names under repos/storacha/."""
    if not os.path.isdir(REPOS_DIR):
        print(f"Error: {REPOS_DIR} does not exist")
        sys.exit(1)

    repos = []
    for entry in sorted(os.listdir(REPOS_DIR)):
        full_path = os.path.join(REPOS_DIR, entry)
        if os.path.isdir(full_path) and not entry.startswith("."):
            repos.append(entry)
    return repos


def get_repos_missing_claude_md(repos):
    """Return repos that don't have a CLAUDE.md."""
    missing = []
    for repo in repos:
        claude_md_path = os.path.join(REPOS_DIR, repo, "CLAUDE.md")
        if not os.path.exists(claude_md_path):
            missing.append(repo)
    return missing


def main():
    parser = argparse.ArgumentParser(
        description="Generate minimal CLAUDE.md files for repos that don't have one."
    )
    parser.add_argument(
        "--repo",
        help="Generate for a specific repo only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated content without writing files",
    )
    parser.add_argument(
        "--list-missing",
        action="store_true",
        help="List repos that need a CLAUDE.md and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing CLAUDE.md files (default: skip existing)",
    )
    args = parser.parse_args()

    all_repos = get_all_repos()
    print(f"Found {len(all_repos)} repos under repos/storacha/")

    # Load product map
    product_map = load_product_map()
    print(f"Loaded product metadata for {len(product_map)} repos")

    # Determine which repos to process
    if args.repo:
        if args.repo not in all_repos:
            print(f"Error: repo '{args.repo}' not found under repos/storacha/")
            sys.exit(1)
        target_repos = [args.repo]
    else:
        target_repos = all_repos

    # Filter to missing ones (unless --force)
    if not args.force:
        missing = get_repos_missing_claude_md(target_repos)
    else:
        missing = target_repos

    if args.list_missing:
        missing_all = get_repos_missing_claude_md(all_repos)
        print(f"\n{len(missing_all)} repos missing CLAUDE.md:")
        for repo in missing_all:
            product_info = product_map.get(repo, {})
            product = product_info.get("product", "?")
            lang = product_info.get("language", detect_language(os.path.join(REPOS_DIR, repo)))
            print(f"  {repo:<45s} [{lang}] ({product})")
        return

    if not missing:
        if args.repo:
            print(f"\n{args.repo} already has a CLAUDE.md (use --force to overwrite)")
        else:
            print("\nAll repos already have CLAUDE.md files!")
        return

    print(f"\nGenerating CLAUDE.md for {len(missing)} repos{'(dry run)' if args.dry_run else ''}...\n")

    generated = 0
    skipped = 0

    for repo_name in missing:
        repo_dir = os.path.join(REPOS_DIR, repo_name)
        product_info = product_map.get(repo_name)

        try:
            content = generate_claude_md(repo_name, repo_dir, product_info)
        except Exception as e:
            print(f"  ERROR: {repo_name}: {e}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"--- {repo_name}/CLAUDE.md ---")
            print(content)
            print()
            generated += 1
        else:
            output_path = os.path.join(repo_dir, "CLAUDE.md")
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  wrote {repo_name}/CLAUDE.md")
                generated += 1
            except OSError as e:
                print(f"  ERROR writing {repo_name}/CLAUDE.md: {e}")
                skipped += 1

    action = "generated" if args.dry_run else "wrote"
    print(f"\nDone: {action} {generated} CLAUDE.md files, {skipped} skipped")


if __name__ == "__main__":
    main()
