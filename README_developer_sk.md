# Extrakcia Dát z PDF Faktúr - Technický Opis

**Cieľ Projektu:** Extrahovať štruktúrované údaje o položkách z viacerých PDF faktúr do CSV súborov, vrátane vypočítanej celkovej čistej hmotnosti pre každú položku, pomocou analýzy obrázkov s využitím AI cez Google Gemini API a lokálneho súboru s hmotnosťami produktov.

**Hlavný Pracovný Postup & Komponenty:**

1.  **Nastavenie Prostredia:**
    *   Využíva súbor `.env` na bezpečné spravovanie `GOOGLE_API_KEY`.
    *   Importuje potrebné knižnice: `glob` na vyhľadávanie PDF súborov, `fitz` (PyMuPDF) na prácu s PDF, `google.generativeai` na interakciu s Gemini API, `os` na súborové operácie, `csv` na CSV I/O, `json` na spracovanie odpovedí od AI.
    *   **Vstupné Súbory:**
        *   PDF faktúry umiestnené v priečinku `data/`.
        *   `data/product_weight.csv`: CSV súbor mapujúci kódy produktov (`Registrační číslo`) na ich jednotkové hmotnosti (`JV Váha komplet SK`), s použitím bodkočiarky ako oddeľovača a desatinnej čiarky pre hmotnosti.

2.  **Načítanie Hmotností Produktov (funkcia `load_product_weights`):**
    *   Načíta `data/product_weight.csv`.
    *   Spracuje CSV, očakáva hlavičku `Registrační číslo;JV Váha komplet SK`.
    *   Konvertuje reťazce hmotností (napr. "0,168") na číselné hodnoty (float).
    *   Vracia slovník mapujúci `item_code` (reťazec) na `unit_weight` (float).
    *   Zahŕňa spracovanie chýb pre nenájdený súbor, chybne formátované riadky a chyby pri konverzii hodnôt.

3.  **Konverzia PDF na Obrázky (funkcia `pdf_to_images`):**
    *   Ako vstup berie cestu k PDF súboru a špecifický `output_folder` pre obrázky daného PDF (napr. `pdf_images/nazov_faktury/`).
    *   Používa `fitz.open()` na otvorenie PDF.
    *   Iteruje cez každú stranu, načíta ju a konvertuje na PNG obrázok pomocou `page.get_pixmap(dpi=200)`.
    *   Ukladá tieto obrázky do špecifikovaného `output_folder` (napr. `pdf_images/nazov_faktury/strana_1.png`).
    *   Vracia zoznam ciest k vygenerovaným obrázkom.
    *   Zahŕňa robustné spracovanie chýb pre API volania a chyby pri dekódovaní JSON, vracia chybový slovník v prípade problémov.

4.  **Analýza Obrázkov s Gemini (funkcia `analyze_image_with_gemini`):**
    *   Ako vstup berie cestu k obrázku a detailný reťazec s výzvou (prompt).
    *   Konfiguruje model Gemini (aktuálne `gemini-1.5-flash-latest`).
    *   Načíta obrázok ako bajty (bytes).
    *   Vytvára slovník `image_part` s `mime_type` a `data` (inline dáta obrázka).
    *   Odosiela časť s obrázkom a výzvu do Gemini API pomocou `model.generate_content()`.
    *   **Prompt Engineering (Tvorba Výzvy):** Kľúčová výzva inštruuje Gemini, aby:
        *   Extrahiovalo celkové číslo faktúry.
        *   Identifikovalo riadkové položky a extrahovalo špecifické polia pre každú: `item_code`, `location`, `quantity`, `unit_price`, `total_price`.
        *   Vrátilo celý výsledok ako jeden validný JSON objekt s hlavným kľúčom `invoice_number` a zoznamom `items` (každá položka je objekt s požadovanými poľami).
    *   Spracúva odpoveď API:
        *   Zaznamenáva surovú textovú odpoveď od Gemini.
        *   Čistí odpoveď odstránením potenciálnych markdown značiek ```json ... ```.
        *   Spracúva (parsuje) vyčistený text na Python slovník pomocou `json.loads()`.
    *   Zahŕňa robustné spracovanie chýb pre API volania a chyby pri dekódovaní JSON, vracia chybový slovník v prípade problémov.

5.  **Spracovanie JSON Odpovede od Gemini (funkcia `process_gemini_response_to_csv_rows`):**
    *   Ako vstup berie spracované JSON dáta od Gemini, číslo strany a slovník `product_weights_map`.
    *   Ak vstup indikuje chybu alebo neočakávanú JSON štruktúru, vytvorí zástupný/chybový riadok pre CSV (vrátane prázdnej "Celkovej Čistej Hmotnosti").
    *   Extrahuje `invoice_number` a zoznam `items` z JSON.
    *   Pre každú položku:
        *   Mapuje JSON polia (`item_code`, `location`, `quantity`, `unit_price`, `total_price`) na CSV polia.
        *   **Výpočet Čistej Hmotnosti:**
            *   Získa `item_code` and `quantity` z dát položky.
            *   Vyhľadá `unit_weight` v `product_weights_map` pomocou `item_code`.
            *   Konvertuje reťazec `quantity` (potenciálne s desatinnou čiarkou) na float.
            *   Ak sú `unit_weight` aj `quantity_float` validné, vypočíta `total_net_weight = quantity_float * unit_weight`.
            *   Formátuje `total_net_weight` na reťazec s 3 desatinnými miestami, s použitím desatinnej čiarky.
            *   Spracúva prípady, keď `item_code` nie je nájdený v `product_weights_map` (hmotnosť nastavená na "NO_WEIGHT_DATA") alebo `quantity` sa nedá konvertovať (hmotnosť nastavená na "QTY_ERR").
        *   Pridá `Celkovú Čistú Hmotnosť` do slovníka pre CSV riadok.
    *   Vracia zoznam slovníkov, každý reprezentujúci CSV riadok.

6.  **Hlavná Orchestrácia (funkcia `main`):**
    *   Definuje vstupné/výstupné priečinky (`data/`, `pdf_images/`, `data_output/`).
    *   **Načíta Hmotnosti Produktov:** Volá `load_product_weights()` pre získanie slovníka `product_weights`. Vytlačí správu, ak načítanie zlyhá, a pokračuje bez výpočtu hmotnosti.
    *   Vykonáva kontrolu a konfiguráciu API kľúča.
    *   Používa `glob.glob()` na nájdenie všetkých `*.pdf` súborov vo vstupnom priečinku.
    *   **Voľba CSV Výstupu Používateľom:** Vyzve používateľa (v slovenčine), aby si vybral medzi jedným spoločným CSV súborom (zadať '1') alebo samostatnými CSV súbormi pre každú faktúru (zadať '2'). Interne mapuje '1' na 'single' a '2' na 'separate'.
    *   Iteruje cez každý nájdený PDF súbor:
        *   Vytvorí unikátny podpriečinok v rámci `pdf_images/` (napr. `pdf_images/nazov_faktury/`) pre obrázky stránok aktuálneho PDF.
        *   Volá `pdf_to_images` na konverziu aktuálneho PDF na obrázky, ukladá ich do dedikovaného podadresára.
        *   Ak sa generuje **jeden CSV súbor** a nie je to prvé spracovávané PDF, pridá oddeľovací riadok do hlavného zoznamu dát. Tento riadok jasne indikuje novú faktúru v CSV, použije názov PDF súboru.
        *   Iteruje cez vygenerované obrázky pre aktuálne PDF:
            *   Volá `analyze_image_with_gemini`.
            *   Volá `process_gemini_response_to_csv_rows`, odovzdávajúc slovník `product_weights`.
            *   Zbiera dáta zo všetkých strán.
        *   **Generovanie Čísla Riadku (Pre Každé PDF):** Pridá sekvenčné "Číslo Riadku".
        *   Ak sa generuje **jeden CSV súbor**, pripojí spracované a očíslované dáta z aktuálneho PDF do zoznamu `master_data_from_all_pdfs`.
        *   Ak sa generujú **samostatné CSV súbory**, spracované a očíslované údaje pre aktuálne PDF sa okamžite zapíšu do vlastného CSV súboru v priečinku `data_output/` (napr. `data_output/nazov_faktury_extracted.csv`).
    *   **Zápis do CSV:**
        *   Definuje `headers` pre CSV: `"Číslo Faktúry", "Číslo Strany", "Číslo Riadku", "Názov Položky", "Lokalita", "Množstvo", "Jednotková Cena", "Celková Cena", "Celková Čistá Hmotnosť"`.
        *   Zapisuje dáta do zvoleného CSV súboru/súborov v `data_output/`.
        *   Zástupné riadky tiež obsahujú prázdnu "Celkovú Čistú Hmotnosť".

7.  **Spustenie:**
    *   Blok `if __name__ == "__main__":` zabezpečuje, že `main()` sa volá pri priamom spustení skriptu.
    *   Zahŕňa predbežné kontroly API kľúča a informatívne výpisy pre používateľa.
    *   **Výpočet Čistej Hmotnosti:** Skript teraz vypočíta celkovú čistú hmotnosť pre každú položku vynásobením jej množstva (z faktúry) jej jednotkovou hmotnosťou (zo súboru `data/product_weight.csv`).
    *   **Voľba Výstupu CSV Používateľom:** Pridaná možnosť pre používateľa rozhodnúť sa, či generovať jeden kombinovaný CSV alebo samostatné CSV súbory pre každú spracovanú faktúru, čo poskytuje väčšiu flexibilitu.
    *   **Spracovanie Viacerých PDF:** Skript teraz spracuje všetky PDF v špecifikovanom adresári a konsoliduje ich dáta do jedného CSV (ak je zvolená táto možnosť).

**Kľúčové Dizajnové Rozhodnutia & Zjednodušenia:**

*   **Voľba Výstupu CSV Používateľom:** Pridaná možnosť pre používateľa rozhodnúť sa, či generovať jeden kombinovaný CSV alebo samostatné CSV súbory pre každú spracovanú faktúru, čo poskytuje väčšiu flexibilitu.
*   **Spracovanie Viacerých PDF:** Skript teraz spracuje všetky PDF v špecifikovanom adresári a konsoliduje ich dáta do jedného CSV (ak je zvolená táto možnosť).
*   **Organizované Ukladanie Obrázkov:** Obrázky strán z rôznych PDF sú ukladané v samostatných podadresároch.
*   **Jasné Oddelenie v CSV:** Oddeľovacie riadky sa pridávajú do CSV (pri voľbe jedného súboru) na rozlíšenie dát z rôznych faktúr.
*   **Prechod na JSON Výstup z AI:** Toto bolo základné vylepšenie, ktoré eliminovalo komplexné regulárne výrazy a urobilo extrakciu dát robustnejšou.
*   **Jasné Oddelenie Zodpovedností:** Funkcie majú zreteľné zodpovednosti.
*   **Cielené Výzvy (Prompting):** Výzva je špecifická, čo zlepšuje spoľahlivosť výstupu AI.
*   **Spracovanie Chýb:** Komplexné spracovanie chýb pre API volania a parsovanie JSON zostáva.
*   **Prispôsobenie Stĺpcov CSV:** Skript bol prispôsobený tak, aby umožňoval flexibilnú definíciu a usporiadanie stĺpcov CSV.
*   **Odstránenie Redundancie:** Odstránená nepotrebná zástupná logika v hlavnej slučke, keďže funkcia spracovania to už riešila.

## Náklady na Používanie API (Gemini 1.5 Flash)

Projekt využíva model `gemini-1.5-flash-latest`. Náklady spojené s Gemini API závisia od počtu tokenov na vstupe (obrázky + textová výzva) a na výstupe (vygenerované JSON dáta).

K augustu 2024 je cena za Gemini 1.5 Flash (platená úroveň, pre výzvy do 128k tokenov) približne:
*   **Vstupné tokeny:** 0,075 $ za 1 milión tokenov
*   **Výstupné tokeny:** 0,30 $ za 1 milión tokenov

**Odhadované náklady pre tento extraktor:**

Na základe typickej zložitosti PDF stránky a množstva extrahovaných dát:
*   **Vstup na stránku (obrázok + výzva):** ~1600 tokenov
*   **Výstup na stránku (JSON dáta):** ~200 tokenov

To vedie k odhadovaným nákladom približne **0,00018 $ na jednu PDF stránku** (menej ako 0,02 amerického centu).

*   Spracovanie **1 000 strán**: približne **0,18 $**
*   Spracovanie **10 000 strán**: približne **1,80 $**

**Poznámka:**
*   Toto sú odhady. Skutočné náklady sa môžu líšiť v závislosti od rozlíšenia/detailu obrázka, dĺžky výzvy a objemu extrahovaných dát.
*   Google ponúka bezplatnú úroveň pre Gemini API, ktorá má limity použitia. Pri rozsiahlom používaní budete pravdepodobne na platenej úrovni.
*   Odporúča sa sledovať vaše využitie a fakturáciu v Google Cloud Console.
*   Ceny sa môžu meniť. Vždy si overte aktuálne informácie na oficiálnej stránke cien Google AI. 