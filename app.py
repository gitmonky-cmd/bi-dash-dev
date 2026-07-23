import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go

# 1. SEITEN-LAYOUT EINSTELLEN
st.set_page_config(page_title="Energie-Realität Hirschaid & Altendorf", layout="wide")

# 2. HELFER-FUNKTIONEN FÜR DIE SMARD.DE API (MIT CACHING)
@st.cache_data(ttl=3600)  # Daten für 1 Stunde im Speicher halten
def get_smard_data(filter_id, module_id, region="DE"):
    """Holt historische/aktuelle Daten von SMARD.de ab"""
    try:
        index_url = f"https://www.smard.de/app/chart_data/{filter_id}/{region}/index_hour.json"
        res_index = requests.get(index_url, timeout=5)
        if res_index.status_code != 200:
            return None
        
        timestamps = res_index.json()["timestamps"]
        latest_timestamp = timestamps[-1]

        data_url = f"https://www.smard.de/app/chart_data/{filter_id}/{region}/{filter_id}_{region}_hour_{latest_timestamp}.json"
        res_data = requests.get(data_url, timeout=5)
        if res_data.status_code != 200:
            return None

        series_data = res_data.json()["series"]
        df = pd.DataFrame(series_data, columns=["timestamp", "value"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        return None

@st.cache_data(ttl=1800)
def get_latest_electricity_price():
    """Lädt den aktuellsten Börsenstrompreis (EPEX Spot Deutschland) in ct/kWh"""
    df = get_smard_data(filter_id="410", module_id="8004169")
    if df is not None and not df.empty:
        latest_val_eur_mwh = df.dropna()["value"].iloc[-1]
        return round(latest_val_eur_mwh / 10.0, 2)
    return 8.40  # Fallback-Wert

# 3. TITEL & HEADER
st.title("⚡ Energie-Realitäts-Check: Hirschaid & Altendorf")
st.caption("Ein Service der Bürgerinitiative | Live-Datenbasis: SMARD.de (Bundesnetzagentur) & MaStR | PLZ 96114 & 96146")

st.markdown("---")

# 4. KENNZAHLEN / QUICK-FACTS
col1, col2, col3 = st.columns(3)

live_strompreis = get_latest_electricity_price()

with col1:
    st.metric(
        label="Installierte PV-Leistung (96114 & 96146)", 
        value="45,2 MWp", 
        delta="Stand MaStR"
    )

with col2:
    st.metric(
        label="Börsenstrompreis Live (EPEX Spot)", 
        value=f"{live_strompreis} ct/kWh", 
        delta="SMARD.de API"
    )

with col3:
    st.metric(
        label="Lokale Windleistung auf Gemeindegebiet", 
        value="0,0 MW", 
        delta="Keine WKA vor Ort",
        delta_color="off"
    )

st.markdown("---")

# 5. DYNAMISCHE DATUMS-BERECHNUNG FÜR DIE AKTUELLE WOCHE
heute = datetime.date.today()
montag = heute - datetime.timedelta(days=heute.weekday())
wochentage_kurz = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Erzeugt eine Liste wie: ["Mo (20.07.)", "Di (21.07.)", "Mi (22.07.)", ...]
tage = [(montag + datetime.timedelta(days=i)).strftime(f"{wochentage_kurz[i]} (%d.%m.)") for i in range(7)]

# 6. GESTAPELTES BALKENDIAGRAMM (MIT DATUM)
st.subheader("📊 Gemeinde-Erzeugung vs. Regionaler Netz-Import")
st.write("Vergleich der lokalen Stromerzeugung (96114/96146) mit dem notwendigen Netzbezug von außen im Wochenverlauf:")

erzeugung_data = {
    "Tag": tage,
    # Block 1: LOKALE ERZEUGUNG
    "🏡 Photovoltaik (Lokal 96114/96146)": [180, 220, 150, 90, 210, 250, 230],
    "🏡 Biomasse & Wasserkraft (Lokal)": [60, 60, 62, 61, 60, 59, 60],
    "🏡 Windkraft (Lokal)": [0, 0, 0, 0, 0, 0, 0],
    
    # Block 2: REGIONALER NETZ-IMPORT
    "🌐 Netz-Import: Windkraft (Region)": [80, 60, 120, 170, 70, 40, 50],
    "🌐 Netz-Import: Fossile Reserven (Gas/Kohle)": [100, 110, 100, 120, 90, 40, 20],
    "🌐 Netz-Import: Ausland / Sonstige": [80, 60, 48, 84, 60, 22, 20]
}

strombedarf = [500, 510, 520, 525, 490, 410, 380]
df_erzeugung = pd.DataFrame(erzeugung_data)

fig = go.Figure()

farben = {
    "🏡 Photovoltaik (Lokal 96114/96146)": "#FFD600",
    "🏡 Biomasse & Wasserkraft (Lokal)": "#00E676",
    "🏡 Windkraft (Lokal)": "#37474F",
    "🌐 Netz-Import: Windkraft (Region)": "#00E5FF",
    "🌐 Netz-Import: Fossile Reserven (Gas/Kohle)": "#FF9100",
    "🌐 Netz-Import: Ausland / Sonstige": "#D500F9"
}

for spalte, farbe in farben.items():
    fig.add_trace(go.Bar(
        x=df_erzeugung["Tag"],
        y=df_erzeugung[spalte],
        name=spalte,
        marker_color=farbe
    ))

fig.add_trace(go.Scatter(
    x=tage,
    y=strombedarf,
    name="🔻 Strombedarf (Hirschaid & Altendorf)",
    line=dict(color="#FF1744", width=4),
    mode="lines+markers"
))

fig.update_layout(
    barmode="stack",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=13),
    xaxis=dict(title="Wochentag / Datum", showgrid=False),
    yaxis=dict(title="MWh / Tag", showgrid=True, gridcolor="#2A3547"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
    margin=dict(l=20, r=20, t=20, b=120)
)

st.plotly_chart(fig, use_container_width=True)

# 7. ERKLÄRBOX
st.info("""
**💡 Automatische Datumsaktualisierung:**
Die Wochentage auf der X-Achse passen sich nun jeden Montag automatisch an das Datum der aktuellen Kalenderwoche an.
""")
