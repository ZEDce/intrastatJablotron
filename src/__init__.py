"""
Intrastat Asistent - Hlavný package.

Refaktorovaná verzia s modulárnou architektúrou.
"""

__version__ = "2.0.0"
__author__ = "Intrastat Team"
__description__ = "Automatizované spracovanie faktúr pre Intrastat reporty"

# Hlavné komponenty
from .config import AppSettings
from .models.invoice_processor import InvoiceProcessor
from .data.csv_loader import DataManager
from .utils.logging_config import setup_logging, get_logger

__all__ = [
    "AppSettings",
    "InvoiceProcessor", 
    "DataManager",
    "setup_logging",
    "get_logger"
] 