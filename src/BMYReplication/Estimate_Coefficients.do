capture program drop Estimate_Coefficients
program define Estimate_Coefficients
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
/*
	forvalues s=1/2 {
		bysort year: egen cs`s'_p1=pctile(costshare`s'), p(1)
		bysort year: egen cs`s'_p99=pctile(costshare`s'), p(99)
	}

	drop if costshare1==0   /* 0 obs dropped because COGS=0 screen in create_data */
	drop if costshare1==.   /* 33,422 obs dropped due to missing capital */

	drop if costshare1 > cs1_p99  /* 207 dropped */
	drop if costshare1 < cs1_p1   /* 3,173 dropped */

	drop if costshare2==0  /* 0 obs dropped because COGS=0 screen in create_data */
	drop if costshare2==.  /* 63,571 dropped due to missing SGA (20.3% of obs) */
	
	drop if costshare2 > cs2_p99  /* 2,499 dropped */
	drop if costshare2 < cs2_p1   /* 1,532 droopped */
	*/
	
}
 else {
 	
	*Trim on sale to sga ratio (DEU says they do this, but they don't)
	gen s_g2 = xsga/sale
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

gen theta_WI1_ct = .
gen theta_WI2_ct = .
gen theta_WI2_xt = .
gen theta_WI1_kt = .
gen theta_WI2_kt = .


* variable definition
gen r	=	ln(sale_D) 
gen y	=	ln(sale_D) 
gen c	=	ln(cogs_D)
gen c2	=	c^2
gen c3	= 	c^3

gen k	=	ln(capital_D)
gen k2	=	k^2
gen ck	=	c*k
gen k3  =   k^3
gen depr = 0.1

gen lsga=ln(xsga_D)
gen lsga2=lsga^2

*drop if id==.

xtset id year, yearly
gen ind2d_fix = ind2d
replace ind2d_fix = 48 if ind2d==49 
* transportation and warehousing put together, too few numbers in ind 49
*drop nrind*
* make sure all previous code on nrind is gone
egen nrind2 = group(ind2d_fix)
xtset id year, yearly

gen K	= exp(k)
gen Inv  = K - (1-depr)*L.K
gen i	 = ln(Inv)
gen i2	 = i^2
gen i3 	 = i^3
gen ik 	 = i*k
* rolling window
quietly { 
forvalues s=1/16 {
ivregress gmm r (c =L.c) k L.i L.k2 L.k  if nrind ==`s' & year<1972
replace theta_WI1_ct = _b[c] if nrind==`s' & year<1970
replace theta_WI1_kt = _b[k] if nrind==`s' & year<1970
ivregress gmm r (c =L.c) k lsga L.i L.k2 L.lsga2 L.k L.lsga if nrind2 ==`s'  & year<1972
replace theta_WI2_ct = _b[c] if nrind==`s' & year<1970
replace theta_WI2_xt = _b[lsga] if nrind==`s' & year<1970
replace theta_WI2_kt = _b[k] if nrind==`s' & year<1970
}

forvalues s=18/22 {
ivregress gmm r (c =L.c) k L.i L.k2 L.k  if nrind ==`s' & year<1972
replace theta_WI1_ct = _b[c] if nrind==`s' & year<1970
replace theta_WI1_kt = _b[k] if nrind==`s' & year<1970
ivregress gmm r (c =L.c) k lsga L.i L.k2 L.lsga2 L.k L.lsga if nrind2 ==`s'  & year<1972
replace theta_WI2_ct = _b[c] if nrind==`s' & year<1970
replace theta_WI2_xt = _b[lsga] if nrind==`s' & year<1970
replace theta_WI2_kt = _b[k] if nrind==`s' & year<1970
}

* fix sector 61 / ind 17 by giving longer first period.
ivregress gmm r (c =L.c) k L.i L.k2 L.k  if nrind ==17 & year<1985
replace theta_WI1_ct = _b[c] if nrind==17 & year<1985
replace theta_WI1_kt = _b[k] if nrind==17 & year<1985
ivregress gmm r (c =L.c) k lsga L.i L.k2 L.lsga2 L.k L.lsga if nrind2 ==17  & year<1985
replace theta_WI2_ct = _b[c] if nrind==17 & year<1985
replace theta_WI2_xt = _b[lsga] if nrind==17 & year<1985
replace theta_WI2_kt = _b[k] if nrind==17 & year<1985

forvalues t= 1970 / 2016 {
gen window_`t' = 1 if year ==`t' | year==`t'-1 | year==`t'+1 | year==`t'-2 | year==`t'+2
xtset id year, yearly
forvalues s=1/16 {
ivregress gmm r (c =L.c) k L.i L.k2 L.k  if nrind ==`s' & window_`t'==1 
replace theta_WI1_ct = _b[c] if nrind==`s' & year==`t' 
replace theta_WI1_kt = _b[k] if nrind==`s' & year==`t' 
ivregress gmm r (c =L.c) k lsga L.i L.k2 L.lsga2 L.k L.lsga if nrind ==`s'  & window_`t'==1 
replace theta_WI2_ct = _b[c] if nrind==`s' & year==`t'
replace theta_WI2_xt = _b[lsga] if nrind==`s' & year==`t'
replace theta_WI2_kt = _b[k] if nrind==`s' & year==`t'
}
}

forvalues t= 1970 / 2016 {
xtset id year, yearly
forvalues s=18/22 {
ivregress gmm r (c =L.c) k L.i L.k2 L.k  if nrind ==`s' & window_`t'==1 
replace theta_WI1_ct = _b[c] if nrind==`s' & year==`t' 
replace theta_WI1_kt = _b[k] if nrind==`s' & year==`t' 
ivregress gmm r (c =L.c) k lsga L.i L.k2 L.lsga2 L.k L.lsga if nrind ==`s'  & window_`t'==1 
replace theta_WI2_ct = _b[c] if nrind==`s' & year==`t'
replace theta_WI2_xt = _b[lsga] if nrind==`s' & year==`t'
replace theta_WI2_kt = _b[k] if nrind==`s' & year==`t'
}
}

forvalues t= 1985 / 2016 {
forvalues s=17/17 {
ivregress gmm r (c =L.c) k L.i L.k2 L.k  if nrind ==`s' & window_`t'==1 
replace theta_WI1_ct = _b[c] if nrind==`s' & year==`t' 
replace theta_WI1_kt = _b[k] if nrind==`s' & year==`t' 
ivregress gmm r (c =L.c) k lsga L.i L.k2 L.lsga2 L.k L.lsga if nrind ==`s'  & window_`t'==1 
replace theta_WI2_ct = _b[c] if nrind==`s' & year==`t'
replace theta_WI2_xt = _b[lsga] if nrind==`s' & year==`t'
replace theta_WI2_kt = _b[k] if nrind==`s' & year==`t'
}
}


preserve
keep ind2d theta_WI* year 
sort ind2d year
drop if ind2d==ind2d[_n-1] & year==year[_n-1]

	
} 

if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 1 ) {
	save "intermediateOutput/theta_W_s_window_DEUSample_intExp.dta", replace
  }
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 1 )  {
	save "intermediateOutput/theta_W_s_window_DEUSample.dta", replace
  }
  else if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 0 )  {
	save "intermediateOutput/theta_W_s_window_fullSample_intExp.dta", replace
  }  
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 0 )  {
	save "intermediateOutput/theta_W_s_window_fullSample.dta", replace
}
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 1 )  {
	save "intermediateOutput/theta_W_s_window_no3254.dta", replace
}
restore




*4 THIS PART GENERATES COST-SHARE OUTPUT ELASTICITY ESTIMATES
qui {
bysort year ind2d: egen cs2d = median(costshare1)
bysort year ind3d: egen cs3d = median(costshare1)
bysort year ind4d: egen cs4d = median(costshare1)
}


preserve
keep ind2d cs2d cs3d cs4d year 
sort ind2d year
drop if ind2d==ind2d[_n-1] & year==year[_n-1]


if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 1 ) {
	save "intermediateOutput/theta_c_DEUSample_intExp.dta", replace
  }
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 1 )  {
	save "intermediateOutput/theta_c_DEUSample.dta", replace
  }
  else if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 0 ) {
	save "intermediateOutput/theta_c_fullSample_intExp.dta", replace
  }
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 0 )  {
	save "intermediateOutput/theta_c_fullSample.dta", replace
}
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 1 ) {
	save "intermediateOutput/theta_c_no3254.dta", replace
}

  
restore




*3. OP_ACF one step [1.3] -- E[\epsilon c_[t]]=0, d= investment
qui {


bysort ind2d year: egen totsales = sum(sale_D)
bysort ind3d year: egen totsales3d = sum(sale_D)
bysort ind4d year: egen totsales4d = sum(sale_D)
gen ms2d = (sale_D/totsales)
gen ms3d = (sale_D/totsales3d)
gen ms4d = (sale_D/totsales4d)

drop window_*
forvalues t= 1970 / 2016 {
gen window_`t' = 1 if year ==`t' | year==`t'-1 | year==`t'+1 | year==`t'-2 | year==`t'+2
}

xtset id year, yearly
gen c_lag=L.c
gen k_lag=L.k
forvalues s= 1/22 {
	forvalues t= 1970 / 2016 {


preserve 
keep if nrind2==`s' & window_`t'==1

// Phi Function
global phireg="c c2 k k2 ck ms2d ms4d i.year"



* 1st stage , d=cogs z=ms2d, ms4d
*xi: reg y  c k c2 k2 ck  ms2d ms4d i.year
reg y $phireg
predict phi
predict epsilon, res
gen phi_lag=L.phi
label var phi "phi_it in ACF"
label var epsilon "epsilon 1st stage markup correction
drop if c_lag==.  | k==. | k_lag==. | phi==. | phi_lag==. | y==. 

gen const=1

// Cobb-Douglas: y=b_c*c+b_k*k
mata: PHI=st_data(.,("phi"))
mata: PHI_LAG=st_data(.,("phi_lag"))
mata: Z=st_data(.,("const","c_lag","k"))
mata: X=st_data(.,("const","c","k"))
mata: X_lag=st_data(.,("const", "c_lag","k_lag"))
mata: W=I(cols(Z))
mata: S=optimize_init()

mata: optimize_init_evaluator(S, &GMM_DL())
mata: optimize_init_evaluatortype(S,"d0")
mata: optimize_init_technique(S, "nm")
mata: optimize_init_nmsimplexdeltas(S, 0.1)
mata: optimize_init_which(S,"min")

// These starting values come from OLS Version or COST-SHARE 
mata: optimize_init_params(S,(0,0.9,0.1))
mata: optimize_init_argument(S, 1, PHI)
mata: optimize_init_argument(S, 2, PHI_LAG)
mata: optimize_init_argument(S, 3, Z)
mata: optimize_init_argument(S, 4, X)
mata: optimize_init_argument(S, 5, X_lag)
mata: optimize_init_argument(S, 6, W)

// Minimize Criterion
mata: p=optimize(S)
mata: p
mata: st_matrix("beta_dl",p)

scalar betac=beta_dl[1,2]
scalar betak=beta_dl[1,3]
gen theta_c_ind`s' = beta_dl[1,2]
keep ind2d nrind2 year theta_c_ind`s'
sort ind2d year
drop if ind2d==ind2d[_n-1] & year==year[_n-1]

save "intermediateOutput/theta_ind`s'_`t'.dta", replace
restore
}
}

use "intermediateOutput/theta_ind1_1970.dta", clear
forvalues t=1971/2016 {

append using "intermediateOutput/theta_ind1_`t'.dta"
	
}

forvalues s=2/22 {
	
	forvalues t=1970/2016 {
append using "intermediateOutput/theta_ind`s'_`t'.dta"
}
}

sort nrind2 year
drop if nrind2==nrind2[_n-1]  & year==year[_n-1]
gen THETA_C=.
forvalues s=1/22 {
	
	forvalues t=1970/2016 {
replace THETA_C = theta_c_ind`s' if nrind2==`s' & year==`t'
}
}

keep nrind2 ind2 year THETA_C


rename THETA_C theta_acf
sort ind2d year
}


if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 1 ) {
	save "intermediateOutput/theta_acf_DEUSample_intExp.dta", replace
  }
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 1 )  {
	save "intermediateOutput/theta_acf_DEUSample.dta", replace
  }
  else if (`includeinterestcogs' == 1) & ( `dropmissingsga' == 0 )  {
	save "intermediateOutput/theta_acf_fullSample_intExp.dta", replace
  }
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 0 )    {
	save "intermediateOutput/theta_acf_fullSample.dta", replace
}
  else if (`includeinterestcogs' == 0) & ( `dropmissingsga' == 0 ) & ( `drop3254' == 1 ) {
	save "intermediateOutput/theta_acf_no3254.dta", replace
}




  
end

