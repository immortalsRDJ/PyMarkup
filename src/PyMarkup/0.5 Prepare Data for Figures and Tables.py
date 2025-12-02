# --------------------------------------------------------------------------------------- #
# Prepare Data for Figure 2 and Table 1
# --------------------------------------------------------------------------------------- #

import pandas as pd
import numpy as np
import pathlib
from path_plot_config import data_dir, int_dir


def CAGR(first, last, periods):
    return ((last/first)**(1/periods)-1)*100



# 1. Annual (1980-2018) ----------------------------------------------------------------- #

# Import data
df = pd.read_csv(int_dir / "main_annual.csv")
df = df.dropna(subset=['ppi'])
df.reset_index(drop=True, inplace=True)


# Normalize PPI with CPI
df['PPI_CPI'] = df['ppi']/df['CPI']*100


# (1) Only keep firms that last for 5 years or longer

# Length of firm data truncation
df_y = (df.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year']]
        .agg(['first','last'])
        .reset_index())

df_y['n'] = df_y['year','last'] - df_y['year','first'] + 1
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','n']]

# Combine length of firms data into the main dataframe
df = pd.merge(df,df_y,on='gvkey')
df = df[df.n >= 5]
df.reset_index(drop=True, inplace=True)

# calculate CPI-adjusted COGS and sale
df['COGS_CPI'] = df['cogs'] / df['CPI'] * 100
df['sale_CPI'] = df['sale'] / df['CPI'] * 100

df1980 = df[df.year < 2019]
df1980 = df1980[df1980.year > 1979]
df1980 = df1980.sort_values(['gvkey','year'])

# Get 2-d industry description for each firm
naics = df1980
naics = naics[['gvkey','ind2d_definition']].drop_duplicates()
naics.reset_index(drop=True, inplace=True)

# Obtain sales weight
share = df1980
share['dot_size'] = np.log(share['sale_CPI'])
share = share.drop_duplicates(subset='gvkey', keep='last')
share = share[['gvkey','dot_size','sale_CPI']]

# Obtain company name and naics code
char = df1980[['gvkey','conm','naics']]
char = char.drop_duplicates(subset=['gvkey','naics'], keep='last')

# Get a list containing 2-d industry description
ind2d = df1980[['ind2d_definition']]
ind2d = ind2d.drop_duplicates()
ind2d.reset_index(drop=True, inplace=True)
ind2d = ind2d['ind2d_definition'].values.tolist()


# (2) Calculate CAGR of PPI (adjusted by CPI), change in PPI, change in markup

# Find the first and last observations for each group
df1980 = (df1980.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','firm_level_markup','PPI_CPI','COGS_CPI']]
        .agg(['first','last'])
        .reset_index())

# Calculate the Compound Annual Growth Rate
df1980['first_markup'] = df1980['firm_level_markup','first']
df1980['last_markup'] = df1980['firm_level_markup','last']
df1980['first_PPI'] = df1980['PPI_CPI','first']
df1980['last_PPI'] = df1980['PPI_CPI','last']
df1980['first_COGS'] = df1980['COGS_CPI','first']
df1980['last_COGS'] = df1980['COGS_CPI','last']
df1980['first_year'] = df1980['year','first']
df1980['last_year'] = df1980['year','last']
df1980 = df1980[['gvkey','first_year','last_year','first_markup','last_markup','first_PPI','last_PPI','first_COGS','last_COGS']]
df1980.columns = df1980.columns.droplevel(1)

df1980['periods'] = df1980['last_year'] - df1980['first_year']
df1980['cagr_markup'] = CAGR(df1980['first_markup'], df1980['last_markup'], df1980['periods'])
df1980['cagr_PPI'] = CAGR(df1980['first_PPI'], df1980['last_PPI'], df1980['periods'])
df1980['cagr_COGS'] = CAGR(df1980['first_COGS'], df1980['last_COGS'], df1980['periods'])

p = pd.merge(df1980, naics, on=['gvkey'], how='outer')
p = pd.merge(p, share, on=['gvkey'], how='outer')
p = pd.merge(p, char, on=['gvkey'], how='left')
p['markup_closest_2018'] = p['last_markup']

# Save the processed dataset
p.to_csv(int_dir / 'scatter_annual.csv', index=False)



# 2. Quarterly (2018Q1-2022Q3) ---------------------------------------------------------- #

# Import data
df = pd.read_csv(int_dir / "main_quarterly.csv")
df = df.dropna(subset=['ppi'])
df.reset_index(drop=True, inplace=True)
df = df.dropna(subset='firm_level_markup')

# Normalize PPI with CPI
df['PPI_CPI'] = df['ppi']/df['CPI']*100


# (1) Only keep firms that last for 5 years or longer

# Length of firm data truncation
df_y = (df.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year']]
        .agg(['first','last'])
        .reset_index())

df_y['n'] = df_y['year','last'] - df_y['year','first'] + 1
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','n']]

# Combine length of firms data into the main dataframe
df = pd.merge(df,df_y,on='gvkey')
df = df[df.n >= 5]
df.reset_index(drop=True, inplace=True)

# calculate CPI-adjusted COGS & SALE
df['COGS_CPI'] = df['cogsq'] / df['CPI'] * 100
df['sale_CPI'] = df['saleq'] / df['CPI'] * 100

df2018 = df[df.year > 2017].copy()
df2018 = df2018.sort_values(['gvkey','quarter'])

# Get 2-d industry description for each firm
naics = df2018
naics = naics[['gvkey','ind2d_definition']].drop_duplicates()
naics.reset_index(drop=True, inplace=True)

# Obtain sales weight
share = df2018
share['dot_size'] = np.log(share['sale_CPI'])
share = share.drop_duplicates(subset='gvkey', keep='first')
share = share[['gvkey','dot_size','sale_CPI']]

# Obtain company name and naics code
char = df2018[['gvkey','conm','naics']]
char = char.drop_duplicates(subset=['gvkey','naics'], keep='last')

# Get a list containing 2-d industry description
ind2d = df2018[['ind2d_definition']]
ind2d = ind2d.drop_duplicates()
ind2d.reset_index(drop=True, inplace=True)
ind2d = ind2d['ind2d_definition'].values.tolist()

# Import quarterly index
index_quarter = pd.read_csv(data_dir / "Other" / "indexed_quarter.csv")
index_quarter.rename(columns={'quarter':'first_quarter', 'index':'first_quarter_index'}, inplace=True)


# (2) Calculate CAGR of PPI (adjusted by CPI), change in PPI, change in markup

# Find the first and last observations for each group
df2018 = (df2018.sort_values(['gvkey','quarter'])
        .groupby(['gvkey'])[['quarter','firm_level_markup','PPI_CPI','COGS_CPI']]
        .agg(['first','last'])
        .reset_index())

# Calculate the Compound Quarterly Growth Rate
df2018['first_markup'] = df2018['firm_level_markup','first']
df2018['last_markup'] = df2018['firm_level_markup','last']
df2018['first_PPI'] = df2018['PPI_CPI','first']
df2018['last_PPI'] = df2018['PPI_CPI','last']
df2018['first_COGS'] = df2018['COGS_CPI','first']
df2018['last_COGS'] = df2018['COGS_CPI','last']
df2018['first_quarter'] = df2018['quarter','first']
df2018['last_quarter'] = df2018['quarter','last']
df2018 = df2018[['gvkey','first_quarter','last_quarter','first_markup','last_markup','first_PPI','last_PPI','first_COGS','last_COGS']]
df2018.columns = df2018.columns.droplevel(1)

df2018 = pd.merge(df2018, index_quarter, on=['first_quarter'])
index_quarter.rename(columns={'first_quarter':'last_quarter', 'first_quarter_index':'last_quarter_index'}, inplace=True)
df2018 = pd.merge(df2018, index_quarter, on=['last_quarter'])

df2018['periods'] = df2018['last_quarter_index'] - df2018['first_quarter_index']
df2018['cagr_markup'] = CAGR(df2018['first_markup'], df2018['last_markup'], df2018['periods'])
df2018['cagr_PPI'] = CAGR(df2018['first_PPI'], df2018['last_PPI'], df2018['periods'])
df2018['cagr_COGS'] = CAGR(df2018['first_COGS'], df2018['last_COGS'], df2018['periods'])

p = pd.merge(df2018, naics, on=['gvkey'], how='outer')
p = pd.merge(p, share, on=['gvkey'], how='outer')
p = pd.merge(p, char, on=['gvkey'], how='left')

p['markup_closest_2018'] = p['first_markup']

# Save the processed dataset
p.to_csv(int_dir / 'scatter_quarterly.csv', index=False)

