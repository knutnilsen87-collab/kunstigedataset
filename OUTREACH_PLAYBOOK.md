# Nordic AML Graph Pack – Outreach Playbook & Valideringsstrategi

Dette dokumentet inneholder konkrete outreach-maler, målgruppeprofiler og en oppfølgingsstrategi for å validere **Nordic AML Graph Pack v0.1** mot 3–5 nordiske nøkkelpersoner innen regtech, AML og finansiell overvåking.

---

## 1. Målgruppe & Mottakerprofiler

Målet er ikke å "kaldselge", men å be om en faglig vurdering fra folk som kjenner smerten med **alarmtretthet og regelbasert støy**:

| Kategori | Eksempler på Selskaper / Miljøer | Relevante Stillinger / Roller |
| :--- | :--- | :--- |
| **Nordiske Regtech & AML-startups** | **Strise**, **Trapets**, **Lucinity**, **Finterai** | Head of AML / Product Lead, Lead Data Scientist, Founder / CTO |
| **Storbanker (Financial Crime / AML)** | **DNB** (Financial Cybercrime Centre / AML Tech), **Nordea**, **SpareBank 1**, **SEB** | Head of Transaction Monitoring, Lead AML Analyst, ML Engineer AML |
| **Konsulentselskaper (Forensics & AML)** | **PwC Forensics**, **EY Financial Crime**, **KPMG Risk** | Senior Manager AML, Partner Forensics & AML Tech |

---

## 2. Outreach-Maler

### Mal A: LinkedIn / Kort InMail (Maks 6–8 linjer)
> **Emne / Åpning:** Syntetisk testsett for eiendomshvitvasking (Økokrim-typologier)  
>  
> Hei [Navn],  
>  
> Jeg har fulgt med på arbeidet dere gjør innen [f.eks. AML / transaksjonsovervåking].  
>  
> Vi har nylig bygget et syntetisk, multilags grafdatasett for eiendomshvitvasking (*Nordic AML Graph Pack v0.1*). Det simulerer typologier fra Økokrim (blankoskjøte, 3-lags holdingselskaper og loan-back lån) med 100 % matematisk balansekonservering og realistisk bankstøy.  
>  
> På et testsett kollapset en naiv regelsjekk med 63 falske alarmer (13,7 % presisjon), mens en enkel graf-ML-modell opprettholder 90 %+ presisjon ved å skille bankpant fra stråselskaper.  
>  
> Vi har pakket en åpen 15-minutters evalueringspakke (med ground truth, BigQuery-views og ML-baseline):  
> 👉 https://github.com/knutnilsen87-collab/kunstigedataset  
>  
> Hadde du hatt 5 minutter til å kaste et blikk på metodikken (`METHODOLOGY.md`)? Ville satt stor pris på din ærlige mening om hvorvidt dette treffer de faktiske utfordringene dere ser i markedet.  
>  
> Beste hilsen,  
> Knut Nilsen

---

### Mal B: E-post (Formell & Innsiktsdrevet)
> **Emne:** Spørsmål om syntetiske grafdata for AML-evaluering / Økokrim-typologier  
>  
> Hei [Navn],  
>  
> Jeg tar kontakt fordi du har solid erfaring med [transaksjonsovervåking / AML-analyse i Norden].  
>  
> Mange AML-team sliter med at tradisjonelle regelsystemer kveles av falske positive når de møter komplekse, men legitime selskapsstrukturer og boliglån.  
>  
> For å teste dette i kontrollerte former har vi utviklet et åpent syntetisk grafdatasett: **Nordic AML Graph Pack v0.1**.  
>  
> **Kjernen i datasettet:**
> 1. **Tre Økokrim-typologier**: Blankoskjøte, lagdelte holdingselskaper (Corporate Veil) og sirkulære pantelån (Loan-back scheme).
> 2. **Realistisk støy**: 180 ordinære banklån, arveoppgjør og lovlige konsern for å stressteste falske positive.
> 3. **Bevist presisjonsløft**: Vår benchmark viser at graf-features reduserer falske alarmer fra 63 ned til 1 sammenlignet med tradisjonelle regelsjekker (6.6x presisjonsløft).
>  
> Hele testpakken med metodikknotat, fasit (`ground_truth.csv`), BigQuery Property Graph-spørringer og ML-pipeline ligger fritt tilgjengelig her:  
> https://github.com/knutnilsen87-collab/kunstigedataset  
>  
> Er dette et problem dere kjenner igjen fra hverdagen? Jeg setter enormt stor pris på en kort tilbakemelding på om dette har verdi for evaluering eller modelltrening hos dere.  
>  
> Mvh,  
> Knut Nilsen  
> knutnilsen87@gmail.com

---

## 3. Innsiktsmål under samtalene (Hva du vil lære)

Når du får svar, er målet å avdekke:
1. **Typologidekning**: Er blankoskjøte, lagdelte AS og loan-back de tre viktigste mønstrene for dem akkurat nå, eller etterspør de andre ting (f.eks. handelsbasert hvitvasking eller krypto-offramps)?
2. **Databehov**: Trenger de rå CSV/Parquet-filer, direkte BigQuery-tabeller, eller et ferdig API?
3. **Volum**: Er 1 000–5 000 noder tilstrekkelig for konsepttesting, eller krever de 100k–1M noder før det er relevant for en pilot?
4. **Betalingsvilje**: Ville de vurdert en betalt lisens for et kontinuerlig oppdatert benchmark-sett, eller en skreddersydd syntetiseringskjøring?
