import os
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class OrbitPipeline(BaseModel):
    id: str = Field(..., description="Pipeline ID")
    status: str = Field(..., description="Status of the pipeline (e.g. running, success, failed)")
    web_url: Optional[str] = Field(None, description="Web URL to the pipeline")

class OrbitMergeRequest(BaseModel):
    id: str = Field(..., description="Merge Request ID/IID")
    title: str = Field(..., description="Title of the merge request")
    state: str = Field(..., description="State of the MR (e.g. opened, merged, closed)")
    web_url: Optional[str] = Field(None, description="Web URL to the merge request")

class OrbitVulnerability(BaseModel):
    id: str = Field(..., description="Vulnerability ID (e.g. CVE or internal identifier)")
    severity: str = Field(..., description="Severity (e.g. critical, high, medium, low, info)")
    description: Optional[str] = Field(None, description="Description of the vulnerability")

class OrbitImpactContext(BaseModel):
    symbol: str = Field(..., description="Symbol queried")
    affected_projects: List[str] = Field(default_factory=list, description="List of projects importing or affected by this symbol")
    dependencies: List[str] = Field(default_factory=list, description="Downstream or upstream dependencies of the symbol")
    pipelines: List[OrbitPipeline] = Field(default_factory=list, description="Pipelines affected by changes to this symbol")
    merge_requests: List[OrbitMergeRequest] = Field(default_factory=list, description="Merge requests related to this symbol")
    related_vulnerabilities: List[OrbitVulnerability] = Field(default_factory=list, description="Known vulnerabilities for the symbol")


class OrbitClient:
    """
    Client for querying the GitLab Orbit Knowledge Graph API directly.
    """
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        use_fake: Optional[bool] = None,
        timeout: float = 5.0
    ) -> None:
        self.api_url = api_url or os.getenv("ORBIT_API_URL")
        self.api_token = api_token or os.getenv("ORBIT_API_TOKEN")
        self.timeout = timeout
        
        if use_fake is None:
            self.use_fake = os.getenv("USE_FAKE_ORBIT", "false").lower() == "true"
        else:
            self.use_fake = use_fake

        # Standard dictionary containing mock responses for tests/fake execution
        self._fake_db: Dict[str, Dict[str, Any]] = {
            "driftstore.db.get_db": {
                "symbol": "driftstore.db.get_db",
                "affected_projects": ["driftstore-backend", "driftstore-admin"],
                "dependencies": ["SQLAlchemy", "psycopg2-binary"],
                "pipelines": [
                    {"id": "pl-891", "status": "failed", "web_url": "https://gitlab.example.com/driftstore/pipelines/891"}
                ],
                "merge_requests": [
                    {"id": "mr-104", "title": "Upgrade DB connection pool size limit", "state": "opened", "web_url": "https://gitlab.example.com/driftstore/merge_requests/104"}
                ],
                "related_vulnerabilities": [
                    {"id": "CVE-2026-9901", "severity": "high", "description": "SQL connection resource exhaustion vulnerability"}
                ]
            },
            "requests.get": {
                "symbol": "requests.get",
                "affected_projects": ["driftstore-sync", "driftstore-gateway"],
                "dependencies": ["urllib3"],
                "pipelines": [
                    {"id": "pl-456", "status": "success", "web_url": "https://gitlab.example.com/requests/pipelines/456"}
                ],
                "merge_requests": [],
                "related_vulnerabilities": [
                    {"id": "CVE-2022-28108", "severity": "medium", "description": "Unverified SSL handshake vulnerability"}
                ]
            }
        }

    def is_configured(self) -> bool:
        """Returns True if the client is fully configured to reach a live endpoint, or running in fake mode."""
        if self.use_fake:
            return True
        return bool(self.api_url and self.api_token)

    def health_check(self) -> bool:
        """
        Performs a health check request. Returns True if healthy, False otherwise.
        """
        if self.use_fake:
            # Fake health check is healthy unless config has URL 'http://unhealthy'
            if self.api_url == "http://unhealthy":
                return False
            return True

        if not self.api_url:
            return False

        url = self.api_url.rstrip("/") + "/health"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "X-Orbit-Token": self.api_token or "",
            "Accept": "application/json"
        }
        
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if 200 <= response.status < 300:
                    return True
        except Exception as e:
            logger.warning(f"Orbit health check failed: {e}")
            
        return False

    def query_symbol(self, symbol: str) -> Optional[OrbitImpactContext]:
        """
        Queries Orbit API for blast-radius impact context for a specific symbol.
        """
        if not self.is_configured():
            raise RuntimeError("OrbitClient queried but is unconfigured.")

        if self.use_fake:
            # Query fake database
            data = self._fake_db.get(symbol)
            if not data:
                return None
            return OrbitImpactContext(**data)

        # Real production endpoint call
        url = self.api_url.rstrip("/") + f"/api/v1/blast-radius?symbol={urllib.parse.quote(symbol)}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "X-Orbit-Token": self.api_token or "",
            "Accept": "application/json"
        }
        
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    raw_data = json.loads(response.read().decode("utf-8"))
                    return OrbitImpactContext(**raw_data)
                elif response.status == 404:
                    return None
                else:
                    logger.warning(f"Orbit query returned unexpected status {response.status}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            logger.warning(f"Orbit query HTTP error: {e}")
        except Exception as e:
            logger.warning(f"Orbit query failed: {e}")
            
        return None
