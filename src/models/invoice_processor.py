"""
Hlavný procesor faktúr - orchestruje celý workflow spracovania.
"""
import os
import re
import shutil
import csv
from typing import Dict, List, Any, Optional
from tqdm import tqdm

from ..config import AppSettings, DEFAULT_CSV_HEADERS, NON_PRODUCT_KEYWORDS
from ..data.csv_loader import DataManager
from ..models.pdf_processor import PDFProcessor
from ..models.ai_analyzer import GeminiAnalyzer, COUNTRY_ORIGIN_OVERRIDES
from ..utils.exceptions import IntrastatError, PDFProcessingError, AIAnalysisError
from ..utils.validators import validate_country_code, validate_weight, validate_quantity
from ..utils.logging_config import get_logger, ProcessingMetrics


logger = get_logger(__name__)


class InvoiceProcessor:
    """Hlavný procesor pre spracovanie PDF faktúr."""
    
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.data_manager = DataManager(settings)
        self.pdf_processor = PDFProcessor(settings)
        self.ai_analyzer = GeminiAnalyzer(settings)
        self.metrics = ProcessingMetrics()
        
        # Zabezpečenie existencie adresárov
        settings.ensure_directories()
        
        logger.info("InvoiceProcessor inicializovaný")
    
    def process_all_pdfs(self) -> Dict[str, Any]:
        """
        Spracuje všetky PDF súbory v input adresári.
        
        Returns:
            Slovník s výsledkami spracovania
        """
        logger.info("Začínam spracovanie všetkých PDF súborov")
        self.metrics.start_processing()
        
        # Načítanie dát
        try:
            product_weights = self.data_manager.get_product_weights()
            customs_codes = self.data_manager.get_customs_codes()
            logger.info(f"Načítané dáta: {len(product_weights)} hmotností, {len(customs_codes)} colných kódov")
        except Exception as e:
            logger.error(f"Chyba pri načítaní dát: {e}")
            return {"error": f"Chyba pri načítaní dát: {e}"}
        
        # Získanie zoznamu PDF súborov
        pdf_files = self.pdf_processor.get_available_pdfs()
        
        if not pdf_files:
            logger.warning("Neboli nájdené žiadne PDF súbory na spracovanie")
            return {"warning": "Žiadne PDF súbory na spracovanie"}
        
        results = {
            "total_files": len(pdf_files),
            "processed": [],
            "failed": [],
            "summary": {}
        }
        
        # Spracovanie súborov s progress barom
        with tqdm(total=len(pdf_files), desc="Spracovávam PDF", unit="súbor") as pbar:
            for pdf_file in pdf_files:
                pbar.set_description(f"Spracovávam: {pdf_file}")
                
                try:
                    result = self.process_single_pdf(pdf_file, product_weights, customs_codes)
                    results["processed"].append({
                        "file": pdf_file,
                        "result": result
                    })
                    self.metrics.pdf_processed_successfully(pdf_file)
                    
                except Exception as e:
                    logger.error(f"Chyba pri spracovaní {pdf_file}: {e}")
                    results["failed"].append({
                        "file": pdf_file,
                        "error": str(e)
                    })
                    self.metrics.pdf_failed(pdf_file, str(e))
                
                finally:
                    pbar.update(1)
        
        # Finalizácia metrík
        self.metrics.finish_processing()
        results["summary"] = self.metrics.get_summary()
        
        logger.info(f"Spracovanie dokončené: {len(results['processed'])} úspešných, {len(results['failed'])} neúspešných")
        return results
    
    def process_single_pdf(self, pdf_file: str, product_weights: Dict[str, float], customs_codes: Dict[str, str]) -> Dict[str, Any]:
        """
        Spracuje jeden PDF súbor.
        
        Args:
            pdf_file: Názov PDF súboru
            product_weights: Mapa produktových hmotností
            customs_codes: Mapa colných kódov
            
        Returns:
            Slovník s výsledkami spracovania
        """
        pdf_path = os.path.join(self.settings.input_pdf_dir, pdf_file)
        logger.info(f"Spracovávam PDF: {pdf_path}")
        
        all_items = []
        invoice_number = os.path.splitext(pdf_file)[0]  # Default fallback
        
        try:
            # Konverzia PDF na obrázky
            image_paths = self.pdf_processor.pdf_to_images(pdf_path)
            logger.info(f"PDF konvertovaný na {len(image_paths)} obrázkov")
            
            # Analýza každej strany
            for page_num, image_path in enumerate(image_paths, 1):
                try:
                    logger.debug(f"Analyzujem stranu {page_num}")
                    
                    # AI analýza obrázka
                    analysis_result = self.ai_analyzer.analyze_invoice_image(image_path, page_num)
                    self.metrics.ai_call_made(self.settings.main_model, "image_analysis")
                    
                    if "error" not in analysis_result:
                        # Aktualizácia čísla faktúry
                        page_invoice_number = analysis_result.get("invoice_number")
                        if page_invoice_number and page_invoice_number != "N/A":
                            invoice_number = page_invoice_number
                        
                        # Spracovanie položiek strany
                        page_items = self._process_page_items(analysis_result, page_num, product_weights, invoice_number)
                        all_items.extend(page_items)
                        
                        logger.info(f"Strana {page_num}: nájdených {len(page_items)} položiek")
                    else:
                        # Chyba pri analýze strany
                        error_item = self._create_error_item(page_num, invoice_number, analysis_result["error"])
                        all_items.append(error_item)
                        logger.warning(f"Chyba pri analýze strany {page_num}: {analysis_result['error']}")
                
                except Exception as e:
                    logger.error(f"Chyba pri spracovaní strany {page_num}: {e}")
                    error_item = self._create_error_item(page_num, invoice_number, str(e))
                    all_items.append(error_item)
            
            # Čistenie obrázkov
            self.pdf_processor.cleanup_images(image_paths)
            
            if not all_items:
                raise IntrastatError(f"Neboli extrahované žiadne položky z PDF {pdf_file}")
            
            # Priradenie colných kódov
            self._assign_customs_codes(all_items, customs_codes)
            
            # Úprava hmotností
            target_weights = self._get_target_weights_from_user(invoice_number)
            if target_weights:
                self._adjust_weights_with_ai(all_items, target_weights)
            
            # Zápis do CSV
            csv_path = self._write_to_csv(all_items, invoice_number)
            
            # Vytvorenie meta súboru
            self._create_meta_file(csv_path, pdf_file)
            
            # Presun spracovaného PDF
            self._move_processed_pdf(pdf_file)
            
            return {
                "invoice_number": invoice_number,
                "items_count": len(all_items),
                "csv_path": csv_path,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Kritická chyba pri spracovaní {pdf_file}: {e}")
            raise IntrastatError(f"Chyba pri spracovaní PDF {pdf_file}: {e}")
    
    def _process_page_items(self, analysis_result: Dict[str, Any], page_number: int, 
                           product_weights: Dict[str, float], invoice_number: str) -> List[Dict[str, Any]]:
        """Spracuje položky z jednej strany."""
        items = analysis_result.get("items", [])
        
        if not items:
            logger.warning(f"Strana {page_number}: žiadne položky nenájdené")
            return []
        
        processed_items = []
        for item in items:
            processed_item = self._process_single_item(item, page_number, product_weights, invoice_number)
            processed_items.append(processed_item)
        
        return processed_items
    
    def _process_single_item(self, item: Dict[str, Any], page_number: int, 
                            product_weights: Dict[str, float], invoice_number: str) -> Dict[str, Any]:
        """Spracuje jednu položku faktúry."""
        # Základné informácie o položke
        raw_item_code = item.get("item_code")
        item_name = item.get("item_name", "N/A")
        description = item.get("description", "")
        
        # Určenie identifikátora položky
        if raw_item_code and str(raw_item_code).lower() not in ["null", "n/a", ""]:
            item_identifier = str(raw_item_code)
        else:
            item_identifier = item_name
        
        # Kombinovaný popis
        if item_name and description:
            final_description = f"{item_name} - {description}"
        elif description:
            final_description = description
        else:
            final_description = item_name
        
        # Určenie či je to produkt
        is_product = self._is_product_item(item_identifier, final_description)
        
        # Spracovanie lokácie
        ai_location = item.get("location")
        processed_location = self._process_location(ai_location, item_identifier, is_product, page_number)
        
        # Validácia a konverzia číselných hodnôt
        try:
            quantity = validate_quantity(item.get("quantity", 0))
            unit_price = float(item.get("unit_price", 0))
            total_price = float(item.get("total_price", 0))
        except Exception as e:
            logger.warning(f"Chyba pri validácii číselných hodnôt pre {item_identifier}: {e}")
            quantity = 0
            unit_price = 0
            total_price = 0
        
        # Výpočet predbežnej hmotnosti
        preliminary_weight = self._calculate_preliminary_weight(
            raw_item_code if raw_item_code else None,
            quantity,
            product_weights,
            item_identifier,
            is_product
        )
        
        return {
            "Page Number": page_number,
            "Invoice Number": invoice_number,
            "Item Name": item_identifier,
            "description": final_description,
            "Location": processed_location,
            "Quantity": quantity,
            "Unit Price": unit_price,
            "Total Price": total_price,
            "Preliminary Net Weight": preliminary_weight,
            "Total Net Weight": "",
            "Total Gross Weight": "",
            "Colný kód": "",
            "Popis colného kódu": ""
        }
    
    def _is_product_item(self, item_identifier: str, description: str) -> bool:
        """Určí či položka je produkt alebo nie (zľava, doprava, atď.)."""
        item_lower = item_identifier.lower()
        desc_lower = description.lower()
        
        # Kontrola non-product keywords
        for keyword in NON_PRODUCT_KEYWORDS:
            if keyword in item_lower or keyword in desc_lower:
                return False
        
        # Ak má špecifický kód, pravdepodobne je to produkt
        if re.match(r'^[A-Z]{2}-\d+', item_identifier):
            return True
        
        return True  # Default assumption
    
    def _process_location(self, ai_location: Any, item_identifier: str, is_product: bool, page_number: int) -> str:
        """Spracuje lokáciu (krajinu pôvodu) položky."""
        if not is_product:
            # Pre non-produkty sa nepýtame na lokáciu
            if ai_location and isinstance(ai_location, str):
                ai_loc_str = ai_location.strip().upper()
                if re.fullmatch(r"[A-Z]{2}", ai_loc_str):
                    return ai_loc_str
            return ""
        
        # Najprv skontroluj hardcoded overrides pre krajiny
        if item_identifier in COUNTRY_ORIGIN_OVERRIDES:
            override_country = COUNTRY_ORIGIN_OVERRIDES[item_identifier]
            logger.info(f"Použitý hardcoded override pre krajinu {item_identifier}: {override_country}")
            return override_country
        
        # Pre produkty - kontrola AI location
        if ai_location:
            ai_loc_str = str(ai_location).strip().upper()
            if re.fullmatch(r"[A-Z]{2}", ai_loc_str):
                return ai_loc_str
        
        # Ak AI neposkytla validný kód, spýtaj sa používateľa
        return self._ask_user_for_location(ai_location, item_identifier, page_number)
    
    def _ask_user_for_location(self, ai_location: Any, item_identifier: str, page_number: int) -> str:
        """Spýta sa používateľa na krajinu pôvodu."""
        # Určenie dôvodu prečo sa pýtame
        if ai_location is None:
            reason = "nebola automaticky extrahovaná"
        elif str(ai_location).strip() == "":
            reason = "bola AI vrátená ako prázdna"
        elif str(ai_location).strip().upper() == "N/A":
            reason = "bola AI označená ako 'N/A'"
        elif str(ai_location).strip().upper() == "NOT_ON_IMAGE":
            reason = "bola AI označená ako 'NOT_ON_IMAGE'"
        else:
            reason = f"bola AI vrátená v neplatnom formáte: '{ai_location}'"
        
        print(f"VAROVANIE: Krajina pôvodu pre produkt '{item_identifier}' (strana {page_number}) {reason}.")
        print(f"           (Tip: Ak je krajina uvedená na inej strane PDF alebo ju viete, zadajte ju teraz.)")
        
        user_input = input(f"  Zadajte 2-písmenový kód krajiny (napr. CN, SK), alebo stlačte Enter: ").strip()
        
        if user_input:
            try:
                validate_country_code(user_input)
                return user_input.upper()
            except Exception:
                print(f"  POZOR: Zadaný kód '{user_input}' nie je platný 2-písmenový kód krajiny.")
                return ""
        
        return ""
    
    def _calculate_preliminary_weight(self, item_code: Optional[str], quantity: Any, 
                                    product_weights: Dict[str, float], item_identifier: str, is_product: bool) -> str:
        """Vypočíta predbežnú hmotnosť položky."""
        if not is_product or not item_code or not product_weights:
            return ""
        
        unit_weight = product_weights.get(item_code)
        if unit_weight is None:
            if is_product:
                logger.warning(f"Hmotnosť nebola nájdená pre kód '{item_code}'")
            return "NENÁJDENÉ"
        
        try:
            numeric_quantity = validate_quantity(quantity)
            preliminary_weight = numeric_quantity * unit_weight
            return f"{preliminary_weight:.3f}".replace('.', ',')
        except Exception as e:
            logger.warning(f"Chyba pri výpočte hmotnosti pre '{item_identifier}': {e}")
            return "CHYBA_QTY"
    
    def _assign_customs_codes(self, items: List[Dict[str, Any]], customs_codes: Dict[str, str]) -> None:
        """Priraďuje colné kódy k položkám pomocou AI."""
        logger.info(f"Priradenie colných kódov pre {len(items)} položiek")
        
        for item in items:
            if "PAGE ANALYSIS FAILED" in item.get("Item Name", ""):
                continue
            
            item_details = {
                "Item Name": item.get("Item Name", ""),
                "item_code": item.get("Item Name", ""),
                "description": item.get("description", ""),
                "location": item.get("Location", "")
            }
            
            try:
                customs_code, reasoning = self.ai_analyzer.assign_customs_code(item_details, customs_codes)
                self.metrics.ai_call_made(self.settings.customs_model, "customs_assignment")
                
                item["Colný kód"] = customs_code
                if customs_code != "NEURCENE":
                    item["Popis colného kódu"] = customs_codes.get(customs_code, "Popis nenájdený")
                else:
                    item["Popis colného kódu"] = "Kód nebol určený AI"
                
                logger.debug(f"Priradený colný kód {customs_code} pre {item['Item Name']}")
                
            except Exception as e:
                logger.error(f"Chyba pri priradení colného kódu pre {item['Item Name']}: {e}")
                item["Colný kód"] = "NEPRIRADENÉ"
                item["Popis colného kódu"] = "Chyba pri priradení AI"
    
    def _get_target_weights_from_user(self, invoice_number: str) -> Optional[Dict[str, float]]:
        """Získa cieľové hmotnosti od používateľa."""
        print(f"\n--- Zadanie hmotností pre faktúru: {invoice_number} ---")
        
        try:
            gross_input = input(f"Zadajte CIEĽOVÚ CELKOVÚ HRUBÚ hmotnosť (kg) pre faktúru {invoice_number}: ")
            target_gross_kg = float(gross_input)
            
            net_input = input(f"Zadajte CIEĽOVÚ CELKOVÚ ČISTÚ hmotnosť (kg) pre faktúru {invoice_number}: ")
            target_net_kg = float(net_input)
            
            if target_gross_kg < target_net_kg:
                logger.warning("Hrubá hmotnosť je menšia ako čistá hmotnosť!")
            
            logger.info(f"Cieľové hmotnosti: hrubá={target_gross_kg}kg, čistá={target_net_kg}kg")
            
            return {
                "target_gross_kg": target_gross_kg,
                "target_net_kg": target_net_kg
            }
            
        except ValueError as e:
            logger.error(f"Neplatný vstup pre hmotnosti: {e}")
            return None
    
    def _adjust_weights_with_ai(self, items: List[Dict[str, Any]], target_weights: Dict[str, float]) -> None:
        """Upraví hmotnosti položiek pomocou AI."""
        # Filtrovanie položiek vhodných pre úpravu hmotností
        valid_items = [item for item in items if self._is_valid_for_weight_adjustment(item)]
        
        if not valid_items:
            logger.warning("Žiadne položky nie sú vhodné pre AI úpravu hmotností")
            return
        
        # Výpočet predbežnej celkovej hmotnosti
        preliminary_total = 0.0
        for item in valid_items:
            weight_str = item.get("Preliminary Net Weight", "")
            if weight_str and weight_str not in ["NENÁJDENÉ", "CHYBA_QTY"]:
                try:
                    weight = float(str(weight_str).replace(',', '.'))
                    preliminary_total += weight
                except ValueError:
                    continue
        
        logger.info(f"Úprava hmotností pre {len(valid_items)} položiek, predbežný súčet: {preliminary_total:.3f}kg")
        
        try:
            adjusted_weights = self.ai_analyzer.adjust_weights(
                items_data=valid_items,
                target_net_kg=target_weights["target_net_kg"],
                target_gross_kg=target_weights["target_gross_kg"],
                preliminary_net_kg=preliminary_total
            )
            self.metrics.ai_call_made(self.settings.main_model, "weight_adjustment")
            
            if adjusted_weights:
                self._apply_corrected_weights(items, adjusted_weights)
                logger.info("AI úprava hmotností úspešne aplikovaná")
            else:
                logger.warning("AI nevrátila platné upravené hmotnosti")
            
        except Exception as e:
            logger.error(f"Chyba pri AI úprave hmotností: {e}")
    
    def _is_valid_for_weight_adjustment(self, item: Dict[str, Any]) -> bool:
        """Určí či je položka vhodná pre AI úpravu hmotností."""
        if "PAGE ANALYSIS FAILED" in item.get("Item Name", ""):
            return False
        
        preliminary_weight = item.get("Preliminary Net Weight", "")
        if not preliminary_weight or preliminary_weight in ["NENÁJDENÉ", "CHYBA_QTY", "CHÝBAJÚ_DÁTA_HMOTNOSTI"]:
            return False
        
        # Kontrola či nie je non-product item
        item_name = item.get("Item Name", "").lower()
        description = item.get("description", "").lower()
        
        for keyword in NON_PRODUCT_KEYWORDS:
            if keyword in item_name or keyword in description:
                return False
        
        return True
    
    def _apply_corrected_weights(self, all_items: List[Dict[str, Any]], adjusted_weights: List[Dict[str, Any]]) -> None:
        """Aplikuje upravené hmotnosti na položky - opravená verzia."""
        logger.info(f"🔧 Aplikujem upravené hmotnosti na {len(all_items)} položiek")
        logger.info(f"📊 Mám k dispozícii {len(adjusted_weights)} upravených hmotností")
        
        # DEBUG: Zobrazenie štruktúry adjusted_weights
        for i, adj_item in enumerate(adjusted_weights[:3]):
            logger.debug(f"   Adjusted item {i}: {adj_item}")
        
        # Vytvorenie mapy upravených hmotností
        weight_map = {}
        for adjusted_item in adjusted_weights:
            item_key = adjusted_item.get("item_code") or adjusted_item.get("Item Name")
            if item_key:
                weight_map[item_key] = adjusted_item
                logger.debug(f"   Pridaný do weight_map: {item_key}")
        
        logger.info(f"🗺️ Weight map vytvorená pre {len(weight_map)} položiek")
        
        applied_count = 0
        skipped_count = 0
        
        for item in all_items:
            item_code = item.get("Item Name")
            adjusted_item = weight_map.get(item_code)
            
            if adjusted_item:
                # Použiť AI upravené hmotnosti
                net_weight = adjusted_item.get("Final Net Weight", "")
                gross_weight = adjusted_item.get("Final Gross Weight", "")
                
                logger.debug(f"🔍 DEBUG pre '{item_code}':")
                logger.debug(f"   - Final Net Weight: '{net_weight}'")
                logger.debug(f"   - Final Gross Weight: '{gross_weight}'")
                
                item["Total Net Weight"] = net_weight
                item["Total Gross Weight"] = gross_weight
                applied_count += 1
                
                logger.info(f"✅ Aplikované hmotnosti pre '{item_code}': net={net_weight}, gross={gross_weight}")
            else:
                # Pre položky bez úpravy
                preliminary_net = item.get("Preliminary Net Weight", "")
                item["Total Net Weight"] = preliminary_net
                
                if preliminary_net and preliminary_net not in ["NENÁJDENÉ", "CHYBA_QTY", ""]:
                    try:
                        net_val = float(str(preliminary_net).replace(',', '.'))
                        gross_val = net_val * 1.1
                        item["Total Gross Weight"] = f"{gross_val:.3f}".replace('.', ',')
                    except ValueError:
                        item["Total Gross Weight"] = preliminary_net
                else:
                    item["Total Gross Weight"] = preliminary_net
                
                skipped_count += 1
                logger.debug(f"⏭️ Použitá predbežná hmotnosť pre '{item_code}': {preliminary_net}")
        
        logger.info(f"📈 Aplikácia hmotností dokončená: {applied_count} aplikovaných, {skipped_count} preskočených")
    
    def _write_to_csv(self, items: List[Dict[str, Any]], invoice_number: str) -> str:
        """Zapíše spracované dáta do CSV súboru."""
        # Vytvorenie bezpečného názvu súboru
        safe_invoice_id = re.sub(r'[\\/*?:"<>|]', "_", str(invoice_number))
        csv_filename = f"processed_invoice_data_{safe_invoice_id}.csv"
        csv_path = os.path.join(self.settings.output_csv_dir, csv_filename)
        
        logger.info(f"Zapisujem {len(items)} položiek do CSV: {csv_path}")
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=DEFAULT_CSV_HEADERS, delimiter=';')
                writer.writeheader()
                
                # Zabezpečenie že všetky položky majú všetky požadované kľúče
                processed_rows = []
                for item in items:
                    row = {header: item.get(header, "") for header in DEFAULT_CSV_HEADERS}
                    processed_rows.append(row)
                
                writer.writerows(processed_rows)
            
            logger.info(f"CSV súbor úspešne vytvorený: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Chyba pri zápise CSV súboru {csv_path}: {e}")
            raise IntrastatError(f"Chyba pri zápise CSV: {e}")
    
    def _create_meta_file(self, csv_path: str, original_pdf_name: str) -> None:
        """Vytvorí meta súbor s informáciou o pôvodnom PDF."""
        meta_path = csv_path + ".meta"
        
        try:
            with open(meta_path, 'w', encoding='utf-8') as meta_file:
                meta_file.write(original_pdf_name)
            
            logger.debug(f"Meta súbor vytvorený: {meta_path}")
            
        except Exception as e:
            logger.warning(f"Chyba pri vytváraní meta súboru {meta_path}: {e}")
    
    def _move_processed_pdf(self, pdf_file: str) -> None:
        """Presunie spracovaný PDF do processed adresára."""
        source_path = os.path.join(self.settings.input_pdf_dir, pdf_file)
        destination_path = os.path.join(self.settings.processed_pdf_dir, pdf_file)
        
        try:
            shutil.move(source_path, destination_path)
            logger.info(f"PDF presunumý do processed: {pdf_file}")
            
        except Exception as e:
            logger.error(f"Chyba pri presúvaní PDF {pdf_file}: {e}")
    
    def _create_error_item(self, page_number: int, invoice_number: str, error_message: str) -> Dict[str, Any]:
        """Vytvorí error záznam pre neúspešne spracovanú stranu."""
        return {
            "Page Number": page_number,
            "Invoice Number": invoice_number,
            "Item Name": f"PAGE ANALYSIS FAILED: {error_message}",
            "description": "",
            "Location": "",
            "Quantity": "",
            "Unit Price": "",
            "Total Price": "",
            "Preliminary Net Weight": "",
            "Total Net Weight": "",
            "Total Gross Weight": "",
            "Colný kód": "",
            "Popis colného kódu": ""
        } 