# GitLab Container Registry Cleanup Configuration

This directory contains scripts for managing GitLab Container Registry via the GitLab API.

## configure-registry-cleanup.sh

Configures GitLab's built-in Container Registry cleanup policies using the `glab` CLI.

### What It Does

Sets up automatic cleanup of old container images based on:
- **Age**: Delete images older than a specified number of days
- **Count**: Keep only the N newest images per repository
- **Schedule**: Runs daily at midnight UTC

### Default Configuration

```bash
CLEANUP_ENABLED=true
CLEANUP_CADENCE=1d          # Run daily
CLEANUP_KEEP_N=10           # Keep 10 newest tags
CLEANUP_OLDER_THAN=30d      # Delete tags older than 30 days
CLEANUP_NAME_REGEX='.*'     # Apply to all tags
```

### Usage

**Local execution (requires authenticated glab):**
```bash
./scripts/configure-registry-cleanup.sh
```

**Customize via environment variables:**
```bash
CLEANUP_KEEP_N=20 CLEANUP_OLDER_THAN=60d ./scripts/configure-registry-cleanup.sh
```

**CI/CD execution:**
```yaml
setup-cleanup-policy:
  stage: setup
  image: alpine:latest
  before_script:
    - apk add --no-cache curl
    - curl -fsSL https://gitlab.com/gitlab-org/cli/-/releases/permalink/latest/downloads/glab_Linux_x86_64.tar.gz | tar -xz -C /usr/local/bin glab
  script:
    - ./scripts/configure-registry-cleanup.sh
  rules:
    - if: '$CI_PIPELINE_SOURCE == "web"'
      when: manual
```

### Benefits Over Manual CI/CD Cleanup

**Built-in policy (this script):**
- ✅ Runs automatically daily without CI/CD minutes
- ✅ GitLab-managed, no custom scripts to maintain
- ✅ Visible in UI: Settings → Packages & Registries → Cleanup policies
- ✅ Applies consistent rules across all repositories

**Manual CI/CD job (previous approach):**
- ❌ Requires manual triggering or consumes CI/CD minutes
- ❌ Custom bash scripts to maintain and debug
- ❌ Must handle pagination, rate limiting, errors
- ❌ No UI visibility

### Verification

Check current policy:
```bash
glab api /projects/l4r51%2Fyt-playlist | jq '.container_expiration_policy'
```

View in GitLab UI:
```
Settings → Packages & Registries → Container Registry → Cleanup policies
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLEANUP_ENABLED` | `true` | Enable/disable automatic cleanup |
| `CLEANUP_CADENCE` | `1d` | How often to run (1d, 7d, 14d, 1month, 3month) |
| `CLEANUP_KEEP_N` | `10` | Number of newest tags to keep per repository |
| `CLEANUP_OLDER_THAN` | `30d` | Delete tags older than (7d, 14d, 30d, 60d, 90d) |
| `CLEANUP_NAME_REGEX` | `'.*'` | Regex matching tag names to consider for deletion |
| `CI_PROJECT_PATH` | `l4r51/yt-playlist` | GitLab project path (auto-set in CI/CD) |
| `CI_PROJECT_ID` | - | Numeric project ID (auto-set in CI/CD) |

### GitLab API Documentation

- [Container Registry API](https://docs.gitlab.com/ee/api/container_registry.html)
- [Cleanup Policies](https://docs.gitlab.com/ee/user/packages/container_registry/reduce_container_registry_storage.html#cleanup-policy)
