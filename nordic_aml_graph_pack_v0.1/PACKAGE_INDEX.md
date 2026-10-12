# Nordic AML Graph Pack v0.1 – Pilot & Buyer Guide

Velkommen til **Nordic AML Graph Pack v0.1**. Denne pakken inneholder alt du trenger for å evaluere syntetiske graf- og transaksjonsdata for eiendomshvitvasking (AML).

---

## 📦 Innhold i Pakken

1. **Datasett (Sample CSV)** i [`output/`](../output/):
   - `entities.csv` (1 254 rader: personer, selskaper, autoriserte banker og eiendommer)
   - `ownership_edges.csv` (1 605 kanter: formelt eierskap, faktisk kontroll, aksjonærer, pant)
   - `transactions.csv` (2 483 transaksjoner: lån, avdrag, egenkapital, overføringer)
   - `scenarios.csv` (35 kriminelle scenarioer)
   - `ground_truth.csv` (Fasit med typologitype, bakmann, stråmann og beløp)
2. **Dokumentasjon & Metodikk**:
   - [`METHODOLOGY.md`](../METHODOLOGY.md) – Detaljert teknisk hvitbok om multilagsmodellen, typologiene og balansekonservering.
   - [`EVALUATION_REPORT.md`](../EVALUATION_REPORT.md) – Ytelsesrapport som beviser at regelsystemer kollapser med 63 falske alarmer, mens graf-ML oppnår 90 %+ presisjon.
   - [`COMMERCIAL_TERMS.md`](../COMMERCIAL_TERMS.md) – Evalueringslisens og kommersielle vilkår.
3. **Kode & Skyintegrasjon**:
   - [`generator.py`](../generator.py) – Kildekode for lokal syntetisering og matematisk balansekontroll.
   - [`load_to_bigquery.py`](../load_to_bigquery.py) – Automatisk opplasting og skjemabygging i Google Cloud BigQuery.
   - [`bigquery_graph_queries.sql`](../bigquery_graph_queries.sql) – DDL for BigQuery Property Graph, deklarativ GQL og produksjonsklare SQL-views.
   - [`baseline_model.py`](../baseline_model.py) – Komplett trenings- og evalueringspipeline for Machine Learning.
   - [`spark_generator.py`](../spark_generator.py) – PySpark-skript for oppskalering til 100 000+ noder på Dataproc Serverless.

---

## ⏱️ Slik Evaluerer Du Datasettet på 15 Minutter

### Steg 1: Inspiser data og ground truth
Åpne `output/ground_truth.csv` og sammenlign med `output/ownership_edges.csv`. Se hvordan faktiske bakmenn (`actual_controller`) skjuler seg bak stråmenn og holdingselskaper.

### Steg 2: Kjør ML-baselinen lokalt
```bash
pip install -r requirements.txt
python baseline_model.py
```
Dette bygger NetworkX-grafene, beregner PageRank og sentraliteter, deler i 70/30 stratified holdout, og demonstrerer at:
- Naiv regelbasert sjekk gir **63 falske alarmer** (13,7 % presisjon).
- Random Forest og Logistic Regression opprettholder **90–91 % presisjon** og fanger opp tilfellene med nesten null falske positive.

### Steg 3: Kjør spørringer i BigQuery (eller lokal SQL)
Bruk spørringene i `bigquery_graph_queries.sql` for å traversere eierkjedene direkte i SQL.

---

## 📬 Kontakt & Fullskala Lisens
For tilgang til 100k+ noder eller tilpassede typologier:
- **E-post**: knutnilsen87@gmail.com
- **Repository**: [https://github.com/knutnilsen87-collab/kunstigedataset](https://github.com/knutnilsen87-collab/kunstigedataset)
