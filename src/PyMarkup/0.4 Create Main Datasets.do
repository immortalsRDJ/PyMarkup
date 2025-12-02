/* 
Reference:
DE LOECKER - EECKHOUT - UNGER
The rise of market power and the macroeconomic implications
Quarterly Journal of Economics
* US compustat - history 
*/

* add your path here
cd "/Users/clairemeng/Dropbox/NYU/RA_Conlon/DLEU_replication/RisingPricesRisingMarkupsReplication/"

* ---------------------------------------------------------------------------------------- *
* Import Data
* ---------------------------------------------------------------------------------------- *

* import macro variables
import excel "Input/DLEU/macro_vars_new.xlsx", sheet("Sheet1") firstrow clear
sort year
tempfile macro_vars_new
save `macro_vars_new'

* import the description of 2-digit NAICS code
import excel "Input/Other/NAICS_2D_Description.xlsx", sheet("Sheet1") firstrow clear
sort ind2d
ren sector_definition ind2d_definition
tempfile naics2d
save `naics2d'

* import PPI data
import delimited "Input/PPI/PPI_annual.csv", clear
sort year naics_code
ren naics_code naics
keep year naics ppi
tempfile ppi_annual
save `ppi_annual'

* import PPI data (quarterly)
import delimited "Input/PPI/PPI_quarterly.csv", varnames(1) clear
/* drop if date == "2022Q4" */
keep date naics_code ppi
sort date naics_code
ren naics_code naics
ren date quarter
tempfile ppi_quarterly
save `ppi_quarterly'

* import CPI data
import delimited "Input/CPI/CPI_annual.csv", case(preserve) clear
sort year
tempfile cpi_annual
save `cpi_annual'

* import CPI data (quarterly)
import delimited "Input/CPI/CPI_quarterly.csv", case(preserve) clear
sort quarter
tempfile cpi_quarterly
save `cpi_quarterly'

* =================================================================================================== *
* For Annual Data
* =================================================================================================== *

* import Compustat data
use "Input/DLEU/Compustat_annual.dta", clear


* ---------------------------------------------------------------------------------------- *
* Data Cleaning and Merging
* ---------------------------------------------------------------------------------------- *
sort gvkey fyear
rename fyear year
bysort gvkey year : gen nrobs = _N
* Keep only observation for one industry (some firms are in several industries) 
drop if (nrobs == 2 | nrobs == 3) & indfmt == "FS"
sort gvkey year
drop if gvkey==gvkey[_n-1] & year==year[_n-1]

* Drop firms without industry information
keep if naics~=""
* Take into account obs with industry code obs for which only d-1 digits in the d-category!!!
forvalues i =2/4 {
gen ind`i'd 								= substr(naics,1,`i')
destring ind`i'd, replace
egen nrind`i' = group(ind`i'd)
}

* use following variables:
keep gvkey year naics ind* sale cogs xsga ppegt conm
replace sale	= sale*1000
replace cogs	= cogs*1000
replace xsga 	= xsga*1000
replace ppegt	= ppegt*1000

/* Macro vars: - Merge in Usercost and US GDP deflator
- deflator: use US-wide for main specification, industry specific deflators dating back to 1955 scattered across industry classification changes
 comment: no impact for markup measure, up to estimation of output elasticity! Robustness deflators see appendix.
- User cost of capital computed using FRED nominal interest rate, inflation and calibrated depreciation (See text)
*/
sort year
merge year using `macro_vars_new', _merge(macro)
keep if macro==3
drop macro

sort year naics
merge year naics using `ppi_annual', _merge(macro)
drop if macro==2
drop macro

sort year
merge year using `cpi_annual', _merge(macro)
drop if macro==2
drop macro

sort ind2d
merge ind2d using `naics2d', _merge(macro)
keep if macro==3


* Deflated values
gen sale_D		= (sale/USGDP)*100
gen cogs_D 		= (cogs/USGDP)*100
gen xsga_D 		= (xsga/USGDP)*100
gen capital_D   = (ppegt/USGDP)*100
gen kexp		= (usercost*capital_D)
* materials is generated from sales, wagebill and operating income bdp, as in Keller and Yeaple (Restat)

* TRIM : no negative values
drop if sale_D<0 
drop if cogs_D<0
drop if xsga<0
* trim on sales-cogs ratio as mu_0 is simply 0.85*sales/cogs
gen s_g = sale/cogs
keep if s_g>0
keep if year>1949

* main results for 1% trim (below)
bysort year: egen s_g_p_1  = pctile(s_g), p(1)
bysort year: egen s_g_p_99  = pctile(s_g), p(99)

sort gvkey year

keep if s_g> s_g_p_1 & s_g< s_g_p_99
drop s_g_p* macro


* ---------------------------------------------------------------------------------------- *
* Trim Based on Cost Share
* ---------------------------------------------------------------------------------------- *


egen id	= group(gvkey)
drop if id==.

gen costshare0 = .85
label var costshare0 "calibrated 0.85 (fig 1 NBER)
gen costshare1 = cogs_D/(cogs_D+kexp)
label var costshare1 "cogs_D/(cogs_D+kexp)
gen costshare2 = cogs_D/(cogs_D+xsga_D+kexp)
label var costshare2 "cogs_D/(cogs_D+xsga_D+kexp)
gen costshare3 = xsga_D/(cogs_D+xsga_D+kexp)
label var costshare3 "sga_D/(cogs_D+xsga_D+kexp)
gen costshare4 = kexp/(cogs_D+xsga_D+kexp)
label var costshare4 " capital cost share
forvalues s=0/2 {
gen mu_`s' = costshare`s'*(sale_D/cogs_D)
label var mu_`s' "markup firm-level costshare `s'
}

* trim on costshares
forvalues s=1/2 {
bysort year: egen cs`s'_p1=pctile(costshare`s'), p(1)
bysort year: egen cs`s'_p99=pctile(costshare`s'), p(99)
drop if costshare`s'==0 | costshare`s'==.
drop if costshare`s' > cs`s'_p99 
drop if costshare`s' < cs`s'_p1
}


* ---------------------------------------------------------------------------------------- *
* Calculate Firm-level Markup and Aggregate Markup
* ---------------------------------------------------------------------------------------- *

* OUTPUT ELASTICITIES ESTIMATED VIA PF ESTIMATION - PULL PARAMETERS
* F(COGS, K) BY PERIOD-INDUSTRY
sort ind2d year
merge ind2d year using "Intermediate/theta_W_s_window_fullSample.dta", _merge(theta_Wtime)
gen mu_10 = theta_WI1_ct*(sale_D/cogs_D)
label var mu_10 "markup PF CD-sector-time (RED)


bysort year:  	egen TOTSALES 	= sum(sale_D)
gen share_firm_agg 				= sale_D/TOTSALES

bysort year: egen MARKUP10_AGG 	= sum(share_firm_agg*mu_10)

label var MARKUP10_AGG "MARKUP AGG PF-SECTOR-TIME (RED)
gen mu_spec1	= mu_10
label var mu_spec1 "markup red tech 
gen MARKUP_spec1 = MARKUP10_AGG
label var MARKUP_spec1 "AGG MARKUP (Trad. PF)

forvalues d=2/4 {
bysort ind`d'd year: egen TOTSALES_IND_`d' = sum(sale_D)
gen share_IND`d' = TOTSALES_IND_`d'/TOTSALES
gen share_ind_`d'  = sale_D/TOTSALES_IND_`d'
forvalues r= 1/1 {
bysort ind`d'd year	: egen MARKUP_sp`r'_IND_`d' = sum(share_ind_`d'*mu_spec`r')
bysort ind`d'd year : egen ThetaW`r'_c_IND`d' 	= sum(share_ind_`d'*theta_WI`r'_ct)  
}
}
label var year " 
label var MARKUP_spec1 "Agg Markup (Benchmark) 

/* drop if year > 2021 */
drop if year < 1955
drop if ind2d == 99
*save "Intermediate/main_annual.dta", replace

preserve
keep gvkey conm year naics ind2d ind2d_definition mu_10 sale sale_D cogs cogs_D ppi CPI
order gvkey conm year naics ind2d ind2d_definition mu_10 sale sale_D cogs cogs_D ppi CPI
ren mu_10 firm_level_markup
export delimited using "Intermediate/main_annual.csv", replace
restore

preserve
keep year MARKUP_spec1
sort year
duplicates drop
export delimited using "Intermediate/For Figure 1/agg_markup_annual.csv", replace
restore

preserve
keep if ppi!=.
bysort year:  	egen TOTSALES_limited 	= sum(sale_D)
gen share_firm_agg_limited 				= sale_D/TOTSALES_limited
bysort year: egen MARKUP10_AGG_limited 	= sum(share_firm_agg_limited*mu_10)
keep year MARKUP10_AGG_limited
sort year
duplicates drop
export delimited using "Intermediate/For Figure 1/agg_markup_limited_to_PPI matched_annual.csv", replace
restore

*--------------------------------------------------*
* data created 







* =================================================================================================== *
* For Quarterly Data
* =================================================================================================== *

* import Compustat data
use "Input/DLEU/Compustat_quarterly.dta", clear


* ---------------------------------------------------------------------------------------- *
* Data Cleaning and Merging
* ---------------------------------------------------------------------------------------- *
drop if fqtr == .
tostring fyearq, replace
tostring fqtr, replace
gen quarter = fyearq + "Q" + fqtr
sort gvkey quarter
bysort gvkey quarter : gen nrobs = _N
* Keep only observation for one industry (some firms are in several industries) 
drop if (nrobs == 2 | nrobs == 3) & indfmt == "FS"
sort gvkey quarter
drop if gvkey==gvkey[_n-1] & quarter==quarter[_n-1]

* Drop firms without industry information
keep if naics~=""
* Take into account obs with industry code obs for which only d-1 digits in the d-category!!!
forvalues i =2/4 {
gen ind`i'd 								= substr(naics,1,`i')
destring ind`i'd, replace
egen nrind`i' = group(ind`i'd)
}

* use following variables:
keep gvkey fyearq quarter naics ind* saleq cogsq xsgaq ppegtq conm
replace saleq	= saleq*1000
replace cogsq	= cogsq*1000
replace xsgaq 	= xsgaq*1000
replace ppegtq	= ppegtq*1000

/* Macro vars: - Merge in Usercost and US GDP deflator
- deflator: use US-wide for main specification, industry specific deflators dating back to 1955 scattered across industry classification changes
 comment: no impact for markup measure, up to estimation of output elasticity! Robustness deflators see appendix.
- User cost of capital computed using FRED nominal interest rate, inflation and calibrated depreciation (See text)
*/
ren fyearq year
destring year, replace

sort year quarter
merge year using `macro_vars_new', _merge(macro)
keep if macro==3
drop macro

sort quarter naics
merge quarter naics using `ppi_quarterly', _merge(macro)
drop if macro==2
drop macro

sort quarter
merge quarter using `cpi_quarterly', _merge(macro)
drop if macro==2
drop macro

sort ind2d
merge ind2d using `naics2d', _merge(macro)
keep if macro==3


* Deflated values
gen sale_D		= (saleq/USGDP)*100
gen cogs_D 		= (cogsq/USGDP)*100
gen xsga_D 		= (xsgaq/USGDP)*100
gen capital_D   = (ppegtq/USGDP)*100
gen kexp		= (usercost*capital_D)
* materials is generated from sales, wagebill and operating income bdp, as in Keller and Yeaple (Restat)

* TRIM : no negative values
drop if sale_D<0 
drop if cogs_D<0
drop if xsgaq<0
* trim on sales-cogs ratio as mu_0 is simply 0.85*sales/cogs
gen s_g = saleq/cogsq
keep if s_g>0

* main results for 1% trim (below)
bysort quarter: egen s_g_p_1  = pctile(s_g), p(1)
bysort quarter: egen s_g_p_99  = pctile(s_g), p(99)

sort gvkey quarter

keep if s_g> s_g_p_1 & s_g< s_g_p_99
drop s_g_p* macro


* ---------------------------------------------------------------------------------------- *
* Trim Based on Cost Share
* ---------------------------------------------------------------------------------------- *

egen id	= group(gvkey)
drop if id==.

gen costshare0 = .85
label var costshare0 "calibrated 0.85 (fig 1 NBER)
gen costshare1 = cogs_D/(cogs_D+kexp)
label var costshare1 "cogs_D/(cogs_D+kexp)
gen costshare2 = cogs_D/(cogs_D+xsga_D+kexp)
label var costshare2 "cogs_D/(cogs_D+xsga_D+kexp)
gen costshare3 = xsga_D/(cogs_D+xsga_D+kexp)
label var costshare3 "sga_D/(cogs_D+xsga_D+kexp)
gen costshare4 = kexp/(cogs_D+xsga_D+kexp)
label var costshare4 " capital cost share
forvalues s=0/2 {
gen mu_`s' = costshare`s'*(sale_D/cogs_D)
label var mu_`s' "markup firm-level costshare `s'
}

* trim on costshares
forvalues s=1/2 {
bysort quarter: egen cs`s'_p1=pctile(costshare`s'), p(1)
bysort quarter: egen cs`s'_p99=pctile(costshare`s'), p(99)
drop if costshare`s'==0 | costshare`s'==.
drop if costshare`s' > cs`s'_p99 
drop if costshare`s' < cs`s'_p1
}


* ---------------------------------------------------------------------------------------- *
* Calculate Firm-level Markup and Aggregate Markup
* ---------------------------------------------------------------------------------------- *

* OUTPUT ELASTICITIES ESTIMATED VIA PF ESTIMATION - PULL PARAMETERS
* F(COGS, K) BY PERIOD-INDUSTRY
sort ind2d year
merge ind2d year using "Intermediate/theta_W_s_window_fullSample.dta", _merge(theta_Wtime)
gen mu_10 = theta_WI1_ct*(sale_D/cogs_D)
label var mu_10 "markup PF CD-sector-time (RED)


bysort quarter:  	egen TOTSALES 	= sum(sale_D)
gen share_firm_agg 				= sale_D/TOTSALES


bysort quarter: egen MARKUP10_AGG 	= sum(share_firm_agg*mu_10)

label var MARKUP10_AGG "MARKUP AGG PF-SECTOR-TIME (RED)
gen mu_spec1	= mu_10
label var mu_spec1 "markup red tech 
gen MARKUP_spec1 = MARKUP10_AGG
label var MARKUP_spec1 "AGG MARKUP (Trad. PF)

forvalues d=2/4 {
bysort ind`d'd quarter: egen TOTSALES_IND_`d' = sum(sale_D)
gen share_IND`d' = TOTSALES_IND_`d'/TOTSALES
gen share_ind_`d'  = sale_D/TOTSALES_IND_`d'
forvalues r= 1/1 {
bysort ind`d'd quarter	: egen MARKUP_sp`r'_IND_`d' = sum(share_ind_`d'*mu_spec`r')
bysort ind`d'd quarter : egen ThetaW`r'_c_IND`d' 	= sum(share_ind_`d'*theta_WI`r'_ct)  
}
}
label var quarter " 
label var MARKUP_spec1 "Agg Markup (Benchmark) 

drop if quarter == ""
/* drop if quarter == "2022Q4"
drop if year > 2022 */
drop if year < 1955
drop if ind2d == 99
*save "Intermediate/main_quarterly.dta", replace


preserve
ren mu_10 firm_level_markup
keep gvkey conm year quarter naics ind2d ind2d_definition firm_level_markup saleq sale_D cogsq cogs_D ppi CPI
order gvkey conm year quarter naics ind2d ind2d_definition firm_level_markup saleq sale_D cogsq cogs_D ppi CPI
export delimited using "Intermediate/main_quarterly.csv", replace
restore


exit, STATA clear
