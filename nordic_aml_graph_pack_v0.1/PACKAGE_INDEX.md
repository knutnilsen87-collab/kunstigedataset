# Nordic AML Graph Pack v0.1 – Pilot & Buyer Guide

Velkommen til **Nordic AML Graph Pack v0.1**. Denne pakken inneholder alt du trenger for å evaluere syntetiske graf- og transaksjonsdata for eiendomshvitvasking (AML).

---

## 📦 Innhold i Pakken

1. **Datasett (Sample CSV)** i [`output/`](../output/):
   - `entities.csv` (1 254 rader: personer, selskaper, autoriserte banker og eiendommer)
   - `ownership_edges.csv` (1 674 kanter: formelt eierskap, faktisk kontroll, aksjonærer, pant)
   - `transactions.csv` (2 565 transaksjoner: lån, avdrag, kapital, overføringer med nøytrale typer)
   - `scenarios.csv` (35 kriminelle scenarioer på disjunkte eiendommer)
   - `ground_truth.csv` (35 rader: fasit med typologitype, bakmann, stråmann og beløp)
2. **Dokumentasjon & Metodikk**:
   - [`METHODOLOGY.md`](../METHODOLOGY.md) – Detaljert teknisk hvitbok om multilagsmodellen, typologiene og balansekonservering.
   - [`EVALUATION_REPORT.md`](../EVALUATION_REPORT.md) – Ytelsesrapport (Benchmark v0.2) som dokumenterer 3.75x presisjonsløft (75.2 % vs 20.0 % for regler) og 91.5 % kutt i falske alarmer under multi-seed blind testing.
   - [`COMMERCIAL_TERMS.md`](../COMMERCIAL_TERMS.md) – Evalueringslisens og kommersielle vilkår.
3. **Kode & Skyintegrasjon**:
   - [`generator.py`](../generator.py) – Kildekode for lokal syntetisering, nøytrale transaksjonstyper og matematisk balansekontroll.
   - [`load_to_bigquery.py`](../load_to_bigquery.py) – Automatisk opplasting, skjemabygging og analytiske views i Google Cloud BigQuery.
   - [`bigquery_graph_queries.sql`](../bigquery_graph_queries.sql) – DDL for BigQuery Property Graph, deklarativ GQL og produksjonsklare SQL-views.
   - [`baseline_model.py`](../baseline_model.py) – Trenings- og evalueringspipeline for Machine Learning (Benchmark v0.2 nøytrale features).
   - [`generalization_test.py`](../generalization_test.py) – Multi-Seed Out-of-Distribution validering over 4 uavhengige testgrafer.
   - [`benchmark_walkthrough.ipynb`](../benchmark_walkthrough.ipynb) – Interaktiv Google Colab walkthrough med visuell graf-plotting og modell-sammenligning.
   - [`spark_generator.py`](../spark_generator.py) – PySpark-skript for oppskalering til 100 000+ noder på Dataproc Serverless.

---

## ⏱️ Slik Evaluerer Du Datasettet på 15 Minutter

### Steg 1: Inspiser data og ground truth
Åpne `output/ground_truth.csv` og sammenlign med `output/ownership_edges.csv`. Se hvordan faktiske bakmenn (`actual_controller`) skjuler seg bak stråmenn og holdingselskaper.

### Steg 2: Kjør ML-baselinen lokalt
```bash
pip install -r requirements.txt
python baseline_model.py
python generalization_test.py
```
Dette bygger NetworkX-grafene, beregner PageRank og sentraliteter, og demonstrerer at:
- Naiv regelbasert sjekk gir **140 falske alarmer** (20,0 % presisjon).
- Random Forest oppnår **75,2 % presisjon og 99,3 % recall** blindt på tvers av 4 uavhengige testgrafer med ulik størrelse, beløpsforskyvning og støy.

### Steg 3: Kjør spørringer i BigQuery (eller lokal SQL)
Bruk spørringene i `bigquery_graph_queries.sql` for å traversere eierkjedene direkte i SQL.

---

## 📬 Kontakt & Fullskala Lisens
For tilgang til 100k+ noder eller tilpassede typologier:
- **E-post**: knutnilsen87@gmail.com
- **Repository**: [https://github.com/knutnilsen87-collab/kunstigedataset](https://github.com/knutnilsen87-collab/kunstigedataset)
