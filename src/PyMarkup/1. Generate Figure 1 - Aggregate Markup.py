import pandas as pd
import matplotlib.pyplot as plt
import pathlib
from path_plot_config import int_dir, out_dir, setplotstyle_agg


# Call function that sets the plot style
setplotstyle_agg()

# ------------------------------------------------------------------------------------- #
# Aggregate markup comparison - annual
# ------------------------------------------------------------------------------------- #
# Set up figure-specific directories
input_dir = int_dir / 'For Figure 1'
fig_dir = out_dir / 'Figure 1'

# Input files


# From Stata output
agg_markup = pd.read_csv(input_dir / "agg_markup_annual.csv",low_memory=False)
agg_markup_limited = pd.read_csv(input_dir / "agg_markup_limited_to_PPI matched_annual.csv",low_memory=False)

# Import DLEU Figure 1 data
df_DLEU = pd.read_csv(input_dir / "Aggregate Markups by DLEU.csv")

p = pd.merge(agg_markup, agg_markup_limited, on=['year'], how='outer')
p = pd.merge(df_DLEU, p, on=['year'], how='outer')

p.rename(columns={'MARKUP10_AGG_limited':'agg_markup_matched_ppi',
                          'MARKUP_spec1':'agg_markup_all_firms'
                         }, inplace=True)

p = p[['year','agg_markup_all_firms','agg_markup_matched_ppi','agg_markup_DLEU']]

plt.plot(p.year, p.agg_markup_DLEU, color="black", linestyle=":", linewidth=3)
plt.plot(p.year, p.agg_markup_all_firms, color="darkgreen", linestyle="-", linewidth=3)
plt.plot(p.year, p.agg_markup_matched_ppi, color="orange", linestyle="--", linewidth=3)

plt.ylabel('Aggregate Markup')
plt.legend(['DLEU','Replication','Firms Matched to PPI'])
plt.tight_layout()
plt.savefig(fig_dir / "Aggregate Markup Comparison (1955-2021, Annual).pdf", bbox_inches="tight")
plt.show()


