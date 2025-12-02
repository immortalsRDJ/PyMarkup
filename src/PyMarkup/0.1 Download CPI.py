import pandas as pd
import numpy as np
import pathlib
from path_plot_config import data_dir, fred_apikey

from fredapi import Fred
fred = Fred(api_key=fred_apikey)

cpi_dict = {'CPIAUCSL': 'CPI'}                 

def name_series(series, name):
    series.name = name
    return series

data_list = [name_series(fred.get_series(k),v) for k, v in cpi_dict.items()]
df = pd.concat(data_list,axis=1)
df.reset_index(inplace=True)
df = df.rename(columns = {'index':'Date'})

df["year"] = df["Date"].dt.year
df["month"] = df["Date"].dt.month

# Get Annual CPI
df_annual = df[df.month==1]
#df_annual['CPI']= pd.to_numeric(df_annual['CPI'])
df_annual = df_annual[['year','CPI']]
df_annual.to_csv(data_dir / 'CPI' / 'CPI_annual.csv', index=False)

# Get Quarterly CPI
df['year']=df['year'].astype(int)
df['year']=df['year'].astype(str)
df['month'] = df['month'].astype(int)
df['quarter'] = np.nan
df.loc[df.month == 1, 'quarter'] = df['year'].astype(str) + 'Q' + '1'
df.loc[df.month == 4, 'quarter'] = df['year'].astype(str) + 'Q' + '2'
df.loc[df.month == 7, 'quarter'] = df['year'].astype(str) + 'Q' + '3'
df.loc[df.month == 10, 'quarter'] = df['year'].astype(str) + 'Q' + '4'
df['CPI']= pd.to_numeric(df['CPI'])
df = df.dropna(subset=['quarter'])
df = df[['quarter','CPI']]
df.to_csv(data_dir / 'CPI' / 'CPI_quarterly.csv', index=False)

