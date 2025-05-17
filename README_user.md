# Extrakcia Dát z PDF Faktúr - Používateľská Príručka

**Čo tento nástroj robí?**

Predstavte si, že máte jednu alebo viac PDF faktúr a potrebujete z nich získať všetky podrobnosti o produktoch (ako sú kódy položiek, množstvá, ceny a vypočítaná celková čistá hmotnosť) a dostať ich do jednej prehľadnej tabuľky (CSV súboru), napríklad do Excelu. Tento nástroj tento proces automatizuje za vás!

**Ako to funguje?**

1.  **Načíta Vaše PDF Faktúry:** Nástroj automaticky nájde všetky PDF faktúry, ktoré umiestnite do priečinka `data/`.
2.  **Načíta Hmotnosti Produktov:** Skript načíta súbor `data/product_weight.csv`, ktorý musí obsahovať kódy produktov a ich jednotkové hmotnosti. Tieto hmotnosti použije na výpočet celkovej čistej hmotnosti pre každú položku na faktúre.
3.  **Opýta sa Vás na Formát Výstupu:** Pred spracovaním sa skript opýta na preferovaný formát CSV výstupu (jeden spoločný súbor alebo samostatné súbory).
4.  **Prechádza Každú Faktúru Jednotlivo:** Pre každú nájdenú PDF faktúru urobí nasledovné:
    *   **Vytvorí "Snímky":** Nástroj sa "pozrie" na každú stránku PDF faktúry, takmer akoby si ju odfotil. Tieto snímky ukladá do samostatného podpriečinka pre každú faktúru (napr. `pdf_images/nazov_faktury/strana_1.png`), aby sa nepomiešali.
    *   **Odošle AI "Asistentovi" (Google Gemini):** Tieto "obrázky" stránok sa odošlú inteligentnému AI asistentovi. Tomuto asistentovi sme dali veľmi presné pokyny, aby našiel:
        *   Hlavné číslo faktúry.
        *   Pre každú jednu položku uvedenú na faktúre:
            *   **Názov Položky** (čo je zvyčajne krátky kód ako "CC-01" alebo "JA-103K-7AH").
            *   Odkiaľ položka pochádza (**Lokalita**).
            *   Koľko kusov ich je (**Množstvo**).
            *   Cenu za jeden kus (**Jednotková Cena**).
            *   Celkovú cenu za daný riadok (**Celková Cena**).
        *   AI je požiadaná, aby všetky tieto informácie prehľadne usporiadala v digitálnom formáte (nazývanom JSON).
    *   **Spracuje Informácie a Vypočíta Hmotnosť:** Nástroj prevezme usporiadané informácie od AI. Následne pre každú položku:
        *   Vyhľadá jednotkovú hmotnosť produktu v načítanom súbore `product_weight.csv` podľa kódu položky.
        *   Vynásobí zistené množstvo (z faktúry) touto jednotkovou hmotnosťou, čím získa **Celkovú Čistú Hmotnosť** položky.
5.  **Vytvorí Tabuľkové Súbory (CSV súbory) Podľa Vašej Voľby:**
    *   **Ak ste si vybrali jeden spoločný súbor:**
        *   Po spracovaní všetkých PDF faktúr spojí všetky získané údaje do jedného CSV súboru s názvom `extracted_invoice_data.csv`.
        *   Medzi údajmi z rôznych faktúr vloží **oddeľovací riadok** (napr. "--- NOVÁ FAKTÚRA: nazov_faktury.pdf ---"), aby ste jasne videli, kde končia údaje jednej faktúry a začínajú údaje ďalšej.
    *   **Ak ste si vybrali samostatné súbory:**
        *   Pre každú spracovanú PDF faktúru vytvorí samostatný CSV súbor (napr. `nazov_faktury_extracted.csv`). Oddeľovacie riadky sa v tomto prípade nepoužívajú.
    *   Pre každú položku na faktúre pridá "Číslo Riadku" (začína od 1 pre každú novú faktúru), aby ste vedeli poradie položiek v rámci danej faktúry.
    *   Všetky podrobnosti usporiada do stĺpcov. Stĺpce budú nasledovné:
        1.  Číslo Faktúry
        2.  Číslo Strany (z PDF, pre danú faktúru)
        3.  Číslo Riadku (položky na danej faktúre)
        4.  Názov Položky (kód produktu)
        5.  Lokalita
        6.  Množstvo
        7.  Jednotková Cena
        8.  Celková Cena
        9.  Celková Čistá Hmotnosť (vypočítaná ako Množstvo * Jednotková hmotnosť z `product_weight.csv`)
    *   Ak z nejakého dôvodu nemôže získať dáta z niektorej faktúry alebo strany, alebo ak nenájde kód produktu v súbore s hmotnosťami, stále sa pokúsi pokračovať a v CSV súbore (alebo súboroch) v priečinku `data_output/` uvedie chybovú alebo informačnú hlášku pre danú časť.

## Inštalačná Príručka

Pred spustením skriptu sa uistite, že máte všetko správne nastavené:

1.  **Nainštalovaný Python:**
    *   Potrebujete mať nainštalovaný Python na vašom počítači (odporúčaná verzia 3.7 alebo novšia).
    *   Ak Python nemáte, môžete si ho stiahnuť z [oficiálnej stránky Pythonu](https://www.python.org/downloads/). Počas inštalácie zaškrtnite možnosť "Add Python to PATH".

2.  **Získanie Skriptu:**
    *   Stiahnite si súbory projektu (najmä `main.py` a `requirements.txt`) do jedného priečinka na vašom počítači.

3.  **Inštalácia Potrebných Knižníc:**
    *   Otvorte terminál alebo príkazový riadok.
    *   Prejdite do priečinka, kam ste uložili súbory skriptu (napríklad pomocou príkazu `cd cesta_k_priecinku`).
    *   Nainštalujte potrebné knižnice spustením príkazu:
        ```bash
        pip install -r requirements.txt
        ```
    *   Tento príkaz automaticky stiahne a nainštaluje všetky knižnice, ktoré skript potrebuje (ako PyMuPDF pre prácu s PDF a knižnicu Google Gemini).

4.  **Nastavenie Google API Kľúča:**
    *   Vytvorte súbor s názvom `.env` **v tom istom priečinku**, kde máte `main.py`.
    *   Otvorte tento `.env` súbor v textovom editore (napr. Poznámkový blok) a vložte do neho váš Google API kľúč v nasledujúcom formáte:
        ```
        GOOGLE_API_KEY=sem_vlozte_vas_aktualny_api_kluc
        ```
    *   Nahraďte `sem_vlozte_vas_aktualny_api_kluc` vaším skutočným API kľúčom od Google AI Studio alebo Google Cloud.

5.  **Príprava Súborov:**
    *   V priečinku, kde máte `main.py`, vytvorte nový podpriečinok s názvom `data` (ak ešte neexistuje).
    *   Všetky PDF faktúry, ktoré chcete spracovať, skopírujte alebo presuňte do tohto priečinka `data/`.
    *   **Dôležité:** Do priečinka `data/` tiež umiestnite súbor `product_weight.csv`. Tento súbor musí obsahovať kódy produktov (v prvom stĺpci, ako "Registrační číslo") a ich jednotkové hmotnosti (v druhom stĺpci, ako "JV Váha komplet SK", s desatinnou čiarkou). Súbor musí byť oddelený bodkočiarkou (;).
        *   Príklad riadku v `product_weight.csv`: `CC-01;9,635`
    *   Skript automaticky vytvorí ďalší podpriečinok s názvom `data_output/`, kam uloží výsledné CSV súbory.

6.  **Spustenie Skriptu:**
    *   V termináli alebo príkazovom riadku (uistite sa, že ste stále v priečinku projektu) spustite skript príkazom:
        ```bash
        python main.py
        ```
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