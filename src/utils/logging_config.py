"""
Konfigurácia logging systému pre Intrastat aplikáciu.
"""
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

from ..config import AppSettings


def setup_logging(settings: Optional[AppSettings] = None) -> None:
    """
    Nastaví logging systém pre aplikáciu.
    
    Args:
        settings: Nastavenia aplikácie. Ak nie sú poskytnuté, použijú sa default hodnoty.
    """
    if settings is None:
        # Default nastavenia ak nie sú poskytnuté
        log_level = "INFO"
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logs_dir = "logs"
    else:
        log_level = settings.log_level
        log_format = settings.log_format
        logs_dir = settings.logs_dir
    
    # Vytvorí logs adresár ak neexistuje
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    
    # Nastavenie log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Vytvorenie formattera
    formatter = logging.Formatter(log_format)
    
    # Root logger konfigurácia
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Vyčistenie existujúcich handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler s rotáciou
    log_file = os.path.join(logs_dir, "intrastat.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Error log súbor
    error_log_file = os.path.join(logs_dir, "errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Log štartu aplikácie
    logging.info("Logging systém bol úspešne inicializovaný")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Log súbory: {log_file}, {error_log_file}")


class ProcessingMetrics:
    """Trieda pre sledovanie metrík spracovania."""
    
    def __init__(self):
        self.processed_pdfs = 0
        self.failed_pdfs = 0
        self.ai_api_calls = 0
        self.processing_time = 0.0
        self.start_time = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def start_processing(self) -> None:
        """Začne meranie času spracovania."""
        import time
        self.start_time = time.time()
        self.logger.info("Začalo spracovanie PDF súborov")
    
    def pdf_processed_successfully(self, pdf_name: str) -> None:
        """Zaznamená úspešne spracovaný PDF."""
        self.processed_pdfs += 1
        self.logger.info(f"Úspešne spracovaný PDF: {pdf_name}")
    
    def pdf_failed(self, pdf_name: str, error: str) -> None:
        """Zaznamená neúspešne spracovaný PDF."""
        self.failed_pdfs += 1
        self.logger.error(f"Chyba pri spracovaní PDF {pdf_name}: {error}")
    
    def ai_call_made(self, model_name: str, operation: str) -> None:
        """Zaznamená AI API volanie."""
        self.ai_api_calls += 1
        self.logger.debug(f"AI volanie: {model_name} - {operation}")
    
    def finish_processing(self) -> None:
        """Ukončí meranie a zapíše súhrn."""
        if self.start_time:
            import time
            self.processing_time = time.time() - self.start_time
        
        summary = self.get_summary()
        self.logger.info("Spracovanie dokončené")
        self.logger.info(f"Súhrn: {summary}")
    
    def get_summary(self) -> dict:
        """Vráti súhrn metrík."""
        total_pdfs = self.processed_pdfs + self.failed_pdfs
        success_rate = (self.processed_pdfs / total_pdfs * 100) if total_pdfs > 0 else 0
        avg_time_per_pdf = (self.processing_time / self.processed_pdfs) if self.processed_pdfs > 0 else 0
        
        return {
            "total_pdfs": total_pdfs,
            "successful": self.processed_pdfs,
            "failed": self.failed_pdfs,
            "success_rate_percent": round(success_rate, 2),
            "total_processing_time_seconds": round(self.processing_time, 2),
            "avg_time_per_pdf_seconds": round(avg_time_per_pdf, 2),
            "total_ai_calls": self.ai_api_calls
        }


def get_logger(name: str) -> logging.Logger:
    """
    Vráti logger s daným názvom.
    
    Args:
        name: Názov loggera (typicky __name__)
    
    Returns:
        Nakonfigurovaný logger
    """
    return logging.getLogger(name) 