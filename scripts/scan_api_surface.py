#!/usr/bin/env python3
"""
API Surface & Data Flow Scanner

Discovers from source code:
- HTTP routes (Cloudflare Workers, Express, Go http.ServeMux, SST Api, Lambda)
- UCAN capabilities (definitions + service handlers)
- Service-to-service calls (ucanto invocations, fetch, service bindings, queues)

Produces a service interaction graph and per-service API surface map.

Run: python3 aidev/scripts/scan_api_surface.py
From: project root (parent of aidev/)
"""

import os
import sys
import json
import re
import yaml
from pathlib import Path
from collections import defaultdict

# aidev/scripts/ -> aidev/ -> project root
AIDEV_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = AIDEV_DIR.parent
REPOS_DIR = PROJECT_ROOT  # repos are siblings of aidev/
OUTPUT_DIR = AIDEV_DIR / "data"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "vendor", ".next",
             "coverage", "__pycache__", ".turbo", "target", ".pnpm",
             "test", "tests", "__tests__", "fixtures", "mocks"}

# Also skip test files themselves (even if not in a test directory)
SKIP_FILE_PATTERNS = {"test.", ".test.", ".spec.", "__test__", "__mock__"}

DROP_REPOS = {"resteep", "stubble", "dashboard-demo-clone"}


def read_file_safe(path, max_bytes=200000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)
    except:
        return ""


def should_skip(fpath):
    return any(s in fpath.parts for s in SKIP_DIRS)


def is_test_file(fpath):
    name = fpath.name.lower()
    return any(p in name for p in SKIP_FILE_PATTERNS)


# ═══════════════════════════════════════════════════════════════
#  SECTION 1: HTTP ROUTE SCANNERS
# ═══════════════════════════════════════════════════════════════

def scan_js_routes(repo_path):
    """Extract HTTP routes from JS/TS files: itty-router, Express, CF Workers, Lambda."""
    routes = []
    entry_points = []

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath) or is_test_file(fpath):
            continue
        if fpath.suffix not in (".js", ".ts", ".mjs", ".mts"):
            continue

        content = read_file_safe(str(fpath))
        if not content:
            continue
        rel = str(fpath.relative_to(repo_path))

        # ── itty-router / Express routes ──
        for m in re.finditer(
            r'(?:router|app)\s*\.\s*(get|post|put|delete|patch|all|options)\s*\(\s*[\'"]([^\'"]+)[\'"]',
            content, re.IGNORECASE
        ):
            method = m.group(1).upper()
            path = m.group(2)
            routes.append({
                "method": method,
                "path": path,
                "framework": "router",
                "file": rel,
            })

        # ── CF Worker export default { fetch } ──
        if re.search(r'export\s+default\s*\{', content):
            if re.search(r'async\s+fetch\s*\(', content):
                entry_points.append({
                    "type": "cloudflare_worker",
                    "file": rel,
                })
                # Extract inline method/path routing
                for m in re.finditer(
                    r"(?:request\.method|method)\s*===?\s*['\"](\w+)['\"]",
                    content
                ):
                    method = m.group(1).upper()
                    # Try to find associated path
                    routes.append({
                        "method": method,
                        "path": "/",
                        "framework": "cf_worker_inline",
                        "file": rel,
                        "note": "inline method check",
                    })

            # CF Queue consumer
            if re.search(r'async\s+queue\s*\(', content):
                entry_points.append({
                    "type": "cloudflare_queue_consumer",
                    "file": rel,
                })

        # ── SST Api routes ──
        for m in re.finditer(
            r"['\"](\w+)\s+(/[^'\"]*)['\"]",
            content
        ):
            candidate_method = m.group(1).upper()
            candidate_path = m.group(2)
            if candidate_method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                # Verify it's in a routes block
                start = max(0, m.start() - 200)
                context_before = content[start:m.start()]
                if "routes" in context_before or "Api(" in context_before:
                    routes.append({
                        "method": candidate_method,
                        "path": candidate_path,
                        "framework": "sst_api",
                        "file": rel,
                    })

        # ── Lambda handler ──
        if re.search(r'export\s+(?:const|function)\s+(?:_?handler|main)\s*=?\s*', content):
            if re.search(r'event\s*(?:\.\s*requestContext|\.rawPath|\.\s*httpMethod)', content):
                entry_points.append({
                    "type": "lambda_handler",
                    "file": rel,
                })
                # Extract path-based routing
                for m in re.finditer(
                    r"(?:rawPath|pathname)\s*(?:===?\s*|\.startsWith\s*\(\s*)['\"]([^'\"]+)['\"]",
                    content
                ):
                    routes.append({
                        "method": "ANY",
                        "path": m.group(1),
                        "framework": "lambda",
                        "file": rel,
                    })

        # ── Middleware composition (Freeway-style) ──
        if re.search(r'composeMiddleware\s*\(', content):
            middlewares = re.findall(r'with(\w+)', content)
            entry_points.append({
                "type": "middleware_composition",
                "file": rel,
                "middlewares": middlewares[:20],
            })

        # ── UCANTO server as HTTP endpoint ──
        if re.search(r'Server\.create\s*\(', content):
            entry_points.append({
                "type": "ucanto_server",
                "file": rel,
            })

    return routes, entry_points


def scan_go_routes(repo_path):
    """Extract HTTP routes from Go files."""
    routes = []
    entry_points = []

    for fpath in Path(repo_path).rglob("*.go"):
        if should_skip(fpath) or is_test_file(fpath):
            continue

        content = read_file_safe(str(fpath))
        if not content:
            continue
        rel = str(fpath.relative_to(repo_path))

        # ── http.NewServeMux + mux.HandleFunc ──
        if "http.NewServeMux" in content or "http.ServeMux" in content:
            entry_points.append({
                "type": "go_http_server",
                "file": rel,
            })

        # Pattern: mux.HandleFunc("METHOD /path", handler)
        # Or: maybeInstrumentAndAdd(mux, "METHOD /path", handler, ...)
        for m in re.finditer(
            r'(?:mux\.HandleFunc|mux\.Handle|HandleFunc|maybeInstrumentAndAdd)\s*\(\s*(?:\w+\s*,\s*)?["\'](\w+)\s+(/[^"\']*)["\']',
            content
        ):
            routes.append({
                "method": m.group(1).upper(),
                "path": m.group(2),
                "framework": "go_http",
                "file": rel,
            })

        # Pattern: "GET /path" as first arg (Go 1.22+ style)
        for m in re.finditer(
            r'["\'](\w+)\s+(/[^"\']+)["\']',
            content
        ):
            candidate = m.group(1).upper()
            if candidate in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                context_start = max(0, m.start() - 100)
                if "mux" in content[context_start:m.start()] or "Handle" in content[context_start:m.start()]:
                    routes.append({
                        "method": candidate,
                        "path": m.group(2),
                        "framework": "go_http",
                        "file": rel,
                    })

        # http.ListenAndServe
        if re.search(r'http\.ListenAndServe|srv\.ListenAndServe|ListenAndServe\(', content):
            entry_points.append({
                "type": "go_http_listener",
                "file": rel,
            })

    return routes, entry_points


def scan_wrangler_routes(repo_path):
    """Extract route info from wrangler.toml (custom domains, route patterns)."""
    routes_info = []

    for wf in Path(repo_path).rglob("wrangler.toml"):
        if should_skip(wf):
            continue
        content = read_file_safe(str(wf))
        rel = str(wf.relative_to(repo_path))

        # Worker name
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        worker_name = name_match.group(1) if name_match else None

        # Custom domains
        for m in re.finditer(r'hostname\s*=\s*"([^"]+)"', content):
            routes_info.append({
                "type": "custom_domain",
                "hostname": m.group(1),
                "worker": worker_name,
                "file": rel,
            })

        # Route patterns
        for m in re.finditer(r'pattern\s*=\s*"([^"]+)"', content):
            routes_info.append({
                "type": "route_pattern",
                "pattern": m.group(1),
                "worker": worker_name,
                "file": rel,
            })

        # Main entrypoint
        main_match = re.search(r'^main\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if main_match:
            routes_info.append({
                "type": "worker_entrypoint",
                "main": main_match.group(1),
                "worker": worker_name,
                "file": rel,
            })

    return routes_info


# ═══════════════════════════════════════════════════════════════
#  SECTION 2: UCAN CAPABILITY SCANNERS
# ═══════════════════════════════════════════════════════════════

def scan_capability_definitions(repo_path):
    """Find UCAN capability definitions (capability({ can: '...' }))."""
    capabilities = []

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath) or is_test_file(fpath):
            continue
        if fpath.suffix not in (".js", ".ts", ".mjs"):
            continue

        content = read_file_safe(str(fpath))
        if "capability(" not in content:
            continue
        rel = str(fpath.relative_to(repo_path))

        # Pattern: export const name = capability({ can: 'namespace/action', ... })
        for m in re.finditer(
            r"(?:export\s+(?:const|let)\s+)?(\w+)\s*=\s*capability\s*\(\s*\{[^}]*?can\s*:\s*['\"]([^'\"]+)['\"]",
            content, re.DOTALL
        ):
            var_name = m.group(1)
            can = m.group(2)

            # Try to extract `with` schema
            block_start = m.start()
            # Find the matching closing of capability({...})
            block_end = content.find("})", block_start)
            if block_end == -1:
                block_end = min(block_start + 500, len(content))
            block = content[block_start:block_end]

            with_match = re.search(r'with\s*:\s*(\S+)', block)
            with_schema = with_match.group(1).rstrip(",") if with_match else None

            # Extract nb fields
            nb_match = re.search(r'nb\s*:\s*Schema\.struct\s*\(\s*\{([^}]+)\}', block, re.DOTALL)
            nb_fields = []
            if nb_match:
                nb_block = nb_match.group(1)
                for field_m in re.finditer(r'(\w+)\s*:', nb_block):
                    nb_fields.append(field_m.group(1))

            capabilities.append({
                "can": can,
                "export_name": var_name,
                "with": with_schema,
                "nb_fields": nb_fields if nb_fields else None,
                "file": rel,
            })

    return capabilities


def scan_capability_handlers(repo_path):
    """Find service handlers that implement capabilities."""
    handlers = []

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath) or is_test_file(fpath):
            continue
        if fpath.suffix not in (".js", ".ts", ".mjs"):
            continue

        content = read_file_safe(str(fpath))
        if "Server." not in content and "provide" not in content.lower():
            continue
        rel = str(fpath.relative_to(repo_path))

        # Pattern: Server.provide(Capability.name, handler)
        for m in re.finditer(
            r'Server\.provide\s*\(\s*(\w+)\.(\w+)\s*,',
            content
        ):
            namespace = m.group(1)
            action = m.group(2)
            handlers.append({
                "pattern": "Server.provide",
                "capability_ref": f"{namespace}.{action}",
                "file": rel,
            })

        # Pattern: Server.provideAdvanced({ capability: Cap.name, handler: ... })
        for m in re.finditer(
            r'Server\.provideAdvanced\s*\(\s*\{\s*capability\s*:\s*(\w+)\.(\w+)',
            content
        ):
            namespace = m.group(1)
            action = m.group(2)
            handlers.append({
                "pattern": "Server.provideAdvanced",
                "capability_ref": f"{namespace}.{action}",
                "file": rel,
            })

        # Pattern: createService / createXxxService factory
        for m in re.finditer(
            r'(?:export\s+)?(?:const|function)\s+(create\w*Service)\s*(?:=\s*)?(?:\([^)]*\)\s*(?:=>)?\s*(?:\(\s*)?\{|(?:\([^)]*\)\s*\{))',
            content
        ):
            fn_name = m.group(1)
            # Extract the service object keys
            block_start = m.end()
            # Try to find the service object
            brace_count = 1
            i = block_start
            while i < len(content) and brace_count > 0:
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                i += 1
            block = content[block_start:min(i, block_start + 2000)]

            # Find keys in the returned object
            service_keys = re.findall(r'^\s+(\w+)\s*:', block, re.MULTILINE)
            # Filter to likely capability handler keys
            service_keys = [k for k in service_keys if not k.startswith("_") and k not in
                           ("id", "codec", "service", "catch", "validateAuthorization",
                            "errorReporter", "context", "connection", "channel")]

            handlers.append({
                "pattern": "service_factory",
                "factory_name": fn_name,
                "capabilities_served": service_keys[:30],
                "file": rel,
            })

    return handlers


def scan_go_ucan_handlers(repo_path):
    """Find Go UCAN/content-claims handlers."""
    handlers = []

    for fpath in Path(repo_path).rglob("*.go"):
        if should_skip(fpath) or is_test_file(fpath):
            continue

        content = read_file_safe(str(fpath))
        rel = str(fpath.relative_to(repo_path))

        # Go handler functions for claims
        for m in re.finditer(
            r'func\s+((?:Get|Post|Put|Delete|Handle)\w+Handler)\s*\(',
            content
        ):
            handlers.append({
                "pattern": "go_handler_func",
                "handler_name": m.group(1),
                "file": rel,
            })

        # ucanto server setup
        if re.search(r'server\.(?:New|Create|ListenAndServe)', content):
            handlers.append({
                "pattern": "go_ucanto_server",
                "file": rel,
            })

    return handlers


# ═══════════════════════════════════════════════════════════════
#  SECTION 3: SERVICE-TO-SERVICE CALL SCANNERS
# ═══════════════════════════════════════════════════════════════

def scan_ucanto_connections(repo_path):
    """Find ucanto client connections to other services."""
    connections = []

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath) or is_test_file(fpath):
            continue
        if fpath.suffix not in (".js", ".ts", ".mjs"):
            continue

        content = read_file_safe(str(fpath))
        if "connect" not in content and "invoke" not in content:
            continue
        rel = str(fpath.relative_to(repo_path))

        # Pattern: connect({ id: ..., codec: ..., channel: HTTP.open({ url: ... }) })
        for m in re.finditer(
            r'connect\s*\(\s*\{[^}]*channel\s*:\s*HTTP\.open\s*\(\s*\{[^}]*url\s*:\s*(?:new\s+URL\s*\(\s*)?([^)},]+)',
            content, re.DOTALL
        ):
            url_expr = m.group(1).strip().strip("'\"")
            connections.append({
                "type": "ucanto_connection",
                "target_url": url_expr,
                "file": rel,
            })

        # Pattern: connect({ id, codec, channel }) — simpler form
        for m in re.finditer(
            r'(?:Client\.)?connect\s*\(\s*\{[^}]*id\s*:\s*(\w+)',
            content, re.DOTALL
        ):
            target_id = m.group(1)
            connections.append({
                "type": "ucanto_connection",
                "target_id": target_id,
                "file": rel,
            })

        # Pattern: Capability.invoke({ issuer, audience, with, nb })
        for m in re.finditer(
            r'(\w+(?:\.\w+)*)\s*\.invoke\s*\(\s*\{[^}]*audience\s*:\s*(\w+)',
            content, re.DOTALL
        ):
            capability = m.group(1)
            audience = m.group(2)
            connections.append({
                "type": "ucanto_invocation",
                "capability": capability,
                "audience": audience,
                "file": rel,
            })

        # Pattern: invocation.execute(connection)
        for m in re.finditer(
            r'\.execute\s*\(\s*(\w+)',
            content
        ):
            connections.append({
                "type": "ucanto_execute",
                "connection_var": m.group(1),
                "file": rel,
            })

    return connections


def scan_http_service_calls(repo_path):
    """Find HTTP fetch calls to other services."""
    calls = []

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath) or is_test_file(fpath):
            continue
        if fpath.suffix not in (".js", ".ts", ".mjs"):
            continue

        content = read_file_safe(str(fpath))
        if "fetch(" not in content:
            continue
        rel = str(fpath.relative_to(repo_path))

        # fetch with env var URLs
        for m in re.finditer(
            r'fetch\s*\(\s*(?:`\$\{)?(?:env\.)?(\w+(?:_URL|_ENDPOINT|_API)[^`\'")\s,]*)',
            content
        ):
            url_ref = m.group(1).strip("`${}'\"\n ")
            calls.append({
                "type": "fetch_env_url",
                "url_ref": url_ref,
                "file": rel,
            })

        # fetch with literal URLs
        for m in re.finditer(
            r'fetch\s*\(\s*[\'"](\w+://[^\'"]+)[\'"]',
            content
        ):
            calls.append({
                "type": "fetch_literal_url",
                "url": m.group(1),
                "file": rel,
            })

        # Service binding fetch: env.SERVICE.fetch(
        for m in re.finditer(
            r'env\.(\w+)\.fetch\s*\(',
            content
        ):
            binding = m.group(1)
            calls.append({
                "type": "service_binding_call",
                "binding": binding,
                "file": rel,
            })

    return calls


def scan_queue_sends(repo_path):
    """Find queue send operations (async service communication)."""
    sends = []

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath) or is_test_file(fpath):
            continue
        if fpath.suffix not in (".js", ".ts", ".mjs"):
            continue

        content = read_file_safe(str(fpath))
        rel = str(fpath.relative_to(repo_path))

        # env.QUEUE_NAME.send(
        for m in re.finditer(r'env\.(\w+)\.send\s*\(', content):
            sends.append({
                "type": "queue_send",
                "queue_binding": m.group(1),
                "file": rel,
            })

        # SQS send
        for m in re.finditer(r'(?:sqs|queue).*\.send(?:Message)?\s*\(', content, re.IGNORECASE):
            sends.append({
                "type": "sqs_send",
                "file": rel,
            })

    return sends


def scan_go_service_calls(repo_path):
    """Find Go HTTP client calls to other services."""
    calls = []

    for fpath in Path(repo_path).rglob("*.go"):
        if should_skip(fpath) or is_test_file(fpath):
            continue

        content = read_file_safe(str(fpath))
        rel = str(fpath.relative_to(repo_path))

        # http.NewRequest / http.Get / http.Post
        for m in re.finditer(
            r'http\.(?:NewRequest|Get|Post|PostForm)\s*\(\s*(?:ctx\s*,\s*)?(?:"(\w+)"\s*,\s*)?([^,)]+)',
            content
        ):
            method = m.group(1) or "GET"
            url_expr = m.group(2).strip().strip('"')
            calls.append({
                "type": "go_http_call",
                "method": method.upper() if m.group(1) else "?",
                "url_expr": url_expr[:100],
                "file": rel,
            })

        # doRequest pattern (custom HTTP client)
        for m in re.finditer(
            r'doRequest\s*\([^,]*,\s*"(\w+)"\s*,\s*"([^"]+)"',
            content
        ):
            calls.append({
                "type": "go_http_call",
                "method": m.group(1).upper(),
                "path": m.group(2),
                "file": rel,
            })

    return calls


def scan_service_url_env_vars(repo_path):
    """Extract environment variables that reference other service URLs."""
    env_urls = []

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath):
            continue
        if fpath.name not in ("wrangler.toml", ".env", ".env.example", ".env.local",
                              ".dev.vars", ".dev.vars.example"):
            continue

        content = read_file_safe(str(fpath))
        rel = str(fpath.relative_to(repo_path))

        # Pattern: VAR_NAME = "https://..."
        for m in re.finditer(
            r'^(\w+(?:_URL|_ENDPOINT|_DID|_SERVICE|_API)\w*)\s*=\s*["\']?([^\s"\'#]+)',
            content, re.MULTILINE
        ):
            env_urls.append({
                "var": m.group(1),
                "value": m.group(2),
                "file": rel,
            })

    # Also scan JS/TS for env var references
    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath) or is_test_file(fpath):
            continue
        if fpath.suffix not in (".js", ".ts", ".mjs"):
            continue

        content = read_file_safe(str(fpath))
        rel = str(fpath.relative_to(repo_path))

        for m in re.finditer(
            r'(?:env|process\.env)\s*[\.\[]\s*[\'"]?(\w+(?:_URL|_DID|_ENDPOINT)\w*)',
            content
        ):
            env_urls.append({
                "var": m.group(1),
                "file": rel,
                "context": "code_reference",
            })

    return env_urls


# ═══════════════════════════════════════════════════════════════
#  SERVICE GRAPH BUILDER
# ═══════════════════════════════════════════════════════════════

def build_service_graph(all_results):
    """Build a service-to-service interaction graph from all findings."""
    edges = []

    for repo_name, data in all_results.items():
        # ucanto invocations
        for conn in data.get("ucanto_connections", []):
            if conn["type"] == "ucanto_invocation":
                edges.append({
                    "from": repo_name,
                    "to": conn.get("audience", "?"),
                    "via": "ucanto",
                    "capability": conn.get("capability", "?"),
                })
            elif conn["type"] == "ucanto_connection":
                target = conn.get("target_url", conn.get("target_id", "?"))
                edges.append({
                    "from": repo_name,
                    "to": target,
                    "via": "ucanto_connection",
                })

        # HTTP service calls
        for call in data.get("http_service_calls", []):
            if call["type"] == "service_binding_call":
                edges.append({
                    "from": repo_name,
                    "to": call["binding"],
                    "via": "cf_service_binding",
                })
            elif call["type"] == "fetch_env_url":
                edges.append({
                    "from": repo_name,
                    "to": call["url_ref"],
                    "via": "http_fetch",
                })

        # Queue sends
        for send in data.get("queue_sends", []):
            edges.append({
                "from": repo_name,
                "to": send.get("queue_binding", "?"),
                "via": "queue",
            })

        # Go HTTP calls
        for call in data.get("go_service_calls", []):
            edges.append({
                "from": repo_name,
                "to": call.get("url_expr", call.get("path", "?"))[:60],
                "via": "go_http",
            })

    return edges


# ═══════════════════════════════════════════════════════════════
#  REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_report(all_results, service_graph, all_capabilities):
    report = []
    report.append("=" * 72)
    report.append("  STORACHA API SURFACE & DATA FLOW MAP")
    report.append("  HTTP routes, UCAN capabilities, service-to-service calls")
    report.append("=" * 72)

    # ── Global Capability Catalog ──
    report.append(f"\n{'━' * 72}")
    report.append("  UCAN CAPABILITY CATALOG")
    report.append(f"{'━' * 72}")

    # Collect all capabilities across repos
    all_caps = []
    for repo_name, data in sorted(all_results.items()):
        for cap in data.get("capabilities", []):
            all_caps.append((repo_name, cap))

    # Group by namespace
    cap_by_namespace = defaultdict(list)
    for repo_name, cap in all_caps:
        ns = cap["can"].rsplit("/", 1)[0] if "/" in cap["can"] else cap["can"]
        cap_by_namespace[ns].append((repo_name, cap))

    for ns in sorted(cap_by_namespace.keys()):
        items = cap_by_namespace[ns]
        report.append(f"\n  [{ns}]")
        for repo_name, cap in sorted(items, key=lambda x: x[1]["can"]):
            nb = f"  nb: {', '.join(cap['nb_fields'])}" if cap.get("nb_fields") else ""
            report.append(f"    {cap['can']:45s} {repo_name:30s}{nb}")

    # ── Service Graph ──
    report.append(f"\n\n{'━' * 72}")
    report.append("  SERVICE INTERACTION GRAPH")
    report.append(f"{'━' * 72}")

    # Deduplicate edges
    seen_edges = set()
    unique_edges = []
    for edge in service_graph:
        key = (edge["from"], edge["to"], edge["via"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)

    # Group by source
    edges_by_source = defaultdict(list)
    for edge in unique_edges:
        edges_by_source[edge["from"]].append(edge)

    for source in sorted(edges_by_source.keys()):
        edges = edges_by_source[source]
        report.append(f"\n  {source}")
        for edge in sorted(edges, key=lambda e: e["to"]):
            cap_info = f"  ({edge['capability']})" if edge.get("capability") else ""
            report.append(f"    → {edge['to']:40s} via {edge['via']}{cap_info}")

    # ── Per-repo API surface ──
    report.append(f"\n\n{'━' * 72}")
    report.append("  PER-SERVICE API SURFACE")
    report.append(f"{'━' * 72}")

    for repo_name in sorted(all_results.keys()):
        data = all_results[repo_name]

        has_content = (data.get("routes") or data.get("entry_points") or
                       data.get("capabilities") or data.get("capability_handlers") or
                       data.get("wrangler_routes"))

        if not has_content:
            continue

        report.append(f"\n{'─' * 60}")
        report.append(f"  {repo_name}")
        report.append(f"{'─' * 60}")

        # Entry points
        if data.get("entry_points"):
            report.append(f"  Entry Points:")
            for ep in data["entry_points"]:
                mw = f"  middlewares: {', '.join(ep['middlewares'][:10])}" if ep.get("middlewares") else ""
                report.append(f"    [{ep['type']}] {ep['file']}{mw}")

        # Wrangler info
        if data.get("wrangler_routes"):
            report.append(f"  Worker Config:")
            for wr in data["wrangler_routes"]:
                if wr["type"] == "worker_entrypoint":
                    report.append(f"    worker: {wr.get('worker', '?')}  main: {wr['main']}")
                elif wr["type"] == "custom_domain":
                    report.append(f"    domain: {wr['hostname']}")
                elif wr["type"] == "route_pattern":
                    report.append(f"    route: {wr['pattern']}")

        # HTTP routes
        if data.get("routes"):
            report.append(f"  HTTP Routes:")
            seen = set()
            for r in sorted(data["routes"], key=lambda x: (x["path"], x["method"])):
                key = f"{r['method']} {r['path']}"
                if key not in seen:
                    seen.add(key)
                    report.append(f"    {r['method']:8s} {r['path']:35s} ({r['framework']}) {r['file']}")

        # UCAN capabilities defined
        if data.get("capabilities"):
            report.append(f"  UCAN Capabilities Defined:")
            for cap in sorted(data["capabilities"], key=lambda x: x["can"]):
                nb = f"  nb: {', '.join(cap['nb_fields'])}" if cap.get("nb_fields") else ""
                report.append(f"    {cap['can']:45s} → {cap['export_name']}{nb}")

        # Capability handlers
        if data.get("capability_handlers"):
            report.append(f"  UCAN Capability Handlers:")
            for h in data["capability_handlers"]:
                if h["pattern"] == "service_factory":
                    caps = ", ".join(h.get("capabilities_served", [])[:15])
                    report.append(f"    {h['factory_name']}(): {caps}")
                    report.append(f"      file: {h['file']}")
                elif h.get("capability_ref"):
                    report.append(f"    {h['pattern']:30s} → {h['capability_ref']:30s} {h['file']}")
                elif h.get("handler_name"):
                    report.append(f"    {h['pattern']:30s} → {h['handler_name']:30s} {h['file']}")
                else:
                    report.append(f"    {h['pattern']:30s}   {h['file']}")

        # Outbound connections
        outbound = []
        for conn in data.get("ucanto_connections", []):
            outbound.append(conn)
        for call in data.get("http_service_calls", []):
            outbound.append(call)
        for send in data.get("queue_sends", []):
            outbound.append(send)
        for call in data.get("go_service_calls", []):
            outbound.append(call)

        if outbound:
            report.append(f"  Outbound Service Calls:")
            for item in outbound:
                t = item["type"]
                if t == "ucanto_invocation":
                    report.append(f"    UCAN invoke  {item.get('capability', '?'):30s} → {item.get('audience', '?')}")
                elif t == "ucanto_connection":
                    target = item.get("target_url", item.get("target_id", "?"))
                    report.append(f"    UCAN connect → {target}")
                elif t == "service_binding_call":
                    report.append(f"    CF binding   env.{item['binding']}.fetch()")
                elif t == "fetch_env_url":
                    report.append(f"    HTTP fetch   {item['url_ref']}")
                elif t == "queue_send":
                    report.append(f"    Queue send   env.{item['queue_binding']}.send()")
                elif t == "go_http_call":
                    report.append(f"    Go HTTP      {item.get('method', '?')} {item.get('url_expr', item.get('path', '?'))[:50]}")

        # Service URL env vars
        if data.get("service_env_vars"):
            env_seen = set()
            env_items = []
            for ev in data["service_env_vars"]:
                key = ev["var"]
                if key not in env_seen:
                    env_seen.add(key)
                    env_items.append(ev)
            if env_items:
                report.append(f"  Service URL Config:")
                for ev in sorted(env_items, key=lambda x: x["var"]):
                    val = ev.get("value", "")
                    if val:
                        report.append(f"    {ev['var']:40s} = {val}")
                    else:
                        report.append(f"    {ev['var']:40s}   (referenced in {ev['file']})")

    return "\n".join(report)


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("  API SURFACE & DATA FLOW SCANNER")
    print("  HTTP routes, UCAN capabilities, service-to-service calls")
    print("=" * 72)

    # Discover repos directly from filesystem
    analyze_list = []
    for d in sorted(REPOS_DIR.iterdir()):
        if d.is_dir() and d.name not in DROP_REPOS and not d.name.startswith("."):
            analyze_list.append({"name": d.name})

    all_results = {}

    for i, ri in enumerate(analyze_list):
        name = ri["name"]
        rp = REPOS_DIR / name
        if not rp.exists():
            continue

        sys.stdout.write(f"\r   [{i+1}/{len(analyze_list)}] {name:40s}")
        sys.stdout.flush()

        result = {}

        # HTTP routes
        js_routes, js_entries = scan_js_routes(rp)
        go_routes, go_entries = scan_go_routes(rp)
        wrangler_routes = scan_wrangler_routes(rp)

        result["routes"] = js_routes + go_routes
        result["entry_points"] = js_entries + go_entries
        result["wrangler_routes"] = wrangler_routes

        # UCAN capabilities
        result["capabilities"] = scan_capability_definitions(rp)
        result["capability_handlers"] = scan_capability_handlers(rp) + scan_go_ucan_handlers(rp)

        # Service-to-service
        result["ucanto_connections"] = scan_ucanto_connections(rp)
        result["http_service_calls"] = scan_http_service_calls(rp)
        result["queue_sends"] = scan_queue_sends(rp)
        result["go_service_calls"] = scan_go_service_calls(rp)
        result["service_env_vars"] = scan_service_url_env_vars(rp)

        # Only keep if there's something interesting
        has_content = any(result[k] for k in result)
        if has_content:
            all_results[name] = result

    print(f"\n\n   Scanned {len(analyze_list)} repos, found API surface in {len(all_results)}")

    # Build service graph
    service_graph = build_service_graph(all_results)

    # Collect all capabilities
    all_caps = []
    for repo_name, data in all_results.items():
        for cap in data.get("capabilities", []):
            all_caps.append({"repo": repo_name, **cap})

    # Generate report
    report = generate_report(all_results, service_graph, all_caps)
    print(report)

    # Save outputs
    with open(OUTPUT_DIR / "api-surface-map.txt", "w") as f:
        f.write(report)

    # JSON output
    json_output = {
        "capability_catalog": all_caps,
        "service_graph": service_graph,
        "per_repo": {},
    }

    for name, data in all_results.items():
        json_output["per_repo"][name] = data

    with open(OUTPUT_DIR / "api-surface-map.json", "w") as f:
        json.dump(json_output, f, indent=2, default=list)

    # Stats
    total_routes = sum(len(d.get("routes", [])) for d in all_results.values())
    total_caps = len(all_caps)
    total_handlers = sum(len(d.get("capability_handlers", [])) for d in all_results.values())
    total_edges = len(service_graph)

    print(f"\n\n{'=' * 72}")
    print(f"  DONE")
    print(f"{'=' * 72}")
    print(f"  Services with API surface:   {len(all_results)}")
    print(f"  HTTP routes found:           {total_routes}")
    print(f"  UCAN capabilities defined:   {total_caps}")
    print(f"  Capability handlers:         {total_handlers}")
    print(f"  Service graph edges:         {total_edges}")
    print(f"")
    print(f"  {OUTPUT_DIR}/")
    print(f"     api-surface-map.txt     <- human-readable")
    print(f"     api-surface-map.json    <- machine-readable")


if __name__ == "__main__":
    main()
