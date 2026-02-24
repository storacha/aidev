#!/usr/bin/env python3
"""
Infrastructure Scanner

Discovers from source code:
- Databases (DynamoDB, Postgres, D1, SQLite, Redis)
- Object storage (R2, S3 buckets)
- Queues & event systems (SQS, Cloudflare Queues)
- KV stores (Cloudflare KV, ElastiCache)
- Table/schema definitions (SST Table constructs, SQL migrations, DynamoDB schemas)
- Environment variables referencing infrastructure
- Terraform resources
- Wrangler bindings

Run: python3 aidev/scripts/scan_infra.py
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
CONFIG_PATH = OUTPUT_DIR / "repos-config.yaml"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "vendor", ".next",
             "coverage", "__pycache__", ".turbo", "target", ".pnpm"}

DROP_REPOS = {"resteep", "stubble", "dashboard-demo-clone"}


def read_file_safe(path, max_bytes=100000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)
    except:
        return ""


def should_skip(fpath):
    return any(s in fpath.parts for s in SKIP_DIRS)


# ── Scanners ────────────────────────────────────────────────

def scan_wrangler_toml(repo_path):
    """Extract all Cloudflare bindings from wrangler.toml files."""
    findings = []
    for wf in Path(repo_path).rglob("wrangler.toml"):
        if should_skip(wf):
            continue
        content = read_file_safe(str(wf))
        rel = str(wf.relative_to(repo_path))

        # R2 buckets
        for m in re.finditer(r'\[\[r2_buckets\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            binding = re.search(r'binding\s*=\s*"([^"]+)"', block)
            bucket = re.search(r'bucket_name\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "r2_bucket",
                "binding": binding.group(1) if binding else "?",
                "bucket_name": bucket.group(1) if bucket else "?",
                "file": rel,
            })

        # KV namespaces
        for m in re.finditer(r'\[\[kv_namespaces\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            binding = re.search(r'binding\s*=\s*"([^"]+)"', block)
            ns_id = re.search(r'id\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "kv_namespace",
                "binding": binding.group(1) if binding else "?",
                "id": ns_id.group(1) if ns_id else "?",
                "file": rel,
            })

        # D1 databases
        for m in re.finditer(r'\[\[d1_databases\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            binding = re.search(r'binding\s*=\s*"([^"]+)"', block)
            db_name = re.search(r'database_name\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "d1_database",
                "binding": binding.group(1) if binding else "?",
                "database_name": db_name.group(1) if db_name else "?",
                "file": rel,
            })

        # Durable objects
        for m in re.finditer(r'\[durable_objects\](.*?)(?=\n\[(?!\[)|\Z)', content, re.DOTALL):
            block = m.group(1)
            for dm in re.finditer(r'name\s*=\s*"([^"]+)"', block):
                findings.append({
                    "type": "durable_object",
                    "name": dm.group(1),
                    "file": rel,
                })

        # Queues (producers + consumers)
        for m in re.finditer(r'\[\[queues\.producers\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            binding = re.search(r'binding\s*=\s*"([^"]+)"', block)
            queue = re.search(r'queue\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "queue_producer",
                "binding": binding.group(1) if binding else "?",
                "queue": queue.group(1) if queue else "?",
                "file": rel,
            })

        for m in re.finditer(r'\[\[queues\.consumers\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            queue = re.search(r'queue\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "queue_consumer",
                "queue": queue.group(1) if queue else "?",
                "file": rel,
            })

        # Hyperdrive (Postgres proxy)
        for m in re.finditer(r'\[\[hyperdrive\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            binding = re.search(r'binding\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "hyperdrive",
                "binding": binding.group(1) if binding else "?",
                "file": rel,
                "note": "Cloudflare Hyperdrive = Postgres connection pooler",
            })

        # Analytics engine
        for m in re.finditer(r'\[\[analytics_engine_datasets\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            binding = re.search(r'binding\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "analytics_engine",
                "binding": binding.group(1) if binding else "?",
                "file": rel,
            })

        # Services (worker-to-worker bindings)
        for m in re.finditer(r'\[\[services\]\]\s*\n(.*?)(?=\n\[|\n\[\[|\Z)', content, re.DOTALL):
            block = m.group(1)
            binding = re.search(r'binding\s*=\s*"([^"]+)"', block)
            service = re.search(r'service\s*=\s*"([^"]+)"', block)
            findings.append({
                "type": "service_binding",
                "binding": binding.group(1) if binding else "?",
                "service": service.group(1) if service else "?",
                "file": rel,
            })

    return findings


def scan_sst_config(repo_path):
    """Scan SST/CDK stack definitions for DynamoDB tables, S3 buckets, SQS queues."""
    findings = []

    # SST config files and stack files
    patterns = ["sst.config.*", "stacks/**/*.ts", "stacks/**/*.js",
                "infra/**/*.ts", "infra/**/*.js"]

    for pattern in patterns:
        for fpath in Path(repo_path).rglob(pattern.replace("**/*", "*")):
            if should_skip(fpath) or fpath.suffix not in (".ts", ".js", ".mjs"):
                continue
            content = read_file_safe(str(fpath))
            rel = str(fpath.relative_to(repo_path))

            # DynamoDB tables
            for m in re.finditer(r'(?:new\s+)?(?:sst\.)?Table\s*\(\s*(?:stack\s*,\s*)?["\']([^"\']+)["\']', content):
                findings.append({"type": "dynamodb_table", "name": m.group(1), "file": rel})

            # Also look for Table with fields
            for m in re.finditer(r'Table\s*\([^)]*\)\s*\{[^}]*fields\s*:\s*\{([^}]+)\}', content, re.DOTALL):
                fields_block = m.group(1)
                fields = re.findall(r'(\w+)\s*:\s*["\'](\w+)["\']', fields_block)
                if fields:
                    findings.append({
                        "type": "dynamodb_schema",
                        "fields": {f: t for f, t in fields},
                        "file": rel,
                    })

            # S3 Buckets
            for m in re.finditer(r'(?:new\s+)?(?:sst\.)?Bucket\s*\(\s*(?:stack\s*,\s*)?["\']([^"\']+)["\']', content):
                findings.append({"type": "s3_bucket", "name": m.group(1), "file": rel})

            # SQS Queues
            for m in re.finditer(r'(?:new\s+)?(?:sst\.)?Queue\s*\(\s*(?:stack\s*,\s*)?["\']([^"\']+)["\']', content):
                findings.append({"type": "sqs_queue", "name": m.group(1), "file": rel})

            # RDS / Aurora
            for m in re.finditer(r'(?:new\s+)?(?:sst\.)?RDS\s*\(\s*(?:stack\s*,\s*)?["\']([^"\']+)["\']', content):
                findings.append({"type": "rds_database", "name": m.group(1), "file": rel})

            # EventBus
            for m in re.finditer(r'(?:new\s+)?(?:sst\.)?EventBus\s*\(\s*(?:stack\s*,\s*)?["\']([^"\']+)["\']', content):
                findings.append({"type": "event_bus", "name": m.group(1), "file": rel})

    return findings


def scan_terraform(repo_path):
    """Extract resources from Terraform files."""
    findings = []
    for tf in Path(repo_path).rglob("*.tf"):
        if should_skip(tf):
            continue
        content = read_file_safe(str(tf))
        rel = str(tf.relative_to(repo_path))

        for m in re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"', content):
            res_type = m.group(1)
            res_name = m.group(2)

            # Classify
            category = "other"
            if "dynamodb" in res_type: category = "dynamodb"
            elif "s3" in res_type: category = "s3"
            elif "sqs" in res_type: category = "sqs"
            elif "rds" in res_type or "aurora" in res_type: category = "rds"
            elif "elasticache" in res_type or "redis" in res_type: category = "redis"
            elif "ecs" in res_type: category = "ecs"
            elif "lambda" in res_type: category = "lambda"
            elif "cloudfront" in res_type: category = "cloudfront"
            elif "route53" in res_type: category = "dns"
            elif "iam" in res_type: category = "iam"
            elif "vpc" in res_type or "subnet" in res_type: category = "networking"

            findings.append({
                "type": f"terraform_{category}",
                "resource_type": res_type,
                "name": res_name,
                "file": rel,
            })

    return findings


def scan_sql_migrations(repo_path):
    """Find SQL migration files and extract table definitions."""
    findings = []

    for sql in Path(repo_path).rglob("*.sql"):
        if should_skip(sql):
            continue
        content = read_file_safe(str(sql))
        rel = str(sql.relative_to(repo_path))

        for m in re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?\s*\(([^;]+)\)', content, re.IGNORECASE | re.DOTALL):
            table_name = m.group(1)
            columns_block = m.group(2)
            columns = []
            for col in re.finditer(r'^\s*[`"\']?(\w+)[`"\']?\s+(\w+(?:\([^)]*\))?)', columns_block, re.MULTILINE):
                col_name = col.group(1)
                col_type = col.group(2)
                if col_name.upper() not in ("PRIMARY", "UNIQUE", "INDEX", "CONSTRAINT", "FOREIGN", "CHECK"):
                    columns.append({"name": col_name, "type": col_type})

            findings.append({
                "type": "sql_table",
                "table_name": table_name,
                "columns": columns,
                "file": rel,
            })

    return findings


def scan_go_database_usage(repo_path):
    """Find database drivers and connection patterns in Go code."""
    findings = []

    gomod = Path(repo_path) / "go.mod"
    if gomod.exists():
        content = read_file_safe(str(gomod))

        db_drivers = {
            "github.com/lib/pq": "postgres",
            "github.com/jackc/pgx": "postgres",
            "gorm.io/gorm": "orm (gorm)",
            "gorm.io/driver/postgres": "postgres (gorm)",
            "gorm.io/driver/sqlite": "sqlite (gorm)",
            "github.com/mattn/go-sqlite3": "sqlite",
            "go.mongodb.org/mongo-driver": "mongodb",
            "github.com/go-redis/redis": "redis",
            "github.com/redis/go-redis": "redis",
            "github.com/aws/aws-sdk-go": "aws_sdk",
            "github.com/aws/aws-sdk-go-v2": "aws_sdk_v2",
            "github.com/ipfs/go-datastore": "ipfs_datastore",
            "github.com/dgraph-io/badger": "badger",
            "go.etcd.io/bbolt": "bbolt",
            "github.com/cockroachdb/pebble": "pebble",
        }

        for driver, db_type in db_drivers.items():
            if driver in content:
                findings.append({
                    "type": f"go_driver_{db_type}",
                    "driver": driver,
                    "file": "go.mod",
                })

    return findings


def scan_js_database_usage(repo_path):
    """Find database packages in package.json files."""
    findings = []

    for pjson in Path(repo_path).rglob("package.json"):
        if should_skip(pjson) or "node_modules" in str(pjson):
            continue
        try:
            with open(pjson) as f:
                pkg = json.load(f)
        except:
            continue

        rel = str(pjson.relative_to(repo_path))
        all_deps = {}
        for key in ["dependencies", "devDependencies", "peerDependencies"]:
            all_deps.update(pkg.get(key, {}))

        db_packages = {
            "@aws-sdk/client-dynamodb": "dynamodb",
            "@aws-sdk/lib-dynamodb": "dynamodb",
            "@aws-sdk/client-s3": "s3",
            "@aws-sdk/client-sqs": "sqs",
            "pg": "postgres",
            "postgres": "postgres",
            "@neondatabase/serverless": "postgres_neon",
            "drizzle-orm": "orm (drizzle)",
            "kysely": "orm (kysely)",
            "prisma": "orm (prisma)",
            "@prisma/client": "orm (prisma)",
            "better-sqlite3": "sqlite",
            "sql.js": "sqlite",
            "ioredis": "redis",
            "redis": "redis",
            "@upstash/redis": "redis_upstash",
            "mongodb": "mongodb",
            "mongoose": "mongodb",
        }

        for dep_name, db_type in db_packages.items():
            if dep_name in all_deps:
                findings.append({
                    "type": f"js_dep_{db_type}",
                    "package": dep_name,
                    "version": all_deps[dep_name],
                    "file": rel,
                })

    return findings


def scan_env_vars(repo_path):
    """Find env vars that reference infrastructure."""
    findings = []
    infra_patterns = [
        (r'(DATABASE_URL|DB_URL|POSTGRES_URL|PG_URL)', "database_url"),
        (r'(REDIS_URL|REDIS_HOST|CACHE_URL)', "redis"),
        (r'(S3_BUCKET|AWS_BUCKET|BUCKET_NAME|R2_BUCKET)', "bucket"),
        (r'(SQS_QUEUE|QUEUE_URL)', "queue"),
        (r'(DYNAMO(?:DB)?_TABLE|TABLE_NAME)', "dynamodb"),
        (r'(MONGODB_URI|MONGO_URL)', "mongodb"),
        (r'(RPC_URL|ETH_RPC|WEB3_PROVIDER)', "blockchain_rpc"),
    ]

    for fpath in Path(repo_path).rglob("*"):
        if should_skip(fpath):
            continue
        if fpath.name in (".env", ".env.example", ".env.local", ".env.template",
                          ".dev.vars", ".dev.vars.example"):
            content = read_file_safe(str(fpath))
            rel = str(fpath.relative_to(repo_path))
            for pattern, category in infra_patterns:
                for m in re.finditer(pattern, content):
                    findings.append({
                        "type": f"env_{category}",
                        "var": m.group(1),
                        "file": rel,
                    })

    # Also scan wrangler.toml [vars]
    for wf in Path(repo_path).rglob("wrangler.toml"):
        if should_skip(wf):
            continue
        content = read_file_safe(str(wf))
        rel = str(wf.relative_to(repo_path))
        for pattern, category in infra_patterns:
            for m in re.finditer(pattern, content):
                findings.append({
                    "type": f"env_{category}",
                    "var": m.group(1),
                    "file": rel,
                })

    return findings


def scan_docker_compose(repo_path):
    """Extract services from docker-compose files."""
    findings = []
    for dc in Path(repo_path).rglob("docker-compose*"):
        if should_skip(dc):
            continue
        try:
            content = yaml.safe_load(read_file_safe(str(dc)))
            rel = str(dc.relative_to(repo_path))
            if content and "services" in content:
                for svc_name, svc_config in content["services"].items():
                    image = svc_config.get("image", "")
                    findings.append({
                        "type": "docker_service",
                        "name": svc_name,
                        "image": image,
                        "file": rel,
                    })
        except:
            continue

    return findings


# ── Main ────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  INFRASTRUCTURE SCANNER")
    print("  Discovering databases, storage, queues from source code")
    print("=" * 70)

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    analyze_list = [r for r in config.get("analyze", []) if r["name"] not in DROP_REPOS]

    all_findings = defaultdict(list)  # repo_name → [findings]
    infra_summary = defaultdict(lambda: defaultdict(set))  # category → {detail → set of repos}

    for i, ri in enumerate(analyze_list):
        name = ri["name"]
        rp = REPOS_DIR / name
        if not rp.exists():
            continue

        sys.stdout.write(f"\r   [{i+1}/{len(analyze_list)}] {name:40s}")
        sys.stdout.flush()

        repo_findings = []

        # Run all scanners
        repo_findings.extend(scan_wrangler_toml(rp))
        repo_findings.extend(scan_sst_config(rp))
        repo_findings.extend(scan_terraform(rp))
        repo_findings.extend(scan_sql_migrations(rp))
        repo_findings.extend(scan_go_database_usage(rp))
        repo_findings.extend(scan_js_database_usage(rp))
        repo_findings.extend(scan_env_vars(rp))
        repo_findings.extend(scan_docker_compose(rp))

        if repo_findings:
            all_findings[name] = repo_findings

        # Build summary
        for f in repo_findings:
            ftype = f["type"]
            if "dynamodb" in ftype:
                detail = f.get("name", f.get("var", "?"))
                infra_summary["DynamoDB"][detail].add(name)
            elif "s3" in ftype or "bucket" in ftype:
                detail = f.get("name", f.get("bucket_name", f.get("var", "?")))
                infra_summary["S3/R2 Buckets"][detail].add(name)
            elif "r2" in ftype:
                detail = f.get("bucket_name", f.get("binding", "?"))
                infra_summary["S3/R2 Buckets"][detail].add(name)
            elif "kv" in ftype:
                detail = f.get("binding", "?")
                infra_summary["KV Stores"][detail].add(name)
            elif "d1" in ftype:
                detail = f.get("database_name", f.get("binding", "?"))
                infra_summary["D1 Databases"][detail].add(name)
            elif "postgres" in ftype:
                detail = f.get("driver", f.get("package", f.get("var", "postgres")))
                infra_summary["PostgreSQL"][detail].add(name)
            elif "redis" in ftype:
                detail = f.get("driver", f.get("package", f.get("var", "redis")))
                infra_summary["Redis"][detail].add(name)
            elif "sqlite" in ftype:
                detail = f.get("driver", f.get("package", "sqlite"))
                infra_summary["SQLite"][detail].add(name)
            elif "sqs" in ftype or "queue" in ftype:
                detail = f.get("name", f.get("queue", f.get("var", "?")))
                infra_summary["Queues"][detail].add(name)
            elif "event_bus" in ftype:
                detail = f.get("name", "?")
                infra_summary["Event Bus"][detail].add(name)
            elif "durable_object" in ftype:
                detail = f.get("name", "?")
                infra_summary["Durable Objects"][detail].add(name)
            elif "analytics_engine" in ftype:
                detail = f.get("binding", "?")
                infra_summary["Analytics"][detail].add(name)
            elif "hyperdrive" in ftype:
                detail = f.get("binding", "?")
                infra_summary["Hyperdrive (Postgres)"][detail].add(name)
            elif "service_binding" in ftype:
                detail = f"{f.get('binding', '?')} → {f.get('service', '?')}"
                infra_summary["Service Bindings"][detail].add(name)
            elif "docker_service" in ftype:
                detail = f"{f.get('name', '?')} ({f.get('image', '?')})"
                infra_summary["Docker Services"][detail].add(name)
            elif "sql_table" in ftype:
                detail = f.get("table_name", "?")
                infra_summary["SQL Tables"][detail].add(name)
            elif "terraform" in ftype:
                detail = f"{f.get('resource_type', '?')}.{f.get('name', '?')}"
                cat = ftype.replace("terraform_", "Terraform: ")
                infra_summary[cat][detail].add(name)
            elif "ipfs_datastore" in ftype:
                infra_summary["IPFS Datastore"][f.get("driver", "go-datastore")].add(name)
            elif "badger" in ftype or "bbolt" in ftype or "pebble" in ftype:
                detail = f.get("driver", "?")
                infra_summary["Embedded KV Store"][detail].add(name)
            elif "aws_sdk" in ftype:
                infra_summary["AWS SDK"][f.get("driver", "?")].add(name)
            elif "blockchain_rpc" in ftype:
                infra_summary["Blockchain RPC"][f.get("var", "?")].add(name)
            elif "mongodb" in ftype:
                infra_summary["MongoDB"][f.get("driver", f.get("package", "?"))].add(name)

    print(f"\n\n   Found infrastructure in {len(all_findings)} repos\n")

    # ── Report ──────────────────────────────────────────────
    report = []
    report.append("=" * 70)
    report.append("  STORACHA INFRASTRUCTURE MAP")
    report.append("  Databases, storage, queues, and services discovered from code")
    report.append("=" * 70)

    for category in sorted(infra_summary.keys()):
        items = infra_summary[category]
        report.append(f"\n{'━' * 70}")
        report.append(f"  📊 {category}")
        report.append(f"{'━' * 70}")

        for detail, repos in sorted(items.items(), key=lambda x: len(x[1]), reverse=True):
            repos_str = ", ".join(sorted(repos))
            report.append(f"  {detail:45s} ← {repos_str}")

    # Per-repo detail
    report.append(f"\n\n{'=' * 70}")
    report.append("  PER-REPO INFRASTRUCTURE DETAIL")
    report.append("=" * 70)

    for name in sorted(all_findings.keys()):
        findings = all_findings[name]
        report.append(f"\n{'─' * 50}")
        report.append(f"  📦 {name}")
        report.append(f"{'─' * 50}")

        # Group by type
        by_type = defaultdict(list)
        for f in findings:
            by_type[f["type"]].append(f)

        for ftype, items in sorted(by_type.items()):
            report.append(f"  [{ftype}]")
            for item in items:
                parts = []
                for k, v in item.items():
                    if k in ("type",):
                        continue
                    if isinstance(v, list):
                        if v and isinstance(v[0], dict):
                            # columns
                            cols_str = ", ".join(f"{c['name']}:{c['type']}" for c in v[:8])
                            if len(v) > 8:
                                cols_str += f"... (+{len(v)-8} more)"
                            parts.append(f"{k}=[{cols_str}]")
                        else:
                            parts.append(f"{k}={v}")
                    else:
                        parts.append(f"{k}={v}")
                report.append(f"    {', '.join(parts)}")

    # SQL table schemas
    sql_tables = []
    for name, findings in all_findings.items():
        for f in findings:
            if f["type"] == "sql_table":
                sql_tables.append((name, f))

    if sql_tables:
        report.append(f"\n\n{'=' * 70}")
        report.append("  SQL TABLE SCHEMAS")
        report.append("=" * 70)
        for repo, table in sql_tables:
            report.append(f"\n  📦 {repo} / {table['file']}")
            report.append(f"  TABLE: {table['table_name']}")
            for col in table.get("columns", []):
                report.append(f"    {col['name']:30s} {col['type']}")

    print("\n".join(report))

    # ── Save ────────────────────────────────────────────────

    with open(OUTPUT_DIR / "infrastructure-map.txt", "w") as f:
        f.write("\n".join(report))

    # JSON output
    json_output = {
        "summary": {
            cat: {detail: sorted(repos) for detail, repos in items.items()}
            for cat, items in infra_summary.items()
        },
        "per_repo": {
            name: findings for name, findings in all_findings.items()
        },
        "sql_schemas": [
            {"repo": repo, **table} for repo, table in sql_tables
        ],
    }

    with open(OUTPUT_DIR / "infrastructure-map.json", "w") as f:
        json.dump(json_output, f, indent=2, default=list)

    print(f"\n\n{'=' * 70}")
    print(f"  DONE")
    print(f"{'=' * 70}")
    print(f"  Repos with infrastructure: {len(all_findings)}")
    print(f"  Categories found:          {len(infra_summary)}")
    print(f"  SQL table schemas:         {len(sql_tables)}")
    print(f"")
    print(f"  📁 {OUTPUT_DIR}/")
    print(f"     infrastructure-map.txt    ← human-readable")
    print(f"     infrastructure-map.json   ← machine-readable")


if __name__ == "__main__":
    main()
