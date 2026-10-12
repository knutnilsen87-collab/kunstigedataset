# Nordic AML Graph Pack – Methodology & Technical Whitepaper
**Versjon**: 0.1  
**Formål**: Dokumentasjon av genereringsmetodikk, typologier, balansebevaring og benchmark for syntetiske AML-grafer innen eiendom og selskapsstrukturer.

---

## 1. Bakgrunn & Problemstilling

Hvitvasking gjennom eiendom og komplekse selskapsstrukturer er blant de mest krevende truslene i det nordiske finanssystemet (jf. Økokrims trusselvurderinger). Kriminelle aktører utnytter:
1. **Formell vs. reell kontroll**: Tinglyste eiere (stråmenn) som dekker over bakenforliggende reelle rettighetshavere.
2. **Lagdelte selskapsstrukturer ("Corporate Veil")**: Aksjeselskaper registrert i flere lag for å vanskeliggjøre innsyn i UBO (Ultimate Beneficial Owner).
3. **Uautoriserte låne- og pantestrukturer ("Loan-back scheme")**: Fiktive lån fra ugjennomsiktige selskaper som gir en lovlig fasade for løpende overføringer av ulovlige midler som "gjeldsbetjening".

Tradisjonelle compliance-systemer i banker er i stor grad basert på **flate tabeller og enkle IF/THEN-regler**. I et komplekst marked fører dette til massiv alarmtretthet: Over 85 % av regelflaggene er falske positive forårsaket av ordinære banklån, familiekonsern og arveoppgjør.

Dette datasettet er designet for å tilby **den første realistiske, flerlags graf-standarden** for trening og evaluering av neste generasjons AML-modeller.

---

## 2. Arkitektur: Multilags Nettverksmodell

Datasettet modellerer det finansielle og juridiske økosystemet som en sammensatt, rettet multilagsgraf bestående av fire sammenvevde lag:

```
[ Entitetslag ]      Personer, Selskaper, Autoriserte Banker, Eiendommer
       │
[ Eierskapslag ]     registered_owner  (Tinglyst / formelt eierskap)
       │
[ Kontroll-lag ]     actual_controller (Reell råderett / UBO)
       │
[ Finansielt lag ]   Pengeoverføringer, Lån, Pant (mortgage_holder) og Utbytter
```

### Entiteter (`entities.csv`)
- **`person`**: Fysiske personer (både vanlige samfunnsborgere, stråmenn og kriminelle bakmenn).
- **`company`**: Aksjeselskaper (ordinære driftsselskaper, holdingselskaper og stråselskaper).
- **`bank`**: Autoriserte finansforetak under finanstilsyn.
- **`property`**: Faste eiendommer.

### Knytninger (`ownership_edges.csv`)
- **`registered_owner`**: Formelt tinglyst eier av eiendommen.
- **`actual_controller`**: Den reelle rettighetshaveren som disponerer eiendommen.
- **`shareholder`**: Aksjonærforhold i aksjeselskap (muliggjør vilkårlig dype holdingkjeder).
- **`mortgage_holder`**: Panthaver med tinglyst pant i eiendommen.

---

## 3. Matematisk Balansekonservering (Zero-Leakage Conservation)

I mange syntetiske datasett oppstår penger ut av intet ved hver transaksjon, noe som ødelegger realistiske regnskaps- og likviditetsanalyser. 

I dette datasettet håndheves **streng matematisk balansekonservering**:
$$\sum_{e \in \text{Entities}} \text{Balance}_t(e) = \sum_{e \in \text{Entities}} \text{Balance}_0(e) = \text{Konstant}$$

- Hver transaksjon $T = (s, r, a)$ trekker nøyaktig beløp $a$ fra avsender $s$ og krediterer mottaker $r$.
- Eiendommer har null likviditetsbalanse ($\text{Balance}(\text{prop}) = 0$).
- Alle kriminelle og legitime kapitalinjeksjoner (egenkapital, lån, bankkreditt) bokføres eksplisitt som innskudd ved simuleringsstart.
- **Ingen penger oppstår eller forsvinner** i noen del av kretsløpet, noe som muliggjør avansert flyt- og nettverksanalyse (Net Cash Flow Analysis).

---

## 4. Kriminelle Typologier (Ground Truth)

Datasettet inneholder tre distinkte og empirisk forankrede hvitvaskingstypologier:

### Typologi 1: Blankoskjøte (`blankoskjoete`)
- **Mekanisme**: En stråmann oppføres som tinglyst eier (`registered_owner`), mens bakmannen registreres som `actual_controller`.
- **Kapitalflyt**: Bakmannen overfører kjøpesummen (`property_financing`, 2–6 MNOK) direkte til stråmannen i forkant av overdragelsen.

### Typologi 2: Lagdelte holdingselskaper (`layered_holding`)
- **Mekanisme**: En reell rettighetshaver (UBO) etablerer 2–3 lag med holdingselskaper:
  $$\text{UBO} \xrightarrow{\text{shareholder}} \text{Holding 1} \xrightarrow{\text{shareholder}} \text{Holding 2} \xrightarrow{\text{shareholder}} \text{PropCo} \xrightarrow{\text{registered\_owner}} \text{Eiendom}$$
- **Kapitalflyt**: Bakmannen sluser ulovlig kapital nedover i kjeden som `equity_injection` gjennom hvert ledd.

### Typologi 3: Fiktivt pantelån / Loan-Back Scheme (`loan_back_mortgage`)
- **Mekanisme**: Bakmannen oppretter og kontrollerer et ugjennomsiktig utlånsselskap (`LenderCo`). `LenderCo` tar pant (`mortgage_holder`) i eiendommen.
- **Kapitalflyt**:
  1. `LenderCo` utbetaler en lånesum (`loan_disbursement`, 3–8 MNOK) til boligkjøper.
  2. Kjøper betaler deretter månedlige "renter og avdrag" (`loan_repayment`) tilbake til `LenderCo`.
  3. Dette gir bakmannen en tilsynelatende legitim begrunnelse for å tømme midler ut av landet under dekke av gjeldsbetjening.

---

## 5. Legitim Støy & Benigne Komplekse Strukturer

For å unngå urealistisk "renhet" er datasettet beriket med fire kategorier lovlig kompleksitet som normalt trigger falske alarmer i tradisjonelle systemer:

| Benign Støytype | Volum | Egenskaper | Formål i Evalueringen |
| :--- | :---: | :--- | :--- |
| **Legitime Banklån** | 180 | Pant registrert på autoriserte banker; ordinære låneavdrag. | Hindrer at modeller naivt stempler all pantsetting som mistenkelig. |
| **Lovlige Konsernholdinger** | 45 | Legitime flerledds AS-eierskap med standard konsernbidrag. | Hindrer at selskapsdybde alene utløser alarm. |
| **Arveoppgjør & Uskifte** | 35 | `registered_owner != actual_controller` pga. dødsbo/arving, uten mistenkelig finansiering. | Hindrer at eierskapsavvik alene flagges som blankoskjøte. |
| **Sameier** | 40 | Ektefeller og partnere med felles registrert eierskap. | Realistisk eierkonstellasjon. |

---

## 6. Evalueringsresultater: Hvorfor Graf-Features Knuser Enkle Regler

Datasettet ble evaluert med et **uavhengig 70/30 Stratified Holdout Testsett (180 eiendommer)**:

```
                          Presisjon     Recall     Falske Positive (FP)
Regelbasert Heuristikk:     13.7 %      100.0 %            63
Graf-ML (Logistic Reg):     90.9 %      100.0 %             1
Graf-ML (Random Forest):    90.0 %       90.0 %             1
```

### Hovedforklaring (Feature Importance):
1. **`mortgagee_is_private_co` (29.97 %)**: Skiller lån fra autoriserte banker fra lån utstedt av ugjennomsiktige private selskaper.
2. **`owner_tx_in_vol` (12.64 %)** & **`owner_net_financial_flow` (12.39 %)**: Fanger opp unormale likviditetsbølger i tilknytning til eiendomstransaksjonen.
3. **`owner_pagerank` (8.20 %)**: Avslører sentralitet og hub-strukturer i selskapsgrafen.

---

## 7. Leveranseformater & Skyintegrasjon

Datasettet er fullt interoperabelt med moderne data warehousing og grafdatabaser:
- **Flate formater**: CSV og Parquet med typesikre kolonner.
- **Google Cloud BigQuery**:
  * Ferdig definert `PROPERTY GRAPH` (`aml_network_graph`) med støtte for ISO/GoogleSQL GQL (`GRAPH_TABLE`).
  * Produksjonstestede rekursive SQL-views (`v_aml_master_alerts`, `v_entity_risk_summary`).
- **Skalerbarhet**: Distribuert PySpark-arkitektur for generering av 100 000+ noder på Google Cloud Dataproc.

---
*Nordic AML Graph Pack er utviklet for profesjonell testing og benchmarking av finansiell overvåking og regtech-løsninger.*
