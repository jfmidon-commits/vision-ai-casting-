from datetime import datetime, timedelta, timezone

from app.ai.visagism.simulation_budget import evaluate_budget, recent_attempts


def test_budget_allows_until_limit_and_reports_remaining():
    now = datetime(2026, 8, 27, 17, 0, tzinfo=timezone.utc)
    values = [(now - timedelta(minutes=5)).isoformat()] * 3
    decision = evaluate_budget(values, now=now, max_attempts=8, window_seconds=3600)
    assert decision.allowed is True
    assert decision.remaining == 4


def test_budget_blocks_at_limit_with_retry_after():
    now = datetime(2026, 8, 27, 17, 0, tzinfo=timezone.utc)
    values = [
        (now - timedelta(minutes=30) + timedelta(seconds=index)).isoformat()
        for index in range(8)
    ]
    decision = evaluate_budget(values, now=now, max_attempts=8, window_seconds=3600)
    assert decision.allowed is False
    assert decision.reason == "simulation_budget_exhausted"
    assert decision.retry_after_seconds > 0


def test_budget_prunes_expired_or_invalid_attempts():
    now = datetime(2026, 8, 27, 17, 0, tzinfo=timezone.utc)
    recent = recent_attempts(
        [
            (now - timedelta(minutes=10)).isoformat(),
            (now - timedelta(hours=2)).isoformat(),
            "invalid",
        ],
        now=now,
        window_seconds=3600,
    )
    assert len(recent) == 1
