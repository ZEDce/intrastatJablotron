"""
Validátory pre vstupné dáta v Intrastat aplikácii.
"""
import re
from pathlib import Path
from typing import Union

from .exceptions import DataValidationError, PDFProcessingError


def validate_pdf_file(file_path: Union[str, Path], max_size_mb: int = 50) -> bool:
    """
    Validuje PDF súbor.
    
    Args:
        file_path: Cesta k PDF súboru
        max_size_mb: Maximálna veľkosť súboru v MB
        
    Returns:
        True ak je súbor validný
        
    Raises:
        PDFProcessingError: Ak súbor nie je validný
    """
    path = Path(file_path)
    
    if not path.exists():
        raise PDFProcessingError(f"PDF súbor neexistuje: {file_path}")
    
    if not path.is_file():
        raise PDFProcessingError(f"Cesta nie je súbor: {file_path}")
    
    if not path.suffix.lower() == '.pdf':
        raise PDFProcessingError(f"Súbor nie je PDF: {file_path}")
    
    # Kontrola veľkosti súboru
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise PDFProcessingError(
            f"PDF súbor je príliš veľký: {file_size_mb:.1f}MB > {max_size_mb}MB"
        )
    
    return True


def validate_country_code(code: str) -> bool:
    """
    Validuje 2-písmenový kód krajiny podľa ISO 3166-1 alpha-2.
    
    Args:
        code: Kód krajiny na validáciu
        
    Returns:
        True ak je kód validný
        
    Raises:
        DataValidationError: Ak kód nie je validný
    """
    if not isinstance(code, str):
        raise DataValidationError(f"Kód krajiny musí byť string, dostal: {type(code)}")
    
    code = code.strip().upper()
    
    if not re.match(r'^[A-Z]{2}$', code):
        raise DataValidationError(
            f"Kód krajiny musí byť 2-písmenový kód (A-Z), dostal: '{code}'"
        )
    
    return True


def validate_customs_code(code: str) -> bool:
    """
    Validuje colný kód.
    
    Args:
        code: Colný kód na validáciu
        
    Returns:
        True ak je kód validný
        
    Raises:
        DataValidationError: Ak kód nie je validný
    """
    if not isinstance(code, str):
        raise DataValidationError(f"Colný kód musí byť string, dostal: {type(code)}")
    
    code = code.strip()
    
    # Povolené sú číselné kódy alebo špeciálne hodnoty
    special_codes = ["NEURCENE", "NEPRIRADENÉ", "Zľava", "Poplatok"]
    
    if code in special_codes:
        return True
    
    if not re.match(r'^\d{8}$', code):
        raise DataValidationError(
            f"Colný kód musí byť 8-ciferný alebo špeciálna hodnota, dostal: '{code}'"
        )
    
    return True


def validate_weight(weight: Union[str, int, float], allow_zero: bool = True) -> float:
    """
    Validuje a konvertuje hmotnosť.
    
    Args:
        weight: Hmotnosť na validáciu
        allow_zero: Či je povolená nulová hmotnosť
        
    Returns:
        Validovaná hmotnosť ako float
        
    Raises:
        DataValidationError: Ak hmotnosť nie je validná
    """
    if isinstance(weight, str):
        # Spracovanie string formátu s čiarkou ako desatinným oddeľovačom
        weight = weight.strip().replace(',', '.')
        
        try:
            weight = float(weight)
        except ValueError:
            raise DataValidationError(f"Hmotnosť nie je platné číslo: '{weight}'")
    
    elif not isinstance(weight, (int, float)):
        raise DataValidationError(f"Hmotnosť musí byť číslo, dostal: {type(weight)}")
    
    if weight < 0:
        raise DataValidationError(f"Hmotnosť nemôže byť záporná: {weight}")
    
    if not allow_zero and weight == 0:
        raise DataValidationError("Hmotnosť nemôže byť nula")
    
    return float(weight)


def validate_quantity(quantity: Union[str, int, float]) -> float:
    """
    Validuje a konvertuje množstvo.
    
    Args:
        quantity: Množstvo na validáciu
        
    Returns:
        Validované množstvo ako float
        
    Raises:
        DataValidationError: Ak množstvo nie je validné
    """
    if isinstance(quantity, str):
        quantity = quantity.strip().replace(',', '.')
        
        try:
            quantity = float(quantity)
        except ValueError:
            raise DataValidationError(f"Množstvo nie je platné číslo: '{quantity}'")
    
    elif not isinstance(quantity, (int, float)):
        raise DataValidationError(f"Množstvo musí byť číslo, dostal: {type(quantity)}")
    
    if quantity < 0:
        raise DataValidationError(f"Množstvo nemôže byť záporné: {quantity}")
    
    return float(quantity)


def validate_price(price: Union[str, int, float]) -> float:
    """
    Validuje a konvertuje cenu.
    
    Args:
        price: Cena na validáciu
        
    Returns:
        Validovaná cena ako float
        
    Raises:
        DataValidationError: Ak cena nie je validná
    """
    if isinstance(price, str):
        price = price.strip().replace(',', '.')
        
        try:
            price = float(price)
        except ValueError:
            raise DataValidationError(f"Cena nie je platné číslo: '{price}'")
    
    elif not isinstance(price, (int, float)):
        raise DataValidationError(f"Cena musí byť číslo, dostal: {type(price)}")
    
    # Cena môže byť záporná (zľavy)
    return float(price)


def validate_invoice_number(invoice_number: str) -> str:
    """
    Validuje číslo faktúry.
    
    Args:
        invoice_number: Číslo faktúry na validáciu
        
    Returns:
        Validované číslo faktúry
        
    Raises:
        DataValidationError: Ak číslo faktúry nie je validné
    """
    if not isinstance(invoice_number, str):
        raise DataValidationError(
            f"Číslo faktúry musí byť string, dostal: {type(invoice_number)}"
        )
    
    invoice_number = invoice_number.strip()
    
    if not invoice_number:
        raise DataValidationError("Číslo faktúry nemôže byť prázdne")
    
    # Základná validácia - číslo faktúry môže obsahovať písmená, číslice a spojovníky
    if not re.match(r'^[A-Za-z0-9\-_/\s]+$', invoice_number):
        raise DataValidationError(
            f"Číslo faktúry obsahuje nepovolené znaky: '{invoice_number}'"
        )
    
    return invoice_number 