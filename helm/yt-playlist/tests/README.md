# Helm Chart Unit Tests

This directory contains unit tests for the yt-playlist Helm chart using [helm-unittest](https://github.com/helm-unittest/helm-unittest).

## Installation

Install the helm-unittest plugin:

```bash
helm plugin install https://github.com/helm-unittest/helm-unittest
```

## Running Tests

Run all tests:

```bash
# From the chart directory
cd helm/yt-playlist
helm unittest .

# Or from the repository root
helm unittest helm/yt-playlist
```

Run specific test files:

```bash
helm unittest -f 'tests/deployment_test.yaml' .
```

Run with verbose output:

```bash
helm unittest -v .
```

## Test Coverage

The test suite covers:

- **deployment_test.yaml**: Main application deployment
  - Default configuration
  - Custom image tags
  - Environment variables
  - Cookies configuration (file and content)
  - Tailscale sidecar integration
  - Resource limits
  - Extra arguments handling

- **service_test.yaml**: Service configuration
  - Service enabled/disabled
  - Service types (ClusterIP, NodePort)
  - Custom annotations
  - Port configuration

- **pvc_test.yaml**: Persistent volume claims
  - PVC creation
  - Retention policy annotation
  - Custom storage sizes
  - Storage class configuration
  - Existing claim usage

- **secret_test.yaml**: Secret management
  - OAuth credentials
  - Existing secret references
  - Cookies content

- **servicemonitor_test.yaml**: Prometheus monitoring
  - ServiceMonitor creation
  - Custom labels
  - Scrape configuration

- **ingress_test.yaml**: Ingress configuration
  - Host configuration
  - TLS setup
  - Annotations
  - IngressClassName

- **auth-ui_test.yaml**: Authentication UI
  - Auth UI deployment
  - RBAC resources
  - Custom images

## Writing New Tests

Tests use YAML format with assertions. Example:

```yaml
suite: test my-feature
templates:
  - deployment.yaml
tests:
  - it: should do something
    set:
      myValue: "test"
    asserts:
      - equal:
          path: spec.template.spec.containers[0].name
          value: expected-value
```

Common assertions:
- `isKind`: Verify resource type
- `equal`: Check exact value match
- `contains`: Check if array contains element
- `isNull`/`isNotNull`: Check null values
- `isNotEmpty`: Verify non-empty values
- `hasDocuments`: Check document count

## CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Install helm-unittest
  run: helm plugin install https://github.com/helm-unittest/helm-unittest

- name: Run Helm tests
  run: helm unittest helm/yt-playlist
```

## Documentation

- [helm-unittest Documentation](https://github.com/helm-unittest/helm-unittest/blob/main/DOCUMENT.md)
- [Assertion Types](https://github.com/helm-unittest/helm-unittest/blob/main/DOCUMENT.md#assertion-types)
