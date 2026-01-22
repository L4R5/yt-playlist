# ArgoCD Deployment

Deploy the YouTube Playlist Manager using ArgoCD for GitOps-style continuous delivery.

## Quick Start

### Prerequisites

Create a Kubernetes secret with your OAuth2 credentials:

```bash
# Create the secret with your OAuth2 client credentials
kubectl create secret generic yt-playlist-oauth-credentials \
  --namespace=yt-playlist \
  --from-literal=CLIENT_SECRET_JSON='{"installed":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost"]}}'

# Or from a file
kubectl create secret generic yt-playlist-oauth-credentials \
  --namespace=yt-playlist \
  --from-file=CLIENT_SECRET_JSON=./client_secret.json
```

### Deployment

1. **Apply the Application manifest:**

```bash
kubectl apply -f argocd/application.yaml
```

2. **Configure your credentials:**

Edit the `application.yaml` file and set:
- `playlists.todoPlaylistId`
- `playlists.donePlaylistId`
- `existingSecret` (reference to the secret created above)

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

## Secrets Management

### Method 1: Using Existing Secret (Recommended)

Create a Kubernetes secret before deploying:

```bash
kubectl create namespace yt-playlist

# Base64 encode your OAuth2 credentials
CLIENT_SECRET='{"installed":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost"]}}'

kubectl create secret generic yt-playlist-oauth-credentials \
  --namespace=yt-playlist \
  --from-literal=CLIENT_SECRET_JSON="$CLIENT_SECRET"
```

Then reference it in your Application:

```yaml
helm:
  values: |
    existingSecret: yt-playlist-oauth-credentials
    playlists:
      todoPlaylistId: "PLxxxx..."
      donePlaylistId: "PLyyyy..."
```

### Method 2: Inline Credentials (Not Recommended)

Only use for testing. Credentials will be stored in Git/ArgoCD:

```yaml
helm:
  values: |
    clientSecretJson: '{"installed":{...}}'
    playlists:
      todoPlaylistId: "PLxxxx..."
      donePlaylistId: "PLyyyy..."
```

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
      
      existingSecret: yt-playlist-oauth-credentials
      
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
            className: nginx
            annotations:
              cert-manager.io/cluster-issuer: letsencrypt-prod
              nginx.ingress.kubernetes.io/ssl-redirect: "true"
              nginx.ingress.kubernetes.io/affinity: "cookie"
            hosts:
              - host: auth.yt-playlist.example.com
                paths:
                  - path: /
                    pathType: Prefix
            tls:
              - secretName: yt-playlist-auth-tls
                hosts:
                  - auth.yt-playlist.example.com
      
      metrics:
        enabled: true
        serviceMonitor:
          enabled: true
          interval: 30s
```

### TLS with cert-manager

Using cert-manager for automatic certificate management:

```yaml
# 1. Install cert-manager (if not already installed)
# kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# 2. Create ClusterIssuer for Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx

# 3. Configure in ArgoCD Application
auth:
  ui:
    ingress:
      enabled: true
      className: nginx
      annotations:
        cert-manager.io/cluster-issuer: letsencrypt-prod
      hosts:
        - host: auth.yt-playlist.example.com
          paths:
            - path: /
              pathType: Prefix
      tls:
        - secretName: yt-playlist-auth-tls  # Auto-created by cert-manager
          hosts:
            - auth.yt-playlist.example.com
```

### TLS with Manual Certificates

Using pre-existing certificates:

```bash
# Create TLS secret from certificate files
kubectl create secret tls yt-playlist-auth-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  --namespace=yt-playlist

# Then configure ingress
auth:
  ui:
    ingress:
      enabled: true
      className: nginx
      hosts:
        - host: auth.yt-playlist.example.com
          paths:
            - path: /
              pathType: Prefix
      tls:
        - secretName: yt-playlist-auth-tls
          hosts:
            - auth.yt-playlist.example.com
```

### TLS with Wildcard Certificates

Using a single wildcard certificate for multiple subdomains:

```yaml
auth:
  ui:
    ingress:
      enabled: true
      className: nginx
      annotations:
        cert-manager.io/cluster-issuer: letsencrypt-prod-dns  # DNS challenge required for wildcards
      hosts:
        - host: auth.yt-playlist.example.com
          paths:
            - path: /
              pathType: Prefix
      tls:
        - secretName: wildcard-yt-playlist-tls
          hosts:
            - auth.yt-playlist.example.com
            - app.yt-playlist.example.com
            - "*.yt-playlist.example.com"
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
