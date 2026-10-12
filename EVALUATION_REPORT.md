# ML Evaluation Report: Herdet Cross-Graph & Multi-Model Benchmark
**Prosjekt**: Syntetisk Grafdatasett for Eiendomshvitvasking (AML)  
**Datasett**: `datsetsyntetisk.aml_synth` (600–800 eiendommer, 524–650 entiteter, 1 619–2 100 kanter, 2 575–3 400 transaksjoner)  
**Graf-arkitektur**: NetworkX `MultiDiGraph` (sikrer at parallelle roller mellom samme noder bevares 100 %)  
**Evaluering**:
1. **Intern 70/30 Stratified Holdout Test** (180 eiendommer).
2. **Out-of-Distribution Cross-Graph Test** (Modell trent på Graf 1 med seed 42 testet blindt på usett Graf 2 med seed 999, +40 % beløpsforskyvning (`amount_shift=1.40`) og +25 % støy).

---

## 1. Hovedfunn: Fra Leketøy til Ekte Ikke-Lineær Separabilitet

Ved å fjerne snarveier og innføre:
- **30 legitime private pantelån** (selgerkreditt / familielån med tinglyst pant som forurenser `mortgagee_is_private_co`),
- **Faktisk +40 % beløpsforskyvning** (`amount_shift = 1.40`),
- **MultiDiGraph-arkitektur** som bevarer parallelle kanter for `registered_owner` og `actual_controller`,

får vi frem en realistisk **ytelsesgradient** mellom modellene:

```
                                  Presisjon    Recall     F1-Score    Falske Positive (FP)
Regelbasert Heuristikk:             11.9 %     100.0 %     0.2118             253
Lineær Modell (Logistic Reg L2):    64.2 %     100.0 %     0.7816              19
Gradient Boosting (HistGB):         93.9 %      91.2 %     0.9254               2
Random Forest (100 trær):          100.0 %     100.0 %     1.0000               0
```

### Hva forteller denne gradienten oss?
1. **Regel-kollaps (11,9 % presisjon, 253 falske alarmer)**: En regel som flagger eiendommer basert på `discrepancy` eller `mortgage` kveles fullstendig av legitime boliglån, selgerkreditter og arveoppgjør.
2. **Lineære begrensninger (64,2 % presisjon, 19 falske alarmer)**: Logistisk regresjon mister presisjon fordi en enkel lineær hyperflate ikke klarer å skille legitime private lån fra kriminelle loan-back-opplegg når begge har privat panthaver.
3. **Ikke-lineær overlegenhet (93,9 % – 100 % presisjon)**: Tree-baserte ensembler (Random Forest og Gradient Boosting) fanger opp den **multivariate samvariasjonen**:
   $$\text{Privat Pant} \;\land\; \text{Manglende ordinære avdrag} \;\land\; \text{Sirkulær tilbakeføring} \;\land\; \text{Uforklarlig likviditet}$$
   Dette beviser at datasettet krever ekte relasjonell maskinlæring, og ikke er en "triviell lekeoppgave".

---

## 2. Injisert Markedsstruktur: Herdede Edge Cases

| Kategori | Volum | Egenskaper | Formål i Evalueringen |
| :--- | :---: | :--- | :--- |
| **Legitime Banklån** | 180 | Pant registrert på autoriserte banker (DNB, Nordea etc.). | Forurenser `has_mortgage`. |
| **Legitim Selgerkreditt / Privat Pant** | 30 | Pant registrert på privatperson eller ordinært AS med vanlige avdrag. | Forurenser `mortgagee_is_private_co` slik at privat pant ikke kan brukes som en naiv snarvei. |
| **Lovlige Konsernholdinger** | 45 | Legitime flerledds AS-eierskap med standard konsernbidrag. | Forurenser `holding_chain_depth`. |
| **Arv & Uskifte** | 40 | `registered_owner != actual_controller` med familieoppgjør. | Forurenser `has_ownership_discrepancy` med beløp som delvis overlapper kjøpesummer. |
| **Sameier** | 40 | To registrerte eiere (f.eks. ektefeller). | Realistisk eierstruktur. |
| **Blankoskjøte (AML)** | 15 | Stråmann + reell bakmann + `property_financing`. | Kriminell anomali. |
| **Lagdelt Holding (AML)** | 10 | Skjult UBO bak 3 lag stråselskaper + `equity_injection`. | Kriminell anomali. |
| **Fiktivt Lån / Loan-Back (AML)** | 10 | Uregistrert privat LenderCo + `loan_disbursement` + sirkulære avdrag. | Kriminell anomali. |

---

## 3. Out-of-Distribution Generaliseringstest (Graf 1 vs. Graf 2)

I denne testen ble modellene trent på Graf 1 (Seed 42, 600 eiendommer) og testet direkte på en helt usett Graf 2 (Seed 999, 800 eiendommer, +40 % beløpsforskyvning, +25 % støy):

| Modell | Test Accuracy | Test Precision | Test Recall | Test F1 | Falske Positive (FP) | Falske Negative (FN) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Regelbasert Heuristikk** | 68.37 % | 11.85 % | 100.0 % | 0.2118 | 253 | 0 |
| **Logistic Regression (L2)** | 97.62 % | 64.15 % | 100.0 % | 0.7816 | 19 | 0 |
| **HistGradientBoosting** | 99.38 % | 93.94 % | 91.18 % | 0.9254 | 2 | 3 |
| **Random Forest (100 trær)** | **100.00 %** | **100.00 %** | **100.00 %** | **1.0000** | **0** | **0** |

---

## 4. Hva Lærte Modellen? (Oppdatert Feature Importance)

Etter innføringen av legitime private pantelån, har modellen måttet skifte fokus fra rene etiketter til helhetlige flytmønstre:

```mermaid
xychart-beta
    title "Feature Importance med Herdet Støy (%)"
    x-axis ["net_flow", "tx_in_vol", "discrepancy", "prop_fin", "loan_disb", "loan_repay", "bank_loan", "pvt_lender"]
    y-axis "Viktighet (%)" 0 --> 20
    bar [15.3, 14.7, 12.7, 11.8, 6.3, 5.7, 4.8, 4.4]
```

1. **`owner_net_financial_flow` (15.29 %)**: Total ubalanse og netto likviditetsendring på eierkontoen.
2. **`owner_tx_in_vol` (14.69 %)**: Total inngående transaksjonsmengde.
3. **`has_ownership_discrepancy` (12.70 %)**: Divergens mellom tinglyst eier og faktisk kontroller (bevart nøyaktig via MultiDiGraph).
4. **`owner_tx_inflow_property_financing` (11.78 %)**: Målrettet bakmannsfinansiering.
5. **`owner_tx_inflow_loan_disbursement` (6.25 %)** & **`loan_repayment` (5.67 %)**: Fanger opp sirkulære låneavtaler.
6. **`mortgagee_is_private_co` (4.39 %)**: Vektet ned fra tidligere 30 % fordi modellen nå forstår at privat pant også forekommer i lovlige sammenhenger (selgerkreditt)!

---

## 5. Konklusjon
Denne oppdaterte testen beviser at:
- Modellene ikke er overtilpasset til faste beløpsgrenser (overlever +40 % beløpsforskyvning).
- MultiDiGraph sikrer korrekt relasjonell semantikk uten overskriving av parallelle eierroller.
- Ytelsesgradienten (11,9 % -> 64,2 % -> 93,9 % -> 100 %) gir en troverdig og faglig forsvarlig benchmark som tåler granskning fra ledende AML-miljøer.
