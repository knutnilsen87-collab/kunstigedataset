"""
Cross-Graph Generalization & Out-of-Distribution Validation Test
Tester om ML-modellen trent på én syntetisk graf generaliserer til en helt uavhengig
graf generert med andre parametere, endret støy-distribusjon og andre tilfeldighetsfrø (seeds).
Dette adresserer direkte risikoen for 'generator overfitting'.
"""

import random
import numpy as np
import networkx as nx
from collections import defaultdict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

from generator import Config, GraphGenerator

def generate_graph_dataset(seed, num_properties=600, noise_factor=1.0, amount_shift=1.0):
    random.seed(seed)
    np.random.seed(seed)
    
    cfg = Config()
    cfg.NUM_PROPERTIES = num_properties
    cfg.NUM_PERSONS = int(400 * noise_factor)
    cfg.NUM_COMPANIES = int(120 * noise_factor)
    cfg.OUTPUT_DIR = f"output_test_seed_{seed}"
    
    gen = GraphGenerator(cfg)
    gen.generate_base_graph()
    gen.inject_legitimate_bank_mortgages()
    gen.inject_legitimate_holding_structures()
    gen.inject_legitimate_inheritance_discrepancies()
    gen.inject_legitimate_joint_ownerships()
    gen.inject_blankoskjoete_scenarios()
    gen.inject_layered_holding_scenarios()
    gen.inject_loan_back_mortgage_scenarios()
    
    assert gen.validate_balance_conservation(), "Balansekonservering feilet!"
    return gen.entities, gen.ownership_edges, gen.transactions, gen.ground_truth

def extract_features_from_graph(entities, ownership_edges, transactions, ground_truth):
    G_own = nx.DiGraph()
    for e in entities:
        G_own.add_node(e["id"], entity_type=e["type"])
    for oe in ownership_edges:
        G_own.add_edge(oe["source"], oe["target"], role=oe["role"])
        
    pagerank = nx.pagerank(G_own, alpha=0.85, max_iter=200)
    gt_map = {gt["property"]: gt for gt in ground_truth}
    
    tx_in_volume = defaultdict(float)
    tx_out_volume = defaultdict(float)
    tx_by_type_in = defaultdict(lambda: defaultdict(float))
    tx_by_type_out = defaultdict(lambda: defaultdict(float))
    
    for tx in transactions:
        s, r, amt, t_type = tx["sender"], tx["receiver"], float(tx["amount"]), tx["type"]
        tx_out_volume[s] += amt
        tx_in_volume[r] += amt
        tx_by_type_out[s][t_type] += amt
        tx_by_type_in[r][t_type] += amt
        
    def get_holding_depth(node, visited=None):
        if visited is None:
            visited = set()
        if node in visited:
            return 0
        visited.add(node)
        parents = [u for u, v, d in G_own.in_edges(node, data=True) if d.get("role") == "shareholder"]
        if not parents:
            return 0
        return 1 + max(get_holding_depth(p, visited.copy()) for p in parents)
        
    properties = [e["id"] for e in entities if e["type"] == "property"]
    X, y, y_typology = [], [], []
    
    for prop in properties:
        in_edges = G_own.in_edges(prop, data=True)
        reg_owners = [u for u, v, d in in_edges if d.get("role") == "registered_owner"]
        act_controllers = [u for u, v, d in in_edges if d.get("role") == "actual_controller"]
        mortgagees = [u for u, v, d in in_edges if d.get("role") == "mortgage_holder"]
        
        reg_owner = reg_owners[0] if reg_owners else None
        act_ctrl = act_controllers[0] if act_controllers else None
        
        has_discrepancy = 1 if (reg_owner and act_ctrl and reg_owner != act_ctrl) else 0
        owner_type = G_own.nodes.get(reg_owner, {}).get("entity_type", "person") if reg_owner else "person"
        is_company = 1 if owner_type == "company" else 0
        has_mortgage = 1 if len(mortgagees) > 0 else 0
        
        mortgagee_types = [G_own.nodes.get(m, {}).get("entity_type", "company") for m in mortgagees]
        mortgagee_is_bank = 1 if any(t == "bank" for t in mortgagee_types) else 0
        mortgagee_is_priv = 1 if any(t in ["company", "person"] for t in mortgagee_types) else 0
        
        chain_depth = get_holding_depth(reg_owner) if reg_owner else 0
        o_pr = pagerank.get(reg_owner, 0.0) if reg_owner else 0.0
        o_in_deg = G_own.in_degree(reg_owner) if reg_owner else 0
        o_out_deg = G_own.out_degree(reg_owner) if reg_owner else 0
        
        tx_in = tx_in_volume[reg_owner]
        tx_out = tx_out_volume[reg_owner]
        prop_fin = tx_by_type_in[reg_owner]["property_financing"]
        eq_inj = tx_by_type_in[reg_owner]["equity_injection"]
        loan_disb = tx_by_type_in[reg_owner]["loan_disbursement"]
        loan_repay = tx_by_type_out[reg_owner]["loan_repayment"]
        bank_loan = tx_by_type_in[reg_owner]["bank_loan_disbursement"]
        bank_inst = tx_by_type_out[reg_owner]["bank_loan_installment"]
        family_tx = tx_by_type_in[reg_owner]["family_settlement"] + tx_by_type_out[reg_owner]["family_settlement"]
        net_flow = tx_in - tx_out
        
        feats = [
            len(reg_owners), len(act_controllers), has_discrepancy, is_company,
            has_mortgage, mortgagee_is_bank, mortgagee_is_priv, chain_depth,
            o_pr, o_in_deg, o_out_deg, tx_in, tx_out, prop_fin, eq_inj,
            loan_disb, loan_repay, bank_loan, bank_inst, family_tx, net_flow
        ]
        X.append(feats)
        if prop in gt_map:
            y.append(1)
            y_typology.append(gt_map[prop]["scenario_type"])
        else:
            y.append(0)
            y_typology.append("normal")
            
    return np.array(X), np.array(y), np.array(y_typology)

def run_cross_graph_generalization():
    print("=" * 70)
    print("GENERERING GRAF 1 (TRENINGS-GRAF, SEED 42)...")
    ent1, edges1, tx1, gt1 = generate_graph_dataset(seed=42, num_properties=600)
    X_train, y_train, _ = extract_features_from_graph(ent1, edges1, tx1, gt1)
    
    print("\nGENERERING GRAF 2 (UAVHENGIG TEST-GRAF MED PARAMETERSKIFT, SEED 999)...")
    # Graf 2 har 800 eiendommer, 25% mer bakgrunnsstøy og en annen tilfeldighetsdistribusjon
    ent2, edges2, tx2, gt2 = generate_graph_dataset(seed=999, num_properties=800, noise_factor=1.25)
    X_test, y_test, typ_test = extract_features_from_graph(ent2, edges2, tx2, gt2)
    
    print(f"\nTreningssett (Graf 1): {len(X_train)} eiendommer ({np.sum(y_train)} AML, {np.sum(y_train == 0)} normale)")
    print(f"Usett Testsett (Graf 2): {len(X_test)} eiendommer ({np.sum(y_test)} AML, {np.sum(y_test == 0)} normale)")
    
    # Preprosessering tilpasses KUN på Graf 1
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)
    
    # Tren modeller på Graf 1
    models = {
        "Regelbasert Heuristikk": None,
        "Logistic Regression (L2)": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
        "Random Forest Classifier": RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42),
        "HistGradientBoosting": HistGradientBoostingClassifier(min_samples_leaf=2, class_weight="balanced", random_state=42)
    }
    
    print("\n" + "=" * 70)
    print("RESULTATER PÅ HELT USETT GRAF 2 (OUT-OF-DISTRIBUTION VALIDATION):")
    print("=" * 70)
    
    for name, clf in models.items():
        if clf is None:
            # Regelbasert heuristikk: discrepancy == 1 eller mortgage == 1
            # Feature indeks 2 (has_discrepancy) og indeks 4 (has_mortgage)
            preds = ((X_test[:, 2] == 1) | (X_test[:, 4] == 1)).astype(int)
        else:
            clf.fit(X_train_scaled, y_train)
            preds = clf.predict(X_test_scaled)
            
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        cm = confusion_matrix(y_test, preds)
        
        print(f"\n[{name}]")
        print(f"Accuracy: {acc:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1: {f1:.4f}")
        print(f"Confusion Matrix (TN: {cm[0,0]}, FP: {cm[0,1]} / FN: {cm[1,0]}, TP: {cm[1,1]}):")
        
        # Sjekk per typologi
        for typ in ["blankoskjoete", "layered_holding", "loan_back_mortgage"]:
            mask = (typ_test == typ)
            if np.sum(mask) > 0:
                sub_rec = recall_score(y_test[mask], preds[mask], zero_division=0)
                print(f"  - Recall for {typ}: {sub_rec:.2%}")

if __name__ == "__main__":
    run_cross_graph_generalization()
