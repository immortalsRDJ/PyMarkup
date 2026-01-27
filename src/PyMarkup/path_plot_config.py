# For files and paths

import pathlib
import os


# File Directories
# Derive project root from this file location so scripts work from anywhere.
proj_dir = pathlib.Path(__file__).resolve().parents[2]
code_dir = proj_dir / 'src' / 'PyMarkup'
data_dir = proj_dir / 'Input'
int_dir = proj_dir / 'Intermediate'
out_dir = proj_dir / 'Output'


# Fred API key for downloading CPI data
# SECURITY: API key has been moved to config file
# See .env.example or config.yaml.example for setup instructions
try:
    from .config_loader import get_fred_api_key
    fred_apikey = get_fred_api_key()
    if fred_apikey is None:
        import warnings
        warnings.warn(
            "FRED API key not found. Please set FRED_API_KEY in:\n"
            "  1. Environment variable: export FRED_API_KEY='your_key'\n"
            "  2. .env file (copy from .env.example)\n"
            "  3. config.yaml file (copy from config.yaml.example)\n"
            "Get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        )
except ImportError:
    fred_apikey = None

# For plotting

# Plot Configuration

def setplotstyle_agg():
    from cycler import cycler
    import seaborn as sns
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.style.use('seaborn-v0_8-whitegrid')

    matplotlib.rcParams.update({'font.size': 26})
    plt.rcParams["figure.figsize"] = (15,10)
    plt.rc('font', size=26)          # controls default text sizes
    plt.rc('axes', titlesize=26)     # fontsize of the axes title
    plt.rc('axes', labelsize=26)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=26)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=26)    # fontsize of the tick labels
    plt.rc('legend', fontsize=26)    # legend fontsize
    plt.rc('figure', titlesize=26)
    plt.rc(
        'axes',
        prop_cycle=cycler(
            color=[
                '#252525',
                '#636363',
                '#969696',
                '#bdbdbd']) *
        cycler(
            linestyle=[
                '-',
                ':',
                '--',
                '-.']))
    plt.rc('lines', linewidth=3)
    
    
def setplotstyle():
    from cycler import cycler
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.style.use('seaborn-v0_8-whitegrid')
    matplotlib.rcParams.update({'font.size': 26})
    plt.rcParams["figure.figsize"] = (15,10)
    plt.rc('font', size=26)          # controls default text sizes
    plt.rc('axes', titlesize=26)     # fontsize of the axes title
    plt.rc('axes', labelsize=26)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=26)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=26)    # fontsize of the tick labels
    plt.rc('legend', fontsize=26)    # legend fontsize
    plt.rc('figure', titlesize=26)
    plt.rc(
        'axes',
        prop_cycle=cycler(
            color=[
                '#252525',
                '#636363',
                '#969696',
                '#bdbdbd']) *
        cycler(
            linestyle=[
                '-',
                ':',
                '--',
                '-.']))
    plt.rc('lines', linewidth=3)
    

