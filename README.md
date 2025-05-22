# 🚀 Intrastat Asistent - Refaktorovaná Verzia

## 📋 Prehľad

Kompletne refaktorovaná verzia Intrastat Asistenta s modulárnou architektúrou, rozšíreným error handlingom, professional logging systémom a pokročilými funkciami.

### ✨ Nové Funkcie v Refaktorovanej Verzii

- 🏗️ **Modulárna architektúra** - rozdelenie do logických komponentov
- 📊 **Professional logging** s rotáciou súborov a detailnými metrikami
- ⚡ **Progress tracking** s real-time feedback
- 🛡️ **Robustné error handling** s custom exception hierarchy
- ⚙️ **Centralizované nastavenia** cez environment variables
- 🔄 **Rate limiting** pre AI API volania
- 📈 **Processing metrics** a štatistiky
- 🎯 **Validácia vstupov** na všetkých úrovniach
- 🔍 **Data validation** pre CSV súbory
- 🎨 **Vylepšené užívateľské rozhranie** s emoji a progress bars

## 📁 Nová Štruktúra Projektu

```
intrastatJablotron/
├── data/                          # 📦 Vstupné dáta (napr. CSV s kódmi, hmotnosťami)
├── data_output/                   # 📤 Výstupné CSV reporty
├── data_output_archiv/            # 🗄️ Archív starších CSV reportov
├── dovozy/                        # ✈️ Dáta pre dovozné faktúry (ak sa používa)
├── faktury_na_spracovanie/        # 📥 PDF faktúry čakajúce na spracovanie
├── logs/                          # 📋 Log súbory aplikácie (auto-vytvorené)
├── pdf_images/                    # 🖼️ Dočasné obrázky z PDF (pre AI analýzu)
├── spracovane_faktury/            # ✅ PDF faktúry, ktoré už boli spracované
├── src/                           # 🏗️ Hlavný source kód aplikácie
│   ├── __init__.py                # 📦 Inicializácia src balíka
│   ├── report.py                  # 📄 Generovanie súhrnných CSV reportov
│   ├── config.py                  # ⚙️ Centrálne nastavenia a konfigurácia
│   ├── models/                    # 🧠 Business logic a dátové modely
│   │   ├── __init__.py            # 📦 Inicializácia models balíka
│   │   ├── ai_analyzer.py         # 🤖 Správa AI modelov a API volaní
│   │   ├── pdf_processor.py       # 📄 Spracovanie PDF, konverzia na obrázky
│   │   └── invoice_processor.py   # 🎯 Orchestrácia spracovania faktúr
│   ├── data/                      # 💾 Moduly pre načítanie a správu dát
│   │   ├── __init__.py            # 📦 Inicializácia data balíka
│   │   └── csv_loader.py          # 📊 Načítanie dát z CSV súborov
│   └── utils/                     # 🛠️ Pomocné funkcie a utility
│       ├── __init__.py            # 📦 Inicializácia utils balíka
│       ├── exceptions.py          # ⚠️ Definície vlastných výnimiek
│       ├── validators.py          # ✅ Funkcie pre validáciu dát
│       └── logging_config.py      # 📝 Konfigurácia logovacieho systému
├── .env                           # 🔑 Lokálne konfiguračné premenné (GIT IGNORED)
├── .env.example                   #  📄 Príklad .env súboru
├── .gitignore                     # 🚫 Špecifikácia ignorovaných súborov Gitom
├── environment.yml                # 🐍 Závislosti projektu pre Conda prostredie
├── LICENSE                        # 📜 Licencia projektu
├── main.py                        # ▶️ Hlavný spúšťací skript aplikácie
└── README.md                      # 📖 Táto dokumentácia
```

## 🚀 Quick Start

### 1. Inštalácia Dependencies

```bash
pip install -r requirements.txt
```

### 2. Konfigurácia Environment Variables

Vytvorte `.env` súbor:

```bash
# Povinné
GOOGLE_API_KEY=your_gemini_api_key_here

# Voliteľné (s default hodnotami)
PDF_DPI=200
MAX_RETRIES=3
BATCH_SIZE=5
LOG_LEVEL=INFO
```

### 3. Spustenie

```bash
python main.py
```

### 4. Výber z Menu

```
==================================================
        INTRASTAT ASISTENT MENU
==================================================
1. 📄 Spracovať nové PDF faktúry
2. 📊 Generovať súhrnný report z CSV
3. 🏷️  Zobraziť colné kódy
6. ❌ Ukončiť
==================================================
```

## 🏗️ Architektúra

### Core Components

#### 🎯 InvoiceProcessor
Hlavný orchestrátor celého workflow:
- Koordinuje všetky komponenty
- Progress tracking s tqdm
- Metrics collection
- Error recovery

#### 🤖 GeminiAnalyzer
AI management s pokročilými funkciami:
- Rate limiting pre API volania
- Connection pooling
- Response parsing s error handling
- Custom prompts pre rôzne úlohy

#### 📄 PDFProcessor
Memory-efficient PDF spracovanie:
- Generator-based processing
- Image cleanup utilities
- PDF metadata extraction
- Configurable DPI settings

#### 💾 DataManager
Centralizované dátové operácie:
- Cached CSV loaders
- Data validation
- Error reporting
- BOM handling

### 🛡️ Error Handling System

```python
# Custom exception hierarchy
IntrastatError
├── ConfigurationError      # Konfiguračné chyby
├── PDFProcessingError      # PDF konverzia a spracovanie
├── AIAnalysisError         # AI API a response handling
├── DataValidationError     # Input validation
├── CSVProcessingError      # CSV operácie
├── WeightCalculationError  # Hmotnostné výpočty
├── CustomsCodeError        # Colné kódy
├── FileOperationError      # Súborové operácie
└── RateLimitExceededError  # API rate limiting
```

### 📊 Logging System

```python
# Hierarchické logging s rotáciou
logs/
├── intrastat.log          # Všetky logy (max 10MB, 5 backups)
└── errors.log             # Iba errors (max 5MB, 3 backups)

# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
# UTF-8 encoding support
# Timestamp + Module + Level + Message format
```

### ⚙️ Configuration Management

```python
# AppSettings dataclass s environment support
@dataclass
class AppSettings:
    google_api_key: str = os.getenv("GOOGLE_API_KEY")
    pdf_dpi: int = int(os.getenv("PDF_DPI", "200"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    # ... a ďalšie nastavenia
    
    def validate(self) -> None:
        # Validácia všetkých nastavení
    
    def ensure_directories(self) -> None:
        # Vytvorenie potrebných adresárov
```

## 📈 Performance Optimizations

### 🔄 Rate Limiting
```python
@rate_limit(calls_per_minute=30)
def ai_api_call(self, ...):
    # Automatické rate limiting pre AI volania
```

### 💾 Memory Management
```python
def pdf_to_images_generator(self, pdf_path):
    # Generator pattern pre memory-efficient processing
    for page_num in range(total_pages):
        yield process_page(page_num)
        # Automatické uvoľnenie pamäte
```

### 🏪 Caching
```python
class DataManager:
    def get_product_weights(self, force_reload=False):
        if self._weights_cache is None or force_reload:
            self._weights_cache = self.weight_loader.load_weights()
        return self._weights_cache
```

## 🔍 Monitoring & Metrics

### 📊 Processing Metrics
```python
class ProcessingMetrics:
    - processed_pdfs: int           # Úspešne spracované
    - failed_pdfs: int             # Neúspešné
    - ai_api_calls: int            # Počet AI volaní
    - processing_time: float       # Celkový čas
    - success_rate_percent: float  # Úspešnosť %
    - avg_time_per_pdf: float      # Priemerný čas na PDF
```

### 📋 Data Validation Reports
```python
validation_results = {
    "product_weights": True/False,
    "customs_codes": True/False
}
# Detailné error reporting pre každý súbor
```

## 🛠️ Advanced Features

### 🎯 Smart Input Validation
```python
# Validácia na všetkých úrovniach
validate_pdf_file(file_path, max_size_mb=50)
validate_country_code("SK")  # ISO 3166-1 alpha-2
validate_customs_code("85311030")  # 8-digit format
validate_weight("123,45")  # Slovak decimal format support
```

### 🤖 Enhanced AI Prompts
- Špecializované prompty pre invoice analysis
- Pokročilé customs code assignment s context
- Weight adjustment s precision targeting
- Hardcoded overrides pre špecifické produkty

### 📊 Progress Tracking
```python
# Real-time progress s tqdm
with tqdm(total=len(pdf_files), desc="Spracovávam PDF") as pbar:
    for pdf_file in pdf_files:
        pbar.set_description(f"Spracovávam: {pdf_file}")
        # processing...
        pbar.update(1)
```

## 🔧 Migration Guide

### Z Pôvodnej Verzie na Refaktorovanú

1. **Backup dát**:
   ```bash
   cp -r data_output/ data_output_backup/
   cp -r spracovane_faktury/ spracovane_faktury_backup/
   ```

2. **Environment setup**:
   ```bash
   # Vytvorte .env súbor s API kľúčom
   echo "GOOGLE_API_KEY=your_key_here" > .env
   ```

3. **Testovanie**:
   ```bash
   # Použite malý test PDF najprv
   python main_new.py
   ```

4. **Postupná migrácia**:
   - Refaktorovaná verzia je plne kompatibilná s existujúcimi dátami
   - Pôvodný `main.py` zostáva funkčný pre backward compatibility
   - Postupne presúvajte workflow na `main_new.py`

## 🐛 Troubleshooting

### Časté Problémy

1. **Import Error**: `ModuleNotFoundError: No module named 'src'`
   ```bash
   # Riešenie: Spustite z root adresára projektu
   cd /path/to/intrastatJablotron
   python main_new.py
   ```

2. **API Rate Limiting**: `RateLimitExceededError`
   ```bash
   # Riešenie: Nastavte nižší rate limit v .env
   echo "AI_RATE_LIMIT_PER_MINUTE=20" >> .env
   ```

3. **Memory Issues**: Pri veľkých PDF súboroch
   ```bash
   # Riešenie: Znížte DPI v .env
   echo "PDF_DPI=150" >> .env
   ```

4. **Logging Issues**: Problémy s UTF-8
   ```bash
   # Riešenie: Nastavte správne locale
   export LANG=en_US.UTF-8
   export LC_ALL=en_US.UTF-8
   ```

### 📋 Debug Mode

```bash
# Nastavte DEBUG level pre detailné logy
echo "LOG_LEVEL=DEBUG" >> .env
python main_new.py

# Skontrolujte logs
tail -f logs/intrastat.log
tail -f logs/errors.log
```

## 🎯 Best Practices

### 1. **Environment Management**
```bash
# Používajte .env súbor pre konfiguráciu
# Nikdy necommitujte API kľúče do git
echo ".env" >> .gitignore
```

### 2. **Monitoring**
```bash
# Pravidelne kontrolujte logy
tail -f logs/intrastat.log

# Sledujte metrics cez menu option 5
```

### 3. **Data Backup**
```bash
# Pred väčšími zmenami backupujte dáta
cp -r data_output/ backup_$(date +%Y%m%d)/
```

### 4. **Performance Tuning**
```bash
# Pre veľké objemy nastavte batch processing
echo "BATCH_SIZE=3" >> .env
echo "AI_RATE_LIMIT_PER_MINUTE=20" >> .env
```

## 🚀 Budúce Vylepšenia

### Plánované Features
- 🌐 **Web Interface** - Django/Flask frontend
- 🗄️ **Database Integration** - SQLite/PostgreSQL support
- 📊 **Advanced Analytics** - dashboards a reporting
- 🔄 **Async Processing** - parallel PDF processing
- 🔐 **Enhanced Security** - role-based access
- 📱 **Mobile Support** - responsive design
- 🤝 **API Integration** - REST API endpoints
- 🧪 **Unit Testing** - comprehensive test suite

### Contributions Welcome
- Fork the repository
- Create feature branch: `git checkout -b feature/amazing-feature`
- Commit changes: `git commit -m 'Add amazing feature'`
- Push to branch: `git push origin feature/amazing-feature`
- Open Pull Request

## 📞 Support

### Dokumentácia
- **Audit Report**: `audit.md` - detailná analýza zlepšení
- **Original README**: `README.md` - pôvodná dokumentácia
- **Config Reference**: `src/config.py` - všetky nastavenia

### Kontakt
- Otvorte GitHub issue pre bugs a feature requests
- Skontrolujte logy pre debugging informácie
- Použite menu option 4 pre validáciu dát

---

## 🎉 Záver

Refaktorovaná verzia predstavuje významný upgrade v kvalite, maintainability a profesionalite kódu. Zachováva všetku pôvodnú funkcionalitu while adding enterprise-grade features ako logging, metrics, validation, a error handling.

**Hlavné benefity:**
- ✅ **Production-ready** kód s professional štandardmi
- ✅ **Modulárna architektúra** pre jednoduché rozšírenie
- ✅ **Comprehensive error handling** pre robustné spracovanie
- ✅ **Performance optimizations** pre škálovateľnosť
- ✅ **Monitoring a metrics** pre operational insight
- ✅ **Backward compatibility** s existujúcimi dátami

Začnite s `python main_new.py` a zažite rozdiel! 🚀 