"""Run one persisted business-story retry, if one is due."""

import sys

from logger import get_logger
from main import main
from modules.state_manager import StateManager
from modules.telegram_bot import send_automation_alert


logger = get_logger(__name__)


def run():
    state_manager = StateManager()
    job = state_manager.claim_pending_business_story()
    if not job:
        logger.info("No pending business-story retry is due.")
        return 0

    logger.info("Claimed pending business-story retry #%s (attempt %s).", job["id"], job["attempt_count"])
    payload = job["payload"]
    try:
        succeeded = main(
            company_override=payload["company"],
            metrics_override=payload["metrics"],
            state_manager=state_manager,
            retry_job_id=job["id"],
        )
        return 0 if succeeded else 1
    except Exception as error:
        logger.exception("Pending business-story retry #%s raised an exception.", job["id"])
        exhausted = state_manager.defer_business_story_retry(job["id"], str(error))
        if exhausted:
            send_automation_alert(
                f"待重試工作 #{job['id']} 已達重試上限，請檢查 GitHub Actions 執行紀錄。"
            )
        else:
            send_automation_alert(
                f"待重試工作 #{job['id']} 執行失敗，已安排稍後再次嘗試。"
            )
        return 1


if __name__ == "__main__":
    sys.exit(run())
