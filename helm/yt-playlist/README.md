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
helm install yt-playlist ./helm/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx... \
  --set playlists.donePlaylistId=PLyyyy... \
  --set clientSecretJson='{"installed":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost"]}}'
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
| `clientSecretJson` | OAuth2 client secret (JSON string) | `{"installed":{...}}` |

### Optional Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Container image repository | `ghcr.io/l4r5/yt-playlist` |
| `image.tag` | Container image tag | `latest` |
| `download.mode` | Download mode (video/audio) | `video` |
| `download.pollInterval` | Polling interval in seconds | `300` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | Storage size for downloads | `50Gi` |
| `persistence.storageClass` | Storage class name | `""` (default) |
| `resources.limits.cpu` | CPU limit | `1000m` |
| `resources.limits.memory` | Memory limit | `1Gi` |
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
image:
  repository: ghcr.io/l4r5/yt-playlist
  tag: latest
  pullPolicy: Always

# Playlists (REQUIRED)
playlists:
  todoPlaylistId: PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  donePlaylistId: PLyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

# OAuth2 credentials (REQUIRED for first deployment)
clientSecretJson: '{"installed":{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}'

# Download settings
download:
  mode: video  # or 'audio'
  pollInterval: 300

# Storage
persistence:
  enabled: true
  size: 100Gi
  storageClass: fast-ssd

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
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'

# Open https://auth.example.com and authenticate
```

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
# Delete release (keeps PVC)
helm uninstall yt-playlist

# Delete PVC if needed
kubectl delete pvc yt-playlist-downloads
```

## Troubleshooting

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
