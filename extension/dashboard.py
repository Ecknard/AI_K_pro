"""
extension/dashboard.py — Extension D v2.0 : Dashboard de supervision temps réel
TP1 — Intelligence Artificielle & Cybersécurité

CORRECTIONS v2.0 :
    ✅ StreamlitDuplicateElementId — key= unique sur chaque st.plotly_chart
    ✅ Auto-refresh non-bloquant via compteur + st.rerun()
    ✅ Cache TTL isolé par session
    ✅ Gestion robuste des données manquantes / vides
    ✅ Nouveau design : SOC terminal / matrix aesthetic
    ✅ 6 vues dont Threat Intelligence (nouveau)
    ✅ 5 KPI cards avec threat score calculé dynamiquement
    ✅ Highlight des données sensibles dans le log terminal
    ✅ Countdown refresh visible en bas à droite

Lancement : streamlit run extension/dashboard.py
URL         : http://localhost:8501
"""

import collections
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Chemins
# ─────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# Page config — PREMIER appel st.*
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Keylogger · SOC Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Terminal / SOC aesthetic
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    background-color: #060a0f !important;
    color: #a0b4c0;
    font-family: 'Inter', sans-serif;
}
.main .block-container { padding: 1.2rem 1.8rem 2rem; max-width: 1500px; }

/* Grid background */
.stApp::before {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(0,255,136,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,.025) 1px, transparent 1px);
    background-size: 44px 44px;
}

/* ── HEADER ── */
.soc-header {
    background: linear-gradient(135deg, #060f1a 0%, #0a1e32 60%, #060f1a 100%);
    border: 1px solid #0c3050;
    border-top: 2px solid #00ff88;
    border-radius: 10px;
    padding: 22px 32px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    overflow: hidden;
}
.soc-header::after {
    content: ''; position: absolute; right:-50px; top:-50px;
    width:180px; height:180px; border-radius:50%;
    background: radial-gradient(circle, rgba(0,255,136,.05) 0%, transparent 70%);
}
.soc-header h1 {
    font-family: 'Orbitron', monospace; font-size: 1.35em; font-weight: 900;
    color: #ddeef4; margin: 0 0 5px 0; letter-spacing: .05em;
}
.soc-header p {
    font-family: 'Share Tech Mono', monospace; font-size: .72em; color: #3a6040; margin: 0;
}
.status-label { font-family:'Share Tech Mono',monospace; font-size:.65em; color:#2a4a30; letter-spacing:.12em; }
.status-val   { font-family:'Orbitron',monospace; font-size:1.05em; font-weight:900; letter-spacing:.15em; }
.s-nominal  { color:#00ff88; text-shadow: 0 0 10px rgba(0,255,136,.4); }
.s-elevated { color:#ffaa00; text-shadow: 0 0 10px rgba(255,170,0,.4); }
.s-critical { color:#ff3366; text-shadow: 0 0 10px rgba(255,51,102,.4);
              animation: flicker .7s ease-in-out infinite alternate; }
@keyframes flicker { from{opacity:1} to{opacity:.65} }

/* ── SCAN BAR ── */
.scan-bar {
    background: #080e16; border: 1px solid #0c2a3e; border-radius: 6px;
    padding: 8px 16px; margin-bottom: 16px;
    display: flex; justify-content: space-between; align-items: center;
    font-family: 'Share Tech Mono', monospace; font-size: .7em; color: #2a4a36;
}
.live-dot::before { content: '◉ '; color: #00ff88;
    animation: blink 1.4s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.2} }

/* ── KPI GRID ── */
.kpi-row { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:18px; }
.kpi-card {
    background: #070e17; border: 1px solid #0c2230; border-radius: 8px;
    padding: 16px 18px; position: relative; overflow: hidden;
    transition: all .2s ease;
}
.kpi-card:hover { border-color: #00ff88; box-shadow: 0 0 18px rgba(0,255,136,.07); transform: translateY(-1px); }
.kpi-card .top-bar { position:absolute; top:0; left:0; right:0; height:2px; }
.kpi-card .ico     { position:absolute; right:13px; top:13px; font-size:1.3em; opacity:.1; }
.kpi-card .val     {
    font-family:'Orbitron',monospace; font-size:1.85em; font-weight:900; line-height:1; margin-bottom:5px;
}
.kpi-card .lbl     {
    font-family:'Share Tech Mono',monospace; font-size:.65em; color:#2a4a52;
    text-transform:uppercase; letter-spacing:.1em; margin-bottom:6px;
}
.kpi-card .sub     { font-family:'Share Tech Mono',monospace; font-size:.68em; color:#1e3a42; }
.kpi-spark { height:24px; margin-top:8px; border-radius:3px;
    background: repeating-linear-gradient(90deg,transparent 0,transparent 4px,rgba(0,255,136,.1) 4px,rgba(0,255,136,.1) 5px);
    animation: spark 4s linear infinite; }
@keyframes spark { from{background-position-x:0} to{background-position-x:50px} }

.c-green  { color:#00ff88; } .b-green  { background:linear-gradient(90deg,#00ff88,#00bb66); }
.c-blue   { color:#00aaff; } .b-blue   { background:linear-gradient(90deg,#00aaff,#0077cc); }
.c-orange { color:#ffaa00; } .b-orange { background:linear-gradient(90deg,#ffaa00,#cc7700); }
.c-red    { color:#ff3366; } .b-red    { background:linear-gradient(90deg,#ff3366,#cc1144); }
.c-purple { color:#bb00ff; } .b-purple { background:linear-gradient(90deg,#bb00ff,#8800cc); }

/* ── SECTION HEADERS ── */
.sec-hdr {
    font-family:'Orbitron',monospace; font-size:.68em; font-weight:700;
    color:#1e5040; letter-spacing:.18em; text-transform:uppercase;
    border-left:2px solid #00ff88; padding-left:10px; margin-bottom:12px;
}

/* ── PANEL ── */
.panel { background:#070e17; border:1px solid #0c2230; border-radius:8px; padding:14px; margin-bottom:12px; }

/* ── LOG TERMINAL ── */
.log-term {
    background:#030608; border:1px solid #090f18; border-top:2px solid #0c3050;
    border-radius:8px; padding:14px; height:255px; overflow-y:auto;
    font-family:'Share Tech Mono',monospace; font-size:.76em; line-height:1.8;
}
.log-term::before {
    content:'> TERMINAL — LIVE LOG STREAM'; display:block;
    color:#0e2820; font-size:.85em; border-bottom:1px solid #090f18;
    padding-bottom:7px; margin-bottom:7px; letter-spacing:.1em;
}
.lt-ts   { color:#183840; }
.lt-text { color:#6aa090; }
.lt-sep  { color:#0a1818; }
.lt-flag { color:#ff3366; }
.lt-empty{ color:#132020; font-style:italic; }

/* ── ALERT ITEMS ── */
.alert-item {
    background:#07111a; border:1px solid #0e2030; border-left:3px solid;
    border-radius:6px; padding:9px 13px; margin-bottom:7px;
    display:flex; justify-content:space-between; align-items:center;
    font-family:'Share Tech Mono',monospace; font-size:.74em;
    transition: background .15s;
}
.alert-item:hover { background:#0a1825; }
.alert-item.crit  { border-left-color:#ff3366; }
.alert-item.warn  { border-left-color:#ffaa00; }
.a-score { font-weight:700; }
.a-ts    { color:#1e3848; font-size:.9em; }

/* ── DETECTION CHIPS ── */
.det-chip {
    display:inline-flex; align-items:center;
    padding:3px 9px; border-radius:4px; border:1px solid;
    font-family:'Share Tech Mono',monospace; font-size:.69em; font-weight:700;
    letter-spacing:.04em; margin-right:4px; margin-bottom:4px;
}
.chip-email { background:rgba(0,170,255,.07); color:#00aaff; border-color:rgba(0,170,255,.25); }
.chip-cb    { background:rgba(255,51,102,.07); color:#ff3366; border-color:rgba(255,51,102,.25); }
.chip-tel   { background:rgba(255,170,0,.07);  color:#ffaa00; border-color:rgba(255,170,0,.25); }
.chip-secu  { background:rgba(187,0,255,.07);  color:#bb00ff; border-color:rgba(187,0,255,.25); }
.chip-pw    { background:rgba(255,100,0,.07);  color:#ff6400; border-color:rgba(255,100,0,.25); }
.chip-def   { background:rgba(80,80,80,.07);   color:#668; border-color:rgba(80,80,80,.25); }

/* ── SENTIMENT ROWS ── */
.sent-row {
    background:#07111a; border:1px solid #0c1e2c; border-radius:6px;
    padding:9px 12px; margin-bottom:6px;
    font-family:'Share Tech Mono',monospace; font-size:.73em;
}
.sr-text { color:#80a898; margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.sr-meta { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }
.sr-bar  { background:#0a1820; border-radius:3px; height:3px; overflow:hidden; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background:#060a0f !important;
    border-right:1px solid #0c1e2c !important;
}
.sb-logo {
    background:linear-gradient(135deg,#060f1a,#091a2c);
    border-bottom:1px solid #0c1e2c;
    padding:18px 14px; margin-bottom:14px; text-align:center;
}
.sb-logo .sb-title { font-family:'Orbitron',monospace; font-size:.95em; font-weight:900; color:#00ff88; letter-spacing:.1em; }
.sb-logo .sb-sub   { font-family:'Share Tech Mono',monospace; font-size:.62em; color:#1e4a28; margin-top:3px; }
.file-row { font-family:'Share Tech Mono',monospace; font-size:.7em; margin:3px 0; display:flex; align-items:center; gap:5px; }
.f-ok    { color:#00ff88; }
.f-miss  { color:#ff3366; }
.ethics  {
    background:rgba(255,51,102,.04); border:1px solid rgba(255,51,102,.12);
    border-radius:6px; padding:10px 12px;
    font-family:'Share Tech Mono',monospace; font-size:.62em; color:#2a3a42; line-height:1.8;
}

/* ── Streamlit overrides ── */
div[data-baseweb="select"] > div { background:#070e17 !important; border-color:#0c2230 !important; color:#a0b4c0 !important; }
.stButton > button {
    background:#07111a; border:1px solid #0c3050; color:#00ff88;
    border-radius:5px; font-family:'Share Tech Mono',monospace; font-size:.78em;
    transition:all .2s;
}
.stButton > button:hover { background:#0c1e2e; border-color:#00ff88; box-shadow:0 0 10px rgba(0,255,136,.15); }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:#060a0f; }
::-webkit-scrollbar-thumb { background:#0c2030; border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:#00ff88; }

.js-plotly-plot .plotly { background:transparent !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Constantes Plotly
# ─────────────────────────────────────────────────────────────────────────────
_PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Share Tech Mono", color="#2a5a48", size=10),
    margin=dict(l=34, r=14, t=34, b=34),
    xaxis=dict(gridcolor="#08141e", linecolor="#08141e", zerolinecolor="#08141e",
               tickfont=dict(color="#1e4838", size=9)),
    yaxis=dict(gridcolor="#08141e", linecolor="#08141e", zerolinecolor="#08141e",
               tickfont=dict(color="#1e4838", size=9)),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#08141e",
                font=dict(color="#2a5a48", size=9)),
    hoverlabel=dict(bgcolor="#07111a", bordercolor="#0c2230",
                    font=dict(family="Share Tech Mono", color="#a0b4c0", size=11)),
)

def _pcfg() -> dict:
    return {"displayModeBar": False, "responsive": True}

def _empty_fig(msg: str = "NO DATA", h: int = 220) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, x=.5, y=.5, xref="paper", yref="paper",
                       showarrow=False,
                       font=dict(size=11, color="#1a3a2e", family="Share Tech Mono"))
    l = dict(**_PL)
    l.update(height=h, xaxis=dict(visible=False), yaxis=dict(visible=False))
    fig.update_layout(**l)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_json(p: Path) -> list:
    if not p.exists(): return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception: return []

def _log_tail(p: Path, n: int = 80) -> list:
    if not p.exists(): return []
    try: return p.read_text(encoding="utf-8").splitlines()[-n:]
    except Exception: return []

@st.cache_data(ttl=4)
def load_data() -> dict:
    return {
        "sentiments": _load_json(DATA / "sentiments.json"),
        "alerts":     _load_json(DATA / "alerts.json"),
        "detections": _load_json(DATA / "detections.json"),
        "metadata":   _load_json(DATA / "metadata.json"),
        "log_lines":  _log_tail(DATA / "log.txt"),
        "ts":         datetime.now(),
    }

def _is_recent(ts: str, minutes: int = 60) -> bool:
    try: return datetime.now() - datetime.fromisoformat(ts) < timedelta(minutes=minutes)
    except Exception: return False

def _kpis(d: dict) -> dict:
    sents  = d["sentiments"]
    alerts = d["alerts"]
    dets   = d["detections"]
    scores = [s.get("score",0) for s in sents]
    labels = [s.get("sentiment","neutre") for s in sents]
    avg_s  = round(sum(scores)/len(scores),3) if scores else 0.0
    pos_pc = int(labels.count("positif")*100/len(labels)) if labels else 0
    rec_al = sum(1 for a in alerts if _is_recent(a.get("timestamp",""), 60))
    sen_ct = sum(1 for r in dets if r.get("has_sensitive"))
    threat = min(100, rec_al*20 + sen_ct*5 + (15 if avg_s < -0.3 else 0))
    return dict(n_phrases=len(sents), avg_score=avg_s, pos_pct=pos_pc,
                n_alerts=len(alerts), rec_alerts=rec_al,
                sensitive=sen_ct, n_meta=len(d["metadata"]), threat=threat)


# ─────────────────────────────────────────────────────────────────────────────
# Charts  ← chaque appel a un key= unique passé en argument (FIX BUG)
# ─────────────────────────────────────────────────────────────────────────────

def chart_sentiment_tl(sents: list, key: str) -> None:
    if not sents:
        st.plotly_chart(_empty_fig("[ NO SENTIMENT DATA ]"), use_container_width=True,
                        config=_pcfg(), key=key)
        return
    recent = sents[-100:]
    ts     = [s.get("timestamp","") for s in recent]
    scores = [s.get("score",0) for s in recent]
    labels = [s.get("sentiment","neutre") for s in recent]
    cmap   = {"positif":"#00ff88","négatif":"#ff3366","neutre":"#2a6050","trop_court":"#1a3028"}
    mcolors= [cmap.get(l,"#2a6050") for l in labels]
    fig = go.Figure()
    fig.add_hrect(y0=0.05,  y1=1,    fillcolor="#00ff88", opacity=0.03, line_width=0)
    fig.add_hrect(y0=-0.05, y1=0.05, fillcolor="#2a6050", opacity=0.02, line_width=0)
    fig.add_hrect(y0=-1,    y1=-0.05,fillcolor="#ff3366", opacity=0.03, line_width=0)
    fig.add_trace(go.Scatter(
        x=ts, y=scores, mode="lines+markers",
        line=dict(color="#00aaff", width=1.5, shape="spline", smoothing=0.7),
        marker=dict(color=mcolors, size=6, line=dict(color="#060a0f", width=1)),
        fill="tozeroy", fillcolor="rgba(0,170,255,0.04)",
        hovertemplate="<b>%{x|%H:%M:%S}</b><br>score: %{y:.4f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="#0c2030")
    l = dict(**_PL)
    l.update(title=dict(text="SENTIMENT STREAM", font=dict(color="#2a6040",size=11)),
             yaxis=dict(**_PL["yaxis"], range=[-1.1,1.1]), height=250)
    fig.update_layout(**l)
    st.plotly_chart(fig, use_container_width=True, config=_pcfg(), key=key)


def chart_delay_hist(meta: list, key: str) -> None:
    delays = [m["inter_key_delay"] for m in meta
              if 0.005 < m.get("inter_key_delay",0) < 2.0]
    if len(delays) < 5:
        st.plotly_chart(_empty_fig("[ AWAITING KEYSTROKE DATA ]"), use_container_width=True,
                        config=_pcfg(), key=key)
        return
    avg = sum(delays)/len(delays)
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=delays, nbinsx=45, marker_color="#00aaff", opacity=0.6,
        histnorm="probability density",
        hovertemplate="delay: %{x:.3f}s<extra></extra>",
    ))
    fig.add_vline(x=avg, line_dash="dash", line_color="#00ff88", line_width=1.5,
                  annotation_text=f"μ={avg:.3f}s",
                  annotation_font=dict(color="#00ff88", size=9, family="Share Tech Mono"),
                  annotation_position="top right")
    l = dict(**_PL)
    l.update(title=dict(text="INTER-KEY DELAY DISTRIBUTION", font=dict(color="#2a6040",size=11)),
             xaxis_title="seconds", bargap=0.02, height=250)
    fig.update_layout(**l)
    st.plotly_chart(fig, use_container_width=True, config=_pcfg(), key=key)


def chart_heatmap(meta: list, key: str) -> None:
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    mx   = [[0]*24 for _ in range(7)]
    for m in meta:
        try:
            dt = datetime.fromtimestamp(m["timestamp"])
            mx[dt.weekday()][dt.hour] += 1
        except Exception: continue
    fig = go.Figure(data=go.Heatmap(
        z=mx, x=list(range(24)), y=days,
        colorscale=[[0,"#060a0f"],[0.3,"#052418"],[0.7,"#094024"],[1,"#00ff88"]],
        hoverongaps=False, showscale=False,
        hovertemplate="%{y} %{x}h — %{z} keys<extra></extra>",
    ))
    l = dict(**_PL)
    l.update(title=dict(text="ACTIVITY HEATMAP", font=dict(color="#2a6040",size=11)),
             xaxis=dict(**_PL["xaxis"], dtick=4),
             height=250)
    fig.update_layout(**l)
    st.plotly_chart(fig, use_container_width=True, config=_pcfg(), key=key)


def chart_anomaly(alerts: list, key: str) -> None:
    if not alerts:
        st.plotly_chart(_empty_fig("[ SYSTEM NOMINAL — NO ANOMALIES ✓ ]"),
                        use_container_width=True, config=_pcfg(), key=key)
        return
    ts     = [a.get("timestamp","") for a in alerts]
    scores = [a.get("score",-0.5) for a in alerts]
    cols   = ["#ff3366" if _is_recent(a.get("timestamp",""),60) else "#1e3848" for a in alerts]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ts, y=scores, mode="markers",
        marker=dict(color=cols, size=10, symbol="x-thin",
                    line=dict(color=cols, width=2.5)),
        hovertemplate="<b>%{x|%H:%M:%S}</b><br>score: %{y:.4f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="#0c2030")
    l = dict(**_PL)
    l.update(title=dict(text="ANOMALY TIMELINE · ISOLATION FOREST", font=dict(color="#2a6040",size=11)),
             yaxis_title="decision score", height=250)
    fig.update_layout(**l)
    st.plotly_chart(fig, use_container_width=True, config=_pcfg(), key=key)


def chart_donut(dets: list, key: str) -> None:
    counts: dict = collections.Counter()
    for r in dets:
        for d in r.get("detections",[]): counts[d["type"]] += 1
    if not counts:
        st.plotly_chart(_empty_fig("[ NO SENSITIVE DATA ✓ ]"),
                        use_container_width=True, config=_pcfg(), key=key)
        return
    colors = ["#ff3366","#ffaa00","#00aaff","#bb00ff","#ff6400","#00ff88"]
    fig = go.Figure(data=go.Pie(
        labels=list(counts.keys()), values=list(counts.values()),
        hole=0.56,
        marker=dict(colors=colors[:len(counts)], line=dict(color="#060a0f", width=2)),
        textfont=dict(family="Share Tech Mono", color="#a0b4c0", size=10),
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    total = sum(counts.values())
    fig.add_annotation(text=f"<b>{total}</b>", x=.5, y=.5, showarrow=False,
                       font=dict(size=18, color="#ff3366", family="Orbitron"))
    l = dict(**_PL)
    l.update(title=dict(text="SENSITIVE DATA BREAKDOWN", font=dict(color="#2a6040",size=11)),
             height=250, showlegend=True)
    fig.update_layout(**l)
    st.plotly_chart(fig, use_container_width=True, config=_pcfg(), key=key)


def chart_gauge(score: int, key: str) -> None:
    if   score < 20: col, txt = "#00ff88", "LOW"
    elif score < 50: col, txt = "#ffaa00", "MEDIUM"
    elif score < 75: col, txt = "#ff6400", "HIGH"
    else:            col, txt = "#ff3366", "CRITICAL"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        domain=dict(x=[0,1], y=[0,1]),
        gauge=dict(
            axis=dict(range=[0,100], tickcolor="#0c2030",
                      tickfont=dict(color="#1e3830",size=8,family="Share Tech Mono")),
            bar=dict(color=col, thickness=0.26),
            bgcolor="#060a0f", borderwidth=1, bordercolor="#0c2030",
            steps=[
                dict(range=[0,20],  color="#060f16"),
                dict(range=[20,50], color="#091418"),
                dict(range=[50,75], color="#0e1818"),
                dict(range=[75,100],color="#140810"),
            ],
            threshold=dict(line=dict(color=col,width=2), thickness=0.8, value=score),
        ),
        number=dict(font=dict(family="Orbitron",size=30,color=col)),
    ))
    l = dict(**_PL)
    l.update(title=dict(text=f"THREAT LEVEL · {txt}",
                        font=dict(color=col,size=11,family="Share Tech Mono")), height=250)
    fig.update_layout(**l)
    st.plotly_chart(fig, use_container_width=True, config=_pcfg(), key=key)


def chart_sent_bar(sents: list, key: str) -> None:
    if not sents:
        st.plotly_chart(_empty_fig("[ NO DATA ]", 180), use_container_width=True,
                        config=_pcfg(), key=key)
        return
    counts = collections.Counter(s.get("sentiment","neutre") for s in sents)
    cats   = ["positif","neutre","négatif"]
    vals   = [counts.get(c,0) for c in cats]
    fig = go.Figure(go.Bar(
        x=cats, y=vals, marker_color=["#00ff88","#2a6050","#ff3366"],
        opacity=0.65, hovertemplate="%{x}: %{y}<extra></extra>",
    ))
    l = dict(**_PL)
    l.update(title=dict(text="SENTIMENT DISTRIBUTION",font=dict(color="#2a6040",size=11)),
             height=200, showlegend=False, bargap=0.3)
    fig.update_layout(**l)
    st.plotly_chart(fig, use_container_width=True, config=_pcfg(), key=key)


# ─────────────────────────────────────────────────────────────────────────────
# UI COMPONENTS (sans graphiques — pas de key nécessaire)
# ─────────────────────────────────────────────────────────────────────────────

def ui_header(k: dict, ts: datetime) -> None:
    t = k["threat"]
    if   t < 20: cls, txt = "s-nominal",  "NOMINAL"
    elif t < 50: cls, txt = "s-elevated", "ELEVATED"
    else:        cls, txt = "s-critical", "CRITICAL"
    st.markdown(f"""
    <div class="soc-header">
        <div>
            <h1>🛡️ SOC · AI KEYLOGGER DASHBOARD</h1>
            <p>LAST UPDATE: {ts.strftime('%Y-%m-%d  %H:%M:%S')}
             &nbsp;·&nbsp; {k['n_phrases']} phrases
             &nbsp;·&nbsp; {k['n_meta']} keystrokes
             &nbsp;·&nbsp; {k['n_alerts']} total alerts</p>
        </div>
        <div style="text-align:right;">
            <div class="status-label">SYSTEM STATUS</div>
            <div class="status-val {cls}">{txt}</div>
        </div>
    </div>""", unsafe_allow_html=True)


def ui_kpis(k: dict) -> None:
    s  = k["avg_score"]
    sc = "c-green" if s>0.05 else ("c-red" if s<-0.05 else "c-blue")
    sl = "POSITIVE" if s>0.05 else ("NEGATIVE" if s<-0.05 else "NEUTRAL")
    ac = "c-red"    if k["rec_alerts"] > 0 else "c-green"
    ad = "c-orange" if k["sensitive"]  > 0 else "c-green"
    t  = k["threat"]
    tc = "c-green" if t<20 else ("c-orange" if t<50 else "c-red")
    tb = "b-green" if t<20 else ("b-orange" if t<50 else "b-red")
    tl = "LOW RISK" if t<20 else ("MEDIUM" if t<50 else ("HIGH" if t<75 else "CRITICAL"))

    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="top-bar b-blue"></div><div class="ico">⌨️</div>
        <div class="val c-blue">{k['n_meta']:,}</div>
        <div class="lbl">Keystrokes</div>
        <div class="sub">{k['n_phrases']} phrases analyzed</div>
        <div class="kpi-spark"></div>
      </div>
      <div class="kpi-card">
        <div class="top-bar b-green"></div><div class="ico">🧠</div>
        <div class="val {sc}">{s:+.3f}</div>
        <div class="lbl">Avg Sentiment</div>
        <div class="sub">{sl} · {k['pos_pct']}% positive</div>
        <div class="kpi-spark"></div>
      </div>
      <div class="kpi-card">
        <div class="top-bar {'b-red' if k['rec_alerts']>0 else 'b-green'}"></div><div class="ico">⚠️</div>
        <div class="val {ac}">{k['rec_alerts']}</div>
        <div class="lbl">Alerts (60 min)</div>
        <div class="sub">Cumulated: {k['n_alerts']}</div>
        <div class="kpi-spark"></div>
      </div>
      <div class="kpi-card">
        <div class="top-bar {'b-orange' if k['sensitive']>0 else 'b-green'}"></div><div class="ico">🔒</div>
        <div class="val {ad}">{k['sensitive']}</div>
        <div class="lbl">Sensitive Data</div>
        <div class="sub">email · CB · phone · sécu</div>
        <div class="kpi-spark"></div>
      </div>
      <div class="kpi-card">
        <div class="top-bar {tb}"></div><div class="ico">🛡️</div>
        <div class="val {tc}">{t}</div>
        <div class="lbl">Threat Score /100</div>
        <div class="sub">{tl}</div>
        <div class="kpi-spark"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def ui_scanbar(refresh: int, ts: datetime) -> None:
    st.markdown(f"""
    <div class="scan-bar">
        <span class="live-dot">LIVE MONITORING</span>
        <span>refresh every {refresh}s</span>
        <span style="color:#1a3830;">ISOLATION FOREST &nbsp;|&nbsp; VADER NLP &nbsp;|&nbsp; REGEX ENGINE</span>
        <span style="color:#1a3830;">{ts.strftime('%H:%M:%S')}</span>
    </div>""", unsafe_allow_html=True)


def ui_log(lines: list, n: int) -> None:
    st.markdown('<div class="sec-hdr">📋 LIVE LOG STREAM</div>', unsafe_allow_html=True)
    html = ""
    for line in lines[-n:]:
        line = line.rstrip()
        if not line: continue
        if line.startswith("[20"):
            html += f'<div><span class="lt-ts">{line}</span></div>'
        elif line.startswith("—") or line.startswith("─"):
            html += f'<div class="lt-sep">{line}</div>'
        else:
            safe = line[:130] + ("…" if len(line)>130 else "")
            # Highlight emails
            safe = re.sub(r'(\b[\w.+\-]+@[\w\-]+\.[a-z]{2,}\b)',
                          r'<span class="lt-flag">\1</span>', safe)
            html += f'<div><span class="lt-text">{safe}</span></div>'
    if not html:
        html = '<div class="lt-empty">[ WAITING FOR DATA — launch keylogger.py ]</div>'
    st.markdown(f'<div class="log-term">{html}</div>', unsafe_allow_html=True)


def ui_alerts(alerts: list) -> None:
    st.markdown('<div class="sec-hdr">🚨 RECENT ALERTS</div>', unsafe_allow_html=True)
    recent = [a for a in alerts if _is_recent(a.get("timestamp",""), 120)][-8:]
    if not recent:
        st.markdown('<div class="panel" style="text-align:center;color:#1a4a30;'
                    'font-family:Share Tech Mono,monospace;font-size:.78em;padding:18px;">'
                    '◉ &nbsp; SYSTEM NOMINAL — NO ANOMALIES</div>', unsafe_allow_html=True)
        return
    for a in reversed(recent):
        score = a.get("score",0)
        ts    = a.get("timestamp","")[:19]
        sev   = "CRITICAL" if score<-0.6 else "WARNING"
        cls   = "crit" if sev=="CRITICAL" else "warn"
        col   = "#ff3366" if cls=="crit" else "#ffaa00"
        st.markdown(f"""
        <div class="alert-item {cls}">
            <div>
                <span style="color:{col};font-family:Share Tech Mono,monospace;
                             font-weight:700;font-size:.82em;">[{sev}]</span>
                <span class="a-score" style="color:{col};margin-left:10px;">
                    score={score:.4f}</span>
            </div>
            <span class="a-ts">{ts}</span>
        </div>""", unsafe_allow_html=True)


_CHIP_CSS = {
    "email":"chip-email","carte_bancaire":"chip-cb",
    "telephone_fr":"chip-tel","numero_secu_fr":"chip-secu",
    "mot_de_passe_probable":"chip-pw",
}

def ui_detections(dets: list) -> None:
    st.markdown('<div class="sec-hdr">🔒 SENSITIVE DATA</div>', unsafe_allow_html=True)
    recent = [r for r in dets if r.get("has_sensitive")][-8:]
    if not recent:
        st.markdown('<div class="panel" style="text-align:center;color:#1a4a30;'
                    'font-family:Share Tech Mono,monospace;font-size:.78em;padding:18px;">'
                    '◉ &nbsp; NO SENSITIVE DATA DETECTED</div>', unsafe_allow_html=True)
        return
    for r in reversed(recent):
        ts    = r.get("timestamp","")[:19]
        chips = "".join(
            f'<span class="det-chip {_CHIP_CSS.get(d["type"],"chip-def")}">'
            f'{d["type"].replace("_"," ").upper()}</span>'
            for d in r.get("detections",[])
        )
        st.markdown(f"""
        <div class="panel" style="padding:9px 13px;display:flex;
             justify-content:space-between;align-items:center;">
            <div>{chips}</div>
            <span style="font-family:Share Tech Mono,monospace;font-size:.68em;
                         color:#1a3040;">{ts}</span>
        </div>""", unsafe_allow_html=True)


def ui_sent_table(sents: list) -> None:
    st.markdown('<div class="sec-hdr">🧠 LATEST SENTIMENT ANALYSIS</div>', unsafe_allow_html=True)
    if not sents:
        st.markdown('<div class="panel" style="color:#1a3a30;font-family:Share Tech Mono,monospace;'
                    'font-size:.78em;text-align:center;padding:18px;">[ NO DATA ]</div>',
                    unsafe_allow_html=True)
        return
    cmap = {"positif":"#00ff88","négatif":"#ff3366","neutre":"#2a6050","trop_court":"#1a3028"}
    html = ""
    for s in reversed(sents[-10:]):
        label = s.get("sentiment","neutre")
        score = s.get("score",0)
        text  = s.get("text","")[:65] + ("…" if len(s.get("text",""))>65 else "")
        ts    = s.get("timestamp","")[:16]
        col   = cmap.get(label,"#2a6050")
        bar   = abs(score)*100
        barc  = "#00ff88" if score>0 else "#ff3366"
        html += f"""
        <div class="sent-row">
            <div class="sr-text">{text}</div>
            <div class="sr-meta">
                <span class="sr-score" style="color:{col};">{score:+.4f} [{label}]</span>
                <span style="color:#1a3040;font-size:.85em;">{ts}</span>
            </div>
            <div class="sr-bar">
                <div style="width:{bar:.0f}%;background:{barc};height:3px;border-radius:3px;"></div>
            </div>
        </div>"""
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("""
        <div class="sb-logo">
            <div class="sb-title">🛡️ AI KEYLOGGER</div>
            <div class="sb-sub">SOC SUPERVISION · v2.0</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### ⚙️ Controls")
        refresh = st.slider("Refresh (s)", 2, 30, 5, key="sl_refresh")
        view    = st.selectbox("View", [
            "🖥️  Global Overview",
            "🧠  Sentiments",
            "⚠️   Anomaly Detection",
            "🔒  Sensitive Data",
            "📋  Log Stream",
            "🛡️  Threat Intelligence",
        ], key="sel_view")
        n_log = st.slider("Log lines", 10, 120, 50, key="sl_log")

        st.markdown("---")
        st.markdown("#### 📂 Data Sources")
        files = {
            "log.txt":         (DATA/"log.txt").exists(),
            "sentiments.json": (DATA/"sentiments.json").exists(),
            "alerts.json":     (DATA/"alerts.json").exists(),
            "detections.json": (DATA/"detections.json").exists(),
            "metadata.json":   (DATA/"metadata.json").exists(),
        }
        rows = ""
        for fname, ok in files.items():
            cls  = "f-ok" if ok else "f-miss"
            icon = "◉" if ok else "◌"
            rows += f'<div class="file-row"><span class="{cls}">{icon}</span> {fname}</div>'
        st.markdown(rows, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🛠️ Actions")
        if st.button("🔄 Force Refresh",        use_container_width=True, key="btn_ref"):
            st.cache_data.clear(); st.rerun()
        if st.button("📊 Generate HTML Report", use_container_width=True, key="btn_rpt"):
            try:
                from report_generator import generate_html_report
                p = generate_html_report(str(DATA))
                st.success(f"✅ {p}")
            except Exception as e:
                st.error(f"Error: {e}")
        if st.button("🗑️ Clear Cache",           use_container_width=True, key="btn_clr"):
            st.cache_data.clear(); st.toast("Cache cleared", icon="🗑️")

        st.markdown("---")
        st.markdown("""
        <div class="ethics">
            ⚠ LEGAL NOTICE<br>
            Authorized use only.<br>
            Explicit consent required.<br>
            FR: Loi Godfrain · RGPD<br>
            Educational context only.
        </div>""", unsafe_allow_html=True)

    return dict(refresh=refresh, view=view, n_log=n_log)


# ─────────────────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def view_global(d: dict, cfg: dict, k: dict) -> None:
    ui_scanbar(cfg["refresh"], d["ts"])
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="sec-hdr">📈 SENTIMENT STREAM</div>', unsafe_allow_html=True)
        chart_sentiment_tl(d["sentiments"], key="g_sent_tl")
    with c2:
        st.markdown('<div class="sec-hdr">🕐 ACTIVITY HEATMAP</div>', unsafe_allow_html=True)
        chart_heatmap(d["metadata"], key="g_heatmap")

    c3, c4 = st.columns(2)
    with c3: ui_alerts(d["alerts"])
    with c4: ui_detections(d["detections"])

    c5, c6 = st.columns(2)
    with c5:
        st.markdown('<div class="sec-hdr">⌨️ INTER-KEY DELAYS</div>', unsafe_allow_html=True)
        chart_delay_hist(d["metadata"], key="g_delay")
    with c6:
        st.markdown('<div class="sec-hdr">🔒 SENSITIVE DATA BREAKDOWN</div>', unsafe_allow_html=True)
        chart_donut(d["detections"], key="g_donut")

    c7, c8 = st.columns([3,2])
    with c7: ui_log(d["log_lines"], cfg["n_log"])
    with c8: ui_sent_table(d["sentiments"])


def view_sentiments(d: dict) -> None:
    chart_sentiment_tl(d["sentiments"], key="s_tl")
    c1, c2 = st.columns([2,1])
    with c1:
        chart_sent_bar(d["sentiments"], key="s_bar")
    with c2:
        sents = d["sentiments"]
        if sents:
            counts = collections.Counter(s.get("sentiment","neutre") for s in sents)
            total  = len(sents)
            for lbl, clr in [("positif","#00ff88"),("négatif","#ff3366"),("neutre","#2a6050")]:
                pct = int(counts.get(lbl,0)*100/total)
                st.markdown(f"""
                <div class="panel" style="text-align:center;padding:14px 10px;margin-bottom:10px;">
                    <div style="font-family:Orbitron,monospace;font-size:1.7em;font-weight:900;color:{clr};">{pct}%</div>
                    <div style="font-family:Share Tech Mono,monospace;font-size:.68em;color:#1e4030;
                                text-transform:uppercase;letter-spacing:.1em;margin-top:4px;">{lbl}</div>
                </div>""", unsafe_allow_html=True)
    ui_sent_table(d["sentiments"])


def view_anomalies(d: dict, k: dict) -> None:
    c1, c2 = st.columns([3,1])
    with c1:
        chart_anomaly(d["alerts"], key="a_scatter")
    with c2:
        chart_gauge(k["threat"], key="a_gauge")
    c3, c4 = st.columns(2)
    with c3:
        chart_delay_hist(d["metadata"], key="a_delay")
    with c4:
        ui_alerts(d["alerts"])


def view_sensitive(d: dict) -> None:
    c1, c2 = st.columns([1,2])
    with c1:
        chart_donut(d["detections"], key="sd_donut")
    with c2:
        ui_detections(d["detections"])


def view_log(d: dict, n: int) -> None:
    ui_log(d["log_lines"], n)


def view_threat(d: dict, k: dict) -> None:
    c1, c2, c3 = st.columns([1,2,1])
    with c1: chart_gauge(k["threat"], key="ti_gauge")
    with c2: chart_anomaly(d["alerts"], key="ti_anom")
    with c3: chart_donut(d["detections"], key="ti_donut")

    t  = k["threat"]
    tc = "#00ff88" if t<20 else ("#ffaa00" if t<50 else ("#ff6400" if t<75 else "#ff3366"))
    tl = "LOW" if t<20 else ("MEDIUM" if t<50 else ("HIGH" if t<75 else "CRITICAL"))

    st.markdown(f"""
    <div class="panel" style="padding:18px 22px;margin-top:6px;">
        <div class="sec-hdr" style="margin-bottom:14px;">🛡️ THREAT ASSESSMENT REPORT</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:.78em;line-height:2.1;color:#3a6050;">
            <span style="color:#1e4030;">THREAT LEVEL ......: </span>
            <span style="color:{tc};font-weight:700;">{tl} ({t}/100)</span><br>
            <span style="color:#1e4030;">RECENT ANOMALIES ..: </span>
            <span style="color:{'#ff3366' if k['rec_alerts']>0 else '#00ff88'};">{k['rec_alerts']} (last 60 min)</span><br>
            <span style="color:#1e4030;">SENSITIVE RECORDS .: </span>
            <span style="color:{'#ffaa00' if k['sensitive']>0 else '#00ff88'};">{k['sensitive']} detected</span><br>
            <span style="color:#1e4030;">SENTIMENT INDEX ...: </span>
            <span style="color:{'#00ff88' if k['avg_score']>0 else '#ff3366'};">{k['avg_score']:+.3f}</span><br>
            <span style="color:#1e4030;">TOTAL KEYSTROKES ..: </span>
            <span style="color:#3a6050;">{k['n_meta']:,}</span><br>
            <span style="color:#1e4030;">ANALYSIS STACK ....: </span>
            <span style="color:#3a6050;">Isolation Forest + VADER NLP + Regex + Random Forest</span>
        </div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Sidebar en premier (stabilise les widgets Streamlit)
    cfg = render_sidebar()

    # 2. Données + KPIs
    d = load_data()
    k = _kpis(d)

    # 3. Header + KPI cards
    ui_header(k, d["ts"])
    ui_kpis(k)

    # 4. Router vue
    v = cfg["view"]
    if   "Global"      in v: view_global(d, cfg, k)
    elif "Sentiment"   in v: view_sentiments(d)
    elif "Anomaly"     in v: view_anomalies(d, k)
    elif "Sensitive"   in v: view_sensitive(d)
    elif "Log"         in v: view_log(d, cfg["n_log"])
    elif "Threat"      in v: view_threat(d, k)

    # 5. Countdown auto-refresh (non-bloquant — 1s par tick)
    ph = st.empty()
    for i in range(cfg["refresh"], 0, -1):
        ph.markdown(
            f'<div style="position:fixed;bottom:10px;right:14px;z-index:9999;'
            f'font-family:Share Tech Mono,monospace;font-size:.65em;color:#0e2820;'
            f'background:#060a0f;padding:4px 10px;border:1px solid #0c2030;border-radius:4px;">'
            f'⟳ {i}s</div>',
            unsafe_allow_html=True,
        )
        time.sleep(1)
    st.cache_data.clear()
    st.rerun()


if __name__ == "__main__":
    main()
