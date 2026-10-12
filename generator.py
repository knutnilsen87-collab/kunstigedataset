import csv
import random
import uuid
import os

class Config:
    NUM_PROPERTIES = 600
    NUM_PERSONS = 400
    NUM_COMPANIES = 120
    NUM_BANKS = 4
    AMOUNT_SHIFT = 1.0  # Faktor for forskyvning av transaksjonsstørrelser
    
    # Kriminelle AML-scenarioer (Ground Truth)
    NUM_BLANKOSKJOETE = 15
    NUM_LAYERED_HOLDING = 10
    NUM_LOAN_BACK = 10
    
    # Legitime komplekse strukturer (Realistisk støy / Hard Edge Cases)
    NUM_LEGIT_BANK_MORTGAGES = 180           # Legitime boliglån fra banker
    NUM_LEGIT_PRIVATE_MORTGAGES = 30        # Legitim selgerkreditt / privatlån med pant (forurenser privat pant!)
    NUM_LEGIT_HOLDING_CHAINS = 45            # Lovlige konsern/familieholdinger (AS bak AS)
    NUM_LEGIT_INHERITANCE_DISCREPANCIES = 40 # Arv/uskifte/sameie der tinglyst != faktisk bruker
    NUM_LEGIT_JOINT_OWNERSHIPS = 40          # Ektefeller / sameie med to eiere
    
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
            balance = initial_funds if initial_funds is not None else int(500000000 * self.config.AMOUNT_SHIFT)
            self.balances[entity_id] = balance
            self.initial_money += balance
        else:
            base_funds = initial_funds if initial_funds is not None else random.randint(200000, 10000000)
            balance = int(base_funds * self.config.AMOUNT_SHIFT)
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
                amount = int(random.randint(1000, 50000) * self.config.AMOUNT_SHIFT)
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
        """
        print(f"Legger til {self.config.NUM_LEGIT_BANK_MORTGAGES} legitime banklån...")
        sample_props = random.sample(self.properties, self.config.NUM_LEGIT_BANK_MORTGAGES)
        
        for prop in sample_props:
            bank = random.choice(self.banks)
            reg_owners = [e["source"] for e in self.ownership_edges if e["target"] == prop and e["role"] == "registered_owner"]
            if not reg_owners:
                continue
            owner = reg_owners[0]
            
            self.ownership_edges.append({"source": bank, "target": prop, "role": "mortgage_holder"})
            
            loan_amt = int(random.randint(1500000, 6000000) * self.config.AMOUNT_SHIFT)
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
                
                installment = int(random.randint(10000, 30000) * self.config.AMOUNT_SHIFT)
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

    def inject_legitimate_private_mortgages(self):
        """
        Legitim selgerkreditt eller privat pantelån (fra privatperson eller ordinært selskap).
        Dette forurenser featuren 'mortgagee_is_private_co', slik at modellen må lære
        å skille legitime private lån fra kriminelle loan-back sirkler!
        """
        print(f"Legger til {self.config.NUM_LEGIT_PRIVATE_MORTGAGES} legitime private pantelån (selgerkreditt)...")
        # Velg eiendommer som ikke allerede har kriminelt pant
        available = [p for p in self.properties if not any(e["target"] == p and e["role"] == "mortgage_holder" for e in self.ownership_edges)]
        sample_props = random.sample(available, min(len(available), self.config.NUM_LEGIT_PRIVATE_MORTGAGES))
        
        actors = self.persons + self.companies
        for prop in sample_props:
            reg_owners = [e["source"] for e in self.ownership_edges if e["target"] == prop and e["role"] == "registered_owner"]
            if not reg_owners:
                continue
            borrower = reg_owners[0]
            
            # Legitim privat kredittyter (f.eks. tidligere eier eller forelder)
            lender = random.choice([a for a in actors if a != borrower])
            
            self.ownership_edges.append({"source": lender, "target": prop, "role": "mortgage_holder"})
            
            loan_amt = int(random.randint(500000, 2500000) * self.config.AMOUNT_SHIFT)
            if self.balances[lender] >= loan_amt:
                self.balances[lender] -= loan_amt
                self.balances[borrower] += loan_amt
                self.transactions.append({
                    "id": str(uuid.uuid4()),
                    "sender": lender,
                    "receiver": borrower,
                    "amount": loan_amt,
                    "type": "private_loan_disbursement"
                })
                
                installment = int(random.randint(15000, 45000) * self.config.AMOUNT_SHIFT)
                for _ in range(2):
                    if self.balances[borrower] >= installment:
                        self.balances[borrower] -= installment
                        self.balances[lender] += installment
                        self.transactions.append({
                            "id": str(uuid.uuid4()),
                            "sender": borrower,
                            "receiver": lender,
                            "amount": installment,
                            "type": "private_loan_installment"
                        })

    def inject_legitimate_holding_structures(self):
        """
        Legitime konsernstrukturer (AS som eier AS som eier eiendom).
        """
        print(f"Legger til {self.config.NUM_LEGIT_HOLDING_CHAINS} legitime konsern- og holdingselskaper...")
        sample_props = random.sample(self.properties, self.config.NUM_LEGIT_HOLDING_CHAINS)
        
        for prop in sample_props:
            owner_person = random.choice(self.persons)
            holding_co = self._create_entity("company")
            prop_co = self._create_entity("company")
            
            self.ownership_edges = [e for e in self.ownership_edges if e["target"] != prop]
            
            self.ownership_edges.append({"source": owner_person, "target": holding_co, "role": "shareholder"})
            self.ownership_edges.append({"source": holding_co, "target": prop_co, "role": "shareholder"})
            self.ownership_edges.append({"source": prop_co, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": owner_person, "target": prop, "role": "actual_controller"})
            
            transfer_amt = int(random.randint(500000, 2000000) * self.config.AMOUNT_SHIFT)
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
        Legitime divergenser mellom tinglyst og faktisk eier (Arv/uskifte).
        """
        print(f"Legger til {self.config.NUM_LEGIT_INHERITANCE_DISCREPANCIES} legitime arve-/uskifteavvik...")
        sample_props = random.sample(self.properties, self.config.NUM_LEGIT_INHERITANCE_DISCREPANCIES)
        
        for prop in sample_props:
            parent = random.choice(self.persons)
            heir = random.choice(self.persons)
            if parent == heir:
                continue
                
            self.ownership_edges = [e for e in self.ownership_edges if e["target"] != prop]
            self.ownership_edges.append({"source": parent, "target": prop, "role": "registered_owner"})
            self.ownership_edges.append({"source": heir, "target": prop, "role": "actual_controller"})
            
            # Arveoppgjør eller familieoverføring med beløp som delvis overlapper med kjøp
            amount = int(random.randint(50000, 1500000) * self.config.AMOUNT_SHIFT)
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
        Legitimt sameie: To registrerte eiere.
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
            
            amount = int(random.randint(2000000, 6000000) * self.config.AMOUNT_SHIFT)
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
            
            equity_amount = int(random.randint(4000000, 12000000) * self.config.AMOUNT_SHIFT)
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
            
            loan_amount = int(random.randint(3000000, 8000000) * self.config.AMOUNT_SHIFT)
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
            
            installment = int(random.randint(150000, 400000) * self.config.AMOUNT_SHIFT)
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
        print("Validerer balanse (balance conservation)...")
        current_money = sum(self.balances.values())
        if current_money == self.initial_money:
            print("OK Balance conservation validert: Ingen midler er tapt eller oppstått ut av intet.")
            return True
        else:
            print(f"ADVARSEL: Balansefeil! Start: {self.initial_money}, Nå: {current_money}")
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
    generator.inject_legitimate_bank_mortgages()
    generator.inject_legitimate_private_mortgages()
    generator.inject_legitimate_holding_structures()
    generator.inject_legitimate_inheritance_discrepancies()
    generator.inject_legitimate_joint_ownerships()
    
    generator.inject_blankoskjoete_scenarios()
    generator.inject_layered_holding_scenarios()
    generator.inject_loan_back_mortgage_scenarios()
    
    generator.validate_balance_conservation()
    generator.export_data()
    print("Skriptet er ferdig kjørt med herdede testmønstre og private lån!")
