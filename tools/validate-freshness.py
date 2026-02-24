#!/usr/bin/env python3
"""
Freshness Validation Script for Storacha Memory Files.

Compares memory file claims against scanner data (data/*.json) and flags
potential drift: stale headers, quantitative mismatches, missing references.

Usage:
    python tools/validate-freshness.py                  # Full report (markdown)
    python tools/validate-freshness.py --ci --output r.json  # CI mode (JSON, exit 1 if issues)
    python tools/validate-freshness.py --file memory/tech/ucanto-framework.md
    python tools/validate-freshness.py --verbose        # Show all checks, not just failures
"""

import argparse
import datetime
import glob
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
DATA_DIR = os.path.join(BASE_DIR, "data")

STALENESS_THRESHOLD_DAYS = 90

# Regex for staleness header: <!-- Last validated: YYYY-MM-DD | Source: ... -->
HEADER_RE = re.compile(
    r"<!--\s*Last validated:\s*(\d{4}-\d{2}-\d{2})\s*\|\s*Source:\s*(.*?)\s*-->"
)

# Regex for capability references in backticks: `domain/verb`
# Matches things like `blob/add`, `space/content/serve/transport/http`
CAPABILITY_RE = re.compile(r"`([a-z][a-z0-9._-]*/[a-z*][-a-z0-9/]*)`")

# Path segments that indicate a file/import path rather than a capability name
FILE_PATH_SEGMENTS = {
    "src", "pkg", "cmd", "lib", "packages", "node", "node_modules",
    "internal", "test", "tests", "bin", "dist", "build",
    "capabilities", "handlers", "middleware",
}

# Regex for quantitative claims — numbers followed by key terms
# These patterns are designed to match aggregate/total claims, not per-item counts.
QUANT_PATTERNS = {
    "capabilities": re.compile(r"(\d+)\s+(?:UCAN\s+)?capabilit(?:y|ies)", re.IGNORECASE),
    "service_edges": re.compile(r"(\d+)\s+service\s+graph\s+edges", re.IGNORECASE),
    "sql_schemas": re.compile(r"(\d+)\s+SQL\s+schemas?", re.IGNORECASE),
    "products": re.compile(r"(\d+)\s+products?(?:\s|,|\.|$)", re.IGNORECASE),
}

# These patterns need context-awareness to avoid false positives
QUANT_CONTEXT_PATTERNS = {
    # Only match when "DynamoDB" and a number are both present on the same line
    "dynamo_tables": re.compile(r"DynamoDB.*?~?(\d+)\s*\+?\s*tables?|(\d+)\s*\+?\s*DynamoDB\s+tables?", re.IGNORECASE),
    # "N repos" — only match total/aggregate claims, not "used by N repos"
    "repos": re.compile(r"(\d+)\s+repos?(?:\s|,|\.|$)", re.IGNORECASE),
}

# Lines matching these patterns are per-item dependency counts, not aggregate claims
# e.g., "| @ucanto/core | 23 repos | ..." in blast radius tables
DEPENDENCY_COUNT_RE = re.compile(r"^\s*\|.*\|\s*\d+\s+repos?\s*\|", re.IGNORECASE)
# Lines that say "triggers N repos" or "used by N repos" are per-package, not aggregate
PER_PACKAGE_RE = re.compile(r"(?:triggers?|affects?|used\s+by|impacts?)\s+\d+", re.IGNORECASE)
# Lines in section headers like "### Tier 2: Change triggers 10-18 repos"
TIER_HEADER_RE = re.compile(r"(?:tier|caution).*\d+.*repos?", re.IGNORECASE)
# "across N repos" is a subset qualifier, not a total
ACROSS_RE = re.compile(r"across\s+\d+\s+repos?", re.IGNORECASE)

# Regex for repo/service name references (backtick-enclosed)
REPO_NAME_RE = re.compile(r"`([a-z][a-z0-9-]*(?:/[a-z][a-z0-9-]*)?)`")

# Minimum word-length for repo name matching to avoid false positives
MIN_REPO_NAME_LEN = 4

DRIFT_THRESHOLD_PERCENT = 10

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_json(filename):
    """Load a JSON file from the data directory, returning None on failure."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_scanner_facts():
    """Build a dict of ground-truth facts from scanner data files."""
    facts = {}

    # --- api-surface-map.json ---
    api = load_json("api-surface-map.json")
    if api:
        catalog = api.get("capability_catalog", [])
        facts["capability_count"] = len(catalog)
        facts["capability_names"] = set(c["can"] for c in catalog)

        graph = api.get("service_graph", [])
        facts["service_edge_count"] = len(graph)

    # --- infrastructure-map.json ---
    infra = load_json("infrastructure-map.json")
    if infra:
        summary = infra.get("summary", {})
        dynamo = summary.get("DynamoDB", {})
        facts["dynamo_table_count"] = len(dynamo)
        facts["dynamo_table_names"] = set(dynamo.keys())

        sql_schemas = infra.get("sql_schemas", [])
        facts["sql_schema_count"] = len(sql_schemas)

        per_repo = infra.get("per_repo", {})
        facts["infra_repo_names"] = set(per_repo.keys())

    # --- product-map.json ---
    prod = load_json("product-map.json")
    if prod:
        products = prod.get("products", [])
        facts["product_count"] = len(products)

        all_repos = set()
        for p in products:
            for r in p.get("repos", []):
                all_repos.add(r.get("name", ""))
        for r in prod.get("standalone", []):
            if isinstance(r, dict):
                all_repos.add(r.get("name", ""))
        for r in prod.get("downstream_consumers", []):
            if isinstance(r, dict):
                all_repos.add(r.get("repo", ""))
        all_repos.discard("")
        facts["repo_names"] = all_repos
        facts["repo_count"] = len(all_repos)

        meta = prod.get("meta", {})
        facts["meta_total_repos"] = meta.get("total_repos", facts["repo_count"])

    return facts


# ---------------------------------------------------------------------------
# Memory file analysis
# ---------------------------------------------------------------------------


def find_memory_files(specific_file=None):
    """Return list of memory .md files to check."""
    if specific_file:
        # Resolve relative to BASE_DIR if needed
        path = specific_file
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        if os.path.exists(path):
            return [path]
        return []

    pattern = os.path.join(MEMORY_DIR, "**", "*.md")
    return sorted(glob.glob(pattern, recursive=True))


def parse_staleness_header(content):
    """Extract (date_str, source) from staleness header, or (None, None)."""
    match = HEADER_RE.search(content)
    if match:
        return match.group(1), match.group(2)
    return None, None


def extract_capability_refs(content):
    """Extract capability name references from backtick-enclosed text."""
    found = set()
    for match in CAPABILITY_RE.finditer(content):
        cap = match.group(1)
        # Filter out things that are clearly not capabilities
        if cap.startswith("@") or "/" not in cap:
            continue
        # Skip paths that look like file paths (contain dots for extensions)
        if "." in cap.split("/")[-1] and not cap.endswith("/*"):
            continue
        # Skip file/import paths: any segment matching known path components
        segments = cap.rstrip("/").split("/")
        if any(seg in FILE_PATH_SEGMENTS for seg in segments):
            continue
        # Skip Go module paths (contain dots like github.com, go-ipld-prime)
        if any("." in seg for seg in segments[:-1]):
            continue
        # Skip if it ends with / (directory reference, not a capability)
        if cap.endswith("/"):
            continue
        # Skip if any segment starts with uppercase (Go package paths)
        if any(seg[0].isupper() for seg in segments if seg):
            continue
        # Skip example/placeholder patterns
        if cap in ("domain/verb", "domain/subdomain/verb"):
            continue
        # Skip programming patterns that use slash notation
        if cap in ("fork/join",):
            continue
        # Skip Go module-like paths and known external library references
        # Patterns: go-* prefix, org-name/pkg format, version suffix
        known_go_orgs = {
            "dgraph-io", "jackc", "lib", "mattn", "hashicorp",
            "aws", "google", "grpc", "prometheus", "opentelemetry",
        }
        if len(segments) >= 2 and (
            segments[0].startswith("go-")
            or segments[0] in known_go_orgs
            or (segments[-1].startswith("v") and segments[-1][1:].isdigit())  # e.g., v9
        ):
            continue
        # Skip npm-like import paths (e.g., multiformats/link, multiformats/hashes/sha2)
        # These are npm packages where first segment is a package scope
        npm_package_names = {
            "multiformats", "uint8arrays", "one-webcrypto",
        }
        if segments[0] in npm_package_names:
            continue
        found.add(cap)
    return found


def extract_quantitative_claims(content, filepath):
    """Extract quantitative claims with line numbers.

    Uses context awareness to skip per-package dependency counts (e.g.,
    '23 repos' in a blast radius table row) and only flag aggregate totals.
    """
    claims = []
    lines = content.split("\n")
    for line_no, line in enumerate(lines, start=1):
        # Check simple (non-context-sensitive) patterns
        for claim_type, pattern in QUANT_PATTERNS.items():
            for match in pattern.finditer(line):
                value = int(match.group(1))
                if value < 3:
                    continue
                claims.append({
                    "type": claim_type,
                    "value": value,
                    "line": line_no,
                    "text": line.strip(),
                })

        # Check context-sensitive patterns (repos, dynamo_tables)
        for claim_type, pattern in QUANT_CONTEXT_PATTERNS.items():
            for match in pattern.finditer(line):
                # Some patterns have multiple capture groups; take the first non-None
                raw = next((g for g in match.groups() if g is not None), None)
                if raw is None:
                    continue
                value = int(raw)
                if value < 3:
                    continue

                # Skip lines that are clearly per-package dependency counts
                if DEPENDENCY_COUNT_RE.search(line):
                    continue
                if PER_PACKAGE_RE.search(line):
                    continue
                if TIER_HEADER_RE.search(line):
                    continue
                # Skip "across N repos" (subset qualifier, not a total)
                if claim_type == "repos" and ACROSS_RE.search(line):
                    continue

                # For "DynamoDB tables", skip if in a table row (| ... |)
                if claim_type == "dynamo_tables" and line.strip().startswith("|"):
                    continue

                # Skip per-service DynamoDB counts (e.g., "5 DynamoDB tables" in a
                # bulleted list describing one service's resources)
                if claim_type == "dynamo_tables" and line.strip().startswith("-"):
                    continue

                claims.append({
                    "type": claim_type,
                    "value": value,
                    "line": line_no,
                    "text": line.strip(),
                })
    return claims


def extract_repo_refs(content):
    """Extract repo-name-like references from the file."""
    found = set()
    for match in REPO_NAME_RE.finditer(content):
        name = match.group(1)
        # Filter out things that are not repo names
        if len(name) < MIN_REPO_NAME_LEN:
            continue
        # Skip package names with @
        if name.startswith("@"):
            continue
        # Skip capability-like strings (contain /)
        if "/" in name:
            continue
        # Skip common non-repo words (generic terms, infra names, etc.)
        skip_words = {
            # Programming terms
            "error", "name", "string", "number", "boolean", "object",
            "function", "async", "await", "const", "export", "import",
            "return", "null", "undefined", "true", "false", "stage",
            "type", "interface", "class", "module", "package", "file",
            "path", "code", "test", "spec", "config", "handler",
            "server", "client", "service", "worker", "route", "method",
            "status", "pending", "active", "draft", "done", "derives",
            "with", "from", "result", "context", "reset", "group",
            "head", "advance", "task", "next", "link", "block",
            "digest", "proof", "receipt", "token", "agent", "issuer",
            "audience", "signer", "verifier", "principal", "validator",
            "transport", "access", "provide",
            # Domain/infra terms that look like repo names
            "blob", "index", "space", "upload", "store", "claim",
            "table", "queue", "bucket", "stack", "cache", "caching",
            "metadata", "usage", "replica", "consumer", "customer",
            "subscription", "allocation", "delegation", "revocation",
            "piece-v2", "egress-traffic-events",
            # Plural domain terms (DynamoDB table names, etc.)
            "indexes", "links", "nodes", "shards", "sources",
            "spaces", "uploads", "queues", "jobs", "machines",
            # Package sub-names (not repos)
            "capabilities", "blob-index", "filecoin-client",
            "upload-api", "upload-client",
            # CLI subcommand names from query tool
            "capability", "graph", "impact", "infra", "product", "repo",
            # Infra resource names
            "carpark-prod-0", "go-datastore", "postgres-provisioner",
            "jobqueue",
            # Spec names (w3-*)
            "w3-account", "w3-provider", "w3-replication",
            # Tool names
            "pnpm", "npm", "yarn",
        }
        if name.lower() in skip_words:
            continue
        found.add(name)
    return found


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def check_staleness(filepath, content, today):
    """Check if the staleness header is >90 days old or missing."""
    issues = []
    date_str, source = parse_staleness_header(content)

    if date_str is None:
        issues.append({
            "severity": "warning",
            "category": "missing_header",
            "message": "No staleness header found (expected `<!-- Last validated: YYYY-MM-DD | Source: ... -->`)",
            "line": 1,
        })
    else:
        try:
            validated_date = datetime.date.fromisoformat(date_str)
            age_days = (today - validated_date).days
            if age_days > STALENESS_THRESHOLD_DAYS:
                issues.append({
                    "severity": "error",
                    "category": "stale_header",
                    "message": f"Last validated {date_str} ({age_days} days ago, threshold is {STALENESS_THRESHOLD_DAYS})",
                    "line": 1,
                })
        except ValueError:
            issues.append({
                "severity": "error",
                "category": "invalid_header",
                "message": f"Invalid date in staleness header: {date_str}",
                "line": 1,
            })

    return issues


def check_quantitative_drift(filepath, content, facts):
    """Compare quantitative claims against scanner facts."""
    issues = []
    claims = extract_quantitative_claims(content, filepath)

    # Mapping from claim type to scanner fact key and label
    fact_map = {
        "capabilities": ("capability_count", "capabilities in api-surface-map.json"),
        "service_edges": ("service_edge_count", "service graph edges in api-surface-map.json"),
        "dynamo_tables": ("dynamo_table_count", "DynamoDB tables in infrastructure-map.json"),
        "repos": ("meta_total_repos", "repos in product-map.json"),
        "products": ("product_count", "products in product-map.json"),
        "sql_schemas": ("sql_schema_count", "SQL schemas in infrastructure-map.json"),
    }

    for claim in claims:
        ctype = claim["type"]
        if ctype not in fact_map:
            continue
        fact_key, label = fact_map[ctype]
        if fact_key not in facts:
            continue

        actual = facts[fact_key]
        claimed = claim["value"]

        if actual == 0:
            continue

        drift_pct = abs(claimed - actual) / actual * 100

        if drift_pct > DRIFT_THRESHOLD_PERCENT:
            issues.append({
                "severity": "warning",
                "category": "quantitative_drift",
                "message": (
                    f"Claims \"{claimed} {ctype}\" but scanner shows {actual} {label} "
                    f"({drift_pct:.0f}% drift)"
                ),
                "line": claim["line"],
                "claimed": claimed,
                "actual": actual,
                "drift_pct": round(drift_pct, 1),
            })

    return issues


def check_capability_refs(filepath, content, facts):
    """Check that capability names in memory exist in scanner data."""
    issues = []
    cap_names = facts.get("capability_names", set())
    if not cap_names:
        return issues

    refs = extract_capability_refs(content)
    lines = content.split("\n")

    for ref in sorted(refs):
        # Wildcard capabilities like `blob/*` are valid
        if ref in cap_names:
            continue

        # Check if it's a wildcard pattern that subsumes real capabilities
        if ref.endswith("/*"):
            prefix = ref[:-2] + "/"
            if any(c.startswith(prefix) for c in cap_names):
                continue

        # Check if it could be a partial match (e.g., Assert.location vs assert/location)
        # Skip if it looks like a code reference rather than a capability name
        if "." in ref:
            continue

        # Find line number for this reference
        ref_line = None
        escaped = re.escape(ref)
        for line_no, line in enumerate(lines, start=1):
            if re.search(r"`" + escaped + r"`", line):
                ref_line = line_no
                break

        # Check for close matches (e.g., blob/add -> space/blob/add)
        close_matches = [c for c in cap_names if ref in c or c in ref]
        suggestion = ""
        if close_matches:
            suggestion = f" (similar: {', '.join(sorted(close_matches)[:3])})"

        issues.append({
            "severity": "info",
            "category": "missing_in_scanner",
            "message": f"Capability `{ref}` mentioned but not found in api-surface-map.json{suggestion}",
            "line": ref_line or 0,
        })

    return issues


def check_repo_refs(filepath, content, facts):
    """Check that repo names referenced in memory exist in scanner data."""
    issues = []
    repo_names = facts.get("repo_names", set())
    if not repo_names:
        return issues

    refs = extract_repo_refs(content)
    lines = content.split("\n")

    for ref in sorted(refs):
        if ref in repo_names:
            continue
        # Skip common false positives (short names, generic terms)
        if len(ref) < 4:
            continue
        # Only flag if it looks like it could plausibly be a repo name
        # (kebab-case, lowercase)
        if not re.match(r"^[a-z][a-z0-9-]+$", ref):
            continue
        # Extra filter: skip if it's clearly a technology/tool name
        tool_names = {
            "mocha", "testify", "mockery", "wrangler", "miniflare",
            "typescript", "javascript", "cloudflare", "lambda",
            "dynamodb", "terraform", "docker", "redis", "postgres",
            "postgresql", "mongodb", "sqlite", "gossipsub", "bitswap",
            "multiaddr", "multihash", "multicodec", "dag-cbor",
            "dag-json", "dag-pb", "unixfs", "ipld", "ipfs", "ipni",
            "filecoin", "ethereum", "solidity", "cbor", "protobuf",
            "ed25519", "secp256k1", "sha256", "blake3",
            "sst", "vitest", "jest", "eslint", "prettier",
            "carpark", "presigned", "invocation", "delegation",
            "receipt", "attestation", "provider",
            "kebab-case", "snake-case", "camel-case",
        }
        if ref.lower() in tool_names:
            continue

        # Find line number
        ref_line = None
        escaped = re.escape(ref)
        for line_no, line in enumerate(lines, start=1):
            if re.search(r"`" + escaped + r"`", line):
                ref_line = line_no
                break

        if ref_line:
            issues.append({
                "severity": "info",
                "category": "missing_repo_in_scanner",
                "message": f"Repo `{ref}` mentioned but not found in product-map.json",
                "line": ref_line,
            })

    return issues


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def relative_path(filepath):
    """Return path relative to BASE_DIR for display."""
    if filepath.startswith(BASE_DIR):
        return filepath[len(BASE_DIR) + 1:]
    return filepath


def generate_markdown_report(results, today, verbose=False):
    """Generate a markdown report from validation results."""
    lines = []
    lines.append(f"# Freshness Validation Report -- {today.isoformat()}")
    lines.append("")

    # --- Summary ---
    total_files = len(results)
    files_with_issues = sum(1 for r in results if r["issues"])
    stale_headers = sum(
        1 for r in results
        for i in r["issues"]
        if i["category"] in ("stale_header", "missing_header", "invalid_header")
    )
    quant_drift = sum(
        1 for r in results
        for i in r["issues"]
        if i["category"] == "quantitative_drift"
    )
    missing_refs = sum(
        1 for r in results
        for i in r["issues"]
        if i["category"] in ("missing_in_scanner", "missing_repo_in_scanner")
    )

    lines.append("## Summary")
    lines.append(f"- Files checked: {total_files}")
    lines.append(f"- Files with issues: {files_with_issues}")
    lines.append(f"- Stale/missing headers: {stale_headers}")
    lines.append(f"- Quantitative drift: {quant_drift}")
    lines.append(f"- Missing references: {missing_refs}")
    lines.append("")

    if files_with_issues == 0 and not verbose:
        lines.append("All files passed validation.")
        return "\n".join(lines)

    # --- Issues by file ---
    lines.append("## Issues")
    lines.append("")

    for result in results:
        filepath = result["file"]
        issues = result["issues"]

        if not issues and not verbose:
            continue

        rel = relative_path(filepath)
        lines.append(f"### {rel}")

        if not issues:
            lines.append("- All checks passed.")
            lines.append("")
            continue

        for issue in issues:
            severity = issue["severity"].upper()
            category = issue["category"]
            message = issue["message"]
            line_no = issue.get("line", 0)

            # Format category into human-readable label
            label_map = {
                "stale_header": "Stale header",
                "missing_header": "Missing header",
                "invalid_header": "Invalid header",
                "quantitative_drift": "Quantitative drift",
                "missing_in_scanner": "Missing in scanner",
                "missing_repo_in_scanner": "Missing repo in scanner",
            }
            label = label_map.get(category, category)

            if line_no:
                lines.append(f"- **{label}** (line {line_no}): {message}")
            else:
                lines.append(f"- **{label}:** {message}")

        lines.append("")

    return "\n".join(lines)


def generate_json_report(results, today):
    """Generate a JSON report for CI mode."""
    total_files = len(results)
    files_with_issues = sum(1 for r in results if r["issues"])

    report = {
        "date": today.isoformat(),
        "summary": {
            "files_checked": total_files,
            "files_with_issues": files_with_issues,
            "stale_headers": sum(
                1 for r in results
                for i in r["issues"]
                if i["category"] in ("stale_header", "missing_header", "invalid_header")
            ),
            "quantitative_drift": sum(
                1 for r in results
                for i in r["issues"]
                if i["category"] == "quantitative_drift"
            ),
            "missing_references": sum(
                1 for r in results
                for i in r["issues"]
                if i["category"] in ("missing_in_scanner", "missing_repo_in_scanner")
            ),
        },
        "files": [],
    }

    for result in results:
        if result["issues"]:
            file_entry = {
                "file": relative_path(result["file"]),
                "issues": result["issues"],
            }
            report["files"].append(file_entry)

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Validate freshness of memory files against scanner data."
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: exit code 1 if issues found",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write report to file (JSON in --ci mode, markdown otherwise)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Check a specific memory file instead of all",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all checks, including passing files",
    )
    args = parser.parse_args()

    today = datetime.date.today()

    # Load scanner data
    facts = build_scanner_facts()
    if not facts:
        print("ERROR: No scanner data found in data/. Run scanners first.", file=sys.stderr)
        sys.exit(2)

    # Find memory files
    files = find_memory_files(specific_file=args.file)
    if not files:
        if args.file:
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        else:
            print(f"ERROR: No memory files found in {MEMORY_DIR}", file=sys.stderr)
        sys.exit(2)

    # Validate each file
    results = []
    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        issues = []
        issues.extend(check_staleness(filepath, content, today))
        issues.extend(check_quantitative_drift(filepath, content, facts))
        issues.extend(check_capability_refs(filepath, content, facts))
        issues.extend(check_repo_refs(filepath, content, facts))

        results.append({
            "file": filepath,
            "issues": issues,
        })

    # Generate report
    if args.ci:
        report = generate_json_report(results, today)
        report_text = json.dumps(report, indent=2)
    else:
        report_text = generate_markdown_report(results, today, verbose=args.verbose)

    # Output
    if args.output:
        output_path = args.output
        if not os.path.isabs(output_path):
            output_path = os.path.join(BASE_DIR, output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
            f.write("\n")
        print(f"Report written to {output_path}")
    else:
        print(report_text)

    # Exit code for CI
    if args.ci:
        has_issues = any(r["issues"] for r in results)
        sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
