import os, re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="CricketIQ", page_icon="🏏", layout="wide", initial_sidebar_state="expanded")

_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env):
    for _l in open(_env, encoding="utf-8"):
        if "=" in _l and not _l.strip().startswith("#"):
            _k, _v = _l.strip().split("=", 1)
            if _v.strip(): os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

TCOL = {"CSK": "#facc15", "DC": "#60a5fa", "GT": "#94a3b8", "PBKS": "#f87171", "KKR": "#a78bfa", "LSG": "#2dd4bf",
        "MI": "#38bdf8", "RR": "#f472b6", "RCB": "#fb7185", "SRH": "#fb923c", "—": "#64748b"}
TEAMS = {"CSK": "Chennai Super Kings", "DC": "Delhi Capitals", "GT": "Gujarat Titans", "KKR": "Kolkata Knight Riders", "LSG": "Lucknow Super Giants",
         "MI": "Mumbai Indians", "PBKS": "Punjab Kings", "RR": "Rajasthan Royals", "RCB": "Royal Challengers Bengaluru", "SRH": "Sunrisers Hyderabad"}
PHN = {"PP": "Powerplay", "MO": "Middle overs", "DO": "Death overs"}
st.markdown("""<style>
.block-container{padding-top:1.4rem;max-width:1400px}
.card{background:#121b2e;border:1px solid #25344f;border-radius:12px;padding:12px 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(125px,1fr));gap:10px;margin:8px 0 14px}
.stat{background:#18243d;border:1px solid #25344f;border-radius:10px;padding:10px 12px}
.stat .v{font-size:22px;font-weight:700;color:#e8eefc}.stat .l{font-size:11px;color:#8fa1c4;text-transform:uppercase;letter-spacing:.5px}
.hero{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.avatar{width:150px;height:190px;background:linear-gradient(180deg,#18243d,#121b2e);border:1px solid #25344f;border-radius:14px;display:flex;align-items:flex-end;justify-content:center;overflow:hidden}
.chip{display:inline-block;padding:1px 9px;border-radius:99px;font-size:11px;font-weight:700;color:#04101c;margin-right:4px}
.badge{display:inline-block;padding:2px 10px;border-radius:6px;font-size:11px;background:#18243d;border:1px solid #25344f;color:#8fa1c4;margin-right:4px}
.flag{display:inline-flex;align-items:center;gap:6px;background:#18243d;border:1px solid #25344f;border-radius:6px;padding:3px 8px;font-size:12px;margin:6px 6px 0 0}
.flag svg,.flag img{width:24px;height:16px;border-radius:2px}
.warn{color:#f59e0b;font-size:12px}
</style>""", unsafe_allow_html=True)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

@st.cache_data
def load():
    r = lambda n: pd.read_csv(os.path.join(DATA, n + ".csv"))
    return {k: r(k) for k in ["matches", "player_season", "team_phase", "team_season", "matchups", "venues", "insights"]}

D = load()
PS, TP, TS, MA, MU, VE, INS = (D[k] for k in ["player_season", "team_phase", "team_season", "matches", "matchups", "venues", "insights"])
SEASONS = sorted(PS.Season.unique())

@st.cache_data
def player_roles():
    g = PS.groupby("Player").agg(bb=("Bat_Balls", "sum"), wb=("Bowl_Balls", "sum"))
    return g.apply(lambda r: "All-rounder" if r.wb >= 60 and r.bb >= 100 else "Bowler" if r.wb >= 60 else "Batter", axis=1).to_dict()

ROLE = player_roles()

try:
    from player_countries import PLAYER_COUNTRY
except Exception:
    PLAYER_COUNTRY = {}

def chip(t): return f'<span class="chip" style="background:{TCOL.get(t, "#64748b")}">{t}</span>'
def cards(items): return '<div class="grid">' + "".join(f'<div class="stat"><div class="v">{v}</div><div class="l">{l}</div></div>' for l, v in items) + "</div>"
def f1(x, d=1): return "–" if x is None or pd.isna(x) else f"{x:,.{d}f}"
def fi(x): return "–" if x is None or pd.isna(x) else f"{int(x):,}"
def div(a, b): return a / b if b else float("nan")

def style(fig, h=320):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=h,
                      margin=dict(l=10, r=10, t=40, b=10), font=dict(size=12), legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(gridcolor="#25344f"); fig.update_yaxes(gridcolor="#25344f")
    return fig

FLAGS = {
    "India": '<svg viewBox="0 0 24 16"><rect width="24" height="5.4" fill="#FF9933"/><rect y="5.3" width="24" height="5.4" fill="#fff"/><rect y="10.6" width="24" height="5.4" fill="#138808"/><circle cx="12" cy="8" r="2" fill="none" stroke="#000080" stroke-width=".8"/></svg>',
    "UAE": '<svg viewBox="0 0 24 16"><rect width="24" height="5.4" fill="#00732F"/><rect y="5.3" width="24" height="5.4" fill="#fff"/><rect y="10.6" width="24" height="5.4" fill="#000"/><rect width="6.5" height="16" fill="#FF0000"/></svg>'}

def avatar(kind, col):
    skin, dark = "#e0b48a", "#0b1220"
    if kind == "bowler":
        return f'''<svg viewBox="0 0 150 190" width="150" height="190"><ellipse cx="75" cy="182" rx="40" ry="5" fill="#000" opacity=".25"/>
        <path d="M62 120 L50 178 L64 178 L76 130 L88 178 L102 178 L90 120Z" fill="#e5e7eb"/><path d="M52 62 Q75 50 98 62 L104 124 L46 124Z" fill="{col}"/>
        <path d="M98 66 L132 26" stroke="{skin}" stroke-width="12" stroke-linecap="round"/><circle cx="134" cy="22" r="8" fill="#b91c1c"/>
        <path d="M52 70 L28 100" stroke="{skin}" stroke-width="12" stroke-linecap="round"/><circle cx="75" cy="40" r="17" fill="{skin}"/><path d="M58 38 Q75 16 92 38 Q75 28 58 38Z" fill="{dark}"/></svg>'''
    return f'''<svg viewBox="0 0 150 190" width="150" height="190"><ellipse cx="75" cy="182" rx="40" ry="5" fill="#000" opacity=".25"/>
        <path d="M60 120 L52 178 L66 178 L76 130 L86 178 L100 178 L92 120Z" fill="#e5e7eb"/><path d="M54 62 Q75 52 96 62 L102 124 L48 124Z" fill="{col}"/>
        <path d="M96 70 L112 112" stroke="{skin}" stroke-width="12" stroke-linecap="round"/><path d="M112 112 L124 168" stroke="#c9a15a" stroke-width="11" stroke-linecap="round"/>
        <path d="M56 72 L100 108" stroke="{skin}" stroke-width="12" stroke-linecap="round"/><circle cx="75" cy="40" r="17" fill="{skin}"/>
        <path d="M57 40 Q75 12 93 40 L93 44 L57 44Z" fill="{col}" stroke="{dark}" stroke-width="1.5"/></svg>'''

BAT_SUM = ["Bat_M", "Bat_Inn", "Bat_Runs", "Bat_Balls", "Bat_NO", "Bat_Dis", "Fours", "Sixes", "F50", "H100"]
BOWL_SUM = ["Bowl_M", "Bowl_Balls", "Bowl_Runs", "Bowl_Wkts", "Dots", "Maidens"]
PHCOLS = [c for c in PS.columns if re.match(r"(Bat|Bowl)_(PP|MO|DO)_", c)]

def add_rates(df):
    df = df.copy()
    df["Bat_Avg"] = df.Bat_Runs / df.Bat_Dis.where(df.Bat_Dis > 0)
    df["Bat_SR"] = 100 * df.Bat_Runs / df.Bat_Balls.where(df.Bat_Balls > 0)
    df["Econ"] = 6 * df.Bowl_Runs / df.Bowl_Balls.where(df.Bowl_Balls > 0)
    df["Bowl_Avg"] = df.Bowl_Runs / df.Bowl_Wkts.where(df.Bowl_Wkts > 0)
    df["Bowl_SR"] = df.Bowl_Balls / df.Bowl_Wkts.where(df.Bowl_Wkts > 0)
    df["Dot_%"] = 100 * df.Dots / df.Bowl_Balls.where(df.Bowl_Balls > 0)
    return df

def players_agg(df):
    g = df.groupby("Player").agg({**{c: "sum" for c in BAT_SUM + BOWL_SUM + PHCOLS}, "HS": "max",
                                  "Matches_India": "sum", "Matches_UAE": "sum",
                                  "Team": lambda s: s.value_counts().index[0]}).reset_index()
    g["Role"] = g.Player.map(ROLE)
    return add_rates(g)

st.sidebar.markdown("## 🏏 Cricket**IQ**")
st.sidebar.caption("IPL 2020–2025 · Performance & Tactical Intelligence")
PAGE = st.sidebar.radio("Navigate", ["Overview", "Player Profile", "Team Intelligence", "Tactical Lab", "AI Analyst"], label_visibility="collapsed")
st.sidebar.divider()
s_lo, s_hi = st.sidebar.select_slider("Season range", options=SEASONS, value=(SEASONS[0], SEASONS[-1]))
TEAM_SEL = st.sidebar.selectbox("Team", ["All teams"] + list(TEAMS), format_func=lambda c: c if c == "All teams" else f"{c} · {TEAMS[c]}")
ROLE_SEL = st.sidebar.selectbox("Role", ["All roles", "Batter", "Bowler", "All-rounder"])
st.sidebar.divider()
st.sidebar.caption("Super Overs are excluded from phase splits. 2024 has 71 of 74 matches in the source. Ties/no-results have no recorded winner.")

in_range = lambda df: df[(df.Season >= s_lo) & (df.Season <= s_hi)]
PSf = in_range(PS)
if TEAM_SEL != "All teams": PSf = PSf[PSf.Team == TEAM_SEL]
PA = players_agg(PSf)
if ROLE_SEL != "All roles": PA = PA[PA.Role == ROLE_SEL]
MAf = in_range(MA)
TSf = in_range(TS); TPf = in_range(TP)
if TEAM_SEL != "All teams":
    TSf = TSf[TSf.Code == TEAM_SEL]; TPf = TPf[TPf.Team == TEAM_SEL]
RANGE = f"{s_lo}" if s_lo == s_hi else f"{s_lo}–{s_hi}"

def page_overview():
    st.title("Overview")
    st.caption(f"Seasons {RANGE} · {TEAMS.get(TEAM_SEL, 'all teams')}")
    mm = MAf if TEAM_SEL == "All teams" else MAf[(MAf.Team1 == TEAM_SEL) | (MAf.Team2 == TEAM_SEL)]
    tt = TSf.groupby("Code")[["Matches", "Wins", "Losses", "No_Results", "Points", "Total_Runs"]].sum()
    c = st.columns(5)
    c[0].metric("Matches", fi(len(mm)))
    c[1].metric("Runs (batters, regular)", fi(PSf.Bat_Runs.sum()))
    c[2].metric("Sixes", fi(PSf.Sixes.sum()))
    c[3].metric("Fours", fi(PSf.Fours.sum()))
    c[4].metric("Bowler wickets", fi(PSf.Bowl_Wkts.sum()))
    a, b = st.columns([3, 2])
    with a:
        st.subheader("Team standings")
        t = tt.reset_index().sort_values(["Points", "Wins"], ascending=False)
        t["Win %"] = 100 * t.Wins / t.Matches; t["Team"] = t.Code.map(TEAMS); t.rename(columns={"No_Results": "NR/Tie"}, inplace=True)
        st.dataframe(t[["Team", "Matches", "Wins", "Losses", "NR/Tie", "Points", "Win %"]], hide_index=True, width="stretch",
                     column_config={"Win %": st.column_config.ProgressColumn("Win %", min_value=0, max_value=100, format="%.1f")})
        st.caption("Ties count under NR/Tie because the source has no Super Over winner.")
    with b:
        st.subheader("Scoring trend")
        s = in_range(PS).groupby("Season").agg(Sixes=("Sixes", "sum"), Runs=("Bat_Runs", "sum")).reset_index()
        s["Matches"] = s.Season.map(MA.groupby("Season").size())
        s["Runs/match"] = s.Runs / s.Matches; s["Sixes/match"] = s.Sixes / s.Matches
        fig = go.Figure()
        fig.add_bar(x=s.Season, y=s["Runs/match"], name="Runs/match", marker_color="#38bdf8")
        fig.add_scatter(x=s.Season, y=s["Sixes/match"], name="Sixes/match", yaxis="y2", mode="lines+markers", line=dict(color="#f59e0b"))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False), xaxis=dict(type="category"))
        st.plotly_chart(style(fig), width="stretch")
    st.subheader("Phase run rate by season")
    p = TPf.groupby(["Season", "Phase"])[["Bat_Runs", "Bat_Balls"]].sum().reset_index(); p["Run rate"] = 6 * p.Bat_Runs / p.Bat_Balls
    p["Phase"] = p.Phase.map(PHN)
    st.plotly_chart(style(px.line(p, x="Season", y="Run rate", color="Phase", markers=True, color_discrete_sequence=["#38bdf8", "#34d399", "#f59e0b"])), width="stretch")
    a, b = st.columns(2)
    with a:
        st.subheader("Top run-scorers")
        x = PA[PA.Bat_Balls > 0].nlargest(10, "Bat_Runs")[["Player", "Team", "Bat_Runs", "Bat_Avg", "Bat_SR"]]
        st.dataframe(x.rename(columns={"Bat_Runs": "Runs", "Bat_Avg": "Avg", "Bat_SR": "SR"}), hide_index=True, width="stretch",
                     column_config={"Avg": st.column_config.NumberColumn(format="%.1f"), "SR": st.column_config.NumberColumn(format="%.1f")})
    with b:
        st.subheader("Top wicket-takers")
        x = PA[PA.Bowl_Balls > 0].nlargest(10, "Bowl_Wkts")[["Player", "Team", "Bowl_Wkts", "Econ", "Bowl_Avg"]]
        st.dataframe(x.rename(columns={"Bowl_Wkts": "Wkts", "Bowl_Avg": "Avg"}), hide_index=True, width="stretch",
                     column_config={"Econ": st.column_config.NumberColumn(format="%.2f"), "Avg": st.column_config.NumberColumn(format="%.1f")})

def page_player():
    st.title("Player Profile")
    if PA.empty: st.warning("No players match these filters."); return
    PA2 = PA.sort_values("Bat_Runs", ascending=False)
    c1, c2 = st.columns([2, 1])
    name = c1.selectbox("Player (type to search)", PA2.Player.tolist(), format_func=lambda p: f"{p} · {ROLE[p]}")
    r = PA[PA.Player == name].iloc[0]
    rows = PSf[PSf.Player == name].sort_values("Season")
    teams = rows.Team.value_counts().index.tolist()
    both = r.Bat_Balls > 0 and r.Bowl_Balls > 0
    default = 1 if ROLE[name] == "Bowler" else 0
    view = c2.radio("View", ["Batting", "Bowling"], index=default, horizontal=True) if both else ("Bowling" if r.Bowl_Balls > 0 and ROLE[name] == "Bowler" or r.Bat_Balls == 0 else "Batting")
    col = TCOL.get(teams[0], "#64748b")
    flags = "".join(f'<span class="flag">{FLAGS[c]}{c} · {int(r["Matches_" + c])} matches</span>' for c in ["India", "UAE"] if r["Matches_" + c] > 0)
    nat = PLAYER_COUNTRY.get(name)
    natl = f'<span class="flag"><img src="https://flagcdn.com/w40/{nat.lower()}.png">Nationality: {nat.upper()}</span>' if nat else ""
    seasons = rows.Season.tolist()
    st.markdown(f'''<div class="card"><div class="hero"><div class="avatar">{avatar("bowler" if view == "Bowling" else "batter", col)}</div><div>
      <h2 style="margin:0 0 6px">{name}</h2>{"".join(chip(t) for t in teams)}<span class="badge">{ROLE[name]}</span><span class="badge">{seasons[0]}{"–" + str(seasons[-1]) if len(seasons) > 1 else ""} · {len(seasons)} season(s)</span>
      <div>{natl}{flags}</div><div class="warn" style="color:#8fa1c4;margin-top:6px">Flags show the country of the venues played at (from match data), not nationality.</div></div></div></div>''', unsafe_allow_html=True)
    if view == "Batting":
        if r.Bat_Balls == 0: st.info("No batting record in this selection."); return
        st.markdown(cards([("Matches", fi(r.Bat_M)), ("Innings", fi(r.Bat_Inn)), ("Runs", fi(r.Bat_Runs)), ("Average", f1(r.Bat_Avg)), ("Strike rate", f1(r.Bat_SR)),
                           ("Highest", fi(r.HS)), ("50s / 100s", f"{int(r.F50)} / {int(r.H100)}"), ("Fours", fi(r.Fours)), ("Sixes", fi(r.Sixes)),
                           ("Balls faced", fi(r.Bat_Balls)), ("Not outs", fi(r.Bat_NO)), ("Dismissals", fi(r.Bat_Dis))]), unsafe_allow_html=True)
        if r.Bat_Balls < 60: st.markdown(f'<div class="warn">⚠ Small sample ({int(r.Bat_Balls)} balls) – treat rates with caution.</div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        s = add_rates(rows)
        with a:
            fig = go.Figure(); fig.add_bar(x=s.Season.astype(str), y=s.Bat_Runs, name="Runs", marker_color="#38bdf8")
            fig.add_scatter(x=s.Season.astype(str), y=s.Bat_SR, name="Strike rate", yaxis="y2", mode="lines+markers", line=dict(color="#f59e0b"))
            fig.update_layout(title="Runs & strike rate by season", yaxis2=dict(overlaying="y", side="right", showgrid=False))
            st.plotly_chart(style(fig), width="stretch")
        with b:
            ph = pd.DataFrame([{"Phase": PHN[k], "SR": div(100 * r[f"Bat_{k}_Runs"], r[f"Bat_{k}_Balls"]), "Balls": r[f"Bat_{k}_Balls"]} for k in PHN])
            fig = px.bar(ph, x="Phase", y="SR", text=ph.SR.round(1), color_discrete_sequence=["#34d399"], hover_data=["Balls"]); fig.update_layout(title="Strike rate by phase")
            st.plotly_chart(style(fig), width="stretch")
    else:
        if r.Bowl_Balls == 0: st.info("No bowling record in this selection."); return
        st.markdown(cards([("Matches", fi(r.Bowl_M)), ("Wickets", fi(r.Bowl_Wkts)), ("Economy", f1(r.Econ, 2)), ("Average", f1(r.Bowl_Avg)), ("Strike rate", f1(r.Bowl_SR)),
                           ("Overs", f"{int(r.Bowl_Balls) // 6}.{int(r.Bowl_Balls) % 6}"), ("Runs conceded", fi(r.Bowl_Runs)), ("Dot balls", fi(r.Dots)),
                           ("Dot ball %", f1(r["Dot_%"]) + "%"), ("Maidens", fi(r.Maidens))]), unsafe_allow_html=True)
        if r.Bowl_Balls < 60: st.markdown(f'<div class="warn">⚠ Small sample ({int(r.Bowl_Balls)} balls) – treat rates with caution.</div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        s = add_rates(rows)
        with a:
            fig = go.Figure(); fig.add_bar(x=s.Season.astype(str), y=s.Bowl_Wkts, name="Wickets", marker_color="#f59e0b")
            fig.add_scatter(x=s.Season.astype(str), y=s.Econ, name="Economy", yaxis="y2", mode="lines+markers", line=dict(color="#f87171"))
            fig.update_layout(title="Wickets & economy by season", yaxis2=dict(overlaying="y", side="right", showgrid=False))
            st.plotly_chart(style(fig), width="stretch")
        with b:
            ph = pd.DataFrame([{"Phase": PHN[k], "Economy": div(6 * r[f"Bowl_{k}_Runs"], r[f"Bowl_{k}_Balls"]), "Wickets": r[f"Bowl_{k}_Wkts"]} for k in PHN])
            fig = px.bar(ph, x="Phase", y="Economy", text=ph.Economy.round(2), color_discrete_sequence=["#f87171"], hover_data=["Wickets"]); fig.update_layout(title="Economy by phase")
            st.plotly_chart(style(fig), width="stretch")
    with st.expander("Season-by-season table"):
        s = add_rates(rows)[["Season", "Team", "Bat_M", "Bat_Runs", "Bat_Avg", "Bat_SR", "Bowl_M", "Bowl_Wkts", "Econ"]]
        st.dataframe(s, hide_index=True, width="stretch")

def page_team():
    st.title("Team Intelligence")
    t = st.selectbox("Team", list(TEAMS), index=list(TEAMS).index(TEAM_SEL) if TEAM_SEL != "All teams" else 0, format_func=lambda c: f"{c} · {TEAMS[c]}")
    ts = in_range(TS)[in_range(TS).Code == t]; tp = in_range(TP)[in_range(TP).Team == t]
    if ts.empty: st.warning("This franchise has no matches in the selected seasons."); return
    w, m = ts.Wins.sum(), ts.Matches.sum()
    st.markdown(cards([("Matches", fi(m)), ("Wins", fi(w)), ("Losses", fi(ts.Losses.sum())), ("NR / Tie", fi(ts.No_Results.sum())), ("Win %", f1(100 * w / m)), ("Points", fi(ts.Points.sum())),
                       ("Avg score", f1(ts.Total_Runs.sum() / max(1, ts.Matches.sum() - ts.No_Results.sum())))]), unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        s = ts.assign(WinPct=100 * ts.Wins / ts.Matches)
        fig = px.bar(s, x=s.Season.astype(str), y="WinPct", text=s.WinPct.round(0), color_discrete_sequence=[TCOL[t]]); fig.update_layout(title="Win % by season", xaxis_title="Season", yaxis_title="Win %")
        st.plotly_chart(style(fig), width="stretch")
    with b:
        g = tp.groupby("Phase")[["Bat_Runs", "Bat_Balls", "Bowl_Runs", "Bowl_Balls", "Wkts_Lost", "Wkts_Taken"]].sum().reindex(["PP", "MO", "DO"]).reset_index()
        g["Batting run rate"] = 6 * g.Bat_Runs / g.Bat_Balls; g["Bowling economy"] = 6 * g.Bowl_Runs / g.Bowl_Balls; g["Phase"] = g.Phase.map(PHN)
        fig = go.Figure(); fig.add_bar(x=g.Phase, y=g["Batting run rate"], name="Batting run rate", marker_color="#38bdf8"); fig.add_bar(x=g.Phase, y=g["Bowling economy"], name="Bowling economy (conceded)", marker_color="#f87171")
        fig.update_layout(title="Phase balance (higher batting / lower economy = better)", barmode="group"); st.plotly_chart(style(fig), width="stretch")
    st.subheader("Squad contributors")
    sq = players_agg(in_range(PS)[in_range(PS).Team == t])
    a, b = st.columns(2)
    a.dataframe(sq[sq.Bat_Balls > 0].nlargest(10, "Bat_Runs")[["Player", "Bat_Runs", "Bat_Avg", "Bat_SR"]].rename(columns={"Bat_Runs": "Runs", "Bat_Avg": "Avg", "Bat_SR": "SR"}), hide_index=True, width="stretch",
                column_config={"Avg": st.column_config.NumberColumn(format="%.1f"), "SR": st.column_config.NumberColumn(format="%.1f")})
    b.dataframe(sq[sq.Bowl_Balls > 0].nlargest(10, "Bowl_Wkts")[["Player", "Bowl_Wkts", "Econ", "Bowl_Avg"]].rename(columns={"Bowl_Wkts": "Wkts", "Bowl_Avg": "Avg"}), hide_index=True, width="stretch",
                column_config={"Econ": st.column_config.NumberColumn(format="%.2f"), "Avg": st.column_config.NumberColumn(format="%.1f")})

def page_tactical():
    st.title("Tactical Lab")
    t1, t2, t3, t4 = st.tabs(["Batter vs Bowler", "Venues", "Toss & chasing", "Phase edge"])
    with t1:
        st.caption("Matchups are aggregated over all 2020–2025 seasons (not affected by the season slider). Wides excluded from balls faced; dismissals are bowler-credited.")
        mode = st.radio("Look up", ["A batter against all bowlers", "A bowler against all batters", "Head to head"], horizontal=True)
        mn = st.slider("Minimum balls", 6, 60, 18)
        d = MU[MU.Balls >= mn].copy(); d["SR"] = 100 * d.Runs / d.Balls; d["Dot %"] = 100 * d.Dots / d.Balls; d["Balls/dismissal"] = d.Balls / d.Dismissals.where(d.Dismissals > 0)
        if mode.startswith("A batter"):
            b = st.selectbox("Batter", sorted(MU.Batter.unique())); x = d[d.Batter == b].sort_values("Balls", ascending=False).head(25)
            xx = x.rename(columns={"Bowler": "Opponent"})
        elif mode.startswith("A bowler"):
            b = st.selectbox("Bowler", sorted(MU.Bowler.unique())); x = d[d.Bowler == b].sort_values("Balls", ascending=False).head(25)
            xx = x.rename(columns={"Batter": "Opponent"})
        else:
            c1, c2 = st.columns(2); bt = c1.selectbox("Batter", sorted(MU.Batter.unique())); bo = c2.selectbox("Bowler", sorted(MU.Bowler.unique()))
            h = MU[(MU.Batter == bt) & (MU.Bowler == bo)]
            if h.empty: st.info("These two haven't faced each other for 6+ balls in the data.")
            else:
                h = h.iloc[0]; st.markdown(cards([("Balls", int(h.Balls)), ("Runs", int(h.Runs)), ("Dismissals", int(h.Dismissals)), ("Strike rate", f1(100 * h.Runs / h.Balls)), ("Dot %", f1(100 * h.Dots / h.Balls)), ("4s / 6s", f"{int(h.Fours)} / {int(h.Sixes)}")]), unsafe_allow_html=True)
                if h.Balls < 30: st.markdown('<div class="warn">⚠ Small sample – exploratory only.</div>', unsafe_allow_html=True)
            xx = pd.DataFrame()
        if not xx.empty:
            fig = px.scatter(xx, x="Balls", y="SR", size="Runs", color="Dismissals", hover_name="Opponent", color_continuous_scale="Turbo"); fig.update_layout(title="Strike rate vs balls faced (bubble = runs, colour = dismissals)")
            st.plotly_chart(style(fig, 360), width="stretch")
            st.dataframe(xx[["Opponent", "Balls", "Runs", "Dismissals", "SR", "Dot %", "Fours", "Sixes"]], hide_index=True, width="stretch",
                         column_config={"SR": st.column_config.NumberColumn(format="%.1f"), "Dot %": st.column_config.NumberColumn(format="%.1f")})
            st.markdown('<div class="warn">Small samples (under ~30 balls) are exploratory, not statistically significant.</div>', unsafe_allow_html=True)
    with t2:
        v = in_range(VE).groupby("Venue").apply(lambda g: pd.Series({"Matches": g.Matches.sum(), "Avg 1st inns": (g.Average_First_Innings_Score * g.Matches).sum() / g.Matches.sum(),
              "Avg 2nd inns": (g.Average_Second_Innings_Score * g.Matches).sum() / g.Matches.sum(), "Bat-first wins": g.Batting_First_Wins.sum(), "Chase wins": g.Batting_Second_Wins.sum(), "Highest": g.Highest_Team_Total.max()}), include_groups=False).reset_index()
        mm = st.slider("Minimum matches at venue", 1, 30, 8); v = v[v.Matches >= mm]
        v["Bat-first win %"] = 100 * v["Bat-first wins"] / (v["Bat-first wins"] + v["Chase wins"]); v = v.sort_values("Avg 1st inns", ascending=False)
        fig = px.bar(v, x="Avg 1st inns", y="Venue", orientation="h", color="Bat-first win %", color_continuous_scale="RdYlGn", range_color=[30, 70]); fig.update_layout(title="Average 1st-innings score (colour = bat-first win %)", yaxis=dict(autorange="reversed"))
        st.plotly_chart(style(fig, max(320, 28 * len(v))), width="stretch")
        st.dataframe(v, hide_index=True, width="stretch", column_config={c: st.column_config.NumberColumn(format="%.1f") for c in ["Avg 1st inns", "Avg 2nd inns", "Bat-first win %"]})
    with t3:
        m = MAf.dropna(subset=["Match_Winner"]).copy(); m["Toss won → match won"] = m.Toss_Winner == m.Match_Winner
        a, b = st.columns(2)
        a.metric("Toss winner also won match", f"{100 * m['Toss won → match won'].mean():.1f}%", help=f"{len(m)} matches with a recorded winner")
        d = m.groupby("Toss_Decision")["Toss won → match won"].agg(["mean", "size"]).reset_index(); d["mean"] *= 100
        fig = px.bar(d, x="Toss_Decision", y="mean", text=d["mean"].round(1), color_discrete_sequence=["#38bdf8"], hover_data=["size"]); fig.update_layout(title="Win % of toss winner by decision", yaxis_title="%", xaxis_title="Decision")
        b.plotly_chart(style(fig), width="stretch")
        w = m.assign(Chase=m.Win_Type == "Wickets").groupby("Season").Chase.mean().mul(100).reset_index()
        st.plotly_chart(style(px.line(w, x="Season", y="Chase", markers=True, title="Chasing-side win % by season")), width="stretch")
        st.caption("Matches without a recorded winner (ties, no-results) are excluded.")
    with t4:
        g = TPf.groupby(["Team", "Phase"])[["Bat_Runs", "Bat_Balls", "Bowl_Runs", "Bowl_Balls"]].sum().reset_index()
        g["Net run-rate edge"] = 6 * g.Bat_Runs / g.Bat_Balls - 6 * g.Bowl_Runs / g.Bowl_Balls; g["Phase"] = g.Phase.map(PHN)
        pv = g.pivot(index="Team", columns="Phase", values="Net run-rate edge")[["Powerplay", "Middle overs", "Death overs"]]
        fig = px.imshow(pv.round(2), text_auto=True, color_continuous_scale="RdYlGn", color_continuous_midpoint=0, aspect="auto"); fig.update_layout(title="Batting run rate minus bowling economy, by phase (positive = edge)")
        st.plotly_chart(style(fig, 420), width="stretch")
    ins = INS
    with st.expander("Strategic insights from the workbook"):
        st.dataframe(ins[["Category", "Player_or_Team", "Season", "Observation", "Supporting_Metric", "Sample_Size", "Confidence_Level", "Strategic_Recommendation"]], hide_index=True, width="stretch")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_Q = int(os.getenv("MAX_QUESTIONS_PER_SESSION", "10"))

def build_context(question):
    q = question.lower(); parts = []
    parts.append(f"Scope: seasons {RANGE}; team filter: {TEAMS.get(TEAM_SEL, 'all')}. Data: IPL 2020-2025 (Cricsheet). 2024 has 71/74 matches. Ties/no-results have no recorded winner. Super Overs excluded from phase splits.")
    t = TSf.groupby("Code")[["Matches", "Wins", "Losses", "No_Results", "Points"]].sum().reset_index().sort_values("Points", ascending=False)
    parts.append("TEAM STANDINGS\n" + t.to_csv(index=False))
    bt = PA[PA.Bat_Balls > 0].nlargest(15, "Bat_Runs")[["Player", "Team", "Bat_Runs", "Bat_Avg", "Bat_SR", "Sixes"]].round(1)
    bw = PA[PA.Bowl_Balls > 0].nlargest(15, "Bowl_Wkts")[["Player", "Team", "Bowl_Wkts", "Econ", "Bowl_Avg"]].round(2)
    parts.append("TOP BATTERS\n" + bt.to_csv(index=False) + "\nTOP BOWLERS\n" + bw.to_csv(index=False))
    names = [p for p in PS.Player.unique() if any(tok.lower() in q for tok in p.split()[1:] if len(tok) > 3) or p.lower() in q]
    for p in names[:3]:
        r = add_rates(in_range(PS)[in_range(PS).Player == p])[["Season", "Team", "Bat_Runs", "Bat_Avg", "Bat_SR", "Bat_PP_Runs", "Bat_PP_Balls", "Bat_DO_Runs", "Bat_DO_Balls", "Bowl_Wkts", "Econ"]].round(1)
        parts.append(f"PLAYER {p} (by season)\n" + r.to_csv(index=False))
    if len(names) >= 2:
        h = MU[MU.Batter.isin(names) & MU.Bowler.isin(names)]
        if not h.empty: parts.append("HEAD-TO-HEAD (all seasons)\n" + h[["Batter", "Bowler", "Balls", "Runs", "Dismissals"]].to_csv(index=False))
    for c, n in TEAMS.items():
        if c.lower() in re.findall(r"\b\w+\b", q) or n.lower() in q:
            g = TPf[TPf.Team == c].groupby("Phase")[["Bat_Runs", "Bat_Balls", "Bowl_Runs", "Bowl_Balls", "Wkts_Lost", "Wkts_Taken"]].sum().reset_index()
            parts.append(f"TEAM PHASES {c}\n" + g.to_csv(index=False))
    parts.append("WORKBOOK INSIGHTS\n" + INS[["Category", "Player_or_Team", "Season", "Observation", "Sample_Size", "Confidence_Level"]].to_csv(index=False))
    return "\n\n".join(parts)[:14000]

SYSTEM = ("You are CricketIQ, an IPL data analyst. Answer ONLY from the DATA block provided. Quote the numbers you use. If the data does not contain the answer "
          "(e.g. nationality, injuries, pitch reports, current form, future matches), say so plainly instead of guessing. Flag small samples (<60 balls batting or bowling, <30 balls matchups). "
          "Never invent statistics, players or facts. Be concise: short paragraphs or bullets, then a one-line recommendation if the question is tactical.")

PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
NOT_CHAT = ("whisper", "orpheus", "guard", "safeguard", "tts", "embed")

@st.cache_data(ttl=1800, show_spinner=False)
def available_models(key):
    r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    if r.status_code != 200: return []
    return [m["id"] for m in r.json().get("data", []) if not any(x in m["id"].lower() for x in NOT_CHAT)]

def choose_model(key, wanted):
    ids = available_models(key)
    if not ids or wanted in ids: return wanted
    for m in PREFERRED:
        if m in ids: return m
    return ids[0]

def ask_groq(key, model, question, history):
    ctx = build_context(question)
    msgs = [{"role": "system", "content": SYSTEM + "\n\nDATA:\n" + ctx}] + history[-6:] + [{"role": "user", "content": question}]
    model = choose_model(key, model)
    r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, json={"model": model, "messages": msgs, "temperature": 0.2, "max_tokens": 900}, timeout=60)
    if r.status_code == 404:
        for m in [x for x in available_models(key) if x != model][:3]:
            r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, json={"model": m, "messages": msgs, "temperature": 0.2, "max_tokens": 900}, timeout=60)
            if r.status_code == 200: break
    if r.status_code != 200: raise RuntimeError(f"Groq API error {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]

def page_ai():
    st.title("AI Analyst")
    st.caption("Ask questions in plain English. The model only sees summary tables from your filtered data – it does not browse the web and can't know anything outside this dataset.")
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        try: key = st.secrets["GROQ_API_KEY"]
        except Exception: key = ""
    saved = bool(key)
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not saved:
        with st.expander("Groq settings", expanded=True):
            key = st.text_input("Groq API key", type="password", help="Better: save it in .env or Streamlit Secrets (see README).")
            model = st.text_input("Model", value=model, help="Any chat model available on your Groq account.")
    else:
        st.caption("🔒 Groq key loaded from secure settings (hidden).")
    ex = ["Who are the best death-over batters in the selected seasons?", "Compare Bumrah and Chahal – who is better in the powerplay?", "Which team has the biggest edge in the middle overs?", "Should a captain bat or field first, based on the toss data?"]
    cols = st.columns(len(ex)); pick = None
    for c, e in zip(cols, ex):
        if c.button(e, width="stretch"): pick = e
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])
    q = st.chat_input("Ask about players, teams, phases, matchups…") or pick
    if q:
        st.chat_message("user").write(q)
        if not key:
            st.chat_message("assistant").warning("Add your Groq API key in the settings above (or set GROQ_API_KEY) to get AI answers. Everything else in the app works without it.")
        elif st.session_state.get("n_q", 0) >= MAX_Q:
            st.chat_message("assistant").warning(f"Demo limit reached ({MAX_Q} questions per visit). Refresh the page to start a new session.")
        elif len(q) > 400:
            st.chat_message("assistant").warning("Please keep the question under 400 characters.")
        else:
            st.session_state.n_q = st.session_state.get("n_q", 0) + 1
            with st.chat_message("assistant"), st.spinner("Analysing…"):
                try:
                    ans = ask_groq(key, model, q, st.session_state.chat); st.write(ans)
                    st.session_state.chat += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]
                except Exception as e:
                    st.error(str(e))
    with st.expander("What the model is shown for your last question type (preview)"):
        st.code(build_context(q or "overview")[:3000])
    if st.button("Clear chat"): st.session_state.chat = []; st.rerun()

{"Overview": page_overview, "Player Profile": page_player, "Team Intelligence": page_team, "Tactical Lab": page_tactical, "AI Analyst": page_ai}[PAGE]()
