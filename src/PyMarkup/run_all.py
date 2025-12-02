import subprocess
import runpy
import pathlib

# Set working directory
code_dir = pathlib.Path.cwd()


## Step 0. Download Datasets ---------------------------------------------------------------- #

# 1. Compustat (from WRDS)
print("Linking to WRDS...\n")
runpy.run_path(path_name = code_dir / "0.0 Download Compustat.py")
print("Compustat data is successfully downloaded.\n")

# 2. CPI (from FRED)
print("Downloading CPI data...\n")
runpy.run_path(path_name = code_dir / "0.1 Download CPI.py")
print("CPI data is successfully downloaded.\n")

# 3. PPI (manually downloaded from BLS)
# NOTE: download the raw PPI files from BLS before running this organizer.
print("Organizing PPI data...\n")
runpy.run_path(path_name = code_dir / "0.2 PPI Data Preparation.py")
print("PPI data is successfully organized.\n")


## Step 1. Theta Estimation ----------------------------------------------------------------- #
dofile_theta = 'your-path/RisingPricesRisingMarkupsReplication/Code/0.3 theta_estimation.do' # need to change the path!
#cmd_theta = ["/Applications/Stata/StataBE.app/Contents/MacOS/StataBE", "do", dofile_theta]  # use for MacOS
cmd_theta = ["C:/Program Files/Stata17/StataBE-64", "do", dofile_theta] # use for Windows
print("Running theta estimation...\n")
subprocess.call(cmd_theta)
print("Theta estimation completed.\n")


## Step 2. Create Main Datasets (Compustat + PPI + CPI) ------------------------------------- #
dofile = 'your-path/RisingPricesRisingMarkupsReplication/Code/0.4 Create Main Datasets.do' # need to change the path!
#cmd = ["/Applications/Stata/StataBE.app/Contents/MacOS/StataBE", "do", dofile]      # apply this line if you are using MacOS
cmd = ["C:/Program Files/Stata17/StataBE-64", "do", dofile] # apply this line if you are using Windows system
print("Creating main datasets...\n")
subprocess.call(cmd)
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
