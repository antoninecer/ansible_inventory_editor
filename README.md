# AIS - Ansible Inventory Studio

**AIS - Ansible Inventory Studio** is a desktop tool for working with Ansible inventories, `group_vars`, `host_vars`, Ansible Vault files and effective host configuration.

The goal is not to replace Ansible or Git.

The goal is to make an existing Ansible inventory easier to understand, safer to maintain and more useful as a source of truth for infrastructure automation.

---

## Why AIS exists

In real infrastructure environments, an Ansible inventory is often much more than a list of hosts.

It can contain:

- multiple groups and nested groups
- hosts that belong to more than one group
- `group_vars/all`
- group-specific variables
- host-specific variables
- multiple variable files per host or group
- Ansible Vault files
- overridden values
- historical structure that is hard to understand at first sight

At some point the operational question becomes:

> Why does this host get this value?

AIS is built to help answer exactly that.

It helps show where variables come from, which source wins, which hosts are affected by a group context and what the final effective inventory view looks like.

---

## Current features

AIS currently provides:

- visual inventory tree for groups and hosts
- support for YAML inventory projects
- support for directory-based `group_vars` and `host_vars`
- support for `group_vars/all`
- support for host-specific directories such as `host_vars/<host>/main.yml`
- support for multiple variable files per host or group
- detection and display of Ansible Vault files
- masked display of secret values from vault-backed files
- internal editor for source files
- adding groups
- adding hosts
- adding variables to host or group context
- safe recommendation to use `vault.yml` for encrypted variables
- variable source display
- files view for selected context
- basic workspace issue reporting
- search toolbar for inventory navigation
- Effective Config Preview
- execution / selection context for suggested Ansible limit usage

---

## Effective Config Preview

The **Effective Config** view is currently one of the strongest features of AIS.

For a selected group, it can show:

- affected hosts
- variables common to all affected hosts
- variables from `group_vars/all`
- variables from selected group context
- per-host differences
- host-specific variables
- vault-backed variables
- suggested Ansible `--limit` expression

For a selected host, it can show:

- final effective variables
- variable source paths
- masked vault values
- trace / override chain
- selected branch/group context
- suggested Ansible limit such as:

```bash
-l 'hostname:&groupname'
```

AIS also explicitly warns that Ansible `--limit` filters hosts, but does not remove variables from other groups if the host is also a member of those groups.

---

## Vault handling

AIS can detect and work with Ansible Vault-backed files.

Vault values are masked in the UI by default.

AIS does not aim to replace Ansible Vault. Vault files remain standard Ansible Vault files and should remain protected by the user's normal vault password or vault password file.

Current vault-related behavior:

- detect vault files
- mask vault-backed values
- allow opening vault files when credentials are available
- suggest `vault.yml` when adding encrypted variables
- keep vault values visually separated in Effective Config output

---

## What AIS is not

AIS is not currently:

- a replacement for `ansible-inventory`
- a replacement for `ansible-playbook`
- a full Ansible runtime simulator
- a full playbook-aware variable resolver
- a backup system
- a secrets manager
- a VS Code extension

The current Effective Config view is a **static AIS inventory resolution** based on the loaded inventory model.

It does not yet include:

- play vars
- role vars
- role defaults
- facts
- `set_fact`
- registered variables
- `extra_vars`
- dynamic inventory plugins
- full Ansible runtime behavior

---

## Current limitations

Known current limitations:

- primary focus is YAML inventory projects
- INI inventory support is not complete
- Effective Config is static and does not yet verify against real `ansible-inventory`
- conflict analysis exists only in basic form
- comment-preserving round-trip editing is not yet guaranteed everywhere
- search is still evolving
- packaging as a native macOS app is not finalized
- UI language is currently English only

---

## Roadmap

Planned or considered areas:

- improve global search across hosts, groups and variable keys
- improve Effective Config grouping and trace output
- add optional verification through `ansible-inventory`
- improve conflict and duplicate variable detection
- improve safe write / before-after save audit
- add better beginner guidance
- improve documentation and examples
- split large GUI modules into smaller components
- package AIS as a native desktop application
- consider CLI mode
- consider VS Code extension later

Postponed for now:

- remote API for audit collection
- cloud synchronization
- full runtime simulation of complete playbook execution

---

## Quick start

From the project root:

```bash
cd inventory-editor
python3 -m inventory_editor.gui ../ansible-lab
```

Or use the helper script if available:

```bash
./run_editor.sh
```

---

## Project structure

Typical workspace layout expected by AIS:

```text
inventory/
  inventory.yml
  group_vars/
    all/
      main.yml
      vault.yml
    db_servers/
      main.yml
      vault.yml
  host_vars/
    host01/
      main.yml
      vault.yml
```

---

## Development status

AIS is under active development.

The project already works as a practical desktop tool for inspecting and editing Ansible inventory structures, but several areas are still experimental and should be treated with care when used against important infrastructure repositories.

Use Git and review diffs before applying changes to production inventories.

---

## Author

Antonín Ečer, DiS.

---

# Česká verze

**AIS - Ansible Inventory Studio** je desktopový nástroj pro práci s Ansible inventory, `group_vars`, `host_vars`, Ansible Vault soubory a výslednou konfigurací hostů.

Cílem není nahradit Ansible ani Git.

Cílem je udělat existující Ansible inventory přehlednější, bezpečnější na údržbu a lépe použitelné jako zdroj pravdy pro automatizaci infrastruktury.

---

## Proč AIS vznikl

V reálném infrastrukturním prostředí není Ansible inventory jen seznam serverů.

Často obsahuje:

- více skupin a vnořené skupiny
- hosty, kteří patří do více skupin
- `group_vars/all`
- skupinové proměnné
- host-specific proměnné
- více souborů proměnných pro jednu skupinu nebo hosta
- Ansible Vault soubory
- přepsané hodnoty
- historickou strukturu, ve které se špatně hledá původ hodnot

Dříve nebo později přijde otázka:

> Proč tento host dostal právě tuto hodnotu?

AIS je stavěný právě na to, aby na tuto otázku pomohl odpovědět.

Ukazuje, odkud proměnné pocházejí, která hodnota vyhrála, jaké hosty ovlivní vybraný skupinový kontext a jak vypadá výsledný inventory pohled.

---

## Aktuální funkce

AIS aktuálně umí:

- vizuální strom skupin a hostů
- práci s YAML inventory projekty
- práci s adresářovou strukturou `group_vars` a `host_vars`
- podporu `group_vars/all`
- podporu host-specific adresářů typu `host_vars/<host>/main.yml`
- více souborů proměnných pro hosta nebo skupinu
- detekci Ansible Vault souborů
- maskování hodnot z vault-backed souborů
- interní editor zdrojových souborů
- přidání skupiny
- přidání hosta
- přidání proměnné do host nebo group kontextu
- doporučení použít `vault.yml` pro šifrované proměnné
- zobrazení zdrojů proměnných
- pohled na soubory pro vybraný kontext
- základní report problémů ve workspace
- hledací toolbar pro navigaci v inventory
- Effective Config Preview
- execution / selection context včetně návrhu Ansible `--limit`

---

## Effective Config Preview

Pohled **Effective Config** je aktuálně jedna z nejsilnějších částí AIS.

Pro vybranou skupinu umí zobrazit:

- ovlivněné hosty
- společné proměnné pro všechny ovlivněné hosty
- proměnné z `group_vars/all`
- proměnné z vybrané skupiny
- rozdíly po jednotlivých hostech
- host-specific proměnné
- vault-backed proměnné
- doporučený Ansible `--limit`

Pro vybraný host umí zobrazit:

- výsledné efektivní proměnné
- zdrojové soubory proměnných
- maskované vault hodnoty
- trace / override chain
- vybraný branch/group context
- návrh Ansible limitu například:

```bash
-l 'hostname:&groupname'
```

AIS zároveň výslovně upozorňuje, že Ansible `--limit` filtruje hosty, ale neodstraňuje proměnné z jiných skupin, pokud je host zároveň jejich členem.

---

## Práce s Vaultem

AIS umí detekovat a používat Ansible Vault-backed soubory.

Vault hodnoty jsou v UI standardně maskované.

AIS nemá nahrazovat Ansible Vault. Vault soubory zůstávají běžné Ansible Vault soubory a mají být chráněné standardním vault heslem nebo vault password file.

Aktuální vault chování:

- detekce vault souborů
- maskování vault-backed hodnot
- otevření vault souboru při dostupných credentials
- doporučení `vault.yml` při přidání šifrované proměnné
- oddělené zobrazení vault hodnot v Effective Config výstupu

---

## Co AIS zatím není

AIS zatím není:

- náhrada za `ansible-inventory`
- náhrada za `ansible-playbook`
- plný simulátor Ansible runtime
- plně playbook-aware resolver proměnných
- backup systém
- secrets manager
- VS Code extension

Současný Effective Config pohled je **statické AIS inventory vyhodnocení** podle načteného modelu.

Zatím nezahrnuje:

- play vars
- role vars
- role defaults
- facts
- `set_fact`
- registered variables
- `extra_vars`
- dynamic inventory pluginy
- plné chování Ansible runtime

---

## Aktuální omezení

Známá omezení:

- hlavní fokus je YAML inventory
- INI inventory podpora není kompletní
- Effective Config je statický a zatím se neověřuje přes reálné `ansible-inventory`
- conflict analýza je zatím základní
- zachování komentářů při round-trip editaci zatím není garantované všude
- hledání se stále ladí
- balení jako nativní macOS aplikace zatím není dokončené
- UI je aktuálně pouze anglicky

---

## Roadmapa

Plánované nebo zvažované oblasti:

- zlepšení globálního hledání přes hosty, skupiny a klíče proměnných
- zlepšení Effective Config pohledu a trace výstupu
- volitelné ověření přes `ansible-inventory`
- lepší detekce konfliktů a duplicitních proměnných
- safe write / before-after save audit
- lepší průvodce pro začátečníky
- lepší dokumentace a ukázky
- rozdělení velkých GUI modulů na menší části
- zabalení AIS jako desktopové aplikace
- případný CLI režim
- VS Code extension někdy později

Prozatím odloženo:

- vzdálené API pro auditní sběr
- cloudová synchronizace
- plná runtime simulace kompletního playbook běhu

---

## Rychlé spuštění

Z rootu projektu:

```bash
cd inventory-editor
python3 -m inventory_editor.gui ../ansible-lab
```

Nebo přes helper script, pokud je dostupný:

```bash
./run_editor.sh
```

---

## Typická struktura projektu

Typická struktura workspace, se kterou AIS pracuje:

```text
inventory/
  inventory.yml
  group_vars/
    all/
      main.yml
      vault.yml
    db_servers/
      main.yml
      vault.yml
  host_vars/
    host01/
      main.yml
      vault.yml
```

---

## Stav vývoje

AIS je aktivně vyvíjený.

Projekt už funguje jako praktický desktopový nástroj pro inspekci a editaci Ansible inventory struktur, ale některé části jsou stále experimentální a je vhodné s nimi zacházet opatrně u důležitých infrastrukturních repozitářů.

Používejte Git a před aplikací změn do produkčního inventory kontrolujte diff.

---

## Autor

Antonín Ečer, DiS.
