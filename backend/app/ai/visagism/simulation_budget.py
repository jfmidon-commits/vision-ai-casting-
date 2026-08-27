"""Persistent per-analysis budget guard for paid visual simulations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Optional

from sqlalchemy import and_, select

from app.database import AsyncSessionLocal
from app.models import Analysis

BUDGET_FIELD = "simulation_budget_v1"


@dataclass(frozen=True)
class SimulationBudgetDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int = 0
    reason: Optional[str] = None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def recent_attempts(
    values: Iterable[Any], *, now: datetime, window_seconds: int
) -> List[datetime]:
    cutoff = now - timedelta(seconds=max(1, int(window_seconds)))
    parsed = [_parse_timestamp(value) for value in values]
    return sorted(item for item in parsed if item is not None and item >= cutoff)


def evaluate_budget(
    values: Iterable[Any],
    *,
    now: datetime,
    max_attempts: int,
    window_seconds: int,
) -> SimulationBudgetDecision:
    maximum = max(1, int(max_attempts))
    recent = recent_attempts(values, now=now, window_seconds=window_seconds)
    if len(recent) < maximum:
        return SimulationBudgetDecision(
            allowed=True,
            remaining=max(0, maximum - len(recent) - 1),
        )
    oldest = recent[0]
    retry_at = oldest + timedelta(seconds=max(1, int(window_seconds)))
    retry_after = max(1, int((retry_at - now).total_seconds()))
    return SimulationBudgetDecision(
        allowed=False,
        remaining=0,
        retry_after_seconds=retry_after,
        reason="simulation_budget_exhausted",
    )


async def claim_simulation_budget(
    *,
    analysis_id: Any,
    tenant_id: Any,
    max_attempts: int,
    window_seconds: int,
) -> SimulationBudgetDecision:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Analysis)
            .where(and_(Analysis.id == analysis_id, Analysis.tenant_id == tenant_id))
            .with_for_update()
        )
        analysis = result.scalar_one_or_none()
        if analysis is None:
            return SimulationBudgetDecision(
                allowed=False,
                remaining=0,
                reason="analysis_not_found",
            )

        visagism = (
            dict(analysis.visagism) if isinstance(analysis.visagism, dict) else {}
        )
        raw_budget = visagism.get(BUDGET_FIELD)
        budget = raw_budget if isinstance(raw_budget, dict) else {}
        raw_attempts = budget.get("attempts")
        attempts = raw_attempts if isinstance(raw_attempts, list) else []
        decision = evaluate_budget(
            attempts,
            now=now,
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )
        if not decision.allowed:
            await session.rollback()
            return decision

        recent = recent_attempts(attempts, now=now, window_seconds=window_seconds)
        recent.append(now)
        visagism[BUDGET_FIELD] = {
            "attempts": [item.isoformat() for item in recent],
            "max_attempts": max(1, int(max_attempts)),
            "window_seconds": max(1, int(window_seconds)),
            "last_attempt_at": now.isoformat(),
        }
        analysis.visagism = visagism
        await session.commit()
        return decision
