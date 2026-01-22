# ArgoCD Deployment

Deploy the YouTube Playlist Manager using ArgoCD for GitOps-style continuous delivery.

## Quick Start

1. **Apply the Application manifest:**

```bash
kubectl apply -f argocd/application.yaml
```

2. **Configure your credentials:**

Edit the `application.yaml` file and set:
- `playlists.todoPlaylistId`
- `playlists.donePlaylistId`
- `clientSecretJson` (OAuth2 credentials)

3. **Initial OAuth Authentication:**

The application will deploy with the auth UI enabled. Port-forward to complete authentication:

```bash
kubectl port-forward -n yt-playlist svc/yt-playlist-auth-ui 5000:5000
```

Open http://localhost:5000 and complete OAuth flow.

4. **Disable Auth UI:**

After authentication is complete, update `application.yaml`:

```yaml
auth:
  ui:
    enabled: false
```

ArgoCD will automatically sync and disable the auth UI.

## Configuration

### Basic Example

Minimal configuration for getting started:

```yaml
source:
  repoURL: https://l4r5.github.io/yt-playlist/
  chart: yt-playlist
  targetRevision: 1.0.6
  helm:
    values: |
      playlists:
        todoPlaylistId: "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        donePlaylistId: "PLyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
      clientSecretJson: '{"installed":{...}}'
```

### Advanced Example

With external access, monitoring, and custom storage:

```yaml
source:
  helm:
    values: |
      playlists:
        todoPlaylistId: "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        donePlaylistId: "PLyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
      
      clientSecretJson: '{"installed":{...}}'
      
      downloadMode: video
      pollInterval: 300
      
      persistence:
        enabled: true
        size: 50Gi
        storageClass: fast-ssd
      
      auth:
        ui:
          enabled: true
          ingress:
            enabled: true
            host: yt-auth.example.com
            className: nginx
            tls:
              - secretName: yt-auth-tls
                hosts:
                  - yt-auth.example.com
      
      metrics:
        enabled: true
        serviceMonitor:
          enabled: true
          interval: 30s
```

## Sync Policies

The provided template uses **automated sync** with:
- **Prune**: Removes resources deleted from Git
- **Self-heal**: Reverts manual changes in cluster
- **Create namespace**: Automatically creates the target namespace

To disable automated sync:

```yaml
syncPolicy:
  automated: null  # Manual sync only
```

## Multi-Environment Setup

Deploy to different environments using ArgoCD ApplicationSets:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: yt-playlist
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
            namespace: yt-playlist-dev
            todoPlaylist: PLdev...
            donePlaylist: PLdev...
          - env: prod
            namespace: yt-playlist-prod
            todoPlaylist: PLprod...
            donePlaylist: PLprod...
  template:
    metadata:
      name: 'yt-playlist-{{env}}'
    spec:
      project: default
      source:
        repoURL: https://l4r5.github.io/yt-playlist/
        chart: yt-playlist
        targetRevision: 1.0.6
        helm:
          values: |
            playlists:
              todoPlaylistId: "{{todoPlaylist}}"
              donePlaylistId: "{{donePlaylist}}"
            clientSecretJson: '{"installed":{...}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

## Monitoring Sync Status

```bash
# Watch sync status
kubectl get application -n argocd yt-playlist -w

# View detailed sync info
argocd app get yt-playlist

# Manual sync
argocd app sync yt-playlist

# View logs
kubectl logs -n yt-playlist -l app.kubernetes.io/name=yt-playlist -f
```

## Updating Chart Version

To upgrade to a new chart version:

1. Update `targetRevision` in `application.yaml`:

```yaml
targetRevision: 1.0.7  # New version
```

2. Commit and push (if using Git-based sync)
3. ArgoCD will automatically detect and sync the new version

Or manually sync:

```bash
argocd app sync yt-playlist
```

## Troubleshooting

### Application Not Syncing

```bash
# Check application health
argocd app get yt-playlist

# Force refresh
argocd app get yt-playlist --refresh

# View events
kubectl get events -n yt-playlist --sort-by='.lastTimestamp'
```

### Chart Not Found

Ensure the Helm repository is accessible:

```bash
helm repo add yt-playlist https://l4r5.github.io/yt-playlist/
helm repo update
helm search repo yt-playlist
```

### OAuth Authentication Issues

Check auth UI logs:

```bash
kubectl logs -n yt-playlist -l app=yt-playlist-auth-ui
```

## Security Best Practices

### 1. Use Sealed Secrets

Instead of storing credentials in Git:

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
echo -n '{"installed":{...}}' | kubectl create secret generic yt-playlist-client-secret \
  --dry-run=client \
  --from-file=client_secret.json=/dev/stdin \
  -n yt-playlist \
  -o yaml | kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml

# Reference in ArgoCD Application
clientSecret:
  enabled: true
  existingSecret: yt-playlist-client-secret
```

### 2. Use External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: yt-playlist-credentials
  namespace: yt-playlist
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: yt-playlist-client-secret
  data:
    - secretKey: client_secret.json
      remoteRef:
        key: secret/yt-playlist/oauth
        property: client_secret
```

## Resources

- [Main Documentation](../README.md)
- [Helm Chart Documentation](../helm/yt-playlist/README.md)
- [Helm Repository Guide](../HELM_REPOSITORY.md)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
