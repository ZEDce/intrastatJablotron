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