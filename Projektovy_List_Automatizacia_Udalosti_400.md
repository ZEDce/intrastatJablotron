# Zmenový list (Projektové riadenie)

**Označenie:** [Vyplniť podľa internej systematiky]
JABLOTRON SECURITY a.s., K dubu 2328/2a, Praha 4

**Typ zmenového listu:** projektový

---

**Číslo projektu:** [Vyplniť]

**Názov projektu/Modul:** Automatizácia spracovania faktúr a generovania Intrastat reportov

**Navrhovateľ:**
*   **Meno/úsek:** [Vyplniť Meno/Úsek zodpovedný za návrh]
*   **Dátum:** [Vyplniť aktuálny dátum, napr. DD.MM.RRRR]

**Príjemca:**
*   **Meno/úsek:** [Vyplniť Meno/Úsek príjemcu, napr. IT oddelenie, Ekonomické oddelenie]
*   **Dátum:** [Vyplniť]

**Schválil:**
*   **Meno/úsek:** [Vyplniť]
*   **Dátum:** [Vyplniť]

**Člen predstavenstva:**
*   **Meno:** [Vyplniť, ak relevantné]
*   **Dátum:** [Vyplniť, ak relevantné]

**Súlad s GDPR:**
*   **Meno/úsek:** [Vyplniť posúdenie GDPR, ak relevantné]
*   **Dátum:** [Vyplniť]

**Dátum predloženia:** [Vyplniť]

**Prílohy:** [Napr. Špecifikácia požiadaviek, Architektúra systému - ak existuje]

---

## Popis zmeny/zadania:

Vývoj a implementácia softvérového nástroja (série Python skriptov) na automatizáciu procesu spracovania PDF faktúr pre účely Intrastat hlásení. Nástroj bude zahŕňať extrakciu dát z PDF dokumentov, priradenie colných kódov s využitím umelej inteligencie (AI), výpočet a úpravu čistých a hrubých hmotností položiek a generovanie finálnych CSV súborov pripravených na import do colného systému alebo ďalšie spracovanie.

---

## Cieľ zmeny:

*   Výrazne znížiť manuálnu prácu a časovú náročnosť spojenú so spracovaním faktúr pre Intrastat.
*   Zvýšiť presnosť dát v Intrastat hláseniach elimináciou chýb spôsobených manuálnym prepisom a interpretáciou.
*   Zrýchliť celkový proces prípravy a odosielania Intrastat hlásení.
*   Automatizovať extrakciu relevantných údajov z PDF faktúr, vrátane:
    *   Čísla faktúry
    *   Kódov položiek, názvov a popisov
    *   Množstiev a cien
    *   Krajiny pôvodu (s možnosťou manuálneho doplnenia používateľom)
*   Automatizovať priradenie colných kódov k jednotlivým položkám faktúry s využitím AI (Google Gemini API) a preddefinovanej databázy colných kódov, vrátane zohľadnenia špecifických pravidiel pre určité kategórie produktov (napr. batérie, komponenty alarmových systémov).
*   Automatizovať výpočet predbežných čistých hmotností na základe internej databázy hmotností produktov.
*   Umožniť používateľovi zadať celkovú čistú a hrubú hmotnosť faktúry a následne automaticky a proporcionálne distribuovať tieto hmotnosti na jednotlivé položky faktúry s využitím AI.
*   Generovať výstupné CSV súbory v štruktúrovanom formáte, kompatibilnom pre ďalšie spracovanie alebo import do colných systémov.
*   Zabezpečiť systematickú archiváciu spracovaných PDF faktúr pre účely auditu a kontroly.
*   Poskytnúť jednoduché používateľské rozhranie (cez príkazový riadok) pre spustenie jednotlivých fáz spracovania a generovania reportov.

---

## Súčasný proces:

*   Manuálne otváranie a vizuálna kontrola každej prijatej PDF faktúry.
*   Ručné vyhľadávanie a prepisovanie všetkých relevantných údajov (kódy položiek, popisy, množstvá, jednotkové a celkové ceny, krajina pôvodu atď.) z PDF faktúr do externých tabuľkových editorov (napr. MS Excel) alebo priamo do systému pre Intrastat.
*   Manuálne vyhľadávanie a priraďovanie správnych colných kódov ku každej položke faktúry na základe jej popisu a povahy, s využitím externých číselníkov alebo interných znalostí.
*   Manuálny výpočet čistej hmotnosti pre každú položku, často na základe samostatne vedenej evidencie hmotností produktov.
*   Komplikovaný a časovo náročný manuálny výpočet a distribúcia celkovej hrubej a čistej hmotnosti zásielky (faktúry) na jednotlivé položky, aby súhlasili celkové súčty.
*   Vysoká miera repetitívnej práce, náchylnosť na ľudské chyby (preklepy, nesprávne priradenia, chybné výpočty).
*   Nedostatočná flexibilita pri spracovaní väčšieho objemu faktúr.
*   Časovo náročná príprava finálneho Intrastat hlásenia.

---

## Navrhované Riešenie / Popis Systému:

**Názov riešenia:** Systém pre automatizáciu spracovania faktúr a generovania Intrastat reportov

**Použité technológie a nástroje:**
*   **Programovací jazyk:** Python 3.x
*   **Knižnice pre prácu s PDF:** PyMuPDF (fitz)
*   **Umelá inteligencia:** Google Gemini API (modely Flash) pre extrakciu dát z obrázkov, priradenie colných kódov a úpravu hmotností.
*   **Spracovanie dát:** Štandardné Python knižnice (csv, json, re, os, shutil).
*   **Správa závislostí:** `requirements.txt`
*   **Konfigurácia:** Súbor `.env` pre API kľúče.
*   **Dátové súbory (vstup):**
    *   `data/product_weight.csv`: Databáza hmotností produktov.
    *   `data/col_sadz.csv`: Číselník colných sadzobníkov.

**Hlavné komponenty a funkcionality systému:**

*   **Hlavný skript (`main.py`):**
    *   Orchestruje celý proces spracovania.
    *   Implementuje používateľské menu pre interakciu (spracovanie PDF, generovanie reportu, zobrazenie colných kódov).
    *   Načítava konfiguračné súbory a vstupné dáta (hmotnosti, colné kódy).
    *   Zabezpečuje spracovanie všetkých PDF súborov umiestnených v adresári `faktury_na_spracovanie/`.
    *   Pre každý PDF súbor:
        1.  Konvertuje stránky PDF na obrázky (PNG) pre analýzu pomocou AI.
        2.  Komunikuje s Google Gemini API na extrakciu štruktúrovaných dát z obrázkov faktúr (číslo faktúry, detaily položiek: kód, názov, popis, množstvo, ceny, mena, a pokus o extrakciu krajiny pôvodu).
        3.  Spracúva a validuje odpoveď od Gemini. V prípade, že AI neurčí krajinu pôvodu pre produktovú položku, vyzve používateľa na jej manuálne zadanie (2-písmenový kód).
        4.  Vypočítava predbežné čisté hmotnosti položiek na základe údajov z `product_weight.csv`.
        5.  Priraďuje colné kódy jednotlivým položkám s využitím ďalšieho volania Gemini API, ktorému poskytne detaily položky a zoznam všetkých dostupných colných kódov z `col_sadz.csv`. Implementuje špecifické logické pravidlá pre priradenie (napr. priorita pre batérie, komponenty alarmov).
        6.  Vyzve používateľa na zadanie celkovej cieľovej čistej a hrubej hmotnosti pre celú faktúru.
        7.  Využíva Gemini API na inteligentné a proporcionálne rozdelenie rozdielu medzi predbežnými a cieľovými hmotnosťami (čistými aj hrubými) na jednotlivé položky faktúry, pričom zabezpečuje dodržanie celkových súčtov a logických väzieb (hrubá >= čistá).
        8.  Generuje finálny CSV súbor pre spracovanú faktúru (napr. `processed_invoice_data_IDFAKTURY.csv`) do adresára `data_output/`. Súbor obsahuje všetky extrahované a vypočítané údaje.
        9.  Vytvára `.meta` súbor k CSV, obsahujúci názov pôvodného PDF súboru.
        10. Presúva spracovaný PDF súbor do archívneho adresára `spracovane_faktury/`.
        11. Čistí dočasné obrázkové súbory.

*   **Modul pre reporty (`report.py`):**
    *   Poskytuje funkcionalitu pre generovanie súhrnných Intrastat reportov.
    *   Umožňuje používateľovi vybrať, z ktorých už spracovaných CSV súborov (z `data_output/`) sa má súhrnný report vytvoriť (všetky dostupné alebo špecifický výber).
    *   Agreguje dáta z vybraných CSV súborov do jedného súhrnného CSV reportu (napr. `Final_Report_RRRR-MM-DD_HHMMSS.csv`) ukladaného tiež do `data_output/`.
    *   Poskytuje pomocnú funkciu na zobrazenie popisov colných kódov.

**Postup implementácie a nasadenia (orientačný):**
1.  Príprava prostredia (inštalácia Pythonu, potrebných knižníc).
2.  Konfigurácia API kľúča pre Google Gemini v `.env` súbore.
3.  Príprava vstupných dátových súborov (`product_weight.csv`, `col_sadz.csv`).
4.  Testovanie jednotlivých modulov a celého workflow.
5.  Školenie používateľov.
6.  Nasadenie do prevádzky.

**Predpokladané prínosy:**
*   Detailne popísané v sekcii "Cieľ zmeny". Hlavnými prínosmi sú úspora času, zníženie chybovosti, zvýšenie efektivity a lepšia kontrolovateľnosť procesu prípravy Intrastat hlásení.

--- 