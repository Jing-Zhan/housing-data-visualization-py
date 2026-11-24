"""定时采集调度器：按固定间隔调用采集落库服务。

对应需求 7.3「更新频率：演示模式每 30 秒生成增量；采集模式按小时执行」，
间隔由 ``SCHEDULER_INTERVAL`` 配置（秒），开关由 ``SCHEDULER_ENABLED`` 控制。
"""

from __future__ import annotations

from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler(app, interval_seconds: int = 30) -> BackgroundScheduler:
    """启动后台调度器，每隔 ``interval_seconds`` 秒执行一次采集落库。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    from backend.services.data_service import collect_once

    def _run_safely() -> None:
        try:
            info = collect_once(app)
            app.logger.info("定时采集完成：%s", info)
        except Exception as exc:  # 采集/入库异常只记日志，不中断调度
            app.logger.error("定时采集失败：%s", exc)

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_run_safely, "interval", seconds=interval_seconds, id="collect")
    _scheduler.start()
    app.logger.info("定时采集已启动，间隔 %s 秒", interval_seconds)
    return _scheduler
