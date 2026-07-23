# 2. LIVE-NETZMIX DIAGRAMM (Dark Mode mit getrennter Wind- & PV-Anzeige)
st.subheader("📊 Physikalisch-Bilanzielle Herkunft des Stroms im Netz")
st.write("Aktuelle Schätzung für das Verteilnetzgebiet TenneT / Bayernwerk:")

# Daten: PV und Windkraft jetzt getrennt
mix_data = {
    "Energieträger": [
        "Photovoltaik (Solar)", 
        "Windkraft", 
        "Biomasse & Wasserkraft", 
        "Fossile Reserven (Gas/Kohle)", 
        "Strom-Importe (z.B. CZ)"
    ],
    "Anteil (%)": [25, 10, 20, 25, 20]  # Beispielwerte
}
df = pd.DataFrame(mix_data)

# Spezifische Farben für jeden Energieträger (Dark-Mode geeignet):
# Gelb für PV, Cyan/Hellblau für Wind, Grün für Wasser/Biomasse, Orange für Fossile, Rot für Importe
farben = {
    "Photovoltaik (Solar)": "#FFD600",
    "Windkraft": "#00E5FF",
    "Biomasse & Wasserkraft": "#00E676",
    "Fossile Reserven (Gas/Kohle)": "#FF9100",
    "Strom-Importe (z.B. CZ)": "#FF1744"
}

fig = px.pie(
    df, 
    values="Anteil (%)", 
    names="Energieträger", 
    color="Energieträger",
    color_discrete_map=farben,  # Feste Farbzuordnung
    hole=0.4                   # Donut-Diagramm
)

# Dark-Mode Layout für Plotly
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=14),
    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
)

st.plotly_chart(fig, use_container_width=True)
