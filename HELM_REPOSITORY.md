# Helm Chart Repository

This repository publishes Helm charts automatically via GitHub Actions.

## Usage

### Method 1: GitHub Pages Repository (Recommended)

Add the Helm repository:

```bash
helm repo add yt-playlist https://l4r5.github.io/yt-playlist/
helm repo update
```

Install the chart:

```bash
helm install yt-playlist yt-playlist/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'
```

Search available versions:

```bash
helm search repo yt-playlist
```

### Method 2: OCI Registry (GitHub Container Registry)

Install directly from OCI registry:

```bash
helm install yt-playlist oci://ghcr.io/l4r5/charts/yt-playlist --version 1.0.0 \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'
```

List available versions:

```bash
helm show chart oci://ghcr.io/l4r5/charts/yt-playlist
```

### Method 3: From Source

Clone the repository and install locally:

```bash
git clone https://github.com/L4R5/yt-playlist.git
cd yt-playlist
helm install yt-playlist ./helm/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'
```

## Chart Versions

The chart follows semantic versioning. Each release creates:
- A GitHub Release with packaged chart (`.tgz`)
- An entry in the Helm chart repository index
- An OCI artifact in GitHub Container Registry

View all releases: https://github.com/L4R5/yt-playlist/releases

## Updating

```bash
# Using Helm repository
helm repo update
helm upgrade yt-playlist yt-playlist/yt-playlist

# Using OCI registry
helm upgrade yt-playlist oci://ghcr.io/l4r5/charts/yt-playlist --version <new-version>
```

## Chart Documentation

See [helm/yt-playlist/README.md](helm/yt-playlist/README.md) for detailed configuration options.

## Development

### Linting

```bash
helm lint helm/yt-playlist
```

### Testing

```bash
# Render templates
helm template test helm/yt-playlist --debug

# Dry-run install
helm install test helm/yt-playlist --dry-run --debug
```

### Versioning

To publish a new chart version:

1. Update `version` in `helm/yt-playlist/Chart.yaml`
2. Update `appVersion` if application version changed
3. Commit and push to main branch
4. GitHub Actions will automatically create a release

Example:

```yaml
# helm/yt-playlist/Chart.yaml
apiVersion: v2
name: yt-playlist
version: 1.1.0  # Increment this
appVersion: "latest"
```

```bash
git add helm/yt-playlist/Chart.yaml
git commit -m "chore: bump chart version to 1.1.0"
git push
```

The workflow will:
- Package the chart
- Create a GitHub Release tagged `yt-playlist-1.1.0`
- Update the Helm repository index on the `gh-pages` branch
- Push OCI artifact to ghcr.io

**After the first workflow run**, enable GitHub Pages manually:
1. Go to: https://github.com/L4R5/yt-playlist/settings/pages
2. Under "Source", select: **Deploy from a branch**
3. Select branch: **gh-pages** and path: **/ (root)**
4. Click **Save**

This only needs to be done once - subsequent chart releases will automatically update.

## Repository Structure

```
yt-playlist/
├── helm/
│   └── yt-playlist/          # Helm chart
│       ├── Chart.yaml        # Chart metadata (version here!)
│       ├── values.yaml       # Default configuration
│       ├── templates/        # Kubernetes manifests
│       └── README.md         # Chart documentation
└── .github/
    └── workflows/
        └── helm-release.yml  # Automated publishing
```

## Troubleshooting

### Chart Not Appearing in Repository

1. Check GitHub Actions workflow status
2. **Enable GitHub Pages** if this is the first run:
   - Go to Settings → Pages
   - Source: Deploy from a branch → gh-pages → / (root)
3. Wait a few minutes for GitHub Pages to deploy
4. Run `helm repo update`

### OCI Push Failed

Ensure GitHub Container Registry permissions are set:
- Repository Settings → Actions → General
- Workflow permissions: "Read and write permissions"

### Chart Validation Failed

```bash
# Validate chart locally
helm lint helm/yt-playlist

# Check for syntax errors
helm template test helm/yt-playlist --debug
```
