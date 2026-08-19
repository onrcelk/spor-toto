"""Hedef15 Dashboard — tahmin + oran + filtre görselleştirme.
Çalıştırma: streamlit run src/sportoto/dashboard/app.py
"""
import json
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Hedef15 Dashboard", layout="wide")


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


st.title("🎯 Hedef15 — Spor Toto Tahmin & Filtre Dashboard")

col1, col2 = st.columns(2)
with col1:
    st.subheader("21 Ağustos Tahminleri")
    pred = load_json("data/predictions/2026-08-21-predictions.json")
    if pred:
        rows = []
        for m in pred.get("matches", []):
            rows.append({
                "M": m["match_index"],
                "Maç": f'{m["home_team"]} - {m["away_team"]}',
                "Tahmin": m["predicted_1x2"],
                "Set": m["option_set"],
                "Banko": "🔒" if m.get("banko") else "",
                "Risk": m.get("risk", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.caption(f"Status: {pred.get('status')}")

with col2:
    st.subheader("Çok-Kaynaklı Oranlar")
    odds = load_json("data/live/odds_2026-08-21_multi.json")
    if odds:
        rows = []
        for mm in odds.get("matches", []):
            srcs = mm.get("sources", {})
            rows.append({
                "Maç": f'{mm["home_team"]} - {mm["away_team"]}',
                "Görsel": str(srcs.get("visual", {}).get("odds", "")),
                "Odds-API": str(srcs.get("odds_api", {}).get("odds", "")),
                "Flashscore": str(srcs.get("flashscore", {}).get("odds", "")),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

st.divider()
st.subheader("📊 Model Karşılaştırması (sports-betting ile)")
cmp = load_json("data/analysis/model_comparison_sportsbet.json")
if cmp:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Baseline", cmp["baseline_majority"])
    c2.metric("Bizim GB", cmp["our_model_gb_acc"])
    c3.metric("sports-betting Logit", cmp["sportsbet_logit_acc"])
    c4.metric("Bizim Lift", f'+{cmp["our_lift"]}')
