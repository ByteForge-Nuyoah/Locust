import logging
import os

class ColoredFormatter(logging.Formatter):
    """
    Custom log formatter that adds ANSI color codes to console output based on log levels.
    """
    
    # ANSI Color Codes
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    GREEN = "\x1b[32;20m"
    CYAN = "\x1b[36;20m"
    RESET = "\x1b[0m"
    
    # Standard format string
    FORMAT_STR = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    SHORT_FORMAT_STR = "%(asctime)s [%(levelname)s] %(message)s"

    LEVEL_COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED
    }

    def __init__(self, use_short_format=False):
        super().__init__()
        self.use_short_format = use_short_format

    def format(self, record):
        log_color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        fmt = self.SHORT_FORMAT_STR if self.use_short_format else self.FORMAT_STR
        formatter = logging.Formatter(f"{log_color}{fmt}{self.RESET}")
        return formatter.format(record)

def setup_logger(name=None, level=logging.INFO, log_to_file=True, log_file="logs/locust_run.log"):
    """
    Utility function to set up a logger with colored console output and optional file output.
    
    Args:
        name: Name of the logger
        level: Logging level
        log_to_file: Whether to log to a file
        log_file: Path to the log file
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
        
    # Console Handler with color
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(use_short_format=(name is None or name == "__main__")))
    logger.addHandler(console_handler)
    
    # File Handler
    if log_to_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
        logger.addHandler(file_handler)
        
    return logger
