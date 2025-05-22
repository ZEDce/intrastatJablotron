"""
Centralizované nastavenia pre Intrastat aplikáciu.
"""
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class AppSettings:
    """Hlavné nastavenia aplikácie."""
    
    # API konfigurácia
    google_api_key: str = ""
    
    # AI modely
    main_model: str = "gemini-2.0-flash-lite"
    customs_model: str = "gemini-2.0-flash-lite"
    
    # Adresáre
    input_pdf_dir: str = "faktury_na_spracovanie/"
    output_csv_dir: str = "data_output/"
    pdf_image_dir: str = "pdf_images/"
    processed_pdf_dir: str = "spracovane_faktury/"
    data_dir: str = "data/"
    reports_dir: str = "dovozy/"
    logs_dir: str = "logs/"
    archive_dir: str = "data_output_archiv/"
    
    # Spracovanie
    pdf_dpi: int = 200
    max_retries: int = 3
    batch_size: int = 5
    ai_rate_limit_per_minute: int = 30
    
    # Validácia
    weight_tolerance_multiplier: float = 0.001
    max_pdf_size_mb: int = 50
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_env(cls) -> 'AppSettings':
        """Vytvorí nastavenia z environment variables."""
        instance = cls()
        instance.google_api_key = os.getenv("GOOGLE_API_KEY", "")
        
        # Voliteľné environment variables
        instance.pdf_dpi = int(os.getenv("PDF_DPI", str(instance.pdf_dpi)))
        instance.max_retries = int(os.getenv("MAX_RETRIES", str(instance.max_retries)))
        instance.batch_size = int(os.getenv("BATCH_SIZE", str(instance.batch_size)))
        instance.log_level = os.getenv("LOG_LEVEL", instance.log_level)
        
        return instance
    
    def validate(self) -> None:
        """Validuje nastavenia."""
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY musí byť nastavený")
        
        # Validácia adresárov
        for dir_attr in ['input_pdf_dir', 'output_csv_dir', 'data_dir']:
            dir_path = getattr(self, dir_attr)
            if not os.path.exists(dir_path):
                raise ValueError(f"Adresár {dir_path} neexistuje")
        
        # Validácia číselných hodnôt
        if self.pdf_dpi <= 0:
            raise ValueError("PDF DPI musí byť kladné číslo")
        
        if self.max_retries < 0:
            raise ValueError("Max retries nemôže byť záporné")
    
    def ensure_directories(self) -> None:
        """Vytvorí potrebné adresáre ak neexistujú."""
        directories = [
            self.output_csv_dir,
            self.pdf_image_dir,
            self.processed_pdf_dir,
            self.reports_dir,
            self.logs_dir,
            self.archive_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# Konstanty pre colné kódy
CUSTOMS_CODE_OVERRIDES = {
    "CZ-1263.1": "85311030",
    "JA-196J": "85311030"
}

# Kľúčové slová pre neproduktové položky
NON_PRODUCT_KEYWORDS = [
    "sleva", "zľava", "doprava", "preprava", "poplatek", 
    "manipulační", "discount", "shipping", "fee", "handling"
]

# Očakávané placeholder hodnoty pre hmotnosti
EXPECTED_WEIGHT_PLACEHOLDERS = [
    "NENÁJDENÉ", "CHYBA_QTY", "CHÝBAJÚ_DÁTA_HMOTNOSTI", 
    "CHÝBA_KÓD_PRE_HMOTNOSŤ", "NOT_IN_AI_RESP", "AI_JSON_DECODE_ERR",
    "AI_BAD_FORMAT_NON_LIST", "AI_EXCEPTION", "ERROR", "AI_SKIP_NO_VALID_ITEMS",
    "ERR_GROSS_LT_NET", "ERR_NEGATIVE", "ERR_CONVERT", "ERR_AI_KEY_MISSING", "N/A"
]

# Default nastavenia pre rôzne komponenty
DEFAULT_CSV_HEADERS = [
    "Page Number", "Invoice Number", "Item Name", "description", "Location", 
    "Quantity", "Unit Price", "Total Price", 
    "Preliminary Net Weight", "Total Net Weight", "Total Gross Weight",
    "Colný kód", "Popis colného kódu"
] 