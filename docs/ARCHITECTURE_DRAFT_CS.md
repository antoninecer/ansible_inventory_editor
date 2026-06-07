Zde je kompletní, ucelený architektonický a produktový rozbor tvého projektu založený na všech poskytnutých souborech (inventory_editor.gen.yml, inventory_editor.schema.yml a kompletním README.md).
Tento dokument slouží jako komplexní technický podklad (Blueprint) pro realizaci, kde klademe extrémní důraz na testovatelnost, protože u nástroje, který manipuluje s produkční infrastrukturou, je stabilita kritická.
1. Analýza a pochopení konceptu (Produktový kontrakt)
Cílem je vytvořit GUI manažer pro komplexní Ansible inventáře. Nástroj řeší zásadní problém: Ansible inventáře začínají jako jednoduché soubory, ale rychle přerůstají do nepřehledných adresářových struktur s desítkami souborů a složitými pravidly pro dědičnost proměnných.
Cílové publikum
•	Začátečníci: UI je bezpečně provede založením projektu, tvorbou skupin a hostů, aniž by museli znát přesnou adresářovou strukturu Ansible.
•	Pokročilí operátoři: Získají vizuální přehled o tom, odkud se jaká proměnná vzala, kde dochází k duplicitám a jaké je výsledné chování (precedence).
Základní filozofie nástroje
1.	Preserve User Intent: Editor nikdy nesmí svévolně doplňovat nebo vymýšlet hodnoty, které v kódu nejsou.
2.	Warn, Don't Crash: Pokud import narazí na neznámou strukturu nebo soubor, nesmí selhat, ale musí uživatele transparentně varovat.
3.	Safety First: Každá změna musí být reverzibilní a před zápisem na disk musí proběhnout záloha.
2. Architektonický návrh (Jak to realizovat)
Pro zajištění špičkové testovatelnosti navrhuji striktní oddělení logiky od GUI pomocí Clean / Hexagonal Architecture. Vše uvnitř jádra pracuje výhradně s relativními cestami vůči kořeni projektu.
Vrstva A: Datový model (Domain Model)
Čisté datové entity, které neví nic o tom, jak se ukládá na disk nebo jak vypadá UI.
•	Host: Reprezentuje uzel (např. dohled01).
•	Group: Skupina uzlů (např. dohled, all).
•	VariableSource: Objekt nesoucí informaci o původu – cesta k souboru (např. group_vars/all/main.yml), typ zdroje (např. host_vars, inline).
•	Variable: Klíč, hodnota, datový typ a vazba na VariableSource.
Vrstva B: Analytický a Transformační Engine
Srdce aplikace, které provádí výpočty.
•	Parser/Serializer (Round-Trip): Načítá YAML/INI a převádí je do Datového modelu. Pro YAML je kritické použít knihovnu podporující round-trip (např. ruamel.yaml pro Python, nebo YamlDotNet s patřičným nastavením pro C# podle jazyka cs v konfiguraci), aby zůstaly zachovány komentáře a formátování uživatele.
•	Precedence Evaluator: Simuluje chování Ansible. Seřadí zdroje proměnných podle priorit (od all_vars přes group_vars a host_vars až po extra_vars) a spočítá výslednou efektivní hodnotu.
•	Issue Analyzer: Prochází model a generuje incidenty rozdělené podle závažnosti:
o	A (Critical): Nevalidní syntaxe, neexistující reference uzlu ve skupině.
o	B (Warning): Duplicita stejného klíče ve více souborech na stejné úrovni precedence.
o	C (Recommendation): Proměnná specifická pro aplikaci (např. nginx_port) je umístěna v obecném main.yml namísto tematického nginx.yml.
Vrstva C: Perzistentní vrstva (Storage Gateways)
Stará se o bezpečný zápis na disk.
•	Backup Manager: Před každým zápisem zkopíruje stávající stav adresáře do interní zálohy (např. .inventory-editor/backups/YYYY-MM-DD_HHMMSS/). Alternativně může na pozadí inicializovat Git a provádět automatické revize (autocommit), což zajistí 100% reverzibilitu.
Vrstva D: Uživatelské rozhraní (GUI)
Podle specifikace mode: gui. Mělo by být postaveno na reaktivním principu: jakákoli změna v Datovém modelu okamžitě přepočítá analýzu rizik a překreslí UI.
3. Strategie řízení stavu (Status Workflow)
Ve specifikaci definuješ stavy: todo, draft, approved, implemented, changed, deprecated. Zde je jasné rozdělení, jak s nimi nakládat:
1.	Vývojový cyklus aplikace (Process): Podle pokynu "When a feature changes, update the YAML manifest first..." tyto stavy slouží tobě k řízení implementace samotného editoru.
2.	Metadata projektu (Data): Pokud chceš tyto stavy aplikovat i na entity v inventáři (např. skupina "dohled" je pouze ve stavu draft a nesmí se exportovat do produkce), ukládej tato metadata do dedikovaného souboru .inventory-editor.json v rootu projektu, aby nebyl znečištěn čistý Ansible inventář.
4. Testovací strategie (Klíč k úspěchu)
Jelikož jsou testy klíčové, testovací pyramida bude postavena tak, aby garantovala, že editor uživateli nikdy "nerozbije" jeho stávající infrastrukturu.
A. Unit Testy (Izolované testy enginu)
Všechny testy v této vrstvě budou běžet v paměti bez reálného zápisu na disk.
•	Testy priority proměnných (Precedence):
o	Vstup: Model obsahující group_vars/all/main.yml s port: 80 a host_vars/dohled01/main.yml s port: 8080.
o	Očekávaný výsledek: EffectiveValue pro dohled01 je 8080. Zdroj původu (source_path_trace) ukazuje na host_vars soubor.
•	Testy detekce konfliktů (Conflict Detection):
o	Vstup: Stejná proměnná definovaná ve dvou různých souborech na stejné úrovni dědičnosti.
o	Očekávaný výsledek: Vygenerování Incidentu se závažností B (Warning).
B. Integrační Testy (Round-Trip & File System)
Zde se testuje reálná práce se soubory. Budeme využívat dočasné složky v RAM (In-Memory File System / Virtual File System).
•	The Round-Trip Guarantee Test:
o	Načti komplexní, ručně napsaný Ansible inventář s komentáři a prázdnými řádky.
o	Převeď ho do interního modelu.
o	Okamžitě ho ulož zpět na disk do jiného souboru.
o	Očekávaný výsledek: MD5/SHA-256 hash původního a nového souboru musí být identický. Editor nesmí změnit ani čárku (ověření pravidla never invent values / preserve intent).
•	The Backup Safe Test:
o	Simuluj proces uložení změny.
o	Uprostřed zápisu vyvolej umělou chybu (např. simulaci plného disku).
o	Očekávaný výsledek: Původní data zůstala nedotčena, nebo byla plně obnovena ze zálohy vytvořené těsně před operací.
C. UI / E2E Testy (Scénáře pro začátečníky)
Automatizované testy simulující reálné klikání uživatele v GUI podle sekce User guidance.
•	Scénář "Nový projekt na zelené louce":
1.	Spustit průvodce vytvořením projektu.
2.	Kliknout na "Přidat skupinu" -> Zadat "dohled".
3.	Kliknout na "Přidat hosta" -> Zadat "dohled01".
4.	Přidat proměnnou a zvolit uložení do tematického souboru nginx.yml.
5.	Očekávaný výsledek: Na disku vznikne přesná adresářová struktura odpovídající tvému příkladu z README.
5. Kontrola a Akceptační kritéria (Definition of Done)
Projekt první fáze (Current Intent) považuj za dokončený a bezpečný k nasazení pouze tehdy, pokud splní tento kontrolní seznam:
Oblast	Kontrolní bod (Kritérium úspěchu)	Ověřeno přes
Data	Program umí importovat složku s group_vars i host_vars bez pádu.	Integrační testy
Data	Neznámé soubory v adresáři nezpůsobí pád, ale vyvolají varování v UI.	Integrační testy
Bezpečnost	Před každou modifikací disku vznikne prokazatelně funkční záloha.	Unit/Integrační testy
Analýza	UI správně zobrazuje barvou rozlišené incidenty úrovní A, B, C.	E2E / Manuální QA
Kvalita	Pokrytí kódu (Code Coverage) analytického jádra a parseru je > 90 %.	CI/CD Pipeline
Tento podklad ti dává jasný, bezpečný a otestovatelný rámec. Pokud se budeš striktně držet oddělení analýzy od samotného souborového systému, vytvoříš robustní nástroj, který začátečníky ochrání a pokročilým ušetří hodiny hledání chyb v prioritách proměnných.

