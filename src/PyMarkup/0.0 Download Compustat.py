import pandas as pd
import wrds
import pathlib
from path_plot_config import data_dir

db = wrds.Connection()

# Obtain NAICS code from comp.company
fields = [
        'gvkey',
        'naics']
query = "select " +         ', '.join(fields) + " from comp.company"
naics = db.raw_sql(query).sort_values(['gvkey'])


# -------------------------------------------------------------------------------- #
# Annual Data
# -------------------------------------------------------------------------------- #
fields = [
        'gvkey',
        'indfmt',
        'consol',
        'popsrc',
        'datafmt',
        'conm',
        'fyear',
        'sale',
        'cogs',
        'xsga',
        'ppegt',
        'xlr',
        'xrd',
        'xad',
        'dvt',
        'intan',
        'mkvalt',
        'tie',
        'emp',
        'ppent']
query = "select " +         ', '.join(fields) + " from comp.funda where consol = 'C' and popsrc = 'D' and datafmt = 'STD'"
df_fund = db.raw_sql(query).sort_values(['gvkey', 'fyear'])

df = pd.merge(df_fund, naics, on=['gvkey'], how='left')

df.to_stata(data_dir / 'DLEU' / 'Compustat_annual.dta', write_index=False)

# -------------------------------------------------------------------------------- #
# Quarterly Data
# -------------------------------------------------------------------------------- #
fields = [
        'gvkey',
        'indfmt',
        'consol',
        'popsrc',
        'datafmt',
        'conm',
        'fyearq',
        'fqtr',
        'saleq',
        'cogsq',
        'xsgaq',
        'ppegtq']
query = "select " +         ', '.join(fields) + " from comp.fundq where consol = 'C' and popsrc = 'D' and datafmt = 'STD'"
df_fund = db.raw_sql(query).sort_values(['gvkey', 'fyearq', 'fqtr'])

df = pd.merge(df_fund, naics, on=['gvkey'], how='left')

df.to_stata(data_dir / 'DLEU' / 'Compustat_quarterly.dta', write_index=False)
