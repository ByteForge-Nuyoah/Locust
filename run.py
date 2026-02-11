import os
import sys
import subprocess
import webbrowser
import glob
import time
import logging
import yaml
from src.common.logger_utils import setup_logger

# Configure logging using common utility
logger = setup_logger(name="__main__", level=logging.INFO, log_to_file=False)

def load_run_config(project_name=None):
    """
    Load parameters from run_config.yaml with hierarchical support.
    Priority: project specific > default values.
    Supports environment variable substitution like ${VAR:-default}.
    """
    import re
    config_path = os.path.join(os.getcwd(), "run_config.yaml")
    
    # Final params to return
    params = {
        "project": project_name or "crm",
        "env": "dev",
        "users": "10",
        "spawn_rate": "2",
        "duration": "30s"
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 0. Substitute environment variables
                pattern = re.compile(r'\$\{(\w+)(?::-(.*?))?\}')
                def replace_match(match):
                    env_var = match.group(1)
                    default_val = match.group(2)
                    return os.getenv(env_var, default_val if default_val is not None else match.group(0))
                
                content = pattern.sub(replace_match, content)
                
                config = yaml.safe_load(content)
                if config:
                    # 1. Load default section
                    default_config = config.get("default", {})
                    params.update(default_config)
                    
                    # Ensure auto_close_delay is in params
                    params["auto_close_delay"] = default_config.get("auto_close_delay", 20)
                    
                    # 2. Load project specific section
                    target_project = project_name or params.get("project")
                    project_config = config.get("projects", {}).get(target_project, {})
                    if project_config:
                        params.update(project_config)
                        params["project"] = target_project
                        
        except Exception as e:
            logger.warning(f"⚠️ Warning: Failed to load run_config.yaml: {e}")
            
    return params

def run():
    """
    Main entry point to run Locust tests and open the report automatically.
    """
    # 1. Determine project first (from CLI or default)
    project_from_cli = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 2. Load configuration based on project
    config = load_run_config(project_from_cli)
    
    project = config.get("project")
    env = config.get("env")
    users = str(config.get("users"))
    spawn_rate = str(config.get("spawn_rate"))
    duration = config.get("duration")

    # 3. Allow overriding other params via command line
    # python3 run.py <project> <env> <users> <duration>
    if len(sys.argv) > 2:
        env = sys.argv[2]
    if len(sys.argv) > 3:
        users = sys.argv[3]
    if len(sys.argv) > 4:
        duration = sys.argv[4]

    logger.info(f"🚀 Starting Performance Test for Project: {project}, Env: {env}")
    
    # Construct the command
    cmd = [
        sys.executable, "tools/run_test.py",
        "-p", project,
        "-e", env,
        "-u", users,
        "-r", spawn_rate,
        "-t", duration
    ]

    try:
        # Run the test
        process = subprocess.run(cmd, check=True)
        
        if process.returncode == 0:
            logger.info("✅ Test completed successfully.")
            
            # Find the latest HTML report
            report_dir = os.path.join(os.getcwd(), "reports")
            html_reports = glob.glob(os.path.join(report_dir, "*.html"))
            
            if html_reports:
                # Get the newest file
                latest_report = max(html_reports, key=os.path.getmtime)
                report_url = f"file://{latest_report}"
                
                logger.info(f"📊 Opening test report: {latest_report}")
                webbrowser.open(report_url)
                
                # Auto close feature
                delay = config.get("auto_close_delay", 20)
                logger.info(f"⏱️  The report will automatically close in {delay} seconds...")
                time.sleep(delay)
                
                # On macOS, we can try to close the tab via AppleScript
                if sys.platform == "darwin":
                    close_script = f'tell application "Google Chrome" to close (tabs of windows whose URL contains "{os.path.basename(latest_report)}")'
                    subprocess.run(["osascript", "-e", close_script], capture_output=True)
                    # Also try Safari if Chrome fails or isn't used
                    close_script_safari = f'tell application "Safari" to close (tabs of windows whose URL contains "{os.path.basename(latest_report)}")'
                    subprocess.run(["osascript", "-e", close_script_safari], capture_output=True)
                
                logger.info("👋 Report closed.")
            else:
                logger.warning("⚠️ No HTML report found in reports/ directory.")
        else:
            logger.error(f"❌ Test failed with return code {process.returncode}")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error executing test: {e}")
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    run()
