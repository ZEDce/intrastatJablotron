# Extrakcia Dát z PDF Faktúr

**Cieľ Projektu:** Extrahovať štruktúrované údaje o položkách z viacerých PDF faktúr do CSV súborov, vrátane vypočítanej celkovej čistej hmotnosti pre každú položku, pomocou analýzy obrázkov s využitím AI cez Google Gemini API a lokálneho súboru s hmotnosťami produktov.

## Obsah

- [Používateľská Príručka](#používateľská-príručka)
- [Inštalačná Príručka](#inštalačná-príručka)
- [Technický Opis pre Vývojárov](#technický-opis-pre-vývojárov)
- [Náklady na Používanie API (Gemini 1.5 Flash)](#náklady-na-používanie-api-gemini-15-flash)

## Používateľská Príručka

**Čo tento nástroj robí?**

Predstavte si, že máte jednu alebo viac PDF faktúr a potrebujete z nich získať všetky podrobnosti o produktoch (ako sú kódy položiek, množstvá, ceny a vypočítaná celková čistá hmotnosť) a dostať ich do jednej prehľadnej tabuľky (CSV súboru), napríklad do Excelu. Tento nástroj tento proces automatizuje za vás!

**Ako to funguje? (Kľúčové Kroky Spracovania):**

1.  **Vstupy:**
    *   PDF faktúry z priečinka `data/`.
    *   Jednotkové hmotnosti produktov zo súboru `data/product_weight.csv` (formát: `kód_produktu;hmotnosť_s_des_čiarkou`).
2.  **Používateľská Voľba Výstupu:** Skript sa opýta, či vytvoriť:
    *   Jeden spoločný CSV súbor pre všetky faktúry.
    *   Samostatné CSV súbory pre každú faktúru.
3.  **Spracovanie Každej Faktúry:**
    *   Každá strana PDF sa skonvertuje na obrázok (uložený do `pdf_images/nazov_faktury/`).
    *   Obrázky strán sa odošlú do Google Gemini API na extrakciu dát (číslo faktúry, kód položky, lokalita, množstvo, jednotková cena, celková cena) vo formáte JSON.
    *   Pre každú položku sa vypočíta **Celková Čistá Hmotnosť** (`množstvo * jednotková hmotnosť`).
4.  **Výstup (v priečinku `data_output/`):**
    *   CSV súbor(y) s extrahovanými a vypočítanými dátami.
    *   Stĺpce: Číslo Faktúry, Číslo Strany, Číslo Riadku, Názov Položky (kód produktu), Lokalita, Množstvo, Jednotková Cena, Celková Cena, Celková Čistá Hmotnosť.
    *   Pri spoločnom CSV súbore sú dáta z rôznych faktúr oddelené.
    *   Prípadné chyby pri spracovaní sú zaznamenané v CSV.

Tieto CSV súbory môžete otvoriť pomocou Excelu alebo akéhokoľvek tabuľkového editora. Skript tiež vypíše do konzoly/terminálu správy o tom, čo práve robí.

## Inštalačná Príručka

Pred spustením skriptu sa uistite, že máte všetko správne nastavené:

1.  **Nainštalovaný Python:**
    *   Potrebujete mať nainštalovaný Python na vašom počítači (odporúčaná verzia 3.7 alebo novšia).
    *   Ak Python nemáte, môžete si ho stiahnuť z [oficiálnej stránky Pythonu](https://www.python.org/downloads/). Počas inštalácie zaškrtnite možnosť \"Add Python to PATH\".

2.  **Získanie Skriptu:**
    *   Stiahnite si súbory projektu (najmä `main.py` a `requirements.txt`) do jedného priečinka na vašom počítači.

3.  **Inštalácia Potrebných Knižníc:**
    *   Otvorte terminál alebo príkazový riadok.
    *   Prejdite do priečinka, kam ste uložili súbory skriptu (napríklad pomocou príkazu `cd cesta_k_priecinku`).
    *   Nainštalujte potrebné knižnice spustením príkazu:
        \`\`\`bash
        pip install -r requirements.txt
        \`\`\`
    *   Tento príkaz automaticky stiahne a nainštaluje všetky knižnice, ktoré skript potrebuje (ako PyMuPDF pre prácu s PDF a knižnicu Google Gemini).

4.  **Nastavenie Google API Kľúča:**
    *   Vytvorte súbor s názvom `.env` **v tom istom priečinku**, kde máte `main.py`.
    *   Otvorte tento `.env` súbor v textovom editore (napr. Poznámkový blok) a vložte do neho váš Google API kľúč v nasledujúcom formáte:
        \`\`\`
        GOOGLE_API_KEY=sem_vlozte_vas_aktualny_api_kluc
        \`\`\`
    *   Nahraďte `sem_vlozte_vas_aktualny_api_kluc` vaším skutočným API kľúčom od Google AI Studio alebo Google Cloud.

5.  **Príprava Súborov:**
    *   V priečinku, kde máte `main.py`, vytvorte nový podpriečinok s názvom `data` (ak ešte neexistuje).
    *   Všetky PDF faktúry, ktoré chcete spracovať, skopírujte alebo presuňte do tohto priečinka `data/`.
    *   **Dôležité:** Do priečinka `data/` tiež umiestnite súbor `product_weight.csv`. Tento súbor musí obsahovať kódy produktov (v prvom stĺpci, ako \"Registrační číslo\") a ich jednotkové hmotnosti (v druhom stĺpci, ako \"JV Váha komplet SK\", s desatinnou čiarkou). Súbor musí byť oddelený bodkočiarkou (;).
        *   Príklad riadku v `product_weight.csv`: `CC-01;9,635`
    *   Skript automaticky vytvorí ďalší podpriečinok s názvom `data_output/`, kam uloží výsledné CSV súbory.

6.  **Spustenie Skriptu:**
    *   V termináli alebo príkazovom riadku (uistite sa, že ste stále v priečinku projektu) spustite skript príkazom:
        \`\`\`bash
        python main.py
        \`\`\`
    *   Skript vás najprv požiada, aby ste si vybrali, či chcete jeden spoločný CSV súbor alebo samostatné súbory pre každú faktúru. Zadajte `1` alebo `2` a stlačte Enter.
    *   Následne začne spracovávať PDF súbory. Priebežne bude vypisovať informácie o tom, čo práve robí.

**Čo potrebujete urobiť? (Stručný prehľad po inštalácii)**

1.  Uistite sa, že súbor `.env` s vaším API kľúčom je správne nastavený v hlavnom priečinku skriptu.
2.  Umiestnite všetky vaše PDF faktúry DO priečinka `data/`.
3.  Uistite sa, že súbor `product_weight.csv` je TAKTIEŽ v priečinku `data/` a má správny formát.
4.  Spustite skript príkazom `python main.py` vo vašom termináli/príkazovom riadku.
5.  Keď sa skript opýta, zadajte `1` pre jeden spoločný CSV súbor, alebo `2` pre samostatné CSV súbory pre každú faktúru.

**Čo získate?**

Výsledné CSV súbory nájdete v novovytvorenom priečinku `data_output/` (v hlavnom priečinku skriptu). Podľa vašej voľby pri spustení skriptu to bude:
*   **Jeden spoločný CSV súbor:** Súbor s názvom `extracted_invoice_data.csv` v priečinku `data_output/`. Bude obsahovať údaje zo všetkých spracovaných PDF faktúr, prehľadne usporiadané a oddelené špeciálnym riadkom pre každú novú faktúru.
*   **Samostatné CSV súbory:** Pre každú spracovanú PDF faktúru sa vytvorí samostatný CSV súbor v priečinku `data_output/` (napr. ak máte faktúru `moja_faktura.pdf`, vytvorí sa `moja_faktura_extracted.csv`).

Tieto CSV súbory môžete otvoriť pomocou Excelu alebo akéhokoľvek tabuľkového editora. Skript tiež vypíše do konzoly/terminálu správy o tom, čo práve robí.

## Technický Opis pre Vývojárov

Skript `main.py` v Pythone vykonáva nasledujúce hlavné kroky:

1.  **Inicializácia:**
    *   Načíta API kľúč z `.env`.
    *   Načíta produktové hmotnosti z `data/product_weight.csv` (`load_product_weights`).
2.  **Spracovanie PDF:**
    *   Iteruje PDF súbory v `data/`.
    *   Konvertuje strany na PNG obrázky (`pdf_to_images`) do `pdf_images/nazov_faktury/`.
3.  **Extrakcia Dát cez AI (Google Gemini):**
    *   Obrázky strán posiela s podrobnou výzvou (prompt) do Gemini API (`analyze_image_with_gemini`).
    *   Očakáva JSON odpoveď s číslom faktúry a detailmi položiek.
4.  **Transformácia Dát a Výpočet Hmotnosti:**
    *   Spracuje JSON odpoveď (`process_gemini_response_to_csv_rows`).
    *   Mapuje polia, vypočíta celkovú čistú hmotnosť (`množstvo * jednotková_hmotnosť`).
    *   Rieši chýbajúce dáta / chyby konverzie.
5.  **Generovanie CSV Výstupu:**
    *   Na základe voľby používateľa zapíše dáta do `data_output/` (jeden spoločný alebo samostatné CSV).
    *   Definované hlavičky zahŕňajú všetky extrahované a vypočítané polia.

**Kľúčové Knižnice:**
*   `PyMuPDF (fitz)`: Konverzia PDF na obrázky.
*   `google-generativeai`: Komunikácia s Gemini API.
*   `python-dotenv`: Správa API kľúča.
*   Štandardné: `os`, `glob`, `csv`, `json`.

**Dôležité Aspekty:**
*   **Prompt Engineering:** Úspech extrakcie závisí od presnosti výzvy pre Gemini API (požaduje JSON).
*   **Spracovanie Chýb:** Skript obsahuje mechanizmy na robustné spracovanie chýb.
*   **Modulárnosť:** Kód je rozdelený do funkcií s jasnými zodpovednosťami.

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
