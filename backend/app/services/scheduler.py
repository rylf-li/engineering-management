"""
定时任务 - 每日凌晨自动生成营收统计数据
"""
import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.services.revenue_stats import calculate_all_revenues

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def run_daily_stats_job():
    """每日统计任务（凌晨2点执行）"""
    db = SessionLocal()
    try:
        today = date.today()
        logger.info(f"📊 开始生成 {today} 日营收统计...")
        calculate_all_revenues(db, today)
        logger.info(f"✅ {today} 日营收统计完成")
    except Exception as e:
        logger.error(f"❌ 统计生成失败: {e}", exc_info=True)
    finally:
        db.close()


def start_scheduler():
    """启动定时调度器"""
    scheduler.add_job(
        run_daily_stats_job,
        "cron",
        hour=2,
        minute=0,
        id="daily_revenue_stats",
        name="每日营收统计",
        replace_existing=True,
    )
    # 启动后立即运行一次
    scheduler.add_job(
        run_daily_stats_job,
        "date",
        id="daily_revenue_stats_boot",
        name="启动时运行一次统计",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("⏰ 定时调度器已启动")


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⏰ 定时调度器已停止")