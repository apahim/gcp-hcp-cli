# Cluster and NodePool Upgrades

## Upgrading a Cluster

Upgrade a cluster to a new OCP version:

```bash
gcphcp clusters upgrade my-cluster --version 4.22.0-ec.5
```

The cluster control plane will begin upgrading to the specified version. The version is resolved to a release image via the Cincinnati update service.

### Checking Upgrade Status

```bash
gcphcp clusters describe upgrade my-cluster
```

Example output during an upgrade:

```
Cluster:            my-cluster
Version:            4.22.0-ec.4 → 4.22.0-ec.5
Progress:           Partial
Updating Version:   True
Message:            Unable to apply 4.22.0-ec.5: the cluster operator console is not available

Available Updates:
  - 4.22.0-ec.5
```

Once completed:

```
Cluster:            my-cluster
Version:            4.22.0-ec.5
Progress:           Completed
Updating Version:   False
Message:            Cluster version is 4.22.0-ec.5

No available updates.
```

## Upgrading a NodePool

Upgrade a nodepool to match the control plane version:

```bash
gcphcp nodepools upgrade my-nodepool --cluster my-cluster
```

The target version is automatically resolved from the cluster's control plane — there is no `--version` flag. The command validates the CP state before proceeding:

- If the nodepool is already at the CP version:
  ```
  Nodepool 'my-nodepool' is already at version 4.22.0-ec.5. Nothing to do.
  ```
- If the CP upgrade hasn't started yet:
  ```
  Error: Control plane upgrade to 4.22.0-ec.5 has not started yet. Wait for the CP upgrade to begin before upgrading nodepools.
  ```
- If the CP upgrade is still in progress:
  ```
  Error: Control plane upgrade to 4.22.0-ec.5 is still in progress (state: Partial). Wait for the CP upgrade to complete before upgrading nodepools.
  ```
- If the CP upgrade has completed, the nodepool upgrade proceeds:
  ```
  Upgrading nodepool 'my-nodepool' from 4.22.0-ec.4 to 4.22.0-ec.5 (matching control plane version)...
  ✓ Upgrade initiated. Use 'gcphcp nodepools describe upgrade my-nodepool --cluster my-cluster' to monitor progress.
  ```

### Checking NodePool Upgrade Status

```bash
gcphcp nodepools describe upgrade my-nodepool --cluster my-cluster
```

Example output during an upgrade:

```
NodePool:           my-nodepool
Cluster:            my-cluster
Version:            4.22.0-ec.4 → 4.22.0-ec.5
Updating Version:   True
Ready:              False
Message:            Minimum availability requires 1 replicas, current 0 available
```

Once completed:

```
NodePool:           my-nodepool
Cluster:            my-cluster
Version:            4.22.0-ec.5
Updating Version:   False
Ready:              True
```

## JSON Output

Both commands support JSON output for scripting:

```bash
gcphcp --format json clusters describe upgrade my-cluster
gcphcp --format json nodepools describe upgrade my-nodepool --cluster my-cluster
```
