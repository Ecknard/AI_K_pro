# extension/dashboard_v3_full.py
# VERSION FINALE — Fusion + améliorations expert

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Keylogger — Threat Monitor",
    page_icon="🛡️",
    layout="wide"
)

# ─────────────────────────────────────────────
# 🎨 CSS ULTRA PREMIUM (NEW)
# ─────────────────────────────────────────────
st.markdown("""
<style>
body {
    background: radial-gradient(circle at top, #0a0e17, #05070d);
}

.risk-banner {
    padding: 14px;
    border-radius: 10px;
    text-align: center;
    font-weight: 800;
    font-size: 1.2em;
    margin-bottom: 15px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% {opacity:0.8;}
    50% {opacity:1;}
    100% {opacity:0.8;}
}

.kpi-card {
    background: #0d1117;
    padding: 18px;
    border-radius: 10px;
    border: 1px solid #21262d;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING (identique)
# ─────────────────────────────────────────────
def load_json_safe(path: Path):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except:
        return []

def load_all():
    return {
        "sentiments": load_json_safe(DATA / "sentiments.json"),
        "alerts": load_json_safe(DATA / "alerts.json"),
        "detections": load_json_safe(DATA / "detections.json"),
        "metadata": load_json_safe(DATA / "metadata.json"),
        "ts": datetime.now()
    }

# ─────────────────────────────────────────────
# 🧠 KPI + SCORE GLOBAL (NEW)
# ─────────────────────────────────────────────
def compute_kpis(data):
    sents = data["sentiments"]
    alerts = data["alerts"]
    dets = data["detections"]

    avg_score = sum([s.get("score", 0) for s in sents]) / len(sents) if sents else 0
    avg_conf = sum([s.get("confidence", 0) for s in sents]) / len(sents) if sents else 0

    risk_map = {"CRITIQUE": 4, "ÉLEVÉ": 3, "MOYEN": 2, "FAIBLE": 1, "AUCUN": 0}
    risks = [risk_map.get(d.get("overall_risk", "AUCUN"), 0) for d in dets]
    max_risk = max(risks) if risks else 0

    # 🔥 SCORE GLOBAL IA
    global_score = round(
        (abs(avg_score) * 0.4) +
        (avg_conf * 0.2) +
        (len(alerts) * 0.1) +
        (max_risk * 0.3),
        2
    )

    return {
        "avg_score": avg_score,
        "avg_conf": avg_conf,
        "alerts": len(alerts),
        "risk_level": max_risk,
        "global_score": global_score
    }

# ─────────────────────────────────────────────
# 🔊 ALERTE SONORE (NEW)
# ─────────────────────────────────────────────
def play_alert():
    st.components.v1.html("""
    <script>
    var audio = new Audio("https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg");
    audio.play();
    </script>
    """, height=0)

# ─────────────────────────────────────────────
# 📊 CORRÉLATION SENTIMENT / RISQUE (NEW)
# ─────────────────────────────────────────────
def chart_correlation(sentiments, detections):
    if not sentiments or not detections:
        return go.Figure()

    scores = [s.get("score", 0) for s in sentiments[-50:]]
    risks = [d.get("overall_risk", "AUCUN") for d in detections[-50:]]

    risk_map = {"AUCUN": 0, "FAIBLE": 1, "MOYEN": 2, "ÉLEVÉ": 3, "CRITIQUE": 4}
    risks_num = [risk_map.get(r, 0) for r in risks]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=scores,
        y=risks_num,
        mode="markers",
        marker=dict(size=10)
    ))

    fig.update_layout(
        title="Corrélation Sentiment vs Risque",
        xaxis_title="Score sentiment",
        yaxis_title="Risque"
    )
    return fig

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    data = load_all()
    kpis = compute_kpis(data)

    # 🎯 RISK BANNER
    risk_colors = ["#3fb950", "#3fb950", "#388bfd", "#d29922", "#f85149"]
    risk_labels = ["AUCUN", "FAIBLE", "MOYEN", "ÉLEVÉ", "CRITIQUE"]

    rc = risk_colors[kpis["risk_level"]]
    rl = risk_labels[kpis["risk_level"]]

    st.markdown(f"""
    <div class="risk-banner" style="background:{rc}20; color:{rc}; border:1px solid {rc}">
        ⚠️ NIVEAU DE RISQUE : {rl}
    </div>
    """, unsafe_allow_html=True)

    # 🔊 SON
    if rl == "CRITIQUE":
        play_alert()

    # KPI
    col1, col2, col3, col4 = st.columns(4)

    col1.markdown(f"<div class='kpi-card'>🧠<br>{kpis['avg_score']:.3f}<br>Sentiment</div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi-card'>📊<br>{kpis['avg_conf']:.2f}<br>Confiance</div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi-card'>⚠️<br>{kpis['alerts']}<br>Alertes</div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='kpi-card'>🔥<br>{kpis['global_score']}<br>Score IA</div>", unsafe_allow_html=True)

    # GRAPH
    st.plotly_chart(
        chart_correlation(data["sentiments"], data["detections"]),
        use_container_width=True
    )

    # RAW DATA
    st.write("### Dernières détections")
    st.json(data["detections"][-5:])

    # AUTO REFRESH PROPRE
    time.sleep(5)
    st.rerun()

if __name__ == "__main__":
    main()
