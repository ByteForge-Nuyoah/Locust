import os
import importlib
import glob
from locust import events, User
from src.common.influxdb_listener import InfluxDBListener
from src.config.manager import config
from src.common.logger_utils import setup_logger

import logging
import psutil
import threading
import time

# Configure logging using common utility
root_logger = setup_logger(level=logging.INFO)
logger = logging.getLogger(__name__)

# 0. System Resource Monitoring
def monitor_resources():
    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        if cpu_usage > 85 or memory_usage > 85:
            logger.warning(f"High Resource Usage! CPU: {cpu_usage}%, Memory: {memory_usage}%")
        time.sleep(5)

# Start monitoring in a separate thread if not already running
# Simple check to avoid multiple threads in reloading
if not any(t.name == "ResourceMonitor" for t in threading.enumerate()):
    t = threading.Thread(target=monitor_resources, name="ResourceMonitor", daemon=True)
    t.start()
    logger.info("System Resource Monitor started.")

# 1. Initialize Infrastructure
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    InfluxDBListener(environment)

# 2. Dynamic Scenario Loading based on Project
project_name = os.getenv("PROJECT")
if not project_name:
    logger.warning("'PROJECT' environment variable not set. Loading all scenarios might fail or be unexpected.")
    logger.info("Usage: PROJECT=crm locust")

# Load configuration for the project to set defaults (like Host)
project_config = config.get_project_config(project_name) if project_name else {}
default_host = project_config.get("host")

# Conditionally load LoadShape if configured
load_shape_config = project_config.get("load_shape")
if load_shape_config and load_shape_config.get("stages"):
    from src.common.shapes import ConfigurableShape
    logger.info("LoadShape configured, enabled ConfigurableShape.")
else:
    logger.info("No load_shape configured, using standard CLI/Web UI parameters.")

logger.info(f"Loading project: {project_name} | Env: {os.getenv('LOCUST_ENV', 'dev')} | Host: {default_host}")

def load_scenarios():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define search paths
    # If PROJECT is set, only load projects/<project>/scenarios/**/*.py
    # Else, load all projects/*/scenarios/**/*.py
    if project_name:
        search_pattern = os.path.join(base_dir, "projects", project_name, "scenarios", "**", "*.py")
    else:
        search_pattern = os.path.join(base_dir, "projects", "*", "scenarios", "**", "*.py")
    
    files = glob.glob(search_pattern, recursive=True)
    
    for file_path in files:
        if "__init__" in file_path:
             # Generated scripts usually need manual import or are sub-modules
             # We can decide to include them if they are robust
             pass
        
        # Convert file path to module path
        rel_path = os.path.relpath(file_path, base_dir)
        module_name = rel_path.replace(os.sep, ".")[:-3] # remove .py
        
        try:
            module = importlib.import_module(module_name)
            
            # Auto-configure User classes with Project settings if they don't have one
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it is a subclass of User (and not User itself)
                if isinstance(attr, type) and issubclass(attr, User) and attr is not User:
                    # Skip abstract classes
                    if getattr(attr, "abstract", False):
                        continue

                    # Only register classes defined in the module (exclude imported base classes)
                    if attr.__module__ != module.__name__:
                        continue

                    # Auto-configure host
                    if hasattr(attr, "host") and hasattr(attr, "tasks"):
                         if default_host and (attr.host is None or attr.host == "https://www.example.com"):
                            attr.host = default_host
                            logger.info(f"Auto-configured host for {attr_name}: {default_host}")
                    
                    # Register to globals so Locust can find it
                    globals()[attr_name] = attr
                    logger.info(f"Registered User class: {attr_name}")
                        
        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")

# Execute loading
load_scenarios()

