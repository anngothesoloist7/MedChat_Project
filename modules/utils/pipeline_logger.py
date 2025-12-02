import os
import logging
from datetime import datetime

class PipelineLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "pipeline_status.log")
        
        self.logger = logging.getLogger("PipelineLogger")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
            # Also log to console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def log_phase(self, phase_name: str, status: str, details: str = ""):
        msg = f"PHASE: {phase_name} | STATUS: {status} | {details}"
        if status == "ERROR":
            self.logger.error(msg)
        elif status == "WARNING":
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def log_info(self, message: str):
        self.logger.info(message)

    def log_warning(self, message: str):
        self.logger.warning(message)

    def log_error(self, message: str):
        self.logger.error(message)

# Global logger instance
pipeline_logger = PipelineLogger()
