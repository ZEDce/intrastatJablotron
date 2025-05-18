# Nástroj na Spracovanie Faktúr a Generovanie Intrastat Reportov

Tento nástroj automatizuje extrakciu dát z PDF faktúr, priradenie colných kódov, úpravu hmotností položiek a následné generovanie súhrnných CSV reportov pre potreby Intrastatu. Využíva umelú inteligenciu (Google Gemini) na analýzu dokumentov a dát.

## Kľúčové Funkcie

*   **Extrakcia dát z PDF:** Pomocou AI (Google Gemini) extrahuje položky, množstvá, ceny, krajiny pôvodu a ďalšie údaje z PDF faktúr.
*   **Priradenie Colných Kódov:** Automaticky priraďuje colné kódy k položkám pomocou AI a lokálneho zoznamu kódov (`data/col_sadz.csv`).
*   **Výpočet a Úprava Hmotností:** Vypočíta predbežné čisté hmotnosti na základe dát z `data/product_weight.csv` a následne pomocou AI a používateľom zadaných celkových súčtov pre faktúru upraví čisté a hrubé hmotnosti pre každú položku.
*   **Generovanie Detailných CSV Výstupov:** Vytvára CSV súbory so spracovanými dátami pre každú faktúru do priečinka `data_output/`. Popri každom CSV sa vytvára aj `.meta` súbor obsahujúci názov pôvodného PDF.
*   **Súhrnný Intrastat Report:** Generuje finálny súhrnný CSV report (ukladaný do `dovozy/`) z vybraného spracovaného CSV súboru. Tento report zoskupuje dáta podľa colnej sadzby a krajiny pôvodu.
*   **Archivácia Spracovaných Dát:** Po vygenerovaní súhrnného reportu sa zdrojový CSV súbor a jeho `.meta` súbor presunú z `data_output/` do `data_output_archiv/`.

## Požiadavky

*   Python (odporúčaná verzia 3.9+, testované na 3.11)
*   Platný Google API kľúč s prístupom k Gemini API.

## Inštalácia a Príprava

1.  **Naklonujte repozitár:**
    ```bash
    git clone <URL_REPOZITARA>
    cd <NAZOV_PRIECINKA_REPOZITARA>
    ```
2.  **(Odporúčané) Vytvorte a aktivujte virtuálne prostredie:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **Nainštalujte potrebné knižnice:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Nastavte Google API Kľúč:**
    *   Vytvorte súbor `.env` v hlavnom (root) priečinku projektu.
    *   Do súboru vložte váš Google API kľúč v nasledujúcom formáte:
        ```
        GOOGLE_API_KEY=VAS_AKTUALNY_API_KLUC
        ```
5.  **Pripravte vstupné súbory a priečinky:**
    *   **PDF Faktúry:** Vložte PDF faktúry, ktoré chcete spracovať, do priečinka `faktury_na_spracovanie/`.
    *   **Dáta pre hmotnosti:** Vytvorte/upravte súbor `data/product_weight.csv`.
        *   Formát: `Registrační číslo;JV Váha komplet SK` (napr. `KOD123;1.234`)
        *   Oddelovač: Bodkočiarka (`;`)
        *   Desatinné miesta: Čiarka (`,`)
    *   **Dáta pre colné sadzby:** Vytvorte/upravte súbor `data/col_sadz.csv`.
        *   Formát: `col_sadz;Popis` (napr. `85311030;Poplachové zabezpečovacie systémy...`)
        *   Oddelovač: Bodkočiarka (`;`)
        *   Kódovanie: UTF-8 (odporúča sa UTF-8 with BOM, ak sú problémy s diakritikou priamo z Excelu)

## Používanie Aplikácie

Spustite hlavný skript z terminálu v koreňovom priečinku projektu:

```bash
python main.py
```

Zobrazí sa menu s nasledujúcimi možnosťami:

1.  **Spracovať nové PDF faktúry:**
    *   Skript postupne spracuje všetky PDF faktúry nájdené v priečinku `faktury_na_spracovanie/`.
    *   Pre každú faktúru (po extrakcii dát zo všetkých jej strán) sa program opýta na **cieľovú celkovú čistú a hrubú hmotnosť** danej faktúry.
    *   Počas spracovania jednotlivých položiek faktúry sa môžu zobraziť výzvy na manuálne doplnenie **2-písmenového kódu krajiny pôvodu**, ak ju AI nedokáže spoľahlivo extrahovať.
    *   Výsledné CSV súbory s detailnými dátami pre každú spracovanú faktúru (napr. `processed_invoice_data_NAZOV-FAKTURY.csv`) sa uložia do priečinka `data_output/`.
    *   Popri každom CSV súbore sa uloží aj `.meta` súbor (napr. `processed_invoice_data_NAZOV-FAKTURY.csv.meta`) obsahujúci názov pôvodného PDF súboru.
    *   Spracované PDF faktúry sa po úspešnom dokončení týchto krokov presunú z `faktury_na_spracovanie/` do `spracovane_faktury/`.

2.  **Generovať súhrnné reporty z už spracovaných dát:**
    *   Skript (modul `report.py`) ponúkne na výber CSV súbory z priečinka `data_output/`.
    *   Po výbere súboru a zadaní názvu výstupného reportu sa vygeneruje súhrnný CSV report (napr. `summary_report_NAZOV.csv`) do priečinka `dovozy/`.
    *   Tento report zoskupuje dáta podľa colnej sadzby a krajiny pôvodu, upravuje započítanie zliav a manipulačných poplatkov a pridáva celkový súčtový riadok "Spolu".
    *   Po úspešnom vygenerovaní reportu sa použitý CSV súbor a jeho príslušný `.meta` súbor presunú z `data_output/` do `data_output_archiv/`.

3.  **Ukončiť:** Ukončí aplikáciu.

## Štruktúra Priečinkov

*   `main.py`: Hlavný spúšťací skript pre spracovanie PDF faktúr.
*   `report.py`: Modul a skript pre generovanie súhrnných reportov.
*   `requirements.txt`: Zoznam potrebných Python knižníc.
*   `.env`: Súbor pre uloženie Google API kľúča (ignorovaný Gitom).
*   `data/`:
    *   `product_weight.csv`: CSV súbor s kódmi produktov a ich jednotkovými hmotnosťami.
    *   `col_sadz.csv`: CSV súbor s colnými kódmi (sadzbami) a ich popismi.
*   `faktury_na_spracovanie/`: Vstupný priečinok pre PDF faktúry určené na spracovanie.
*   `data_output/`: Priečinok, kam `main.py` ukladá spracované dáta z jednotlivých faktúr vo formáte CSV, spolu s `.meta` súbormi.
*   `dovozy/`: Priečinok, kam `report.py` ukladá finálne súhrnné CSV reporty.
*   `spracovane_faktury/`: Priečinok, kam `main.py` presúva PDF faktúry po ich úspešnom spracovaní a uložení dát.
*   `data_output_archiv/`: Priečinok, kam `report.py` presúva CSV súbory (a ich `.meta` súbory) z `data_output/` po tom, čo boli použité na generovanie súhrnného reportu.
*   `pdf_images/`: Dočasný priečinok pre obrázky extrahované zo stránok PDF počas spracovania. Obsah sa môže premazávať.
*   `venv/`: (Odporúčané) Priečinok pre Python virtuálne prostredie (ignorovaný Gitom).

## Dôležité Poznámky

*   Kvalita extrakcie dát z PDF a presnosť priradenia colných kódov či úpravy hmotností závisí od kvality vstupných PDF faktúr a schopností použitého AI modelu (Gemini).
*   Dôkladne skontrolujte a udržiavajte aktuálne dáta v súboroch `data/product_weight.csv` a `data/col_sadz.csv`, vrátane ich správneho formátovania (oddelovače, kódovanie).
*   Používanie Google Gemini API môže byť spoplatnené. Sledujte svoje využitie a náklady v Google Cloud Console.
*   Pred prvým spustením sa uistite, že všetky potrebné priečinky existujú, alebo ich skripty vytvoria (väčšina by sa mala vytvoriť automaticky pri prvom použití).

## Licencia

Tento projekt je distribuovaný pod licenciou uvedenou v súbore `LICENSE`.
