# Example: AI Analysis Workflow — ML on Project Data

## Objective
Apply machine learning to project/source data (forecasting, anomaly detection, segmentation)
and optionally feed the results back into the model.

## Example Prompt
```text
On sales.csv: forecast the next 12 periods of Amount with Holt-Winters,
detect anomalies on the same column, and run RFM segmentation on the customer data.
Summarize the findings.
```

## Tools Used
- `forecast_series` — time-series forecasting (Holt-Winters / exponential smoothing)
- `detect_anomalies` — statistical anomaly detection
- `run_clustering` — k-means / hierarchical clustering
- `rfm_segmentation` — Recency–Frequency–Monetary customer segmentation
- `correlation_analysis` — Pearson/Spearman correlation matrix

## Expected Result
- A forecast with predicted values and confidence intervals.
- A list of anomalous points on the chosen metric.
- RFM segments with customer assignments.
- Optionally, results integrated back as DAX calculated tables or Power Query.

## Professional Use Case
Brings analytics that normally live in separate notebooks **into the BI workflow**: a BI
developer can forecast demand, flag anomalies or segment customers and surface the output
directly in the model and visuals — no separate data-science pipeline required.

> Verified in practice: `forecast_series` (Holt-Winters) and `detect_anomalies` have been run
> on real financial sample data. Results feed `create_visual` / `export_html_visual` for
> reporting.
