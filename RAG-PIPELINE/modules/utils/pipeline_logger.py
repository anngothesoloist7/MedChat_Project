import os
import logging
from modules.config import Config

class PipelineLogger:
    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or str(Config.LOGS_DIR)
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "pipeline_status.log")
        
        self.logger = logging.getLogger("PipelineLogger")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh = logging.FileHandler(self.log_file, encoding='utf-8')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        self.callbacks = []

    def register_callback(self, callback):
        """Register a function to be called with log messages."""
        self.callbacks.append(callback)

    def _notify_callbacks(self, message: str):
        for cb in self.callbacks:
            try: cb(message)
            except: pass

    def log_phase(self, phase_name: str, status: str, details: str = ""):
        msg = f"PHASE: {phase_name} | STATUS: {status} | {details}"
        if status == "ERROR": self.logger.error(msg)
        elif status == "WARNING": self.logger.warning(msg)
        else: self.logger.info(msg)
        self._notify_callbacks(msg)

    def log_phase_1(self, pdf_name: str, file_id: str, exists: bool, collection_status: str, points_deleted: bool):
        details = (f"FileID: {file_id[:8]}... | Exists: {exists} | "
                   f"Collection: {collection_status} | Cleaned Old Points: {points_deleted}")
        self.log_phase("Split & Metadata", "COMPLETED", f"{pdf_name} | {details}")

    def log_phase_2(self, split_file: str, ocr_status: str, translated: bool, chunks: int, time_taken: float):
        details = (f"OCR: {ocr_status} | Translated: {translated} | "
                   f"Chunks: {chunks} | Time: {time_taken:.1f}s")
        self.log_phase("OCR & Parsing", "COMPLETED", f"{split_file} | {details}")

    def log_phase_3(self, book_name: str, total_chunks: int, imported: int, failed: int, collection_size_before: int, collection_size_after: int):
        details = (f"Total Chunks: {total_chunks} | Imported: {imported} | Failed: {failed} | "
                   f"Collection Size: {collection_size_before} -> {collection_size_after}")
        self.log_phase("Embedding", "COMPLETED", f"{book_name} | {details}")

    def log_info(self, message: str): 
        # Ensure message has [INFO] prefix if not already present
        if not message.startswith("["): message = f"[INFO] {message}"
        self.logger.info(message)
        self._notify_callbacks(message)

    def log_warning(self, message: str): 
        self.logger.warning(message)
        self._notify_callbacks(message)

    def log_error(self, message: str): 
        self.logger.error(message)
        self._notify_callbacks(message)

pipeline_logger = PipelineLogger()
