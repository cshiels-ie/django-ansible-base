"""Tests for ansible_base.metrics_ingest.utils."""

from unittest.mock import MagicMock, patch

import pytest


RESOURCE_SERVER_WITH_URL = {
    "URL": "https://gateway.example.com",
    "SECRET_KEY": "test-secret-key-32-chars-minimum!!",
    "VALIDATE_HTTPS": True,
}
RESOURCE_SERVER_EMPTY = {}


@pytest.fixture(autouse=True)
def reset_client_cache():
    """Reset the module-level client cache between tests."""
    import ansible_base.metrics_ingest.utils as utils_mod

    utils_mod._cache["client"] = None
    yield
    utils_mod._cache["client"] = None


@pytest.mark.unit
class TestIsMetricsIngestEnabled:
    def test_disabled_by_default(self, settings):
        settings.METRICS_INGEST_ENABLED = False
        from ansible_base.metrics_ingest.utils import is_metrics_ingest_enabled

        assert is_metrics_ingest_enabled() is False

    def test_disabled_when_flag_missing(self, settings):
        if hasattr(settings, "METRICS_INGEST_ENABLED"):
            delattr(settings, "METRICS_INGEST_ENABLED")
        from ansible_base.metrics_ingest.utils import is_metrics_ingest_enabled

        assert is_metrics_ingest_enabled() is False

    def test_disabled_when_no_resource_server_url(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_EMPTY
        from ansible_base.metrics_ingest.utils import is_metrics_ingest_enabled

        assert is_metrics_ingest_enabled() is False

    def test_enabled_when_both_configured(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        from ansible_base.metrics_ingest.utils import is_metrics_ingest_enabled

        assert is_metrics_ingest_enabled() is True


@pytest.mark.unit
class TestGetMetricsIngestClient:
    def test_returns_none_when_disabled(self, settings):
        settings.METRICS_INGEST_ENABLED = False
        from ansible_base.metrics_ingest.utils import get_metrics_ingest_client

        assert get_metrics_ingest_client() is None

    def test_returns_client_when_enabled(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        settings.METRICS_INGEST_JWT_EXPIRATION = 60
        with patch("ansible_base.metrics_ingest.client.get_resource_server_config", return_value=RESOURCE_SERVER_WITH_URL):
            from ansible_base.metrics_ingest.utils import get_metrics_ingest_client
            from ansible_base.metrics_ingest.client import MetricsIngestClient

            client = get_metrics_ingest_client()
            assert isinstance(client, MetricsIngestClient)

    def test_client_is_cached(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        settings.METRICS_INGEST_JWT_EXPIRATION = 60
        with patch("ansible_base.metrics_ingest.client.get_resource_server_config", return_value=RESOURCE_SERVER_WITH_URL):
            from ansible_base.metrics_ingest.utils import get_metrics_ingest_client

            c1 = get_metrics_ingest_client()
            c2 = get_metrics_ingest_client()
            assert c1 is c2


@pytest.mark.unit
class TestMaybeSendEvent:
    def test_no_op_when_disabled(self, settings):
        settings.METRICS_INGEST_ENABLED = False
        from ansible_base.metrics_ingest.utils import maybe_send_event

        # Should not raise
        maybe_send_event("svc", "evt", {"k": "v"})

    def test_calls_send_event_on_client(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        mock_client = MagicMock()
        mock_client.send_event.return_value = MagicMock(ok=True, status_code=202)
        with patch("ansible_base.metrics_ingest.utils.get_metrics_ingest_client", return_value=mock_client):
            from ansible_base.metrics_ingest.utils import maybe_send_event

            maybe_send_event("aap-eda-server", "eda_stats", {"active": 47})
            mock_client.send_event.assert_called_once_with("aap-eda-server", "eda_stats", {"active": 47})

    def test_swallows_exception_from_client(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        mock_client = MagicMock()
        mock_client.send_event.side_effect = ConnectionError("timeout")
        with patch("ansible_base.metrics_ingest.utils.get_metrics_ingest_client", return_value=mock_client):
            from ansible_base.metrics_ingest.utils import maybe_send_event

            # Must not raise
            maybe_send_event("svc", "evt", {})

    def test_logs_warning_on_bad_status(self, settings, caplog):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        mock_client = MagicMock()
        mock_client.send_event.return_value = MagicMock(ok=False, status_code=500)
        with patch("ansible_base.metrics_ingest.utils.get_metrics_ingest_client", return_value=mock_client):
            import logging
            from ansible_base.metrics_ingest.utils import maybe_send_event

            with caplog.at_level(logging.WARNING, logger="ansible_base.metrics_ingest"):
                maybe_send_event("svc", "evt", {})
            assert any("HTTP 500" in r.message for r in caplog.records)


@pytest.mark.unit
class TestMaybeSendBatch:
    def test_no_op_when_disabled(self, settings):
        settings.METRICS_INGEST_ENABLED = False
        from ansible_base.metrics_ingest.utils import maybe_send_batch

        maybe_send_batch("svc", "evt", {}, "2026-08-05T00:00:00Z", "2026-08-05T23:59:59Z")

    def test_calls_send_batch_on_client(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        mock_client = MagicMock()
        mock_client.send_batch.return_value = MagicMock(ok=True, status_code=202)
        with patch("ansible_base.metrics_ingest.utils.get_metrics_ingest_client", return_value=mock_client):
            from ansible_base.metrics_ingest.utils import maybe_send_batch

            maybe_send_batch("svc", "evt", {"count": 5}, "2026-08-05T00:00:00Z", "2026-08-05T23:59:59Z")
            mock_client.send_batch.assert_called_once()

    def test_swallows_exception(self, settings):
        settings.METRICS_INGEST_ENABLED = True
        settings.RESOURCE_SERVER = RESOURCE_SERVER_WITH_URL
        mock_client = MagicMock()
        mock_client.send_batch.side_effect = TimeoutError("timed out")
        with patch("ansible_base.metrics_ingest.utils.get_metrics_ingest_client", return_value=mock_client):
            from ansible_base.metrics_ingest.utils import maybe_send_batch

            maybe_send_batch("svc", "evt", {}, "s", "e")
