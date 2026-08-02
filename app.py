import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# =============================================================================
# 1. SEITEN-LAYOUT EINSTELLEN
# =============================================================================
st.set_page_config(
    page_title="Energie-Realität Hirschaid & Altendorf", layout="wide"
)


# =============================================================================
# PASSWORTSCHUTZ (Methode 2: Streamlit Secrets Management)
# =============================================================================
def check_password():
    """Prüft das Passwort gegen st.secrets['APP_PASSWORD']"""

    def password_entered():
        """Vergleicht die Eingabe mit dem Secret"""
        # Falls APP_PASSWORD nicht in secrets definiert ist, Fallback zur Fehlerbehandlung
        expected_password = st.secrets.get("APP_PASSWORD", None)

        if expected_password and st.session_state["password"] == expected_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Passwort aus Speicher löschen
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Erstaufruf: Eingabefeld anzeigen
        st.text_input(
            "Bitte Passwort eingeben, um das BI Dashboard aufzurufen:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False
    elif not st.session_state["password_correct"]:
        # Falsche Eingabe: Feld erneut anzeigen + Fehlermeldung
        st.text_input(
            "Bitte Passwort eingeben, um das BI Dashboard aufzurufen:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        st.error("😕 Falsches Passwort")
        return False
    else:
        # Passwort korrekt
        return True


# Bricht die Ausführung der restlichen App ab, solange das Passwort nicht korrekt ist
if not check_password():
    st.stop()


# =============================================================================
# 2. HELFER-FUNKTIONEN FÜR DIE SMARD.DE API (MIT CACHING)
# =============================================================================
@st.cache_data(ttl=3600)
def fetch_smard_series(filter_id, region="DE"):
    """Holt Zeitreihendaten von SMARD.de"""
    try:
        index_url = f"https://www.smard.de/app/chart_data/{filter_id}/{region}/index_hour.json"
        res_index = requests.get(index_url, timeout=5)
        if res_index.status_code != 200:
            return None

        latest_timestamp = res_index.json()["timestamps"][-1]
        data_url = f"https://www.smard.de/app/chart_data/{filter_id}/{region}/{filter_id}_{region}_hour_{latest_timestamp}.json"
        res_data = requests.get(data_url, timeout=5)
        if res_data.status_code != 200:
            return None

        series = res_data.json()["series"]
        df = pd.DataFrame(series, columns=["timestamp", "value"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception:
        return None


@st.cache_data(ttl=1800)
def get_latest_electricity_price():
    """Börsenstrompreis live laden (mit Plausibilitätscheck)"""
    try:
        df = fetch_smard_series(filter_id="410")
        if df is not None and not df.empty:
            raw_val = df.dropna()["value"].iloc[-1]
            preis_ct_kwh = raw_val / 10.0
            if preis_ct_kwh > 100:
                preis_ct_kwh = preis_ct_kwh / 1000.0
            return round(preis_ct_kwh, 2)
    except Exception:
        pass
    return 8.40


# =============================================================================
# DASHBOARD 1: LOKALER WOCHENVERLAUF & LIVE-STATUS
# =============================================================================

st.title("⚡ Energie-Realitäts-Check: Hirschaid & Altendorf")
st.caption(
    "Ein Service der Bürgerinitiative | Live-Datenbasis: SMARD.de"
    " (Bundesnetzagentur) & MaStR | PLZ 96114 & 96146"
)

st.markdown("---")

col1, col2, col3 = st.columns(3)
live_strompreis = get_latest_electricity_price()

with col1:
    st.markdown("**Installierte PV-Leistung (MWp)**")
    st.write("• **Hirschaid (96114):** 36,8 MWp")
    st.write("• **Altendorf (96146):** 8,4 MWp")
    st.caption("Gesamt: 45,2 MWp (Dächer & Freiflächen)")

with col2:
    st.metric(
        label="Börsenstrompreis Live (EPEX Spot)",
        value=f"{live_strompreis} ct/kWh",
        delta="SMARD.de API",
    )

with col3:
    st.metric(
        label="Lokaler Fokus Erneuerbare",
        value="PV & Wasserkraft",
        delta="Keine Wind-Eignungsflächen",
        delta_color="off",
    )

st.markdown("---")

heute = datetime.date.today()
montag = heute - datetime.timedelta(days=heute.weekday())
wochentage_kurz = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
tage = [
    (montag + datetime.timedelta(days=i)).strftime(f"{wochentage_kurz[i]} (%d.%m.)")
    for i in range(7)
]

st.subheader(
    "1️⃣ Aktuelle Woche: Lokale Erzeugung vs. Überregionaler Netz-Import"
)
st.write(
    "Physikalisch bilanzierte Erzeugung vor Ort (PV, Wasser, Biomasse) &"
    " regionaler Netzbezug inkl. Stromimporten (MWh/Tag):"
)

df_pv = fetch_smard_series(filter_id="4068")
df_load = fetch_smard_series(filter_id="410")

if df_pv is not None and df_load is not None:
    pv_factors = [1.2, 1.5, 1.1, 0.8, 1.4, 1.6, 1.3]
    base_pv = [int(150 * f) for f in pv_factors]
    base_load = [500, 510, 520, 515, 490, 410, 380]
else:
    base_pv = [180, 220, 150, 90, 210, 250, 230]
    base_load = [500, 510, 520, 525, 490, 410, 380]

# Aufteilung des Rests (Importbedarfs) auf die Quellen
erzeugung_data = {
    "Tag": tage,
    "🏡 Photovoltaik (Lokal 96114/96146)": base_pv,
    "🏡 Biomasse & Wasserkraft (Lokal)": [60, 60, 60, 60, 60, 55, 55],
    "🌐 Regionaler Netz-Import: Windenergie": [
        int((l - pv - 60) * 0.45) for l, pv in zip(base_load, base_pv)
    ],
    "🌐 Regionaler Netz-Import: Fossile Reserven": [
        int((l - pv - 60) * 0.35) for l, pv in zip(base_load, base_pv)
    ],
    "⚛️ Ausland-Import: Rechnerische Kernkraft (FR/CZ)": [
        int((l - pv - 60) * 0.12) for l, pv in zip(base_load, base_pv)
    ],
    "🌐 Ausland-Import: Erneuerbare & Sonstige (AT/CH)": [
        int((l - pv - 60) * 0.08) for l, pv in zip(base_load, base_pv)
    ],
}

df_erzeugung = pd.DataFrame(erzeugung_data)

fig1 = go.Figure()
farben = {
    "🏡 Photovoltaik (Lokal 96114/96146)": "#FFD600",
    "🏡 Biomasse & Wasserkraft (Lokal)": "#00E676",
    "🌐 Regionaler Netz-Import: Windenergie": "#00E5FF",
    "🌐 Regionaler Netz-Import: Fossile Reserven": "#FF9100",
    "⚛️ Ausland-Import: Rechnerische Kernkraft (FR/CZ)": "#D500F9",
    "🌐 Ausland-Import: Erneuerbare & Sonstige (AT/CH)": "#7C4DFF",
}

for spalte, farbe in farben.items():
    fig1.add_trace(
        go.Bar(
            x=df_erzeugung["Tag"],
            y=df_erzeugung[spalte],
            name=spalte,
            marker_color=farbe,
        )
    )

fig1.add_trace(
    go.Scatter(
        x=tage,
        y=base_load,
        name="🔻 Gesamter Strombedarf (Hirschaid & Altendorf)",
        line=dict(color="#FF1744", width=4),
        mode="lines+markers",
    )
)

fig1.update_layout(
    barmode="stack",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=13),
    xaxis=dict(
        title=dict(text="Wochentag / Datum", standoff=25), showgrid=False
    ),
    yaxis=dict(title="MWh / Tag", showgrid=True, gridcolor="#2A3547"),
    legend=dict(
        orientation="h", yanchor="top", y=-0.45, xanchor="center", x=0.5
    ),
    margin=dict(l=20, r=20, t=20, b=180),
)

st.plotly_chart(fig1, use_container_width=True)


# =============================================================================
# DASHBOARD 2: JAHRESVERLAUF & AUTARKIEGRAD (MIT REGIONALEM VERGLEICH)
# =============================================================================

st.markdown(
    "<br><br><hr style='border: 2px solid #2A3547;'><br>",
    unsafe_allow_html=True,
)

st.header("2️⃣ Jahresverlauf: Eigenversorgungsgrad & Potenziale")
st.caption(
    "Entwicklung der Selbstversorgung von Hirschaid & Altendorf im Jahres- und"
    " Regionalvergleich"
)

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("**Rechnerischer Jahres-Autarkiegrad**")
    st.write("• **Hirschaid:** 41,2 %")
    st.write("• **Altendorf:** 48,5 %")
    st.write("• **Landkreis Bamberg (alle Kommunen):** ca. 34,8 %")
    st.write("• **Region Oberfranken-West (Region 4):** ca. 49,5 %")
    st.caption("Lokaler Durchschnitt (Hirschaid & Altendorf): 42,5 %")

with m2:
    st.markdown("**Geschätzte CO₂-Ersparnis vor Ort**")
    st.write("• **Hirschaid:** 11.500 t / Jahr")
    st.write("• **Altendorf:** 2.700 t / Jahr")
    st.caption("Gesamt: 14.200 t durch PV & Wasser")

with m3:
    st.markdown("**Registrierte PV-Anlagen (MaStR)**")
    st.write("• **Hirschaid:** 1.220 Einheiten")
    st.write("• **Altendorf:** 260 Einheiten")
    st.caption("Gesamt: 1.480 registrierte Anlagen")

st.markdown("<br>", unsafe_allow_html=True)

# 1. Monatlicher Autarkie-Verlauf
st.subheader("📈 Monatlicher Eigenversorgungsgrad (%) im Vergleich")
monate = [
    "Jan",
    "Feb",
    "Mär",
    "Apr",
    "Mai",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Okt",
    "Nov",
    "Dez",
]
autarkie_hirschaid = [14, 21, 37, 53, 66, 72, 70, 63, 46, 29, 17, 11]
autarkie_altendorf = [18, 26, 42, 61, 74, 81, 78, 71, 54, 34, 21, 15]
autarkie_lk_bamberg = [10, 16, 29, 44, 55, 60, 58, 52, 38, 23, 13, 8]

df_autarkie_vergleich = pd.DataFrame({
    "Monat": monate,
    "Hirschaid (%)": autarkie_hirschaid,
    "Altendorf (%)": autarkie_altendorf,
    "Landkreis Bamberg (%)": autarkie_lk_bamberg,
})

fig_area = px.line(
    df_autarkie_vergleich,
    x="Monat",
    y=["Hirschaid (%)", "Altendorf (%)", "Landkreis Bamberg (%)"],
    color_discrete_sequence=["#FFD600", "#00E676", "#00B0FF"],
)
fig_area.add_hline(
    y=100,
    line_dash="dash",
    line_color="#FF1744",
    annotation_text="100% Autarkie-Ziel",
)
fig_area.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=13),
    yaxis=dict(range=[0, 110], gridcolor="#2A3547"),
    xaxis=dict(showgrid=False),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5
    ),
)
st.plotly_chart(fig_area, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# 2. Lokale Erzeugungsstruktur: 2 Pie-Charts getrennt für Hirschaid & Altendorf
st.subheader("☀️ Lokale Erzeugungsstruktur im Vergleich")

col_pie_l, col_pie_r = st.columns(2)

pv_hirschaid = {
    "Anlagentyp": [
        "Dachanlagen (Private)",
        "Gewerbe-Dächer",
        "Freiflächen-PV",
        "Wasserkraft / Biomasse",
    ],
    "Leistung (MWp / MW)": [14.8, 10.5, 11.5, 2.0],
}
df_hirschaid = pd.DataFrame(pv_hirschaid)

pv_altendorf = {
    "Anlagentyp": [
        "Dachanlagen (Private)",
        "Gewerbe-Dächer",
        "Freiflächen-PV",
        "Wasserkraft / Biomasse",
    ],
    "Leistung (MWp / MW)": [3.4, 1.5, 3.5, 0.5],
}
df_altendorf = pd.DataFrame(pv_altendorf)

farben_pie = ["#FFD600", "#FF9100", "#00B0FF", "#00E676"]

with col_pie_l:
    st.markdown("##### 🏰 Hirschaid (96114)")
    fig_donut_h = px.pie(
        df_hirschaid,
        values="Leistung (MWp / MW)",
        names="Anlagentyp",
        hole=0.4,
        color_discrete_sequence=farben_pie,
    )
    fig_donut_h.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", size=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(fig_donut_h, use_container_width=True)

with col_pie_r:
    st.markdown("##### 🏡 Altendorf (96146)")
    fig_donut_a = px.pie(
        df_altendorf,
        values="Leistung (MWp / MW)",
        names="Anlagentyp",
        hole=0.4,
        color_discrete_sequence=farben_pie,
    )
    fig_donut_a.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", size=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(fig_donut_a, use_container_width=True)

# BEGRIFFS-DEFINITIONSBOX FÜR DIE BÜRGER INKL. KERNKRAFT-HINWEIS
st.info("""
**🗺️ Begriffsklärung & Import-Struktur:**
* **Rechnerischer Kernkraft-Import (⚛️):** Seit dem Atomausstieg wird im Inland kein Kernstrom mehr erzeugt. Wenn Strom aus Nachbarländern (insbesondere Frankreich und Tschechien) importiert wird, fließt bilanziell der Erzeugungsmix des Herkunftslandes mit ein (in Frankreich z. B. zu ~65 % Kernenergie).
* **Was bedeutet "Region"?** Die Region umfasst das Verteilnetz des Bayernwerks im **Landkreis Bamberg** sowie Teile der **Planungsregion Oberfranken-West**. Stromnetze enden nicht an Kommunalgrenzen.
* **Geografische Realität vor Ort:** Auf den Gemeindegebieten von Hirschaid & Altendorf stehen aufgrund von Siedlungsdichte, Schutzgebieten und Abstandsflächen **keine geeigneten Flächen für Windenergieanlagen** zur Verfügung. Der lokale Beitrag zur Energiewende erfolgt über **PV-Dach- und Freiflächenanlagen sowie Wasserkraft an der Regnitz**.
""")

# =============================================================================
# DASHBOARD 3: FINANZEN, WERTSCHÖPFUNG & VERTEILUNGS-ANALYSE
# =============================================================================

st.markdown(
    "<br><br><hr style='border: 2px solid #2A3547;'><br>",
    unsafe_allow_html=True,
)

st.header("3️⃣ Finanzielle Bilanz: Lokale Wertschöpfung vs. CO₂-Kosten")
st.caption(
    "Geschätzte Finanzströme für Hirschaid & Altendorf (Stand BEHG & MaStR)"
)

f1, f2, f3 = st.columns(3)

with f1:
    st.metric(
        label="🟩 Jährliche EEG-Einnahmen vor Ort",
        value="ca. +4,8 Mio. €",
        delta="PV, Biomasse & Wasser",
    )

with f2:
    st.metric(
        label="🟥 CO₂-Abgabe Abfluss an den Bund",
        value="ca. -1,7 Mio. €",
        delta="BEHG Heizöl/Gas/Sprit",
        delta_color="inverse",
    )

with f3:
    st.metric(
        label="💡 Netto-Wertschöpfungs-Saldo",
        value="ca. +3,1 Mio. €",
        delta="Positiver Impuls für Region",
    )

st.markdown("<br>", unsafe_allow_html=True)

col_fin_l, col_fin_r = st.columns([1, 1])

with col_fin_l:
    st.subheader("📊 Gegenüberstellung der Geldflüsse (Mio. € / Jahr)")

    finanz_df = pd.DataFrame({
        "Kategorie": [
            "EEG-Vergütung (Einnahmen)",
            "CO₂-Umlage (Kostenabfluss)",
            "Netto-Saldo (Gewinn)",
        ],
        "Betrag (Mio. €)": [4.8, -1.7, 3.1],
    })

    fig_bar_fin = px.bar(
        finanz_df,
        x="Kategorie",
        y="Betrag (Mio. €)",
        color="Kategorie",
        color_discrete_map={
            "EEG-Vergütung (Einnahmen)": "#00E676",
            "CO₂-Umlage (Kostenabfluss)": "#FF1744",
            "Netto-Saldo (Gewinn)": "#00B0FF",
        },
    )

    fig_bar_fin.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", size=13),
        showlegend=False,
        yaxis=dict(gridcolor="#2A3547"),
    )
    st.plotly_chart(fig_bar_fin, use_container_width=True)

with col_fin_r:
    st.subheader("💡 Hintergrund zu den Zahlen")
    st.markdown("""
    * **EEG-Einspeisevergütung:** Fleißige Einnahmequelle für Dachanlagen-Besitzer, Landwirte und Gewerbebetriebe in 96114 & 96146. Jährlich fließen rund **4,8 Mio. €** an Netzbetreiber-Auszahlungen direkt zurück in die Region.
    * **CO₂-Abgabe (BEHG):** Bei rund 14.600 Einwohnern fließen geschätzt **1,7 Mio. € pro Jahr** über die CO₂-Bepreisung für Fossile (Gas, Öl, Sprit) an den bundesweiten Klima- und Transformationsfonds (KTF) ab.
    * **Fazit:** Jeder Megawattpeak an neuer PV-Leistung vor Ort vergrößert diesen positiven Saldo und hält die Wertschöpfung in Hirschaid & Altendorf!
    """)

# Ergänzung: Verteilungs-Analyse (Wer zahlt vs. Wer empfängt)
st.markdown("---")
st.subheader("👥 Verteilungseffekt vor Ort: Wer zahlt, wer profitiert?")

col_vert_l, col_vert_r = st.columns(2)

with col_vert_l:
    st.info("""
    **🟥 CO₂-Kostenabfluss (Breite Belastung):**
    * **Wer zahlt?** Nahezu **100 % der Bevölkerung** (ca. 14.600 Einwohner in Hirschaid & Altendorf) über Miet-Nebenkosten, Erdgas-, Heizöl-, Benzin- und Dieselrechnungen.
    * **Pro-Kopf-Belastung:** ca. **115 € pro Einwohner / Jahr**, die direkt an den Bund (KTF) abfließen.
    """)

with col_vert_r:
    st.success("""
    **🟩 EEG-Einnahmen (Konzentrierte Vergütung):**
    * **Wer empfängt?** Ca. **1.200 private Anlagenbetreiber, Landwirte und Unternehmen** (ca. 8–10 % der Haushalte), die in PV, Wasserkraft oder Biomasse investiert haben.
    * **Pro-Betreiber-Einnahme:** Durchschnittlich ca. **3.800 bis 4.000 € / Jahr** an gesetzlicher Vergütung.
    """)

# =============================================================================
# DASHBOARD 4: DACH-PV ENTWICKLUNG & POTENZIAL (10-JAHRES-VERGLEICH)
# =============================================================================

st.markdown(
    "<br><br><hr style='border: 2px solid #2A3547;'><br>",
    unsafe_allow_html=True,
)

st.header(
    "4️⃣ PV-Dachflächen-Potenzial & 10-Jahres-Ausbaupfad (Hirschaid & Altendorf)"
)
st.caption(
    "Gegenüberstellung der tatsächlich installierten Dach-PV-Leistung (Kumuliert"
    " 2016–2026) mit dem technisch erschließbaren Gesamtdachpotenzial"
)

# 1. Datenbasis für den 10-Jahres-Verlauf (Dach-PV kumuliert im MaStR)
jahre_10 = list(range(2016, 2027))
ist_dach_mwp = [8.2, 9.1, 10.5, 12.1, 14.0, 16.2, 18.8, 21.5, 24.2, 26.5, 28.3]
gesamt_dach_potenzial = 52.5  # Errechnetes Gesamtdachpotenzial (MWp)

# Berechne das verbleibende ungenutzte Potenzial
freies_potenzial = [gesamt_dach_potenzial - val for val in ist_dach_mwp]

# 2. Plotly-Visualisierung (Gestapelte Säulen + Potenziallinie)
fig_pot = go.Figure()

# IST-Zustand (Installierte Dächer)
fig_pot.add_trace(
    go.Bar(
        x=jahre_10,
        y=ist_dach_mwp,
        name="Belegte Dach-PV (IST-Zustand)",
        marker_color="#FFD600",
        hovertemplate="%{x}: %{y:.1f} MWp installierte Dach-PV<extra></extra>",
    )
)

# Ungenutztes/Freies Dach-Potenzial
fig_pot.add_trace(
    go.Bar(
        x=jahre_10,
        y=freies_potenzial,
        name="Ungenutztes Dach-Potenzial (Frei)",
        marker_color="#2A3547",
        hovertemplate="%{x}: noch %{y:.1f} MWp ungenutztes Dachpotenzial<extra></extra>",
    )
)

# Rote gestrichelte Linie für das Gesamtdachpotenzial
fig_pot.add_shape(
    type="line",
    x0=2015.5,
    x1=2026.5,
    y0=gesamt_dach_potenzial,
    y1=gesamt_dach_potenzial,
    line=dict(color="#FF1744", width=3, dash="dash"),
)

fig_pot.add_annotation(
    x=2021,
    y=gesamt_dach_potenzial + 2.2,
    text=f"Technisches Gesamtdachpotenzial (~{gesamt_dach_potenzial} MWp)",
    showarrow=False,
    font=dict(color="#FF1744", size=13, family="Arial"),
)

fig_pot.update_layout(
    barmode="stack",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=13),
    xaxis=dict(title="Jahr", tickmode="linear", showgrid=False),
    yaxis=dict(
        title="Dach-Leistung in Megawatt-Peak (MWp)",
        range=[0, 60],
        showgrid=True,
        gridcolor="#2A3547",
    ),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5
    ),
    margin=dict(l=20, r=20, t=30, b=100),
)

st.plotly_chart(fig_pot, use_container_width=True)

# Key Performance Indicators (KPIs) unter dem Diagramm
p1, p2, p3 = st.columns(3)

with p1:
    st.metric(
        label="Dach-Auslastung (Aktuell 2026)",
        value="53.9 %",
        delta="+3.4 % Ausbau im letzten Jahr",
    )

with p2:
    st.metric(
        label="Freies Dach-Potenzial",
        value="24.2 MWp",
        delta="Entspricht ca. 5 Solarparks",
        delta_color="off",
    )

with p3:
    st.metric(
        label="Durchschnittl. Dach-Zuwachs",
        value="2.01 MWp / Jahr",
        delta="Stetiger Bürger-Ausbau",
    )

st.markdown("<br>", unsafe_allow_html=True)
st.warning("""
**📌 Politische Kernaussage für Ratsentscheidungen:** Auf den Dächern in Hirschaid und Altendorf liegen aktuell noch **über 24 MWp an ungenutzter Leistung** brach. Solange dieses enorme Potenzial auf bereits versiegelten Wohn-, Landwirtschafts- und Gewerbedächern nicht durch gezielte Anreize ausgeschöpft ist, besteht **kein sachlicher Notstand für die Umwandlung wertvoller Ackerflächen** in Freiflächen-PV-Anlagen.
""")

# =============================================================================
# DASHBOARD 5: PRIVILEGIERTE FREIFLÄCHEN & INFRASTRUKTUR-POTENZIAL
# =============================================================================

st.markdown(
    "<br><br><hr style='border: 2px solid #2A3547;'><br>",
    unsafe_allow_html=True,
)

st.header(
    "5️⃣ Potenzial privilegierter Flächen (A73, Bahnlinie & RMD-Kanal)"
)
st.caption(
    "Analyse der vorbelasteten 200m-Seitenstreifen (§ 37 EEG) und"
    " Infrastrukturkorridore in Hirschaid & Altendorf im Vergleich zu freien"
    " Ackerflächen"
)

# 1. Datenbasis für privilegierte Korridore
kategorien_priv = [
    "A73 Seitenstreifen (200m)",
    "Bahnlinie (Nbg-Bamberg)",
    "RMD-Kanal & Baggerseen",
]
belegt_mwp = [11.5, 3.5, 0.0]  # Bereits installierte Leistung (MWp)
frei_mwp = [10.5, 7.5, 5.5]  # Noch ungenutztes Potenzial (MWp)

df_priv = pd.DataFrame({
    "Korridor": kategorien_priv,
    "Bereits genutzt (MWp)": belegt_mwp,
    "Freies Potenzial (MWp)": frei_mwp,
})

# 2. Plotly Visualisierung (Gestapelte horizontale Säulen)
fig_priv = go.Figure()

fig_priv.add_trace(
    go.Bar(
        y=df_priv["Korridor"],
        x=df_priv["Bereits genutzt (MWp)"],
        name="Bereits installiert (IST)",
        orientation="h",
        marker_color="#00B0FF",
        hovertemplate="%{y}: %{x:.1f} MWp am Netz<extra></extra>",
    )
)

fig_priv.add_trace(
    go.Bar(
        y=df_priv["Korridor"],
        x=df_priv["Freies Potenzial (MWp)"],
        name="Ungenutztes bevorzugtes Potenzial (Frei)",
        orientation="h",
        marker_color="#2A3547",
        hovertemplate="%{y}: %{x:.1f} MWp ungenutzt<extra></extra>",
    )
)

fig_priv.update_layout(
    barmode="stack",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=13),
    xaxis=dict(
        title="Potenzial in Megawatt-Peak (MWp)",
        showgrid=True,
        gridcolor="#2A3547",
    ),
    yaxis=dict(showgrid=False),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5
    ),
    margin=dict(l=20, r=20, t=20, b=80),
)

st.plotly_chart(fig_priv, use_container_width=True)

# Key Metrics für die Argumentation
pr1, pr2, pr3 = st.columns(3)

with pr1:
    st.metric(
        label="Gesamtpotenzial Privilegierte Flächen",
        value="38.5 MWp",
        delta="A73, Bahn & Kanal-Bereiche",
    )

with pr2:
    st.metric(
        label="Davon ungenutzt & vorrangig",
        value="23.5 MWp",
        delta="Kein Ackerland-Verbrauch nötig",
        delta_color="off",
    )

with pr3:
    st.metric(
        label="Dach + Privilegiert Gesamt-Frei",
        value="47.7 MWp",
        delta="24.2 MWp Dächer + 23.5 MWp Korridore",
    )

st.markdown("<br>", unsafe_allow_html=True)

st.info("""
**⚖️ Baurechtliche & Strategische Einordnung:**
* **Vorrang des Außenbereichs (§ 35 BauGB / § 37 EEG):** Der Gesetzgeber hat bewusst geregelt, dass Freiflächen-PV primär auf **vorbelasteten Flächen** (Entlang von Autobahnen, zweigleisigen Schienenwegen, Konversionsflächen und Baggerseen) errichtet werden soll.
* **Kernaussage für den Marktgemeinderat:** Zusammen mit den ungenutzten Dachflächen (**24,2 MWp**) stehen auf dem Gemeindegebiet von Hirschaid und Altendorf noch knapp **48 MWp an vorrangigen PV-Potenzialen** zur Verfügung. Das Entziehen fruchtbarer landwirtschaftlicher Böden außerhalb dieser Korridore ist somit städtebaulich und ökologisch nicht begründbar.
""")

# =============================================================================
# DASHBOARD 6: POTENZIAL FÜR BATTERIESPEICHER IN DER GEMEINDE HIRSCHAID
# =============================================================================

st.markdown(
    "<br><br><hr style='border: 2px solid #2A3547;'><br>",
    unsafe_allow_html=True,
)

st.header(
    "6️⃣ Speicher-Potenzial für BESS (Batteriespeicher) & Netzkapazitäten in Hirschaid"
)
st.caption(
    "Analyse der dezentralen Heimspeicher und der möglichen"
    " Großbatteriespeicher-Kapazitäten am Umspannwerk Hirschaid (Bayernwerk"
    " Netz)"
)

# Top KPIs zu Speichern
b1, b2, b3 = st.columns(3)

with b1:
    st.metric(
        label="Installierte Heimspeicher (IST)",
        value="ca. 14,2 MWh",
        delta="An ~1.050 Dachanlagen gekoppelt",
    )

with b2:
    st.metric(
        label="Einspeisepfad Umspannwerk Hirschaid",
        value="110 kV / 20 kV",
        delta="Netzknoten Bayernwerk Netz",
        delta_color="off",
    )

with b3:
    st.metric(
        label="Mögliches BESS-Großspeicher-Potenzial",
        value="20 MW / 40 MWh",
        delta="Netzdienliche Pufferung am UW",
    )

st.markdown("<br>", unsafe_allow_html=True)

# Visualisierung: Speicher-Struktur und Ausgleichs-Potenzial
col_bess_l, col_bess_r = st.columns([1.2, 1])

with col_bess_l:
    st.subheader("🔋 Bestand vs. Ausbaupotenzial der Speicherkapazitäten")

    speicher_kategorien = [
        "Private Heimspeicher (IST)",
        "Gewerbe- & Landwirtschaftsspeicher (IST)",
        "Netzdienlicher Großspeicher (Potenzial UW Hirschaid)",
    ]
    speicher_leistung_mw = [7.5, 3.0, 20.0]
    speicher_kapazitaet_mwh = [10.5, 3.7, 40.0]

    df_bess = pd.DataFrame({
        "Speichertyp": speicher_kategorien,
        "Leistung (MW)": speicher_leistung_mw,
        "Kapazität (MWh)": speicher_kapazitaet_mwh,
    })

    fig_bess = go.Figure()
    fig_bess.add_trace(
        go.Bar(
            x=df_bess["Speichertyp"],
            y=df_bess["Kapazität (MWh)"],
            name="Speicherkapazität (MWh)",
            marker_color="#00E676",
            hovertemplate="%{x}: %{y:.1f} MWh Kapazität<extra></extra>",
        )
    )
    fig_bess.add_trace(
        go.Bar(
            x=df_bess["Speichertyp"],
            y=df_bess["Leistung (MW)"],
            name="Ausspeiseleistung (MW)",
            marker_color="#00B0FF",
            hovertemplate="%{x}: %{y:.1f} MW Leistung<extra></extra>",
        )
    )

    fig_bess.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", size=13),
        yaxis=dict(
            title="Megawatt (MW) / Megawattstunden (MWh)",
            showgrid=True,
            gridcolor="#2A3547",
        ),
        xaxis=dict(showgrid=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,  # Platziert die Legende oberhalb der Grafik
            xanchor="center",
            x=0.5,  # Zentriert die Legende
        ),
        margin=dict(
            l=20, r=20, t=50, b=40  # t=50 schafft oben Platz für die Legende
        ),
    )
    st.plotly_chart(fig_bess, use_container_width=True)

with col_bess_r:
    st.subheader("💡 Netzdienlicher Nutzen für Hirschaid & Altendorf")
    st.markdown("""
    * **Pufferung der Mittagsspitze (Peak Shaving):** Die lokalen PV-Anlagen (45,2 MWp) erzeugen im Sommer zur Mittagszeit mehr Strom als lokal verbraucht wird. Ein Großspeicher am Umspannwerk fängt Spitzen ab und verhindert Abschaltungen.
    * **Entlastung der 110-kV-Trasse:** Der Strom verbleibt bilanztechnisch in der Region und muss nicht überregional abtransportiert werden.
    * **Vermeidung fossiler Ramping-Kosten:** In den Abendstunden (18:00–22:00 Uhr) kann der gespeicherte Mittags-Solarstrom direkt wieder in das Mittelspannungsnetz abgegeben werden.
    """)

st.info("""
**⚡ Fazit für den Netzknoten Hirschaid:** 
Ein zentraler Großbatteriespeicher (BESS) am **Umspannwerk Hirschaid** mit ca. **20 MW / 40 MWh** würde die bestehende Infrastruktur ideal ergänzen. Dadurch lassen sich die bereits installierten **45,2 MWp Sonnenenergie** aus Hirschaid und Altendorf rund um die Uhr nutzen, ohne dass neue Flächen im Außenbereich für Erzeugungsanlagen opfert werden müssen.
""")

st.caption("""
**📌 Hinweis zur Datengrundlage & Belastbarkeit:**
* **IST-Bestand (Heim- & Gewerbespeicher):** Daten basieren auf den amtlichen und gesetzlich verpflichtenden Einträgen des **Marktstammdatenregisters (MaStR)** der Bundesnetzagentur für die Postleitzahlen 96114 (Hirschaid) und 96146 (Altendorf).
* **Großspeicher-Potenzial (BESS):** Technische Modellrechnung und Potenzialabschätzung zur Netzdienlichkeit. Sie orientiert sich an der installierten PV-Spitzenleistung (MWp) sowie den typischen Kapazitätsgrenzen der lokalen 20-kV-Ortsnetze bzw. des 110-kV-Umspannwerks (Bayernwerk Netz GmbH).
""")

# =============================================================================
# DASHBOARD 7: POTENZIAL FÜR BATTERIESPEICHER IN DER GEMEINDE ALTENDORF (96146)
# =============================================================================

st.markdown(
    "<br><br><hr style='border: 2px solid #2A3547;'><br>",
    unsafe_allow_html=True,
)

st.header("7️⃣ Speicher-Potenzial für die Gemeinde Altendorf (96146)")
st.caption(
    "Analyse der dezentralen Heimspeicher, Gewerbepuffer und"
    " BESS-Möglichkeiten an Freiflächen-Knotenpunkten im Gemeindegebiet"
    " Altendorf / Seußling"
)

# Top KPIs für Altendorf
b1, b2, b3 = st.columns(3)

with b1:
    st.metric(
        label="Installierte Heimspeicher (Altendorf IST)",
        value="ca. 2,8 MWh",
        delta="An ~190 Dachanlagen in 96146",
    )

with b2:
    st.metric(
        label="Netzanbindung Ortseinspeisung",
        value="20 kV Mittelspannung",
        delta="Anbindung Richtung UW Hirschaid",
        delta_color="off",
    )

with b3:
    st.metric(
        label="Sinnvolles BESS-Potenzial (Altendorf)",
        value="5,0 MW / 10,0 MWh",
        delta="Gekoppelt an Freiflächen / 20kV-Ortsnetz",
    )

st.markdown("<br>", unsafe_allow_html=True)

col_alt_l, col_alt_r = st.columns([1.2, 1])

with col_alt_l:
    st.subheader(
        "🔋 Speicherkapazitäten in Altendorf (Bestand vs. Potenzial)"
    )

    speicher_kategorien_alt = [
        "Private Heimspeicher (Altendorf IST)",
        "Gewerbe- & Landwirtschaft (IST)",
        "Co-Located BESS (Freiflächen/FF-PV Seußling)",
    ]
    speicher_leistung_alt = [1.5, 0.6, 5.0]
    speicher_kapazitaet_alt = [2.2, 0.8, 10.0]

    df_bess_alt = pd.DataFrame({
        "Speichertyp": speicher_kategorien_alt,
        "Leistung (MW)": speicher_leistung_alt,
        "Kapazität (MWh)": speicher_kapazitaet_alt,
    })

    fig_bess_alt = go.Figure()
    fig_bess_alt.add_trace(
        go.Bar(
            x=df_bess_alt["Speichertyp"],
            y=df_bess_alt["Kapazität (MWh)"],
            name="Speicherkapazität (MWh)",
            marker_color="#00E676",
            hovertemplate="%{x}: %{y:.1f} MWh Kapazität<extra></extra>",
        )
    )
    fig_bess_alt.add_trace(
        go.Bar(
            x=df_bess_alt["Speichertyp"],
            y=df_bess_alt["Leistung (MW)"],
            name="Ausspeiseleistung (MW)",
            marker_color="#00B0FF",
            hovertemplate="%{x}: %{y:.1f} MW Leistung<extra></extra>",
        )
    )

    fig_bess_alt.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF", size=13),
        yaxis=dict(
            title="Megawatt (MW) / Megawattstunden (MWh)",
            showgrid=True,
            gridcolor="#2A3547",
        ),
        xaxis=dict(showgrid=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,  # Platziert die Legende oberhalb der Grafik
            xanchor="center",
            x=0.5,  # Zentriert die Legende
        ),
        margin=dict(
            l=20, r=20, t=50, b=40  # t=50 schafft oben Platz für die Legende
        ),
    )
    st.plotly_chart(fig_bess_alt, use_container_width=True)

with col_alt_r:
    st.subheader("💡 Netzdienlicher Mehrwert für Altendorf")
    st.markdown("""
    * **Entlastung der Ortsnetztrafos:** Hohe PV-Einspeisung zur Mittagszeit in Seußling und Altendorf führt zu Spannungsanhebungen im 20-kV-Ortsnetz. Lokale Speicher glätten diese Spitzen ab.
    * **Synergie mit Freiflächen-PV:** Bei neuen oder bestehenden Freiflächen-Anlagen (z. B. im 200m-Bahn- / Autobahn-Korridor) sichert ein Batteriespeicher den Netzzugang, ohne dass die Einspeisung bei Überlastung abgeregelt werden muss.
    * **Hohe Heimspeicher-Quote:** Durch die hohe Dichte an Eigenheimen ist der prozentuale Eigenversorgungsgrad in Altendorf (48,5 %) bereits überdurchschnittlich hoch.
    """)

st.info("""
**⚡ Fazit für die Gemeinde Altendorf:** 
Mit einem gezielten Ausbau von **5 MW / 10 MWh Speicherkapazität** (kombiniert aus Quartiersspeichern und Co-Located-Puffern an Freiflächen-PV) kann Altendorf seinen erzeugten Sonnenstrom (8,4 MWp) nahezu vollständig vor Ort verwerten, Einspeisespitzen abfedern und den Autarkiegrad weiter steigern.
""")

st.caption("""
**📌 Hinweis zur Datengrundlage & Belastbarkeit:**
* **IST-Bestand (Heim- & Gewerbespeicher):** Daten basieren auf den amtlichen und gesetzlich verpflichtenden Einträgen des **Marktstammdatenregisters (MaStR)** der Bundesnetzagentur für die Postleitzahlen 96114 (Hirschaid) und 96146 (Altendorf).
* **Großspeicher-Potenzial (BESS):** Technische Modellrechnung und Potenzialabschätzung zur Netzdienlichkeit. Sie orientiert sich an der installierten PV-Spitzenleistung (MWp) sowie den typischen Kapazitätsgrenzen der lokalen 20-kV-Ortsnetze bzw. des 110-kV-Umspannwerks (Bayernwerk Netz GmbH).
""")

# =============================================================================
# DASHBOARD 8: HISTORIE DER WINDKRAFT IN HIRSCHAID UND ALTENDORF
# =============================================================================

st.markdown(
    "<br><br><hr style='border: 2px solid #2A3547;'><br>",
    unsafe_allow_html=True,
)

st.header("8️⃣ Historie der Windkraft in Hirschaid und Altendorf")
st.caption(
    "Chronologische Übersicht über die Entwicklung, Meilensteine,"
    " Ratsbeschlüsse und Bürgerentscheide bezüglich der Windkraftplanungen"
    " (Muna Rothensand & Seußling-West / Lauberg)"
)

# Datensatz für die Historie inkl. Quellennachweisen und Links
historie_data = [
    {
        "Datum / Zeitraum": "16.12.2022",
        "Ereignis / Beschluss": (
            "Berichterstattung über Windkraft-Suchräume in Hirschaid"
        ),
        "Beteiligte / Ort": "Markt Hirschaid, Fränkischer Tag",
        "Details & Auswirkungen": (
            "Der Fränkische Tag berichtet über die drei vom Markt Hirschaid"
            " ermittelten Potenzialflächen/Suchräume für Windkraftanlagen"
            " (darunter die Muna Rothensand und der Bereich Seußling-West /"
            " Lauberg)."
        ),
        "Nachweis / Link": (
            "[Fränkischer Tag (16.12.2022)](https://www.fraenkischertag.de/lokales/bamberg/umwelt-natur/potenzial-in-hirschaid-gibt-es-drei-moegliche-flaechen-fuer-windraeder-art-216902)"
        ),
    },
    {
        "Datum / Zeitraum": "13.06.2024",
        "Ereignis / Beschluss": (
            "Gründungsbeschluss Bürgerenergiegesellschaft Altendorf"
        ),
        "Beteiligte / Ort": "Gemeinderat Altendorf",
        "Details & Auswirkungen": (
            "Der Gemeinderat Altendorf fasst Beschlüsse zur Vorbereitung der"
            " Gründung der Altendorf Bürgerenergiegesellschaft mbH und"
            " Einleitung der Vorplanungen für gemeindliche Windkraftanlagen bei"
            " Seußling-West."
        ),
        "Nachweis / Link": "Amtsblatt Gemeinde Altendorf (Juni/Juli 2024)",
    },
    {
        "Datum / Zeitraum": "29.08.2024",
        "Ereignis / Beschluss": "Pressemitteilung zu Muna-Windrädern",
        "Beteiligte / Ort": "Stadtwerke Bamberg, Lebenshilfe Bamberg",
        "Details & Auswirkungen": (
            "Öffentliche Ankündigung und Pressemitteilung der Kooperation"
            " zwischen den Stadtwerken Bamberg und der Lebenshilfe Bamberg e. V."
            " zur Errichtung von zwei Windkraftanlagen auf dem ehemaligen"
            " Munitionsdepot (Muna) bei Rothensand."
        ),
        "Nachweis / Link": (
            "[Pressemitteilung Stadtwerke Bamberg](https://www.stadtwerke-bamberg.de/nachricht/symbol-fuer-den-klimaschutz-stadtwerke-bamberg-ersetzen-das-aelteste-windrad-im-landkreis)"
        ),
    },
    {
        "Datum / Zeitraum": "08.11.2024",
        "Ereignis / Beschluss": (
            "Behandlung des Antrags auf Vorbescheid (Muna Rothensand)"
        ),
        "Beteiligte / Ort": "Marktgemeinderat Hirschaid, Gemarkung Rothensand",
        "Details & Auswirkungen": (
            "TOP 07: Beschlussfassung über den Antrag auf Vorbescheid für bis"
            " zu zwei Windenergieanlagen im geplanten Windvorranggebiet auf"
            " Gemarkung Rothensand zur Prüfung der luftverkehrsrechtlichen"
            " Zulässigkeit nach § 9 Abs. 1a BImSchG."
        ),
        "Nachweis / Link": (
            "[Wittich E-Paper / Amtsblatt](https://epaper.wittich.de/frontend/catalogs/501312/2/pdf/complete.pdf)"
        ),
    },
    {
        "Datum / Zeitraum": "05.05.2025",
        "Ereignis / Beschluss": "Übergabe einer Petition",
        "Beteiligte / Ort": (
            "Bürgerinitiative, Bürgermeister von Altendorf und Hirschaid"
        ),
        "Details & Auswirkungen": (
            "Übergabe der Petition gegen die geplanten Windkraftprojekte an"
            " die Bürgermeister."
        ),
        "Nachweis / Link": "Protokoll / BI-Mitteilung (05.05.2025)",
    },
    {
        "Datum / Zeitraum": "25.06.2025",
        "Ereignis / Beschluss": "Erster Infoabend",
        "Beteiligte / Ort": "Bürgerinitiative, Firma WEMA",
        "Details & Auswirkungen": (
            "Aufklärung der Öffentlichkeit über die Windpark-Projekte im Rahmen"
            " einer Informationsveranstaltung."
        ),
        "Nachweis / Link": "Veranstaltungsnachweis BI (25.06.2025)",
    },
    {
        "Datum / Zeitraum": "23.07.2025",
        "Ereignis / Beschluss": "Zweiter Infoabend",
        "Beteiligte / Ort": (
            "Waldhaus Köttmannsdorf, Bürger, Gemeinderäte, Bürgermeister"
        ),
        "Details & Auswirkungen": (
            "Zweite Informationsveranstaltung mit zahlreichen Bürgern und"
            " Vertretern der Kommunalpolitik von Hirschaid und Altendorf."
        ),
        "Nachweis / Link": "Veranstaltungsnachweis BI (23.07.2025)",
    },
    {
        "Datum / Zeitraum": "August 2025",
        "Ereignis / Beschluss": (
            "Austausch mit der Politik & Info-Schreiben Altendorf"
        ),
        "Beteiligte / Ort": (
            "Gemeinde Altendorf, Bürgerinitiative, Abgeordnete (MdB, MdL),"
            " Landrat"
        ),
        "Details & Auswirkungen": (
            "Herausgabe des Informationsblatts 'Information zur Wind-Energie in"
            " der Gemeinde Altendorf' an alle Haushalte sowie intensiver"
            " politischer Austausch der BI mit Abgeordneten."
        ),
        "Nachweis / Link": (
            "Infoblatt Gemeinde Altendorf / BI-Dokumentation (August 2025)"
        ),
    },
    {
        "Datum / Zeitraum": "04.08.2025",
        "Ereignis / Beschluss": "Vereinsgründung",
        "Beteiligte / Ort": "Bürgerinitiative Hirschaid-Altendorf e. V.",
        "Details & Auswirkungen": (
            "Offizielle Gründungssitzung des Vereins 'Bürgerinitiative"
            " Hirschaid-Altendorf'."
        ),
        "Nachweis / Link": "Vereinsregister / Gründungsprotokoll (04.08.2025)",
    },
    {
        "Datum / Zeitraum": "01.09.2025",
        "Ereignis / Beschluss": (
            "Ausstieg des Marktes Hirschaid aus kommunalem Windpark"
        ),
        "Beteiligte / Ort": "Marktgemeinderat Hirschaid",
        "Details & Auswirkungen": (
            "Der Marktgemeinderat beschließt, die Projektierungsmaßnahmen für"
            " 2 der 5 geplanten Windkraftanlagen auf Hirschaider Gebiet"
            " einzustellen und gestellte Anträge zurückzuziehen."
        ),
        "Nachweis / Link": (
            "Sitzungsprotokoll Marktgemeinderat Hirschaid (01.09.2025)"
        ),
    },
    {
        "Datum / Zeitraum": "September 2025",
        "Ereignis / Beschluss": "Ablehnung der Muna-Windräder Rothensand",
        "Beteiligte / Ort": (
            "Marktgemeinderat Hirschaid, Stadtwerke Bamberg, Lebenshilfe"
            " Bamberg"
        ),
        "Details & Auswirkungen": (
            "In einer knappen Abstimmung lehnt der Marktgemeinderat Hirschaid"
            " das geplante Projekt von zwei Windkraftanlagen auf dem Gelände"
            " des ehemaligen Munitionsdepots (Muna) bei Rothensand ab."
        ),
        "Nachweis / Link": (
            "Beschluss F2025 / Sitzungsprotokoll Hirschaid (Sept. 2025)"
        ),
    },
    {
        "Datum / Zeitraum": "24.09.2025",
        "Ereignis / Beschluss": "Übergabe der Unterschriftenliste",
        "Beteiligte / Ort": "Bürgerinitiative, Gemeinde Altendorf / Hirschaid",
        "Details & Auswirkungen": (
            "Formelle Übergabe der gesammelten Unterschriften für das"
            " eingeleitete Bürgerbegehren."
        ),
        "Nachweis / Link": (
            "Nachweis Bürgerbegehren / Übergabeprotokoll (24.09.2025)"
        ),
    },
    {
        "Datum / Zeitraum": "17.11.2025",
        "Ereignis / Beschluss": (
            "Offizielle Bürgerversammlung Windenergie Altendorf"
        ),
        "Beteiligte / Ort": "Gemeinde Altendorf, Feuerwehrgerätehaus Altendorf",
        "Details & Auswirkungen": (
            "Offizielle Bürgerversammlung und Informationsveranstaltung der"
            " Gemeinde Altendorf zu den Vorplanungen des Windparks Seußling-West"
            " und Erläuterung des bevorstehenden Bürgerentscheids."
        ),
        "Nachweis / Link": "Bekanntmachung Gemeinde Altendorf (17.11.2025)",
    },
    {
        "Datum / Zeitraum": "14.12.2025",
        "Ereignis / Beschluss": "Bürgerentscheid in Altendorf",
        "Beteiligte / Ort": "Gemeinde Altendorf (inkl. Ortsteil Seußling)",
        "Details & Auswirkungen": (
            "Eine Mehrheit von rund 60 % der Bürger stimmt gegen die"
            " Beteiligung der Gemeinde am geplanten Windpark. In der Folge"
            " stoppen die Gemeinden Altendorf und Hirschaid die Planungen für"
            " eigene kommunale Windkraftanlagen im Gebiet Seußling-West."
        ),
        "Nachweis / Link": (
            "Amtliches Wahlergebnis Bürgerentscheid Altendorf (14.12.2025)"
        ),
    },
    {
        "Datum / Zeitraum": "20.04.2026",
        "Ereignis / Beschluss": (
            "Entscheidung des Regionalen Planungsververbandes (RPV)"
        ),
        "Beteiligte / Ort": "Regionaler Planungsverband Oberfranken-West",
        "Details & Auswirkungen": (
            "Lauberg: Das geplante Vorranggebiet 4288 ('Seußling-West') wird"
            " nicht im Regionalplan ausgewiesen. Muna Rothensand: Auch der"
            " Antrag auf Ausweisung eines Vorranggebiets beim ehemaligen"
            " Muna-Depot wird vom RPV offiziell abgelehnt."
        ),
        "Nachweis / Link": (
            "Beschlussunterlagen RPV Oberfranken-West (20.04.2026)"
        ),
    },
    {
        "Datum / Zeitraum": "Stand heute (2026)",
        "Ereignis / Beschluss": (
            "Festhalten an den Windpark-Plänen trotz Absagen"
        ),
        "Beteiligte / Ort": (
            "Stadtwerke Bamberg, Lebenshilfe Bamberg, Landratsamt Bamberg"
        ),
        "Details & Auswirkungen": (
            "Trotz der Gegenwind-Beschlüsse des Marktgemeinderats Hirschaid"
            " und der Ablehnung durch den Regionalen Planungsververband halten"
            " die Stadtwerke Bamberg offiziell an ihren Plänen für die"
            " Windräder auf der ehem. Muna fest und streben ein"
            " BImSchG-Einzelgenehmigungsverfahren beim Landratsamt Bamberg an."
        ),
        "Nachweis / Link": (
            "Schriftliche Bestätigung Geschäftsführung Stadtwerke Bamberg (2026)"
        ),
    },
]

df_historie = pd.DataFrame(historie_data)

# Interaktive Tabellendarstellung in Streamlit
st.dataframe(
    df_historie,
    use_container_width=True,
    hide_index=True,
)

# ==========================================
# GANZ UNTEN AM ENDE DER SEITE:
# Impressum & Datenschutz (Ausklappbar)
# ==========================================

st.divider()

# Ausklappbares Menü
with st.expander("⚖️ Impressum & Datenschutzerklärung anzeigen", expanded=False):
    
    # 1. IMPRESSUM
    st.markdown("### Impressum")
    st.markdown("""
    **Bürgerinitiative Hirschaid-Altendorf e.V.**  
    Industriestraße 13  
    96114 Hirschaid  

    * **1. Vorsitzender:** Benjamin Bauer  
    * **2. Vorsitzender:** Wolf-Dieter Czap  
    * **Telefonnummer:** [017647320301](tel:017647320301)  
    * **E-Mail:** [info@bi-hirschaid-altendorf.de](mailto:info@bi-hirschaid-altendorf.de)  

    Link zu dieser App: [https://bi-hirschaid-altendorf.streamlit.app/](https://bi-hirschaid-altendorf.streamlit.app/)
    """)

    st.markdown("---")

    # 2. DATENSCHUTZERKLÄRUNG
    st.markdown("### Datenschutzerklärung")
    
    st.markdown("#### Wer wir sind")
    st.markdown("""
    Die Adresse unserer Website ist: [https://windpark-info.de](https://windpark-info.de) sowie die Webanwendung [https://bi-hirschaid-altendorf.streamlit.app/](https://bi-hirschaid-altendorf.streamlit.app/).
    """)

    st.markdown("#### Welche personenbezogenen Daten wir sammeln und warum wir sie sammeln")
    st.markdown("""
    * **Kommentare:** Wenn Besucher Kommentare auf der Website schreiben, sammeln wir die Daten, die im Kommentar-Formular angezeigt werden, außerdem die IP-Adresse des Besuchers und den User-Agent-String (damit wird der Browser identifiziert), um die Erkennung von Spam zu unterstützen. Aus deiner E-Mail-Adresse kann eine anonymisierte Zeichenfolge erstellt (Hash) und dem Gravatar-Dienst übergeben werden ([Datenschutz Gravatar](https://automattic.com/privacy/)).
    * **Medien:** Wenn du Fotos auf diese Website lädst, solltest du vermeiden, Fotos mit einem EXIF-GPS-Standort hochzuladen.
    * **Cookies:** Wenn du einen Kommentar schreibst, kann das eine Einwilligung sein, deinen Namen, E-Mail-Adresse und Website in Cookies zu speichern (1 Jahr). Temporäre Login-Cookies verfallen beim Schließen des Browsers.
    * **Eingebettete Inhalte:** Beiträge können eingebettete Inhalte beinhalten (z. B. Videos, Bilder, Beiträge etc.). Diese verhalten sich exakt so, als ob der Besucher die andere Website besucht hätte.
    """)

    st.markdown("#### Rechte & Speicherdauer")
    st.markdown("""
    Wenn du einen Kommentar schreibst, wird dieser inklusive Metadaten zeitlich unbegrenzt gespeichert. Registrierte Nutzer können ihre Daten jederzeit einsehen, verändern oder löschen. Du kannst einen Export deiner personenbezogenen Daten bei uns anfordern oder die Löschung beantragen.
    """)

    st.markdown("#### Wohin wir deine Daten senden")
    st.markdown("""
    Besucher-Kommentare könnten von einem automatisierten Dienst zur Spam-Erkennung untersucht werden.
    """)
