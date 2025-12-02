import pandas as pd
import os
import pathlib
from path_plot_config import data_dir, int_dir, out_dir

# Set up table-specific directories
tab_dir = out_dir / 'Summary Statistics'



# ---------------------------------------------------------------------------------------- #
# For the annual data
# ---------------------------------------------------------------------------------------- #

# ## Creating tables of statistics

# Importing cleaned Compustat data

df_cpi = pd.read_csv(int_dir / "main_annual.csv")

# Normalizing PPI with CPI
df_cpi['PPI_CPI'] = df_cpi['ppi']/df_cpi['CPI']*100

main = df_cpi[['gvkey','year','cogs','sale','ind2d','firm_level_markup','ppi','CPI','ind2d_definition']].copy()

main.rename(columns={'sale':'sale_raw',
                   'ppi':'PPI'}, inplace=True)
main = main[main.year != 2022]
main.reset_index(drop=True, inplace=True)

# CPI inflation adjusting the sales revenue
main['sale'] = (main['sale_raw']/main['CPI'])*100

# Editing the 2-digit industry codes
main['ind2d'] = main['ind2d'].astype(str)

# Manufacturing
main.loc[main.ind2d == '31', 'ind2d'] = '31-33'
main.loc[main.ind2d == '32', 'ind2d'] = '31-33'
main.loc[main.ind2d == '33', 'ind2d'] = '31-33'

# Retail trade
main.loc[main.ind2d == '44', 'ind2d'] = '44-45'
main.loc[main.ind2d == '45', 'ind2d'] = '44-45'

# Transportation and warehousing
main.loc[main.ind2d == '48', 'ind2d'] = '48-49'
main.loc[main.ind2d == '49', 'ind2d'] = '48-49'


# Adjusting the sample

# Length of firm data truncation
df_y = (main.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d','ind2d_definition']]
        .agg(['first','last'])
        .reset_index())
df_y['periods'] = df_y['year','last'] - df_y['year','first'] 
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','periods']]

# Combine length of firms data into the main dataframe
df = pd.merge(main,df_y,on='gvkey')
df = df[df.periods >= 4]

# Choosing the years
df = df[df.year >= 1980]
df = df[df.year <= 2018]
df.reset_index(drop=True, inplace=True)


# ## Data for all firms

# Column (i) Number of all firms by 2-digit industries

firms = df[['ind2d','gvkey']]
firms = firms.drop_duplicates(subset = 'gvkey')

n_firms = firms.pivot_table(columns=['ind2d'], aggfunc='size')
n_firms = pd.DataFrame(n_firms)                          # To check the number of observations
n_firms.reset_index(inplace=True)
n_firms.rename(columns={0:'N_firms'}, inplace=True) 

# Total number of firms
print('Total number of firms is',n_firms.N_firms.sum())


# For Column (iii) summing up revenue for all firms

df_revenue = df.groupby('ind2d').sum(numeric_only = True)
df_revenue = df_revenue['sale']
df_revenue = pd.DataFrame(df_revenue)
df_revenue.reset_index(inplace=True)
df_revenue

col123 = pd.merge(n_firms, df_revenue, on='ind2d')


# ## Data for matched firms

# For Column (ii) share of all firms matched to PPI data

df_matched = main.dropna(subset=['PPI']).copy()

df_matched.rename(columns={'cogs_D':'cogs',
                    'sale_D':'sale',
                   'ppi':'PPI'}, inplace=True)

# Adjusting the sample
# Length of firm data truncation
df_y = (df_matched.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d','ind2d_definition']]
        .agg(['first','last'])
        .reset_index())
df_y['periods'] = df_y['year','last'] - df_y['year','first'] 
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','periods']]

# Combine length of firms data into the main dataframe
df_matched = pd.merge(df_matched,df_y,on='gvkey')
df_matched = df_matched[df_matched.periods >= 4]

# Choosing the years
df_matched = df_matched[df_matched.year >= 1980]
df_matched = df_matched[df_matched.year <= 2018]
df_matched.reset_index(drop=True, inplace=True)


# Number of firms per 2-digit industry

firms_matched = df_matched[['ind2d','gvkey']]
firms_matched = firms_matched.drop_duplicates(subset = 'gvkey')

n_firms_matched = firms_matched.pivot_table(columns=['ind2d'], aggfunc='size')
n_firms_matched = pd.DataFrame(n_firms_matched)                          # To check the number of observations
n_firms_matched.reset_index(inplace=True)
n_firms_matched.rename(columns={0:'N_firms_m'}, inplace=True) 

# Number of matched firms
print('Total number of firms matched:',n_firms_matched.N_firms_m.sum())


# Revenue share of the matched firms

df_revenue_m = df_matched.groupby('ind2d').sum(numeric_only = True)
df_revenue_m = df_revenue_m['sale']
df_revenue_m = pd.DataFrame(df_revenue_m)
df_revenue_m.reset_index(inplace=True)
df_revenue_m.rename(columns={'sale':'sale_m'}, inplace=True) 

# Adding columns to the main table
col123_m = pd.merge(n_firms_matched,df_revenue_m,on='ind2d')
col123_f = pd.merge(col123,col123_m,on='ind2d',how ='outer')
col123_f  = col123_f.fillna(0)


# Calculating totals and adding as a row

col123_t = col123_f.sum(numeric_only=True)
col123_t = pd.DataFrame(col123_t).T
col123_t = pd.concat([col123_t,col123_f])
col123_t.reset_index(drop=True, inplace=True)


# Calculating values for Columns ii-iii

col123_t['share_firms_matched'] = col123_t['N_firms_m'] / col123_t['N_firms']
col123_t['share_revenue_matched'] = col123_t['sale_m'] / col123_t['sale']

col123_t = col123_t[['ind2d','N_firms','share_firms_matched','share_revenue_matched']].copy()
col123_t.reset_index(drop=True, inplace=True)


# ## Adding column (iv)

# Column (iv) number of 6-digit codes in matched data

# Importing main dataset to get 6-digit industries
naics = pd.read_csv(int_dir / "main_annual.csv", usecols = ['gvkey','naics'])
naics = naics.drop_duplicates(subset = 'gvkey')

# Merging with the data for matched firms
df_matched = pd.merge(df_matched,naics,on='gvkey')
df_matched['naics'] = df_matched['naics'].astype(int)
df_matched['naics'] = df_matched['naics'].astype(str)

df_6digit = df_matched[['ind2d','naics']]
df_6digit = df_6digit.drop_duplicates(subset = 'naics')
df_6digit=df_6digit[df_6digit.naics.apply(lambda x: len(str(x))==6)]

n_6digit = df_6digit.pivot_table(columns=['ind2d'], aggfunc='size')
n_6digit = pd.DataFrame(n_6digit)                          
n_6digit.reset_index(inplace=True)
n_6digit.rename(columns={0:'N_6d_codes'}, inplace=True) 

stat_table = pd.merge(col123_t,n_6digit,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)
stat_table['N_6d_codes'] = stat_table['N_6d_codes'].astype(int)


# ### Adding column (v)

# Column (v) average length of firm data

df_years = (df_matched.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d','ind2d_definition']]
        .agg(['first','last'])
        .reset_index())
df_years['periods'] = df_years['year','last'] - df_years['year','first'] + 1
df_years.columns = df_years.columns.map(','.join).str.strip(',')
df_years = df_years[['ind2d,first','periods']]
df_years.rename(columns={'ind2d,first':'ind2d'}, inplace=True)
mean_periods = df_years['periods'].mean()

df_n_years = df_years.groupby('ind2d').mean(numeric_only = True)
stat_table = pd.merge(stat_table,df_n_years,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)

# Adding industry definitions

defs = df[['ind2d','ind2d_definition']]
defs = defs.drop_duplicates(subset = 'ind2d')

stat_table = pd.merge(stat_table,defs,on='ind2d',how='outer')

stat_table.loc[0,'ind2d_definition'] = 'Total'
stat_table.loc[0,'N_6d_codes'] = stat_table.N_6d_codes[1:].sum()
stat_table.loc[0,'periods'] = mean_periods
stat_table.loc[0,'ind2d'] = 'Total'

# Formatting the table

stat_table_annual = stat_table[['ind2d','ind2d_definition','N_firms',
                         'share_firms_matched','share_revenue_matched','N_6d_codes','periods']]
stat_table_annual.rename(columns={'ind2d':'Industry',
                          'ind2d_definition':'Definition',
                          'N_firms':'Number of firms',
                          'share_firms_matched': 'Share of firms matched',
                          'N_6d_codes':'Number of 6-digit industries',
                          'periods':'Number of periods (years)'},inplace=True)



# Exporting the table
stat_table_annual.round(4).to_csv(tab_dir / 'Stats Table Annual.csv')

# Saving as Tex file
with open(tab_dir / 'Stats Table Annual.tex','w') as tf:
    tf.write(stat_table_annual
             .rename(columns ={'share_revenue_matched': 'Share of revenue matched'})
             .round(2)
             .to_latex(index=False))


# ## Generating table of statistics (with truncation)

# For Column (ii) share of all firms matched to PPI data

df_matched = main.dropna(subset=['PPI']).copy()

df_matched.rename(columns={'cogs_D':'cogs',
                    'sale_D':'sale',
                   'ppi':'PPI'}, inplace=True)

# Adjusting the sample
# Length of firm data truncation
df_y = (df_matched.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d','ind2d_definition']]
        .agg(['first','last'])
        .reset_index())
df_y['periods'] = df_y['year','last'] - df_y['year','first'] 
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','periods']]

# Combine length of firms data into the main dataframe
df_matched = pd.merge(df_matched,df_y,on='gvkey')
df_matched = df_matched[df_matched.periods >= 4]

# Choosing the years
df_matched = df_matched[df_matched.year >= 1980]
df_matched = df_matched[df_matched.year <= 2018]
df_matched.reset_index(drop=True, inplace=True)

# Importing CAGR data for truncation (following Figure 2)

cagr = pd.read_csv(int_dir / "scatter_annual.csv",usecols=['gvkey','cagr_PPI','cagr_markup'])
cagr = cagr.drop_duplicates()

df_matched = pd.merge(df_matched,cagr,on='gvkey')

# Applying Figure 2 truncations
# Truncating the data
df_matched = df_matched[df_matched.cagr_PPI <= 20]
df_matched = df_matched[df_matched.cagr_PPI >= -20]
df_matched = df_matched[df_matched.cagr_markup <= 100]

# Number of firms per 2-digit industry

firms_matched = df_matched[['ind2d','gvkey']]
firms_matched = firms_matched.drop_duplicates(subset = 'gvkey')

n_firms_matched = firms_matched.pivot_table(columns=['ind2d'], aggfunc='size')
n_firms_matched = pd.DataFrame(n_firms_matched)                          
n_firms_matched.reset_index(inplace=True)
n_firms_matched.rename(columns={0:'N_firms_m'}, inplace=True) 

# Number of matched firms
print('Number of matched firms after truncation:',n_firms_matched.N_firms_m.sum())


# Revenue share of the matched firms

df_revenue_m = df_matched.groupby('ind2d').sum(numeric_only = True)
df_revenue_m = df_revenue_m['sale']
df_revenue_m = pd.DataFrame(df_revenue_m)
df_revenue_m.reset_index(inplace=True)
df_revenue_m.rename(columns={'sale':'sale_m'}, inplace=True) 

# Adding columns to the main table

col123_m = pd.merge(n_firms_matched,df_revenue_m,on='ind2d')
col123_f = pd.merge(col123,col123_m,on='ind2d',how ='outer')
col123_f  = col123_f.fillna(0)

# Calculating totals and adding as a row

col123_t = col123_f.sum(numeric_only=True)
col123_t = pd.DataFrame(col123_t).T
col123_t = pd.concat([col123_t,col123_f])
col123_t.reset_index(drop=True, inplace=True)

# Calculating values for Columns ii-iii

col123_t['share_firms_matched'] = col123_t['N_firms_m'] / col123_t['N_firms']
col123_t['share_revenue_matched'] = col123_t['sale_m'] / col123_t['sale']

col123_t = col123_t[['ind2d','N_firms','share_firms_matched','share_revenue_matched']].copy()
col123_t.reset_index(drop=True, inplace=True)

# Column (iv) number of 6-digit codes in matched data

# Importing dataset to get 6-digit industries
naics = pd.read_csv(int_dir / "main_annual.csv", usecols = ['gvkey','naics'])
naics = naics.drop_duplicates(subset = 'gvkey')

# Merging with the data for matched firms
df_matched = pd.merge(df_matched,naics,on='gvkey')
df_matched['naics'] = df_matched['naics'].astype(int)
df_matched['naics'] = df_matched['naics'].astype(str)

df_6digit = df_matched[['ind2d','naics']]
df_6digit = df_6digit.drop_duplicates(subset = 'naics')
df_6digit=df_6digit[df_6digit.naics.apply(lambda x: len(str(x))==6)]

n_6digit = df_6digit.pivot_table(columns=['ind2d'], aggfunc='size')
n_6digit = pd.DataFrame(n_6digit)                          
n_6digit.reset_index(inplace=True)
n_6digit.rename(columns={0:'N_6d_codes'}, inplace=True) 

stat_table = pd.merge(col123_t,n_6digit,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)
stat_table['N_6d_codes'] = stat_table['N_6d_codes'].astype(int)


# Column (v) average length of firm data

df_years = (df_matched.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d','ind2d_definition']]
        .agg(['first','last'])
        .reset_index())
df_years['periods'] = df_years['year','last'] - df_years['year','first'] + 1
df_years.columns = df_years.columns.map(','.join).str.strip(',')
df_years = df_years[['ind2d,first','periods']]
df_years.rename(columns={'ind2d,first':'ind2d'}, inplace=True)
mean_periods = df_years['periods'].mean()

df_n_years = df_years.groupby('ind2d').mean(numeric_only = True)
stat_table = pd.merge(stat_table,df_n_years,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)

# Adding industry definitions

defs = df[['ind2d','ind2d_definition']]
defs = defs.drop_duplicates(subset = 'ind2d')

stat_table = pd.merge(stat_table,defs,on='ind2d',how='outer')

stat_table.loc[0,'ind2d_definition'] = 'Total'
stat_table.loc[0,'N_6d_codes'] = stat_table.N_6d_codes[1:].sum()
stat_table.loc[0,'periods']= mean_periods
stat_table.loc[0,'ind2d'] = 'Total'

# Formatting the table

stat_table_annual = stat_table[['ind2d','ind2d_definition','N_firms',
                         'share_firms_matched','share_revenue_matched','N_6d_codes','periods']]
stat_table_annual.rename(columns={'ind2d':'Industry',
                          'ind2d_definition':'Definition',
                          'N_firms':'Number of firms',
                          'share_firms_matched': 'Share of firms matched',
                          'N_6d_codes':'Number of 6-digit industries',
                          'periods':'Number of periods (years)'},inplace=True)


# Exporting the table
stat_table_annual.round(4).to_csv(tab_dir / 'Stats Table Annual (truncated).csv')

# Saving as Tex file
with open(tab_dir / 'Stats Table Annual (truncated).tex','w') as tf:
    tf.write(stat_table_annual
             .rename(columns ={'share_revenue_matched': 'Share of revenue matched'})
             .round(2)
             .to_latex(index=False))






# ---------------------------------------------------------------------------------------- #
# For the quarterly data
# ---------------------------------------------------------------------------------------- #

# ## Generating table of statistics (Quarterly)

# Importing cleaned Compustat data

df_cpi = pd.read_csv(int_dir / "main_quarterly.csv")

df_cpi = df_cpi.dropna(subset='firm_level_markup')

# Normalizing PPI with CPI
df_cpi['PPI_CPI'] = df_cpi['ppi']/df_cpi['CPI']*100

main = df_cpi[['gvkey','year','quarter','cogsq','saleq','ind2d','firm_level_markup','ppi','CPI','ind2d_definition']].copy()

main.rename(columns={'saleq':'sale_raw',
                   'ppi':'PPI'}, inplace=True)
main = main[main.quarter != '2022Q4']
main.reset_index(drop=True, inplace=True)

# Deflating sales revenue using CPI
main['sale'] = (main['sale_raw']/main['CPI'])*100

# Editing the 2-digit industry codes
main['ind2d'] = main['ind2d'].astype(int)
main['ind2d'] = main['ind2d'].astype(str)
main['ind2d'] = main['ind2d'].astype(str)

# Manufacturing
main.loc[main.ind2d == '31', 'ind2d'] = '31-33'
main.loc[main.ind2d == '32', 'ind2d'] = '31-33'
main.loc[main.ind2d == '33', 'ind2d'] = '31-33'

# Retail trade
main.loc[main.ind2d == '44', 'ind2d'] = '44-45'
main.loc[main.ind2d == '45', 'ind2d'] = '44-45'

# Transportation and warehousing
main.loc[main.ind2d == '48', 'ind2d'] = '48-49'
main.loc[main.ind2d == '49', 'ind2d'] = '48-49'

# Adjusting the sample

# Length of firm data truncation

df_y = (main.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d']]
        .agg(['first','last'])
        .reset_index())
df_y['periods'] = df_y['year','last'] - df_y['year','first']
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','periods']]

# Combine length of firms data into the main dataframe
df = pd.merge(main,df_y,on='gvkey')
df = df[df.periods >= 4]
df = df[df.year >= 2018]
df.reset_index(drop=True, inplace=True)

# Including period index
index_quarter = pd.read_csv(data_dir / "Other" / "indexed_quarter.csv")
index_quarter.rename(columns={'index':'quarter_index'}, inplace=True)

# Merging with the data
df = pd.merge(df,index_quarter, on ='quarter')
df


# ## Data for all firms

# Column (i) Number of firms by 2-digit industries

firms = df[['ind2d','gvkey']]
firms = firms.drop_duplicates(subset = 'gvkey')

n_firms = firms.pivot_table(columns=['ind2d'], aggfunc='size')
n_firms = pd.DataFrame(n_firms)                          # To check the number of observations
n_firms.reset_index(inplace=True)
n_firms.rename(columns={0:'N_firms'}, inplace=True) 

print('Total number of firms:',n_firms.N_firms.sum())

# For Column (iii) summing up revenue for all firms

df_revenue = df.groupby('ind2d').sum(numeric_only = True)
df_revenue = df_revenue['sale']
df_revenue = pd.DataFrame(df_revenue)
df_revenue.reset_index(inplace=True)
df_revenue

col123 = pd.merge(n_firms, df_revenue, on='ind2d')


# ## Data for matched firms

# For Column (ii) share of all firms matched to PPI data

df_matched = main.dropna(subset=['PPI'])

# Dropping firms that have data for less than 5 years
df_y = (df_matched.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d']]
        .agg(['first','last'])
        .reset_index())
df_y['periods'] = df_y['year','last'] - df_y['year','first']
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','periods']]

# Combine length of firms data into the main dataframe
df_matched = pd.merge(df_matched,df_y,on='gvkey')
df_matched = df_matched[df_matched.periods >= 4]
#df_matched = df_matched[df_matched.year >= 2018]

# Adding index for quarters
df_matched = pd.merge(df_matched,index_quarter, on ='quarter')
df_matched.reset_index(drop=True, inplace=True)
df_matched

# Number of firms in 2-digit industries

firms_matched = df_matched[['ind2d','gvkey']]
firms_matched = firms_matched.drop_duplicates(subset = 'gvkey')

n_firms_matched = firms_matched.pivot_table(columns=['ind2d'], aggfunc='size')
n_firms_matched = pd.DataFrame(n_firms_matched)                          # To check the number of observations
n_firms_matched.reset_index(inplace=True)
n_firms_matched.rename(columns={0:'N_firms_m'}, inplace=True) 

print('Total number of matched firms:',n_firms_matched.N_firms_m.sum())


df_revenue_m = df_matched.groupby('ind2d').sum(numeric_only = True)
df_revenue_m = df_revenue_m['sale']
df_revenue_m = pd.DataFrame(df_revenue_m)
df_revenue_m.reset_index(inplace=True)
df_revenue_m.rename(columns={'sale':'sale_m'}, inplace=True) 

col123_m = pd.merge(n_firms_matched,df_revenue_m,on='ind2d')
col123_f = pd.merge(col123,col123_m,on='ind2d',how ='outer')
col123_f  = col123_f.fillna(0)


# Calculating total and adding as a row
col123_t = col123_f.sum(numeric_only=True)
col123_t = pd.DataFrame(col123_t).T
col123_t = pd.concat([col123_t,col123_f])
#col123_t = col123_t.append(col123_f, ignore_index=True)
col123_t.reset_index(drop=True, inplace=True)
col123_t

# Calculating values for Columns ii-iii
col123_t['share_firms_matched'] = col123_t['N_firms_m'] / col123_t['N_firms']
col123_t['share_revenue_matched'] = col123_t['sale_m'] / col123_t['sale']
col123_t = col123_t[['ind2d','N_firms','share_firms_matched','share_revenue_matched']].copy()
col123_t.reset_index(drop=True, inplace=True)


# ## Adding column (iv)

# Column (iv) number of 6-digit codes in matched data

# Importing main dataset to get 6-digit industries
naics = pd.read_csv(int_dir / "main_quarterly.csv", usecols = ['gvkey','naics'])
naics = naics.drop_duplicates(subset = 'gvkey')

# Merging with the data for matched firms
df_matched = pd.merge(df_matched,naics,on='gvkey')
df_matched['naics'] = df_matched['naics'].astype(int)
df_matched['naics'] = df_matched['naics'].astype(str)

# Keep only 6-digit industry codes
df_6digit = df_matched[['ind2d','naics']]
df_6digit = df_6digit.drop_duplicates(subset = 'naics')
df_6digit=df_6digit[df_6digit.naics.apply(lambda x: len(str(x))==6)]

n_6digit = df_6digit.pivot_table(columns=['ind2d'], aggfunc='size')
n_6digit = pd.DataFrame(n_6digit)                          # To check the number of observations
n_6digit.reset_index(inplace=True)
n_6digit.rename(columns={0:'N_6d_codes'}, inplace=True) 

stat_table = pd.merge(col123_t,n_6digit,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)
stat_table['N_6d_codes'] = stat_table['N_6d_codes'].astype(int)


# Column (v) average length of firm data

df_years = (df_matched.sort_values(['gvkey','quarter_index'])
        .groupby(['gvkey'])[['quarter_index','ind2d','ind2d_definition']]
        .agg(['first','last'])
        .reset_index())
df_years['periods'] = df_years['quarter_index','last'] - df_years['quarter_index','first'] + 1
df_years.columns = df_years.columns.map(','.join).str.strip(',')
df_years = df_years[['ind2d,first','periods']]
df_years.rename(columns={'ind2d,first':'ind2d'}, inplace=True)
mean_periods = df_years['periods'].mean()

df_n_years = df_years.groupby('ind2d').mean(numeric_only = True)
stat_table = pd.merge(stat_table,df_n_years,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)

# Adding industry definitions

defs = df[['ind2d','ind2d_definition']]
defs = defs.drop_duplicates(subset = 'ind2d')

stat_table = pd.merge(stat_table,defs,on='ind2d',how='outer')

stat_table.loc[0,'ind2d_definition'] = 'Total'
stat_table.loc[0,'N_6d_codes'] = stat_table.N_6d_codes[1:].sum()
stat_table.loc[0,'periods'] = mean_periods
stat_table.loc[0,'ind2d'] = 'Total'

# Formatting the table

stat_table_quarterly = stat_table[['ind2d','ind2d_definition','N_firms',
                         'share_firms_matched','share_revenue_matched','N_6d_codes','periods']]
stat_table_quarterly.rename(columns={'ind2d':'Industry',
                          'ind2d_definition':'Definition',
                          'N_firms':'Number of firms',
                          'share_firms_matched': 'Share of firms matched',
                          'N_6d_codes':'Number of 6-digit industries',
                          'periods':'Number of periods (quarters)'},inplace=True)

stat_table_quarterly


# Exporting the table

stat_table_quarterly.round(4).to_csv(tab_dir / 'Stats Table Quarterly.csv')

# Saving as Tex file
with open(tab_dir / 'Stats Table Quarterly.tex','w') as tf:
    tf.write(stat_table_quarterly
             .rename(columns ={'share_revenue_matched': 'Share of revenue matched'})
             .round(2)
             .to_latex(index=False))




# ## Table of statistics (quarterly, truncated)

# For Column (ii) share of all firms matched to PPI data

df_matched = main.dropna(subset=['PPI'])

# Dropping firms that have data for less than 5 years
df_y = (df_matched.sort_values(['gvkey','year'])
        .groupby(['gvkey'])[['year','ind2d']]
        .agg(['first','last'])
        .reset_index())
df_y['periods'] = df_y['year','last'] - df_y['year','first']
df_y.columns = df_y.columns.map(','.join).str.strip(',')
df_y = df_y[['gvkey','periods']]

# Combine length of firms data into the main dataframe
df_matched = pd.merge(df_matched,df_y,on='gvkey')
df_matched = df_matched[df_matched.periods >= 4]
#df_matched = df_matched[df_matched.year >= 2018]

# Adding index for quarters
df_matched = pd.merge(df_matched,index_quarter, on ='quarter')
df_matched.reset_index(drop=True, inplace=True)


# Importing CAGR data for truncation (following Figure 2)

cagr = pd.read_csv(int_dir / "scatter_quarterly.csv",usecols=['gvkey','cagr_PPI','cagr_markup'])
cagr = cagr.drop_duplicates()

df_matched = pd.merge(df_matched,cagr,on='gvkey')

# Applying Figure 2 truncations
# Truncating the data
df_matched = df_matched[df_matched.cagr_PPI <= 5]
df_matched = df_matched[df_matched.cagr_PPI >= -5]
df_matched = df_matched[df_matched.cagr_markup >= -30]
df_matched = df_matched[df_matched.cagr_markup <= 30]
df_matched


# Number of firms in 2-digit industries

firms_matched = df_matched[['ind2d','gvkey']]
firms_matched = firms_matched.drop_duplicates(subset = 'gvkey')

n_firms_matched = firms_matched.pivot_table(columns=['ind2d'], aggfunc='size')
n_firms_matched = pd.DataFrame(n_firms_matched)                          # To check the number of observations
n_firms_matched.reset_index(inplace=True)
n_firms_matched.rename(columns={0:'N_firms_m'}, inplace=True) 

print('Total number of matched firms:',n_firms_matched.N_firms_m.sum())


# Calculating revenue share

df_revenue_m = df_matched.groupby('ind2d').sum(numeric_only = True)
df_revenue_m = df_revenue_m['sale']
df_revenue_m = pd.DataFrame(df_revenue_m)
df_revenue_m.reset_index(inplace=True)
df_revenue_m.rename(columns={'sale':'sale_m'}, inplace=True) 

col123_m = pd.merge(n_firms_matched,df_revenue_m,on='ind2d')
col123_f = pd.merge(col123,col123_m,on='ind2d',how ='outer')
col123_f  = col123_f.fillna(0)


# Calculating total and adding as a row
col123_t = col123_f.sum(numeric_only=True)
col123_t = pd.DataFrame(col123_t).T
col123_t = pd.concat([col123_t,col123_f])
#col123_t = col123_t.append(col123_f, ignore_index=True)
col123_t.reset_index(drop=True, inplace=True)
col123_t

# Calculating values for Columns ii-iii
col123_t['share_firms_matched'] = col123_t['N_firms_m'] / col123_t['N_firms']
col123_t['share_revenue_matched'] = col123_t['sale_m'] / col123_t['sale']
col123_t = col123_t[['ind2d','N_firms','share_firms_matched','share_revenue_matched']].copy()
col123_t.reset_index(drop=True, inplace=True)


# Column (iv) number of 6-digit codes in matched data

# Importing main dataset to get 6-digit industries
naics = pd.read_csv(int_dir / "main_quarterly.csv", usecols = ['gvkey','naics'])
naics = naics.drop_duplicates(subset = 'gvkey')

# Merging with the data for matched firms
df_matched = pd.merge(df_matched,naics,on='gvkey')
df_matched['naics'] = df_matched['naics'].astype(int)
df_matched['naics'] = df_matched['naics'].astype(str)

# Keep only 6-digit industry codes
df_6digit = df_matched[['ind2d','naics']]
df_6digit = df_6digit.drop_duplicates(subset = 'naics')
df_6digit=df_6digit[df_6digit.naics.apply(lambda x: len(str(x))==6)]

n_6digit = df_6digit.pivot_table(columns=['ind2d'], aggfunc='size')
n_6digit = pd.DataFrame(n_6digit)                          # To check the number of observations
n_6digit.reset_index(inplace=True)
n_6digit.rename(columns={0:'N_6d_codes'}, inplace=True) 

stat_table = pd.merge(col123_t,n_6digit,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)
stat_table['N_6d_codes'] = stat_table['N_6d_codes'].astype(int)


# Column (v) average length of firm data

df_years = (df_matched.sort_values(['gvkey','quarter_index'])
        .groupby(['gvkey'])[['quarter_index','ind2d','ind2d_definition']]
        .agg(['first','last'])
        .reset_index())
df_years['periods'] = df_years['quarter_index','last'] - df_years['quarter_index','first'] + 1
df_years.columns = df_years.columns.map(','.join).str.strip(',')
df_years = df_years[['ind2d,first','periods']]
df_years.rename(columns={'ind2d,first':'ind2d'}, inplace=True)
mean_periods = df_years['periods'].mean()

df_n_years = df_years.groupby('ind2d').mean(numeric_only = True)
stat_table = pd.merge(stat_table,df_n_years,on='ind2d',how='outer')
stat_table  = stat_table.fillna(0)


# Adding industry definitions

defs = df[['ind2d','ind2d_definition']]
defs = defs.drop_duplicates(subset = 'ind2d')

stat_table = pd.merge(stat_table,defs,on='ind2d',how='outer')

stat_table.loc[0,'ind2d_definition'] = 'Total'
stat_table.loc[0,'N_6d_codes'] = stat_table.N_6d_codes[1:].sum()
stat_table.loc[0,'periods'] = mean_periods
stat_table.loc[0,'ind2d'] = 'Total'


# Formatting the table

stat_table_quarterly = stat_table[['ind2d','ind2d_definition','N_firms',
                         'share_firms_matched','share_revenue_matched','N_6d_codes','periods']]
stat_table_quarterly.rename(columns={'ind2d':'Industry',
                          'ind2d_definition':'Definition',
                          'N_firms':'Number of firms',
                          'share_firms_matched': 'Share of firms matched',
                          'N_6d_codes':'Number of 6-digit industries',
                          'periods':'Number of periods (quarters)'},inplace=True)

# Exporting the table

stat_table_quarterly.round(4).to_csv(tab_dir / 'Stats Table Quarterly (truncated).csv')

# Saving as Tex file
with open(tab_dir / 'Stats Table Quarterly (truncated).tex','w') as tf:
    tf.write(stat_table_quarterly
             .rename(columns ={'share_revenue_matched': 'Share of revenue matched'})
             .round(2)
             .to_latex(index=False))
