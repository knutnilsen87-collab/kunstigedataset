from google.cloud import bigquery
import os

# Konfigurasjon
PROJECT_ID = "datsetsyntetisk"
DATASET_ID = "aml_synth"
LOCATION = "europe-west1"  # eller europe-north1
OUTPUT_DIR = r"c:\Prosjekter\kunstigedataset\output"

client = bigquery.Client(project=PROJECT_ID)

# Opprett dataset hvis det ikke finnes
dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
dataset = bigquery.Dataset(dataset_ref)
dataset.location = LOCATION
client.create_dataset(dataset, exists_ok=True)
print(f"Dataset {DATASET_ID} klar")

# Tabeller og eksplisitte skjemaer
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

for table_name, filename in tables.items():
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=table_schemas[table_name],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    
    with open(file_path, "rb") as source_file:
        job = client.load_table_from_file(source_file, table_id, job_config=job_config)
    
    job.result()  # Vent til ferdig
    table = client.get_table(table_id)
    print(f"Lastet {table.num_rows} rader til {table_id}")

print("Ferdig – alle tabeller er i BigQuery med korrekte kolonner og typer")
