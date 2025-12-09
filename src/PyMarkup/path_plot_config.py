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
fred_apikey = '1aa8f608e651844ecccf03f08aba2dc3' # insert your Fred API key here

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
    

