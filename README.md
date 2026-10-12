# Syntetisk AML Grafdatasett for Eiendom & Foretaksstrukturer
**Nordic AML Graph Pack v0.2 – Independent Multi-Seed Benchmark**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/knutnilsen87-collab/kunstigedataset/blob/main/benchmark_walkthrough.ipynb)
[![GitHub Repository](https://img.shields.io/badge/GitHub-kunstigedataset-blue.svg)](https://github.com/knutnilsen87-collab/kunstigedataset)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Et produksjonsklart, syntetisk multilags grafdatasett for anti-hvitvasking (AML) innen eiendom og komplekse selskapsstrukturer, tilpasset nordiske forhold og trusselvurderinger (Økokrim).

Datasettet kombinerer **eierskapsgraf**, **kontrollgraf** og **transaksjonsflyt**, og håndhever **100 % matematisk balansebevaring (balance conservation)** i det lukkede finansielle kretsløpet.

---

### 📂 Sentrale Ressurser
- 🚀 **[Interactive Colab Walkthrough (1-Click Run)](https://colab.research.google.com/github/knutnilsen87-collab/kunstigedataset/blob/main/benchmark_walkthrough.ipynb)** – Kjør generering, visuelle grafer og modell-evaluering direkte i nettleseren.
- 📦 **[Pilot & Buyer Guide](nordic_aml_graph_pack_v0.1/PACKAGE_INDEX.md)** – Kom i gang og evaluer sample-pakken på 15 minutter.
- 📑 **[Technical Whitepaper & Methodology](METHODOLOGY.md)** – Formell spesifikasjon av multilagsgrafen, balansebevaring og typologier.
- 📈 **[ML Evaluation Report (Benchmark v0.2)](EVALUATION_REPORT.md)** – Multi-seed blind test som dokumenterer 3.75x presisjonsløft (75.2 % vs 20.0 % for regler) og 91.5 % kutt i falske alarmer.
- ⚖️ **[Commercial & Evaluation Terms](COMMERCIAL_TERMS.md)** – Pilotlisens og vilkår for kommersiell testing.
- 🗄️ **[BigQuery Graph & GQL Queries](bigquery_graph_queries.sql)** – DDL for Property Graph, GQL og SQL-views for BigQuery.
- 🤝 **[Outreach Playbook](OUTREACH_PLAYBOOK.md)** – Valideringsstrategi og maler for kontakt med regtech og banker.

---

## 🏛️ Hvorfor Dette Datasettet?
Tradisjonelle tabellbaserte regelverk og enkle IF/THEN-varsler lider av ekstrem alarmtretthet:
- En naiv regel som flagger eiendommer med eieravvik eller privat pant, kollapser i et realistisk marked med **20,03 % ± 0.75 % presisjon og 140 falske alarmer** på tvers av ukjente testgrafer.
- Dette datasettet beviser verdien av **multilags graf-features**: Maskinlæring (Random Forest og HistGradientBoosting) oppnår **75,22 % ± 5.87 % presisjon og 99,29 % ± 1.24 % recall**, og reduserer de falske alarmene med over **91.5 %** (ned til 11.8 i snitt).

---

## 🔍 Inkluderte Hvitvaskingstypologier (Ground Truth)

Alle transaksjoner benytter **nøytrale, standardiserte banktyper** for å forhindre leksikalsk snarvei:

1. **Blankoskjøte (`blankoskjoete`)**:
   - En stråmann oppføres formelt som tinglyst eier (`registered_owner`), mens den reelle bakmannen har full disposisjonsrett (`actual_controller`).
   - Bakmannen overfører kjøpesummen via ordinær `transfer` direkte til stråmannen.
2. **Lagdelte holdingselskaper (`layered_holding`)**:
   - Reell rettighetshaver (UBO) gjemmer seg bak en kjede av 3 lag med aksjeselskaper:
     $$\text{UBO} \xrightarrow{\text{shareholder}} \text{Holding 1} \xrightarrow{\text{shareholder}} \text{Holding 2} \xrightarrow{\text{shareholder}} \text{PropCo} \xrightarrow{\text{registered\_owner}} \text{Eiendom}$$
   - Kapital tilføres nedover i selskapsstrukturen via nøytral `capital_contribution`.
3. **Fiktivt lån / Loan-Back Mortgage Scheme (`loan_back_mortgage`)**:
   - Bakmannen kontrollerer i skjul et privat utlånsselskap (`LenderCo`) som tar pant (`mortgage_holder`) i eiendommen.
   - `LenderCo` utbetaler et lån via `loan_disbursement` til kjøper, og kjøper betaler deretter månedlige avdrag via `loan_installment` tilbake til LenderCo.

---

## ⚖️ Realistisk Markedsstøy (Legitime Komplekse Strukturer)
Datasettet inneholder bevisst realistisk forstyrrelse for å stressteste falsk positiv-rate:
- **180 legitime banklån**: Registrerte banker (DNB, Nordea etc.) med ordinære pantedokumenter (`loan_disbursement` og `loan_installment`).
- **30 legitime private pantelån (selgerkreditt)**: Lån fra privatpersoner eller vanlige bedrifter som forurenser privat pant og tvinger modeller til å lære helhetlig relasjonsanalyse.
- **45 lovlige konsernstrukturer**: Ordinære flerledds holdingselskaper med lovlige konsernbidrag (`capital_contribution`).
- **40 arveoppgjør & uskifteavvik**: Arvinger som disponerer eiendom hvor tinglysing henger igjen på dødsbo/forelder (`transfer`), uten kriminelle bakmenn.
- **40 sameier**: Ektefeller og partnere med felles registrert eierskap.

---

## 📊 Benchmark v0.2: Independent Cross-Graph Validation

Evaluert ved å trene på Graf 1 (Seed 42, 600 eiendommer, basis-beløp) og teste blindt på **4 uavhengige test-grafer** med varierende størrelse (700–850 eiendommer), opptil +60 % beløpsforskyvning (`amount_shift=1.60`) og opptil +30 % økt støy:

| Modell | Test Presisjon (Mean ± Std) | Test Recall (Mean ± Std) | Test F1-Score (Mean ± Std) | Falske Positive (FP) | Falske Negative (FN) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Regelbasert Heuristikk** | **20.03 % ± 0.75 %** | **100.00 % ± 0.00 %** | **0.3337 ± 0.0104** | **140.0 ± 6.5** | **0.0 ± 0.0** |
| **Logistic Regression (L2)** | **73.02 % ± 4.08 %** | **93.57 % ± 1.24 %** | **0.8195 ± 0.0254** | **12.2 ± 2.6** | **2.2 ± 0.5** |
| **HistGradientBoosting** | **66.91 % ± 5.03 %** | **99.29 % ± 1.24 %** | **0.7982 ± 0.0343** | **17.5 ± 4.0** | **0.2 ± 0.5** |
| **Random Forest (100 trær)** | **75.22 % ± 5.87 %** | **99.29 % ± 1.24 %** | **0.8543 ± 0.0321** | **11.8 ± 3.5** | **0.2 ± 0.5** |

### Top Nøytrale Features (Random Forest Importance):
1. `controller_transfer_outflow` (12.4 %) – Avslører bakmannens direkte finansiering til stråmann ved blankoskjøter.
2. `owner_tx_in_vol` (11.3 %) – Samlet inngående likviditetsvolum.
3. `owner_loan_outflow` (10.2 %) – Månedlig avdragsbetaling i lånestrukturer.
4. `owner_net_financial_flow` (9.3 %) – Netto kontantstrøm på eierkontoen.
5. `owner_transfer_inflow` (8.5 %) – Mottatte overføringer.
6. `has_ownership_discrepancy` (8.4 %) – Avvik mellom registrert eier og faktisk kontroller.
7. `loan_repayment_ratio` (7.8 %) – Forholdet mellom tilbakebetalte avdrag og utbetalt lån.
8. `mortgagee_is_private` (6.5 %) – Indikerer privat panthaver kombinert med sirkulære relasjoner.

---

## 🚀 Kom i Gang

### 1. Klon repo og installer avhengigheter
```bash
git clone https://github.com/knutnilsen87-collab/kunstigedataset.git
cd kunstigedataset
pip install -r requirements.txt
```

### 2. Generer datasettet lokalt
```bash
python generator.py
```
Dette produserer typesikre CSV-filer i `output/`:
- `entities.csv` (personer, selskaper, banker og eiendommer)
- `ownership_edges.csv` (eierskaps-, kontroll-, aksjonær- og pantekanter)
- `transactions.csv` (finansielle overføringer med nøytrale typer)
- `scenarios.csv` (registrerte typologiscenarioer med disjunkte eiendommer)
- `ground_truth.csv` (fasit med metadata for ML)

### 3. Tren og evaluer modeller
```bash
# 70/30 Stratified Holdout Test
python baseline_model.py

# Multi-Seed Independent Cross-Graph Validation Test
python generalization_test.py
```

### 4. Last inn i Google Cloud BigQuery
Forhåndskonfigurer Google Cloud credentials (`gcloud auth application-default login`), deretter:
```bash
python load_to_bigquery.py
```
Dette oppretter og verifiserer følgende i `datsetsyntetisk.aml_synth` (europe-west1):
- `entities` (1 254 rader)
- `ownership_edges` (1 674 rader)
- `transactions` (2 565 rader)
- `scenarios` (35 rader)
- `ground_truth` (35 rader)
- `v_detected_blankoskjoete` (189 rader)
- `v_entity_risk_summary` (1 254 rader)
- `v_aml_master_alerts` (229 rader)

### 5. BigQuery Property Graph & GQL
Grafstrukturen kan opprettes direkte i BigQuery med:
```sql
CREATE OR REPLACE PROPERTY GRAPH `datsetsyntetisk.aml_synth.aml_network_graph` ...
```
Se [`bigquery_graph_queries.sql`](bigquery_graph_queries.sql) for:
- Deklarative GQL-mønstre for flerledds eierkjeder og sirkulære låneavtaler (BigQuery Enterprise/Enterprise Plus).
- Produksjonstestede rekursive SQL-views som kjører på alle BigQuery On-Demand prosjekter.

### 6. Skalering for stordata (Dataproc / Apache Spark)
Bruk `spark_generator.py` for distribuert syntetisering av millioner av noder og kanter på Google Cloud Dataproc Serverless.

---

## 📄 Lisens
Apache-2.0
