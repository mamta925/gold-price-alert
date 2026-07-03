from __future__ import annotations

import hmac
import os
from collections.abc import Callable

from flask import Flask, jsonify, request

from src.main import JobResult, run_daily_job

RunJobFn = Callable[[], JobResult]
CronSecretFn = Callable[[], str | None]


def job_result_to_dict(result: JobResult) -> dict[str, object]:
    run = result.run
    breach = run.analysis.breach if run else None
    payload: dict[str, object] = {
        "status": result.status,
        "should_alert": run.should_alert if run else False,
        "window_key": breach.window_key if breach else None,
        "notifications": [
            {"email_sent": n.email_sent, "whatsapp_sent": n.whatsapp_sent}
            for n in result.notifications
        ],
    }
    if run is not None:
        payload["fetch_mode"] = run.fetch.mode.value
        payload["trading_days"] = run.fetch.trading_days
    else:
        payload["fetch_mode"] = None
        payload["trading_days"] = None
    return payload


def _extract_secret() -> str | None:
    header = request.headers.get("X-Cron-Secret")
    if header:
        return header
    return request.args.get("secret")


def _secrets_match(expected: str, provided: str) -> bool:
    return hmac.compare_digest(expected, provided)


def create_app(
    run_job_fn: RunJobFn = run_daily_job,
    cron_secret_fn: CronSecretFn | None = None,
) -> Flask:
    secret_fn = cron_secret_fn or (lambda: os.environ.get("CRON_SECRET"))

    app = Flask(__name__)

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return jsonify(status="ok"), 200

    @app.post("/run")
    def run_job() -> tuple[dict[str, object], int]:
        expected = secret_fn()
        if not expected:
            return jsonify(error="CRON_SECRET not configured"), 503

        provided = _extract_secret()
        if not provided or not _secrets_match(expected, provided):
            return jsonify(error="unauthorized"), 401

        result = run_job_fn()
        return jsonify(job_result_to_dict(result)), 200

    return app
