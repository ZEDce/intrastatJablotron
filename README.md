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
    *   Colné kódy a ich popisy zo súboru `data/col_sadz.csv` (formát: `kod_colnej_sadzby;Popis`).
2.  **Používateľská Voľba Výstupu:** Skript sa opýta, či vytvoriť:
    *   Jeden spoločný CSV súbor pre všetky faktúry.
    *   Samostatné CSV súbory pre každú faktúru.
3.  **Spracovanie Každej Faktúry:**
    *   Každá strana PDF sa skonvertuje na obrázok (uložený do `pdf_images/nazov_faktury/`).
    *   Obrázky strán sa odošlú do Google Gemini API na extrakciu dát (číslo faktúry, kód položky, popis položky, lokalita, množstvo, jednotková cena, celková cena) vo formáte JSON.
    *   Pre každú položku sa vypočíta **Celková Čistá Hmotnosť** (`množstvo * jednotková hmotnosť`).
    *   Pre každú položku sa **pomocou AI priradí colný kód** na základe jej popisu a zoznamu colných kódov z `col_sadz.csv`.
4.  **Výstup (v priečinku `data_output/`):**
    *   CSV súbor(y) s extrahovanými a vypočítanými dátami.
    *   Stĺpce: Číslo Faktúry, Číslo Strany, Číslo Riadku, Názov Položky (kód produktu), Popis položky, Lokalita, Množstvo, Jednotková Cena, Celková Cena, Celková Čistá Hmotnosť, Colný kód, Popis colného kódu.
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
    *   **Dôležité:** Do priečinka `data/` tiež umiestnite súbor `product_weight.csv`. Tento súbor musí obsahovať kódy produktov (v prvom stĺpci, ako "Registrační číslo") a ich jednotkové hmotnosti (v druhom stĺpci, ako "JV Váha komplet SK", s desatinnou čiarkou). Súbor musí byť oddelený bodkočiarkou (;).
        *   Príklad riadku v `product_weight.csv`: `CC-01;9,635`
    *   Do priečinka `data/` tiež umiestnite súbor `col_sadz.csv`. Tento súbor musí obsahovať kódy colných sadzieb (v prvom stĺpci, napr. `85311030`, bez medzier) a ich stručné popisy (v druhom stĺpci). Súbor musí byť oddelený bodkočiarkou (;). Tento súbor je nevyhnutný pre správne priradenie colných kódov k položkám.
        *   Príklad riadku v `col_sadz.csv`: `85311030;Poplachové zabezpečovacie systémy na ochranu budov`
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
4.  Uistite sa, že súbor `col_sadz.csv` je TAKTIEŽ v priečinku `data/` a má správny formát.
5.  Spustite skript príkazom `python main.py` vo vašom termináli/príkazovom riadku.
6.  Keď sa skript opýta, zadajte `1` pre jeden spoločný CSV súbor, alebo `2` pre samostatné CSV súbory pre každú faktúru.

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
    *   Načíta colné kódy z `data/col_sadz.csv` (`load_customs_tariff_codes`).
2.  **Spracovanie PDF:**
    *   Iteruje PDF súbory v `data/`.
    *   Konvertuje strany na PNG obrázky (`pdf_to_images`) do `pdf_images/nazov_faktury/`.
3.  **Extrakcia Dát cez AI (Google Gemini):**
    *   Obrázky strán posiela s podrobnou výzvou (prompt) do Gemini API (`analyze_image_with_gemini` s modelom `gemini-2.0-flash-lite`).
    *   Očakáva JSON odpoveď s číslom faktúry a detailmi položiek (vrátane `description`).
4.  **Priraďovanie Colných Kódov cez AI (Google Gemini):**
    *   Pre každú extrahovanú položku sa na základe jej textového popisu a zoznamu colných kódov (z `col_sadz.csv`) pomocou ďalšieho volania Gemini API (`assign_customs_code_with_ai` s modelom `gemini-2.0-flash-lite`) priradí najvhodnejší 8-miestny colný kód.
5.  **Transformácia Dát a Výpočet Hmotnosti:**
    *   Spracuje JSON odpoveď (`process_gemini_response_to_csv_rows`).
    *   Mapuje polia, vypočíta celkovú čistú hmotnosť (`množstvo * jednotková_hmotnosť`).
    *   Pridá priradený colný kód a jeho popis.
    *   Rieši chýbajúce dáta / chyby konverzie.
6.  **Generovanie CSV Výstupu:**
    *   Na základe voľby používateľa zapíše dáta do `data_output/` (jeden spoločný alebo samostatné CSV).
    *   Definované hlavičky zahŕňajú všetky extrahované, vypočítané a priradené polia (vrátane "Popis položky", "Colný kód", "Popis colného kódu").

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

Projekt využíva model `gemini-2.0-flash-lite`. Náklady spojené s Gemini API závisia od počtu tokenov na vstupe (obrázky + textová výzva) a na výstupe (vygenerované JSON dáta alebo textová odpoveď pre colný kód).

K augustu 2024 je cena za Gemini 1.5 Flash (platená úroveň, pre výzvy do 128k tokenov) približne:
*   **Vstupné tokeny:** 0,075 $ za 1 milión tokenov (cena pre gemini-2.0-flash-lite môže byť iná, toto je pre 1.5 Flash)
*   **Výstupné tokeny:** 0,30 $ za 1 milión tokenov (cena pre gemini-2.0-flash-lite môže byť iná, toto je pre 1.5 Flash)

**Odhadované náklady pre tento extraktor:**

Spracovanie jednej položky na faktúre teraz zahŕňa:
1.  Jedno volanie API na extrakciu dát z obrázka stránky (zdieľané pre všetky položky na stránke).
2.  Jedno volanie API na priradenie colného kódu pre každú jednotlivú položku.

To znamená, že náklady budú o niečo vyššie ako pri pôvodnom skripte, ktorý robil len extrakciu dát. Model `gemini-2.0-flash-lite` je však navrhnutý pre rýchlosť a efektivitu.
*   **Vstup na stránku (obrázok + výzva pre extrakciu):** ~1600 tokenov (hrubý odhad)
*   **Výstup na stránku (JSON dáta):** ~200-500 tokenov (závisí od počtu položiek)
*   **Vstup na pridelenie colného kódu (detaily položky + zoznam kódov + výzva):** ~300-700 tokenov (závisí od dĺžky popisov a počtu colných kódov v `col_sadz.csv`)
*   **Výstup na pridelenie colného kódu (zdôvodnenie + kód):** ~50-150 tokenov

Presné náklady sa budú líšiť. Náklady na pridelenie colného kódu sa pripočítavajú pre každú položku zvlášť.

**Poznámka:**
*   Toto sú odhady. Skutočné náklady sa môžu líšiť.
*   Google ponúka bezplatnú úroveň pre Gemini API, ktorá má limity použitia.
*   Odporúča sa sledovať vaše využitie a fakturáciu v Google Cloud Console.
*   Ceny sa môžu meniť. Vždy si overte aktuálne informácie na oficiálnej stránke cien Google AI pre model `gemini-2.0-flash-lite` alebo ekvivalent, ktorý používate.
