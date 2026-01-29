# YouTube Playlist Manager Helm Chart

Kubernetes Helm chart for deploying the YouTube Playlist Manager application.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- OAuth2 credentials from Google Cloud Console (see main [OAUTH_SETUP.md](../../OAUTH_SETUP.md))

## Installation

### Quick Start

1. **Add playlist IDs and client secret:**

```bash
# Method 1: From Helm repository (once published)
helm repo add yt-playlist https://l4r5.github.io/yt-playlist/
helm repo update

helm install yt-playlist yt-playlist/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx... \
  --set playlists.donePlaylistId=PLyyyy... \
  --set-string clientSecretJson="{\"installed\":{\"client_id\":\"...\",\"client_secret\":\"...\",\"redirect_uris\":[\"http://localhost\"]}}"

# Method 2: From OCI registry
helm install yt-playlist oci://ghcr.io/l4r5/charts/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx... \
  --set playlists.donePlaylistId=PLyyyy... \
  --set-string clientSecretJson="{\"installed\":{...}}"

# Method 3: From source
helm install yt-playlist ./helm/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx... \
  --set playlists.donePlaylistId=PLyyyy... \
  --set-string clientSecretJson="{\"installed\":{...}}"
```

2. **Run initial authentication:**

```bash
# Enable auth job
helm upgrade yt-playlist ./helm/yt-playlist --set auth.enabled=true --reuse-values

# Port-forward for OAuth callback
kubectl port-forward svc/yt-playlist-auth 8080:8080

# Watch logs and complete OAuth in browser
kubectl logs -f job/yt-playlist-auth
```

3. **Extract and save token:**

```bash
# Get pod name and copy token
POD=$(kubectl get pod -l job-name=yt-playlist-auth -o jsonpath='{.items[0].metadata.name}')
kubectl cp $POD:/app/data/token.json ./token.json

# Update secret with token
kubectl create secret generic yt-playlist-credentials \
  --from-literal=CLIENT_SECRET_JSON='{"installed":{...}}' \
  --from-file=token.json=./token.json \
  --dry-run=client -o yaml | kubectl apply -f -
```

4. **Deploy main application:**

```bash
# Disable auth job and restart
helm upgrade yt-playlist ./helm/yt-playlist --set auth.enabled=false --reuse-values
```

## Configuration

### Required Values

| Parameter | Description | Example |
|-----------|-------------|---------|
| `playlists.todoPlaylistId` | Source playlist ID | `PLxxxx...` |
| `playlists.donePlaylistId` | Destination playlist ID | `PLyyyy...` |
| `playlists.failedPlaylistId` | Failed videos playlist (optional) | `PLzzzz...` |
| `clientSecretJson` | OAuth2 client secret (JSON string) | `{"installed":{...}}` |

### Optional Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Container image repository | `ghcr.io/l4r5/yt-playlist` |
| `image.tag` | Container image tag (defaults to Chart.AppVersion) | `""` |
| `download.mode` | Download mode (video/audio) | `video` |
| `download.pollInterval` | Polling interval in seconds | `300` |
| `download.retry.delay` | Initial retry delay in seconds | `60` |
| `download.retry.maxBackoff` | Max backoff time in seconds | `3600` |
| `download.retry.failureThreshold` | Attempts before moving to failed playlist | `10` |
| `email.enabled` | Enable email notifications | `false` |
| `email.recipients` | Comma-separated email addresses | `""` |
| `email.smtp.host` | SMTP server hostname | `smtp.gmail.com` |
| `email.smtp.port` | SMTP server port | `587` |
| `email.smtp.username` | SMTP username | `""` |
| `email.smtp.password` | SMTP password (app-specific for Gmail) | `""` |
| `logging.level` | Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL) | `INFO` |
| `logging.file` | Log file path | `/tmp/playlist_manager.log` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | Storage size for downloads | `50Gi` |
| `persistence.storageClass` | Storage class name | `""` (default) |
| `persistence.retain` | Keep PVC after uninstall | `false` |
| `resources.limits.cpu` | CPU limit | `1000m` |
| `resources.limits.memory` | Memory limit | `1Gi` |
| `securityContext.runAsUser` | User ID to run container as | `1000` |
| `securityContext.runAsGroup` | Group ID to run container as | `1000` |
| `podSecurityContext.fsGroup` | Group ID for volume ownership | `1000` |
| `auth.enabled` | Enable authentication job | `false` |
| `service.enabled` | Enable Service resource | `false` |
| `serviceMonitor.enabled` | Enable Prometheus ServiceMonitor | `false` |
| `serviceMonitor.interval` | Metrics scrape interval | `30s` |
| `ingress.enabled` | Enable Ingress resource | `false` |
| `ingress.className` | Ingress class name | `""` |

### Full Configuration Example

Create a `custom-values.yaml`:

```yaml
# Image configuration
  failedPlaylistId: PLzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz  # Optional: for permanently failed videos

# OAuth2 credentials (REQUIRED for first deployment)
clientSecretJson: '{"installed":{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}'

# Download settings
download:
  mode: video  # or 'audio'
  pollInterval: 300
  retry:
    delay: 60  # Initial retry delay in seconds
    maxBackoff: 3600  # Cap at 1 hour
    failureThreshold: 10  # Attempts before moving to failed playlist

# Email notifications (optional)
email:
  enabled: true
  recipients: admin@example.com,alerts@example.com
  smtp:
    host: smtp.gmail.com
    port: 587
    username: notifications@gmail.com
    password: your-app-specific-password  # Use --set-string for sensitive data
    from: YT Playlist <notifications@gmail.com>Lxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  donePlaylistId: PLyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

# OAuth2 credentials (REQUIRED for first deployment)
clientSecretJson: '{"installed":{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}'

# Download settings
download:
  mode: video  # or 'audio'
  pollInterval: 300

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: /tmp/playlist_manager.log

# Storage
persistence:
  enabled: true
  size: 100Gi
  storageClass: fast-ssd
  retain: true  # Keep data after uninstall (recommended for production)

# Resources
resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 200m
    memory: 512Mi

# Initial authentication
auth:
  enabled: true  # Enable for first-time setup

# Monitoring (optional - requires Prometheus Operator)
serviceMonitor:
  enabled: false
service:
  enabled: false
```

Install with custom values:

```bash
helm install yt-playlist ./helm/yt-playlist -f custom-values.yaml
```

## Data Persistence and Retention

By default, the PVC for downloaded videos is deleted when you uninstall the Helm release. For production deployments, you may want to preserve the data:

```yaml
persistence:
  enabled: true
  size: 100Gi
  retain: true  # Keep PVC after helm uninstall
```

**Use cases for retention:**
- **Upgrades**: Preserve downloaded videos during application upgrades
- **Disaster recovery**: Maintain data even if the application is removed
- **Cost optimization**: Avoid re-downloading large video files

**Using subPath for shared storage:**

When multiple applications or environments share the same PVC:

```yaml
persistence:
  enabled: true
  existingClaim: shared-videos-pvc
  subPath: production  # Each environment gets its own subdirectory
```

Common subPath patterns:
- **Environment separation**: `dev`, `staging`, `production`
- **Multi-tenant**: `tenant-a`, `tenant-b`, `customer-123`
- **Application instances**: `playlist-manager-1`, `playlist-manager-2`

**Reusing a retained PVC:**

```bash
# After uninstalling with retain=true, the PVC still exists
kubectl get pvc yt-playlist-downloads

# Reinstall and reuse the PVC
helm install yt-playlist ./helm/yt-playlist \
  --set persistence.existingClaim=yt-playlist-downloads
```

**Manual cleanup:**

```bash
# Delete the retained PVC when no longer needed
kubectl delete pvc yt-playlist-downloads
```

## Authentication Methods

### Method 1: Web UI (Recommended) - No Command Line Required!

Best for: Easy, user-friendly authentication

```bash
# 1. Deploy with auth UI enabled
helm install yt-playlist ./helm/yt-playlist \
  --set auth.ui.enabled=true \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'

# 2. Access the web interface
kubectl port-forward svc/yt-playlist-auth-ui 5000:5000
# Open http://localhost:5000 in your browser

# 3. Click "Authenticate with Google" and grant permissions
# Token is automatically saved!

# 4. Disable auth UI and start main app
helm upgrade yt-playlist ./helm/yt-playlist \
  --set auth.ui.enabled=false \
  --reuse-values
```

**With Ingress (for production):**
```bash
helm install yt-playlist ./helm/yt-playlist \
  --set auth.ui.enabled=true \
  --set auth.ui.ingress.enabled=true \
  --set auth.ui.ingress.hosts[0].host=auth.example.com \
  --set auth.ui.redirectUri=https://auth.example.com/callback \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'

# Open https://auth.example.com and authenticate
```

**Important:** 
- Set `auth.ui.redirectUri` to match your ingress URL + `/callback`
- Add the same URI (`https://auth.example.com/callback`) to "Authorized redirect URIs" in Google Cloud Console OAuth client settings
- Without `redirectUri` set, the app auto-detects the URL (works for port-forward, may fail with ingress)

### Method 2: Authentication Job (Command Line)

Best for: First-time setup in Kubernetes (requires kubectl)

1. Deploy with `auth.enabled=true`
2. Port-forward the auth service
3. Complete OAuth in browser
4. Extract token from job pod
5. Create secret with token
6. Redeploy with `auth.enabled=false`

See [Quick Start](#quick-start) for detailed steps.

### Method 3: Pre-authenticate Locally

Best for: When you already have a token.json file

```bash
# 1. Authenticate locally (outside Kubernetes)
python manage_playlist.py

# 2. Create secret from local token
kubectl create secret generic yt-playlist-credentials \
  --from-literal=CLIENT_SECRET_JSON='{"installed":{...}}' \
  --from-file=token.json=./token.json

# 3. Deploy application
helm install yt-playlist ./helm/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy
```

## Web UI Screenshots

The authentication web UI provides a clean, modern interface:

- **Landing Page**: Click "Authenticate with Google" button
- **OAuth Flow**: Standard Google sign-in and permission grant
- **Success Page**: Confirmation that token was saved to Kubernetes
- **No Command Line**: Everything works through the browser

See [auth-ui/README.md](../../auth-ui/README.md) for more details.

## Monitoring

```bash
# View application logs
kubectl logs -f deployment/yt-playlist

# Enable debug logging (restart required)
helm upgrade yt-playlist ./helm/yt-playlist \
  --set logging.level=DEBUG \
  --reuse-values
kubectl rollout restart deployment/yt-playlist

# Check pod status
kubectl get pods -l app.kubernetes.io/name=yt-playlist

# Access downloads
kubectl exec -it deployment/yt-playlist -- ls -lh /app/downloads

# Check persistent volume
kubectl get pvc
```

## Upgrading

```bash
# Update values
helm upgrade yt-playlist ./helm/yt-playlist \
  --set download.pollInterval=600 \
  --reuse-values

# Update to new image version
helm upgrade yt-playlist ./helm/yt-playlist \
  --set image.tag=v1.2.0 \
  --reuse-values
```

## Uninstallation

```bash
# Delete release
helm uninstall yt-playlist

# Delete PVC manually if retention is enabled (persistence.retain=true)
kubectl delete pvc yt-playlist-downloads
```

**Data Retention:**
- When `persistence.retain=false` (default): PVC is automatically deleted with the release
- When `persistence.retain=true`: PVC persists after uninstall, preserving downloaded videos
  - Useful for production deployments where data should survive upgrades
  - Must manually delete PVC if you want to remove the data
  - Can reuse the PVC by setting `persistence.existingClaim` in a new deployment

## Troubleshooting

### Error: failed parsing --set data

**Problem:** `Error: failed parsing --set data: key "}" has no value`

**Cause:** Incorrect quote escaping. Single quotes don't allow escaping in bash.

**Solution:** Use double quotes on the outside with escaped inner quotes:
```bash
# ✅ Correct - double quotes outside, escape inner quotes
--set-string clientSecretJson="{\"installed\":{\"client_id\":\"...\",\"client_secret\":\"...\"}}"

# ❌ Wrong - single quotes + escaping doesn't work (backslashes are literal)
--set-string clientSecretJson='{\"installed\":{\"client_id\":\"...\"}}'

# ✅ Best - use values file (strongly recommended for JSON)
helm install yt-playlist ./helm/yt-playlist -f my-values.yaml
```

**In values file (use single quotes, no escaping needed):**
```yaml
clientSecretJson: '{"installed":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost"]}}'
```

### OAuth Authentication Fails

```bash
# Check auth job logs
kubectl logs job/yt-playlist-auth

# Verify secret exists
kubectl get secret yt-playlist-credentials -o yaml

# Check port-forward is active
kubectl get svc yt-playlist-auth
```

### Application Won't Start

```bash
# Check pod events
kubectl describe pod -l app.kubernetes.io/name=yt-playlist

# Verify configuration
kubectl get configmap yt-playlist -o yaml

# Check secret contains token
kubectl get secret yt-playlist-credentials -o jsonpath='{.data.token\.json}' | base64 -d
```

### No Videos Being Downloaded

```bash
# Check logs for errors
kubectl logs -f deployment/yt-playlist

# Verify playlist IDs
kubectl get configmap yt-playlist -o jsonpath='{.data.TODO_PLAYLIST_ID}'

# Check token is valid (look for auth errors in logs)
```

## Advanced Usage

### Running Multiple Instances

Deploy separate releases for different playlists:

```bash
helm install yt-playlist-set1 ./helm/yt-playlist \
  --set playlists.todoPlaylistId=PLaaaa... \
  --set playlists.donePlaylistId=PLbbbb...

helm install yt-playlist-set2 ./helm/yt-playlist \
  --set playlists.todoPlaylistId=PLcccc... \
  --set playlists.donePlaylistId=PLdddd...
```

### Custom Storage Classes

```bash
helm install yt-playlist ./helm/yt-playlist \
  --set persistence.storageClass=fast-ssd \
  --set persistence.size=200Gi
```

### Custom User/Group IDs

The container runs as UID 1000 by default. To use different IDs:

```bash
# Method 1: Using fsGroup (recommended for Kubernetes)
# Kubernetes automatically changes volume ownership to fsGroup
helm install yt-playlist ./helm/yt-playlist \
  --set securityContext.runAsUser=5000 \
  --set securityContext.runAsGroup=5000 \
  --set podSecurityContext.fsGroup=5000

# Method 2: Pre-create PVC with correct ownership
kubectl exec -it <pod> -- chown -R 5000:5000 /app/downloads /app/data
```

**How it works:**
- **Image default**: Container built with UID/GID 1000
- **Kubernetes fsGroup**: Automatically changes mounted volume ownership
- **Application files**: Readable by any user (application code in `/app`)
- **Volume mounts**: `/app/downloads` and `/app/data` inherit fsGroup permissions

**Note**: When changing UIDs, ensure fsGroup matches to allow volume access.

### Monitoring with Prometheus

The application exposes Prometheus metrics on port 8080. Enable ServiceMonitor for Prometheus Operator:

```bash
helm install yt-playlist ./helm/yt-playlist \
  --set serviceMonitor.enabled=true \
  --set serviceMonitor.additionalLabels.prometheus=kube-prometheus
```

**Available metrics:**
- Video processing statistics (success/failure rates)
- Download counts and status
- YouTube API call tracking
- **API quota usage** (used and remaining)
- TODO playlist size
- Processing duration histograms

Access metrics directly:
```bash
kubectl port-forward svc/yt-playlist 8080:8080
curl http://localhost:8080/metrics
```

### Ingress Configuration

Expose via Ingress (for future web UI or API):

```bash
helm install yt-playlist ./helm/yt-playlist \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=yt-playlist.example.com \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix
```

With TLS:

```bash
helm install yt-playlist ./helm/yt-playlist \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=yt-playlist.example.com \
  --set ingress.tls[0].secretName=yt-playlist-tls \
  --set ingress.tls[0].hosts[0]=yt-playlist.example.com \
  --set-string ingress.annotations."cert-manager\.io/cluster-issuer"=letsencrypt-prod
```

**Note**: The application is a background daemon without HTTP endpoints. Ingress is provided for future use cases (web UI, API, webhooks).

### Resource Constraints

```bash
helm install yt-playlist ./helm/yt-playlist \
  --set resources.limits.cpu=2000m \
  --set resources.limits.memory=4Gi \
  --set resources.requests.cpu=500m \
  --set resources.requests.memory=1Gi
```
