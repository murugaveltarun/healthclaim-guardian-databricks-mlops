# Setup Guide

This guide walks you through setting up Healthclaim Guardian from scratch.

## Prerequisites

### Required Software

1. **Python 3.10-3.12**
   ```bash
   # Check version
   python --version

   # Install (macOS)
   brew install python@3.11

   # Install (Windows)
   # Download from https://python.org
   ```

2. **UV Package Manager**
   ```bash
   # Install
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Verify
   uv --version
   ```

3. **Databricks CLI**
   ```bash
   # Install (macOS)
   brew install databricks

   # Install (Windows)
   winget install Databricks.DatabricksCLI

   # Verify
   databricks --version
   ```

4. **Git**
   ```bash
   # Check installation
   git --version
   ```

### Databricks Workspace Requirements

- Databricks workspace with Unity Catalog enabled
- Cluster creation permissions
- MLflow tracking enabled
- Secrets management enabled

---

## Step 1: Clone Repository

```bash
git clone <repository-url> healthclaim_guardian
cd healthclaim_guardian
```

---

## Step 2: Install Dependencies

```bash
# Install all dependencies (including dev)
uv sync --dev

# Verify installation
uv run python --version
uv run pytest --version
```

---

## Step 3: Configure Databricks Authentication

### Option A: Databricks CLI (Recommended for Development)

```bash
# Configure CLI
databricks configure

# You will be prompted for:
# 1. Host: https://your-workspace.azuredatabricks.net
# 2. Token: <your-personal-access-token>
# 3. Account ID (optional for most users)
```

### Option B: Environment Variables

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export DATABRICKS_HOST="https://your-workspace.azuredatabricks.net"
export DATABRICKS_TOKEN="your-personal-access-token"

# Or create a .env file
cp .env.example .env
# Edit .env with your values
```

### Option C: Databricks Secrets (Production)

```bash
# Create secrets scope
databricks secrets create-scope \
  --scope healthclaim_guardian \
  --initial-manage-principal users

# Add secrets
databricks secrets put-secret \
  --scope healthclaim_guardian \
  --key databricks-host

databricks secrets put-secret \
  --scope healthclaim_guardian \
  --key databricks-token
```

---

## Step 4: Verify Connection

```bash
# Test connection
databricks workspace list

# Should show your workspace files
```

---

## Step 5: Create Unity Catalog Objects

```sql
-- Run in Databricks SQL Editor

-- Create catalog (if not exists)
CREATE CATALOG IF NOT EXISTS healthclaim_guardian;

-- Use catalog
USE CATALOG healthclaim_guardian;

-- Create schema
CREATE SCHEMA IF NOT EXISTS default;

-- Verify
SHOW SCHEMAS;
```

---

## Step 6: Configure MLflow

```bash
# Set MLflow tracking URI (add to .env if needed)
# MLflow will use Databricks-managed tracking by default

# Test MLflow connection
uv run python -c "
import mlflow
mlflow.set_tracking_uri('databricks')
experiments = mlflow.search_experiments()
print(f'Found {len(experiments)} experiments')
"
```

---

## Step 7: Run Tests

```bash
# Run unit tests
uv run pytest

# Expected output: All tests passing
```

---

## Step 8: Run Pipeline (Development)

### Option A: Run Individual Stages

```bash
# 1. Bronze Ingestion
uv run python -m src.ingest.generate_bronze

# 2. Silver Cleansing
uv run python -m src.process.silver_cleansing

# 3. Feature Engineering
uv run python -m src.mlops.feature_engineering

# 4. Model Training
uv run python -m src.mlops.train_model

# 5. Gold Detection
uv run python -m src.process.gold_aggregation
```

### Option B: Run as Workflow

```bash
# Deploy to dev
databricks bundle deploy --target dev

# Run workflow
databricks bundle run
```

---

## Step 9: Verify Output

```bash
# Query gold layer
databricks sql \
  --warehouse-id <your-warehouse-id> \
  --query "SELECT * FROM healthclaim_guardian.default.insurance_gold_anomalies WHERE is_anomaly = true LIMIT 10"
```

Or in Databricks UI:
1. Navigate to Data → Databases
2. Select `healthclaim_guardian` → `default`
3. Query `insurance_gold_anomalies`

---

## Step 10: Configure Monitoring (Optional)

### Set Up Alerts

```sql
-- Create alert for high anomaly rate
CREATE OR REPLACE ALERT high_anomaly_rate
ON SELECT SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as anomaly_rate
   FROM healthclaim_guardian.default.insurance_gold_anomalies
   WHERE ingestion_timestamp >= CURRENT_DATE - INTERVAL 1 DAY
THRESHOLD anomaly_rate > 0.10
NOTIFY ON CHANGE
```

### Create Dashboard

1. Go to Dashboards → Create Dashboard
2. Add widgets for:
   - Pipeline execution history
   - Daily anomaly count
   - Anomaly rate trend
   - Risk level distribution

---

## Troubleshooting

### Issue: "databricks: command not found"

**Solution**: Install Databricks CLI
```bash
# macOS
brew install databricks

# Windows
winget install Databricks.DatabricksCLI

# Linux
curl -fsSL https://raw.githubusercontent.com/databricks/cli/main/install.sh | sh
```

### Issue: "ModuleNotFoundError: No module named 'healthclaim_guardian'"

**Solution**: Reinstall dependencies
```bash
uv sync --dev
```

### Issue: "DATABRICKS_HOST is not set"

**Solution**: Set environment variable
```bash
export DATABRICKS_HOST="https://your-workspace.azuredatabricks.net"
```

### Issue: "Permission denied to create table"

**Solution**: Grant permissions
```sql
-- Grant CREATE TABLE permission
GRANT CREATE TABLE ON SCHEMA healthclaim_guardian.default TO `your-user-email`;

-- Or grant full access
GRANT ALL PRIVILEGES ON SCHEMA healthclaim_guardian.default TO `your-user-email`;
```

### Issue: "MLflow experiment not found"

**Solution**: Create experiment
```python
import mlflow
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/healthclaim_fraud")
```

---

## Next Steps

After successful setup:

1. **Review Documentation**
   - [README.md](README.md) - Project overview
   - [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
   - [RUNBOOK.md](docs/RUNBOOK.md) - Operations guide
   - [API.md](docs/API.md) - API reference

2. **Customize Configuration**
   - Edit `.env` for your environment
   - Update `resources/*.yml` for deployment settings

3. **Set Up CI/CD** (Optional)
   - Configure GitHub Actions
   - Set up automated testing
   - Configure automated deployment

4. **Invite Team Members**
   - Add users to Databricks workspace
   - Grant appropriate permissions
   - Share secrets scope

---

## Support

If you encounter issues not covered in this guide:

- Check [Troubleshooting](README.md#troubleshooting) section
- Review logs in Databricks Job UI
- Contact: ml-team@synergech.com
- Slack: #healthclaim-guardian
