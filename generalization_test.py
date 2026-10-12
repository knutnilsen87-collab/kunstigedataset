"""
Benchmark v0.2: Independent Cross-Graph Validation Test
Herdet out-of-distribution testing med nøytrale transaksjonstyper,
disjunkte scenario-eiendommer, og evaluering over flere uavhengige test-frø (seeds).
Rapporterer gjennomsnitt og variasjon (std / min-max) i presisjon, recall og falske positive.
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
    cfg.AMOUNT_SHIFT = amount_shift
    cfg.OUTPUT_DIR = f"output_test_seed_{seed}"
    
    # Juster støy proporsjonalt
    cfg.NUM_LEGIT_BANK_MORTGAGES = int(180 * noise_factor)
    cfg.NUM_LEGIT_PRIVATE_MORTGAGES = int(30 * noise_factor)
    cfg.NUM_LEGIT_HOLDING_CHAINS = int(45 * noise_factor)
    cfg.NUM_LEGIT_INHERITANCE_DISCREPANCIES = int(40 * noise_factor)
    cfg.NUM_LEGIT_JOINT_OWNERSHIPS = int(40 * noise_factor)
    
    gen = GraphGenerator(cfg)
    gen.generate_base_graph()
    
    # 1. Kriminelle scenarioer først (disjunkte eiendommer)
    gen.inject_blankoskjoete_scenarios()
    gen.inject_layered_holding_scenarios()
    gen.inject_loan_back_mortgage_scenarios()
    
    # 2. Legitim støy
    gen.inject_legitimate_holding_structures()
    gen.inject_legitimate_inheritance_discrepancies()
    gen.inject_legitimate_joint_ownerships()
    gen.inject_legitimate_private_mortgages()
    gen.inject_legitimate_bank_mortgages()
    
    assert gen.validate_balance_conservation(), f"Balansekonservering feilet for seed {seed}!"
    return gen.entities, gen.ownership_edges, gen.transactions, gen.ground_truth

def extract_features_from_graph(entities, ownership_edges, transactions, ground_truth):
    G_own = nx.MultiDiGraph()
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
    
    feature_names = [
        "reg_owner_count", "act_ctrl_count", "has_ownership_discrepancy",
        "owner_is_company", "owner_is_bank", "has_mortgage",
        "mortgagee_is_bank", "mortgagee_is_private", "mortgagee_controls_owner",
        "holding_chain_depth", "owner_pagerank", "owner_in_degree", "owner_out_degree",
        "controller_pagerank", "owner_tx_in_vol", "owner_tx_out_vol", "owner_net_financial_flow",
        "owner_loan_inflow", "owner_loan_outflow", "owner_capital_inflow",
        "owner_transfer_inflow", "owner_transfer_outflow", "controller_transfer_outflow",
        "loan_repayment_ratio"
    ]
    
    X, y, y_typology = [], [], []
    
    for prop in properties:
        in_edges = list(G_own.in_edges(prop, data=True))
        reg_owners = [u for u, v, d in in_edges if d.get("role") == "registered_owner"]
        act_controllers = [u for u, v, d in in_edges if d.get("role") == "actual_controller"]
        mortgagees = [u for u, v, d in in_edges if d.get("role") == "mortgage_holder"]
        
        reg_owner = reg_owners[0] if reg_owners else None
        act_ctrl = act_controllers[0] if act_controllers else None
        
        reg_owner_count = len(reg_owners)
        act_ctrl_count = len(act_controllers)
        has_discrepancy = 1 if (reg_owner and act_ctrl and reg_owner != act_ctrl) else 0
        owner_type = G_own.nodes.get(reg_owner, {}).get("entity_type", "person") if reg_owner else "person"
        is_company = 1 if owner_type == "company" else 0
        is_bank = 1 if owner_type == "bank" else 0
        
        has_mortgage = 1 if len(mortgagees) > 0 else 0
        mortgagee_types = [G_own.nodes.get(m, {}).get("entity_type", "company") for m in mortgagees]
        mortgagee_is_bank = 1 if any(t == "bank" for t in mortgagee_types) else 0
        mortgagee_is_priv = 1 if any(t in ["company", "person"] for t in mortgagee_types) else 0
        
        mortgagee_controls_owner = 0
        for m in mortgagees:
            if act_ctrl and G_own.has_edge(act_ctrl, m):
                mortgagee_controls_owner = 1
            if reg_owner and G_own.has_edge(m, reg_owner):
                mortgagee_controls_owner = 1
                
        chain_depth = get_holding_depth(reg_owner) if reg_owner else 0
        o_pr = pagerank.get(reg_owner, 0.0) if reg_owner else 0.0
        o_in_deg = G_own.in_degree(reg_owner) if reg_owner else 0
        o_out_deg = G_own.out_degree(reg_owner) if reg_owner else 0
        c_pr = pagerank.get(act_ctrl, 0.0) if act_ctrl else 0.0
        
        tx_in = tx_in_volume[reg_owner] if reg_owner else 0.0
        tx_out = tx_out_volume[reg_owner] if reg_owner else 0.0
        net_flow = tx_in - tx_out
        
        loan_in = tx_by_type_in[reg_owner]["loan_disbursement"] if reg_owner else 0.0
        loan_out = tx_by_type_out[reg_owner]["loan_installment"] if reg_owner else 0.0
        cap_in = tx_by_type_in[reg_owner]["capital_contribution"] if reg_owner else 0.0
        tf_in = tx_by_type_in[reg_owner]["transfer"] if reg_owner else 0.0
        tf_out = tx_by_type_out[reg_owner]["transfer"] if reg_owner else 0.0
        
        ctrl_tf_out = tx_by_type_out[act_ctrl]["transfer"] if (act_ctrl and act_ctrl != reg_owner) else 0.0
        repay_ratio = (loan_out / loan_in) if loan_in > 0 else 0.0
        
        feats = [
            reg_owner_count, act_ctrl_count, has_discrepancy, is_company, is_bank,
            has_mortgage, mortgagee_is_bank, mortgagee_is_priv, mortgagee_controls_owner,
            chain_depth, o_pr, o_in_deg, o_out_deg, c_pr,
            tx_in, tx_out, net_flow, loan_in, loan_out, cap_in,
            tf_in, tf_out, ctrl_tf_out, repay_ratio
        ]
        
        X.append(feats)
        if prop in gt_map:
            y.append(1)
            y_typology.append(gt_map[prop]["scenario_type"])
        else:
            y.append(0)
            y_typology.append("normal")
            
    return np.array(X), np.array(y), np.array(y_typology), feature_names

def run_multi_seed_independent_validation():
    print("=" * 80)
    print("BENCHMARK v0.2: MULTI-SEED INDEPENDENT CROSS-GRAPH VALIDATION")
    print("=" * 80)
    
    # 1. Treningsgraf (Seed 42)
    print("\nGenererer Trenings-Graf (Seed 42, 600 eiendommer, basis-beløp amount_shift=1.0)...")
    ent_tr, edges_tr, tx_tr, gt_tr = generate_graph_dataset(seed=42, num_properties=600, amount_shift=1.0, noise_factor=1.0)
    X_train, y_train, typ_train, feat_names = extract_features_from_graph(ent_tr, edges_tr, tx_tr, gt_tr)
    print(f"Treningstørrelse: {len(X_train)} eiendommer (Normale: {np.sum(y_train==0)}, AML: {np.sum(y_train==1)})")
    
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    
    # Tren modeller
    models = {
        "Regelbasert Heuristikk": None,
        "Logistic Regression (L2)": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
        "HistGradientBoosting": HistGradientBoostingClassifier(min_samples_leaf=2, class_weight="balanced", random_state=42),
        "Random Forest (100 trær)": RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
    }
    
    print("\nTrener modeller på Treningsgrafen...")
    for name, clf in models.items():
        if clf is not None:
            clf.fit(X_train_scaled, y_train)
            print(f" - {name}: Ferdig tilpasset.")
            
    # Indekser for heuristikk
    disc_idx = feat_names.index("has_ownership_discrepancy")
    mort_idx = feat_names.index("has_mortgage")
    bank_idx = feat_names.index("mortgagee_is_bank")
    
    # 2. Test-konfigurasjoner (Flere uavhengige test-frø med ulik størrelse, støy og beløpsforskyvning)
    test_configs = [
        {"seed": 101, "props": 700, "amount_shift": 1.20, "noise": 1.15, "name": "Graf A (Seed 101, +20% shift, +15% støy)"},
        {"seed": 202, "props": 750, "amount_shift": 1.35, "noise": 1.20, "name": "Graf B (Seed 202, +35% shift, +20% støy)"},
        {"seed": 555, "props": 800, "amount_shift": 1.45, "noise": 1.25, "name": "Graf C (Seed 555, +45% shift, +25% støy)"},
        {"seed": 999, "props": 850, "amount_shift": 1.60, "noise": 1.30, "name": "Graf D (Seed 999, +60% shift, +30% støy)"},
    ]
    
    metrics_history = defaultdict(lambda: defaultdict(list))
    
    print("\n" + "=" * 80)
    print("STARTER BLIND TESTING PÅ 4 INDEPENDENTE TEST-GRAFER")
    print("=" * 80)
    
    for cfg in test_configs:
        print(f"\n---> Tester på {cfg['name']}...")
        ent_te, edges_te, tx_te, gt_te = generate_graph_dataset(
            seed=cfg["seed"], num_properties=cfg["props"],
            amount_shift=cfg["amount_shift"], noise_factor=cfg["noise"]
        )
        X_test, y_test, typ_test, _ = extract_features_from_graph(ent_te, edges_te, tx_te, gt_te)
        
        # Bruk KUN trenings-skalering
        X_test_imp = imputer.transform(X_test)
        X_test_scaled = scaler.transform(X_test_imp)
        
        print(f"     Teststørrelse: {len(X_test)} eiendommer (Normale: {np.sum(y_test==0)}, AML: {np.sum(y_test==1)})")
        
        for name, clf in models.items():
            if clf is None:
                # Regelbasert heuristikk
                preds = (
                    (X_test[:, disc_idx] == 1) | 
                    ((X_test[:, mort_idx] == 1) & (X_test[:, bank_idx] == 0))
                ).astype(int)
            else:
                preds = clf.predict(X_test_scaled)
                
            acc = accuracy_score(y_test, preds)
            prec = precision_score(y_test, preds, zero_division=0)
            rec = recall_score(y_test, preds, zero_division=0)
            f1 = f1_score(y_test, preds, zero_division=0)
            cm = confusion_matrix(y_test, preds)
            fp = cm[0, 1]
            fn = cm[1, 0]
            
            metrics_history[name]["accuracy"].append(acc)
            metrics_history[name]["precision"].append(prec)
            metrics_history[name]["recall"].append(rec)
            metrics_history[name]["f1"].append(f1)
            metrics_history[name]["fp"].append(fp)
            metrics_history[name]["fn"].append(fn)
            
            print(f"     [{name:25s}] Prec: {prec*100:5.2f}% | Rec: {rec*100:5.2f}% | F1: {f1:0.4f} | FP: {fp:3d} | FN: {fn:2d}")
            
    # 3. Sammendrag og variasjonsstatistikk
    print("\n" + "=" * 80)
    print("SAMLET BENCHMARK v0.2 RESULTAT (Gjennomsnitt ± Standardavvik over alle 4 test-grafer)")
    print("=" * 80)
    print(f"{'Modell':28s} | {'Presisjon':18s} | {'Recall':18s} | {'F1-Score':18s} | {'Falske Pos (FP)':14s}")
    print("-" * 105)
    
    summary_data = {}
    for name in models.keys():
        p_mean, p_std = np.mean(metrics_history[name]["precision"]), np.std(metrics_history[name]["precision"])
        r_mean, r_std = np.mean(metrics_history[name]["recall"]), np.std(metrics_history[name]["recall"])
        f_mean, f_std = np.mean(metrics_history[name]["f1"]), np.std(metrics_history[name]["f1"])
        fp_mean, fp_std = np.mean(metrics_history[name]["fp"]), np.std(metrics_history[name]["fp"])
        
        summary_data[name] = {
            "p_mean": p_mean, "p_std": p_std,
            "r_mean": r_mean, "r_std": r_std,
            "f_mean": f_mean, "f_std": f_std,
            "fp_mean": fp_mean, "fp_std": fp_std
        }
        
        print(
            f"{name:28s} | "
            f"{p_mean*100:5.2f}% ± {p_std*100:4.2f}% | "
            f"{r_mean*100:5.2f}% ± {r_std*100:4.2f}% | "
            f"{f_mean:0.4f} ± {f_std:0.4f} | "
            f"{fp_mean:5.1f} ± {fp_std:4.1f}"
        )
    print("=" * 105)
    
    return summary_data, metrics_history

if __name__ == "__main__":
    run_multi_seed_independent_validation()
