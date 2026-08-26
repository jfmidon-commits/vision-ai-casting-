"""Memory instrumentation - reads RSS from /proc on Linux (Render)."""

from app.utils.logger import get_logger

logger = get_logger(__name__)


def log_rss(stage: str, analysis_id: str = "unknown"):
    """Log current RSS in MB via /proc/self/status. Returns MB or None."""
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    kb = int(line.split()[1])
                    mb = round(kb / 1024.0, 1)
                    logger.info(
                        "[RSS] analysis_id=%s stage=%s rss_mb=%.1f",
                        analysis_id,
                        stage,
                        mb,
                    )
                    return mb
    except Exception as exc:
        logger.debug("RSS read failed: %s", exc)
        return None
