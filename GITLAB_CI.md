# GitLab CI/CD Configuration

This document explains the GitLab CI/CD pipeline configured in `.gitlab-ci.yml`.

## ⚠️ Important: GitHub Actions Synchronization

**This project maintains parallel CI/CD configurations for both GitLab and GitHub.**

When modifying CI/CD workflows:
- ✅ Keep trigger rules identical between `.gitlab-ci.yml` and `.github/workflows/`
- ✅ Current triggers: Main branch pushes, version tags (v*.*.*), manual runs
- ✅ Both platforms: NO PR/MR builds to conserve resources
- ✅ Update both platforms when changing build logic or deployment steps

## Overview

The pipeline has 4 stages:
1. **test** - Helm chart validation and testing
2. **build** - Multi-platform Docker image builds
3. **release** - Helm chart publishing to GitLab Pages
4. **cleanup** - Container registry cleanup (manual trigger)

## Pipeline Stages

### 1. Test Stage

**Job: `helm-test`**
- Runs Helm unit tests using helm-unittest plugin
- Validates template rendering with `helm template`
- Lints charts with `helm lint`
- Triggers on: MR changes to `helm/**`, main branch changes, manual

### 2. Build Stage

**Job: `build-yt-playlist`**
- Builds main application Docker image
- Multi-platform: `linux/amd64`, `linux/arm64`
- Uses Docker Buildx with BuildKit
- Registry: GitLab Container Registry (`$CI_REGISTRY_IMAGE`)
- Triggers on: **main branch pushes**, **version tags** (v*.*.*), and **manual runs**
- Tagging strategy:
  - Main branch: `latest`, `<commit-sha>`
  - Tags (v*.*.*): `<version>`, `<major>`, `<major>.<minor>`, `latest`
- Cache: Uses registry cache for faster builds

**Job: `build-auth-ui`**
- Builds authentication UI Docker image
- Same multi-platform and tagging strategy as main app
- Registry: `$CI_REGISTRY_IMAGE/auth-ui`
- Triggers on: **main branch pushes**, **version tags** (v*.*.*), and **manual runs**

### 3. Release Stage

**Job: `helm-release`**
- Packages Helm chart using `helm package`
- Generates/updates Helm repository index.yaml
- Prepares artifacts for GitLab Pages
- Triggers on: main branch changes to `helm/**`

**Job: `pages`**
- Deploys Helm repository to GitLab Pages
- Automatic deployment from `helm-release` artifacts
- Repository URL: `https://<namespace>.gitlab.io/<project>`

### 4. Cleanup Stage

**Job: `cleanup-registry`**
- Cleans up old container images from GitLab Container Registry
- Keeps 10 latest tags per repository (configurable via `KEEP_COUNT`)
- Processes both main app and auth-ui repositories
- Uses GitLab API to list and delete old tags
- **Manual trigger only** - prevents accidental deletions

**Job: `trigger-cleanup`**
- Placeholder job to remind about manual cleanup after builds
- Runs after successful builds on main branch

## Required GitLab Settings

### Container Registry

1. Enable Container Registry in your project:
   - Go to: Settings → General → Visibility
   - Enable "Container Registry"

### GitLab Pages

1. Enable GitLab Pages:
   - Pages are automatically enabled for public projects
   - For private projects: Settings → General → Visibility → Pages

2. After first `helm-release` job runs, access Helm repo at:
   ```bash
   helm repo add yt-playlist https://<namespace>.gitlab.io/<project>
   helm repo update
   ```

### CI/CD Variables

No additional CI/CD variables required! The pipeline uses built-in variables:
- `$CI_REGISTRY` - GitLab Container Registry URL
- `$CI_REGISTRY_USER` - Registry authentication user
- `$CI_REGISTRY_PASSWORD` - Registry authentication token
- `$CI_REGISTRY_IMAGE` - Full image path
- `$CI_JOB_TOKEN` - Job-specific authentication token

Optional variables you can configure (Settings → CI/CD → Variables):
- `KEEP_COUNT` - Number of container tags to keep (default: 10)

## Docker Image Locations

After builds complete, images are available at:

**Main application:**
```
registry.gitlab.com/<namespace>/<project>:latest
registry.gitlab.com/<namespace>/<project>:main
registry.gitlab.com/<namespace>/<project>:<version>
```

**Auth UI:**
```
registry.gitlab.com/<namespace>/<project>/auth-ui:latest
registry.gitlab.com/<namespace>/<project>/auth-ui:main
registry.gitlab.com/<namespace>/<project>/auth-ui:<version>
```

## Helm Repository Usage

After the first release:

```bash
# Add repository
helm repo add yt-playlist https://<namespace>.gitlab.io/<project>

# Update repository index
helm repo update

# Search charts
helm search repo yt-playlist

# Install chart
helm install my-release yt-playlist/yt-playlist

# View available versions
helm search repo yt-playlist/yt-playlist --versions
```

## Manual Cleanup

To clean up old container images:

1. Go to: CI/CD → Pipelines
2. Click on the latest pipeline for main branch
3. Navigate to "cleanup" stage
4. Click "Play" button on `cleanup-registry` job
5. Monitor job output to see deletions

## Differences from GitHub Actions

| Feature | GitHub Actions | GitLab CI/CD |
|---------|---------------|--------------|
| Container Registry | GHCR (ghcr.io) | GitLab Registry (registry.gitlab.com) |
| Helm Publishing | GitHub Pages (chart-releaser) | GitLab Pages (helm package) |
| Multi-platform | docker/build-push-action | docker buildx (manual) |
| Cleanup API | GitHub REST API | GitLab REST API |
| Auth | GITHUB_TOKEN | CI_JOB_TOKEN (automatic) |

## Updating Helm Values for GitLab

When deploying from GitLab registry, update Helm values:

```yaml
# values.yaml or --set flags
image:
  repository: registry.gitlab.com/<namespace>/<project>
  tag: latest

auth:
  ui:
    image:
      repository: registry.gitlab.com/<namespace>/<project>/auth-ui
      tag: latest
```

## Troubleshooting

**Build fails with "docker: command not found"**
- Ensure `docker:24-dind` service is running
- Check `DOCKER_HOST` is set correctly

**Registry authentication fails**
- Verify Container Registry is enabled
- Check project visibility settings

**Cleanup job can't delete tags**
- Ensure you have Maintainer role or higher
- Check API token permissions (CI_JOB_TOKEN has limited scope)

**GitLab Pages not accessible**
- Wait 5-10 minutes after first deployment
- Check Settings → Pages for deployment status
- Verify project visibility allows Pages

**Multi-platform build hangs**
- GitLab shared runners may have limited resources
- Consider using specific runners with more CPU/memory
- Reduce platforms to single architecture for testing

## Migration Checklist

- [x] Created `.gitlab-ci.yml` with all workflow equivalents
- [ ] Push to GitLab and verify first pipeline runs
- [ ] Enable Container Registry in project settings
- [ ] Enable GitLab Pages in project settings
- [ ] Update Helm chart `values.yaml` with GitLab registry URLs
- [ ] Update documentation (README.md) with GitLab instructions
- [ ] Test Helm repository access after first release
- [ ] Configure cleanup schedule or run manually
- [ ] Update ArgoCD applications to use GitLab registry
- [ ] Update `.github/copilot-instructions.md` with GitLab CI/CD patterns
