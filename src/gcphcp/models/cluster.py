"""Cluster data models for GCP HCP CLI."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ClusterCondition(BaseModel):
    """Represents a cluster condition."""

    type: str = Field(description="Type of condition")
    status: str = Field(description="Status of condition (True/False/Unknown)")
    lastTransitionTime: Optional[datetime] = Field(default=None, description="Last transition time")
    reason: Optional[str] = Field(default=None, description="Reason for condition")
    message: Optional[str] = Field(default=None, description="Human-readable message")


class ClusterStatus(BaseModel):
    """Represents cluster status information."""

    phase: Optional[str] = Field(default=None, description="Current phase of the cluster")
    message: Optional[str] = Field(default=None, description="Status message")
    generation: Optional[int] = Field(default=None, description="Generation number")
    resourceVersion: Optional[str] = Field(default=None, description="Resource version")
    conditions: List[ClusterCondition] = Field(default_factory=list, description="Cluster conditions")
    controllerStatuses: List[Dict[str, Any]] = Field(
        default_factory=list, description="Controller status information"
    )


class ClusterSpec(BaseModel):
    """Represents cluster specification."""

    targetProjectId: Optional[str] = Field(default=None, description="Target GCP project ID")
    region: Optional[str] = Field(default=None, description="Target region")
    network: Optional[Dict[str, Any]] = Field(default=None, description="Network configuration")
    dns: Optional[Dict[str, Any]] = Field(default=None, description="DNS configuration")
    platform: Optional[Dict[str, Any]] = Field(default=None, description="Platform configuration")


class Cluster(BaseModel):
    """Represents a cluster resource."""

    id: str = Field(description="Unique cluster identifier")
    name: str = Field(description="Cluster name")
    targetProjectId: Optional[str] = Field(default=None, description="Target GCP project ID")
    createdBy: Optional[str] = Field(default=None, description="User who created the cluster")
    generation: Optional[int] = Field(default=None, description="Generation number")
    resourceVersion: Optional[str] = Field(default=None, description="Resource version")
    spec: Optional[ClusterSpec] = Field(default=None, description="Cluster specification")
    status: Optional[ClusterStatus] = Field(default=None, description="Cluster status")
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
        """Check if cluster is ready.

        Returns:
            True if cluster is ready, False otherwise
        """
        return self.get_display_status() == "Ready"

    def get_age(self) -> str:
        """Get cluster age as human-readable string.

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
    def from_api_response(cls, data: Dict[str, Any]) -> "Cluster":
        """Create cluster from API response data.

        Args:
            data: API response data

        Returns:
            Cluster instance
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
                    conditions.append(ClusterCondition(**cond))
                status_data["conditions"] = conditions
            data["status"] = ClusterStatus(**status_data)

        # Handle spec
        if "spec" in data and data["spec"]:
            data["spec"] = ClusterSpec(**data["spec"])

        return cls(**data)