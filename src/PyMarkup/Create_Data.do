capture program drop Create_Data
program define Create_Data
	syntax, includeinterestcogs(integer)


* BASED OF CODE FROM:
/* DE LOECKER - EECKHOUT - UNGER
The rise of market power and the macroeconomic implications
Quarterly Journal of Economics
* US compustat - history 
*/

/* Use stata file downloaded Compustat using protocol:
Access compustat (WRDS KU Leuven FEB)
> Compustat - Capital IQ from Standard & Poor's
> NORTH AMERICA
> FUNDAMENTALS ANNUAL
> DATE RANGE 1955 - 2016
> GVKEY CODE - search the entire database
> CONSOLIDATED ACCOUNTS, FORMAT INDL AND FS (BELOW DROP FS IF REPORTED BOTH), DOMESTIC POPULATION SOURCE, DATA FORMAT STD, 
>> DATA SELECTED:
	SALE, COGS, XLR, XSGA, PPEGT, PPENT, INTAN, XRD, XAD, EMP, MKVALT, DVT, INDUSTRY INFO (NAICS)
	additional data for robustness: foreign incorp code, company name, 
	
	* external datasets:
		1. interest_rate.dta
		2. us_gdpdeflator.dta
*/



* insert your data file here:
 *use "data/feb-21-2025_NA_exact.dta", clear
 
// use "rawData/june-24-2025_NA_exact_intExp_CAD.dta", clear

import excel "Input/DLEU/macro_vars_new.xlsx", firstrow clear
sort year
save "Input/DLEU/macro_vars_new.dta", replace

use "Input/DLEU/Compustat_annual.dta", clear

keep if fyear>1954 
*qui {
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

* write code to put all $ vars into comparable units!!!!  (commented out by AY)
*gen newmk2 = prcc_f * csho
*label var newmk2 " fiscal year market value prior 1998
*replace mkvalt  = newmk2 if mkvalt==.

replace tie=0 if missing(tie)

* use following variables:
keep gvkey year naics ind* sale cogs xsga xlr xrd xad dvt ppegt intan emp  mkvalt conm  tie
* oibdp
*oibdp
replace sale	= sale*1000
replace xlr		= xlr*1000
*replace oibdp	=oibdp*1000

if `includeinterestcogs' == 1 {
replace cogs	= (cogs+tie)*1000
  }
  else {
replace cogs	= cogs*1000	
  }
  
replace xsga 	= xsga*1000
replace mkvalt 	= mkvalt*1000
replace dvt 	= dvt*1000
replace ppegt	= ppegt*1000
*replace ppent 	= ppent*1000
replace intan	= intan*1000

/* Macro vars: - Merge in Usercost and US GDP deflator
- deflator: use US-wide for main specification, industry specific deflators dating back to 1955 scattered across industry classification changes
 comment: no impact for markup measure, up to estimation of output elasticity! Robustness deflators see appendix.
- User cost of capital computed using FRED nominal interest rate, inflation and calibrated depreciation (See text)
*/



sort year
merge year using "Input/DLEU/macro_vars_new.dta", _merge(macro)
keep if macro==3

 
// drop USGDP2
* Deflated values
gen sale_D		= (sale/USGDP)*100
gen cogs_D 		= (cogs/USGDP)*100
gen xsga_D 		= (xsga/USGDP)*100
gen mkvalt_D 	= (mkvalt/USGDP)*100
gen dividend_D	= (dvt/USGDP)*100
gen capital_D   = (ppegt/USGDP)*100
*gen capital2_D  = (ppent/USGDP)*100
gen intan_D		= (intan/USGDP)*100
gen xlr_D 		= (xlr/USGDP)*100
gen kexp		= (usercost*capital_D)
*gen mat1 		= ((sale-xlr-oibdp)/USGDP)*100 * commented out by AY
* materials is generated from sales, wagebill and operating income bdp, as in Keller and Yeaple (Restat)

* TRIM : no negative values
drop if sale_D<0      /* 296 obs drop */
drop if cogs_D<0      /* 173 obs drop */

* Added by NHM: no zero values for sales and cogs (pulling forward from restrictions imposed later)
drop if sale_D == 0   /* 19,672 obs drop */
drop if cogs_D == 0   /* 1,723  obs drop */

* Added by NHM: no missing values for sales and cogs (pulling forward from restrictions imposed later)
drop if sale_D == .   /* 53,631 obs drop */
drop if cogs_D == .   /* 2,315  obs drop */

* trim on sales-cogs ratio as mu_0 is simply 0.85*sales/cogs
gen s_g = sale/cogs   /* NHM: note that the paper says this will be COGS/SALES */
keep if s_g>0         /* 0 obs drop; but 4660 obs drop without the screen added by NHM just above */

gen trim=0            /* Confirm: we don't consider the above restrictions to be trimmed? */
keep if year>1949     /* NHM: Why is this here? We have already picked 1955-2016 */


* save files to temp directory
* main results for 1% trim (below)
* robustness for appendix: change to p(x) p(y) with x=2-5 and y=95-98
* robustness 2% and 5%
forvalues t=1/5 {
bysort year: egen s_g_p_`t'  = pctile(s_g), p(`t')
}
forvalues s=95/99 {
bysort year: egen s_g_p_`s'  = pctile(s_g), p(`s')
}
* label vars:
label var cogs "Costs directly allocated to production, such as material, labor and overhead.
label var emp "Nr people employed by the company and its consolidated subsidiaries in thousands
foreach var of varlist sale cogs xsga mkvalt intan xlr {
label var `var'_D "Deflated `x'
}
label var dividend_D "Deflated Dvt
label var capital_D "Deflated cap
label var kexp "real capital expenditure

label var ind2d "2 digit NAICS
label var ind3d "3 digit NAICS
label var ind4d "4 digit NAICS
label var usercost "usercost (i-delf+deprc)
label var kexp "capital expenses
*label var mat1 "material cost imputed
label var s_g "sale-cogs ratio
sort gvkey year

keep if s_g> s_g_p_1 & s_g< s_g_p_99   /* 7,285 deleted */
replace trim = 1
drop s_g_p* macro trim indfmt

* Dropping negative SGA (moved down by NHM)
drop if xsga<0        /* 112 obs drop  NHM: SHOULD WE DROP THESE HERE?  */


if `includeinterestcogs' == 1 {
save "Intermediate/data_main_upd_trim_1_intExp.dta", replace
  }
  else {
save "Intermediate/data_main_upd_trim_1.dta", replace
  }
  



end

*--------------------------------------------------*
* data created   
