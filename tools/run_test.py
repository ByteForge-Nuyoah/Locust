import argparse
import os
import sys
import time
import subprocess
import logging

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.notifier import Notifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

import csv

from src.config.manager import config

def parse_stats(csv_file):
    """Parse Locust CSV stats file to get summary metrics and top 5 slowest requests."""
    stats = {
        "requests": 0,
        "failures": 0,
        "rps": 0.0,
        "avg_rt": 0.0,
        "min_rt": 0.0,
        "max_rt": 0.0,
        "p50_rt": 0.0,
        "p90_rt": 0.0,
        "p95_rt": 0.0,
        "p99_rt": 0.0,
        "top_slowest": []
    }
    
    if not os.path.exists(csv_file):
        logger.warning(f"Stats CSV not found: {csv_file}")
        return stats
        
    all_requests = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name")
                if name in ["Aggregated", "Total"]:
                    stats["requests"] = int(row.get("Request Count", 0))
                    stats["failures"] = int(row.get("Failure Count", 0))
                    stats["rps"] = float(row.get("Requests/s", 0))
                    
                    # Parse Response Times
                    stats["avg_rt"] = float(row.get("Average Response Time", 0))
                    stats["min_rt"] = float(row.get("Min Response Time", 0))
                    stats["max_rt"] = float(row.get("Max Response Time", 0))
                    
                    # Parse Percentiles
                    stats["p50_rt"] = float(row.get("50%", 0))
                    stats["p90_rt"] = float(row.get("90%", 0))
                    stats["p95_rt"] = float(row.get("95%", 0))
                    stats["p99_rt"] = float(row.get("99%", 0))
                else:
                    # Collect individual request data
                    all_requests.append({
                        "method": row.get("Type", ""),
                        "name": name,
                        "avg": float(row.get("Average Response Time", 0)),
                        "p95": float(row.get("95%", 0)),
                        "count": int(row.get("Request Count", 0))
                    })
        
        # Sort by p95 response time descending and take top 5
        stats["top_slowest"] = sorted(all_requests, key=lambda x: x["p95"], reverse=True)[:5]
        
    except Exception as e:
        logger.error(f"Failed to parse stats CSV: {e}")
        
    return stats

def run_test(project, env, users, rate, run_time, output_dir):
    """
    Run Locust test via subprocess, generate report, and send notifications.
    """
    logger.info(f"Starting test for project: {project} (Env: {env})")
    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"{project}_{env}_{timestamp}"
    report_file = os.path.join(output_dir, f"{base_name}.html")
    csv_prefix = os.path.join(output_dir, base_name)
    
    # Construct Locust command
    # Assuming locustfile.py is in project root
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--headless",
        "-u", str(users),
        "-r", str(rate),
        "-t", run_time,
        "--html", report_file,
        "--csv", csv_prefix
    ]
    
    # Set Environment Variables
    env_vars = os.environ.copy()
    env_vars["PROJECT"] = project
    env_vars["LOCUST_ENV"] = env
    
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    start_time_str = time.strftime("%Y-%m-%d %H:%M:%S")
    start_time = time.time()
    
    try:
        # Run Locust
        # We capture output to parse stats roughly if needed, or just let it print
        result = subprocess.run(cmd, env=env_vars, check=False, text=True, capture_output=True)
        
        end_time = time.time()
        duration_seconds = end_time - start_time
        duration_str = f"{duration_seconds:.2f} s"
        
        # Log stdout/stderr
        logger.info("Test execution finished.")
        if result.returncode != 0:
            logger.warning(f"Locust exited with code {result.returncode}")
            logger.error(result.stderr)
        else:
            logger.info(result.stdout)

        # Check if report exists
        if os.path.exists(report_file):
            logger.info(f"Report generated: {report_file}")
            
            # Parse stats from generated CSV
            stats_csv = f"{csv_prefix}_stats.csv"
            stats = parse_stats(stats_csv)
            
            # Add extra context for notification
            project_config = config.get_project_config(project)
            stats["host"] = project_config.get("host", "Unknown")
            stats["start_time"] = start_time_str
            stats["duration"] = duration_str
            stats["users"] = users
            
            logger.info(f"Parsed Stats: {stats}")
            
            # Send Notification
            notifier = Notifier()
            notifier.send_report(report_file, project, stats)
        else:
            logger.error("Report file was not generated.")
            
    except Exception as e:
        logger.error(f"Test run failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Locust Test with Reporting & Notifications")
    parser.add_argument("-p", "--project", required=True, help="Project name (e.g., website)")
    parser.add_argument("-e", "--env", default="dev", help="Environment (dev/prod)")
    parser.add_argument("-u", "--users", type=int, default=1, help="Number of users")
    parser.add_argument("-r", "--rate", type=float, default=1, help="Spawn rate")
    parser.add_argument("-t", "--time", default="10s", help="Run time (e.g., 10s, 1m)")
    parser.add_argument("-o", "--output", default="reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    run_test(args.project, args.env, args.users, args.rate, args.time, args.output)
