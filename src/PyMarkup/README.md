Replication Scripts
===================

```text
Code/
├── run_all.py                # orchestrates the numbered pipeline
├── 0.x ... , 1-4 ...         # main staging scripts executed by run_all.py
├── Create_Data.py            # Python port of Create_Data.do
├── Estimate_Coefficients.py  # Python port of Estimate_Coefficients.do
└── macro_var_calculation.py  # DLEU macro-variable appender
```

**Python-first workflow (Benkard–Miller–Yurukoglu, 2025)**

- `0.3 theta_estimation.py`: self-contained; builds the trimmed Compustat panel and estimates theta outputs into `Intermediate/` (IV/GMM and OP/ACF).
- `0.4 Create Main Datasets.py`: merges Compustat with CPI/PPI/NAICS descriptors and computes firm-level markups for the plotting scripts.
