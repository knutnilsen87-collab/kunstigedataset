# ML Evaluation Report: Robusthet mot Realistisk Støy & Benigne Komplekse Strukturer
**Prosjekt**: Syntetisk Grafdatasett for Eiendomshvitvasking (AML)  
**Datasett**: `datsetsyntetisk.aml_synth` (600 eiendommer, 524 entiteter inkl. 4 banker, 1 605 eierskapskanter, 2 483 transaksjoner)  
**Evaluering**: 70/30 Stratified Holdout Testsett (180 eiendommer: 170 normale, 10 AML-anomalier)

---

## 1. Hovedkonklusjon: Hvorfor Enkle Regler Feiler og ML Er Nødvendig

Ved å injisere **realistiske, legitime komplekse markedsstrukturer** (180 ordinære banklån, 45 lovlige konsernselskaper, 35 legitime arve-/uskifteavvik og 40 sameier):

1. **Regelbasert Heuristikk kollapser**:
   - Precision stuper fra 100 % til **13.70 %**.
   - Falsk positiv-rate eksploderer: **63 uskyldige eiendommer** flagges feilaktig som hvitvasking (63 av 73 alarmer er falske!).
   - En regel som kun ser på `discrepancy` eller `mortgage` kveler et compliance-team med støy.
2. **Machine Learning opprettholder høy presisjon**:
   - **Logistic Regression (L2)**: Precision = **90.91 %**, Recall = **100.0 %**, F1 = **0.9524**, ROC-AUC = **0.9941** (kun 1 FP i hele testsettet mot regelens 63).
   - **Random Forest**: Precision = **90.00 %**, Recall = **90.00 %**, F1 = **0.9000**, ROC-AUC = **0.9994**.
   - **HistGradientBoosting**: Precision = **100.00 %** (0 FP), Recall = **80.00 %**, F1 = **0.8889**, ROC-AUC = **0.9988**.

Dette gir datasettet en **eksepsjonell defensibility og salgsverdi**: Det beviser hvorfor banker må kjøpe multilags graf-innsikt fremfor å stole på flate regelsjekker.

---

## 2. Injisert Markedsstruktur: Legitime Edge Cases vs. Kriminelle Anomalier

| Kategori | Volum | Mekanikk | Forretningsmessig hensikt |
| :--- | :---: | :--- | :--- |
| **Legitime Banklån** | 180 | `mortgage_holder` fra godkjent bank med ordinære renter/avdrag | Forurenser `has_mortgage` så modellen må skille bank vs. stråselskap |
| **Legitime Konsernholdinger** | 45 | Lovlig AS som eier AS med ordinære konsernbidrag | Forurenser `holding_chain_depth` så selskapslag ikke automatisk er mistenkelig |
| **Arv & Uskifte** | 35 | `registered_owner != actual_controller` uten uvanlig finansiering | Forurenser eieravvik så arveoppgjør ikke forveksles med blankoskjøte |
| **Sameier** | 40 | To registrerte eiere (f.eks. ektefeller) | Realistisk eierstruktur |
| **Blankoskjøte (AML)** | 14 | Stråmann + reell bakmann + `property_financing` | Kriminell anomali |
| **Lagdelt Holding (AML)** | 10 | Skjult UBO bak 3 lag stråselskaper + `equity_injection` | Kriminell anomali |
| **Fiktivt Lån (AML)** | 10 | Uregistrert privat LenderCo + `loan_disbursement` + sirkulære avdrag | Kriminell anomali |

---

## 3. Modell-Sammenligning (Testsett: 180 eiendommer)

| Modell | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Falske Positive (FP) | Falske Negative (FN) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Naive Majority Baseline** | 94.44 % | 0.00 % | 0.00 % | 0.000 | 0.500 | 0 | 10 |
| **Regelbasert Heuristikk** | **65.00 %** | **13.70 %** | **100.0 %** | **0.241** | **0.815** | **63** | **0** |
| **Logistic Regression (L2)** | **99.44 %** | **90.91 %** | **100.0 %** | **0.952** | **0.994** | **1** | **0** |
| **Random Forest (100 trær)** | **98.89 %** | **90.00 %** | **90.00 %** | **0.900** | **0.999** | **1** | **1** |
| **HistGradientBoosting** | **98.89 %** | **100.0 %** | **80.00 %** | **0.889** | **0.999** | **0** | **2** |

---

## 4. Slice-basert Evaluering per Typologi (Testsett)

| Typologi | Regelbasert Recall | Random Forest Recall | HistGradientBoosting Recall |
| :--- | :---: | :---: | :---: |
| **Blankoskjøte (`blankoskjoete`)** | 100 % (4/4) | 75 % (3/4) | 50 % (2/4) |
| **Lagdelte holdingselskaper (`layered_holding`)** | 100 % (3/3) | 100 % (3/3) | 100 % (3/3) |
| **Fiktivt lån (`loan_back_mortgage`)** | 100 % (3/3) | 100 % (3/3) | 100 % (3/3) |

*Merk: Regelbasert heuristikk finner alle, men prisen er 63 falske alarmer på uskyldige boligeiere. ML-modellene eliminerer nesten all falsk støy (kun 0-1 FP).*

---

## 5. Hva Lærte Modellen? (Random Forest Feature Importance)

1. **`mortgagee_is_private_co` (29.97 %)**: Den desidert viktigste separasjonsfaktoren! Modellen forstår at pant fra en godkjent bank er ufarlig, mens pant fra et privat uautorisert aksjeselskap er et sterkt faresignal.
2. **`owner_tx_in_vol` (12.64 %)** & **`owner_net_financial_flow` (12.39 %)**: Fanger opp uforklarlig netto likviditetsflyt til/fra eieren.
3. **`has_mortgage` (9.40 %)**: Pantstatus som kontekstuelt signal.
4. **`owner_pagerank` (8.20 %)**: Posisjon og innflytelse i det totale selskapsnettverket.
5. **`has_ownership_discrepancy` (6.25 %)**: Eierskapsdivergens veies nå sammen med transaksjonstype (skiller familie/arv fra stråmannsoverføringer).

---

## 6. Oppsummering
Datasettet har nå nådd en standard som er moden for kommersiell presentasjon mot banker og finanstilsyn:
- Inneholder 3 kriminelle typologier.
- Inneholder 4 distinkte legitime forstyrrelsesmønstre (banklån, familiekonsern, arv, sameie).
- Matematisk balansebevaring er 100 % verifisert.
- Viser en klar og målbar "lift" (Precision 90.9 % vs 13.7 %) som rettferdiggjør bruk av graf-ML over enkle regelsystemer.
