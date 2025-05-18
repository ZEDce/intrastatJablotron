# Nástroj na Spracovanie Faktúr a Generovanie Intrastat Reportov

Tento nástroj automatizuje extrakciu dát z PDF faktúr, priradenie colných kódov, úpravu hmotností položiek a následné generovanie súhrnných CSV reportov pre potreby Intrastatu.

## Kľúčové Funkcie

*   **Extrakcia dát z PDF:** Pomocou AI (Google Gemini) extrahuje položky, množstvá, ceny a ďalšie údaje z PDF faktúr.
*   **Priradenie Colných Kódov:** Automaticky priraďuje colné kódy k položkám pomocou AI a lokálneho zoznamu kódov.
*   **Výpočet a Úprava Hmotností:** Vypočíta predbežné čisté hmotnosti a následne pomocou AI a používateľom zadaných celkových súčtov upraví čisté a hrubé hmotnosti pre každú položku.
*   **Generovanie CSV Výstupov:** Vytvára CSV súbory so spracovanými dátami z faktúr.
*   **Súhrnný Intrastat Report:** Generuje finálny CSV report zoskupený podľa colnej sadzby a krajiny pôvodu, pripravený pre Intrastat.

## Inštalácia a Príprava

1.  **Python:** Uistite sa, že máte nainštalovaný Python (verzia 3.7+).
2.  **Knižnice:** Otvorte terminál/príkazový riadok v priečinku projektu a spustite:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Google API Kľúč:**
    *   Vytvorte súbor `.env` v hlavnom priečinku projektu.
    *   Vložte doň váš Google API kľúč: `GOOGLE_API_KEY=VAS_AKTUALNY_API_KLUC`
4.  **Vstupné Súbory (v priečinku `data/`):
    *   **PDF Faktúry:** Vložte všetky PDF faktúry, ktoré chcete spracovať, do podpriečinka `invoices/`.
    *   `data/product_weight.csv`: Súbor s jednotkovými hmotnosťami produktov (formát: `kod_produktu;hmotnost_s_des_ciarkou`, oddelené bodkočiarkou).
    *   `data/col_sadz.csv`: Súbor s colnými kódmi a ich popismi (formát: `kod_colnej_sadzby;Popis`, oddelené bodkočiarkou).

## Používanie Aplikácie

Spustite hlavný skript z terminálu v priečinku projektu:

```bash
python main.py
```

Zobrazí sa menu:

1.  **Spracovať nové PDF faktúry:**
    *   Skript spracuje PDF faktúry z `invoices/`.
    *   Pre každú faktúru sa opýta na **cieľovú celkovú čistú a hrubú hmotnosť**.
    *   Počas spracovania sa môžu zobraziť výzvy na manuálne doplnenie **krajiny pôvodu** pre niektoré položky, ak ju AI nedokáže extrahovať.
    *   Výsledné CSV súbory s detailnými dátami pre každú faktúru sa uložia do `data_output/`.
    *   Spracované PDF faktúry sa presunú do `processed_invoices/`.

2.  **Generovať súhrnný report z CSV:**
    *   Umožní vybrať jeden z CSV súborov z `data_output/`.
    *   Vygeneruje súhrnný CSV report (napr. `summary_report_NAZOV.csv`) do priečinka `dovozy/`.
    *   Tento report zoskupuje dáta podľa colnej sadzby a krajiny pôvodu, upravuje započítanie zliav a poplatkov a pridáva celkový súčtový riadok.

3.  **Zobraziť colné kódy:**
    *   Zobrazí zoznam colných kódov načítaných zo súboru `data/col_sadz.csv`.

4.  **Ukončiť:** Ukončí aplikáciu.

## Štruktúra Priečinkov

*   `invoices/`: Sem umiestnite vstupné PDF faktúry.
*   `data/`: Obsahuje pomocné CSV súbory (`product_weight.csv`, `col_sadz.csv`).
*   `data_output/`: Sem sa ukladajú CSV súbory vygenerované po spracovaní jednotlivých faktúr (výstup z `main.py`).
*   `dovozy/`: Sem sa ukladajú finálne súhrnné CSV reporty (výstup z `report.py`).
*   `pdf_images/`: Dočasný priečinok pre obrázky strán PDF počas spracovania (automaticky sa čistí).
*   `processed_invoices/`: Sem sa presúvajú PDF faktúry po úspešnom spracovaní.

## Dôležité Poznámky

*   Kvalita extrakcie dát závisí od kvality PDF faktúr a presnosti Gemini API.
*   Pravidelne kontrolujte aktuálnosť súborov `product_weight.csv` a `col_sadz.csv`.
*   Používanie Google Gemini API môže byť spoplatnené. Sledujte svoje využitie v Google Cloud Console.

---
*Technické detaily a presné odhady nákladov na API boli z pôvodného README odstránené pre stručnosť. V prípade potreby je možné nahliadnuť do histórie verzií súboru alebo konzultovať s vývojárom.*
