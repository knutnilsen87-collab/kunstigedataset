import csv
import random
import uuid
import os

class Config:
    NUM_PROPERTIES = 600
    NUM_PERSONS = 400
    NUM_COMPANIES = 120
    NUM_BANKS = 4
    
    # Kriminelle AML-scenarioer (Ground Truth)
    NUM_BLANKOSKJOETE = 15
    NUM_LAYERED_HOLDING = 10
    NUM_LOAN_BACK = 10
    
    # Legitime komplekse strukturer (Realistisk støy / Edge cases)
    NUM_LEGIT_BANK_MORTGAGES = 180       # Legitime boliglån fra banker
    NUM_LEGIT_HOLDING_CHAINS = 45        # Lovlige konsern/familieholdinger (AS bak AS)
    NUM_LEGIT_INHERITANCE_DISCREPANCIES = 35  # Arv/uskifte/sameie der tinglyst != faktisk bruker
    NUM_LEGIT_JOINT_OWNERSHIPS = 40      # Ektefeller / sameie med to eiere
    
    OUTPUT_DIR = "output"

class GraphGenerator:
    def __init__(self, config):
        self.config = config
        self.entities = []
        self.ownership_edges = []
        self.transactions = []
        self.scenarios = []
        self.ground_truth = []
        
        # System for å holde styr på balanse ("balance conservation")
        self.balances = {}
        self.initial_money = 0
        
    def _create_entity(self, entity_type, initial_funds=None):
        entity_id = str(uuid.uuid4())
        self.entities.append({"id": entity_id, "type": entity_type})
        
        if entity_type == 'property':
            self.balances[entity_id] = 0
        elif entity_type == 'bank':
            balance = initial_funds if initial_funds is not None else 500000000 # 500 MNOK
            self.balances[entity_id] = balance
            self.initial_money += balance
        else:
            balance = initial_funds if initial_funds is not None else random.randint(200000, 10000000)
            self.balances[entity_id] = balance
            self.initial_money += balance
            
        return entity_id
        
    def generate_base_graph(self):
        print("Genererer basis-graf (noder, banker og standard eierskap)...")
        self.properties = [self._create_entity("property") for _ in range(self.config.NUM_PROPERTIES)]
        self.persons = [self._create_entity("person") for _ in range(self.config.NUM_PERSONS)]
        self.companies = [self._create_entity("company") for _ in range(self.config.NUM_COMPANIES)]
        self.banks = [self._create_entity("bank") for _ in range(self.config.NUM_BANKS)]
        
        actors = self.persons + self.companies
        
        # 1. Tildel lovlig eierskap (hvor registrert eier = faktisk kontroller)
        for prop in self.properties:
            owner = random.choice(actors)
            self.ownership_edges.append({"source": owner, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": owner, "target": prop, "role": "actual_controller"})
            
        # 2. Generer vanlige selskapseierskap (legitime holdingstrukturer og datterselskaper)
        for comp in self.companies:
            parent = random.choice(actors)
            if parent != comp and random.random() < 0.35:
                self.ownership_edges.append({"source": parent, "target": comp, "role": "shareholder"})
            
        # 3. Generer standard støytransaksjoner mellom aktører
        print("Genererer vanlige transaksjoner...")
        for _ in range(self.config.NUM_PROPERTIES * 3):
            sender = random.choice(actors)
            receiver = random.choice(actors)
            if sender != receiver:
                amount = random.randint(1000, 50000)
                if self.balances[sender] >= amount:
                    self.balances[sender] -= amount
                    self.balances[receiver] += amount
                    self.transactions.append({
                        "id": str(uuid.uuid4()),
                        "sender": sender,
                        "receiver": receiver,
                        "amount": amount,
                        "type": "standard_transfer"
                    })

    # =========================================================================
    # LEGITIME KOMPLEKSE STRUKTURER (REALISTISK STØY - BENIGN NOISE)
    # =========================================================================

    def inject_legitimate_bank_mortgages(self):
        """
        Legitime boliglån fra autoriserte banker.
        Skaper 'mortgage_holder' kanter på ~30 % av eiendommene med ordinære bankrenter/avdrag.
        Dette forhindrer at modeller naivt klassifiserer alle pant som hvitvasking!
        """
        print(f"Legger til {self.config.NUM_LEGIT_BANK_MORTGAGES} legitime banklån...")
        sample_props = random.sample(self.properties, self.config.NUM_LEGIT_BANK_MORTGAGES)
        
        for prop in sample_props:
            bank = random.choice(self.banks)
            # Finn registrert eier
            reg_owners = [e["source"] for e in self.ownership_edges if e["target"] == prop and e["role"] == "registered_owner"]
            if not reg_owners:
                continue
            owner = reg_owners[0]
            
            # Legg til pantekant fra banken
            self.ownership_edges.append({"source": bank, "target": prop, "role": "mortgage_holder"})
            
            # Bank utbetaler ordinært boliglån
            loan_amt = random.randint(1500000, 6000000)
            if self.balances[bank] >= loan_amt:
                self.balances[bank] -= loan_amt
                self.balances[owner] += loan_amt
                self.transactions.append({
                    "id": str(uuid.uuid4()),
                    "sender": bank,
                    "receiver": owner,
                    "amount": loan_amt,
                    "type": "bank_loan_disbursement"
                })
                
                # Ordinære månedlige avdrag tilbake til banken
                installment = random.randint(10000, 30000)
                for _ in range(2):
                    if self.balances[owner] >= installment:
                        self.balances[owner] -= installment
                        self.balances[bank] += installment
                        self.transactions.append({
                            "id": str(uuid.uuid4()),
                            "sender": owner,
                            "receiver": bank,
                            "amount": installment,
                            "type": "bank_loan_installment"
                        })

    def inject_legitimate_holding_structures(self):
        """
        Legitime konsernstrukturer (AS som eier AS som eier eiendom).
        Helt lovlig, åpen eierkjede uten hemmelige bakmenn eller fiktiv kapital.
        """
        print(f"Legger til {self.config.NUM_LEGIT_HOLDING_CHAINS} legitime konsern- og holdingselskaper...")
        sample_props = random.sample(self.properties, self.config.NUM_LEGIT_HOLDING_CHAINS)
        
        for prop in sample_props:
            owner_person = random.choice(self.persons)
            holding_co = self._create_entity("company")
            prop_co = self._create_entity("company")
            
            # Fjern gammelt eierskap
            self.ownership_edges = [e for e in self.ownership_edges if e["target"] != prop]
            
            # Lovlig eierkjede
            self.ownership_edges.append({"source": owner_person, "target": holding_co, "role": "shareholder"})
            self.ownership_edges.append({"source": holding_co, "target": prop_co, "role": "shareholder"})
            self.ownership_edges.append({"source": prop_co, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": owner_person, "target": prop, "role": "actual_controller"})
            
            # Ordinært konsernbidrag
            transfer_amt = random.randint(500000, 2000000)
            if self.balances[holding_co] >= transfer_amt:
                self.balances[holding_co] -= transfer_amt
                self.balances[prop_co] += transfer_amt
                self.transactions.append({
                    "id": str(uuid.uuid4()),
                    "sender": holding_co,
                    "receiver": prop_co,
                    "amount": transfer_amt,
                    "type": "standard_transfer"
                })

    def inject_legitimate_inheritance_discrepancies(self):
        """
        Legitime divergenser mellom tinglyst og faktisk eier:
        - Arveoppgjør / uskifte / foreldre som står som tinglyst mens arving er faktisk bruker.
        - Ingen mistenkelig 'property_financing' fra kriminelle bakmenn.
        Dette tester false positive-raten til regelsjekker som bare sjekker registered != actual!
        """
        print(f"Legger til {self.config.NUM_LEGIT_INHERITANCE_DISCREPANCIES} legitime arve-/uskifteavvik...")
        sample_props = random.sample(self.properties, self.config.NUM_LEGIT_INHERITANCE_DISCREPANCIES)
        
        for prop in sample_props:
            parent = random.choice(self.persons)
            heir = random.choice(self.persons)
            if parent == heir:
                continue
                
            self.ownership_edges = [e for e in self.ownership_edges if e["target"] != prop]
            # Forelder/dødsbo står fortsatt tinglyst, men arving disponerer og kontrollerer
            self.ownership_edges.append({"source": parent, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": heir, "target": prop, "role": "actual_controller"})
            
            # Helt ordinær familietransaksjon (gebyr/gave/arveoppgjør)
            amount = random.randint(10000, 100000)
            if self.balances[heir] >= amount:
                self.balances[heir] -= amount
                self.balances[parent] += amount
                self.transactions.append({
                    "id": str(uuid.uuid4()),
                    "sender": heir,
                    "receiver": parent,
                    "amount": amount,
                    "type": "family_settlement"
                })

    def inject_legitimate_joint_ownerships(self):
        """
        Legitimt sameie: To registrerte eiere (f.eks. ektefeller).
        """
        print(f"Legger til {self.config.NUM_LEGIT_JOINT_OWNERSHIPS} legitime sameier...")
        sample_props = random.sample(self.properties, self.config.NUM_LEGIT_JOINT_OWNERSHIPS)
        
        for prop in sample_props:
            co_owner = random.choice(self.persons)
            self.ownership_edges.append({"source": co_owner, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": co_owner, "target": prop, "role": "actual_controller"})

    # =========================================================================
    # KRIMINELLE AML-SCENARIOER (GROUND TRUTH INJECTION)
    # =========================================================================

    def inject_blankoskjoete_scenarios(self):
        """
        Typology 1: Blankoskjøte (Illegitim stråmann)
        En stråmann er formelt registrert eier, men den reelle bakmannen er actual_controller.
        Bakmann overfører kjøpesum til stråmannen under type 'property_financing'.
        """
        print(f"Injisere {self.config.NUM_BLANKOSKJOETE} 'blankoskjøte' scenarioer...")
        actors = self.persons + self.companies
        
        for _ in range(self.config.NUM_BLANKOSKJOETE):
            prop = random.choice(self.properties)
            strawman = random.choice(actors)
            hidden_owner = random.choice(actors)
            
            if strawman == hidden_owner:
                continue
                
            self.ownership_edges = [e for e in self.ownership_edges if e["target"] != prop]
            self.ownership_edges.append({"source": strawman, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": hidden_owner, "target": prop, "role": "actual_controller"})
            
            amount = random.randint(2000000, 6000000)
            self.balances[hidden_owner] += amount
            self.initial_money += amount
            self.balances[hidden_owner] -= amount
            self.balances[strawman] += amount
            
            self.transactions.append({
                "id": str(uuid.uuid4()),
                "sender": hidden_owner,
                "receiver": strawman,
                "amount": amount,
                "type": "property_financing"
            })
            
            scenario_id = str(uuid.uuid4())
            self.scenarios.append({
                "scenario_id": scenario_id,
                "type": "blankoskjoete",
                "property": prop,
                "registered_owner": strawman,
                "actual_controller": hidden_owner,
                "details": f"Finansiert med {amount} NOK direkte til stråmann"
            })
            self.ground_truth.append({
                "scenario_id": scenario_id,
                "scenario_type": "blankoskjoete",
                "hidden_owner": hidden_owner,
                "strawman": strawman,
                "property": prop,
                "details": f"amount={amount}"
            })

    def inject_layered_holding_scenarios(self):
        """
        Typology 2: Lagdelte holdingselskaper (Kriminell Corporate Veil)
        En UBO gjemmer seg bak en kjede av stråselskaper (2-3 lag med AS).
        UBO -> Holding1 (AS) -> Holding2 (AS) -> PropCo (AS) -> Eiendom.
        Penger sluses ned som 'equity_injection'.
        """
        print(f"Injisere {self.config.NUM_LAYERED_HOLDING} kriminelle 'lagdelte holdingselskaper' scenarioer...")
        for _ in range(self.config.NUM_LAYERED_HOLDING):
            prop = random.choice(self.properties)
            ubo = random.choice(self.persons)
            
            holding1 = self._create_entity("company", initial_funds=0)
            holding2 = self._create_entity("company", initial_funds=0)
            prop_co = self._create_entity("company", initial_funds=0)
            
            self.ownership_edges = [e for e in self.ownership_edges if e["target"] != prop]
            
            self.ownership_edges.append({"source": ubo, "target": holding1, "role": "shareholder"})
            self.ownership_edges.append({"source": holding1, "target": holding2, "role": "shareholder"})
            self.ownership_edges.append({"source": holding2, "target": prop_co, "role": "shareholder"})
            self.ownership_edges.append({"source": prop_co, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": ubo, "target": prop, "role": "actual_controller"})
            
            equity_amount = random.randint(4000000, 12000000)
            self.balances[ubo] += equity_amount
            self.initial_money += equity_amount
            
            self.balances[ubo] -= equity_amount
            self.balances[holding1] += equity_amount
            self.transactions.append({
                "id": str(uuid.uuid4()),
                "sender": ubo,
                "receiver": holding1,
                "amount": equity_amount,
                "type": "equity_injection"
            })
            
            self.balances[holding1] -= equity_amount
            self.balances[holding2] += equity_amount
            self.transactions.append({
                "id": str(uuid.uuid4()),
                "sender": holding1,
                "receiver": holding2,
                "amount": equity_amount,
                "type": "equity_injection"
            })
            
            self.balances[holding2] -= equity_amount
            self.balances[prop_co] += equity_amount
            self.transactions.append({
                "id": str(uuid.uuid4()),
                "sender": holding2,
                "receiver": prop_co,
                "amount": equity_amount,
                "type": "equity_injection"
            })
            
            scenario_id = str(uuid.uuid4())
            chain_str = f"{ubo} -> {holding1} -> {holding2} -> {prop_co}"
            self.scenarios.append({
                "scenario_id": scenario_id,
                "type": "layered_holding",
                "property": prop,
                "registered_owner": prop_co,
                "actual_controller": ubo,
                "details": f"Holdingkjede: {chain_str}, kapital: {equity_amount} NOK"
            })
            self.ground_truth.append({
                "scenario_id": scenario_id,
                "scenario_type": "layered_holding",
                "hidden_owner": ubo,
                "strawman": prop_co,
                "property": prop,
                "details": f"chain={chain_str}, amount={equity_amount}"
            })

    def inject_loan_back_mortgage_scenarios(self):
        """
        Typology 3: Fiktivt lån / Third-party Mortgage Fraud (Loan-back scheme)
        En hemmelig bakmann kontrollerer et ugjennomsiktig utlånsselskap (LenderCo).
        LenderCo tildeler lån ('loan_disbursement') og tar pant ('mortgage_holder') i eiendommen.
        Låntaker betaler tilbake fiktive renter/avdrag ('loan_repayment') til LenderCo.
        """
        print(f"Injisere {self.config.NUM_LOAN_BACK} kriminelle 'fiktivt lån / loan-back' scenarioer...")
        for _ in range(self.config.NUM_LOAN_BACK):
            prop = random.choice(self.properties)
            hidden_mastermind = random.choice(self.persons)
            borrower = random.choice(self.persons)
            
            if hidden_mastermind == borrower:
                continue
                
            lender_co = self._create_entity("company", initial_funds=0)
            
            self.ownership_edges.append({"source": hidden_mastermind, "target": lender_co, "role": "actual_controller"})
            self.ownership_edges.append({"source": lender_co, "target": prop, "role": "mortgage_holder"})
            
            self.ownership_edges = [e for e in self.ownership_edges if e["target"] != prop or e["role"] == "mortgage_holder"]
            self.ownership_edges.append({"source": borrower, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": borrower, "target": prop, "role": "actual_controller"})
            
            loan_amount = random.randint(3000000, 8000000)
            self.balances[lender_co] += loan_amount
            self.initial_money += loan_amount
            
            self.balances[lender_co] -= loan_amount
            self.balances[borrower] += loan_amount
            self.transactions.append({
                "id": str(uuid.uuid4()),
                "sender": lender_co,
                "receiver": borrower,
                "amount": loan_amount,
                "type": "loan_disbursement"
            })
            
            installment = random.randint(150000, 400000)
            for _ in range(2):
                if self.balances[borrower] >= installment:
                    self.balances[borrower] -= installment
                    self.balances[lender_co] += installment
                    self.transactions.append({
                        "id": str(uuid.uuid4()),
                        "sender": borrower,
                        "receiver": lender_co,
                        "amount": installment,
                        "type": "loan_repayment"
                    })
                    
            scenario_id = str(uuid.uuid4())
            self.scenarios.append({
                "scenario_id": scenario_id,
                "type": "loan_back_mortgage",
                "property": prop,
                "registered_owner": borrower,
                "actual_controller": hidden_mastermind,
                "details": f"Långiver: {lender_co}, lån: {loan_amount} NOK"
            })
            self.ground_truth.append({
                "scenario_id": scenario_id,
                "scenario_type": "loan_back_mortgage",
                "hidden_owner": hidden_mastermind,
                "strawman": lender_co,
                "property": prop,
                "details": f"lender={lender_co}, borrower={borrower}, loan={loan_amount}"
            })

    def validate_balance_conservation(self):
        """
        Validerer at summen av penger på start-tidspunktet tilsvarer 
        summen av penger nå (pengesirkulasjonen er lukket).
        """
        print("Validerer balanse (balance conservation)...")
        current_money = sum(self.balances.values())
        if current_money == self.initial_money:
            print("OK Balance conservation validert: Ingen midler er tapt eller oppstatt ut av intet.")
            return True
        else:
            print(f"ADVARSEL: Balansefeil! Start: {self.initial_money}, Naa: {current_money}")
            return False
            
    def _write_csv(self, filename, data):
        if not data:
            return
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)

    def export_data(self):
        print(f"Eksporterer grafer til CSV i '{self.config.OUTPUT_DIR}' mappen...")
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        
        self._write_csv(f"{self.config.OUTPUT_DIR}/entities.csv", self.entities)
        self._write_csv(f"{self.config.OUTPUT_DIR}/ownership_edges.csv", self.ownership_edges)
        self._write_csv(f"{self.config.OUTPUT_DIR}/transactions.csv", self.transactions)
        self._write_csv(f"{self.config.OUTPUT_DIR}/scenarios.csv", self.scenarios)
        self._write_csv(f"{self.config.OUTPUT_DIR}/ground_truth.csv", self.ground_truth)
        
        print("Eksport ferdig! Filer klare for lasting til BigQuery/Dataflow.")

if __name__ == "__main__":
    config = Config()
    generator = GraphGenerator(config)
    
    generator.generate_base_graph()
    
    # 1. Legg til realistisk legitim støy
    generator.inject_legitimate_bank_mortgages()
    generator.inject_legitimate_holding_structures()
    generator.inject_legitimate_inheritance_discrepancies()
    generator.inject_legitimate_joint_ownerships()
    
    # 2. Injisere kriminelle hvitvaskingsmønstre (Ground Truth)
    generator.inject_blankoskjoete_scenarios()
    generator.inject_layered_holding_scenarios()
    generator.inject_loan_back_mortgage_scenarios()
    
    # 3. Verifiser matematisk balanse og eksporter
    generator.validate_balance_conservation()
    generator.export_data()
    print("Skriptet er ferdig kjørt med både legitime komplekse strukturer og AML-anomalier!")
