# Extrakcia Dát z PDF Faktúr

**Cieľ Projektu:** Extrahovať štruktúrované údaje o položkách z viacerých PDF faktúr do CSV súborov, vrátane vypočítanej celkovej čistej hmotnosti pre každú položku, pomocou analýzy obrázkov s využitím AI cez Google Gemini API a lokálneho súboru s hmotnosťami produktov.

## Obsah

- [Používateľská Príručka](#používateľská-príručka)
- [Inštalačná Príručka](#inštalačná-príručka)
- [Technický Opis pre Vývojárov](#technický-opis-pre-vývojárov)
- [Náklady na Používanie API (Gemini 2.0 Flash Lite)](#náklady-na-používanie-api-gemini-20-flash-lite)

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
    *   **Používateľský Vstup pre Hmotnosti:** Pre každú spracovávanú faktúru sa skript najprv opýta na cieľovú celkovú čistú hmotnosť a cieľovú celkovú hrubú hmotnosť pre danú faktúru. Tieto hodnoty poskytnuté používateľom sa použijú na finálnu úpravu hmotností položiek.
    *   Každá strana PDF sa skonvertuje na obrázok (uložený do `pdf_images/nazov_faktury/`).
    *   Obrázky strán sa odošlú do Google Gemini API na extrakciu dát (číslo faktúry, kód položky, popis položky, lokalita, množstvo, jednotková cena, celková cena) vo formáte JSON.
    *   Pre každú položku sa vypočíta **Predbežná Čistá Hmotnosť** (`množstvo * jednotková hmotnosť z product_weight.csv`).
    *   Pre každú položku sa **pomocou AI priradí colný kód** na základe jej popisu a zoznamu colných kódov z `col_sadz.csv`.
    *   **Úprava Hmotností Pomocou AI a Programatická Korekcia:** Na základe používateľom zadaných cieľových celkových hmotností pre faktúru a predbežne vypočítaných čistých hmotností položiek sa uskutoční ďalšie volanie AI. Táto AI má za úlohu navrhnúť finálnu čistú a hrubú hmotnosť pre každú položku tak, aby ich súčty presne zodpovedali cieľovým hodnotám. Výstup AI sa následne programaticky skontroluje a doladí, aby sa zabezpečila presná zhoda súčtov.
4.  **Výstup (v priečinku `data_output/`):**
    *   CSV súbor(y) s extrahovanými a vypočítanými dátami z `main.py`.
    *   Stĺpce: Číslo Faktúry, Číslo Strany, Číslo Riadku, Názov Položky (kód produktu), Popis položky (description), Lokalita, Množstvo, Jednotková Cena, Celková Cena, **Predbežná Čistá Hmotnosť**, **Celková Čistá Hmotnosť (upravená)**, **Celková Hrubá Hmotnosť (upravená)**, Colný kód, Popis colného kódu.
    *   Pri spoločnom CSV súbore sú dáta z rôznych faktúr oddelené.
    *   Prípadné chyby pri spracovaní sú zaznamenané v CSV.
5.  **Generovanie Súhrnného Reportu (pomocou `report.py`):**
    *   Po dokončení `main.py` môžete spustiť `python report.py`.
    *   Skript `report.py` načíta jeden z CSV súborov vygenerovaný `main.py` (z priečinka `data_output/`), ktorý si používateľ vyberie.
    *   Spracuje dáta:
        *   Zoskupí položky podľa `Colnej sadzby` (predtým `Colný kód`) a `Krajiny Pôvodu`.
        *   Vypočíta súčty pre hrubú hmotnosť, čistú hmotnosť, počet kusov a celkovú cenu.
        *   Položky "Sleva zákazníkovi" (zľava) a "Manipulační poplatek" (manipulačný poplatok), identifikované podľa stĺpca `description` z CSV súboru z `main.py`:
            *   Ich množstvo (`Quantity`) sa nepočíta do celkového súčtu kusov.
            *   Cena ("Celková Cena") manipulačného poplatku sa nepočíta do celkového súčtu cien. Cena zľavy *je* zahrnutá.
            *   Zľavy ("Sleva zákazníkovi") sa v reporte zobrazia pod colnou sadzbou "Zľava" a krajinou pôvodu "Zľava".
        *   Odstráni riadky, kde je colná sadzba "NEURCENE" a všetky súčtové hodnoty (hmotnosti, kusy, cena) sú nulové (typicky to platí pre manipulačné poplatky po ich vynulovaní).
        *   Pridá celkový súčtový riadok "Spolu".
    *   **Výstup reportu (v priečinku `dovozy/`):**
        *   Jeden CSV súbor (názov zadáva používateľ, predvolený je napr. `summary_report_processed_invoice_data_Fa_XXXX.csv`).
        *   Stĺpce: `Colná sadzba`, `Krajina Pôvodu`, `Súčet Hrubá Hmotnosť`, `Súčet Čistá Hmotnosť`, `Súčet Počet Kusov`, `Súčet Celková Cena`. Stĺpec `Popis Colného Kódu` bol odstránený.

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
    *   Následne, **pre každú PDF faktúru**, vás skript požiada zadať cieľovú celkovú čistú hmotnosť a cieľovú celkovú hrubú hmotnosť pre danú faktúru. Zadajte požadované hodnoty a potvrďte Enterom.
    *   Potom začne spracovávať PDF súbory. Priebežne bude vypisovať informácie o tom, čo práve robí.

**Čo potrebujete urobiť? (Stručný prehľad po inštalácii)**

1.  Uistite sa, že súbor `.env` s vaším API kľúčom je správne nastavený v hlavnom priečinku skriptu.
2.  Umiestnite všetky vaše PDF faktúry DO priečinka `data/`.
3.  Uistite sa, že súbor `product_weight.csv` je TAKTIEŽ v priečinku `data/` a má správny formát.
4.  Uistite sa, že súbor `col_sadz.csv` je TAKTIEŽ v priečinku `data/` a má správny formát.
5.  Spustite skript príkazom `python main.py` vo vašom termináli/príkazovom riadku.
6.  Keď sa skript opýta, zadajte `1` pre jeden spoločný CSV súbor, alebo `2` pre samostatné CSV súbory pre každú faktúru.
7.  Pre každú faktúru zadajte požadovanú celkovú čistú a hrubú hmotnosť, keď vás skript vyzve.
8.  Po dokončení `main.py` môžete spustiť `python report.py` pre generovanie súhrnného reportu. Vyberiete vstupný CSV súbor z `data_output/` a zadáte názov výstupného reportu, ktorý sa uloží do `dovozy/`.

**Čo získate?**

- Výsledné CSV súbory **po spracovaní `main.py`** nájdete v novovytvorenom priečinku `data_output/` (v hlavnom priečinku skriptu). Podľa vašej voľby pri spustení skriptu to bude:
    *   **Jeden spoločný CSV súbor:** Súbor s názvom `extracted_invoice_data.csv` v priečinku `data_output/`. Bude obsahovať údaje zo všetkých spracovaných PDF faktúr, prehľadne usporiadané a oddelené špeciálnym riadkom pre každú novú faktúru.
    *   **Samostatné CSV súbory:** Pre každú spracovanú PDF faktúru sa vytvorí samostatný CSV súbor v priečinku `data_output/` (napr. ak máte faktúru `moja_faktura.pdf`, vytvorí sa `processed_invoice_data_moja_faktura.csv`).
- Výsledný **súhrnný report po spracovaní `report.py`** nájdete v priečinku `dovozy/`. Bude to jeden CSV súbor (napr. `summary_report_processed_invoice_data_Fa_XXXX.csv`) obsahujúci agregované dáta.

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
    *   Očakáva JSON odpoveď s číslom faktúry a detailmi položiek (vrátane `description`, ktoré sa neskôr použije v `report.py` na identifikáciu zliav a poplatkov).
    *   **Dôležité pre extrakciu krajiny pôvodu:** Výzva pre Gemini bola špeciálne upravená tak, aby explicitne žiadala extrakciu poľa `"location"` ako dvojpísmenového kódu krajiny pôvodu (napr. GB, CZ, CN) alebo fráz typu "Made in X" / "Origin: Y", ktoré sa často nachádzajú pri kóde položky alebo v jej popise. Ak krajina nie je nájdená, Gemini má vrátiť `null`.
4.  **Priraďovanie Colných Kódov cez AI (Google Gemini):**
    *   Funkcia `assign_customs_code_with_ai` (s modelom `gemini-2.0-flash-lite`):
        *   **Špecifické Priradenia:** Obsahuje logiku na priame priradenie colných kódov pre konkrétne "Item Name" (napr. "CZ-1263.1", "JA-196J"), čím sa obchádza AI pre tieto položky.
        *   **AI Priradenie:** Pre ostatné položky sa na základe ich textového popisu a zoznamu colných kódov (z `col_sadz.csv`) pomocou Gemini API priradí najvhodnejší 8-miestny colný kód.
5.  **Transformácia Dát a Výpočet Predbežnej Hmotnosti:**
    *   Spracuje JSON odpoveď (`process_gemini_response_to_csv_rows`).
    *   Mapuje polia, vypočíta predbežnú celkovú čistú hmotnosť (`množstvo * jednotková_hmotnosť`) a uloží ju ako "Preliminary Net Weight".
    *   Pridá priradený colný kód a jeho popis.
    *   Rieši chýbajúce dáta / chyby konverzie.
6.  **Úprava Hmotností Položiek cez AI a Programatická Korekcia:**
    *   Používateľ zadá cieľovú celkovú čistú a hrubú hmotnosť pre aktuálnu faktúru.
    *   Funkcia `adjust_item_weights_to_target_totals_with_ai` (s modelom `gemini-2.0-flash-lite`) je zavolaná. AI dostane zoznam položiek (s ich predbežnými čistými hmotnosťami) a cieľové sumy.
    *   AI navrhne finálne čisté a hrubé hmotnosti pre každú položku s cieľom dodržať sumy a zabezpečiť logickú distribúciu (vrátane "nerovnomernej" distribúcie hmotnosti obalov).
    *   Výstup AI sa následne programaticky skontroluje a upraví, aby sa zabezpečilo, že súčty finálnych čistých a hrubých hmotností presne zodpovedajú používateľom zadaným cieľom. Táto korekcia distribuuje prípadné malé rozdiely proporcionálne.
7.  **Generovanie CSV Výstupu:**
    *   Na základe voľby používateľa zapíše dáta do `data_output/` (jeden spoločný alebo samostatné CSV).
    *   Definované hlavičky zahŕňajú všetky extrahované, vypočítané a priradené polia (vrátane "Preliminary Net Weight", "Total Net Weight" (upravená), "Total Gross Weight" (upravená), "Popis položky", "Colný kód", "Popis colného kódu").
8.  **Generovanie Súhrnného Reportu (`report.py`):**
    *   Načíta CSV súbor vygenerovaný `main.py` (z `data_output/`).
    *   Vykoná zoskupenie dát podľa `Colnej sadzby` (predtým `Colný kód`) a `Krajiny Pôvodu`.
    *   Agreguje hmotnosti, počet kusov a ceny.
    *   **Špeciálne spracovanie zliav a poplatkov:** Identifikuje položky ako "Sleva zákazníkovi" a "Manipulační poplatek" na základe stĺpca `description`. Pre tieto položky upravuje započítavanie množstva a ceny do súhrnov. Zľavy sú reportované pod špecifickou colnou sadzbou "Zľava".
    *   Odfiltruje riadky s colnou sadzbou "NEURCENE", ak sú všetky ich súčtové hodnoty nulové.
    *   Uloží finálny report do priečinka `dovozy/`. Stĺpec `Popis Colného Kódu` sa v tomto reporte nenachádza a `Colný kód` je premenovaný na `Colná sadzba`.

**Kľúčové Knižnice:**
*   `PyMuPDF (fitz)`: Konverzia PDF na obrázky.
*   `google-generativeai`: Komunikácia s Gemini API.
*   `python-dotenv`: Správa API kľúča.
*   Štandardné: `os`, `glob`, `csv`, `json`.

**Dôležité Aspekty:**
*   **Prompt Engineering:** Úspech extrakcie a úpravy hmotností závisí od presnosti výziev pre Gemini API.
*   **Spracovanie Chýb:** Skript obsahuje mechanizmy na robustné spracovanie chýb.
*   **Programatická Korekcia:** Na zabezpečenie presnosti súčtov hmotností sa po návrhu AI vykonáva finálna programatická korekcia.
*   **Modulárnosť:** Kód je rozdelený do funkcií s jasnými zodpovednosťami.

## Náklady na Používanie API (Gemini 2.0 Flash Lite)

Projekt využíva model `gemini-2.0-flash-lite`. Náklady spojené s Gemini API závisia od počtu tokenov na vstupe (obrázky + textová výzva) a na výstupe (vygenerované JSON dáta alebo textová odpoveď pre colný kód/úpravu hmotností).

K augustu 2024 je cena za model `gemini-2.0-flash-lite` (alebo jeho ekvivalent, ceny sa môžu líšiť, overte si aktuálne cenníky Google AI):
*   Ceny sú typicky udávané za 1 milión tokenov pre vstup a odlišne pre výstup.

**Odhadované náklady pre tento extraktor:**

Spracovanie jednej faktúry teraz zahŕňa:
1.  Jedno volanie API na extrakciu dát z obrázka každej stránky faktúry (zdieľané pre všetky položky na stránke).
2.  Jedno volanie API na priradenie colného kódu pre každú jednotlivú položku.
3.  Jedno volanie API pre celú faktúru na úpravu čistých a hrubých hmotností všetkých jej položiek naraz.

To znamená, že náklady budú o niečo vyššie ako pri pôvodnom skripte. Model `gemini-2.0-flash-lite` je však navrhnutý pre rýchlosť a efektivitu.
*   **Vstup na stránku (obrázok + výzva pre extrakciu):** ~1600 tokenov (hrubý odhad)
*   **Výstup na stránku (JSON dáta):** ~200-500 tokenov (závisí od počtu položiek)
*   **Vstup na pridelenie colného kódu (detaily položky + zoznam kódov + výzva):** ~300-700 tokenov (závisí od dĺžky popisov a počtu colných kódov v `col_sadz.csv`)
*   **Výstup na pridelenie colného kódu (zdôvodnenie + kód):** ~50-150 tokenov
*   **Vstup na úpravu hmotností (zoznam položiek faktúry + detaily + výzva):** ~500-1500+ tokenov (veľmi závisí od počtu položiek na faktúre a dĺžky ich popisov)
*   **Výstup na úpravu hmotností (JSON so všetkými upravenými hmotnosťami položiek):** ~100-400+ tokenov (závisí od počtu položiek)

Presné náklady sa budú líšiť.

**Poznámka:**
*   Toto sú odhady. Skutočné náklady sa môžu líšiť.
*   Google ponúka bezplatnú úroveň pre Gemini API, ktorá má limity použitia.
*   Odporúča sa sledovať vaše využitie a fakturáciu v Google Cloud Console.
*   Ceny sa môžu meniť. Vždy si overte aktuálne informácie na oficiálnej stránke cien Google AI pre model `gemini-2.0-flash-lite` alebo ekvivalent, ktorý používate.
