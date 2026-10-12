"""
BigQuery Ingestion & View Creation Script
Laster syntetiske CSV-tabeller til Google Cloud BigQuery (datsetsyntetisk.aml_synth)
og oppretter analytiske views (v_detected_blankoskjoete, v_entity_risk_summary, v_aml_master_alerts).
Verifiserer rader og spørreresultater.
"""

from google.cloud import bigquery
import os

PROJECT_ID = "datsetsyntetisk"
DATASET_ID = "aml_synth"
LOCATION = "europe-west1"
OUTPUT_DIR = r"c:\Prosjekter\kunstigedataset\output"

client = bigquery.Client(project=PROJECT_ID)

# 1. Sikre at datasettet eksisterer
dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
dataset = bigquery.Dataset(dataset_ref)
dataset.location = LOCATION
client.create_dataset(dataset, exists_ok=True)
print(f"Dataset {dataset_ref} verifisert i {LOCATION}.")

# 2. Skjemaer for basis-tabeller
table_schemas = {
    "entities": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("type", "STRING", mode="REQUIRED"),
    ],
    "ownership_edges": [
        bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("role", "STRING", mode="REQUIRED"),
    ],
    "transactions": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sender", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("receiver", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("amount", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("type", "STRING", mode="REQUIRED"),
    ],
    "scenarios": [
        bigquery.SchemaField("scenario_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("property", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("registered_owner", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("actual_controller", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("details", "STRING", mode="NULLABLE"),
    ],
    "ground_truth": [
        bigquery.SchemaField("scenario_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("scenario_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("hidden_owner", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("strawman", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("property", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("details", "STRING", mode="NULLABLE"),
    ],
}

tables = {
    "entities": "entities.csv",
    "ownership_edges": "ownership_edges.csv",
    "transactions": "transactions.csv",
    "scenarios": "scenarios.csv",
    "ground_truth": "ground_truth.csv",
}

print("\n--- LASTER TABELLER TIL BIGQUERY ---")
for table_name, filename in tables.items():
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fil mangler: {file_path}. Kjører du generator.py først?")
        
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=table_schemas[table_name],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    
    with open(file_path, "rb") as source_file:
        job = client.load_table_from_file(source_file, table_id, job_config=job_config)
    
    job.result()  # Vent til jobben fullfører
    table = client.get_table(table_id)
    print(f" OK {table_id}: {table.num_rows} rader lastet inn.")

# 3. Opprett analytiske SQL-views
print("\n--- OPPRETTER ANALYTISKE VIEWS ---")

views = {
    "v_detected_blankoskjoete": f"""
        CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_detected_blankoskjoete` AS
        SELECT 
          prop.id AS property_id,
          strawman.source AS strawman_id,
          controller.source AS hidden_controller_id,
          tx.amount AS financing_amount,
          tx.type AS transaction_type
        FROM `{PROJECT_ID}.{DATASET_ID}.entities` prop
        JOIN `{PROJECT_ID}.{DATASET_ID}.ownership_edges` strawman
          ON prop.id = strawman.target AND strawman.role = 'registered_owner'
        JOIN `{PROJECT_ID}.{DATASET_ID}.ownership_edges` controller
          ON prop.id = controller.target AND controller.role = 'actual_controller'
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.transactions` tx
          ON controller.source = tx.sender AND strawman.source = tx.receiver
        WHERE prop.type = 'property'
          AND strawman.source != controller.source;
    """,
    "v_entity_risk_summary": f"""
        CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_entity_risk_summary` AS
        WITH entity_props AS (
          SELECT source AS entity_id, COUNT(DISTINCT target) AS properties_owned
          FROM `{PROJECT_ID}.{DATASET_ID}.ownership_edges`
          WHERE role = 'registered_owner'
          GROUP BY source
        ),
        entity_ctrls AS (
          SELECT source AS entity_id, COUNT(DISTINCT target) AS properties_controlled
          FROM `{PROJECT_ID}.{DATASET_ID}.ownership_edges`
          WHERE role = 'actual_controller'
          GROUP BY source
        ),
        entity_inflow AS (
          SELECT receiver AS entity_id, SUM(amount) AS total_inflow, COUNT(id) AS tx_in_count
          FROM `{PROJECT_ID}.{DATASET_ID}.transactions`
          GROUP BY receiver
        ),
        entity_outflow AS (
          SELECT sender AS entity_id, SUM(amount) AS total_outflow, COUNT(id) AS tx_out_count
          FROM `{PROJECT_ID}.{DATASET_ID}.transactions`
          GROUP BY sender
        )
        SELECT 
          e.id,
          e.type,
          COALESCE(ep.properties_owned, 0) AS properties_owned,
          COALESCE(ec.properties_controlled, 0) AS properties_controlled,
          COALESCE(ei.total_inflow, 0) AS total_inflow,
          COALESCE(eo.total_outflow, 0) AS total_outflow,
          COALESCE(ei.total_inflow, 0) - COALESCE(eo.total_outflow, 0) AS net_cashflow
        FROM `{PROJECT_ID}.{DATASET_ID}.entities` e
        LEFT JOIN entity_props ep ON e.id = ep.entity_id
        LEFT JOIN entity_ctrls ec ON e.id = ec.entity_id
        LEFT JOIN entity_inflow ei ON e.id = ei.entity_id
        LEFT JOIN entity_outflow eo ON e.id = eo.entity_id;
    """,
    "v_aml_master_alerts": f"""
        CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_aml_master_alerts` AS
        SELECT 
          prop.id AS property_id,
          'OWNERSHIP_DISCREPANCY' AS alert_type,
          'HIGH' AS risk_level,
          CONCAT('Registrert eier (', reg.source, ') skiller seg fra faktisk kontroller (', ctrl.source, ')') AS alert_description
        FROM `{PROJECT_ID}.{DATASET_ID}.entities` prop
        JOIN `{PROJECT_ID}.{DATASET_ID}.ownership_edges` reg
          ON prop.id = reg.target AND reg.role = 'registered_owner'
        JOIN `{PROJECT_ID}.{DATASET_ID}.ownership_edges` ctrl
          ON prop.id = ctrl.target AND ctrl.role = 'actual_controller'
        WHERE prop.type = 'property' AND reg.source != ctrl.source

        UNION ALL

        SELECT 
          prop.id AS property_id,
          'PRIVATE_OR_UNREGULATED_MORTGAGE' AS alert_type,
          'MEDIUM' AS risk_level,
          CONCAT('Privat panthaver (', m.source, ') registrert på eiendommen') AS alert_description
        FROM `{PROJECT_ID}.{DATASET_ID}.entities` prop
        JOIN `{PROJECT_ID}.{DATASET_ID}.ownership_edges` m
          ON prop.id = m.target AND m.role = 'mortgage_holder'
        JOIN `{PROJECT_ID}.{DATASET_ID}.entities` lender
          ON m.source = lender.id
        WHERE prop.type = 'property' AND lender.type != 'bank';
    """
}

for view_name, ddl in views.items():
    client.query(ddl).result()
    print(f" OK View opprettet: {PROJECT_ID}.{DATASET_ID}.{view_name}")

# 4. Verifisering og sammendrag
print("\n--- VERIFISERING AV BIGQUERY DATASETT ---")
for table_name in tables.keys():
    t = client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{table_name}")
    print(f" - Tabell {table_name:18s}: {t.num_rows:6d} rader")

for view_name in views.keys():
    q = client.query(f"SELECT COUNT(*) AS cnt FROM `{PROJECT_ID}.{DATASET_ID}.{view_name}`")
    cnt = list(q.result())[0].cnt
    print(f" - View   {view_name:18s}: {cnt:6d} rader generert")

print("\nVerifisert: Alle tabeller og views er oppdatert og operative i Google Cloud BigQuery!")
