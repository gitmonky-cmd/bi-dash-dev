import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. SEITEN-LAYOUT EINSTELLEN
st.set_page_config(page_title="Energie-Realität Hirschaid & Altendorf", layout="wide")

# 2. TITEL & HEADER
st.title("⚡ Energie-Realitäts-Check: Hirschaid & Altendorf")
st.caption("Ein Service der Bürgerinitiative | Datenbasis: SMARD.de (Bundesnetzagentur) & MaStR | PLZ 96114 & 96146")

st.markdown("---")

# 3. KENNZAHLEN / QUICK-FACTS
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Installierte PV-Leistung (96114 & 96146)", 
        value="45,2 MWp", 
        delta="Stand MaStR"
    )

with col2:
    st.metric(
        label="Lokale Windleistung auf Gemeindegebiet", 
        value="0,0 MW", 
        delta="Keine WKA vor Ort",
        delta_color="off"
    )

with col3:
    st.metric(
        label="Netzzustand Region (TenneT)", 
        value="Redispatch aktiv", 
        delta="-12 MW Drosselung", 
        delta_color="inverse"
    )

st.markdown("---")

# 4. GESTAPELTES BALKENDIAGRAMM (LOKAL VS. IMPORT)
st.subheader("📊 Gemeinde-Erzeugung vs. Regionaler Netz-Import")
st.write("Vergleich der lokalen Stromerzeugung (96114/96146) mit dem notwendigen Netzbezug von außen im Wochenverlauf:")

# Beispieldaten für die Wochentage (Mo - So)
tage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Erzeugungsdaten in MWh (Gestapelte Säulen)
# WICHTIG: Lokale Windkraft ist exakt 0,0 MWh!
erzeugung_data = {
    "Tag": tage,
    # Block 1: ECHTE LOKALE ERZEUGUNG (Gemeindegebiet Hirschaid & Altendorf)
    "🏡 Photovoltaik (Lokal 96114/96146)": [180, 220, 150, 90, 210, 250, 230],
    "🏡 Biomasse & Wasserkraft (Lokal)": [60, 60, 62, 61, 60, 59, 60],
    "🏡 Windkraft (Lokal)": [0, 0, 0, 0, 0, 0, 0],
    
    # Block 2: REGIONALER NETZ-IMPORT (Aus dem Bayernwerk/TenneT-Netz zugeflossen)
    "🌐 Netz-Import: Windkraft (Region)": [80, 60, 120, 170, 70, 40, 50],
    "🌐 Netz-Import: Fossile Reserven (Gas/Kohle)": [100, 110, 100, 120, 90, 40, 20],
    "🌐 Netz-Import: Ausland / Sonstige": [80, 60, 48, 84, 60, 22, 20]
}

# Strombedarf / Lastprofil der beiden Gemeinden (Rote Kurve)
strombedarf = [500, 510, 520, 525, 490, 410, 380]

df_erzeugung = pd.DataFrame(erzeugung_data)

# Erstellen des Plotly-Diagramms
fig = go.Figure()

# Farbschema zur klaren optischen Trennung:
# Warme / Grüne Töne = Lokale Erzeugung
# Kühle / Violette / Graue Töne = Netz-Import
farben = {
    # Lokaler Block
    "🏡 Photovoltaik (Lokal 96114/96146)": "#FFD600",         # Leuchtendes Sonnengelb
    "🏡 Biomasse & Wasserkraft (Lokal)": "#00E676",             # Echtes Naturgrün
    "🏡 Windkraft (Lokal)": "#37474F",                        # Dunkelgrau (da 0 MWh)
    
    # Import Block
    "🌐 Netz-Import: Windkraft (Region)": "#00E5FF",            # Cyan / Hellblau
    "🌐 Netz-Import: Fossile Reserven (Gas/Kohle)": "#FF9100",  # Orange
    "🌐 Netz-Import: Ausland / Sonstige": "#D500F9"             # Magenta/Pink
}

# Säulen stapeln
for spalte, farbe in farben.items():
    fig.add_trace(go.Bar(
        x=df_erzeugung["Tag"],
        y=df_erzeugung[spalte],
        name=spalte,
        marker_color=farbe
    ))

# Rote Kurve für den Strombedarf (Lastprofil Hirschaid & Altendorf)
fig.add_trace(go.Scatter(
    x=tage,
    y=strombedarf,
    name="🔻 Strombedarf (Hirschaid & Altendorf)",
    line=dict(color="#FF1744", width=4),
    mode="lines+markers"
))

# Layout-Anpassung (Dark Mode & Visuelle Trennung)
fig.update_layout(
    barmode="stack",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=13),
    xaxis=dict(title="Wochentag", showgrid=False),
    yaxis=dict(title="MWh / Tag", showgrid=True, gridcolor="#2A3547"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.5,
        xanchor="center",
        x=0.5
    ),
    margin=dict(l=20, r=20, t=20, b=120)
)

st.plotly_chart(fig, use_container_width=True)

# 5. KLARSTELLENDE ERKLÄRBOX
st.info("""
**💡 Der Unterschied auf einen Blick:**
* **🏡 Gelbe & Grüne Abschnitte:** Strom, der **direkt auf dem Gemeindegebiet** von Hirschaid und Altendorf erzeugt wurde. *(Hinweis: Windkraft vor Ort ist exakt 0 MW).*
* **🌐 Blaue & Violette Abschnitte:** Strom, der über das Bayernwerk-Netz aus Nachbargemeinden oder dem Ausland **importiert werden musste**, um die Deckungslücke zur roten Linie zu schließen.
""")
