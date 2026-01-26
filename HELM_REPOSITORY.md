# Helm Chart Repository

This repository publishes Helm charts automatically via GitHub Actions (GitHub Pages) and GitLab CI/CD (GitLab Pages).

> **Important**: GitHub Releases in this repository are **Helm chart versions**, not application versions. The chart version (e.g., `yt-playlist-1.0.4`) refers to the Kubernetes deployment configuration, not the YouTube playlist manager application itself. The application version is specified in the chart's `appVersion` field.

## Usage

### Method 1: GitHub Pages Repository

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

### Method 2: GitLab Pages Repository

Add the Helm repository:

```bash
helm repo add yt-playlist-gitlab https://l4r51.gitlab.io/yt-playlist/
helm repo update
```

Install the chart:

```bash
helm install yt-playlist yt-playlist-gitlab/yt-playlist \
  --set playlists.todoPlaylistId=PLxxxx \
  --set playlists.donePlaylistId=PLyyyy \
  --set clientSecretJson='{"installed":{...}}'
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

## Repository Comparison

| Feature | GitHub Pages | GitLab Pages |
|---------|--------------|--------------|
| **URL** | https://l4r5.github.io/yt-playlist/ | https://l4r51.gitlab.io/yt-playlist/ |
| **Primary** | ✅ Yes | Alternative |
| **Updates** | On version tag push | On main branch helm/** changes |
| **Releases** | GitHub Releases UI | No release UI |
| **Availability** | Public repository | Public repository |

Both repositories contain identical charts. Use either based on your preference or network access.

Search available versions:

```bash
helm search repo yt-playlist
```

## Chart Versions

The Helm chart follows semantic versioning independently from the application:

- **Chart Version** (e.g., `1.0.4`): Kubernetes deployment configuration changes
- **App Version** (e.g., `latest`): The actual YouTube playlist manager Docker image

Each Helm chart release creates:
- A GitHub Release tagged with chart version (e.g., `yt-playlist-1.0.4`)
- A packaged chart file (`.tgz`)
- An updated Helm repository index

**Note**: Chart version bumps occur when Kubernetes manifests, values, or deployment configuration change. Application updates use Docker image tags and do not require chart version changes.

View all chart releases: https://github.com/L4R5/yt-playlist/releases

## Updating

```bash
helm repo update
helm upgrade yt-playlist yt-playlist/yt-playlist
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

To publish a new **Helm chart** release:

1. Update `version` in `helm/yt-playlist/Chart.yaml` (increment for configuration changes)
2. Update `appVersion` only if the application Docker image version changed
3. Commit and push to main branch
4. GitHub Actions will automatically create a **chart release**

**When to bump chart version:**
- Changed Kubernetes manifests (Deployment, Service, etc.)
- Modified default values in `values.yaml`
- Added/removed configuration options
- Changed deployment behavior

**When to bump appVersion only:**
- Application code changes (managed via Docker image tags)
- No chart/configuration changes needed

Example:

```yaml
# helm/yt-playlist/Chart.yaml
apiVersion: v2
name: yt-playlist
version: 1.1.0      # Chart/configuration version
appVersion: "latest" # Application Docker image tag
```

```bash
git add helm/yt-playlist/Chart.yaml
git commit -m "chore: bump chart version to 1.1.0"
git push
```

The workflow will:
- Package the Helm chart
- Create a GitHub Release tagged `yt-playlist-1.1.0` **(chart version, not app version)**
- Update the Helm repository index on the `gh-pages` branch

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

### Chart Validation Failed

```bash
# Validate chart locally
helm lint helm/yt-playlist

# Check for syntax errors
helm template test helm/yt-playlist --debug
```
