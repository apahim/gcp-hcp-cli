"""Unit tests for data models."""

from datetime import datetime
import pytest

from gcphcp.models.cluster import ClusterCondition, ClusterStatus, Cluster
from gcphcp.models.nodepool import NodePool, NodePoolStatus


class TestClusterModels:
    """Test suite for cluster data models."""

    def test_cluster_condition_creation(self):
        """Test creating a cluster condition."""
        condition = ClusterCondition(
            type="Ready",
            status="True"
        )
        assert condition.type == "Ready"
        assert condition.status == "True"
        assert condition.lastTransitionTime is None
        assert condition.reason is None
        assert condition.message is None

    def test_cluster_condition_with_all_fields(self):
        """Test creating a cluster condition with all fields."""
        time_now = datetime.now()
        condition = ClusterCondition(
            type="Ready",
            status="True",
            lastTransitionTime=time_now,
            reason="ClusterReady",
            message="Cluster is ready"
        )
        assert condition.type == "Ready"
        assert condition.status == "True"
        assert condition.lastTransitionTime == time_now
        assert condition.reason == "ClusterReady"
        assert condition.message == "Cluster is ready"

    def test_cluster_status_creation(self):
        """Test creating cluster status."""
        status = ClusterStatus(
            phase="Running",
            conditions=[]
        )
        assert status.phase == "Running"
        assert status.conditions == []
        assert status.message is None
        assert status.generation is None

    def test_cluster_status_with_conditions(self):
        """Test creating cluster status with conditions."""
        condition = ClusterCondition(type="Ready", status="True")
        status = ClusterStatus(
            phase="Running",
            conditions=[condition],
            message="Cluster is running",
            generation=1
        )
        assert status.phase == "Running"
        assert len(status.conditions) == 1
        assert status.conditions[0].type == "Ready"
        assert status.message == "Cluster is running"
        assert status.generation == 1

    def test_cluster_creation(self):
        """Test creating a cluster."""
        cluster_data = {
            "metadata": {"name": "test-cluster"},
            "spec": {"machineType": "e2-standard-4"},
            "status": {"phase": "Running"}
        }
        cluster = Cluster(**cluster_data)
        assert cluster.metadata == {"name": "test-cluster"}
        assert cluster.spec == {"machineType": "e2-standard-4"}
        assert cluster.status == {"phase": "Running"}


class TestNodePoolModels:
    """Test suite for nodepool data models."""

    def test_nodepool_status_creation(self):
        """Test creating nodepool status."""
        status = NodePoolStatus(
            phase="Ready",
            replicas=3
        )
        assert status.phase == "Ready"
        assert status.replicas == 3
        assert status.readyReplicas is None
        assert status.conditions == []

    def test_nodepool_creation(self):
        """Test creating a nodepool."""
        nodepool_data = {
            "metadata": {"name": "test-nodepool"},
            "spec": {"replicas": 3},
            "status": {"phase": "Ready", "replicas": 3}
        }
        nodepool = NodePool(**nodepool_data)
        assert nodepool.metadata == {"name": "test-nodepool"}
        assert nodepool.spec == {"replicas": 3}
        assert nodepool.status == {"phase": "Ready", "replicas": 3}

    def test_nodepool_json_serialization(self):
        """Test nodepool JSON serialization."""
        nodepool_data = {
            "metadata": {"name": "test-nodepool"},
            "spec": {"replicas": 3},
            "status": {"phase": "Ready", "replicas": 3}
        }
        nodepool = NodePool(**nodepool_data)
        json_data = nodepool.model_dump()
        assert json_data["metadata"]["name"] == "test-nodepool"
        assert json_data["spec"]["replicas"] == 3
        assert json_data["status"]["phase"] == "Ready"