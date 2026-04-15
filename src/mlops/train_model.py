import os
from databricks.connect import DatabricksSession
import mlflow
import mlflow.sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import pandas as pd

# --- DIRECT AUTHENTICATION ---
# Replace with your actual token
os.environ['DATABRICKS_HOST'] = "https://adb-7405610641612330.10.azuredatabricks.net/"
os.environ['DATABRICKS_TOKEN'] = "dapif40ff3e2e50f6676856877efd64c8cb5" 

mlflow.set_tracking_uri("databricks")

# Using a path in your own user folder is the most reliable
# Example: /Users/tarun.v@company.com/healthclaim_fraud
experiment_path = "/Users/312825103015@act.edu.in/healthclaim_fraud"
mlflow.set_experiment(experiment_path)
# -----------------------------

spark = DatabricksSession.builder.getOrCreate()
def train_anomaly_model():
    database_name = "healthclaim_guardian.default"
    features_table = f"{database_name}.insurance_silver_features"
    
    print(f"Loading features from {features_table} via Spark...")
    df = spark.read.table(features_table)

    print("Converting to Pandas for local ML training...")
    pdf = df.toPandas()
    pdf = pdf.dropna()

    feature_cols = ["billed_amount", "hosp_avg_billed", "amount_to_avg_ratio"]
    X = pdf[feature_cols]
    
    print("Standardizing features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"Connecting to MLflow and logging to {experiment_path}...")
    
    with mlflow.start_run(run_name="local_dev_kmeans_anomaly"):
        kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
        kmeans.fit(X_scaled)
        
        mlflow.log_param("algorithm", "Scikit-Learn KMeans")
        mlflow.log_param("k_clusters", 3)
        mlflow.log_param("features", feature_cols)
        
        # Log the model
        mlflow.sklearn.log_model(kmeans, "fraud_detection_model")
        
        print("✅ Model trained successfully!")
        print("✅ Parameters and Model securely logged to Azure Databricks.")

if __name__ == "__main__":
    train_anomaly_model()