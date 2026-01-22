# OAuth Authentication Web UI

Simple, user-friendly web interface for completing YouTube OAuth2 authentication in Kubernetes without command-line tools.

## Features

- 🌐 **Web-based authentication** - No kubectl commands required
- 🔐 **Automatic secret management** - Token saved directly to Kubernetes
- 🎨 **Beautiful UI** - Clean, modern interface
- 🔒 **Secure** - Runs with minimal RBAC permissions
- ☁️ **Cloud-ready** - Works with any Kubernetes cluster

## Usage

### Quick Start

Deploy the authentication UI:

```bash
helm install yt-playlist ./helm/yt-playlist \
  --set auth.ui.enabled=true \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'
```

Access the UI:

```bash
# Option 1: Port-forward (local access)
kubectl port-forward svc/yt-playlist-auth-ui 5000:5000
# Open http://localhost:5000

# Option 2: Ingress (public access)
helm upgrade yt-playlist ./helm/yt-playlist \
  --set auth.ui.ingress.enabled=true \
  --set auth.ui.ingress.hosts[0].host=auth.example.com \
  --reuse-values
```

### Authentication Flow

1. **Open the Web UI** - Navigate to the auth UI URL
2. **Click "Authenticate with Google"** - Button redirects to Google OAuth
3. **Grant Permissions** - Allow YouTube playlist management
4. **Success!** - Token automatically saved to Kubernetes secret
5. **Deploy Main App** - Disable auth UI and start the playlist manager

### After Authentication

Once authenticated, disable the auth UI and deploy the main application:

```bash
helm upgrade yt-playlist ./helm/yt-playlist \
  --set auth.ui.enabled=false \
  --reuse-values
```

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Browser   │─────▶│   Auth UI    │─────▶│   Google    │
│             │◀─────│   (Flask)    │◀─────│   OAuth2    │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Kubernetes  │
                     │   Secret     │
                     └──────────────┘
```

### Components

- **Flask Web App** - Lightweight Python web server
- **OAuth2 Flow** - Handles Google authentication
- **Kubernetes Client** - Saves token to secret automatically
- **RBAC** - Minimal permissions (secret create/update only)

## Configuration

### values.yaml

```yaml
auth:
  ui:
    enabled: true
    image:
      repository: ghcr.io/l4r5/yt-playlist-auth-ui
      tag: latest
    service:
      type: ClusterIP  # or LoadBalancer for cloud
    ingress:
      enabled: false
      hosts:
        - host: auth.example.com
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLIENT_SECRET_JSON` | OAuth2 client secret (JSON) | - |
| `SECRET_NAME` | Kubernetes secret name | `yt-playlist-credentials` |
| `NAMESPACE` | Kubernetes namespace | `default` |
| `PORT` | HTTP server port | `5000` |

## Deployment Options

### 1. Port-Forward (Development)

```bash
kubectl port-forward svc/yt-playlist-auth-ui 5000:5000
# Access at http://localhost:5000
```

### 2. NodePort (On-premises)

```bash
helm upgrade yt-playlist ./helm/yt-playlist \
  --set auth.ui.service.type=NodePort \
  --set auth.ui.service.nodePort=30500 \
  --reuse-values

# Access at http://<node-ip>:30500
```

### 3. LoadBalancer (Cloud)

```bash
helm upgrade yt-playlist ./helm/yt-playlist \
  --set auth.ui.service.type=LoadBalancer \
  --reuse-values

# Get external IP
kubectl get svc yt-playlist-auth-ui
```

### 4. Ingress (Production)

```bash
helm upgrade yt-playlist ./helm/yt-playlist \
  --set auth.ui.ingress.enabled=true \
  --set auth.ui.ingress.className=nginx \
  --set auth.ui.ingress.hosts[0].host=auth.example.com \
  --set-string auth.ui.ingress.annotations."cert-manager\.io/cluster-issuer"=letsencrypt-prod \
  --reuse-values

# Access at https://auth.example.com
```

## Security

### RBAC Permissions

The auth UI runs with minimal permissions:

```yaml
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "create", "update", "patch"]
  resourceNames: ["yt-playlist-credentials"]
```

### Container Security

- Runs as non-root user (UID 1000)
- Read-only root filesystem possible
- No privilege escalation
- Drops all capabilities

### Secret Management

- Tokens stored in Kubernetes secrets (encrypted at rest)
- No tokens logged or persisted to disk
- Secret scoped to namespace

## Troubleshooting

### Auth UI Not Accessible

```bash
# Check if pod is running
kubectl get pods -l app.kubernetes.io/component=auth-ui

# Check logs
kubectl logs -l app.kubernetes.io/component=auth-ui

# Check service
kubectl get svc yt-playlist-auth-ui
```

### OAuth Callback Error

Ensure redirect URI in Google Cloud Console includes your auth UI URL:
- Development: `http://localhost:5000/callback`
- Production: `https://auth.example.com/callback`

### Secret Not Created

```bash
# Check RBAC permissions
kubectl get rolebinding yt-playlist-auth-ui

# Check service account
kubectl get sa yt-playlist-auth-ui

# Verify secret exists
kubectl get secret yt-playlist-credentials
```

## Comparison with CLI Method

| Aspect | Web UI | CLI (kubectl) |
|--------|--------|---------------|
| User Experience | ✅ Click button | ❌ Complex commands |
| Secret Management | ✅ Automatic | ❌ Manual |
| Prerequisites | ✅ Browser only | ❌ kubectl, base64 |
| Error Handling | ✅ User-friendly | ❌ Cryptic errors |
| Accessibility | ✅ Non-technical users | ❌ Requires CLI skills |

## Building Custom Image

If you want to build your own auth UI image:

```bash
cd auth-ui
docker build -t your-registry/yt-playlist-auth-ui:latest .
docker push your-registry/yt-playlist-auth-ui:latest

# Use in Helm
helm install yt-playlist ./helm/yt-playlist \
  --set auth.ui.image.repository=your-registry/yt-playlist-auth-ui \
  --set auth.ui.image.tag=latest
```

## License

Same as parent project - Created 100% by AI (GitHub Copilot & Claude).
