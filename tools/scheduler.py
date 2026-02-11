import schedule
import time
import subprocess
import logging
import argparse
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def job(project, env, users, rate, run_time, output):
    logger.info(f"Running scheduled job for {project}...")
    cmd = [
        "python3", "tools/run_test.py",
        "-p", project,
        "-e", env,
        "-u", str(users),
        "-r", str(rate),
        "-t", run_time,
        "-o", output
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple Scheduler for Locust Tests")
    parser.add_argument("--mode", choices=["interval", "daily"], help="Schedule mode: interval (minutes) or daily (at specific time)")
    parser.add_argument("--at", help="Time to run for daily mode (HH:MM)")
    parser.add_argument("--interval", type=int, help="Interval in minutes (for interval mode)")
    parser.add_argument("-p", "--project", required=True, help="Project name")
    parser.add_argument("-e", "--env", default="dev", help="Environment")
    parser.add_argument("-u", "--users", type=int, default=1, help="Number of users")
    parser.add_argument("-r", "--rate", type=float, default=1, help="Spawn rate")
    parser.add_argument("-t", "--time", default="10s", help="Run time")
    parser.add_argument("-o", "--output", default="reports", help="Output directory")

    args = parser.parse_args()

    # Load defaults from config
    os.environ["LOCUST_ENV"] = args.env
    from src.config.manager import config
    
    scheduler_config = config.get("scheduler", {})
    
    # Resolve parameters: CLI Args > Config > Defaults
    mode = args.mode or scheduler_config.get("mode", "daily")
    at_time = args.at or scheduler_config.get("at", "00:00")
    interval = args.interval or scheduler_config.get("interval", 60)

    # Schedule the job
    if mode == "daily":
        schedule.every().day.at(at_time).do(job, args.project, args.env, args.users, args.rate, args.time, args.output)
        logger.info(f"Scheduler started. Running {args.project} every day at {at_time}.")
    else:
        schedule.every(interval).minutes.do(job, args.project, args.env, args.users, args.rate, args.time, args.output)
        logger.info(f"Scheduler started. Running {args.project} every {interval} minutes.")
    
    # Run once immediately for verification? 
    # job(args.project, args.env, args.users, args.rate, args.time, args.output)
    
    while True:
        schedule.run_pending()
        time.sleep(1)
