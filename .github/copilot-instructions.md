# YouTube Playlist Manager - AI Coding Instructions

## Project Overview
Single-file Python application that monitors a YouTube "todo" playlist, downloads videos using yt-dlp, and moves completed videos to a "done" playlist. Designed to run as a daemon with Docker/Kubernetes deployment support.

## Local Development

### Running the Application Locally
**Always use the virtual environment** when running the app locally:
```bash
cd /home/lamerke/git/yt-playlist
source venv/bin/activate  # Always activate venv first
python manage_playlist.py  # Run application
```

This ensures:
- Correct Python dependencies are used
- No conflicts with system packages
- Consistent execution environment
## Architecture

### Single Module Design
**manage_playlist.py** (737 lines) - Complete application in one file:
- `PlaylistManager` class encapsulates all YouTube API operations
- OAuth2 authentication with automatic token refresh
- Video processing pipeline: download → add to done → remove from todo
- Daemon mode with configurable polling interval
- Structured logging to both console and file (`playlist_manager.log`)

### Key Design Decisions
- **OAuth2 over API keys**: Required for playlist modification (insert/delete operations)
- **Single-file architecture**: Simplifies deployment and Docker containerization
- **Graceful degradation**: Video downloads succeed even if playlist moves fail
- **No database**: Stateless - relies on YouTube API as source of truth

## Critical Workflows

### Initial Setup & Authentication
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Get OAuth2 credentials from Google Cloud Console (see OAUTH_SETUP.md)
# 4. Save as client_secret.json

# 5. Configure environment
cp .env.example .env
# Edit TODO_PLAYLIST_ID and DONE_PLAYLIST_ID

# 6. First run - browser opens for OAuth2 authentication
python manage_playlist.py
# Grants: https://www.googleapis.com/auth/youtube scope
# Creates: token.json (auto-refreshed on expiry)
```

### Docker Deployment Pattern

**Option 1: Using CLIENT_SECRET_JSON (recommended for secrets management)**
```bash
mkdir -p data downloads

# Set client secret as environment variable
export CLIENT_SECRET_JSON='{"installed":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost"]}}'

# Or add to .env file
echo 'CLIENT_SECRET_JSON={"installed":{...}}' >> .env

# First run - authentication
docker-compose run --rm --service-ports yt-playlist
```

**Option 2: Using file mount (traditional)**
```bash
mkdir -p data downloads
cp client_secret.json data/

# First run - authentication (requires port forwarding)
docker-compose run --rm --service-ports yt-playlist
# Opens browser at localhost:8080/... for OAuth flow

# After token.json exists, run as daemon
docker-compose up -d

# Volumes mounted:
# - ./data → /app/data (credentials + tokens)
# - ./downloads → /app/downloads (video files)
```

### CLI Arguments
- `--daemon`: Continuous mode with POLL_INTERVAL sleeps (default: 5 seconds)
- `--download-path PATH`: Override DOWNLOAD_PATH env var
- `--poll-interval SECONDS`: Override POLL_INTERVAL env var
- No args = run once and exit

## Environment Variables

From `.env.example`:
```bash
# OAuth2 credentials - use ONE of these methods:
CLIENT_SECRET_JSON={"installed":{...}}  # Option 1: JSON string (Docker/CI/CD)
CREDENTIALS_FILE=client_secret.json     # Option 2: File path (default)

# Required configuration
TODO_PLAYLIST_ID=PLxxxx...           # Source playlist (required)
DONE_PLAYLIST_ID=PLyyyy...           # Destination playlist (required)

# Optional configuration
DOWNLOAD_PATH=./downloads            # Video storage directory
POLL_INTERVAL=5                      # Seconds between checks (daemon mode)
DOWNLOAD_MODE=video                  # 'video' or 'audio' (M4A format)
METRICS_PORT=8080                    # Prometheus metrics HTTP port
DAILY_QUOTA_LIMIT=10000              # YouTube API daily quota limit
LOG_LEVEL=INFO                       # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=/tmp/playlist_manager.log   # Log file path (writable location for containers)

# YouTube cookies (bot detection bypass) - use ONE method:
COOKIES_FILE=./cookies.txt           # Path to Netscape cookies.txt file
COOKIES_CONTENT="..."                # Cookies content as string (for secrets)
```

**Note**: `token.json` is auto-generated on first authentication and stored in the working directory. Advanced users can override with `TOKEN_FILE` environment variable if needed.

**Client Secret Methods**:
- **CLIENT_SECRET_JSON**: Full JSON content as string (useful for Docker secrets, CI/CD)
- **CREDENTIALS_FILE**: Path to JSON file (default: `client_secret.json`)
- Priority: Checks `CLIENT_SECRET_JSON` first, then falls back to file

**Critical**: `POLL_INTERVAL=5` in production `.env` but `POLL_INTERVAL=300` in README examples - Docker uses env file value

## YouTube API Quota Management

**Daily Quota**: 10,000 units (default)
**Per-video cost**: ~101 units
- `playlistItems().list()`: 1 unit (paginated, maxResults=50)
- `playlistItems().insert()`: 50 units (add to done)
- `playlistItems().delete()`: 50 units (remove from todo)

**Processing capacity**: ~99 videos/day with default quota

**Quota tracking**: Implemented via `QuotaTracker` class
- Automatically resets at midnight Pacific Time (YouTube's quota reset time)
- Tracks all API operations and their costs
- Exposes metrics via Prometheus (`api_quota_used`, `api_quota_remaining`)
- Logs quota usage at start/end of each processing cycle

## Prometheus Metrics

The application exposes metrics on port 8080 (configurable via `METRICS_PORT`):

**Counters:**
- `yt_playlist_videos_processed_total{status}` - Videos processed (success/download_failed/api_failed)
- `yt_playlist_downloads_total{status}` - Downloads attempted (success/failed)
- `yt_playlist_api_calls_total{operation}` - API calls (list/insert/delete)

**Gauges:**
- `yt_playlist_api_quota_used` - Estimated quota units used today
- `yt_playlist_api_quota_remaining` - Estimated quota units remaining
- `yt_playlist_todo_videos` - Current videos in TODO playlist
- `yt_playlist_last_processing_timestamp` - Unix timestamp of last cycle

**Histograms:**
- `yt_playlist_processing_duration_seconds{operation}` - Operation duration (download/api_call/full_cycle)

Access metrics: `http://localhost:8080/metrics`

### Quota Optimization Opportunities
Current implementation is stateless - potential optimizations if quota becomes constrained:

1. **Local state tracking**: Store processed video IDs in a JSON file
   - Skip `playlistItems().list()` call if no new videos expected
   - Only query playlist when file modification indicates new additions

2. **Conditional fetching**: Compare playlist item count before full fetch
   - `playlists().list()` returns `contentDetails.itemCount` (1 unit)
   - Only fetch items if count changed since last check

3. **Partial pagination**: Stop fetching after finding last known video
   - Requires ordered playlist assumption (newest first)
   - Saves quota on large playlists

4. **Batch operations**: Group playlist modifications
   - Current: insert + delete per video (~100 units each)
   - Alternative: Batch inserts, then batch deletes (same cost, fewer API calls)

**Trade-off**: Caching adds state management complexity vs. stateless simplicity. Current quota limit (99 videos/day) sufficient for most use cases.

## yt-dlp Configuration

Mode selection via `DOWNLOAD_MODE` env var:
```python
# Video mode (default)
'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

# Audio mode (original format, typically M4A)
'format': 'bestaudio[ext=m4a]/bestaudio'
```

**Output template**: `'%(title)s.%(ext)s'` (no subdirectories)
**Retry logic**: 10 retries for download + 10 for fragments
**Certificate validation**: Disabled (`nocheckcertificate: True`)

## OAuth2 Token Lifecycle

### Token Files
- `client_secret.json`: OAuth2 client credentials (manually downloaded, never auto-generated)
- `token.json`: Access/refresh tokens (auto-generated on first auth, auto-refreshed)
  - Default filename hardcoded, can be overridden with `TOKEN_FILE` env var if needed

### Authentication Flow
1. **First run**: No `token.json` exists
   - Opens browser at `http://localhost:PORT/`
   - User grants YouTube permissions
   - Saves credentials to `token.json`

2. **Subsequent runs**: `token.json` exists and valid
   - Loads credentials from file (line 81)
   - Validates token with `creds.valid` check (line 85)
   - Silent execution, no browser interaction

3. **Token expiry**: Access token expired but refresh token valid
   - Auto-refreshes via `creds.refresh(Request())` (line 88)
   - Updates `token.json` with new access token (line 103)
   - No user interaction required

4. **Token invalidation**: Refresh token revoked or corrupted
   - Re-runs full OAuth flow via `InstalledAppFlow` (line 97)
   - Opens browser for re-authentication

### Debugging Authentication Issues
```bash
# Force re-authentication
rm token.json
python manage_playlist.py  # Browser will open

# Check token validity
python -c "from google.oauth2.credentials import Credentials; \
  c = Credentials.from_authorized_user_file('token.json'); \
  print(f'Valid: {c.valid}, Expired: {c.expired}')"

# Common errors:
# - "invalid_grant" → Delete token.json and re-authenticate
# - "redirect_uri_mismatch" → Check Google Cloud Console OAuth settings
# - Port already in use → OAuth flow picks random port automatically
```

## Error Handling Patterns

### Authentication Failures
- Missing `client_secret.json` → FileNotFoundError with setup instructions (line 92)
- Expired token → Auto-refresh via `creds.refresh(Request())` (line 88)
- Invalid token → Re-runs OAuth flow via `InstalledAppFlow` (line 97)

### API Errors
- HTTP 404 on playlist fetch → Logs 3 possible reasons (see lines 164-171)
- Playlist modification fails → Warning logged, continues processing
- Uses `googleapiclient.errors.HttpError` with status code inspection

### Download Failures
- yt-dlp exception → Logged, video stays in todo playlist for retry
- Process continues to next video (no abort on single failure)

## Code Conventions

### Logging Strategy
- **INFO**: Progress updates, successful operations
- **DEBUG**: API request/response details (currently commented out)
- **WARNING**: Non-fatal issues (e.g., playlist move fails after download)
- **ERROR**: Failures requiring attention
- Dual output: stdout + `playlist_manager.log` file

### Type Hints
Used for function signatures:
```python
def get_playlist_videos(self, playlist_id: str) -> List[Dict[str, str]]:
```
Dictionary structure: `{'playlist_item_id': str, 'video_id': str, 'title': str, 'video_url': str}`

### Configuration Validation
`validate_config()` function (line 371) checks:
- File existence: `CREDENTIALS_FILE`
- Required env vars: `TODO_PLAYLIST_ID`, `DONE_PLAYLIST_ID`
- Exits with status 1 if validation fails

## Docker Build & CI/CD

### CI/CD Platform Synchronization
**CRITICAL**: This project supports both GitHub Actions and GitLab CI/CD with **identical trigger rules**.
- **When modifying workflows**: Update BOTH `.github/workflows/` AND `.gitlab-ci.yml`
- **Trigger consistency**: Main branch pushes, version tags (v*.*.*), manual runs only
- **No PR/MR builds**: Conserves CI/CD minutes, prevents redundant builds

### Multi-platform Build
GitHub Actions workflow (`.github/workflows/docker-build.yml`):
- Builds for `linux/amd64` and `linux/arm64`
- Pushes to `ghcr.io/l4r5/yt-playlist` on main branch
- Tags: branch name, semver, SHA
- Separate workflow for auth-ui: `.github/workflows/docker-build-auth-ui.yml`
- **Triggers**: Main branch, version tags, manual (NO pull requests)

GitLab CI/CD pipeline (`.gitlab-ci.yml`):
- Same multi-platform build strategy
- Pushes to `registry.gitlab.com/<namespace>/<project>`
- **Triggers**: Main branch, version tags, manual (NO merge requests)
- See `GITLAB_CI.md` for complete documentation

### Alpine-based Image
- Base: `python:3.13-alpine`
- System deps: `ffmpeg`, `gcc`, `musl-dev`, `linux-headers` (for compilation)
- Entrypoint: `python manage_playlist.py`
- Default CMD: `--daemon`

### Automated Cleanup
`.github/workflows/cleanup-old-releases.yml` - Triggered after Docker builds:
- **Purpose**: Prevent GHCR storage bloat from CI/CD builds
- **Retention**: Keeps 10 latest versions (configurable via `keep_count`)
- **Two-phase cleanup**:
  1. Deletes ALL untagged images (orphaned layers from cancelled builds)
  2. Deletes old tagged releases beyond retention limit
- **Dual API support**: Handles both organization and user-owned packages
- **Releases + Tags**: Cleans GitHub releases AND associated Git tags
- **Matrix strategy**: Processes both `yt-playlist` and `yt-playlist-auth-ui` images
- **Trigger**: Runs after docker-build workflows complete on main branch

## Kubernetes Deployment

### Helm Chart Structure
**helm/yt-playlist/** - Complete chart with 14 templates:
- **deployment.yaml**: Main application with metrics, liveness/readiness probes
- **pvc.yaml**: Persistent storage for downloaded videos with retention policy
- **auth-ui.yaml**: Flask web UI (Deployment, Service, RBAC) for OAuth authentication
- **auth-job.yaml**: CLI authentication fallback (runs once, requires port-forward)
- **secret.yaml**: OAuth credentials (supports existingSecret for external secret management)
- **servicemonitor.yaml**: Prometheus Operator integration for metrics
- **ingress.yaml**: TLS-enabled ingress with cert-manager annotations
- **configmap.yaml, service.yaml, serviceaccount.yaml**: Standard Kubernetes resources
- **_helpers.tpl, NOTES.txt**: Helm templating utilities

### PVC Retention Policy
**Critical feature for production**: Data persistence beyond application lifecycle

```yaml
# values.yaml
persistence:
  enabled: true
  size: 100Gi
  retain: true  # Adds helm.sh/resource-policy: keep annotation
  subPath: ""  # Optional: mount subdirectory within PVC
```

**Behavior:**
- `retain: false` (default): PVC deleted with `helm uninstall`
- `retain: true`: PVC survives uninstall, preserving downloaded videos
  - Useful for upgrades, disaster recovery, cost optimization
  - Reuse with `persistence.existingClaim` in new deployment
  - Manual cleanup: `kubectl delete pvc yt-playlist-downloads`

**SubPath for shared storage:**
- `subPath: ""` (default): Mount entire PVC volume
- `subPath: "production"`: Mount only the `/production` subdirectory
  - Enables multiple apps/environments to share one PVC
  - Common patterns: environment names, tenant IDs, instance identifiers
  - Example: `dev`, `staging`, `production`, `tenant-a`, `customer-123`

**Implementation:** Conditional annotation in pvc.yaml:
```yaml
{{- if .Values.persistence.retain }}
annotations:
  helm.sh/resource-policy: keep
{{- end }}
```

### Authentication Methods
1. **Web UI (recommended)**: Flask app on port 5000, browser-based OAuth
   - Deployment with RBAC (ServiceAccount, Role, RoleBinding)
   - Automatically saves token to Kubernetes secret
   - Multi-arch images: ghcr.io/l4r5/yt-playlist-auth-ui
   - Location: `auth-ui/` directory with Dockerfile and Flask app

2. **Authentication Job**: One-time CLI authentication
   - Requires `kubectl port-forward` for OAuth callback
   - Job pod extracts token after user grants permissions

3. **Pre-authenticate locally**: Generate token.json outside cluster
   - Create Kubernetes secret from local file
   - Deploy with existing token

### External Secrets Integration
**existingSecret parameter** for GitOps workflows:
```yaml
# values.yaml
existingSecret: "yt-oauth-credentials"  # References external secret
clientSecretJson: ""  # Leave empty when using existingSecret
```

Supports:
- Sealed Secrets (Bitnami)
- External Secrets Operator (AWS Secrets Manager, Vault, GCP Secret Manager)
- Manual secret creation

### Helm Repository Publishing
**GitHub Pages**: https://l4r5.github.io/yt-playlist/
- Automated via `.github/workflows/helm-release.yml`
- Triggered on version tag push (e.g., `v1.0.6`)
- Chart-releaser-action packages and publishes to gh-pages branch
- Post-processing step updates release notes to clarify chart vs app versions

**Usage:**
```bash
helm repo add yt-playlist https://l4r5.github.io/yt-playlist/
helm install my-release yt-playlist/yt-playlist
```

### Helm Testing
`.github/workflows/helm-test.yml` - Automated chart validation:
- **helm-unittest**: Unit tests with snapshot comparisons (`helm/yt-playlist/tests/`)
- **helm template**: Validates successful rendering without syntax errors
- **helm lint**: Schema validation and best practices checks
- Runs on PR and main branch changes to `helm/**` paths
- Test coverage includes: deployment configs, secrets, PVC, ingress, service monitors, auth-ui

**Running tests locally:**
```bash
helm plugin install https://github.com/helm-unittest/helm-unittest
cd helm/yt-playlist
helm unittest .  # Run all tests
helm unittest -f 'tests/deployment_test.yaml' .  # Specific test
helm unittest -v .  # Verbose output
```

### ArgoCD GitOps Deployment
**argocd/** directory contains:
- **application.yaml**: Single-environment deployment
- **applicationset.yaml**: Multi-environment (dev/staging/prod) with generator
- Production defaults: `retain: true`, TLS ingress, existingSecret

**TLS Configuration** (3 approaches):
1. Automatic with cert-manager + Let's Encrypt
2. Manual certificates via Kubernetes secret
3. Wildcard certificates for multiple domains

## Testing

### Helm Chart Tests
**Location**: `helm/yt-playlist/tests/` - Unit tests using helm-unittest plugin

**Test coverage** (8 test files with snapshots):
- `deployment_test.yaml`: Main app deployment, Tailscale sidecar, cookies, resource limits
- `auth-ui_test.yaml`: Flask OAuth UI deployment, service, RBAC
- `secret_test.yaml`: OAuth credential handling, existingSecret support
- `pvc_test.yaml`: Persistent volume retention policy, subPath mounting
- `service_test.yaml`: Metrics service configuration
- `servicemonitor_test.yaml`: Prometheus Operator integration
- `ingress_test.yaml`: TLS configuration, cert-manager annotations

**Running tests:**
```bash
cd helm/yt-playlist
helm unittest .  # Requires: helm plugin install https://github.com/helm-unittest/helm-unittest
```

### Python Application Tests
**Status**: Not implemented
- No pytest or unit test framework currently in codebase
- Would require mocking `googleapiclient` and `yt_dlp` modules
- `manage_playlist.py` has no test coverage

## YouTube Cookies for Bot Detection

**Feature**: Bypass YouTube's bot detection by authenticating with browser cookies
**Documentation**: See `COOKIES.md` for complete setup guide

### Cookie Format Normalization
- App automatically converts spaces to tabs (Netscape format requirement)
- Both `COOKIES_FILE` (path) and `COOKIES_CONTENT` (string) supported
- Implemented in lines 361-395 of `manage_playlist.py`
- Creates temporary file from `COOKIES_CONTENT` at runtime

### Export Methods
1. Browser extensions (Get cookies.txt LOCALLY for Chrome, cookies.txt for Firefox)
2. yt-dlp: `yt-dlp --cookies-from-browser chrome --cookies cookies.txt https://youtube.com/`

### Kubernetes Integration
```bash
# Store cookies in secret
kubectl create secret generic yt-playlist-cookies \
  --from-literal=cookies="$(cat cookies.txt)"

# Helm configuration
helm upgrade yt-playlist yt-playlist/yt-playlist \
  --set-string download.cookiesContent="$(cat cookies.txt)"
```

## Tailscale VPN Integration

**Purpose**: Route traffic through home network to use residential IP instead of datacenter IP
**Documentation**: See `TAILSCALE.md` for setup guide

### Architecture
- Sidecar container pattern in Kubernetes
- Shares pod network namespace with main app
- Requires exit node on home network
- Auth key management via secrets

### Configuration
```yaml
# helm/yt-playlist/values.yaml
tailscale:
  enabled: true
  authKey: "tskey-auth-xxx"  # Or use existingSecret
  exitNode: "home-server"    # Tailscale hostname
  acceptRoutes: true
```

## Common Debugging Commands
```bash
# Docker
docker-compose logs -f
docker-compose run --rm yt-playlist env

# Kubernetes
kubectl logs -f deployment/yt-playlist
kubectl get pvc  # Check persistent volume claims
kubectl describe pod <pod-name>
helm status yt-playlist
helm get values yt-playlist  # Show effective configuration

# Cookies troubleshooting
kubectl exec deployment/yt-playlist -- ls -la /app/cookies/
kubectl exec deployment/yt-playlist -- env | grep COOKIES

# Tailscale status (if enabled)
kubectl exec deployment/yt-playlist -c tailscale -- tailscale status

# Manual authentication test
python manage_playlist.py  # Should open browser

# Check API quota usage (Google Cloud Console)
# Navigate to: APIs & Services → Dashboard → YouTube Data API v3
```
