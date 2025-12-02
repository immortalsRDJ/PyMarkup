import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpl_patches
from matplotlib.pyplot import figure
import sklearn
from sklearn.metrics import r2_score
from sklearn import linear_model
from textwrap import wrap
import pathlib
from path_plot_config import int_dir, out_dir, setplotstyle


def fun_plot(p, ind2d_definition, x_var, y_var, weight, x_label, y_label):
    
    # scatter plot
    g = sns.scatterplot(
        data=p,
        x=x_var, y=y_var, 
        size="dot_size", color='darkgreen', alpha = 1, legend=False)
    
    # calculate the weighted fitted line
    regr = linear_model.LinearRegression()
    X = p[x_var].to_numpy().reshape(-1, 1)
    y = p[y_var].to_numpy().reshape(-1, 1)
    sample_weight=p[weight].to_numpy()
    regr.fit(X, y, sample_weight)

    # plot weighted fitted line
    plt.plot(X, regr.predict(X), color='gray')

    # calculate R^2
    r2 = r2_score(y, regr.predict(X), sample_weight=sample_weight)

    # create a list with one empty handle (or more if needed)
    handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", 
                                 lw=0, alpha=0)] * 1

    # create the corresponding number of labels (= the text you want to display)
    labels = []
    labels.append("R$^2$: {:.4f}".format(r2))

    # create the legend, supressing the blank space of the empty line symbol and the
    # padding between symbol and label by setting handlelenght and handletextpad
    plt.legend(handles, labels, loc='best', fontsize=20, frameon=True,
              fancybox=True, framealpha=0.7, borderpad=0.3,
              handlelength=0, handletextpad=0)
    
    if ind2d_definition != 'Full Sample':
        plt.title('\n'.join(wrap(ind2d_definition,45)))
        
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    
    # beta_hat
    print('beta_hat of ' + ind2d_definition + ' is:')
    print(regr.coef_)
    
    # R^2
    print('R^2 of ' + ind2d_definition + ' is:')
    print(r2)
    

def create_outlier_tab(outlier, x_var, y_var, x_label, y_label):
    outlier = outlier[['gvkey', x_var, y_var,'ind2d_definition']]
    outlier = pd.merge(outlier, char, on=['gvkey'], how='left')
    outlier = outlier[['conm','naics','ind2d_definition', x_var, y_var]]

    outlier.rename(columns={'ind2d_definition':'2-Digit Industry',
                        'conm':'Company Name',
                        'naics':'NAICS',
                        x_var: x_label, 
                        y_var: y_label,
                         }, inplace=True)

    outlier = outlier.sort_values(['2-Digit Industry'])
    return outlier


setplotstyle()


# Set up figure-specific directories
path_fig2 = out_dir / 'Figure 2'
path_ind2d = path_fig2 / 'Industries'
path_outlier_tab = path_fig2 / 'Outliers'


# ------------------------------------------------------------------------------------- #
# Annual, 1980-2018
# ------------------------------------------------------------------------------------- #

# Import data
p = pd.read_csv(int_dir / "scatter_annual.csv")

# Get a list containing 2-d industry description
ind2d = p[['ind2d_definition']]
ind2d = ind2d.drop_duplicates()
ind2d.reset_index(drop=True, inplace=True)
ind2d = ind2d['ind2d_definition'].values.tolist()

# Obtain company name and naics code
char = p[['gvkey','conm','naics']]
char = char.drop_duplicates(subset=['gvkey','naics'], keep='last')

# set the variables and labels for the x-axis and y-axis
x_var = 'cagr_markup'
y_var = 'cagr_PPI'
x_label = 'Markup Growth'
y_label = 'PPI Growth'
weight = 'sale_CPI'


# obtain list of outliers
th0 = -20
th1 = 20
th3 = 100
outlier = p[p.cagr_PPI<th0]
outlier2 = p[p.cagr_PPI>th1]
outlier3 = p[p.cagr_markup>th3]
outlier = pd.concat([outlier, outlier2, outlier3], ignore_index=True)
outlier = outlier.drop_duplicates()
outlier = create_outlier_tab(outlier, x_var, y_var, x_label, y_label)
outlier.to_csv(str(path_outlier_tab) + '/Outliers 1980-2018.csv', index=False)
outlier.to_latex(str(path_outlier_tab) + '/Outliers 1980-2018.tex', index=False)

# Truncate outliers
p = p[p.cagr_PPI>=th0]
p = p[p.cagr_PPI<=th1]
p = p[p.cagr_markup<=th3]

# For the full sample
fun_plot(p, 'Full Sample', x_var, y_var, weight, x_label, y_label)
plt.savefig(path_fig2 / "Growth of PPI and Markup (1980-2018).pdf", bbox_inches="tight")
plt.show()

# For all 2-digit industries
for sector in ind2d:
    print('\n\nGrowth (CAGR) of PPI and Markup (adjusted by CPI, with truncation)\n\n')
    temp = p[p.ind2d_definition == sector]
    
    if temp.empty == True:
        print("Data for " + sector + " is not available.")
    
    else:   
        fun_plot(temp, sector, x_var, y_var, weight, x_label, y_label)
        plt.savefig(str(path_ind2d) + "/1980-2018 " + sector + ".pdf", bbox_inches="tight")
        plt.show()
        


# ------------------------------------------------------------------------------------- #
# Quarterly, 2018Q1-2022Q3
# ------------------------------------------------------------------------------------- #

# Import data
p = pd.read_csv(int_dir / "scatter_quarterly.csv")

# Get a list containing 2-d industry description
ind2d = p[['ind2d_definition']]
ind2d = ind2d.drop_duplicates()
ind2d.reset_index(drop=True, inplace=True)
ind2d = ind2d['ind2d_definition'].values.tolist()

# Obtain company name and naics code
char = p[['gvkey','conm','naics']]
char = char.drop_duplicates(subset=['gvkey','naics'], keep='last')


# obtain list of outliers
th0 = -5
th1 = 5
th2 = -30
th3 = 30
outlier0 = p[p.cagr_PPI<th0]
outlier1 = p[p.cagr_PPI>th1]
outlier2 = p[p.cagr_markup<th2]
outlier3 = p[p.cagr_markup>th3]
outlier = pd.concat([outlier0,outlier1, outlier2, outlier3], ignore_index=True)
outlier = outlier.drop_duplicates()
outlier = create_outlier_tab(outlier, x_var, y_var, x_label, y_label)
outlier.to_csv(str(path_outlier_tab) + '/Outliers 2018Q1-2024Q4.csv', index=False)
outlier.to_latex(str(path_outlier_tab) + '/Outliers 2018Q1-2024Q4.tex', index=False)

# Truncate outliers
p = p[p.cagr_PPI>=th0]
p = p[p.cagr_PPI<=th1]
p = p[p.cagr_markup>=th2]
p = p[p.cagr_markup<=th3]

# For the full sample
fun_plot(p, 'Full Sample', x_var, y_var, weight, x_label, y_label)
plt.savefig(path_fig2 / "Growth of PPI and Markup (2018Q1-2024Q4).pdf", bbox_inches="tight")
plt.show()

# For all 2-digit industries
for sector in ind2d:
    print('\n\nGrowth (CAGR) of PPI and Markup (adjusted by CPI, with truncation)\n\n')
    temp = p[p.ind2d_definition == sector]
    
    if temp.empty == True:
        print("Data for " + sector + " is not available.")
    
    else:   
        fun_plot(temp, sector, x_var, y_var, weight, x_label, y_label)
        plt.savefig(str(path_ind2d) + "/2018-2024 " + sector + ".pdf", bbox_inches="tight")
        plt.show()
