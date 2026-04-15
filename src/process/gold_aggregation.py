from sklearn.preprocessing import StandardScaler # Add this import at the top

def generate_gold():
    run_id = "6f9aa7a9e85c4118a22b03f6f014ec16"
    model_uri = f"runs:/{run_id}/fraud_detection_model"

    print(f"Loading model from {model_uri}...")
    model = mlflow.sklearn.load_model(model_uri)

    database_name = "healthclaim_guardian.default"
    features_table = f"{database_name}.insurance_silver_features"

    print(f"Downloading features from {features_table}...")
    spark_df = spark.read.table(features_table)
    pdf = spark_df.toPandas()

    print("Predicting anomalies locally...")
    feature_cols = ["billed_amount", "hosp_avg_billed", "amount_to_avg_ratio"]
    X = pdf[feature_cols]

    # --- CRITICAL FIX: SCALE THE DATA ---
    # K-Means needs the data in the same format/scale as when it was trained
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Predict clusters
    pdf["cluster_prediction"] = model.predict(X_scaled)

    # --- REFINED ANOMALY LOGIC ---
    # Calculate stats for each cluster
    cluster_stats = pdf.groupby("cluster_prediction")["amount_to_avg_ratio"].mean()
    print(f"Cluster Stats (Average Ratios):\n{cluster_stats}")

    # Anomaly is the cluster with the highest ratio, BUT 
    # if everyone is in one cluster, we shouldn't flag all.
    if len(cluster_stats) > 1:
        anomaly_cluster = cluster_stats.idxmax()
        # We only flag if the ratio is significantly higher than average (e.g., > 1.2)
        pdf["is_anomaly"] = (pdf["cluster_prediction"] == anomaly_cluster) & (pdf["amount_to_avg_ratio"] > 1.1)
    else:
        print("Warning: Only one cluster found. No anomalies flagged to prevent 100% false positives.")
        pdf["is_anomaly"] = False

    print(f"Target Anomaly Cluster: {anomaly_cluster if len(cluster_stats) > 1 else 'None'}")

    # ... (Rest of the code for saving Spark tables stays the same)