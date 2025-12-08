


* Figure 1
use "intermediateOutput/markup_DEU.dta", clear
merge 1:1 year using "intermediateOutput/markup_full.dta"

label var MARKUP10_AGG_DEU "DEU Sample"
label var MARKUP10_AGG_full "Full Sample"
label var MARKUP10_AGG_full_no52 "Full Sample, No F&I"

line MARKUP10_AGG_DEU MARKUP10_AGG_full MARKUP10_AGG_full_no52 year, lcolor(red green black) lwidth(medthick medium thick)  msymbol(O S T) lpattern(l - _.-) legend(ring(0) pos(11)) ytitle("Sales Weighted Markup") xtitle("")
graph export "outputFigures/figure1.eps", replace

* Figure 2 
use "intermediateOutput/markup_DEU.dta", clear
merge 1:1 year using "intermediateOutput/markup_full.dta"
merge 1:1 year using "intermediateOutput/markup_full_intExp.dta", gen(_mergeIntExp)


label var MARKUP10_AGG_DEU "DEU Sample"
label var MARKUP10_AGG_full_intExp "Full Sample, Interest Expense in COGS"
label var MARKUP10_AGG_full_no52 "Full Sample, No F&I"

line MARKUP10_AGG_DEU MARKUP10_AGG_full_intExp MARKUP10_AGG_full_no52 year, lcolor(red green black) lwidth(medthick medium thick)  msymbol(O S T) lpattern(l - _.- ) legend(ring(0) pos(11)) ytitle("Sales Weighted Markup") xtitle("")
graph export "outputFigures/figure2.eps", replace




* Alternative weights
use "intermediateOutput/markup_DEU.dta", clear
merge 1:1 year using "intermediateOutput/markup_full.dta"

label var MARKUP10_AGG_DEU "DEU Sample, Baseline Sales Weighted"
label var MARKUP10_AGGCOGS_DEU "DEU Sample, COGS Weighted"
label var MARKUP10_AGGCOGS_full "Full Sample, COGS Weighted"
label var MARKUP10_AGGCOGS_full_no52 "Full Sample, COGS Weighted, No F&I"

line MARKUP10_AGG_DEU MARKUP10_AGGCOGS_DEU MARKUP10_AGGCOGS_full MARKUP10_AGGCOGS_full_no52 year, lcolor(red purple green black) lwidth(medthick medthick medium thick)  msymbol(O S T T) lpattern(l - _.- _.-) legend(ring(0) pos(11)) ytitle("Sales Weighted Markup") xtitle("")
graph export "outputFigures/figure_altWeights.eps", replace


** Additional figures (these make some additional computations)
	use "intermediateOutput/data_main_upd_trim_1.dta", clear
	
	egen id=group(gvkey)
	drop if id==.
	
	gen s_g2 = xsga/sale
	bysort year: egen s_g2_p1=pctile(s_g2), p(1)
	bysort year: egen s_g2_p99=pctile(s_g2), p(99)
	drop if s_g2<s_g2_p1 & !missing(s_g2)
	drop if s_g2>s_g2_p99 & !missing(s_g2)
	drop s_g2*	
	
	sort ind2d year
	merge ind2d year using  "intermediateOutput/theta_W_s_window_fullSample.dta", _merge(theta_Wtime)	
	drop if ind2==52  
	
	gen mu_10 = theta_WI1_ct*(sale_D/cogs_D)
	label var mu_10 "markup PF CD-sector-time (RED)
	gen mu_11 = theta_WI2_ct*(sale_D/cogs_D)
	label var mu_11 "markup PF CD-sector-time (BLUE)

	bysort year:  	egen TOTSALES 	= sum(sale_D)
	gen share_firm_agg 				= sale_D/TOTSALES
	bysort year:  	egen TOTCOST 	= sum(cogs_D+xsga_D)
	gen share_firm_cost= (cogs_D+xsga_D)/TOTCOST

	bysort ind2 year: egen sectorShare=sum(share_firm_agg)


	forvalues i=10/11{
	bysort year: egen MARKUP`i'_AGG 	= sum(share_firm_agg*mu_`i')
	bysort year: egen MARKUP`i'_COST 	= sum(share_firm_cost*mu_`i')
	label var MARKUP`i'_AGG "Markup `i'[w=s]
	}

	bysort year: egen medianMarkup=pctile(mu_10), p(50)

	bysort year: egen p10Markup=pctile(mu_10), p(10)
	bysort year: egen p25Markup=pctile(mu_10), p(25)
	bysort year: egen p75Markup=pctile(mu_10), p(75)
	bysort year: egen p90Markup=pctile(mu_10), p(90)
		
	
	gen mu_spec1	= mu_10

	forvalues r=1/1 {
	bysort year (mu_spec`r'): gen ms_cum_mu_`r' 		= sum(share_firm_agg) 
	bysort year (mu_spec`r'): gen ms90_`r' = 1 if ms_cum_mu_`r'<.9
	bysort year (mu_spec`r'): gen ms75_`r' = 1 if ms_cum_mu_`r'<.75
	bysort year (mu_spec`r'): gen ms50_`r' = 1 if ms_cum_mu_`r'<.5
	bysort year (mu_spec`r'): gen ms25_`r' = 1 if ms_cum_mu_`r'<.25
	bysort year (mu_spec`r'): gen ms10_`r' = 1 if ms_cum_mu_`r'<.1

	bysort year (mu_spec`r'): egen mu_`r'_ms90 =	max(mu_spec`r') if ms90_`r'==1
	bysort year (mu_spec`r'): egen mu_`r'_ms75 =	max(mu_spec`r') if ms75_`r'==1
	bysort year (mu_spec`r'): egen mu_`r'_ms50 =	max(mu_spec`r') if ms50_`r'==1
	bysort year (mu_spec`r'): egen mu_`r'_ms25 =	max(mu_spec`r') if ms25_`r'==1
	bysort year (mu_spec`r'): egen mu_`r'_ms10 =	max(mu_spec`r') if ms10_`r'==1

	label var mu_`r'_ms90 "p90 (ms)
	label var mu_`r'_ms75 "p75 (ms)
	label var mu_`r'_ms50 "p50 (ms)
	label var mu_`r'_ms25 "p25 (ms)
	label var mu_`r'_ms10 "p10 (ms)
	}



	label var mu_1_ms90 "P90
	label var mu_1_ms50 "P50
	label var mu_1_ms75 "P75
	label var mu_1_ms25 "P25
	label var mu_1_ms10 "P10
	label var MARKUP10_AGG "Average
	scatter  MARKUP10_AGG mu_1_ms90 mu_1_ms75 mu_1_ms50 mu_1_ms25 mu_1_ms10  year , connect(l l l l l l)  msymbol(none none none none none none ) color(red red red red red red) lpattern(solid dash shortdash longdash_dot shortdash_dot longdash) lwidth(thick thick thick thick thick thick) xtitle("") xlabel(1960 1970 1980 1990 2000 2010) ylabel(1 1.5 2 2.5) legend(ring(0)  pos(10) )   sort
graph export "outputFigures/figureDEU3a.eps", replace
		
		
	drop if mu_10<0.5
	drop if mu_10> 3.5
	twoway (kdensity mu_10 if (year==2016 ) , kernel(gaussian) xlabel(1 2 3) lcolor(red) lwidth(thick) ) (kdensity mu_10 if (year==1980 ),  kernel(gaussian)  lcolor(red) ytitle("") xtitle("") clpattern(dash) lwidth(thick) graphregion(color(white) )  legend(ring(0)  col(1) pos(2) label(1 "2016") label(2 "1980")  ) )		
	graph export "outputFigures/figureDEU3b.eps", replace

	
	
	use "intermediateOutput/data_main_upd_trim_1.dta", clear
	
	egen id=group(gvkey)
	drop if id==.
	
	gen s_g2 = xsga/sale
	bysort year: egen s_g2_p1=pctile(s_g2), p(1)
	bysort year: egen s_g2_p99=pctile(s_g2), p(99)
	drop if s_g2<s_g2_p1 & !missing(s_g2)
	drop if s_g2>s_g2_p99 & !missing(s_g2)
	drop s_g2*
	
	sort ind2d year
	merge ind2d year using  "intermediateOutput/theta_W_s_window_fullSample.dta", _merge(theta_Wtime)	
	drop if ind2==52  
	
	gen mu_10 = theta_WI1_ct*(sale_D/cogs_D)
	label var mu_10 "markup PF CD-sector-time (RED)
	gen mu_11 = theta_WI2_ct*(sale_D/cogs_D)
	label var mu_11 "markup PF CD-sector-time (BLUE)

	bysort year:  	egen TOTSALES 	= sum(sale_D)
	gen share_firm_agg 				= sale_D/TOTSALES
	bysort year:  	egen TOTCOST 	= sum(cogs_D+xsga_D)
	gen share_firm_cost= (cogs_D+xsga_D)/TOTCOST

	bysort ind2 year: egen sectorShare=sum(share_firm_agg)


	forvalues i=10/11{
	bysort year: egen MARKUP`i'_AGG 	= sum(share_firm_agg*mu_`i')
	bysort year: egen MARKUP`i'_COST 	= sum(share_firm_cost*mu_`i')
	label var MARKUP`i'_AGG "Markup `i'[w=s]
	}
	

	gen mu_spec1	= mu_10
	
	preserve
	* cut-off year
	keep if year>1979 & year<=2016
	drop if ind2d <9 
	drop if ind2d>99
	bysort year: egen ts = sum(sale_D)
	gen msagg = sale_D/ts

	xtset id year, yearly
	foreach x of varlist mu_spec1 {
	bysort year: egen MU_agg 		= sum(msagg*`x')
	xtset id year, yearly
	gen d`x' 	= D.`x'
	gen Lms 	= L.msagg
	gen demean`x'= `x'-MU_agg
	gen L`x' 	= L.demean`x'
	gen Lmsagg	= L.msagg
	gen dmsagg  = D.msagg
	bysort year: egen Dagg`x' 		= sum(d`x'*Lmsagg)
	bysort year: egen Daggms`x'		= sum(dmsagg*L`x')
	bysort year: egen Cross_agg`x' 	= sum(dmsagg*d`x')
	bysort ind2d year: egen D`x' 	= sum(d`x'*Lms)
	bysort ind2d year: egen Dms`x' 	= sum(dms*L`x')
	bysort ind2d year: egen Cross`x' 	= sum(dms*d`x')
	}
	* aggregate 
	sort year
	drop if year==year[_n-1]
	gen DMU_agg = MU_agg -MU_agg[_n-1]
	gen net_entry = DMU_agg - Daggmu_spec - Daggms -Cross_agg
	gen REALL = net_entry + Daggms +Cross_agg
	gen reall_inc = Daggms + Cross_agg
	*initialise at 1980 so keep from 1980
	gen Dagg_sum 	= sum(Daggmu)
	gen Daggms_sum 	= sum(Daggms)
	gen Cross_sum		= sum(Cross_agg)
	gen Net_sum		= sum(net_entry)
	gen Reall_sum	= sum(REALL)	
	gen reall_inc_s	= sum(reall_inc)
	gen a	=	1 if year==1980
	egen a_m = mean(MU_agg) if a==1
	egen a_mu = mean(a_m)
	foreach x of varlist Dagg_sum Daggms_s Cross_s Net_s Reall_s reall_inc_s {
	replace `x' = `x'+a_mu
	}
	label var MU_agg "Markup (benchmark)
	label var Dagg_sum "Within 
	label var Net_s "Net Entry 
	label var reall_inc_s "Reallocation
	scatter MU_agg Dagg_sum  reall_inc_s Net_s   year , c(l l l l) lwidth(thick thick thick medium) lpattern(_.- dash shortdash l) lcolor(black red blue  green)  yscale(range(1.0 1.65)) ylabel(1 1.1 1.2 1.3 1.4 1.5 1.6) xlabel(1980 1990 2000 2010) msymbol(none none none none none) sort xtitle("") legend(ring(0)  pos(11) ) 
	graph export "outputFigures/figureDEU4.eps", replace

	restore		



* Figure 1, drop 3254
use "intermediateOutput/markup_DEU.dta", clear
merge 1:1 year using "intermediateOutput/markup_full.dta"
drop _merge
merge 1:1 year using "intermediateOutput/markup_full_no3254.dta"

label var MARKUP10_AGG_DEU "DEU Sample"
label var MARKUP10_AGG_full_no52_no3254 "Full Sample, No F&I, No 3254"
label var MARKUP10_AGG_full_no52 "Full Sample, No F&I"

line MARKUP10_AGG_DEU MARKUP10_AGG_full_no52_no3254 MARKUP10_AGG_full_no52 year, lcolor(red green black) lwidth(medthick thick thick)  msymbol(O S T) lpattern(l - _.-) legend(ring(0) pos(11)) ytitle("Sales Weighted Markup") xtitle("")
graph export "outputFigures/figure1_drop3254.eps", replace
			
			
* Just sector 32
use "intermediateOutput/markup_DEU.dta", clear
merge 1:1 year using "intermediateOutput/markup_full.dta"
drop _merge
merge 1:1 year using "intermediateOutput/census.dta"
label var MARKUP10_AGG_DEU_man32 "DEU Sample, Sector 32"
label var MARKUP10_AGG_full_man32 "Full Sample, Sector 32"
label var census32 "DEU Reported Census Sector 32"
line MARKUP10_AGG_DEU_man32 census32 MARKUP10_AGG_full_man32 year, lcolor(red green black) lwidth(medthick medium thick)  msymbol(O S T) lpattern(l - _.-) legend(ring(0) pos(11)) ytitle("Sales Weighted Markup") xtitle("")
graph export "outputFigures/figure_man32.eps", replace			


* Just manufacturing
use "intermediateOutput/markup_DEU.dta", clear
merge 1:1 year using "intermediateOutput/markup_full.dta"
drop _merge
merge 1:1 year using "intermediateOutput/census.dta"

gen DEU1980=MARKUP10_AGG_DEU_man if year==1980
egen DEU1980fill=max(DEU1980)
gen DEUnorm=MARKUP10_AGG_DEU_man/DEU1980fill

gen full1980=MARKUP10_AGG_full_man if year==1980
egen full1980fill=max(full1980)
gen fullnorm=MARKUP10_AGG_full_man/full1980fill

* linear interpolation of census between 1977 and 1982 to get 1980 value
replace censusman=(1.54*2+1.59*3)/5 if year==1980
gen censusman1980=censusman if year==1980
egen censusman1980fill=max(censusman1980)
gen censusnorm=censusman/censusman1980fill


label var DEUnorm "DEU Sample, Manufacturing"
label var fullnorm "Full Sample, Manufacturing"
label var censusnorm "Census, Manufacturing"

line DEUnorm censusnorm fullnorm year, lcolor(red green black) lwidth(medthick medium thick)  msymbol(O S T) lpattern(l - _.-) legend(ring(0) pos(11)) ytitle("Normalized Sales Weighted Markup (1980=1)") xtitle("")
graph export "outputFigures/figure_man.eps", replace			