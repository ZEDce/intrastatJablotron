"""
CSV Data Loader pre načítanie produktových hmotností a colných kódov.
"""
import csv
import os
from typing import Dict, Optional
import re

from ..config import AppSettings
from ..utils.exceptions import CSVProcessingError, DataValidationError
from ..utils.logging_config import get_logger


logger = get_logger(__name__)


class ProductWeightLoader:
    """Loader pre produktové hmotnosti z CSV súboru."""
    
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.weights_file = os.path.join(settings.data_dir, "product_weight.csv")
    
    def load_weights(self) -> Dict[str, float]:
        """
        Načíta produktové hmotnosti z CSV súboru.
        
        Returns:
            Slovník mapujúci kódy produktov na hmotnosti
            
        Raises:
            CSVProcessingError: Pri chybe načítania
        """
        if not os.path.exists(self.weights_file):
            logger.error(f"Súbor s hmotnosťami neexistuje: {self.weights_file}")
            return {}
        
        logger.info(f"Načítavam produktové hmotnosti z: {self.weights_file}")
        
        weights = {}
        errors = []
        
        try:
            with open(self.weights_file, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                
                # Kontrola hlavičky
                try:
                    header = next(reader)
                    expected_header = ["Registrační číslo", "JV Váha komplet SK"]
                    
                    if header != expected_header:
                        logger.warning(
                            f"Neočakávaná hlavička v {self.weights_file}: {header}. "
                            f"Očakávaná: {expected_header}"
                        )
                except StopIteration:
                    raise CSVProcessingError(f"Prázdny súbor: {self.weights_file}")
                
                # Spracovanie riadkov
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if len(row) != 2:
                            errors.append(f"Riadok {row_num}: Nesprávny počet stĺpcov ({len(row)})")
                            continue
                        
                        item_code = row[0].strip()
                        weight_str = row[1].strip()
                        
                        if not item_code:
                            errors.append(f"Riadok {row_num}: Chýba kód položky")
                            continue
                        
                        if not weight_str:
                            errors.append(f"Riadok {row_num}: Chýba hmotnosť pre '{item_code}'")
                            continue
                        
                        # Konverzia hmotnosti (čiarka -> bodka)
                        weight_normalized = weight_str.replace(',', '.')
                        
                        try:
                            weight = float(weight_normalized)
                            if weight < 0:
                                errors.append(f"Riadok {row_num}: Záporná hmotnosť pre '{item_code}': {weight}")
                                continue
                            
                            weights[item_code] = weight
                            logger.debug(f"Načítaná hmotnosť: {item_code} = {weight} kg")
                            
                        except ValueError:
                            errors.append(f"Riadok {row_num}: Neplatná hmotnosť pre '{item_code}': '{weight_str}'")
                    
                    except Exception as e:
                        errors.append(f"Riadok {row_num}: Neočakávaná chyba: {e}")
            
            # Reportovanie chýb
            if errors:
                for error in errors[:10]:  # Prvých 10 chýb
                    logger.warning(f"WEIGHTS CSV: {error}")
                
                if len(errors) > 10:
                    logger.warning(f"WEIGHTS CSV: ... a ďalších {len(errors) - 10} chýb")
            
            logger.info(f"Načítaných {len(weights)} produktových hmotností ({len(errors)} chýb)")
            return weights
        
        except Exception as e:
            logger.error(f"Chyba pri načítaní {self.weights_file}: {e}")
            raise CSVProcessingError(f"Chyba pri načítaní produktových hmotností: {e}")


class CustomsCodeLoader:
    """Loader pre colné kódy z CSV súboru."""
    
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.codes_file = os.path.join(settings.data_dir, "col_sadz.csv")
    
    def load_codes(self) -> Dict[str, str]:
        """
        Načíta colné kódy z CSV súboru.
        
        Returns:
            Slovník mapujúci colné kódy na ich popisy
            
        Raises:
            CSVProcessingError: Pri chybe načítania
        """
        if not os.path.exists(self.codes_file):
            logger.error(f"Súbor s colnými kódmi neexistuje: {self.codes_file}")
            return {}
        
        logger.info(f"Načítavam colné kódy z: {self.codes_file}")
        
        codes = {}
        errors = []
        
        try:
            with open(self.codes_file, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                
                # Kontrola hlavičky
                try:
                    header = next(reader)
                    # Normalizácia hlavičky (odstránenie BOM)
                    normalized_header = [h.lstrip('\ufeff') for h in header]
                    expected_header = ["col_sadz", "Popis"]
                    
                    if normalized_header != expected_header:
                        logger.warning(
                            f"Neočakávaná hlavička v {self.codes_file}: {header} "
                            f"(normalizovaná: {normalized_header}). Očakávaná: {expected_header}"
                        )
                except StopIteration:
                    raise CSVProcessingError(f"Prázdny súbor: {self.codes_file}")
                
                # Spracovanie riadkov
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if len(row) != 2:
                            errors.append(f"Riadok {row_num}: Nesprávny počet stĺpcov ({len(row)})")
                            continue
                        
                        code_raw = row[0].strip()
                        description = row[1].strip()
                        
                        if not code_raw:
                            errors.append(f"Riadok {row_num}: Chýba colný kód")
                            continue
                        
                        if not description:
                            errors.append(f"Riadok {row_num}: Chýba popis pre kód '{code_raw}'")
                            continue
                        
                        # Normalizácia kódu (odstránenie medzier)
                        code = code_raw.replace(" ", "")
                        
                        # Validácia formátu kódu
                        if not re.fullmatch(r"[0-9]+", code):
                            errors.append(f"Riadok {row_num}: Neplatný formát kódu '{code_raw}' (normalizovaný: '{code}')")
                            continue
                        
                        codes[code] = description
                        logger.debug(f"Načítaný colný kód: {code} = {description}")
                    
                    except Exception as e:
                        errors.append(f"Riadok {row_num}: Neočakávaná chyba: {e}")
            
            # Reportovanie chýb
            if errors:
                for error in errors[:10]:  # Prvých 10 chýb
                    logger.warning(f"CUSTOMS CSV: {error}")
                
                if len(errors) > 10:
                    logger.warning(f"CUSTOMS CSV: ... a ďalších {len(errors) - 10} chýb")
            
            logger.info(f"Načítaných {len(codes)} colných kódov ({len(errors)} chýb)")
            return codes
        
        except Exception as e:
            logger.error(f"Chyba pri načítaní {self.codes_file}: {e}")
            raise CSVProcessingError(f"Chyba pri načítaní colných kódov: {e}")


class DataManager:
    """Centrálny manager pre načítanie všetkých dát."""
    
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.weight_loader = ProductWeightLoader(settings)
        self.customs_loader = CustomsCodeLoader(settings)
        
        # Cache pre načítané dáta
        self._weights_cache: Optional[Dict[str, float]] = None
        self._customs_cache: Optional[Dict[str, str]] = None
    
    def get_product_weights(self, force_reload: bool = False) -> Dict[str, float]:
        """
        Vráti produktové hmotnosti s caching.
        
        Args:
            force_reload: Či vynútiť znovunačítanie
            
        Returns:
            Slovník hmotností
        """
        if self._weights_cache is None or force_reload:
            self._weights_cache = self.weight_loader.load_weights()
        
        return self._weights_cache
    
    def get_customs_codes(self, force_reload: bool = False) -> Dict[str, str]:
        """
        Vráti colné kódy s caching.
        
        Args:
            force_reload: Či vynútiť znovunačítanie
            
        Returns:
            Slovník colných kódov
        """
        if self._customs_cache is None or force_reload:
            self._customs_cache = self.customs_loader.load_codes()
        
        return self._customs_cache
    
    def get_product_weight(self, product_code: str) -> Optional[float]:
        """
        Vráti hmotnosť konkrétneho produktu.
        
        Args:
            product_code: Kód produktu
            
        Returns:
            Hmotnosť produktu alebo None
        """
        weights = self.get_product_weights()
        return weights.get(product_code)
    
    def get_customs_code_description(self, customs_code: str) -> Optional[str]:
        """
        Vráti popis colného kódu.
        
        Args:
            customs_code: Colný kód
            
        Returns:
            Popis kódu alebo None
        """
        codes = self.get_customs_codes()
        return codes.get(customs_code)
    
    def validate_data_files(self) -> Dict[str, bool]:
        """
        Validuje existenciu a formát dátových súborov.
        
        Returns:
            Slovník s výsledkami validácie
        """
        results = {}
        
        # Kontrola súboru hmotností
        try:
            weights = self.get_product_weights()
            results["product_weights"] = len(weights) > 0
            logger.info(f"Validácia hmotností: {len(weights)} položiek")
        except Exception as e:
            results["product_weights"] = False
            logger.error(f"Validácia hmotností zlyhala: {e}")
        
        # Kontrola súboru colných kódov
        try:
            codes = self.get_customs_codes()
            results["customs_codes"] = len(codes) > 0
            logger.info(f"Validácia colných kódov: {len(codes)} položiek")
        except Exception as e:
            results["customs_codes"] = False
            logger.error(f"Validácia colných kódov zlyhala: {e}")
        
        return results 