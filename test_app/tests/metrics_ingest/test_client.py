"""Tests for ansible_base.metrics_ingest.client.MetricsIngestClient."""

from unittest.mock import MagicMock, patch

import pytest


GATEWAY_URL = "https://gateway.example.com"
EXPECTED_BASE_URL = f"{GATEWAY_URL}/api/metrics/api/v1/ingest/"

RESOURCE_SERVER_SETTINGS = {
    "URL": GATEWAY_URL,
    "SECRET_KEY": "test-secret-key-32-chars-minimum!!",
    "VALIDATE_HTTPS": True,
    "JWT_ALGORITHM": "HS256",
}


@pytest.fixture
def mock_resource_server_config():
    with patch(
        "ansible_base.metrics_ingest.client.get_resource_server_config",
        return_value=RESOURCE_SERVER_SETTINGS,
    ):
        yield


@pytest.fixture
def client(mock_resource_server_config):
    from ansible_base.metrics_ingest.client import MetricsIngestClient

    c = MetricsIngestClient()
    c._make_request = MagicMock(return_value=MagicMock(status_code=202, ok=True))
    return c


@pytest.mark.unit
class TestMetricsIngestClientURL:
    def test_base_url_derived_from_resource_server(self, mock_resource_server_config):
        from ansible_base.metrics_ingest.client import MetricsIngestClient

        c = MetricsIngestClient()
        assert c.base_url == EXPECTED_BASE_URL

    def test_gateway_url_trailing_slash_stripped(self, mock_resource_server_config):
        with patch(
            "ansible_base.metrics_ingest.client.get_resource_server_config",
            return_value={**RESOURCE_SERVER_SETTINGS, "URL": GATEWAY_URL + "/"},
        ):
            from ansible_base.metrics_ingest.client import MetricsIngestClient

            c = MetricsIngestClient()
            assert "//" not in c.base_url.replace("https://", "")

    def test_default_timeout_is_short(self, mock_resource_server_config):
        from ansible_base.metrics_ingest.client import MetricsIngestClient

        c = MetricsIngestClient()
        assert c.timeout == 5

    def test_custom_timeout_accepted(self, mock_resource_server_config):
        from ansible_base.metrics_ingest.client import MetricsIngestClient

        c = MetricsIngestClient(timeout=10)
        assert c.timeout == 10


@pytest.mark.unit
class TestMetricsIngestClientRegister:
    def test_register_posts_to_register_path(self, client):
        client.register(
            service_name="aap-eda-server",
            event_name="eda_stats",
            display_name="EDA",
            version="2.5.0",
            segment_event_name="EDA Daily Stats",
            payload_schema={"type": "object", "properties": {}},
        )
        client._make_request.assert_called_once()
        method, path = client._make_request.call_args[0][:2]
        assert method == "post"
        assert path == "register/"

    def test_register_payload_contains_required_fields(self, client):
        client.register(
            service_name="aap-eda-server",
            event_name="eda_stats",
            display_name="EDA",
            version="2.5.0",
            segment_event_name="EDA Daily Stats",
            payload_schema={"type": "object"},
        )
        body = client._make_request.call_args[1]["data"]
        assert body["service_name"] == "aap-eda-server"
        assert body["event_name"] == "eda_stats"
        assert body["display_name"] == "EDA"
        assert body["version"] == "2.5.0"
        assert body["segment_event_name"] == "EDA Daily Stats"
        assert body["validate_payload"] is False

    def test_register_includes_rollup_config_when_provided(self, client):
        rollup = {"strategy": "count_by_field", "group_by": ["region"]}
        client.register(
            service_name="s", event_name="e", display_name="D",
            version="1", segment_event_name="E",
            payload_schema={}, rollup_config=rollup,
        )
        body = client._make_request.call_args[1]["data"]
        assert body["rollup_config"] == rollup

    def test_register_omits_rollup_config_when_not_provided(self, client):
        client.register(
            service_name="s", event_name="e", display_name="D",
            version="1", segment_event_name="E", payload_schema={},
        )
        body = client._make_request.call_args[1]["data"]
        assert "rollup_config" not in body


@pytest.mark.unit
class TestMetricsIngestClientSendEvent:
    def test_send_event_posts_to_events_path(self, client):
        client.send_event("svc", "evt", {"key": "val"})
        method, path = client._make_request.call_args[0][:2]
        assert method == "post"
        assert path == "events/"

    def test_send_event_payload_type_is_event(self, client):
        client.send_event("svc", "evt", {"key": "val"})
        body = client._make_request.call_args[1]["data"]
        assert body["payload_type"] == "event"

    def test_send_event_includes_payload(self, client):
        payload = {"tool_name": "get_job_status", "http_status": 200}
        client.send_event("svc", "evt", payload)
        body = client._make_request.call_args[1]["data"]
        assert body["payload"] == payload

    def test_send_event_uses_provided_timestamp(self, client):
        ts = "2026-08-06T10:00:00+00:00"
        client.send_event("svc", "evt", {}, event_timestamp=ts)
        body = client._make_request.call_args[1]["data"]
        assert body["event_timestamp"] == ts

    def test_send_event_defaults_timestamp_to_now(self, client):
        client.send_event("svc", "evt", {})
        body = client._make_request.call_args[1]["data"]
        assert "event_timestamp" in body
        assert body["event_timestamp"] is not None


@pytest.mark.unit
class TestMetricsIngestClientSendBatch:
    def test_send_batch_payload_type_is_batch(self, client):
        client.send_batch("svc", "evt", {}, "2026-08-05T00:00:00Z", "2026-08-05T23:59:59Z")
        body = client._make_request.call_args[1]["data"]
        assert body["payload_type"] == "batch"

    def test_send_batch_includes_collection_window(self, client):
        client.send_batch("svc", "evt", {}, "2026-08-05T00:00:00Z", "2026-08-05T23:59:59Z")
        body = client._make_request.call_args[1]["data"]
        assert body["collection_start"] == "2026-08-05T00:00:00Z"
        assert body["collection_end"] == "2026-08-05T23:59:59Z"


@pytest.mark.unit
class TestMetricsIngestClientGetStatus:
    def test_get_status_calls_status_path(self, client):
        client.get_status()
        method, path = client._make_request.call_args[0][:2]
        assert method == "get"
        assert path == "status/"

    def test_get_status_no_params_when_no_service_name(self, client):
        client.get_status()
        kwargs = client._make_request.call_args[1]
        assert kwargs.get("params", {}) == {}

    def test_get_status_sends_service_name_param(self, client):
        client.get_status(service_name="aap-eda-server")
        kwargs = client._make_request.call_args[1]
        assert kwargs["params"] == {"service_name": "aap-eda-server"}
