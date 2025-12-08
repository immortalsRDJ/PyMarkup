* Main replication file
* Benkard, Miller, and Yurukoglu


* set directory

cd "C:\BMYReplication"


clear all

* Clean_Data.do
* This code is essentially identical to the DEU QJE supplementary materials
* Import Compustat, deflate using macrovars.dta
	* Option for including interest expense in COGS or not (1 = include)
	do Create_Data.do
	Create_Data, includeinterestcogs(1)
	Create_Data, includeinterestcogs(0)
	
* Analyze missing SG&A observations

	ssc install estout, replace
	do Analyze_Missing.do
	Analyze_Missing 


* Estimate production function coefficients
* Option for drop missing SGA or not


*-------------------------------------BEGIN MATA PROGRAM--------------------------------------------*
capture mata: mata drop GMM_DL()
mata:
void GMM_DL(todo, betas, PHI, PHI_LAG, Z, X, X_lag, W, crit, g, H)
{
    real matrix CONST, OMEGA, OMEGA_lag, OMEGA2_lag, OMEGA_lag_pol, g_b, XI
    // others like crit, g, H are assumed output variables

    CONST = J(rows(PHI), 1, 1)

    // Gross Output Criterion Function
    OMEGA = PHI - X * betas'
    OMEGA_lag = PHI_LAG - X_lag * betas'
    OMEGA2_lag = OMEGA_lag :* OMEGA_lag
    OMEGA_lag_pol = (CONST, OMEGA_lag)

    g_b = invsym(OMEGA_lag_pol' * OMEGA_lag_pol) * OMEGA_lag_pol' * OMEGA
    XI = OMEGA - OMEGA_lag_pol * g_b
    crit = (Z' * XI)' * W * (Z' * XI)
}
end
*-----------------------END MATA PROGRAM---------------------------------------*	
	do Estimate_Coefficients.do
	
	Estimate_Coefficients, includeinterestcogs(1) dropmissingsga(0) drop3254(0)
	Estimate_Coefficients, includeinterestcogs(0) dropmissingsga(0) drop3254(0)
	Estimate_Coefficients, includeinterestcogs(0) dropmissingsga(0) drop3254(1)
	Estimate_Coefficients, includeinterestcogs(0) dropmissingsga(1) drop3254(0)

* Compute markups 
* Option for drop missing SGA or not

	do Compute_Markups.do
	Compute_Markups, includeinterestcogs(0) dropmissingsga(0) drop3254(0)
	Compute_Markups, includeinterestcogs(0) dropmissingsga(0) drop3254(1)
	Compute_Markups, includeinterestcogs(1) dropmissingsga(0) drop3254(0)
	Compute_Markups, includeinterestcogs(0) dropmissingsga(1) drop3254(0)
	
* Make figures

	do Markup_Figures.do