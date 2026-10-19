import logging
import os
import threading

from app.db.connection import get_connection
from app.db.queries.subscriptions_queries import GET_DUE_SUBSCRIPTIONS
from app.utils.plans import _settle_subscription


logger = logging.getLogger(__name__)


DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60


def _settle_due_subscription(conn, subscription: dict) -> bool:
    """
    Settles a single expired subscription in its own transaction.
    Returns True when it settled, False when it failed (and rolled back).
    """

    cursor = conn.cursor(dictionary=True)

    try:
        _settle_subscription(
            cursor,
            subscription["id"],
            subscription["user_id"],
            "COMPLETED"
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        logger.exception(
            "Failed to settle expired subscription %s",
            subscription["id"]
        )
        return False

    finally:
        cursor.close()


def run_expiry_sweep() -> int:
    """
    Settles every active subscription whose expiration date has passed.

    Runs a single pass and returns the number of subscriptions settled.
    Each subscription is committed on its own so one failure cannot undo
    the others.
    """

    conn = get_connection()
    settled = 0

    try:
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(GET_DUE_SUBSCRIPTIONS)
            due_subscriptions = cursor.fetchall()
        finally:
            cursor.close()

        for subscription in due_subscriptions:
            if _settle_due_subscription(conn, subscription):
                settled += 1

        return settled

    finally:
        conn.close()


class SettlementService:
    """
    Background worker that runs the expiry sweep every 24 hours.

    Follows the same daemon thread pattern as EmailService: it is started
    and stopped from the FastAPI lifespan and holds no extra dependencies.
    """

    def __init__(self, interval_seconds: int | None = None):
        self.interval_seconds = interval_seconds or int(
            os.getenv(
                "SETTLEMENT_INTERVAL_SECONDS",
                str(DEFAULT_INTERVAL_SECONDS)
            )
        )
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _worker(self):
        logger.info(
            "Settlement worker started (interval %ss)",
            self.interval_seconds
        )

        while not self._stop_event.wait(self.interval_seconds):
            try:
                run_expiry_sweep()
            except Exception:
                logger.exception("Expiry sweep failed")

        logger.info("Settlement worker stopped")

    def start(self):
        """Start the background worker (no-op if already running)."""

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="SettlementWorker"
        )
        self._thread.start()

    def stop(self):
        """Signal the worker to stop and wait for it to finish."""

        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None


settlement_service = SettlementService()
