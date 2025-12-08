Main.do will produce all the graphs and figures in the paper.

1. It requires a data file to be downloaded from Compustat. Here are the specifications for a download that produces the results of this paper. 

Variables:
	dvt 
	emp 
	tie 
	tii 
	xad 
	xlr 
	xrd 
	cogs 
	conm 
	sale 
	sich 
	xsga 
	curcd 
	fyear 
	gvkey 
	intan 
	naics 
	oibdp 
	ppegt 
	ppent 
	consol 
	costat 
	indfmt 
	mkvalt 
	datafmt 
	idbflag 
	datadate 
	extra1	[1]
	0	:	C
	extra2		[2]
	0	:	INDL
	1	:	FS
	extra3		[1]
	0	:	STD
	extra5		[2]
	0	:	USD
	1	:	CAD
	extra7		[2]
	0	:	A
	1	:	I
	
file	:	funda
qvar	:	comp_na_daily_all.company.gvkey
datef	:	YYYY-MM-DD
idvar	:	gvkey
end_date	:	2016-12-31
id_table	:	company
begin_date	:	1955-01-01

2. It also requires a list of firm ID's (gvkey) and years that match the dataset used by DEU (denoted DEU_observations.dta) that we obtained from the DEU authors. One can still run this code by commenting out all instances of "joinby gvkey year using "rawData/deu_observations.dta", but the DEU replication will match less closely to the published result. 

