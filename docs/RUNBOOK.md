# Operations Runbook

## Daily Operations Checklist

### Morning Checks (9:00 AM ET)

- [ ] Verify overnight pipeline run completed successfully
- [ ] Check anomaly detection rate (expected: 1-5%)
- [ ] Review any data quality alerts
- [ ] Confirm model predictions are within expected ranges

### Weekly Checks (Monday)

- [ ] Review model performance metrics
- [ ] Check for data drift indicators
- [ ] Analyze anomaly trends from past week
- [ ] Review storage costs and optimize if needed

### Monthly Checks (1st of month)

- [ ] Retrain model if performance degraded
- [ ] Review and archive old data
- [ ] Update documentation if needed
- [ ] Security review of access permissions

---

## Common Procedures

### Procedure 1: Manual Pipeline Run

**When**: Ad-hoc data refresh needed, testing changes

**Steps**:

1. Navigate to Databricks Workspace
2. Go to Workflows → Jobs → `healthclaim_guardian_pipeline`
3. Click "Run Now"
4. Monitor execution in real-time
5. Verify output tables updated

**Expected Duration**: 15-30 minutes

**Rollback**: If fails, check logs and fix root cause before retry

---

### Procedure 2: Model Retraining

**When**: 
- Model performance degraded (silhouette < 0.3)
- Significant data drift detected
- Monthly scheduled retrain

**Steps**:

1. **Evaluate Current Model**
   ```bash
   # Check current model metrics
   databricks sql -c "SELECT * FROM mlflow.metrics WHERE model_name = 'healthclaim_fraud_detector'"
   ```

2. **Trigger Training**
   ```bash
   databricks bundle run --run-name manual_training
   ```

3. **Validate New Model**
   - Check silhouette score > 0.3
   - Verify cluster separation
   - Compare anomaly rates with previous model

4. **Promote to Production**
   ```python
   from healthclaim_guardian.model_registry import ModelRegistryManager
   
   registry = ModelRegistryManager()
   registry.transition_to_stage(version="N", stage="Production")
   ```

5. **Monitor First Run**
   - Watch next pipeline execution
   - Compare anomaly rates before/after
   - Alert stakeholders of change

---

### Procedure 3: Data Quality Incident Response

**When**: Validation failures detected

**Severity Levels**:

| Severity | Condition | Response Time |
|----------|-----------|---------------|
| Critical | Pipeline failure | Immediate |
| High | >50% validation failures | < 1 hour |
| Medium | 10-50% validation failures | < 4 hours |
| Low | <10% validation failures | Next business day |

**Response Steps**:

1. **Identify Root Cause**
   - Check which validation failed
   - Review bronze layer data quality
   - Check upstream system changes

2. **Assess Impact**
   - How many records affected?
   - Is gold layer data corrupted?
   - Are downstream users impacted?

3. **Contain**
   - Pause pipeline if needed
   - Notify stakeholders
   - Document incident

4. **Fix**
   - Update validation rules if needed
   - Re-run affected pipeline stages
   - Verify data quality restored

5. **Post-Mortem**
   - Document root cause
   - Implement preventive measures
   - Update runbook if needed

---

### Procedure 4: Emergency Pipeline Stop

**When**: Pipeline causing issues (data corruption, runaway costs)

**Steps**:

1. **Stop Running Job**
   - Go to Workflows → Active Runs
   - Click "Cancel" on running execution

2. **Pause Schedule**
   - Go to Job → Settings → Schedule
   - Set pause_status to "PAUSED"

3. **Notify Team**
   - Slack: #ml-alerts
   - Email: ml-team@synergech.com

4. **Investigate**
   - Review job logs
   - Check cluster metrics
   - Identify root cause

5. **Resume** (when fixed)
   - Fix root cause
   - Test in dev environment
   - Re-enable schedule
   - Monitor first run

---

### Procedure 5: Deploy Pipeline Changes

**When**: New features, bug fixes, configuration changes

**Pre-Deployment Checklist**:

- [ ] Code reviewed and approved
- [ ] Tests passing (unit + integration)
- [ ] Documentation updated
- [ ] Rollback plan documented

**Deployment Steps**:

1. **Deploy to Dev**
   ```bash
   git checkout main
   git pull
   databricks bundle deploy --target dev
   ```

2. **Verify Dev**
   - Run pipeline in dev
   - Check output tables
   - Validate data quality

3. **Deploy to Staging**
   ```bash
   databricks bundle deploy --target staging
   ```

4. **Verify Staging**
   - Run pipeline in staging
   - Compare with production data patterns
   - Get stakeholder signoff

5. **Deploy to Production**
   ```bash
   databricks bundle deploy --target prod
   ```

6. **Monitor**
   - Watch first production run
   - Check all metrics normal
   - Stand by for 1 hour post-deploy

**Rollback Steps**:

```bash
# Revert to previous version
git checkout <previous-commit>
databricks bundle deploy --target prod
```

---

## Troubleshooting Guide

### Issue: Pipeline Fails at Bronze Ingestion

**Symptoms**: Job fails at `ingest_bronze` task

**Possible Causes**:
1. Databricks connection issues
2. Unity Catalog permissions
3. Cluster configuration

**Diagnosis**:
```bash
# Check cluster logs
databricks clusters get --cluster-id <id>

# Check permissions
databricks permissions check --table healthclaim_guardian.default.insurance_bronze_claims
```

**Resolution**:
1. Verify Databricks credentials valid
2. Check cluster has Unity Catalog access
3. Retry with fresh cluster

---

### Issue: High Anomaly Rate Detected

**Symptoms**: >20% of claims flagged as anomalous

**Possible Causes**:
1. Data quality issue in silver layer
2. Model drift
3. Actual fraud spike

**Diagnosis**:
```sql
-- Check data distribution
SELECT 
    risk_level,
    COUNT(*) as count,
    AVG(billed_amount) as avg_amount
FROM healthclaim_guardian.default.insurance_gold_anomalies
GROUP BY risk_level;

-- Compare with historical
SELECT 
    DATE(ingestion_timestamp) as date,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) / COUNT(*) as anomaly_rate
FROM healthclaim_guardian.default.insurance_gold_anomalies
GROUP BY DATE(ingestion_timestamp)
ORDER BY date DESC
LIMIT 30;
```

**Resolution**:
1. If data quality issue: Re-run silver cleansing
2. If model drift: Retrain model
3. If actual fraud: Alert fraud investigation team

---

### Issue: Model Training Fails

**Symptoms**: `train_model` task fails

**Possible Causes**:
1. Insufficient training data
2. MLflow connection issues
3. Resource constraints

**Diagnosis**:
```bash
# Check features table
databricks sql -c "SELECT COUNT(*) FROM healthclaim_guardian.default.insurance_silver_features"

# Check MLflow connection
databricks mlflow experiments list
```

**Resolution**:
1. Ensure >1000 records in features table
2. Verify MLflow tracking URI set correctly
3. Increase cluster resources if OOM

---

### Issue: Validation Failures

**Symptoms**: Data quality checks failing

**Common Failures**:

| Validation | Cause | Fix |
|------------|-------|-----|
| `no_negative_amounts` | Source system bug | Contact data provider |
| `no_invalid_diagnosis_codes` | Coding changes | Update validation rules |
| `required_features_exist` | Schema drift | Re-run feature engineering |

**Resolution**:
1. Review validation report
2. Identify failing expectation
3. Fix upstream or adjust threshold
4. Re-run validation

---

## Contact Information

### On-Call Schedule

| Week | Primary | Backup |
|------|---------|--------|
| Week 1 | John Doe | Jane Smith |
| Week 2 | Jane Smith | Bob Wilson |
| Week 3 | Bob Wilson | John Doe |

### Escalation Path

1. **Level 1**: On-call engineer (immediate)
2. **Level 2**: Team lead (< 30 min)
3. **Level 3**: Engineering manager (< 1 hour)
4. **Level 4**: VP Engineering (critical only)

### Communication Channels

- **Slack**: #healthclaim-guardian, #ml-alerts
- **Email**: ml-team@synergech.com
- **PagerDuty**: Fraud Detection Service
- **Status Page**: status.synergech.com

---

## Performance Benchmarks

### Expected Run Times

| Task | Expected | Alert if > |
|------|----------|------------|
| ingest_bronze | 2 min | 10 min |
| cleanse_silver | 3 min | 15 min |
| engineer_features | 5 min | 20 min |
| train_model | 10 min | 45 min |
| detect_anomalies | 3 min | 15 min |
| **Total** | **23 min** | **90 min** |

### Data Quality Benchmarks

| Metric | Expected | Alert if |
|--------|----------|----------|
| Bronze → Silver retention | 90% | <80% or >95% |
| Anomaly rate | 1-5% | >10% |
| NULL ratio in features | 0% | >1% |
| Model silhouette score | >0.5 | <0.3 |

---

## Appendix: Useful Commands

### Databricks CLI

```bash
# Deploy bundle
databricks bundle deploy --target prod

# Run job
databricks bundle run

# View job runs
databricks job runs list --job-id <id>

# Cancel running job
databricks job runs cancel --job-id <id> --run-id <run-id>
```

### SQL Queries

```sql
-- Latest pipeline run status
SELECT * FROM system.billing.usage
WHERE cluster_id IN (
    SELECT cluster_id FROM system.compute.clusters
    WHERE cluster_name LIKE '%healthclaim%'
)
ORDER BY start_time DESC
LIMIT 10;

-- Anomaly trends
SELECT 
    DATE_TRUNC('week', ingestion_timestamp) as week,
    COUNT(*) as total_claims,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) as anomalies,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as anomaly_rate
FROM healthclaim_guardian.default.insurance_gold_anomalies
GROUP BY DATE_TRUNC('week', ingestion_timestamp)
ORDER BY week DESC;

-- Top anomalous hospitals
SELECT 
    hospital_id,
    COUNT(*) as total_claims,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) as anomalies,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as anomaly_rate
FROM healthclaim_guardian.default.insurance_gold_anomalies
GROUP BY hospital_id
HAVING COUNT(*) > 100
ORDER BY anomaly_rate DESC
LIMIT 10;
```

### Python Utilities

```python
# Load production model
from healthclaim_guardian.model_registry import load_production_model
model = load_production_model()

# Validate layer
from healthclaim_guardian.validation import validate_layer
is_valid = validate_layer(spark, "silver")

# Get configuration
from healthclaim_guardian.config import get_pipeline_config
config = get_pipeline_config()
print(f"Anomaly threshold: {config.anomaly_ratio_threshold}")
```
