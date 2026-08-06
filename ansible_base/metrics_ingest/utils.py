"""
Guards and convenience functions for metrics-service telemetry.

The primary call site function is ``maybe_send_event``. It checks whether
metrics ingest is enabled, obtains a cached client, calls ``send_event``,
and swallows all errors — telemetry must never affect normal service flow.
"""

import logging

logger = logging.getLogger("ansible_base.metrics_ingest")

# Mutable container avoids `global` declarations and Python 3.12 cell-variable
# issues with conditional deferred imports.  Reset _cache["client"] to None
# in tests using the ``reset_metrics_client`` fixture.
_cache: dict = {"client": None}


def is_metrics_ingest_enabled() -> bool:
    """
    Return True if all conditions are met to send telemetry:
    - ``METRICS_INGEST_ENABLED`` is True in Django settings
    - ``RESOURCE_SERVER["URL"]`` is configured (provides the gateway host)

    All imports are deferred to avoid circular-import issues at module load time.
    """
    from django.conf import settings

    if not getattr(settings, "METRICS_INGEST_ENABLED", False):
        return False

    resource_server = getattr(settings, "RESOURCE_SERVER", {})
    if not resource_server.get("URL"):
        logger.debug("metrics_ingest disabled: RESOURCE_SERVER.URL is not configured")
        return False

    return True


def get_metrics_ingest_client():
    """
    Return a cached MetricsIngestClient if metrics ingest is enabled, else None.

    The client is constructed lazily on first call and cached for the process
    lifetime. Reset ``_cache["client"] = None`` in tests to force reconstruction.
    """
    if not is_metrics_ingest_enabled():
        return None

    if _cache["client"] is None:
        from django.conf import settings

        from ansible_base.metrics_ingest.client import MetricsIngestClient

        _cache["client"] = MetricsIngestClient(
            jwt_expiration=getattr(settings, "METRICS_INGEST_JWT_EXPIRATION", 60),
        )

    return _cache["client"]


def maybe_send_event(
    service_name: str,
    event_name: str,
    payload: dict,
    **kwargs,
) -> None:
    """
    Fire-and-forget telemetry send.

    Checks whether metrics ingest is enabled, sends the event, and silently
    swallows any exception (with a warning log). Never raises.

    Example::

        from ansible_base.metrics_ingest.utils import maybe_send_event

        maybe_send_event(
            service_name="aap-eda-server",
            event_name="eda_activation_daily_summary",
            payload={"active_activations": 47, "installer_pseudo_id": "abc..."},
        )
    """
    client = get_metrics_ingest_client()
    if client is None:
        return

    try:
        resp = client.send_event(service_name, event_name, payload, **kwargs)
        if not resp.ok:
            logger.warning(
                "metrics_ingest send_event failed — %s/%s: HTTP %s",
                service_name,
                event_name,
                resp.status_code,
            )
    except Exception as exc:
        logger.warning(
            "metrics_ingest send_event error for %s/%s: %s",
            service_name,
            event_name,
            exc,
        )


def maybe_send_batch(
    service_name: str,
    event_name: str,
    payload: dict,
    collection_start: str,
    collection_end: str,
    **kwargs,
) -> None:
    """
    Fire-and-forget batch send. Dispatched to Segment immediately on receipt.
    Never raises.
    """
    client = get_metrics_ingest_client()
    if client is None:
        return

    try:
        resp = client.send_batch(service_name, event_name, payload, collection_start, collection_end, **kwargs)
        if not resp.ok:
            logger.warning(
                "metrics_ingest send_batch failed — %s/%s: HTTP %s",
                service_name,
                event_name,
                resp.status_code,
            )
    except Exception as exc:
        logger.warning(
            "metrics_ingest send_batch error for %s/%s: %s",
            service_name,
            event_name,
            exc,
        )
