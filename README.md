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

## Important Ansible behavior AIS makes visible

Ansible host targeting and Ansible variable loading are not the same thing.

A playbook limit such as:

```bash
ansible-playbook -i inventory/inventory.yml playbook.yml -l 'hostname:&groupname'
```

limits which hosts the playbook runs on.

It does **not** isolate variable loading to only that selected group.

If a host is a member of multiple inventory groups, Ansible can load variables from all groups the host belongs to, including `group_vars` directories outside the group used in `--limit`.

This matters especially when one of those other groups contains Ansible Vault-backed variables.

A job that appears to target a safe group may still fail with a Vault-related error if the selected host is also a member of another group with vault-backed group variables.

AIS therefore shows both:

- the selected AIS branch/group context
- the actual Ansible inventory group membership impact for the host

This distinction is one of the main reasons AIS exists.

---

## Current features

AIS currently provides:

- visual inventory tree for groups and hosts
- support for YAML inventory projects
- support for explicit inventory file selection
- support for workspaces containing multiple inventory files
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
- Issues view with Ansible group membership and Vault impact warnings
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

- final effective variables grouped by source
- variables from `group_vars/all`
- vault variables from `group_vars/all`
- variables from selected group context
- vault variables from selected group context
- host-specific variables
- host-specific vault variables
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

## Actual Ansible Inventory Membership Impact

AIS distinguishes between two views:

### AIS branch preview

This is the context selected in the tree.

For example, a host may be selected under:

```text
web_servers/hostname
```

This is useful for inspection and for understanding how a host looks from a selected inventory branch.

### Actual Ansible inventory membership

This shows all groups the host belongs to.

For example:

```text
all
managed
prod
prod_zabbix
web_servers
```

Ansible variable loading is based on this broader membership, not only on the selected UI branch.

AIS can therefore show:

- selected AIS branch/context groups
- all Ansible inventory groups for the host
- variable sources Ansible may load for the host
- vault-backed files reachable through host membership
- vault-backed files outside the selected branch
- a warning that jobs without vault secrets may fail even when limited to another group

This helps detect cases where a host is safe-looking in one branch but still pulls variables from another group.

---

## Issues and severity levels

The **Issues** tab is used for operational warnings and analysis findings.

AIS currently uses the following severity model:

```text
[A/HIGH]  High risk
[B/WARN]  Warning / medium risk
[C/INFO]  Informational notice
```

### A / HIGH

High-risk issue.

Typical example:

```text
Vault-backed variables exist outside the selected branch, but are still reachable by host membership.
```

This can cause a playbook limited to one group to still require Vault secrets from another group.

### B / WARN

Important operational warning.

Typical examples:

```text
Host is member of multiple Ansible inventory groups.
Host may load variables from groups outside the selected branch.
Host has vault-backed variables reachable through inventory membership.
```

This is not always wrong, but it is important and can explain unexpected Ansible behavior.

### C / INFO

Informational notice.

Typical examples:

```text
Static AIS preview only.
Unusual structure detected.
Multiple variable files exist for one group or host.
```

AIS may later use this level for recommendations and non-blocking guidance.

---

## Vault handling

AIS can detect and work with Ansible Vault-backed files.

Vault values are masked in the UI by default.

AIS does not aim to replace Ansible Vault. Vault files remain standard Ansible Vault files and should remain protected by the user's normal vault password or vault password file.

Current vault-related behavior:

- detect vault files
- detect vault-backed files by source path and Ansible Vault file header
- mask vault-backed values
- allow opening vault files when credentials are available
- suggest `vault.yml` when adding encrypted variables
- keep vault values visually separated in Effective Config output
- warn when vault-backed files are reachable through Ansible group membership
- warn when vault-backed files exist outside the selected branch but may still affect the selected host

AIS does not upload vault passwords and does not act as a secrets manager.

---

## Inventory file selection

AIS treats the workspace directory and the inventory file as two separate concepts.

A workspace may contain more than one inventory file, for example:

```text
inventory.yml
inventory-prod.yml
inventories/dev.yml
inventories/prod.yml
```

AIS therefore supports selecting the exact inventory file that should be used as the source of truth.

The selected inventory file is also shown in the Effective Config execution context.

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
- improve Issues view and severity reporting
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
./run_editor.sh
```

If the application has saved settings, AIS starts using the saved workspace and inventory file.

You can also pass a workspace explicitly:

```bash
./run_editor.sh /path/to/inventory-workspace
```

From inside the Python package directory:

```bash
cd inventory-editor
python3 -m inventory_editor.gui /path/to/inventory-workspace
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

A real project may also contain multiple inventory files. In that case, choose the intended inventory file in AIS.

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

## Důležité chování Ansible, které AIS zviditelňuje

Cílení hostů v Ansible a načítání proměnných v Ansible nejsou totéž.

Limit například:

```bash
ansible-playbook -i inventory/inventory.yml playbook.yml -l 'hostname:&groupname'
```

omezuje, na kterých hostech playbook poběží.

Neizoluje ale načítání proměnných pouze na vybranou skupinu.

Pokud je host členem více inventory skupin, Ansible může načítat proměnné ze všech skupin, do kterých host patří, včetně `group_vars` adresářů mimo skupinu použitou v `--limit`.

To je důležité hlavně v případě, kdy některá z těchto dalších skupin obsahuje Ansible Vault proměnné.

Job, který zdánlivě cílí na bezpečnou skupinu, může spadnout na Vault, pokud je vybraný host zároveň členem jiné skupiny s vault-backed group variables.

AIS proto ukazuje obě roviny:

- vybraný AIS branch/group context
- skutečný dopad Ansible inventory členství hosta

Tohle rozlišení je jeden z hlavních důvodů, proč AIS vzniká.

---

## Aktuální funkce

AIS aktuálně umí:

- vizuální strom skupin a hostů
- práci s YAML inventory projekty
- výběr konkrétního inventory souboru
- práci s workspace, kde je více inventory souborů
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
- Issues pohled s upozorněním na group membership a Vault dopad
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

- výsledné efektivní proměnné seskupené podle zdroje
- proměnné z `group_vars/all`
- vault proměnné z `group_vars/all`
- proměnné z vybrané skupiny
- vault proměnné z vybrané skupiny
- host-specific proměnné
- host-specific vault proměnné
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

## Skutečný dopad Ansible inventory členství

AIS rozlišuje dvě věci.

### AIS branch preview

To je kontext vybraný ve stromu.

Například host může být vybraný pod:

```text
web_servers/hostname
```

To je užitečné pro inspekci a pochopení hosta z konkrétní větve inventory.

### Skutečné Ansible inventory členství

To ukazuje všechny skupiny, do kterých host patří.

Například:

```text
all
managed
prod
prod_zabbix
web_servers
```

Ansible načítání proměnných se řídí tímto širším členstvím, ne pouze vybranou větví v UI.

AIS proto umí zobrazit:

- vybrané AIS branch/context skupiny
- všechny Ansible inventory skupiny hosta
- zdroje proměnných, které může Ansible pro hosta načíst
- vault-backed soubory dosažitelné přes členství hosta
- vault-backed soubory mimo vybranou větev
- upozornění, že joby bez Vault secretu mohou spadnout i při limitu na jinou skupinu

To pomáhá odhalit situace, kdy host v jedné větvi vypadá bezpečně, ale proměnné se mu reálně načítají ještě odjinud.

---

## Issues a úrovně závažnosti

Pohled **Issues** slouží pro provozní varování a analytické nálezy.

AIS aktuálně používá tento model závažnosti:

```text
[A/HIGH]  Vysoké riziko
[B/WARN]  Varování / střední riziko
[C/INFO]  Informační upozornění
```

### A / HIGH

Vysoce rizikový nález.

Typický příklad:

```text
Vault-backed variables exist outside the selected branch, but are still reachable by host membership.
```

To může způsobit, že playbook omezený na jednu skupinu bude přesto vyžadovat Vault secret z jiné skupiny.

### B / WARN

Důležité provozní varování.

Typické příklady:

```text
Host is member of multiple Ansible inventory groups.
Host may load variables from groups outside the selected branch.
Host has vault-backed variables reachable through inventory membership.
```

Nemusí to být chyba, ale je to důležité vědět a může to vysvětlit nečekané chování Ansible.

### C / INFO

Informační upozornění.

Typické příklady:

```text
Static AIS preview only.
Unusual structure detected.
Multiple variable files exist for one group or host.
```

AIS může tuto úroveň později používat pro doporučení a neblokující poznámky.

---

## Práce s Vaultem

AIS umí detekovat a používat Ansible Vault-backed soubory.

Vault hodnoty jsou v UI standardně maskované.

AIS nemá nahrazovat Ansible Vault. Vault soubory zůstávají běžné Ansible Vault soubory a mají být chráněné standardním vault heslem nebo vault password file.

Aktuální vault chování:

- detekce vault souborů
- detekce vault-backed souborů podle zdrojové cesty a Ansible Vault hlavičky
- maskování vault-backed hodnot
- otevření vault souboru při dostupných credentials
- doporučení `vault.yml` při přidání šifrované proměnné
- oddělené zobrazení vault hodnot v Effective Config výstupu
- upozornění, pokud jsou vault-backed soubory dosažitelné přes Ansible group membership
- upozornění, pokud vault-backed soubory existují mimo vybranou větev, ale stále mohou ovlivnit vybraný host

AIS neposílá vault hesla nikam pryč a nechová se jako secrets manager.

---

## Výběr inventory souboru

AIS rozlišuje workspace adresář a konkrétní inventory soubor.

Workspace může obsahovat více inventory souborů, například:

```text
inventory.yml
inventory-prod.yml
inventories/dev.yml
inventories/prod.yml
```

AIS proto podporuje výběr konkrétního inventory souboru, který má být použit jako zdroj pravdy.

Vybraný inventory soubor je zároveň zobrazený v Effective Config execution context.

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
- lepší Issues pohled a severity reporting
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
./run_editor.sh
```

Pokud má aplikace uložené nastavení, AIS se spustí s uloženým workspace a inventory souborem.

Workspace lze také předat explicitně:

```bash
./run_editor.sh /path/to/inventory-workspace
```

Z adresáře Python package:

```bash
cd inventory-editor
python3 -m inventory_editor.gui /path/to/inventory-workspace
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

Reálný projekt může obsahovat i více inventory souborů. V takovém případě v AIS vyberte ten, který má být použitý.

---

## Stav vývoje

AIS je aktivně vyvíjený.

Projekt už funguje jako praktický desktopový nástroj pro inspekci a editaci Ansible inventory struktur, ale některé části jsou stále experimentální a je vhodné s nimi zacházet opatrně u důležitých infrastrukturních repozitářů.

Používejte Git a před aplikací změn do produkčního inventory kontrolujte diff.

---

## Autor

Antonín Ečer, DiS.
