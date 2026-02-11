from locust import LoadTestShape
from src.config.manager import config
import logging
import os

logger = logging.getLogger(__name__)

class ConfigurableShape(LoadTestShape):
    """
    Reads 'load_shape' from the project configuration.
    
    Example config (in yaml):
    load_shape:
      stages:
        - duration: 60
          users: 10
          spawn_rate: 1
        - duration: 120
          users: 50
          spawn_rate: 2
    """
    
    def __init__(self):
        super().__init__()
        self.project_name = os.getenv("PROJECT")
        self.config = config.get_project_config(self.project_name) if self.project_name else {}
        self.stages = self.config.get("load_shape", {}).get("stages", [])
        
        if self.stages:
            logger.info(f"Loaded {len(self.stages)} stages from config.")
            # Sort stages by duration just in case
            self.stages.sort(key=lambda x: x["duration"])
        else:
            logger.info("No load_shape configured. Using standard CLI/Web UI parameters.")

    def tick(self):
        if not self.stages:
            return None

        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                try:
                    tick_data = (stage["users"], stage["spawn_rate"])
                    return tick_data
                except KeyError:
                    logger.error("Invalid stage configuration. Must contain 'users' and 'spawn_rate'.")
                    return None

        # End of stages: stop the test (return None) or keep last stage?
        # Usually return None to let it stop or finish
        return None
