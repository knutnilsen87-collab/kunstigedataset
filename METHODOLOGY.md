# Nordic AML Graph Pack – Methodology & Technical Whitepaper
**Versjon**: 0.2 (Independent Multi-Seed Benchmark)  
**Formål**: Dokumentasjon av genereringsmetodikk, typologier, balansebevaring, nøytrale transaksjonstyper og benchmark for syntetiske AML-grafer innen eiendom og selskapsstrukturer.

---

## 1. Bakgrunn & Problemstilling

Hvitvasking gjennom eiendom og komplekse selskapsstrukturer er blant de mest krevende truslene i det nordiske finanssystemet (jf. Økokrims trusselvurderinger). Kriminelle aktører utnytter:
1. **Formell vs. reell kontroll**: Tinglyste eiere (stråmenn) som dekker over bakenforliggende reelle rettighetshavere.
2. **Lagdelte selskapsstrukturer ("Corporate Veil")**: Aksjeselskaper registrert i flere lag for å vanskeliggjøre innsyn i UBO (Ultimate Beneficial Owner).
3. **Uautoriserte låne- og pantestrukturer ("Loan-back scheme")**: Fiktive lån fra ugjennomsiktige selskaper som gir en lovlig fasade for løpende overføringer av ulovlige midler som "gjeldsbetjening".

Tradisjonelle compliance-systemer i banker er i stor grad basert på **flate tabeller og enkle IF/THEN-regler**. I et komplekst marked fører dette til massiv alarmtretthet: Over 80 % av regelflaggene er falske positive forårsaket av ordinære banklån, selgerkreditter, familiekonsern og arveoppgjør.

Dette datasettet er designet for å tilby **den første realistiske, flerlags graf-standarden** for trening og evaluering av neste generasjons AML-modeller uten leksikalsk datalekkasje.

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
[ Finansielt lag ]   Pengeoverføringer, Lån, Pant (mortgage_holder) og Egenkapital
```

### Entiteter (`entities.csv`)
- **`person`**: Fysiske personer (vanlige samfunnsborgere, stråmenn og bakmenn).
- **`company`**: Aksjeselskaper (driftsselskaper, holdingselskaper og stråselskaper).
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
- **Ingen penger oppstår eller forsvinner** i noen del av kretsløpet, noe som muliggjør avansert flyt- og likviditetsanalyse.

---

## 4. Kriminelle Typologier & Nøytrale Transaksjonstyper

For å forhindre at maskinlæringsmodeller tar leksikalske snarveier på etikettnavn, benytter alle transaksjoner universelle, standardiserte typer:

| Transaksjonstype | Brukes i Kriminelle Scenarioer | Brukes i Legitime Strukturer |
| :--- | :--- | :--- |
| **`transfer`** | Kjøpsfinansiering ved blankoskjøte | Ordinære oppgjør, arveoppgjør, kontooverføringer |
| **`capital_contribution`** | Kapitaltilførsel i kriminell holdingkjede | Ordinære konsernbidrag og aksjekapital |
| **`loan_disbursement`** | Utbetaling fra fiktivt utlånsselskap | Boliglån fra bank, privat selgerkreditt |
| **`loan_installment`** | Renter/avdrag tilbake til bakmann | Månedlige bankavdrag, private låneavdrag |

### Typologi 1: Blankoskjøte (`blankoskjoete`)
- **Mekanisme**: En stråmann oppføres som tinglyst eier (`registered_owner`), mens bakmannen registreres som `actual_controller`.
- **Kapitalflyt**: Bakmannen overfører kjøpesummen via nøytral `transfer` direkte til stråmannen.

### Typologi 2: Lagdelte holdingselskaper (`layered_holding`)
- **Mekanisme**: En reell rettighetshaver (UBO) etablerer 3 lag med holdingselskaper:
  $$\text{UBO} \xrightarrow{\text{shareholder}} \text{Holding 1} \xrightarrow{\text{shareholder}} \text{Holding 2} \xrightarrow{\text{shareholder}} \text{PropCo} \xrightarrow{\text{registered\_owner}} \text{Eiendom}$$
- **Kapitalflyt**: Bakmannen sluser ulovlig kapital nedover i kjeden som `capital_contribution` gjennom hvert ledd.

### Typologi 3: Fiktivt pantelån / Loan-Back Scheme (`loan_back_mortgage`)
- **Mekanisme**: Bakmannen kontrollerer et ugjennomsiktig utlånsselskap (`LenderCo`) som tar pant (`mortgage_holder`) i eiendommen.
- **Kapitalflyt**: `LenderCo` utbetaler en lånesum via `loan_disbursement`, og kjøper betaler deretter månedlige avdrag via `loan_installment` tilbake til `LenderCo`.

---

## 5. Legitim Støy & Benigne Komplekse Strukturer

For å unngå urealistisk "renhet" er datasettet beriket med fem kategorier lovlig kompleksitet som normalt trigger falske alarmer i tradisjonelle systemer:

| Benign Støytype | Volum | Egenskaper | Formål i Evalueringen |
| :--- | :---: | :--- | :--- |
| **Legitime Banklån** | 180 | Pant registrert på autoriserte banker; ordinære låneavdrag. | Hindrer at modeller naivt stempler all pantsetting som mistenkelig. |
| **Legitim Selgerkreditt / Privat Pant** | 30 | Lån fra privatpersoner eller selskaper med pant og avdrag. | Forurenser privat pant og tvinger fram helhetlig relasjonsanalyse. |
| **Lovlige Konsernholdinger** | 45 | Legitime flerledds AS-eierskap med standard konsernbidrag. | Hindrer at selskapsdybde alene utløser alarm. |
| **Arveoppgjør & Uskifte** | 40 | `registered_owner != actual_controller` pga. dødsbo/arving (`transfer`). | Hindrer at eierskapsavvik alene flagges som blankoskjøte. |
| **Sameier** | 40 | Ektefeller og partnere med felles registrert eierskap. | Realistisk eierkonstellasjon. |

---

## 6. Evalueringsresultater: Benchmark v0.2 Independent Validation

Evaluert ved å trene på Graf 1 (Seed 42, 600 eiendommer) og teste blindt på **4 uavhengige test-grafer** (Seed 101, 202, 555, 999) med opptil +60 % beløpsforskyvning og +30 % økt støy:

```
                              Test Presisjon (Mean ± Std)    Test Recall      Falske Positive (FP)
Regelbasert Heuristikk:             20.03 % ± 0.75 %          100.00 %            140.0 ± 6.5
Logistic Regression (L2):           73.02 % ± 4.08 %           93.57 %             12.2 ± 2.6
HistGradientBoosting:               66.91 % ± 5.03 %           99.29 %             17.5 ± 4.0
Random Forest (100 trær):           75.22 % ± 5.87 %           99.29 %             11.8 ± 3.5
```

### Nøkkelforbedringer i Benchmark v0.2:
1. **3.75x Presisjonsløft**: Maskinlæring kutter de falske alarmene med over **91.5 %** (fra 140 ned til under 12), samtidig som **99.3 % recall** opprettholdes.
2. **Ingen leksikalske snarveier**: Modellene lærer genuint samspill mellom grafdybde, relasjoner mellom panthaver og bakmann, og kontantstrømforhold.
3. **Statistisk robusthet**: Testet og verifisert over multiple uavhengige testfrø med målt varians.

---

## 7. Leveranseformater & Skyintegrasjon

Datasettet er fullt interoperabelt med moderne data warehousing og grafdatabaser:
- **Flate formater**: CSV og Parquet med typesikre kolonner.
- **Google Cloud BigQuery**:
  * Ferdig definert `PROPERTY GRAPH` (`aml_network_graph`) med støtte for ISO/GoogleSQL GQL (`GRAPH_TABLE`).
  * Produksjonstestede analytiske SQL-views (`v_detected_blankoskjoete`, `v_entity_risk_summary`, `v_aml_master_alerts`).
  * Verifisert i `datsetsyntetisk.aml_synth` (europe-west1).
- **Skalerbarhet**: Distribuert PySpark-arkitektur (`spark_generator.py`) for generering av 100 000+ noder på Google Cloud Dataproc.

---
*Nordic AML Graph Pack er utviklet for profesjonell testing og benchmarking av finansiell overvåking og regtech-løsninger.*
