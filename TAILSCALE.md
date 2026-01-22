# Tailscale VPN Integration

Route YouTube traffic through your home network to bypass datacenter IP restrictions and bot detection.

## Overview

YouTube applies stricter rate limiting and bot detection to datacenter IPs compared to residential IPs. By routing traffic through Tailscale VPN connected to your home network, downloads appear to originate from your home IP address.

## Architecture

```
Kubernetes Pod
├── Main Container (yt-playlist)
│   └── Downloads YouTube videos
└── Tailscale Sidecar
    └── Routes traffic through VPN to home network
    
Home Network
└── Tailscale Exit Node
    └── Forwards traffic to YouTube with residential IP
```

Both containers share the pod's network namespace, so all outbound traffic from the main container automatically goes through Tailscale.

## Setup

### 1. Configure Home Exit Node

On your home machine/server:

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Start Tailscale and advertise as exit node
sudo tailscale up --advertise-exit-node

# Verify status
tailscale status
```

In the Tailscale admin console (https://login.tailscale.com/admin/machines):
- Find your home machine
- Click "Review" under "Exit node" and approve

Note the machine's Tailscale hostname (e.g., `home-server`).

### 2. Generate Auth Key

Visit https://login.tailscale.com/admin/settings/keys and create an auth key:

- **Reusable**: Yes (allows pod restarts)
- **Ephemeral**: Yes (auto-cleanup when pod terminates)
- **Tags**: Optional (e.g., `tag:k8s`)
- **Expiration**: Set based on your security requirements

**Important**: Copy the key immediately - it won't be shown again.

### 3. Configure Kubernetes

**Option A: Direct Value (Testing Only)**

```yaml
# values.yaml
tailscale:
  enabled: true
  authKey: "tskey-auth-xxxxxxxxxxxxx-yyyyyyyyyyyyyyyyyyyy"
  exitNode: "home-server"  # Your home machine's Tailscale hostname
  acceptRoutes: true
```

**Option B: Kubernetes Secret (Recommended)**

```bash
# Create secret
kubectl create secret generic tailscale-auth \
  --from-literal=TS_AUTHKEY='tskey-auth-xxxxxxxxxxxxx-yyyyyyyyyyyyyyyyyyyy' \
  -n yt-playlist

# values.yaml
tailscale:
  enabled: true
  existingSecret: "tailscale-auth"
  exitNode: "home-server"
  acceptRoutes: true
```

**Option C: External Secrets Operator (GitOps)**

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: tailscale-auth
spec:
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: tailscale-auth
  data:
  - secretKey: TS_AUTHKEY
    remoteRef:
      key: yt-playlist/tailscale
      property: authKey
```

### 4. Deploy

```bash
helm upgrade --install yt-playlist ./helm/yt-playlist \
  --set tailscale.enabled=true \
  --set tailscale.existingSecret=tailscale-auth \
  --set tailscale.exitNode=home-server
```

### 5. Verify Connection

```bash
# Check pod status
kubectl get pods -n yt-playlist

# Check Tailscale connection
kubectl exec -it deployment/yt-playlist -c tailscale -- tailscale status

# Verify IP address (should show your home IP)
kubectl exec -it deployment/yt-playlist -c yt-playlist -- curl -s ifconfig.me

# Check routing
kubectl exec -it deployment/yt-playlist -c yt-playlist -- ip route
```

## Configuration Options

### Full values.yaml Example

```yaml
tailscale:
  enabled: true
  
  # Docker image
  image:
    repository: tailscale/tailscale
    tag: latest
    pullPolicy: IfNotPresent
  
  # Authentication
  authKey: ""  # Direct auth key (not recommended for production)
  existingSecret: "tailscale-auth"  # Kubernetes secret name
  
  # Exit node configuration
  exitNode: "home-server"  # Tailscale hostname or IP (100.x.y.z)
  acceptRoutes: true  # Accept subnet routes from exit node
  
  # Additional Tailscale arguments
  extraArgs:
    - "--advertise-tags=tag:k8s"
    - "--hostname=yt-playlist-pod"
  
  # Resource limits
  resources:
    requests:
      memory: "50Mi"
      cpu: "50m"
    limits:
      memory: "200Mi"
      cpu: "200m"
```

### Advanced: Route Only YouTube Traffic

By default, **all** traffic routes through Tailscale. To route only YouTube:

1. On home exit node, advertise specific routes:
```bash
sudo tailscale up --advertise-routes=142.250.0.0/15,172.217.0.0/16
```

2. In Kubernetes, add init container to set up selective routing:
```yaml
# Add to deployment.yaml
initContainers:
- name: setup-routes
  image: alpine:latest
  command:
  - sh
  - -c
  - |
    apk add --no-cache iproute2
    # Default route stays unchanged
    # Add specific routes for YouTube IPs through Tailscale
    ip route add 142.250.0.0/15 via $(tailscale ip -4)
    ip route add 172.217.0.0/16 via $(tailscale ip -4)
  securityContext:
    capabilities:
      add:
      - NET_ADMIN
```

## Troubleshooting

### Pod Stuck in Init

**Symptom**: Pod stays in `Init:0/1` state

**Cause**: Tailscale sidecar trying to start before auth key is available

**Solution**: Ensure secret exists before deploying:
```bash
kubectl get secret tailscale-auth -n yt-playlist
```

### Connection Fails

**Symptom**: `tailscale status` shows "Logged out"

**Causes**:
1. Invalid auth key - regenerate in admin console
2. Auth key expired - create new non-expiring key
3. Exit node not approved - check Tailscale admin console

**Debug**:
```bash
kubectl logs deployment/yt-playlist -c tailscale
```

### Exit Node Not Working

**Symptom**: Traffic not routing through home IP

**Check exit node status**:
```bash
# On home machine
sudo tailscale status
# Should show "offers exit node"

# In Kubernetes pod
kubectl exec -it deployment/yt-playlist -c tailscale -- \
  tailscale status
# Should show "Exit node: home-server"
```

**Verify IP forwarding** on home machine:
```bash
sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding
# Both should be 1
```

### Downloads Still Blocked

**Symptom**: YouTube still shows bot detection errors

**Verify traffic path**:
```bash
# Check public IP from pod
kubectl exec -it deployment/yt-playlist -c yt-playlist -- \
  curl -s ifconfig.me
# Should match your home IP (check at https://whatismyipaddress.com)

# Trace route to YouTube
kubectl exec -it deployment/yt-playlist -c yt-playlist -- \
  traceroute youtube.com
```

**Additional solutions**:
- Use cookies in addition to Tailscale (see COOKIES.md)
- Add delays between downloads (adjust `POLL_INTERVAL`)
- Use Android player client (already configured)

## Security Considerations

### Auth Key Management

- **Never commit auth keys** to Git
- Use Kubernetes secrets or external secret managers
- Rotate keys regularly (set expiration)
- Use ephemeral keys for automatic cleanup

### Network Security

- Tailscale adds NET_ADMIN capability to sidecar
- Main container runs as non-root (no additional privileges)
- All traffic encrypted via WireGuard (Tailscale's protocol)
- Exit node sees all pod traffic (trust your home network)

### Home Network Impact

- **Upload bandwidth**: Downloads limited by home upload speed
- **Always-on**: Home machine must be running 24/7
- **Power**: Consider power consumption and UPS for reliability
- **ISP limits**: May violate ToS if you have business restrictions

## Performance

### Bandwidth

- **Download speed**: Limited by home **upload** bandwidth
- Typical home: 20-50 Mbps upload
- Audio downloads: ~128-256 kbps (adequate)
- Video downloads: May be slow for 4K content

### Latency

- Added roundtrip through VPN: ~10-50ms typically
- Negligible impact for background downloads
- Initial connection: 2-5 seconds for Tailscale handshake

### Resource Usage

- **Tailscale sidecar**: 50-100 MB RAM, minimal CPU
- **WireGuard overhead**: ~100 bytes per packet
- **Total impact**: <5% additional resource consumption

## Alternatives

If Tailscale doesn't meet your needs:

1. **Run pod at home**: Deploy Kubernetes cluster at home
2. **Proxy service**: Use residential proxy service (paid)
3. **Cloud with residential IP**: Some cloud providers offer residential IPs
4. **Cookies only**: Use COOKIES.md method without VPN (may expire)

## References

- Tailscale Exit Nodes: https://tailscale.com/kb/1103/exit-nodes
- Tailscale Kubernetes: https://tailscale.com/kb/1185/kubernetes
- Subnet Routers: https://tailscale.com/kb/1019/subnets
- Auth Keys: https://tailscale.com/kb/1085/auth-keys
