Replication Scripts
===================

```text
Code/
├── run_all.py                # orchestrates the numbered pipeline
├── 0.x ... , 1-4 ...         # main staging scripts executed by run_all.py
├── Create_Data.do            # see note below
├── Estimate_Coefficients.do  # see note below
└── macro_var_calculation.py  # DLEU macro-variable appender
```

**Comment paper scripts (Benkard–Miller–Yurukoglu, 2025)**

- `Create_Data.do`: Run in Stata to rebuild the intermediate datasets. Used as a helper for the `0.3 theta_estimation.do` stage.
- `Estimate_Coefficients.do`: Run in Stata after `Create_Data.do` to estimate the model coefficients. Also supports `0.3 theta_estimation.do`.
