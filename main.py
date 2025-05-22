#!/usr/bin/env python3
"""
Intrastat Asistent - Hlavný vstupný bod aplikácie.

Refaktorovaná verzia s modulárnou architektúrou.
"""
import os
import sys
from dotenv import load_dotenv

# Načítanie environment variables
load_dotenv()

# Pridanie src do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import AppSettings
from src.models.invoice_processor import InvoiceProcessor
from src.utils.logging_config import setup_logging, get_logger
from src.utils.exceptions import ConfigurationError, IntrastatError
from src.data.csv_loader import DataManager

# Import report functions z pôvodného report.py
from src.report import list_csv_files, get_customs_code_descriptions, generate_single_report, prompt_and_generate_report


def main():
    """Hlavná funkcia aplikácie."""
    try:
        # Načítanie a validácia konfigurácie
        settings = AppSettings.from_env()
        settings.validate()
        
        # Nastavenie logging systému
        setup_logging(settings)
        logger = get_logger(__name__)
        
        logger.info("=== Intrastat Asistent Spustený ====")
        logger.info(f"Konfigurácia načítaná a validovaná")
        
        # Spustenie hlavného menu
        run_main_menu(settings, logger)
        
    except ConfigurationError as e:
        print(f"CHYBA KONFIGURÁCIE: {e}")
        print("Uistite sa, že máte správne nastavené environment variables.")
        sys.exit(1)
    except Exception as e:
        print(f"KRITICKÁ CHYBA: {e}")
        sys.exit(1)


def run_main_menu(settings: AppSettings, logger):
    """Spustí hlavné menu aplikácie."""
    processor = InvoiceProcessor(settings)
    data_manager = DataManager(settings)
    
    while True:
        print("\n" + "="*50)
        print("        INTRASTAT ASISTENT MENU")
        print("="*50)
        print("1. 📄 Spracovať nové PDF faktúry")
        print("2. 📊 Generovať súhrnný report z CSV")
        print("3. 🏷️  Zobraziť colné kódy")
        print("4. ❌ Ukončiť")
        print("="*50)
        
        choice = input("Zadajte vašu voľbu (1-4): ").strip()
        
        try:
            if choice == '1':
                handle_pdf_processing(processor, logger)
            elif choice == '2':
                handle_report_generation(logger)
            elif choice == '3':
                handle_customs_codes_display(data_manager, logger)
            elif choice == '4':
                logger.info("Aplikácia ukončená používateľom")
                print("👋 Aplikácia sa ukončuje. Dovidenia!")
                break
            else:
                print("❌ Neplatná voľba. Prosím, vyberte číslo 1-4.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Operácia prerušená používateľom.")
            logger.info("Operácia prerušená Ctrl+C")
        except Exception as e:
            logger.error(f"Chyba v menu operácii: {e}")
            print(f"❌ Nastala chyba: {e}")
            print("💡 Podrobnosti nájdete v log súboroch.")


def handle_pdf_processing(processor: InvoiceProcessor, logger):
    """Spracuje PDF faktúry."""
    logger.info("Používateľ vybral spracovanie PDF")
    print("\n🔄 Začínam spracovanie PDF faktúr...")
    
    try:
        # Kontrola dostupných PDF súborov
        available_pdfs = processor.pdf_processor.get_available_pdfs()
        
        if not available_pdfs:
            print("⚠️  Neboli nájdené žiadne PDF súbory na spracovanie.")
            print(f"   Uistite sa, že máte PDF súbory v adresári: {processor.settings.input_pdf_dir}")
            return
        
        print(f"📋 Nájdených {len(available_pdfs)} PDF súborov na spracovanie:")
        for i, pdf in enumerate(available_pdfs, 1):
            print(f"   {i}. {pdf}")
        
        confirm = input(f"\n✅ Chcete spracovať všetky súbory? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes', 'a', 'ano']:
            print("❌ Spracovanie zrušené.")
            return
        
        # Spracovanie všetkých PDF
        results = processor.process_all_pdfs()
        
        # Zobrazenie výsledków
        print(f"\n📊 VÝSLEDKY SPRACOVANIA:")
        print(f"   ✅ Úspešne spracované: {len(results.get('processed', []))}")
        print(f"   ❌ Neúspešné: {len(results.get('failed', []))}")
        
        if results.get('failed'):
            print(f"\n❌ Neúspešné súbory:")
            for failed in results['failed']:
                print(f"   • {failed['file']}: {failed['error']}")
        
        summary = results.get('summary', {})
        if summary:
            print(f"\n📈 Štatistiky:")
            print(f"   • Úspešnosť: {summary.get('success_rate_percent', 0)}%")
            print(f"   • Celkový čas: {summary.get('total_processing_time_seconds', 0):.1f}s")
            print(f"   • AI volania: {summary.get('total_ai_calls', 0)}")
        
        logger.info(f"PDF spracovanie dokončené: {results}")
        
    except IntrastatError as e:
        logger.error(f"Chyba pri spracovaní PDF: {e}")
        print(f"❌ Chyba pri spracovaní: {e}")
    except Exception as e:
        logger.error(f"Neočakávaná chyba pri spracovaní PDF: {e}")
        print(f"❌ Neočakávaná chyba: {e}")


def handle_report_generation(logger):
    """Generuje reporty z CSV súborov."""
    logger.info("Používateľ vybral generovanie reportov")
    print("\n📊 Generovanie reportov...")
    
    try:
        # Použitie pôvodnej funkcie z report.py
        prompt_and_generate_report(available_csvs_paths=None)
        logger.info("Report generation dokončené")
        
    except Exception as e:
        logger.error(f"Chyba pri generovaní reportu: {e}")
        print(f"❌ Chyba pri generovaní reportu: {e}")


def handle_customs_codes_display(data_manager: DataManager, logger):
    """Zobrazí dostupné colné kódy."""
    logger.info("Používateľ vybral zobrazenie colných kódov")
    print("\n🏷️  Načítavam colné kódy...")
    
    try:
        customs_codes = data_manager.get_customs_codes()
        
        if not customs_codes:
            print("⚠️  Žiadne colné kódy neboli načítané.")
            print(f"   Skontrolujte súbor: data/col_sadz.csv")
            return
        
        print(f"\n📋 Dostupných {len(customs_codes)} colných kódov:")
        print("-" * 80)
        print(f"{'Kód':<12} | {'Popis'}")
        print("-" * 80)
        
        for code, description in sorted(customs_codes.items()):
            print(f"{code:<12} | {description}")
        
        print("-" * 80)
        logger.info(f"Zobrazených {len(customs_codes)} colných kódov")
        
    except Exception as e:
        logger.error(f"Chyba pri zobrazení colných kódov: {e}")
        print(f"❌ Chyba pri načítaní colných kódov: {e}")


if __name__ == "__main__":
    main() 