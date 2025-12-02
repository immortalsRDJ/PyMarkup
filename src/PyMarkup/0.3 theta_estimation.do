* Main replication file
* Benkard, Miller, and Yurukoglu
* Modified by Claire Meng Oct 2025

* set directory

// cd "C:\BMYReplication"

cd "/Users/clairemeng/Dropbox/NYU/RA_Conlon/DLEU_replication/RisingPricesRisingMarkupsReplication/"
clear all

* Clean_Data.do
* This code is essentially identical to the DEU QJE supplementary materials
* Import Compustat, deflate using macrovars.dta (Here i deflate using macro_vars_new.dta, updated to 2025, by Claire)
	* Option for including interest expense in COGS or not (1 = include)
	do "Code/Create_Data.do"
	/* Create_Data, includeinterestcogs(1) */ // (Ignore interest expense in COGS, by Claire)
	Create_Data, includeinterestcogs(0)
	
* Analyze missing SG&A observations

	/* ssc install estout, replace
	do Analyze_Missing.do
	Analyze_Missing  */


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
	do "Code/Estimate_Coefficients.do"
	// run with dropmissingsga(0) to keep observations that DLEU would have dropped due to missing SGA, by Claire

	/* Estimate_Coefficients, includeinterestcogs(1) dropmissingsga(0) */
	Estimate_Coefficients, includeinterestcogs(0) dropmissingsga(0)
	/* Estimate_Coefficients, includeinterestcogs(1) dropmissingsga(1)
	Estimate_Coefficients, includeinterestcogs(0) dropmissingsga(1) */

    