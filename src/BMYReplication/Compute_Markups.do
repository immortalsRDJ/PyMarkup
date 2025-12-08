capture program drop Compute_Markups
program define Compute_Markups
	syntax, includeinterestcogs(integer) dropmissingsga(integer) drop3254(integer)

 
 

  if `includeinterestcogs' == 1 {
	use "intermediateOutput/data_main_upd_trim_1_intExp.dta", clear
  }
  else {
	use "intermediateOutput/data_main_upd_trim_1.dta", clear
  }
  

  
gen costshare1 = cogs_D/(cogs_D+kexp)
gen costshare2 = cogs_D/(cogs_D+xsga_D+kexp)    
  
  
 if `dropmissingsga' == 1 {
	
	*DEU dropping criteria
forvalues s=1/2 {
bysort year: egen cs`s'_p1=pctile(costshare`s'), p(1)
bysort year: egen cs`s'_p99=pctile(costshare`s'), p(99)
drop if costshare`s'==0 | costshare`s'==.
drop if costshare`s' > cs`s'_p99 
drop if costshare`s' < cs`s'_p1
}
* This limits to the observations in DEU that overlap
joinby gvkey year using "rawData/deu_observations.dta"

 }
 else {
 	
	*Trim on sale to sga ratio (DEU says they do this, but they don't)
gen s_g2 = sale/xsga
bysort year: egen s_g2_p1=pctile(s_g2), p(1)
bysort year: egen s_g2_p99=pctile(s_g2), p(99)
drop if s_g2<s_g2_p1 & !missing(s_g2)
drop if s_g2>s_g2_p99 & !missing(s_g2)
drop s_g2*

 }
 
 if `drop3254' == 1 {
	drop if ind4d==3254
 } 
 
 
egen id=group(gvkey)
drop if id==.
 
 
sort ind2d year

if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 1 )  {
	merge m:1 ind2d year using "intermediateOutput/theta_W_s_window_DEUSample.dta", gen(theta_Wtime)
	merge m:1 ind2d year using "intermediateOutput/theta_acf_DEUSample.dta", gen(theta_ACFtime)	
  }
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 0)  {
	merge m:1 ind2d year using  "intermediateOutput/theta_W_s_window_fullSample.dta", gen(theta_Wtime)
	merge m:1 ind2d year using  "intermediateOutput/theta_acf_fullSample.dta", gen(theta_ACFtime)
	merge m:1 ind2d year using  "intermediateOutput/theta_c_fullSample.dta", gen(theta_costShare)	
   }
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 1) {
	merge m:1 ind2d year using  "intermediateOutput/theta_W_s_window_no3254.dta", gen(theta_Wtime)
	merge m:1 ind2d year using  "intermediateOutput/theta_acf_no3254.dta", gen(theta_ACFtime)
	merge m:1 ind2d year using  "intermediateOutput/theta_c_no3254.dta", gen(theta_costShare)	
   }   
  else if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 0 )  {
	merge m:1 ind2d year using  "intermediateOutput/theta_W_s_window_fullSample_intExp.dta", gen(theta_Wtime)
	merge m:1 ind2d year using  "intermediateOutput/theta_acf_fullSample_intExp.dta", gen(theta_ACFtime)
	merge m:1 ind2d year using  "intermediateOutput/theta_c_fullSample.dta", gen(theta_costShare)	
   }


gen mu_10 = theta_WI1_ct*(sale_D/cogs_D)
gen mu_11 = theta_WI2_ct*(sale_D/cogs_D)
gen mu_12 = theta_acf*(sale_D/cogs_D)





bysort year:  	egen TOTSALES 	= sum(sale_D)
gen share_firm_agg 				= sale_D/TOTSALES

bysort year:  	egen TOTCOGS 	= sum(cogs_D)
gen share_firm_agg_cogs 				= cogs_D/TOTCOGS

gen newSGA=xsga_D 
replace newSGA=0 if missing(newSGA)
bysort year:  	egen TOTOPEX 	= sum(cogs_D+newSGA)
gen share_firm_agg_opex 				= (cogs_D+newSGA)/TOTOPEX


forvalues i=10/12{
bysort year: egen MARKUP`i'_AGG 	= sum(share_firm_agg*mu_`i')
bysort year: egen MARKUP`i'_AGGCOGS 	= sum(share_firm_agg_cogs*mu_`i')
bysort year: egen MARKUP`i'_AGGOPEX 	= sum(share_firm_agg_opex*mu_`i')

}


preserve
drop if ind2==52
bysort year:  	egen TOTSALES_no52 	= sum(sale_D)
gen share_firm_agg_no52 				= sale_D/TOTSALES_no52

bysort year:  	egen TOTCOGS_no52 	= sum(cogs_D)
gen share_firm_agg_cogs_no52 				= cogs_D/TOTCOGS_no52

bysort year:  	egen TOTOPEX_no52 	= sum(cogs_D+newSGA)
gen share_firm_agg_opex_no52 				= (cogs_D+newSGA)/TOTOPEX_no52


forvalues i=10/12{
bysort year: egen MARKUP`i'_AGG_no52 	= sum(share_firm_agg_no52*mu_`i')
bysort year: egen MARKUP`i'_AGGCOGS_no52	= sum(share_firm_agg_cogs_no52*mu_`i')
bysort year: egen MARKUP`i'_AGGOPEX_no52 	= sum(share_firm_agg_opex_no52*mu_`i')

}

keep if ind2==31 | ind2==32 | ind2==33
bysort year:  	egen TOTSALES_man 	= sum(sale_D)
gen share_firm_agg_man 				= sale_D/TOTSALES_man


forvalues i=10/12{
bysort year: egen MARKUP`i'_AGG_man 	= sum(share_firm_agg_man*mu_`i')

}


keep if ind2==32
bysort year:  	egen TOTSALES_man32 	= sum(sale_D)
gen share_firm_agg_man32 				= sale_D/TOTSALES_man32


forvalues i=10/12{
bysort year: egen MARKUP`i'_AGG_man32 	= sum(share_firm_agg_man32*mu_`i')

}





duplicates drop year, force

if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 1 )  {
	rename MARKUP10_AGG MARKUP10_AGG_DEU
	rename MARKUP10_AGG_no52 MARKUP10_AGG_DEU_no52
	
	rename MARKUP10_AGGCOGS MARKUP10_AGGCOGS_DEU
	rename MARKUP10_AGGCOGS_no52 MARKUP10_AGGCOGS_DEU_no52

	rename MARKUP10_AGGOPEX MARKUP10_AGGOPEX_DEU
	rename MARKUP10_AGGOPEX_no52 MARKUP10_AGGOPEX_DEU_no52
	
	rename MARKUP12_AGG MARKUP12_AGG_DEU
	rename MARKUP12_AGG_no52 MARKUP12_AGG_DEU_no52	


	rename MARKUP10_AGG_man MARKUP10_AGG_DEU_man
	rename MARKUP10_AGG_man32 MARKUP10_AGG_DEU_man32
	
	save "intermediateOutput/markup_DEU.dta", replace
  } 
  else if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 0 )   {
	rename MARKUP10_AGG MARKUP10_AGG_full_intExp
	rename MARKUP10_AGG_no52 MARKUP10_AGG_full_int_no52
	rename MARKUP12_AGG MARKUP12_AGG_full_intExp
	rename MARKUP12_AGG_no52 MARKUP12_AGG_full_int_no52	
	save "intermediateOutput/markup_full_intExp.dta", replace
  }

  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 )  & ( `drop3254' == 0 )  {
	rename MARKUP10_AGG MARKUP10_AGG_full
	rename MARKUP10_AGG_no52 MARKUP10_AGG_full_no52
	rename MARKUP12_AGG MARKUP12_AGG_full
	rename MARKUP12_AGG_no52 MARKUP12_AGG_full_no52	
	
	rename MARKUP10_AGGCOGS MARKUP10_AGGCOGS_full
	rename MARKUP10_AGGCOGS_no52 MARKUP10_AGGCOGS_full_no52	
	
	rename MARKUP10_AGGOPEX MARKUP10_AGGOPEX_full
	rename MARKUP10_AGGOPEX_no52 MARKUP10_AGGOPEX_full_no52	
	
	rename MARKUP10_AGG_man MARKUP10_AGG_full_man
	rename MARKUP10_AGG_man32 MARKUP10_AGG_full_man32
		
	save "intermediateOutput/markup_full.dta", replace
}

  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 )  & ( `drop3254' == 1 )  {
	rename MARKUP10_AGG MARKUP10_AGG_no3254
rename MARKUP10_AGG_no52 MARKUP10_AGG_full_no52_no3254
	

	save "intermediateOutput/markup_full_no3254.dta", replace
}


end

 
 
 
 
