"""
Baseline Machine Learning Model for AML Real Estate Synthetic Dataset.
Inneholder graf-feature engineering, streng featurization ordering (split før scaling),
sammenligning mot naive og regelbaserte baselines, samt evaluering per typologi.
"""

import csv
import os
import numpy as np
import networkx as nx
from collections import defaultdict
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, classification_report
)

def load_csv_data(data_dir="output"):
    def read_csv(filename):
        with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    entities = read_csv("entities.csv")
    ownership_edges = read_csv("ownership_edges.csv")
    transactions = read_csv("transactions.csv")
    ground_truth = read_csv("ground_truth.csv")
    return entities, ownership_edges, transactions, ground_truth

def build_graphs_and_features(entities, ownership_edges, transactions, ground_truth):
    print("Bygger NetworkX-grafer over eierskap og transaksjoner...")
    
    # 1. Bygg eierskapsgraf (DiGraph)
    G_own = nx.DiGraph()
    for e in entities:
        G_own.add_node(e["id"], entity_type=e["type"])
        
    for oe in ownership_edges:
        G_own.add_edge(oe["source"], oe["target"], role=oe["role"])
        
    # 2. Bygg transaksjonsgraf (MultiDiGraph)
    G_tx = nx.MultiDiGraph()
    for tx in transactions:
        amount = float(tx["amount"])
        G_tx.add_edge(tx["sender"], tx["receiver"], amount=amount, tx_type=tx["type"], tx_id=tx["id"])
        
    # Beregn globale grafmetrikker
    print("Beregner PageRank og grad-sentraliteter...")
    pagerank = nx.pagerank(G_own, alpha=0.85, max_iter=200)
    
    # Lagre ground truth indeksering
    gt_map = {gt["property"]: gt for gt in ground_truth}
    
    # Forbered transaksjonsaggregering per entitet
    tx_in_volume = defaultdict(float)
    tx_out_volume = defaultdict(float)
    tx_in_count = defaultdict(int)
    tx_out_count = defaultdict(int)
    tx_by_type_in = defaultdict(lambda: defaultdict(float))
    tx_by_type_out = defaultdict(lambda: defaultdict(float))
    
    for tx in transactions:
        s, r, amt, t_type = tx["sender"], tx["receiver"], float(tx["amount"]), tx["type"]
        tx_out_volume[s] += amt
        tx_in_volume[r] += amt
        tx_out_count[s] += 1
        tx_in_count[r] += 1
        tx_by_type_out[s][t_type] += amt
        tx_by_type_in[r][t_type] += amt
        
    # Eierskapskjede-hjelper for lagdelte selskaper
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
        
    # 3. Bygg feature-matrise for hver eiendom (Property level classification)
    properties = [e["id"] for e in entities if e["type"] == "property"]
    print(f"Ekstraherer graf-features for {len(properties)} eiendommer...")
    
    feature_names = [
        "reg_owner_count",
        "act_ctrl_count",
        "has_ownership_discrepancy",
        "owner_is_company",
        "has_mortgage",
        "mortgagee_is_bank",
        "mortgagee_is_private_co",
        "holding_chain_depth",
        "owner_pagerank",
        "owner_in_degree",
        "owner_out_degree",
        "owner_tx_in_vol",
        "owner_tx_out_vol",
        "owner_tx_inflow_property_financing",
        "owner_tx_inflow_equity_injection",
        "owner_tx_inflow_loan_disbursement",
        "owner_tx_outflow_loan_repayment",
        "owner_tx_inflow_bank_loan",
        "owner_tx_outflow_bank_installment",
        "owner_tx_family_settlement",
        "owner_net_financial_flow"
    ]
    
    X = []
    y_binary = []
    y_typology = []
    prop_ids = []
    
    for prop in properties:
        # Inngående kanter til eiendommen
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
        
        # Sjekk panthavers type (Bank vs privat selskap)
        mortgagee_types = [G_own.nodes.get(m, {}).get("entity_type", "company") for m in mortgagees]
        mortgagee_is_bank = 1 if any(t == "bank" for t in mortgagee_types) else 0
        mortgagee_is_priv = 1 if any(t in ["company", "person"] for t in mortgagee_types) else 0
        
        chain_depth = get_holding_depth(reg_owner) if reg_owner else 0
        
        # Sentralitet og transaksjoner for registrert eier
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
            len(reg_owners),
            len(act_controllers),
            has_discrepancy,
            is_company,
            has_mortgage,
            mortgagee_is_bank,
            mortgagee_is_priv,
            chain_depth,
            o_pr,
            o_in_deg,
            o_out_deg,
            tx_in,
            tx_out,
            prop_fin,
            eq_inj,
            loan_disb,
            loan_repay,
            bank_loan,
            bank_inst,
            family_tx,
            net_flow
        ]
        
        X.append(feats)
        prop_ids.append(prop)
        
        # Ground Truth etiketter
        if prop in gt_map:
            y_binary.append(1)
            y_typology.append(gt_map[prop]["scenario_type"])
        else:
            y_binary.append(0)
            y_typology.append("normal")
            
    return np.array(X), np.array(y_binary), np.array(y_typology), feature_names, prop_ids

def train_and_evaluate():
    entities, ownership_edges, transactions, ground_truth = load_csv_data()
    X, y, y_typology, feature_names, prop_ids = build_graphs_and_features(
        entities, ownership_edges, transactions, ground_truth
    )
    
    print("\n--- DATASET OVERSIKT ---")
    print(f"Totalt antall eiendommer: {len(X)}")
    print(f"Normale eiendommer: {np.sum(y == 0)}")
    print(f"Mistenkelige (AML Ground Truth): {np.sum(y == 1)}")
    for t_type in set(y_typology):
        print(f" - {t_type}: {np.sum(y_typology == t_type)}")
        
    # 1. Strict Featurization Ordering: Stratified Split FØR pre-prosessering
    print("\nDeler data i 70% Treningssett og 30% Testsett (Stratified)...")
    X_train, X_test, y_train, y_test, typ_train, typ_test = train_test_split(
        X, y, y_typology, test_size=0.30, random_state=42, stratify=y_typology
    )
    
    # 2. Imputering og Skalering tilpasset KUN på treningssettet
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)
    
    # 3. Baselines
    # Baseline A: Naive Baseline (Majority Class)
    y_pred_naive = np.zeros_like(y_test)
    
    # Baseline B: Heuristisk / Regelbasert (discrepancy == 1 eller mortgage == 1)
    disc_idx = feature_names.index("has_ownership_discrepancy")
    mort_idx = feature_names.index("has_mortgage")
    y_pred_heuristic = ((X_test[:, disc_idx] == 1) | (X_test[:, mort_idx] == 1)).astype(int)
    
    # 4. Machine Learning Modeller
    models = {
        "Naive Majority Baseline": (None, y_pred_naive, y_pred_naive.astype(float)),
        "Regelbasert Heuristikk": (None, y_pred_heuristic, y_pred_heuristic.astype(float)),
        "Logistic Regression (L2)": (
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            None, None
        ),
        "Random Forest Classifier": (
            RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42),
            None, None
        ),
        "HistGradientBoosting": (
            HistGradientBoostingClassifier(min_samples_leaf=2, class_weight="balanced", random_state=42),
            None, None
        )
    }
    
    results = {}
    print("\n--- TRENER OG EVALUERER MODELLER ---")
    for name, (clf, preds, probs) in models.items():
        if clf is not None:
            clf.fit(X_train_scaled, y_train)
            preds = clf.predict(X_test_scaled)
            probs = clf.predict_proba(X_test_scaled)[:, 1]
            
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        roc = roc_auc_score(y_test, probs) if probs is not None else 0.5
        pr_auc = average_precision_score(y_test, probs) if probs is not None else 0.0
        cm = confusion_matrix(y_test, preds)
        
        # Typology slice recall
        slice_recalls = {}
        for typology in ["blankoskjoete", "layered_holding", "loan_back_mortgage"]:
            mask = (typ_test == typology)
            if np.sum(mask) > 0:
                slice_recalls[typology] = recall_score(y_test[mask], preds[mask], zero_division=0)
            else:
                slice_recalls[typology] = 0.0
                
        results[name] = {
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1-Score": f1,
            "ROC-AUC": roc,
            "PR-AUC": pr_auc,
            "Confusion Matrix": cm,
            "Slice Recalls": slice_recalls,
            "Model Object": clf
        }
        
        print(f"\n[{name}]")
        print(f"Accuracy: {acc:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1: {f1:.4f} | ROC-AUC: {roc:.4f}")
        print(f"Confusion Matrix (TN, FP / FN, TP):\n{cm}")
        print(f"Gjenkjenning per typologi: {slice_recalls}")
        
    # 5. Feature Importance fra Random Forest
    rf_model = results["Random Forest Classifier"]["Model Object"]
    importances = rf_model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    
    print("\n--- TOPP GRAF-FEATURES (Random Forest Importance) ---")
    top_features = []
    for idx in sorted_idx[:10]:
        feat = feature_names[idx]
        imp = importances[idx]
        top_features.append((feat, imp))
        print(f" - {feat:35s}: {imp:.4f}")
        
    return results, feature_names, top_features

if __name__ == "__main__":
    train_and_evaluate()
