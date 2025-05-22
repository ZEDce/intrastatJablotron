"""
AI Analyzer - špecializovaný modul pre analýzu faktúr pomocou Google Gemini.
"""
import os
import re
import json
import time
from typing import Dict, Any, Optional
from functools import wraps

import google.generativeai as genai

from ..config import AppSettings
from ..utils.exceptions import AIAnalysisError
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Rate limiting decorator
def rate_limit(calls_per_minute: int = 60):
    """Decorator pre rate limiting AI volání."""
    min_interval = 60.0 / calls_per_minute
    last_called = {}
    
    def decorator(func):
        func_name = func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            
            if func_name in last_called:
                time_since_last = current_time - last_called[func_name]
                if time_since_last < min_interval:
                    sleep_time = min_interval - time_since_last
                    logger.debug(f"Rate limiting: čakám {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            
            last_called[func_name] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Hardcoded customs code overrides
CUSTOMS_CODE_OVERRIDES = {
    "CZ-1263.1": "85311030",
    "JA-196J": "85311030",
    "JA-165A": "85311030",  # Sirény
    "JA-192Y": "85311030",  # GSM komunikátor
    "JA-194Y": "85311030"   # LTE komunikátor
}


class AIModelManager:
    """Manager pre AI modely s connection pooling."""
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def configure_api(cls, api_key: str) -> None:
        """Nakonfiguruje Google AI API."""
        genai.configure(api_key=api_key)
        logger.info("Google AI API bol nakonfigurovaný")
    
    @classmethod
    def get_model(cls, model_name: str) -> Any:
        """Vráti AI model s connection pooling."""
        if model_name not in cls._instances:
            try:
                cls._instances[model_name] = genai.GenerativeModel(model_name)
                logger.info(f"Vytváram nový AI model: {model_name}")
            except Exception as e:
                logger.error(f"Chyba pri vytváraní AI modelu {model_name}: {e}")
                raise AIAnalysisError(f"Nepodarilo sa vytvoriť AI model: {e}")
        
        return cls._instances[model_name]


class GeminiAnalyzer:
    """Analyzer pre faktúry pomocou Google Gemini."""
    
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.rate_limit_per_minute = 30
        
        # Inicializácia AI
        if not os.getenv("GOOGLE_API_KEY"):
            logger.warning("GOOGLE_API_KEY nie je nastavený")
        else:
            AIModelManager.configure_api(os.getenv("GOOGLE_API_KEY"))
            logger.info(f"GeminiAnalyzer inicializovaný s rate limitom {self.rate_limit_per_minute}/min")
    
    @rate_limit(calls_per_minute=30)  # Default, bude prepisaný
    def _make_ai_call(self, model_name: str, prompt: str, image_data: Optional[bytes] = None) -> str:
        """Spraví AI volanie s retry logikou."""
        try:
            model = AIModelManager.get_model(model_name)
            
            if image_data:
                # Image analysis
                image_part = {
                    "mime_type": "image/png",
                    "data": image_data
                }
                response = model.generate_content([image_part, prompt])
            else:
                # Text only
                response = model.generate_content(prompt)
            
            response.resolve()
            
            if response.candidates and response.candidates[0].content.parts:
                return response.text
            else:
                logger.warning("AI API nevrátilo žiadny obsah")
                if hasattr(response, 'prompt_feedback'):
                    logger.warning(f"Prompt feedback: {response.prompt_feedback}")
                raise AIAnalysisError("AI API nevrátilo žiadny obsah")
                
        except Exception as e:
            logger.error(f"Chyba pri AI volaní: {e}")
            raise AIAnalysisError(f"AI volanie zlyhalo: {e}")
    
    def analyze_invoice_image(self, image_path: str, page_number: int) -> Dict[str, Any]:
        """
        Analyzuje obrázok faktúry pomocí AI.
        
        Args:
            image_path: Cesta k obrázku
            page_number: Číslo strany
            
        Returns:
            Parsované dáta faktúry
        """
        logger.info(f"Analyzujem obrázok faktúry: {image_path}, strana {page_number}")
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            prompt = self._get_invoice_analysis_prompt()
            
            decorated_call = rate_limit(self.rate_limit_per_minute)(self._make_ai_call)
            raw_response = decorated_call(
                model_name=self.settings.main_model,
                prompt=prompt,
                image_data=image_data
            )
            
            parsed_data = self._parse_ai_response(raw_response)
            
            # Validácia a logging
            items_count = len(parsed_data.get("items", []))
            logger.info(f"Úspešne analyzovaná strana {page_number}, nájdené {items_count} položiek")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Chyba pri analýze obrázka {image_path}: {e}")
            raise AIAnalysisError(f"Analýza obrázka zlyhala: {e}")
    
    def assign_customs_code(self, item_details: Dict[str, Any], customs_codes_map: Dict[str, str]) -> tuple[str, str]:
        """
        Priradí colný kód k položke pomocí AI alebo hardcoded pravidiel.
        
        Args:
            item_details: Detaily položky
            customs_codes_map: Mapa colných kódov
            
        Returns:
            Tuple (colný_kód, dôvod_priradenia)
        """
        item_code = item_details.get("item_code", "")
        
        # Hardcoded overrides
        if item_code in CUSTOMS_CODE_OVERRIDES:
            assigned_code = CUSTOMS_CODE_OVERRIDES[item_code]
            description = customs_codes_map.get(assigned_code, "Popis nenájdený")
            logger.info(f"Použitý hardcoded override pre {item_code}: {assigned_code}")
            return assigned_code, f"Hardkódované pravidlo pre {item_code}"
        
        # AI analýza
        prompt = self._get_customs_code_prompt(item_details, customs_codes_map)
        
        try:
            decorated_call = rate_limit(self.rate_limit_per_minute)(self._make_ai_call)
            raw_response = decorated_call(
                model_name=self.settings.customs_model,
                prompt=prompt
            )
            
            # Extrahovanie kódu z odpovede
            assigned_code, reasoning = self._parse_customs_response(raw_response, customs_codes_map)
            logger.info(f"AI priradil kód {assigned_code} pre položku {item_code}")
            
            return assigned_code, reasoning
            
        except Exception as e:
            logger.error(f"Chyba pri AI priradení colného kódu pre {item_code}: {e}")
            return "NEURCENE", f"Chyba: {e}"
    
    def adjust_weights(self, items_data: list, target_net_kg: float, target_gross_kg: float, preliminary_net_kg: float) -> list:
        """
        Upravuje hmotnosti položiek pomocou AI na dosiahnutie cieľových súčtov.
        Používa AI pre distribúciu a programmatic correction pre presnosť.
        
        Args:
            items_data: Zoznam položiek s dátami
            target_net_kg: Cieľová čistá hmotnosť
            target_gross_kg: Cieľová hrubá hmotnosť
            preliminary_net_kg: Vypočítaná predbežná čistá hmotnosť
            
        Returns:
            Zoznam upravených položiek
        """
        logger.info(f"Upravujem hmotnosti pre {len(items_data)} položiek")
        logger.info(f"Ciele: čistá={target_net_kg}kg, hrubá={target_gross_kg}kg")
        
        prompt = self._get_weight_adjustment_prompt(items_data, target_net_kg, target_gross_kg, preliminary_net_kg)
        
        try:
            decorated_call = rate_limit(self.rate_limit_per_minute)(self._make_ai_call)
            raw_response = decorated_call(
                model_name=self.settings.main_model,
                prompt=prompt
            )
            
            ai_adjusted_data = self._parse_weight_response(raw_response)
            
            # PROGRAMMATIC CORRECTION pre presné dodržanie cieľov
            final_adjusted_data = self._apply_programmatic_correction(
                ai_adjusted_data, items_data, target_net_kg, target_gross_kg
            )
            
            logger.info("Úspešne upravené hmotnosti pomocou AI + programmatic correction")
            
            return final_adjusted_data
            
        except Exception as e:
            logger.error(f"Chyba pri AI úprave hmotností: {e}")
            return []
    
    def _apply_programmatic_correction(self, ai_data: list, original_items: list, target_net_kg: float, target_gross_kg: float) -> list:
        """
        Aplikuje programmatic correction pre presné dodržanie cieľových hmotností.
        
        Args:
            ai_data: AI výsledky
            original_items: Pôvodné položky
            target_net_kg: Cieľová čistá hmotnosť  
            target_gross_kg: Cieľová hrubá hmotnosť
            
        Returns:
            Finálne upravené položky
        """
        logger.debug("Aplikujem programmatic correction")
        
        # Vytvorenie mapy AI výsledkov
        ai_map = {item.get("item_code", ""): item for item in ai_data if isinstance(item, dict)}
        
        # Spracovanie všetkých položiek
        items_for_correction = []
        sum_ai_net = 0.0
        sum_ai_gross = 0.0
        
        for orig_item in original_items:
            item_code = orig_item.get("Item Name", "")
            ai_item = ai_map.get(item_code, {})
            
            # Konverzia AI hmotností na float
            try:
                ai_net_str = ai_item.get("Final Net Weight", "0")
                ai_gross_str = ai_item.get("Final Gross Weight", "0")
                
                ai_net = float(str(ai_net_str).replace(',', '.'))
                ai_gross = float(str(ai_gross_str).replace(',', '.'))
                
                if ai_gross < ai_net or ai_net < 0:
                    logger.warning(f"Neplatné AI hmotnosti pre {item_code}: net={ai_net}, gross={ai_gross}")
                    ai_net = max(0, ai_net)
                    ai_gross = max(ai_net, ai_gross)
                
                sum_ai_net += ai_net
                sum_ai_gross += ai_gross
                
                items_for_correction.append({
                    "item_code": item_code,
                    "ai_net": ai_net,
                    "ai_gross": ai_gross,
                    "is_valid": True
                })
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Nepodarilo sa konvertovať AI hmotnosti pre {item_code}: {e}")
                items_for_correction.append({
                    "item_code": item_code,
                    "ai_net": 0.0,
                    "ai_gross": 0.0,
                    "is_valid": False
                })
        
        # Korekcia čistých hmotností
        net_difference = target_net_kg - sum_ai_net
        if abs(net_difference) > 1e-6:
            logger.debug(f"Korekcia čistých hmotností: rozdiel {net_difference:.6f} kg")
            self._distribute_weight_difference(items_for_correction, net_difference, "net")
        
        # Prekalkulácia hrubých hmotností
        corrected_net_sum = sum(item["corrected_net"] for item in items_for_correction if item["is_valid"])
        total_packaging = target_gross_kg - corrected_net_sum
        
        # Korekcia hrubých hmotností
        current_packaging_sum = sum(item["ai_gross"] - item["ai_net"] for item in items_for_correction if item["is_valid"])
        packaging_difference = total_packaging - current_packaging_sum
        
        if abs(packaging_difference) > 1e-6:
            logger.debug(f"Korekcia obalových hmotností: rozdiel {packaging_difference:.6f} kg")
            self._distribute_packaging_difference(items_for_correction, packaging_difference)
        
        # Finálna validácia a formátovanie výstupu
        result = []
        final_net_sum = 0.0
        final_gross_sum = 0.0
        
        for item in items_for_correction:
            if item["is_valid"]:
                final_net = item["corrected_net"]
                final_gross = item["corrected_gross"]
                
                # Zabezpečenie že gross >= net
                if final_gross < final_net:
                    final_gross = final_net
                
                final_net_sum += final_net
                final_gross_sum += final_gross
                
                result.append({
                    "item_code": item["item_code"],
                    "Final Net Weight": f"{final_net:.3f}".replace('.', ','),
                    "Final Gross Weight": f"{final_gross:.3f}".replace('.', ',')
                })
            else:
                # Chybné položky
                result.append({
                    "item_code": item["item_code"],
                    "Final Net Weight": "CHYBA_AI",
                    "Final Gross Weight": "CHYBA_AI"
                })
        
        # Finálna kontrola presnosti
        net_error = abs(final_net_sum - target_net_kg)
        gross_error = abs(final_gross_sum - target_gross_kg)
        
        logger.info(f"Programmatic correction dokončená:")
        logger.info(f"  Čistá hmotnosť: {final_net_sum:.6f} kg (cieľ: {target_net_kg:.3f} kg, chyba: {net_error:.6f} kg)")
        logger.info(f"  Hrubá hmotnosť: {final_gross_sum:.6f} kg (cieľ: {target_gross_kg:.3f} kg, chyba: {gross_error:.6f} kg)")
        
        if net_error > 1e-3 or gross_error > 1e-3:
            logger.warning("Programmatic correction nebola úplne presná!")
        
        return result
    
    def _distribute_weight_difference(self, items: list, difference: float, weight_type: str) -> None:
        """Distribuuje rozdiel hmotnosti proporcionálne medzi položky."""
        valid_items = [item for item in items if item["is_valid"]]
        
        if not valid_items:
            return
        
        if weight_type == "net":
            total_base = sum(item["ai_net"] for item in valid_items)
            
            if total_base > 1e-9:
                for item in valid_items:
                    proportion = item["ai_net"] / total_base
                    adjustment = difference * proportion
                    item["corrected_net"] = max(0, item["ai_net"] + adjustment)
            else:
                # Rovnomerná distribúcia ak sú všetky hmotnosti 0
                equal_adjustment = difference / len(valid_items)
                for item in valid_items:
                    item["corrected_net"] = max(0, equal_adjustment)
        
        # Nastavenie corrected_net pre nevalidné položky
        for item in items:
            if not item["is_valid"]:
                item["corrected_net"] = 0.0
    
    def _distribute_packaging_difference(self, items: list, packaging_diff: float) -> None:
        """Distribuuje rozdiel obalových hmotností."""
        valid_items = [item for item in items if item["is_valid"]]
        
        if not valid_items:
            return
        
        # Báza pre distribúciu - existujúce obalové hmotnosti
        base_packaging = []
        for item in valid_items:
            current_packaging = max(1e-6, item["ai_gross"] - item["ai_net"])  # Min epsilon
            base_packaging.append(current_packaging)
        
        total_base_packaging = sum(base_packaging)
        
        if total_base_packaging > 1e-9:
            for i, item in enumerate(valid_items):
                proportion = base_packaging[i] / total_base_packaging
                packaging_adjustment = packaging_diff * proportion
                
                original_packaging = item["ai_gross"] - item["ai_net"]
                new_packaging = max(0, original_packaging + packaging_adjustment)
                
                item["corrected_gross"] = item["corrected_net"] + new_packaging
        else:
            # Rovnomerná distribúcia
            equal_packaging = packaging_diff / len(valid_items)
            for item in valid_items:
                item["corrected_gross"] = item["corrected_net"] + max(0, equal_packaging)
        
        # Nastavenie corrected_gross pre nevalidné položky
        for item in items:
            if not item["is_valid"]:
                item["corrected_gross"] = 0.0

    def _get_invoice_analysis_prompt(self) -> str:
        """Vráti prompt pre analýzu faktúry."""
        return """
Analyze the provided invoice image to extract structured data.
The invoice contains information about items, quantities, prices, and potentially an overall invoice number.
Please return the data in JSON format with the following structure:
{
  "invoice_number": "INV12345", // Extract if present, otherwise use "N/A"
  "items": [
    {
      "item_code": "CODE123", // Product code or registration number, if available
      "item_name": "Product Name Example", // Full name of the item
      "description": "Detailed description of the item",
      "quantity": 10, // Number of units. Must be a number.
      "unit_price": 25.99, // Price per unit. Must be a number.
      "total_price": 259.90, // Total price for the item
      "location": "COUNTRY CODE (e.g., CZ, GB, CN). Search for 2-letter ISO code or 'Made in [Country]'. If genuinely ABSENT, use 'NOT_ON_IMAGE'.",
      "currency": "EUR" // Currency code
    }
  ]
}

Instructions:
- Ensure all numeric fields are numbers, not strings. Use dot (.) as decimal separator.
- For "location": This field is ESSENTIAL. Find country of origin for EVERY item.
- Return ONLY the JSON structure. No other text.
"""
    
    def _get_customs_code_prompt(self, item_details: Dict[str, Any], customs_codes_map: Dict[str, str]) -> str:
        """Vráti prompt pre priradenie colného kódu."""
        customs_codes_text = "\\n".join([f"- Kód: {code}, Popis: {desc}" for code, desc in customs_codes_map.items()])
        
        return f"""
Si expert na colnú klasifikáciu tovaru pre spoločnosť zaoberajúcu sa bezpečnostnými systémami.
Na základe nasledujúcich detailov položky:
- Kód položky: {item_details.get('item_code', 'N/A')}
- Popis položky: {item_details.get('description', 'Žiadny popis')}
- Krajina pôvodu: {item_details.get('location', 'N/A')}

A zoznamu dostupných colných kódov:
{customs_codes_text}

Vyber JEDEN najvhodnejší 8-miestny colný kód. Mnohé produkty patria pod '85311030' (Poplachové systémy).

Vysvetli svoje rozhodnutie a na konci uveď:
VYSLEDNY_KOD: XXXXXXXX

Ak nie je možné určiť, uveď:
VYSLEDNY_KOD: NEURCENE
"""
    
    def _get_weight_adjustment_prompt(self, items_data: list, target_net_kg: float, target_gross_kg: float, preliminary_net_kg: float) -> str:
        """Vráti prompt pre úpravu hmotností."""
        items_json = json.dumps([{
            "item_code": item.get("Item Name", ""),
            "description": item.get("description", ""),
            "quantity": item.get("Quantity", ""),
            "preliminary_net_weight_kg_str": item.get("Preliminary Net Weight", "")
        } for item in items_data], ensure_ascii=False, indent=2)
        
        return f"""
Si expert na logistiku. Upravuj hmotnosti položiek tak, aby súčty zodpovedali cieľom.

Cieľová ČISTÁ hmotnosť: {target_net_kg:.3f} kg
Cieľová HRUBÁ hmotnosť: {target_gross_kg:.3f} kg
Predbežná čistá hmotnosť: {preliminary_net_kg:.3f} kg

Položky faktúry:
{items_json}

Pravidlá:
1. Súčet Final Net Weight MUSÍ = {target_net_kg:.3f} kg
2. Súčet Final Gross Weight MUSÍ = {target_gross_kg:.3f} kg
3. Pre každú položku: Final Gross Weight >= Final Net Weight
4. Hmotnosti nesmú byť záporné
5. Rozdeľuj proporcionálne podľa predbežných hmotností

Výstup MUSÍ byť validný JSON zoznam:
[
  {{"item_code": "KOD", "Final Net Weight": "10.500", "Final Gross Weight": "11.200"}},
  ...
]

DÔLEŽITÉ: Skontroluj súčty pred odoslaním! Poskytni IBA JSON bez iného textu.
"""
    
    def _parse_ai_response(self, raw_response: str) -> Dict[str, Any]:
        """Parsuje AI odpoveď pre analýzu faktúry."""
        cleaned_response = self._clean_json_response(raw_response)
        
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Chyba pri parsovaní JSON: {e}, odpoveď: {cleaned_response[:200]}...")
            raise AIAnalysisError(f"Nepodarilo sa parsovať AI odpoveď: {e}")
    
    def _parse_customs_response(self, raw_response: str, customs_codes_map: Dict[str, str]) -> tuple[str, str]:
        """Parsuje AI odpoveď pre colný kód."""
        code_match = re.search(r"VYSLEDNY_KOD:\s*([0-9]{8}|NEURCENE)", raw_response, re.IGNORECASE)
        
        if code_match:
            extracted_code = code_match.group(1).strip()
            
            if re.fullmatch(r"[0-9]{8}", extracted_code):
                if extracted_code in customs_codes_map:
                    return extracted_code, raw_response
                else:
                    logger.warning(f"AI vrátil neznámy kód: {extracted_code}")
                    return "NEURCENE", f"Neznámy kód: {extracted_code}"
            elif extracted_code.upper() == "NEURCENE":
                return "NEURCENE", raw_response
        
        logger.warning("AI nevrátil validný formát odpovede")
        return "NEURCENE", "Nevalidný formát odpovede"
    
    def _parse_weight_response(self, raw_response: str) -> list:
        """Parsuje AI odpoveď pre úpravu hmotností."""
        cleaned_response = self._clean_json_response(raw_response)
        
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Chyba pri parsovaní hmotností JSON: {e}")
            raise AIAnalysisError(f"Nepodarilo sa parsovať hmotnosti: {e}")
    
    def _clean_json_response(self, response: str) -> str:
        """Vyčistí AI odpoveď od markdown formátovania."""
        cleaned = response.strip()
        
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        
        return cleaned 