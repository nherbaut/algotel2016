set N	:= {read "substrate.nodes.data" as "<1s>"};
set NS	:= {read "service.nodes.data" as "<1s>"};

set E := { read "substrate.edges.data" as "<1s,2s>"};
set Et := { <u,v> in N cross N with <v,u> in E};
set ES := { read "service.edges.data" as "<1s,2s>"};

set CDN_ASSIGNED := {read "CDN.nodes.data" as "<1s,2s>"};
set CDN := {read "CDN.nodes.data" as "<1s>"};
set CDN_ES := {<i,j> in ES inter (NS cross CDN) with i!=j};
set VHG := {read "VHG.nodes.data" as "<1s>"};
set VHG_ES := {<i,j> in ES inter (NS cross VHG) with i!=j};
set VCDN := {read "VCDN.nodes.data" as "<1s>"};
set VCDN_ES := {<i,j> in ES inter (NS cross VCDN) with i!=j};
set S := {read "starters.nodes.data" as "<1s>"};
set S_ASSIGNED := {read "starters.nodes.data" as "<1s,2s>"};
set S_ES := {<i,j> in ES inter (NS cross S) with i!=j};

set VHG_LABEL := {read "VHG.nodes.data" as "<1s>"};
set VHG_INCOMING_LINKS := {<i,j> in ES inter (NS cross VHG_LABEL) with i!=j};
set VHG_OUTGOING_LINKS := {<i,j> in ES inter (VHG_LABEL cross NS) with i!=j};


set VCDN_LABEL := {read "VCDN.nodes.data" as "<1s>"};
set VCDN_INCOMING_LINKS := {<i,j> in ES inter (NS cross VCDN_LABEL)};



set STARTERS_MAPPING := {read "starters.nodes.data" as "<1s,2s>"};
set STARTERS_LABEL := {read "starters.nodes.data" as "<1s>"};
set STARTERS_OUTGOING_LINKS := {<i,j> in ES inter (STARTERS_LABEL cross NS) with i!=j};
set STARTERS_INCOMING_LINKS := {<i,j> in ES inter (NS cross STARTERS_LABEL ) with i!=j};

defset delta(u) := { <v> in N with <u,v> in (E union Et)};

param cpuS[NS] := read "service.nodes.data" as "<1s> 2n";
param cpu[N] := read "substrate.nodes.data" as "<1s> 2n";

param delays[E] := read "substrate.edges.data" as "<1s,2s> 4n";
param delayst[Et] := read "substrate.edges.data" as "<2s,1s> 4n";
param delaysS[ES] := read "service.edges.data" as "<1s,2s> 4n";



param bwS[ES] := read "service.edges.data" as "<1s,2s> 3n";
param bw[E] := read "substrate.edges.data" as "<1s,2s> 3n";
param bwt[Et] := read "substrate.edges.data" as "<2s,1s> 3n";
param source := read "starters.nodes.data" as "2s" use 1;
param cdn_count := read "cdnmax.data" as "1n" use 1;
param cdnratio := 0.65;



var x[N cross NS ] binary;
var x_cdn[N cross CDN ] binary;
var y [(E union Et) cross ES ] binary;
var y_cdn [(E union Et) cross ES ] binary;
var w binary;
var cdns_var [CDN_LABEL] binary;
var rho[ES] binary;
var gamma[NS] binary;

subto gammaMustHave:
  forall <i> in STARTERS_LABEL  union {"S0"}:
    gamma[i]==1;

subto rhoMustHave:
  forall <i,j> in STARTERS_INCOMING_LINKS  union STARTERS_OUTGOING_LINKS:
   rho[i,j]==1;




#maximize cost:
#			    sum <u,v> in E:
#					((bw[u,v]-sum <i,j> in ES:(y[u,v,i,j] * bwS[i,j] ))/(bw[u,v]))+
#				sum <u,v> in Et:
#				    ((bw[v,u]-sum <i,j> in ES:(y[u,v,i,j] * bwS[i,j] ))/(bw[v,u]));



minimize cost:
                sum<u,v,i,j> in (E union Et) cross ES: y[u,v,i,j];

subto mappingVHGVCDN:
	forall <j> in VHG union VCDN:
		sum<u> in N: x[u,j] == gamma[j];



subto everyNodeIsMapped:
	forall <j> in NS\CDN_LABEL:
		sum<i> in N: x[i,j]==1;



#subto onVHGPerSource:
#  forall <i> in STARTERS_LABEL:
#     forall <uu,vv> in { <uu,vv> in (E union Et) }:
#      vif x[uu,i]==1 then
#        sum <ii,jj> in { <ii,jj> in ES with ii!=i}:
#            y[uu,vv,ii,jj]==1
#      end;


subto oneVhgPerSource:
    forall <s,u> in STARTERS_MAPPING:
      sum <uu,vv,ii,jj> in { <uu,vv,ii,jj> in (E union Et) cross ES with uu==u and ii==s}:
        y[uu,vv,ii,jj]<=1;



subto popRes:
	forall <i> in N:
		sum<j> in NS: x[i,j]*cpuS[j] <= cpu[i];

		
subto bwSubstrate:
   forall <u,v> in E:
       sum<i,j> in ES\CDN_LINKS: (y[u,v,i,j]+y[v,u,i,j]) * bwS[i,j] <= bw[u,v];
       
subto bwtSubstrate:
   forall <u,v> in Et:
       sum<i,j> in ES\CDN_LINKS: (y[u,v,i,j]+y[v,u,i,j]) * bwS[i,j] <= bwt[u,v];





subto flowconservation:
   forall <i,j> in {<i,j> in ES\CDN_LINKS }:
      forall <u> in N:
         sum<v> in {<v> in N with <u,v> in (E union Et)}:
                    (y[u, v, i, j] - y[v, u, i,j]) == x[u,i]-x[u,j];

subto flowconservation_cdn:
   forall <i,j> in {<i,j> in CDN_ES  with i != j}:
      forall <u> in N:
         sum<v> in {<v> in N with <u,v> in (E union Et)}: (y[u, v, i, j] - y[v, u, i,j]) *cdns_var[j]==( (x[u,i]-x[u,j])*cdns_var[j]);

subto startsource:
    forall <o> in origin:
        x[source,o]==1;

subto sources:
    forall <name,id> in S_ASSIGNED:
        x[id,name]==1;

subto onlyXCDN:
  sum <i> in (CDN) :
    cdns_var[i] ==cdn_count;

subto cdnToNode:
	forall <i,j> in CDN_ASSIGNED:
		x[j,i]==cdns_var[i];


subto popRes:
	forall <i> in N:
    	sum<j> in NS: x[i,j]*cpuS[j] <= cpu[i];


subto noloop:
	forall <i,j> in {<i,j> in ES  with i != j}:
		forall <u,v> in (E union Et):
			y[u, v, i, j] + y[v, u, i,j] <= 1;

subto noBigloop:
	forall <i,j> in {<i,j> in ES  with i != j}:
		forall <u> in N:
			sum <v> in delta(u):
			  y[u,v,i,j] <= 1;
		
		
		

subto startsource:
    x[source,"S0"]==1;
    
subto sources:
    forall <name,id> in STARTERS_MAPPING:
        x[id,name]==1;

subto only1CDN:
  sum <i> in (CDN_LABEL) : cdns_var[i] ==cdn_count;

subto cdnToNode:
	forall <i,j> in CDN:
		x[j,i]==cdns_var[i];

subto flowconservation_cdn:
   forall <i,j> in {<i,j> in CDN_LINKS  with i != j}:
      forall <u> in N:
         sum<v> in {<v> in N with <u,v> in (E union Et)}: (y[u, v, i, j] - y[v, u, i,j]) *cdns_var[j]==( (x[u,i]-x[u,j])*cdns_var[j]);


