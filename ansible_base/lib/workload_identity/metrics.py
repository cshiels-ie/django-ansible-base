"""
OIDC Workload Identity Scope for AAP Metrics Service.

Defines the scope and claims used when the metrics service requests a
gateway-issued JWT to authenticate against Controller, EDA, or Hub
Prometheus endpoints.
"""

from .base import BaseWorkloadIdentityScope


class AAPMetricsServiceScope(BaseWorkloadIdentityScope):
    """
    Scope for AAP Metrics Service internal service-to-service scraping.

    When the metrics service requests a token with this scope it receives
    a gateway-signed JWT it can present as X-DAB-JW-TOKEN to Controller,
    EDA, or Hub in order to authenticate as the gateway system user and
    scrape Prometheus metrics endpoints.
    """

    name = "aap_metrics_collection"
    description = "AAP Metrics Service workload identity for scraping internal Prometheus endpoints"

    CLAIM_TARGET_SERVICE = "aap_metrics_target_service"

    @classmethod
    def list_claims(cls) -> list[str]:
        return [cls.CLAIM_TARGET_SERVICE]

    @classmethod
    def get_target_claim_names_to_sub_stubs(cls) -> dict[str, str]:
        return {
            cls.CLAIM_TARGET_SERVICE: "service",
        }

    def populate_claims(self, workload_data: dict) -> dict:
        raise NotImplementedError("populate_claims() not yet implemented")
