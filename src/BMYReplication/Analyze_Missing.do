capture program drop Analyze_Missing
program define Analyze_Missing
	

* ---------------------------------------------------------------------------- *
* Add NAICS Description, SGA Missing Indicator, and Regression Variables
* ---------------------------------------------------------------------------- *

* Import the description of 2-digit NAICS code
import excel "rawData/NAICS_2D_Description.xlsx", sheet("Sheet1") firstrow clear
ren sector_definition ind2d_definition

* Add definition for ind2d == 99
set obs `=_N + 1'
replace ind2d = 99 in L
replace ind2d_definition = "Unclassified" in L

* Sorting and saving from a merge
sort ind2d
tempfile naics2d
save "temp/naics2d", replace

* Merging with DEU data set
use "intermediateOutput/data_main_upd_trim_1.dta", clear
sort ind2d
merge m:1 ind2d using "temp/naics2d"
keep if _merge==3   /* does not drop any obs from DEU data set */ 

* Create SGA Missing Indicator and Regression Variables
gen sga_missing = xsga_D==. 
gen ln_sale_D = log(sale_D)
gen ln_cogs_D = log(cogs_D)
gen sale_cogs_ratio = s_g

tab sga_missing


* ---------------------------------------------------------------------------- *
* Summarize Missing SG&A Observations Over Time, Export Figure
* ---------------------------------------------------------------------------- *
preserve

* Create a constant dummy to count
gen obs_dummy = 1

* Create missing_sales before collapsing
gen missing_sales = sale_D if sga_missing == 1

* Collapse to year-level aggregates
collapse (count) total_obs = obs_dummy (sum) missing_obs = sga_missing total_sales = sale_D missing_sales, by(year)

* Create the two fractions
gen frac_missing_obs = missing_obs / total_obs
gen frac_missing_sales = missing_sales / total_sales

* Plot the two lines
twoway ///
    (line frac_missing_obs year, lpattern(solid) lwidth(medthick) lcolor(green) legend(label(1 "Observations with Missing SG&A")))  ///
    (line frac_missing_sales year, lpattern(dash) lwidth(medthick) lcolor(orange) legend(label(2 "Sales with Missing SG&A"))) ///
    , ytitle("Fraction") ///
      ylabel(0(0.1)0.4, angle(horizontal)) ///
      yscale(range(0 0.4)) ///
      xtitle("") ///
	  xlab(,grid) ///
      legend(order(1 2) row(2) pos(11) ring(0) region(style(none))) ///
      graphregion(color(white)) bgcolor(white)

graph export "outputFigures/fig_frac_sga_obs_sale_by_year.pdf", as(pdf) name(Graph) replace


restore


* ---------------------------------------------------------------------------------------- *
* Summarize missing SG&A observations, by 2-digit NAICS code
* ---------------------------------------------------------------------------------------- *
preserve

* Create relevant variables
gen missing_sales = sale_D if sga_missing == 1
gen total_sales = sale_D

* Collapse to industry level
collapse (count) total_obs = sale_D (sum) missing_obs = sga_missing total_sales missing_sales, by(ind2d ind2d_definition)

* Calculate within-industry missing data fractions
gen frac_obs_missing = missing_obs / total_obs * 100
gen frac_sales_missing = missing_sales / total_sales * 100

* Get total sales for the full sample
sum total_sales
scalar full_total_sales = r(sum)

* Calculate industry share of total sales
gen share_all_sales = total_sales / full_total_sales * 100

* Keep and sort relevant variables
keep ind2d ind2d_definition frac_obs_missing frac_sales_missing share_all_sales
sort ind2d

* Clean LaTeX special characters
gen strL defn_clean = subinstr(ind2d_definition, "&", "\\&", .)
replace defn_clean = subinstr(defn_clean, "_", "\\_", .)

* Define LaTeX output file
local outfile "outputFigures/tab_frac_sga_obs_sale_by_ind2d.tex"
file open texfile using `"`outfile'"', write replace

* Write LaTeX table preamble
file write texfile "\begin{table}[t]" _n "\centering \footnotesize" _n "\caption{Summary of Missing SG\&A Information by 2-Digit NAICS Code}" _n "\begin{tabular}{llccc}" _n "\hline \hline" _n "&& Share of All & Observations & Sales \rule[0mm]{0mm}{4mm} \\" _n "NAICS Code & Definition & Sales (\%) & Missing (\%) & Missing (\%) \\" _n "\hline" _n

* Write rows
quietly {
    forvalues i = 1/`=_N' {
        local ind = ind2d[`i']
        local defn = defn_clean[`i']
        local f1 : display %5.2f share_all_sales[`i']
        local f2 : display %5.2f frac_obs_missing[`i']
        local f3 : display %5.2f frac_sales_missing[`i']

        if `ind' == 56 {
            file write texfile "`ind' & Administrative and Support and Waste & `f1' & `f2' & `f3' \\" _n "& $\quad$ Management and Remediation Services \\" _n
        }
		else if `ind' == 11 {
			file write texfile "`ind' & `defn' & `f1' & `f2' & `f3' \rule[0mm]{0mm}{4mm} \\" _n
		}
        else {
            file write texfile "`ind' & `defn' & `f1' & `f2' & `f3' \\" _n
        }
    }
}

* End of table
file write texfile "\hline" _n "\end{tabular}" _n "\end{table}" _n
file close texfile

restore



* ---------------------------------------------------------------------------------------- *
* Regressions on sales, COGS, sale/COGS ratio
* ---------------------------------------------------------------------------------------- *

******************************
* Unweighted LOG regressions
******************************

preserve
reghdfe ln_sale_D sga_missing, absorb(year ind2d) vce(cluster gvkey)
eststo m1

reghdfe ln_sale_D sga_missing, absorb(year ind2d gvkey) vce(cluster gvkey)
eststo m2

reghdfe ln_cogs_D sga_missing, absorb(year ind2d) vce(cluster gvkey)
eststo m3

reghdfe ln_cogs_D sga_missing, absorb(year ind2d gvkey) vce(cluster gvkey)
eststo m4

reghdfe sale_cogs_ratio sga_missing, absorb(year ind2d) vce(cluster gvkey)
eststo m5

reghdfe sale_cogs_ratio sga_missing, absorb(year ind2d gvkey) vce(cluster gvkey)
eststo m6

******************************
* Export results
******************************

* Define output path
local outfile "outputFigures/reg_unweighted_log_sga_missing.tex"

* Extract coefficients, SEs, R2, and N
est restore m1
scalar b1 = _b[sga_missing]
scalar se1 = _se[sga_missing]
scalar r2_1 = e(r2)
scalar n_obs = e(N)

est restore m2
scalar b2 = _b[sga_missing]
scalar se2 = _se[sga_missing]
scalar r2_2 = e(r2)

est restore m3
scalar b3 = _b[sga_missing]
scalar se3 = _se[sga_missing]
scalar r2_3 = e(r2)

est restore m4
scalar b4 = _b[sga_missing]
scalar se4 = _se[sga_missing]
scalar r2_4 = e(r2)

est restore m5
scalar b5 = _b[sga_missing]
scalar se5 = _se[sga_missing]
scalar r2_5 = e(r2)

est restore m6
scalar b6 = _b[sga_missing]
scalar se6 = _se[sga_missing]
scalar r2_6 = e(r2)

* Format coefficients, SEs, R2s, N
local b1 : display %6.3f b1
local b2 : display %6.3f b2
local b3 : display %6.3f b3
local b4 : display %6.3f b4
local b5 : display %6.3f b5
local b6 : display %6.3f b6

local se1 : display %6.3f se1
local se2 : display %6.3f se2
local se3 : display %6.3f se3
local se4 : display %6.3f se4
local se5 : display %6.3f se5
local se6 : display %6.3f se6

local r2_1 : display %6.3f r2_1
local r2_2 : display %6.3f r2_2
local r2_3 : display %6.3f r2_3
local r2_4 : display %6.3f r2_4
local r2_5 : display %6.3f r2_5
local r2_6 : display %6.3f r2_6

local n_obs : display %15.0fc n_obs

* Write the table
file open texfile using `"`outfile'"', write replace
file write texfile ///
"\begin{table}[t]" _n ///
"\centering \footnotesize" _n ///
"\caption{Relationships between Missing SG\&A and Sales, COGS, and Sales/COGS}" _n ///
"\begin{tabular}{lcccccc}" _n ///
"\hline \hline" _n ///
" & Sales & Sales & COGS & COGS & Sales/COGS & Sales/COGS\rule[0mm]{0mm}{4mm} \\" _n ///
"\hline" _n ///
"SG\&A Missing & `b1' & `b2' & `b3' & `b4' & `b5' & `b6' \rule[0mm]{0mm}{4mm} \\" _n ///
" & (`se1') & (`se2') & (`se3') & (`se4') & (`se5') & (`se6') \\" _n ///
"\\" _n ///
"Year Fixed Effects & yes & yes & yes & yes & yes & yes \\" _n ///
"Industry Fixed Effects & yes & yes & yes & yes & yes & yes \\" _n ///
"Firm Fixed Effects & no & yes & no & yes & no & yes \\" _n ///
"\\" _n ///
"R-squared & `r2_1' & `r2_2' & `r2_3' & `r2_4' & `r2_5' & `r2_6' \\" _n ///
"\hline" _n ///
"\multicolumn{7}{p{5.6in}}{\rule[0mm]{0mm}{4mm}\scriptsize{" ///
"Notes: The table reports the results of OLS regression. The dependent variables are the natural logs of Sales, COGS, and Sales/COGS. " ///
"The independent variable is an indicator that equals one if SG\&A is missing. There are `n_obs' firm-year observations in the sample. " ///
"The industry fixed effects are at the 2-digit NAICS code level. Standard errors are in parentheses." ///
"}}\n" ///
"\end{tabular}" _n ///
"\end{table}" _n
file close texfile

restore



**************************************
* Interact with Demeaned Time Trend
**************************************
preserve

* --- Prepare Data ---
* Calculate mean of year
summarize year
scalar year_mean = r(mean)

* Generate demeaned time trend and interaction term
gen year_demeaned = year - year_mean
gen sga_missing_trend = sga_missing * year_demeaned

* --- Run Regressions ---
reghdfe ln_sale_D sga_missing sga_missing_trend, absorb(year ind2d) vce(cluster gvkey)
eststo m1
reghdfe ln_sale_D sga_missing sga_missing_trend, absorb(year ind2d gvkey) vce(cluster gvkey)
eststo m2
reghdfe ln_cogs_D sga_missing sga_missing_trend, absorb(year ind2d) vce(cluster gvkey)
eststo m3
reghdfe ln_cogs_D sga_missing sga_missing_trend, absorb(year ind2d gvkey) vce(cluster gvkey)
eststo m4
reghdfe sale_cogs_ratio sga_missing sga_missing_trend, absorb(year ind2d) vce(cluster gvkey)
eststo m5
reghdfe sale_cogs_ratio sga_missing sga_missing_trend, absorb(year ind2d gvkey) vce(cluster gvkey)
eststo m6

* --- Extract Statistics ---
foreach i in 1 2 3 4 5 6 {
    est restore m`i'
    scalar b_sga_`i'   = _b[sga_missing]
    scalar se_sga_`i'  = _se[sga_missing]
    scalar b_trend_`i' = _b[sga_missing_trend]
    scalar se_trend_`i' = _se[sga_missing_trend]
    scalar r2_`i'      = e(r2)
}
est restore m1
scalar n_obs = e(N)
local n_obs_fmt : display %15.0fc n_obs

* --- Export to LaTeX ---
local outfile "outputFigures/reg_unweighted_log_sga_missing_time_trend_interaction.tex"
file open texfile using `"`outfile'"', write replace

* Table header
file write texfile ///
"\begin{table}[t]" _n ///
"\centering \footnotesize" _n ///
"\caption{Interaction of Missing SG\&A with Time Trend}" _n ///
"\begin{tabular}{lcccccc}" _n ///
"\hline \hline" _n ///
" & Sales & Sales & COGS & COGS & Sales/COGS & Sales/COGS\rule[0mm]{0mm}{4mm} \\" _n ///
"\hline" _n

* SG&A Missing row
file write texfile "SG\&A Missing &"
forvalues i = 1/6 {
    local b : display %6.3f b_sga_`i'
    file write texfile " `b'"
    if `i' < 6 file write texfile " &"
}
file write texfile "\rule[0mm]{0mm}{4mm} \\" _n

* SG&A Missing SE
file write texfile " &"
forvalues i = 1/6 {
    local se : display %6.3f se_sga_`i'
    file write texfile " (`se')"
    if `i' < 6 file write texfile " &"
}
file write texfile " \\" _n

* Interaction term row
file write texfile "SG\&A Missing $\times$ Trend &"
forvalues i = 1/6 {
    local b : display %6.3f b_trend_`i'
    file write texfile " `b'"
    if `i' < 6 file write texfile " &"
}
file write texfile " \\" _n

* Interaction SE
file write texfile " &"
forvalues i = 1/6 {
    local se : display %6.3f se_trend_`i'
    file write texfile " (`se')"
    if `i' < 6 file write texfile " &"
}
file write texfile " \\" _n

* Fixed effects rows
file write texfile ///
"\\" _n ///
"Year Fixed Effects & yes & yes & yes & yes & yes & yes \\" _n ///
"Industry Fixed Effects & yes & yes & yes & yes & yes & yes \\" _n ///
"Firm Fixed Effects & no & yes & no & yes & no & yes \\" _n ///
"\\" _n

* R-squared
file write texfile "R-squared &"
forvalues i = 1/6 {
    local r2 : display %6.3f r2_`i'
    file write texfile " `r2'"
    if `i' < 6 file write texfile " &"
}
file write texfile " \\" _n

* Notes
file write texfile ///
"\hline" _n ///
"\multicolumn{7}{p{5.6in}}{\rule[0mm]{0mm}{4mm}\scriptsize{" ///
"Notes: This table reports the results of OLS regressions of log Sales, COGS, and Sales/COGS on an indicator for missing SG\&A and its interaction with a demeaned time trend. " ///
"The industry fixed effects are at the 2-digit NAICS level. There are `n_obs_fmt' firm-year observations. Standard errors are in parentheses." ///
"}}\n" ///
"\end{tabular}" _n ///
"\end{table}" _n

file close texfile
restore






end

*--------------------------------------------------*
* missing SG&A values analyzed 
