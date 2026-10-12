# Syntetisk AML Grafdatasett for Eiendom & Foretaksstrukturer

Et produksjonsklart, syntetisk multilags grafdatasett for anti-hvitvasking (AML) innen eiendom og komplekse selskapsstrukturer, tilpasset nordiske forhold og trusselvurderinger (Økokrim).

Datasettet kombinerer **eierskapsgraf**, **kontrollgraf** og **transaksjonsflyt**, og håndhever **100 % matematisk balansebevaring (balance conservation)** i det lukkede finansielle kretsløpet.

---

### 📂 Nordic AML Graph Pack v0.1 – Sentrale Ressurser
- 📦 **[Pilot & Buyer Guide](nordic_aml_graph_pack_v0.1/PACKAGE_INDEX.md)** – Kom i gang og evaluer sample-pakken på 15 minutter.
- 📑 **[Technical Whitepaper & Methodology](METHODOLOGY.md)** – Formell spesifikasjon av multilagsgrafen, balansebevaring og typologier.
- 📈 **[ML Evaluation Report](EVALUATION_REPORT.md)** – Benchmark som dokumenterer 6.6x presisjonsløft (90.9 % vs 13.7 % for enkle regler).
- ⚖️ **[Commercial & Evaluation Terms](COMMERCIAL_TERMS.md)** – Pilotlisens og vilkår for kommersiell testing.
- 🗄️ **[BigQuery Graph & GQL Queries](bigquery_graph_queries.sql)** – DDL for Property Graph og spørringer for eierkjeder og lånesirkler.
- 🤝 **[Outreach Playbook](OUTREACH_PLAYBOOK.md)** – Valideringsstrategi og maler for kontakt med regtech og banker.

---

## 🏛️ Hvorfor Dette Datasettet?
Tradisjonelle tabellbaserte regelverk og naive IF/THEN-sjekker lider av ekstrem alarmtretthet:
- En naiv regel som flagger eiendommer med eieravvik eller pant, kollapser i et realistisk marked med **13,7 % presisjon og 63 falske alarmer** på et testsett av 180 eiendommer.
- Dette datasettet beviser verdien av **multilags graf-features**: Gradient Boosting og Random Forest oppnår **90–100 % presisjon og recall**, og eliminerer nesten all falsk støy (kun 0–1 falsk positiv).

---

## 🔍 Inkluderte Hvitvaskingstypologier (Ground Truth)

1. **Blankoskjøte (`blankoskjoete`)**:
   - En stråmann oppføres formelt som tinglyst eier (`registered_owner`), mens den reelle bakmannen har full disposisjonsrett (`actual_controller`).
   - Bakmannen overfører kjøpesummen (`property_financing`) direkte til stråmannen.
2. **Lagdelte holdingselskaper (`layered_holding`)**:
   - Reell rettighetshaver (UBO) gjemmer seg bak en kjede av 2–3 lag med aksjeselskaper:
     $$\text{UBO} \xrightarrow{\text{shareholder}} \text{Holding 1} \xrightarrow{\text{shareholder}} \text{Holding 2} \xrightarrow{\text{shareholder}} \text{PropCo} \xrightarrow{\text{registered\_owner}} \text{Eiendom}$$
   - Kapital tilføres nedover i selskapsstrukturen via `equity_injection`.
3. **Fiktivt lån / Loan-Back Mortgage Scheme (`loan_back_mortgage`)**:
   - Bakmannen kontrollerer i skjul et uautorisert utlånsselskap (`LenderCo`) som tar pant (`mortgage_holder`) i eiendommen.
   - `LenderCo` utbetaler et lån (`loan_disbursement`) til kjøper, og kjøper betaler deretter månedlige "renter og avdrag" (`loan_repayment`) tilbake til LenderCo – en legalisert overføring ut av økonomien.

---

## ⚖️ Realistisk Markedsstøy (Legitime Komplekse Strukturer)
Datasettet inneholder bevisst realistisk forstyrrelse for å stressteste falsk positiv-rate:
- **180 legitime banklån**: Registrerte banker (DNB, Nordea osv.) med ordinære pantedokumenter og månedlige avdrag.
- **45 lovlige konsernstrukturer**: Ordinære flerledds holdingselskaper og datterselskaper.
- **35 arveoppgjør & uskifteavvik**: Arvinger som disponerer eiendom hvor tinglysing henger igjen på dødsbo/forelder, men uten kriminelle transaksjoner.
- **40 sameier**: Ektefeller og partnere med felles registrert eierskap.

---

## 📊 Maskinlærings-Benchmark (Testsett: 180 eiendommer)

Evaluert med 70/30 Stratified Split før preprosesserings-skalering (ingen data leakage):

| Modell | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Falske Positive (FP) | Falske Negative (FN) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Naive Majority Baseline** | 94.44 % | 0.00 % | 0.00 % | 0.000 | 0.500 | 0 | 10 |
| **Regelbasert Heuristikk** | **65.00 %** | **13.70 %** | **100.0 %** | **0.241** | **0.815** | **63** | **0** |
| **Logistic Regression (L2)** | **99.44 %** | **90.91 %** | **100.0 %** | **0.952** | **0.994** | **1** | **0** |
| **Random Forest (100 trær)** | **98.89 %** | **90.00 %** | **90.00 %** | **0.900** | **0.999** | **1** | **1** |
| **HistGradientBoosting** | **98.89 %** | **100.0 %** | **80.00 %** | **0.889** | **0.999** | **0** | **2** |

### Top Feature Importance (Random Forest MDI):
1. `mortgagee_is_private_co` (29.97 %) – Avslører om panthaver er en godkjent bank eller et ugjennomsiktig privat AS.
2. `owner_tx_in_vol` (12.64 %) – Total transaksjonsinngang til eier.
3. `owner_net_financial_flow` (12.39 %) – Netto likviditetsendring i tilknytning til eiendommen.
4. `has_mortgage` (9.40 %) – Tilstedeværelse av pant.
5. `owner_pagerank` (8.20 %) – Sentralitet i det overordnede selskapsnettverket.

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
- `transactions.csv` (finansielle overføringer)
- `scenarios.csv` (registrerte typologiscenarioer)
- `ground_truth.csv` (fasit med metadata for ML)

### 3. Tren og evaluer ML-baseline
```bash
python baseline_model.py
```

### 4. Last inn i Google Cloud BigQuery
Forhåndskonfigurer Google Cloud credentials (`gcloud auth application-default login`), deretter:
```bash
python load_to_bigquery.py
```
Dette oppretter tabellene i BigQuery med typesikre skjemaer under `aml_synth`, samt views som `v_aml_master_alerts` og `v_entity_risk_summary`.

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
