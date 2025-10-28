"""NodePool data models for GCP HCP CLI."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodePoolCondition(BaseModel):
    """Represents a nodepool condition."""

    type: str = Field(description="Type of condition")
    status: str = Field(description="Status of condition (True/False/Unknown)")
    lastTransitionTime: Optional[datetime] = Field(default=None, description="Last transition time")
    reason: Optional[str] = Field(default=None, description="Reason for condition")
    message: Optional[str] = Field(default=None, description="Human-readable message")


class NodePoolStatus(BaseModel):
    """Represents nodepool status information."""

    phase: Optional[str] = Field(default=None, description="Current phase of the nodepool")
    message: Optional[str] = Field(default=None, description="Status message")
    generation: Optional[int] = Field(default=None, description="Generation number")
    resourceVersion: Optional[str] = Field(default=None, description="Resource version")
    conditions: List[NodePoolCondition] = Field(
        default_factory=list, description="NodePool conditions"
    )
    nodeCount: Optional[int] = Field(default=None, description="Current number of nodes")
    readyNodeCount: Optional[int] = Field(default=None, description="Number of ready nodes")


class NodePoolManagement(BaseModel):
    """Represents nodepool management configuration."""

    autoRepair: Optional[bool] = Field(default=None, description="Enable auto-repair")
    autoUpgrade: Optional[bool] = Field(default=None, description="Enable auto-upgrade")
    upgradeType: Optional[str] = Field(default=None, description="Upgrade strategy type")


class NodePoolSpec(BaseModel):
    """Represents nodepool specification."""

    clusterId: str = Field(description="Parent cluster ID")
    machineType: Optional[str] = Field(default=None, description="GCP machine type")
    diskSize: Optional[int] = Field(default=None, description="Boot disk size in GB")
    nodeCount: Optional[int] = Field(default=None, description="Desired number of nodes")
    minNodeCount: Optional[int] = Field(default=None, description="Minimum number of nodes")
    maxNodeCount: Optional[int] = Field(default=None, description="Maximum number of nodes")
    management: Optional[NodePoolManagement] = Field(
        default=None, description="Management configuration"
    )
    labels: Optional[Dict[str, str]] = Field(default=None, description="Node labels")
    taints: Optional[List[Dict[str, Any]]] = Field(default=None, description="Node taints")


class NodePool(BaseModel):
    """Represents a nodepool resource."""

    id: str = Field(description="Unique nodepool identifier")
    name: str = Field(description="NodePool name")
    clusterId: str = Field(description="Parent cluster ID")
    createdBy: Optional[str] = Field(default=None, description="User who created the nodepool")
    generation: Optional[int] = Field(default=None, description="Generation number")
    resourceVersion: Optional[str] = Field(default=None, description="Resource version")
    spec: Optional[NodePoolSpec] = Field(default=None, description="NodePool specification")
    status: Optional[NodePoolStatus] = Field(default=None, description="NodePool status")
    createdAt: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updatedAt: Optional[datetime] = Field(default=None, description="Last update timestamp")

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }

    def get_display_status(self) -> str:
        """Get human-readable status.

        Returns:
            Status string for display
        """
        if self.status and self.status.phase:
            return self.status.phase
        return "Unknown"

    def is_ready(self) -> bool:
        """Check if nodepool is ready.

        Returns:
            True if nodepool is ready, False otherwise
        """
        return self.get_display_status() == "Ready"

    def get_node_info(self) -> str:
        """Get node count information.

        Returns:
            Node count string (e.g., "3/5 ready")
        """
        if not self.status:
            return "Unknown"

        ready_count = self.status.readyNodeCount or 0
        total_count = self.status.nodeCount or 0

        if total_count == 0:
            return "0 nodes"

        return f"{ready_count}/{total_count} ready"

    def get_age(self) -> str:
        """Get nodepool age as human-readable string.

        Returns:
            Age string (e.g., "2d", "5h", "30m")
        """
        if not self.createdAt:
            return "Unknown"

        now = datetime.now(self.createdAt.tzinfo)
        delta = now - self.createdAt

        if delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours}h"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes}m"
        else:
            return f"{delta.seconds}s"

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "NodePool":
        """Create nodepool from API response data.

        Args:
            data: API response data

        Returns:
            NodePool instance
        """
        # Handle datetime fields
        if "createdAt" in data and data["createdAt"]:
            data["createdAt"] = datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
        if "updatedAt" in data and data["updatedAt"]:
            data["updatedAt"] = datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00"))

        # Handle nested status
        if "status" in data and data["status"]:
            status_data = data["status"]
            if "conditions" in status_data:
                conditions = []
                for cond in status_data["conditions"]:
                    if "lastTransitionTime" in cond and cond["lastTransitionTime"]:
                        cond["lastTransitionTime"] = datetime.fromisoformat(
                            cond["lastTransitionTime"].replace("Z", "+00:00")
                        )
                    conditions.append(NodePoolCondition(**cond))
                status_data["conditions"] = conditions
            data["status"] = NodePoolStatus(**status_data)

        # Handle spec
        if "spec" in data and data["spec"]:
            spec_data = data["spec"]
            if "management" in spec_data and spec_data["management"]:
                spec_data["management"] = NodePoolManagement(**spec_data["management"])
            data["spec"] = NodePoolSpec(**spec_data)

        return cls(**data)