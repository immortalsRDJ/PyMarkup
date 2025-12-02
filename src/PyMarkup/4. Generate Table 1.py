import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import math
import scipy
import os
import pathlib
from path_plot_config import int_dir, out_dir


# Functions for creating regression tables

# WLS 
def table1(data,X,Y,weight):

    # Running regression (all sectors pooled)
    ind = 'All sectors'
    data_WLS = data
    model = sm.WLS(data_WLS[Y], sm.add_constant(data_WLS[X]), weights=data_WLS[weight]).fit()
    beta_hat = model.params[1]
    st_err = model.bse[1]
    p_val = model.pvalues[1]
    r_sq = model.rsquared
    data_coefs = pd.DataFrame([[ind,beta_hat,st_err,r_sq]], columns=list(['ind2d_definition','Estimate','St.Err','R2']))

    # Including sector fixed effects
    ind = 'All sectors with FE'
    ybar = data_WLS[Y].mean()
    xbar = data_WLS[X].mean()
    y = data_WLS[Y] -  data_WLS[Y].groupby(data_WLS['ind2d_definition']).transform('mean') + ybar
    x = data_WLS[X] -  data_WLS[X].groupby(data_WLS['ind2d_definition']).transform('mean') + xbar
    model = sm.WLS(y, sm.add_constant(x), weights=data_WLS[weight]).fit()
    model.df_resid -= (data_WLS['ind2d_definition'].nunique() - 1)
    beta_hat = model.params[1]
    st_err = model.bse[1]
    p_val = model.pvalues[1]
    r_sq = model.rsquared
    data_coefs_temp = pd.DataFrame([[ind,beta_hat,st_err,r_sq]], columns=list(['ind2d_definition','Estimate','St.Err','R2']))
    data_coefs = pd.concat([data_coefs, data_coefs_temp])

    # Checking the number of observations for each 2-digit industry
    n_obs = data.pivot_table(columns=['ind2d_definition'], aggfunc='size')
    n_obs = pd.DataFrame(n_obs)                          # To check the number of observations
    n_obs.reset_index(inplace=True)
    n_obs.rename(columns={0:'N_obs'}, inplace = True) 
    n_obs['N_obs'] = n_obs['N_obs'].astype(int)
    # Selecting sectors with observations equal or more than 30
    n_obs_30 = n_obs[n_obs.N_obs >= 30].copy()

    # Get a list containing 2-d industry description
    ind2d = n_obs_30.ind2d_definition.tolist()

    # Adding OLS estimates for the other sectors
    for ind in ind2d:
        data_WLS = data[data.ind2d_definition == ind]
        model = sm.WLS(data_WLS[Y], sm.add_constant(data_WLS[X]), weights=data_WLS[weight]).fit()
        beta_hat = model.params[1]
        st_err = model.bse[1]
        p_val = model.pvalues[1]
        r_sq = model.rsquared

        data_coefs_temp = pd.DataFrame([[ind,beta_hat,st_err,r_sq]], columns=list(['ind2d_definition','Estimate','St.Err','R2']))
        data_coefs = pd.concat([data_coefs, data_coefs_temp]) 

    data_coefs.reset_index(drop=True, inplace=True)

    # Combining with industry numbers of observations
    data_coefs = pd.merge(data_coefs,n_obs, on='ind2d_definition',how ='outer')
    data_coefs = data_coefs.dropna(subset='Estimate')
    data_coefs.rename(columns={'ind2d_definition':'Industry'}, inplace=True)
    data_coefs.loc[data_coefs['Industry']=='All sectors', 'N_obs'] = n_obs.N_obs.sum()
    data_coefs.loc[data_coefs['Industry']=='All sectors with FE', 'N_obs'] = n_obs.N_obs.sum()
    data_coefs = data_coefs[['Industry','Estimate','St.Err','R2','N_obs']]

    return data_coefs


def save_table1(data_coefs,folder,name,period,stats):
    # Adding column of revenue share matched
    data_coefs = pd.merge(data_coefs,stats,on='Industry', how='outer')
    
    # Adding total share
    data_coefs.loc[data_coefs['Industry']=='All sectors', 'Share matched (revenue)'] = 0.5948
    data_coefs.loc[data_coefs['Industry']=='All sectors with FE', 'Share matched (revenue)']= 0.5948
    data_coefs = data_coefs.dropna(subset='Estimate')
    
    # Saving path
    filename = folder + name + ' ' + period
    file_CSV = filename + '.csv'
    file_tex = filename + '.tex'

    # Saving the table to CSV
    data_coefs.round(4).to_csv(file_CSV)
    # Saving as Tex file
    with open(file_tex,'w') as tf:
        tf.write(data_coefs[['Industry','Estimate','St.Err','R2','N_obs','Share matched (revenue)']]
                 .rename(columns ={'Estimate': r"$\hat{\beta}$",
                                  'St.Err': 'SE',
                                  'R2':r"$R^{2}$",
                                  'N_obs':'Obs'})
                 .round(2)
                 .to_latex(index=False, escape=False, column_format ='lccccc'))
        
    

# Set up figure-specific directories
tab1_dir = out_dir / 'Table 1'
folder = str(tab1_dir) + "/"
folder_sale_weighted = str(tab1_dir) + "/Weighted by CPI-adjusted Sale/"
period = 'Annual'


# # Generating Table 1 Panel 1 (Annual data)

# Import data
p = pd.read_csv(int_dir / "scatter_annual.csv")
p['COGS_CPI'] = p['last_COGS']

# Data truncation

# Truncating the data
data = p[p.cagr_PPI <= 20]
data = data[data.cagr_PPI >= -20]
data = data[data.cagr_markup <= 100]



# Importing Stats table
stats = pd.read_csv(out_dir / "Summary Statistics" / "Stats Table Annual (truncated).csv",usecols=['Definition','share_revenue_matched'])
stats.rename(columns ={'Definition': 'Industry',
                       'share_revenue_matched': 'Share matched (revenue)'}, inplace=True)
print('Share of revenue matched:',stats[stats.Industry == 'Total']['Share matched (revenue)'])


## WLS regression: PPI vs MU change (CAGR)

# SALE as weight

# Variables
Y = 'cagr_PPI'
X = 'cagr_markup'
weight = 'sale_CPI'
name = 'CAGR WLS(Sale)'

# Creating Table 1
data_coefs = table1(data,X,Y,weight)
save_table1(data_coefs,folder_sale_weighted,name,period,stats)


# COGS as weight

# Variables
Y = 'cagr_PPI'
X = 'cagr_markup'
weight = 'COGS_CPI'
name = 'CAGR WLS(COGS)'

# Creating Table 1
data_coefs = table1(data,X,Y,weight)
save_table1(data_coefs,folder,name,period,stats)




# # Generating Panel 2 (Quarterly data)

def save_table1(data_coefs,folder,name,period,stats):
    # Adding column of revenue share matched
    data_coefs = pd.merge(data_coefs,stats,on='Industry', how='outer')
    
    # Adding total share
    data_coefs.loc[data_coefs['Industry']=='All sectors', 'Share matched (revenue)'] = 0.7022
    data_coefs.loc[data_coefs['Industry']=='All sectors with FE', 'Share matched (revenue)']= 0.7022
    data_coefs = data_coefs.dropna(subset='Estimate')
    
    # Saving path
    filename = folder + name + ' ' + period
    file_CSV = filename + '.csv'
    file_tex = filename + '.tex'

    # Saving the table to CSV
    data_coefs.round(4).to_csv(file_CSV)
    # Saving as Tex file
    with open(file_tex,'w') as tf:
        tf.write(data_coefs[['Industry','Estimate','St.Err','R2','N_obs','Share matched (revenue)']]
                 .rename(columns ={'Estimate': r"$\hat{\beta}$",
                                  'St.Err': 'SE',
                                  'R2':r"$R^{2}$",
                                  'N_obs':'Obs'})
                 .round(2)
                 .to_latex(index=False, escape=False, column_format ='lccccc'))


# Import data
p = pd.read_csv(int_dir / "scatter_quarterly.csv")
p['COGS_CPI'] = p['first_COGS']    # Selecting weights

# Truncating the data
data = p[p.cagr_PPI <= 5]
data = data[data.cagr_PPI >= -5]
data = data[data.cagr_markup >= -30]
data = data[data.cagr_markup <= 30]

# Importing Stats table for coverage statistics
stats = pd.read_csv(out_dir / "Summary Statistics" / "Stats Table Quarterly (truncated).csv",usecols=['Definition','share_revenue_matched'])
stats.rename(columns ={'Definition': 'Industry',
                       'share_revenue_matched': 'Share matched (revenue)'}, inplace=True)
print('Share of revenue matched',stats[stats.Industry == 'Total']['Share matched (revenue)'])


# For the saving path
period = 'Quarterly'


# ## WLS: PPI and markups (CAGR)

# SALE as weight

# Variables
Y = 'cagr_PPI'
X = 'cagr_markup'
weight = 'sale_CPI'
name = 'CAGR WLS(Sale)'

# Creating Table 1
data_coefs = table1(data,X,Y,weight)
save_table1(data_coefs,folder_sale_weighted,name,period,stats)


# COGS as weight

# Variables
Y = 'cagr_PPI'
X = 'cagr_markup'
weight = 'COGS_CPI'
name = 'CAGR WLS(COGS)'

# Creating Table 1
data_coefs = table1(data,X,Y,weight)
save_table1(data_coefs,folder,name,period,stats)