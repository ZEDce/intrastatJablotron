#!/usr/bin/env python3
"""
Test súbor pre overenie funkčnosti refaktorovanej verzie.
"""
import sys
import os

# Pridanie src do path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Otestuje importy a základnú funkcionalitu."""
    print("🔍 Testujem importy...")
    
    try:
        # Test config
        from src.config import AppSettings
        print("✅ Config import OK")
        
        # Test settings
        settings = AppSettings.from_env()
        print("✅ Settings creation OK")
        print(f"   📂 Input PDF dir: {settings.input_pdf_dir}")
        print(f"   📂 Output CSV dir: {settings.output_csv_dir}")
        print(f"   📂 Processed PDF dir: {settings.processed_pdf_dir}")
        
        # Test logging
        from src.utils.logging_config import setup_logging, get_logger
        print("✅ Logging import OK")
        
        # Test data manager
        from src.data.csv_loader import DataManager
        print("✅ DataManager import OK")
        
        # Test models
        from src.models.invoice_processor import InvoiceProcessor
        from src.models.pdf_processor import PDFProcessor  
        from src.models.ai_analyzer import GeminiAnalyzer
        print("✅ Models import OK")
        
        # Test exceptions
        from src.utils.exceptions import IntrastatError, ConfigurationError
        print("✅ Exceptions import OK")
        
        # Test validators
        from src.utils.validators import validate_country_code, validate_pdf_file
        print("✅ Validators import OK")
        
        print("\n🎉 Všetky importy úspešné!")
        return True
        
    except Exception as e:
        print(f"❌ Chyba pri importe: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Otestuje základnú funkcionalitu."""
    print("\n🔧 Testujem základnú funkcionalitu...")
    
    try:
        from src.config import AppSettings
        from src.data.csv_loader import DataManager
        
        settings = AppSettings.from_env()
        data_manager = DataManager(settings)
        
        # Test data validation
        validation_results = data_manager.validate_data_files()
        print(f"✅ Data validation OK: {validation_results}")
        
        # Test environment 
        print(f"✅ Python version: {sys.version}")
        print(f"✅ Working directory: {os.getcwd()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chyba pri teste funkcionality: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("    INTRASTAT JABLOTRON - TEST REFAKTOROVANEJ VERZIE")
    print("=" * 60)
    
    # Test importov
    import_success = test_imports()
    
    if import_success:
        # Test funkcionality
        func_success = test_basic_functionality()
        
        if func_success:
            print("\n" + "=" * 60)
            print("✅ VŠETKY TESTY ÚSPEŠNÉ!")
            print("🚀 Refaktorovaná verzia je pripravená na použitie!")
            print("\nPre spustenie použite:")
            print("   python main_new.py")
            print("=" * 60)
        else:
            print("\n❌ Test funkcionality neúspešný!")
            sys.exit(1)
    else:
        print("\n❌ Test importov neúspešný!")
        sys.exit(1) 