"""
Client for sending telemetry to the metrics-service ingest endpoint.

The target URL is always {RESOURCE_SERVER["URL"]}/api/metrics/ — the metrics-service
is routed through the gateway host. No separate URL setting is needed.
Authentication uses X-ANSIBLE-SERVICE-AUTH (HS256 JWT via get_service_token),
the same mechanism used for all other DAB service-to-service calls.

Usage::

    from ansible_base.metrics_ingest.utils import maybe_send_event

    maybe_send_event(
        service_name="aap-eda-server",
        event_name="eda_activation_daily_summary",
        payload={"active_activations": 47, ...},
    )
"""

import logging

from ansible_base.resource_registry.resource_server import get_resource_server_config
from ansible_base.resource_registry.service_client import BaseServiceClient

logger = logging.getLogger("ansible_base.metrics_ingest")

_INGEST_API_PATH = "api/v1/ingest"


class MetricsIngestClient(BaseServiceClient):
    """
    HTTP client for the metrics-service ingest endpoint.

    URL is derived at instantiation from RESOURCE_SERVER["URL"] + "/api/metrics/".
    Auth token is auto-refreshed via BaseServiceClient's JWT lifecycle.
    All calls use a short timeout (default 5s) so telemetry never blocks callers.
    """

    def __init__(self, jwt_expiration: int = 60, timeout: int = 5, **kwargs):
        config = get_resource_server_config()
        gateway_url = config["URL"].rstrip("/")
        base_url = f"{gateway_url}/api/metrics/{_INGEST_API_PATH}/"
        super().__init__(
            base_url=base_url,
            verify_https=config.get("VALIDATE_HTTPS", True),
            jwt_expiration=jwt_expiration,
            timeout=timeout,
            **kwargs,
        )

    def register(
        self,
        service_name: str,
        event_name: str,
        display_name: str,
        version: str,
        segment_event_name: str,
        payload_schema: dict,
        rollup_config: "dict | None" = None,
        validate_payload: bool = False,
    ):
        """
        Register or update a ServiceDefinition on metrics-service.

        Idempotent — safe to call on every service startup. Returns 201 on first
        registration, 200 on subsequent calls (upsert on service_name + event_name).
        """
        body = {
            "service_name": service_name,
            "event_name": event_name,
            "display_name": display_name,
            "version": version,
            "segment_event_name": segment_event_name,
            "payload_schema": payload_schema,
            "validate_payload": validate_payload,
        }
        if rollup_config is not None:
            body["rollup_config"] = rollup_config
        return self._make_request("post", "register/", data=body)

    def send_event(
        self,
        service_name: str,
        event_name: str,
        payload: dict,
        event_timestamp: "str | None" = None,
        schema_version: str = "1.0",
    ):
        """
        Send a single per-event payload.

        Events accumulate in metrics-service and are aggregated by the daily
        rollup task before forwarding to Segment. Returns 202 immediately.
        event_timestamp defaults to the current UTC time if not provided.
        """
        from django.utils.timezone import now

        body = {
            "service_name": service_name,
            "event_name": event_name,
            "schema_version": schema_version,
            "payload_type": "event",
            "event_timestamp": event_timestamp or now().isoformat(),
            "payload": payload,
        }
        return self._make_request("post", "events/", data=body)

    def send_batch(
        self,
        service_name: str,
        event_name: str,
        payload: dict,
        collection_start: str,
        collection_end: str,
        schema_version: str = "1.0",
    ):
        """
        Send a pre-aggregated batch payload.

        Batch payloads are dispatched to Segment immediately (not via daily rollup).
        Use for pre-computed summaries, heartbeats, or low-frequency snapshots.
        """
        body = {
            "service_name": service_name,
            "event_name": event_name,
            "schema_version": schema_version,
            "payload_type": "batch",
            "collection_start": collection_start,
            "collection_end": collection_end,
            "payload": payload,
        }
        return self._make_request("post", "events/", data=body)

    def get_status(self, service_name: "str | None" = None):
        """
        Query ingest status for this service (or all services if service_name is None).

        Returns event counts by status and the last_sent_at timestamp.
        """
        params = {"service_name": service_name} if service_name else {}
        return self._make_request("get", "status/", params=params)
