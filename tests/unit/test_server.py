from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from src.main import JobResult
from src.models import AnalysisResult, FetchMode, FetchResult, RunResult, TradingDayClose
from src.server import create_app, job_result_to_dict


def _run_result(mode: FetchMode = FetchMode.FULL) -> RunResult:
    closes = [
        TradingDayClose(date=date(2024, 1, 1) + timedelta(days=i), close=2000.0 - i)
        for i in range(252)
    ]
    fetch = FetchResult(mode=mode, trading_days=len(closes), closes=closes)
    return RunResult(fetch=fetch, analysis=AnalysisResult(breach=None))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> pytest.FixtureRequest:
    mock_job = MagicMock(
        return_value=JobResult(
            status="silent",
            run=_run_result(),
            notifications=(),
        )
    )
    app = create_app(
        run_job_fn=mock_job,
        cron_secret_fn=lambda: "test-secret",
    )
    app.config["TESTING"] = True
    return app.test_client()


class TestHealth:
    def test_health_returns_ok(self, client: pytest.FixtureRequest) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}


class TestRunEndpoint:
    def test_run_requires_secret(self, client: pytest.FixtureRequest) -> None:
        response = client.post("/run")
        assert response.status_code == 401
        assert response.get_json()["error"] == "unauthorized"

    def test_run_rejects_wrong_secret(self, client: pytest.FixtureRequest) -> None:
        response = client.post(
            "/run",
            headers={"X-Cron-Secret": "wrong"},
        )
        assert response.status_code == 401

    def test_run_accepts_header_secret(self, client: pytest.FixtureRequest) -> None:
        response = client.post(
            "/run",
            headers={"X-Cron-Secret": "test-secret"},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "silent"
        assert body["fetch_mode"] == "full"
        assert body["trading_days"] == 252

    def test_run_accepts_query_secret(self, client: pytest.FixtureRequest) -> None:
        response = client.post("/run?secret=test-secret")
        assert response.status_code == 200

    def test_run_returns_503_when_secret_not_configured(self) -> None:
        app = create_app(
            run_job_fn=lambda: JobResult(status="silent", run=_run_result(), notifications=()),
            cron_secret_fn=lambda: None,
        )
        app.config["TESTING"] = True
        response = app.test_client().post(
            "/run",
            headers={"X-Cron-Secret": "anything"},
        )
        assert response.status_code == 503


class TestJobResultJson:
    def test_serializes_notifications(self) -> None:
        from src.notifier import DispatchResult

        result = JobResult(
            status="price_alert",
            run=_run_result(),
            notifications=(DispatchResult(email_sent=True, whatsapp_sent=True),),
        )
        payload = job_result_to_dict(result)
        assert payload["notifications"] == [
            {"email_sent": True, "whatsapp_sent": True},
        ]
