import runpy
from path_plot_config import code_dir


## Step 0. Download Datasets ---------------------------------------------------------------- #

# 1. Compustat (from WRDS)
print("Linking to WRDS...\n")
runpy.run_path(path_name = code_dir / "0.0 Download Compustat.py")
print("Compustat data is successfully downloaded.\n")

# 2. CPI (from FRED)
print("Downloading CPI data...\n")
runpy.run_path(path_name = code_dir / "0.1 Download CPI.py")
print("CPI data is successfully downloaded.\n")

# 3. PPI (from BLS)
print("Organizing PPI data...\n")
runpy.run_path(path_name = code_dir / "0.2 PPI Data Preparation.py")
print("PPI data is successfully downloaded and organized.\n")


## Step 1. Theta Estimation ----------------------------------------------------------------- #
print("Running theta estimation (Python)...\n")
runpy.run_path(path_name = code_dir / "0.3 theta_estimation.py")
print("Theta estimation completed.\n")


## Step 2. Create Main Datasets (Compustat + PPI + CPI) ------------------------------------- #
print("Creating main datasets (Python)...\n")
runpy.run_path(path_name = code_dir / "0.4 Create Main Datasets.py")
print("Main datasets have been created.\n")


## Step 3. Prepare Data for Table 1 and Figure 2 -------------------------------------------- #
runpy.run_path(path_name = code_dir / "0.5 Prepare Data for Figures and Tables.py")


## Step 4. Generate Figure 1 ---------------------------------------------------------------- #
runpy.run_path(path_name = code_dir / "1. Generate Figure 1 - Aggregate Markup.py")


## Step 5. Generate Figure 2 ---------------------------------------------------------------- #
runpy.run_path(path_name = code_dir / "2. Generate Figure 2 - CAGR of PPI vs Markup.py")


## Step 6. Generate Summary Statistics ------------------------------------------------------ #
runpy.run_path(path_name = code_dir / "3. Generate Summary Statistics.py")


## Step 7. Generate Table 1 ----------------------------------------------------------------- #
runpy.run_path(path_name = code_dir / "4. Generate Table 1.py")
print("All output has been generated.")
