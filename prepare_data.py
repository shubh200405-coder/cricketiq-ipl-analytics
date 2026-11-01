import sys, pandas as pd
src = sys.argv[1] if len(sys.argv) > 1 else "CricketIQ_IPL_2020_2025_Ready_For_PowerBI.xlsx"
d = pd.read_excel(src, sheet_name=["Matches","Deliveries","Batting_Stats","Bowling_Stats","Team_Performance","Venue_Analysis","Strategic_Insights"])
M, D, B, W, T, V, I = (d[k] for k in ["Matches","Deliveries","Batting_Stats","Bowling_Stats","Team_Performance","Venue_Analysis","Strategic_Insights"])

TEAM = {"Chennai Super Kings":("CSK","Chennai Super Kings"),"Delhi Capitals":("DC","Delhi Capitals"),"Gujarat Titans":("GT","Gujarat Titans"),
"Kings XI Punjab":("PBKS","Punjab Kings"),"Punjab Kings":("PBKS","Punjab Kings"),"Kolkata Knight Riders":("KKR","Kolkata Knight Riders"),
"Lucknow Super Giants":("LSG","Lucknow Super Giants"),"Mumbai Indians":("MI","Mumbai Indians"),"Rajasthan Royals":("RR","Rajasthan Royals"),
"Royal Challengers Bangalore":("RCB","Royal Challengers Bengaluru"),"Royal Challengers Bengaluru":("RCB","Royal Challengers Bengaluru"),
"Sunrisers Hyderabad":("SRH","Sunrisers Hyderabad")}
UAE = {"Dubai International Cricket Stadium","Sharjah Cricket Stadium","Sheikh Zayed Stadium","Zayed Cricket Stadium, Abu Dhabi"}
VEN = {"Zayed Cricket Stadium, Abu Dhabi":"Sheikh Zayed Stadium",
       "Maharaja Yadavindra Singh International Cricket Stadium, New Chandigarh":"Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur"}
PH = {"Powerplay":"PP","Middle Overs":"MO","Death Overs":"DO"}
CREDIT = ["caught","bowled","lbw","stumped","caught and bowled","hit wicket"]

M["Venue_C"] = M.Venue.replace(VEN); M["Country"] = M.Venue.map(lambda v: "UAE" if v in UAE else "India")
for c in ["Team1","Team2","Toss_Winner","Match_Winner"]: M[c+"_C"] = M[c].map(lambda x: TEAM[x][0] if isinstance(x,str) else None)
M[["Match_ID","Season","Match_Date","Venue_C","Country","Team1_C","Team2_C","Toss_Winner_C","Toss_Decision","Match_Winner_C","Win_Type","Win_Margin","Match_Result","Player_of_Match"]]\
 .rename(columns=lambda c: c.replace("_C","")).to_csv("data/matches.csv", index=False)

D = D.merge(M[["Match_ID","Country"]], on="Match_ID")
D["BT"] = D.Batting_Team.map(lambda x: TEAM[x][0]); D["WT"] = D.Bowling_Team.map(lambda x: TEAM[x][0])
D["Phase"] = D.Match_Phase.where(D.Innings <= 2, "Super Over")
R = D[D.Innings <= 2].copy()
R["rc"] = R.Total_Runs - R.Bye_Runs - R.Leg_Bye_Runs - R.Penalty_Runs
R["wk"] = ((R.Wicket_Flag == 1) & R.Wicket_Type.isin(CREDIT)).astype(int)

tb = D.groupby(["Season","Batter","BT"]).size().rename("n").reset_index().rename(columns={"Batter":"Player","BT":"Team"})
tw = D.groupby(["Season","Bowler","WT"]).size().rename("n").reset_index().rename(columns={"Bowler":"Player","WT":"Team"})
tt = pd.concat([tb,tw]).groupby(["Season","Player","Team"]).n.sum().reset_index().sort_values("n",ascending=False).drop_duplicates(["Season","Player"])[["Season","Player","Team"]]
ps = B.rename(columns={"Matches":"Bat_M","Innings":"Bat_Inn","Runs":"Bat_Runs","Balls_Faced":"Bat_Balls","Not_Outs":"Bat_NO","Dismissals":"Bat_Dis",
      "Fours":"Fours","Sixes":"Sixes","Highest_Score":"HS","Fifties":"F50","Hundreds":"H100"}).drop(columns=["Batting_Average","Strike_Rate"])
ps = ps[~((ps.Bat_Balls==0)&(ps.Bat_Inn==0))]
wb = W.rename(columns={"Matches":"Bowl_M","Legal_Balls":"Bowl_Balls","Runs_Conceded":"Bowl_Runs","Wickets":"Bowl_Wkts","Dot_Balls":"Dots","Maidens":"Maidens"})[["Season","Player","Bowl_M","Bowl_Balls","Bowl_Runs","Bowl_Wkts","Dots","Maidens"]]
ps = ps.merge(wb, on=["Season","Player"], how="outer")
bf = R[R.Wide_Runs==0].groupby(["Season","Batter","Phase"]).agg(r=("Batter_Runs","sum"), b=("Batter_Runs","size")).reset_index()
bf = bf.pivot(index=["Season","Batter"], columns="Phase", values=["r","b"]); bf.columns = [f"Bat_{PH[p]}_{'Runs' if a=='r' else 'Balls'}" for a,p in bf.columns]
bw = R.groupby(["Season","Bowler","Phase"]).agg(r=("rc","sum"), b=("Is_Legal_Delivery","sum"), w=("wk","sum")).reset_index()
bw = bw.pivot(index=["Season","Bowler"], columns="Phase", values=["r","b","w"]); bw.columns = [f"Bowl_{PH[p]}_{ {'r':'Runs','b':'Balls','w':'Wkts'}[a]}" for a,p in bw.columns]
bf.index.names = ["Season","Player"]; bw.index.names = ["Season","Player"]
ps = ps.merge(bf.reset_index(), on=["Season","Player"], how="left").merge(bw.reset_index(), on=["Season","Player"], how="left")
ct = pd.concat([D[["Season","Match_ID","Batter","Country"]].rename(columns={"Batter":"Player"}), D[["Season","Match_ID","Bowler","Country"]].rename(columns={"Bowler":"Player"})]).drop_duplicates()
ct = ct.groupby(["Season","Player","Country"]).size().unstack(fill_value=0).rename(columns=lambda c:f"Matches_{c}").reset_index()
ps = ps.merge(ct, on=["Season","Player"], how="left").merge(tt, on=["Season","Player"], how="left")
ps["Team"] = ps.Team.fillna("—")
ps.fillna(0, inplace=True)
ps.to_csv("data/player_season.csv", index=False)

a = R.groupby(["Season","BT","Phase"]).agg(Bat_Runs=("Total_Runs","sum"), Bat_Balls=("Is_Legal_Delivery","sum"), Wkts_Lost=("Wicket_Flag","sum"), Boundaries=("Is_Boundary","sum")).reset_index().rename(columns={"BT":"Team"})
b = R.groupby(["Season","WT","Phase"]).agg(Bowl_Runs=("Total_Runs","sum"), Bowl_Balls=("Is_Legal_Delivery","sum"), Wkts_Taken=("Wicket_Flag","sum")).reset_index().rename(columns={"WT":"Team"})
tp = a.merge(b, on=["Season","Team","Phase"], how="outer").fillna(0); tp["Phase"] = tp.Phase.map(PH); tp.to_csv("data/team_phase.csv", index=False)

ts = T.copy(); ts["Code"] = ts.Team.map(lambda x: TEAM[x][0]); ts["Franchise"] = ts.Team.map(lambda x: TEAM[x][1])
ts = ts[["Season","Code","Franchise","Matches","Wins","Losses","No_Results","Points","Total_Runs","Total_Wickets_Lost","Average_Score"]]; ts.to_csv("data/team_season.csv", index=False)

mu = R[R.Wide_Runs==0].copy()
mu["dis"] = ((mu.Wicket_Flag==1) & mu.Wicket_Type.isin(CREDIT) & (mu.Player_Dismissed==mu.Batter)).astype(int)
mu = mu.groupby(["Batter","Bowler"]).agg(Balls=("Batter_Runs","size"), Runs=("Batter_Runs","sum"), Dismissals=("dis","sum"), Dots=("Batter_Runs", lambda s:(s==0).sum()),
        Fours=("Is_Four","sum"), Sixes=("Is_Six","sum"), First=("Season","min"), Last=("Season","max")).reset_index()
mu = mu[mu.Balls >= 6]; mu.to_csv("data/matchups.csv", index=False)

v = V.copy(); v["Venue"] = v.Venue.replace(VEN); v.to_csv("data/venues.csv", index=False)
I.to_csv("data/insights.csv", index=False)
print({f: len(pd.read_csv(f"data/{f}.csv")) for f in ["matches","player_season","team_phase","team_season","matchups","venues","insights"]})
