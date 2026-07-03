"""定时任务调度器 - 每天定时更新数据

分层更新策略：
1. 学校学区数据（rxyj API）：每周一凌晨3点更新，全量约5分钟
2. 小区价格数据（贝壳）：按区轮询，每天凌晨4点更新1-2个区，7天覆盖全部区域
3. 前端数据构建：每次更新完成后自动重建

使用方法：
  python3 scheduler.py           # 启动调度器（后台运行）
  python3 scheduler.py --run-now # 立即执行一次所有任务

使用Python内置模块实现，无需外部依赖
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "data" / "scripts"

DISTRICT_LIST = [
    "西湖区", "上城区", "拱墅区", "滨江区",
    "钱塘区", "余杭区", "临平区", "临安区",
    "桐庐县", "淳安县", "建德市"
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "data" / "scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_script(script_name, *args):
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)] + list(args)
    logger.info(f"执行脚本: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if result.returncode == 0:
            logger.info(f"脚本执行成功: {script_name}")
            if result.stdout:
                logger.debug(f"输出: {result.stdout[:200]}")
        else:
            logger.error(f"脚本执行失败: {script_name}, 返回码: {result.returncode}")
            if result.stderr:
                logger.error(f"错误: {result.stderr[:500]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error(f"脚本执行超时: {script_name}")
        return False
    except Exception as e:
        logger.error(f"脚本执行异常: {script_name}, 错误: {e}")
        return False


def update_school_data():
    logger.info("========== 开始更新学校数据 ==========")
    success = run_script("fetch_rxyj_schools.py")
    if success:
        run_script("build_frontend_data.py")
        logger.info("========== 学校数据更新完成 ==========")
    else:
        logger.error("========== 学校数据更新失败 ==========")


def update_price_data():
    logger.info("========== 开始更新小区价格数据 ==========")
    
    today = datetime.now()
    day_of_week = today.weekday()
    
    districts_to_update = []
    if day_of_week == 0:
        districts_to_update = ["西湖区", "上城区"]
    elif day_of_week == 1:
        districts_to_update = ["拱墅区", "滨江区"]
    elif day_of_week == 2:
        districts_to_update = ["钱塘区", "余杭区"]
    elif day_of_week == 3:
        districts_to_update = ["临平区", "临安区"]
    elif day_of_week == 4:
        districts_to_update = ["桐庐县", "淳安县"]
    elif day_of_week == 5:
        districts_to_update = ["建德市"]
    else:
        districts_to_update = ["西湖区"]
    
    logger.info(f"今日更新区域: {districts_to_update}")
    
    all_success = True
    for district in districts_to_update:
        success = run_script("crawl_community_prices.py", "--district", district)
        if not success:
            all_success = False
    
    if all_success:
        run_script("build_frontend_data.py")
        logger.info("========== 小区价格数据更新完成 ==========")
    else:
        logger.error("========== 小区价格数据更新部分失败 ==========")


def update_transaction_data():
    logger.info("========== 开始更新成交数据 ==========")
    
    today = datetime.now()
    day_of_week = today.weekday()
    
    districts_to_update = []
    if day_of_week == 0:
        districts_to_update = ["西湖区", "上城区"]
    elif day_of_week == 1:
        districts_to_update = ["拱墅区", "滨江区"]
    elif day_of_week == 2:
        districts_to_update = ["钱塘区", "余杭区"]
    elif day_of_week == 3:
        districts_to_update = ["临平区", "临安区"]
    elif day_of_week == 4:
        districts_to_update = ["桐庐县", "淳安县"]
    elif day_of_week == 5:
        districts_to_update = ["建德市"]
    else:
        districts_to_update = ["西湖区"]
    
    logger.info(f"今日更新成交数据区域: {districts_to_update}")
    
    all_success = True
    for district in districts_to_update:
        success = run_script("crawl_transactions.py", "--district", district)
        if not success:
            all_success = False
    
    if all_success:
        run_script("build_transaction_data.py")
        logger.info("========== 成交数据更新完成 ==========")
    else:
        logger.error("========== 成交数据更新部分失败 ==========")


def build_frontend_data():
    logger.info("========== 开始构建前端数据 ==========")
    success = run_script("build_frontend_data.py")
    if success:
        run_script("build_community_prices.py")
        run_script("build_primary_data.py")
        run_script("build_price_data.py")
        run_script("build_transaction_data.py")
        logger.info("========== 前端数据构建完成 ==========")
    else:
        logger.error("========== 前端数据构建失败 ==========")


def get_next_run_time(hour, minute=0):
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def is_monday():
    return datetime.now().weekday() == 0


def start_scheduler():
    logger.info("启动定时任务调度器...")
    
    try:
        while True:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            if current_hour == 3 and current_minute == 0 and is_monday():
                update_school_data()
                time.sleep(60)
            
            elif current_hour == 4 and current_minute == 0:
                update_price_data()
                time.sleep(60)
            
            elif current_hour == 5 and current_minute == 0:
                update_transaction_data()
                time.sleep(60)
            
            elif current_hour == 6 and current_minute == 0:
                build_frontend_data()
                time.sleep(60)
            
            time.sleep(30)
    
    except (KeyboardInterrupt, SystemExit):
        logger.info("停止定时任务调度器...")


def run_all_tasks():
    logger.info("立即执行所有更新任务...")
    update_school_data()
    update_price_data()
    update_transaction_data()
    build_frontend_data()
    logger.info("所有任务执行完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="定时任务调度器")
    parser.add_argument("--run-now", action="store_true", help="立即执行一次所有任务")
    args = parser.parse_args()
    
    if args.run_now:
        run_all_tasks()
    else:
        start_scheduler()