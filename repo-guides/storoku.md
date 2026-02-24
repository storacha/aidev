# storoku

Go CLI tool for generating standardized AWS infrastructure deployments. Generates Terraform/OpenTofu scripts, GitHub Actions CI workflows, Makefiles, and Dockerfiles.

## Quick Reference

```bash
make build              # go build -o storoku ./cmd/storoku/main.go
make test               # go test ./...
make install            # go install ./...
storoku new <app-name>  # Create new project scaffold
storoku regen           # Regenerate from .storoku.json
```

## Structure

```
cmd/storoku/
  main.go               # CLI entry (urfave/cli v3, NOT Cobra)
  bucket.go, cache.go, database.go, queue.go, secret.go, topic.go,
  table.go, js.go, network.go, domain.go, didenv.go, port.go,
  cloudflare.go, writetocontainer.go  # One file per subcommand
template/               # Embedded Terraform, GHA, Dockerfile, Makefile templates
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `new` | Create new project scaffold |
| `regen` | Regenerate from existing .storoku.json |
| `bucket` | Add S3 bucket resource |
| `queue` | Add SQS queue resource |
| `database` | Add PostgreSQL database |
| `topic` | Add SNS topic |
| `secret` | Add secrets management |
| `cache` | Add Redis cache |
| `cloudflare` | Add Cloudflare integration |
| `domain` | Add domain configuration |
| `didenv` | Add DID environment variable |
| `port` | Configure port |
| `js` | Add JavaScript app (Next.js or custom) |
| `table` | Add DynamoDB table |

## Key Concepts

- **No UCAN**: This is infrastructure tooling, not a runtime service
- **State file**: `.storoku.json` tracks project config (app name, services, environment)
- **Template-based**: All output is generated from embedded Go templates
- **Minimal deps**: Uses urfave/cli v3 (not Cobra like other Go services)

## What Breaks If You Change Things Here

- Template changes affect all newly generated projects
- .storoku.json schema changes break existing projects on `regen`
- Self-contained tool — no blast radius to other services
