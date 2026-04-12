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

Upgrade a nodepool to a new OCP version:

```bash
gcphcp nodepools upgrade my-nodepool --cluster my-cluster --version 4.22.0-ec.5
```

Cluster and nodepool upgrades are independent operations. You can upgrade them separately and to different versions (within the supported version skew).

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
