import os
import logging

class PipelineLogger:
    def __init__(self, log_dir: str = "RAG-PIPELINE/logs"):
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
            
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def log_phase(self, phase_name: str, status: str, details: str = ""):
        msg = f"PHASE: {phase_name} | STATUS: {status} | {details}"
        if status == "ERROR": self.logger.error(msg)
        elif status == "WARNING": self.logger.warning(msg)
        else: self.logger.info(msg)

    def log_phase_1(self, pdf_name: str, file_id: str, exists: bool, collection_status: str, points_deleted: bool):
        """Logs detailed status for Phase 1: Splitting & Metadata"""
        details = (f"FileID: {file_id[:8]}... | Exists: {exists} | "
                   f"Collection: {collection_status} | Cleaned Old Points: {points_deleted}")
        self.log_phase("Split & Metadata", "COMPLETED", f"{pdf_name} | {details}")

    def log_phase_2(self, split_file: str, ocr_status: str, translated: bool, chunks: int, time_taken: float):
        """Logs detailed status for Phase 2: OCR & Chunking"""
        details = (f"OCR: {ocr_status} | Translated: {translated} | "
                   f"Chunks: {chunks} | Time: {time_taken:.1f}s")
        self.log_phase("OCR & Parsing", "COMPLETED", f"{split_file} | {details}")

    def log_phase_3(self, book_name: str, total_chunks: int, imported: int, failed: int, collection_size_before: int, collection_size_after: int):
        """Logs detailed status for Phase 3: Embedding & Indexing"""
        details = (f"Total Chunks: {total_chunks} | Imported: {imported} | Failed: {failed} | "
                   f"Collection Size: {collection_size_before} -> {collection_size_after}")
        self.log_phase("Embedding", "COMPLETED", f"{book_name} | {details}")

    def log_info(self, message: str): self.logger.info(message)
    def log_warning(self, message: str): self.logger.warning(message)
    def log_error(self, message: str): self.logger.error(message)

pipeline_logger = PipelineLogger()
