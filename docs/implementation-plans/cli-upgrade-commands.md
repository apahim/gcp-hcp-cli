# CLI Upgrade Commands

## Overview

Add `upgrade` and `describe upgrade` commands to `gcphcp clusters` and `gcphcp nodepools`. These commands use existing CLS Backend endpoints (no backend changes) to trigger version upgrades and display upgrade status.

**Design Decision**: [adopt-cincinnati-for-version-resolution](https://github.com/openshift-online/gcp-hcp/blob/main/design-decisions/adopt-cincinnati-for-version-resolution.md)

## Architecture

```
User
  |  gcphcp clusters upgrade my-cluster --version 4.22.0-ec.5
  v
CLI (gcphcp)
  |  1. GET /api/v1/clusters/{id}          -> fetch current spec
  |  2. Set spec.release.version = "4.22.0-ec.5"
  |  3. PUT /api/v1/clusters/{id}          -> submit updated spec
  v
CLS Backend
  |  Stores updated spec, bumps generation
  |  Publishes cluster.updated event
  v
CLS Controller (existing)
  |  Version Resolution Controller resolves new version via Cincinnati
  |  HC Templating Controller updates HostedCluster with resolved image
  v
HyperShift HostedCluster
  |  CVO performs the OCP upgrade
```

## Commands

### Cluster Commands

```bash
# Upgrade cluster to a specific version
gcphcp clusters upgrade my-cluster --version 4.22.0-ec.5

# Check upgrade status
gcphcp clusters describe upgrade my-cluster
```

### NodePool Commands

```bash
# Upgrade nodepool to a specific version
gcphcp nodepools upgrade my-nodepool --cluster my-cluster --version 4.22.0-ec.5

# Check upgrade status
gcphcp nodepools describe upgrade my-nodepool --cluster my-cluster
```

### Command Structure

`describe` is a subgroup under `clusters` and `nodepools`, allowing future `describe` subcommands (e.g., `describe status`, `describe config`).

```
gcphcp clusters
  ├── create
  ├── list
  ├── status
  ├── delete
  ├── upgrade              # new
  └── describe             # new subgroup
      └── upgrade          # new
gcphcp nodepools
  ├── create
  ├── list
  ├── delete
  ├── upgrade              # new
  └── describe             # new subgroup
      └── upgrade          # new
```

## Implementation Details

### `clusters upgrade`

**File**: `src/gcphcp/cli/commands/clusters.py`

1. Accept `CLUSTER` argument and `--version` (required) flag
2. Resolve cluster identifier using existing `resolve_cluster_identifier()`
3. GET `/api/v1/clusters/{id}` to fetch current cluster (full spec needed for PUT)
4. Set `spec.release.version` to the target version
5. PUT `/api/v1/clusters/{id}` with the updated spec
6. Display confirmation

```
$ gcphcp clusters upgrade my-cluster --version 4.22.0-ec.5let 
Upgrading cluster 'my-cluster' to version 4.22.0-ec.5...
✓ Upgrade initiated. Use 'gcphcp clusters describe upgrade my-cluster' to monitor progress.
```

### `clusters describe upgrade`

**File**: `src/gcphcp/cli/commands/clusters.py`

**Data source**: HostedCluster resource status from `GET /api/v1/clusters/{id}/status` at path `controller_status[].metadata.resources.hostedcluster.resource_status`.

Fields displayed:

| Field | Source |
|-------|--------|
| Version | `version.history[0].version` — shows `old → new` during upgrades |
| Progress | `version.history[0].state` (Partial/Completed) |
| Updating Version | `conditions[type=ClusterVersionProgressing].status` |
| Message | `conditions[type=ClusterVersionProgressing].message` |
| Available Updates | `version.availableUpdates[].version` |

**Stable state:**
```
$ gcphcp clusters describe upgrade my-cluster
Cluster:            my-cluster
Version:            4.22.0-ec.5
Progress:           Completed
Updating Version:   False
Message:            Cluster version is 4.22.0-ec.5

No available updates.
```

**During upgrade:**
```
$ gcphcp clusters describe upgrade my-cluster
Cluster:            my-cluster
Version:            4.22.0-ec.4 → 4.22.0-ec.5
Progress:           Partial
Updating Version:   True
Message:            Unable to apply 4.22.0-ec.5: the cluster operator console is not available

Available Updates:
  - 4.22.0-ec.5
```

### `nodepools upgrade`

**File**: `src/gcphcp/cli/commands/nodepools.py`

1. Accept `NODEPOOL` argument, `--cluster` (required) and `--version` (required) flags
2. Resolve cluster and nodepool identifiers using existing resolvers
3. GET `/api/v1/nodepools/{id}` to fetch current nodepool
4. Set `spec.release.version` to the target version
5. PUT `/api/v1/nodepools/{id}` with the updated spec
6. Display confirmation

### `nodepools describe upgrade`

**File**: `src/gcphcp/cli/commands/nodepools.py`

**Data source**: NodePool resource status from `GET /api/v1/nodepools/{id}/status` at path `controller_status[].metadata.resources.nodepool.resource_status`.

Fields displayed:

| Field | Source |
|-------|--------|
| Version | `resource_status.version` — shows `old → new` during upgrades (parsed from `UpdatingVersion` condition message) |
| Updating Version | `conditions[type=UpdatingVersion].status` |
| Ready | `conditions[type=Ready].status` |
| Message | `conditions[type=Ready].message` (shown when not ready) |

**Stable state:**
```
$ gcphcp nodepools describe upgrade my-nodepool --cluster my-cluster
NodePool:           my-nodepool
Cluster:            my-cluster
Version:            4.22.0-ec.5
Updating Version:   False
Ready:              True
```

**During upgrade:**
```
$ gcphcp nodepools describe upgrade my-nodepool --cluster my-cluster
NodePool:           my-nodepool
Cluster:            my-cluster
Version:            4.22.0-ec.4 → 4.22.0-ec.5
Updating Version:   True
Ready:              False
Message:            Minimum availability requires 1 replicas, current 0 available
```

## API Endpoints Used

No new backend endpoints. All existing:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get cluster | GET | `/api/v1/clusters/{id}` |
| Update cluster | PUT | `/api/v1/clusters/{id}` |
| Get cluster status | GET | `/api/v1/clusters/{id}/status` |
| Get nodepool | GET | `/api/v1/nodepools/{id}` |
| Update nodepool | PUT | `/api/v1/nodepools/{id}` |
| Get nodepool status | GET | `/api/v1/nodepools/{id}/status` |

## Status Data Paths

| Data | Endpoint | Path |
|------|----------|------|
| HC version info | `/clusters/{id}/status` | `controller_status[].metadata.resources.hostedcluster.resource_status.version` |
| HC conditions | `/clusters/{id}/status` | `controller_status[].metadata.resources.hostedcluster.resource_status.conditions` |
| NP version | `/nodepools/{id}/status` | `controller_status[].metadata.resources.nodepool.resource_status.version` |
| NP conditions | `/nodepools/{id}/status` | `controller_status[].metadata.resources.nodepool.resource_status.conditions` |
