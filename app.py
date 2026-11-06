from pathlib import Path
import sys
import base64
import html
import re
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import APP_TITLE, APP_SUBTITLE, PAGE_NAMES
from utils.data_loader import load_data, quality_summary
from utils.calculations import calculate_kpis, add_maintenance_group
from components.login import require_login
from components.extra_pages import render as render_extra_page
from components.charts import style, bar, line, donut, pareto, PALETTE

st.set_page_config(page_title=APP_TITLE, page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

st.session_state.setdefault("ama_theme", "dark")

def inject_theme_css():
    # Streamlit-compatible CSS injection: extract the CSS body and place it
    # inside one style element rendered by st.markdown.
    css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
    css = re.sub(r"</?style\b[^>]*>", "", css, flags=re.IGNORECASE)
    if st.session_state.get("ama_theme", "dark") == "light":
        variables = ":root{--bg:#edf3f8;--panel:#ffffff;--panel2:#f7fbff;--text:#12263d;--muted:#60758a;--line:rgba(36,74,108,.16);--accent:#087f9b;--accent2:#e28c20;--shadow:0 16px 42px rgba(20,49,76,.08); }"
    else:
        variables = ":root{--bg:#030b1d;--panel:#071a38;--panel2:#0b2450;--text:#f3f8ff;--muted:#9db7df;--line:rgba(74,153,255,.28);--accent:#28baff;--accent2:#8b5cf6;--shadow:0 18px 48px rgba(0,5,22,.42); }"
    st.markdown("<style>\n" + css + "\n" + variables + "\n</style>", unsafe_allow_html=True)

inject_theme_css()

@st.cache_data(show_spinner="Chargement et préparation des données...")
def get_data():
    return load_data()

if not require_login():
    st.stop()

try:
    df = get_data()
except Exception as exc:
    st.error(f"Impossible de charger le CSV : {exc}")
    st.info("Vérifie que data/ait_laraik_islam.csv est présent dans le dossier du projet.")
    st.stop()

# Sidebar navigation and global filters
with st.sidebar:
    logo_b64 = base64.b64encode((ROOT / "assets" / "ama_logo.svg").read_bytes()).decode("ascii")
    st.markdown(f"<div class='sidebar-brand'><img src='data:image/svg+xml;base64,{logo_b64}'/><div class='eyebrow'>AERONEX · FLEET INTELLIGENCE</div></div>", unsafe_allow_html=True)
    lang_options = ["Français", "English", "العربية", "Español"]
    selected_lang = st.selectbox("LANGUAGE / LANGUE", lang_options,
        index={"fr":0,"en":1,"ar":2}.get(st.session_state.get("ama_language","fr"),0), key="sidebar_language")
    new_lang = {"Français":"fr","English":"en","العربية":"ar","Español":"es"}[selected_lang]
    if new_lang != st.session_state.get("ama_language","fr"):
        st.session_state.ama_language = new_lang
        st.rerun()
    theme_label = st.selectbox("APPARENCE", ["Dark cockpit", "Light hangar"], index=0 if st.session_state.ama_theme == "dark" else 1, key="app_theme_choice")
    selected_theme = "dark" if theme_label == "Dark cockpit" else "light"
    if selected_theme != st.session_state.ama_theme:
        st.session_state.ama_theme = selected_theme
        st.rerun()
    lang = st.session_state.get("ama_language", "fr")
    if lang == "ar":
        st.markdown("<style>.main .block-container{direction:rtl;text-align:right}.stSidebar{direction:rtl;text-align:right}</style>", unsafe_allow_html=True)
    page_labels = {
      "fr": PAGE_NAMES,
      "en": ["Overview", "Fleet", "Daily Operations", "Reliability", "ATA Analysis", "Workshop & Costs", "Downtime & Delays", "Alerts", "Work Orders", "Aircraft profiles", "Maintenance planning", "Operations map", "AERONEX AI", "Parts inventory", "Technician management", "Smart notifications", "PDF reports", "Reports & recommendations"],
      "ar": ["نظرة عامة", "الأسطول", "العمليات اليومية", "الموثوقية", "تحليل ATA", "الورشة والتكاليف", "التوقف والتأخير", "التنبيهات", "أوامر العمل", "ملفات الطائرات", "تخطيط الصيانة", "خريطة العمليات", "AERONEX AI", "مخزون القطع", "إدارة الفنيين", "الإشعارات الذكية", "تقارير PDF", "التقارير والتوصيات"],
      "es": ["Resumen", "Flota", "Operaciones diarias", "Fiabilidad", "Análisis ATA", "Taller y costes", "Inmovilización y retrasos", "Alertas", "Órdenes de trabajo", "Fichas de aeronaves", "Planificación de mantenimiento", "Mapa de operaciones", "AERONEX AI", "Inventario de piezas", "Gestión de técnicos", "Notificaciones inteligentes", "Informes PDF", "Informes y recomendaciones"]
    }
    st.markdown("### " + {"fr":"Navigation", "en":"Navigation", "ar":"التنقل"}[lang])
    requested_page = st.session_state.pop("requested_page", None)
    requested_index = PAGE_NAMES.index(requested_page) if requested_page in PAGE_NAMES else 0
    if requested_page in PAGE_NAMES:
        # Synchronise the radio value as well as its index so shortcut buttons
        # navigate correctly even after the widget has already been created.
        st.session_state["module_nav"] = page_labels[lang][requested_index]
    selected_label = st.radio("MODULES", page_labels[lang], index=requested_index,
                              label_visibility="visible", key="module_nav")
    page = dict(zip(page_labels[lang], PAGE_NAMES))[selected_label]
    st.divider()
    st.markdown("### Filtres globaux")
    min_date = df.open_datetime.min().date()
    max_date = df.open_datetime.max().date()
    date_range = st.date_input("Période d’ouverture", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    stations = st.multiselect("Escales", sorted(df.station.unique()), default=sorted(df.station.unique()))
    aircraft_types = st.multiselect("Type d’avion", sorted(df.aircraft_type.unique()), default=sorted(df.aircraft_type.unique()))
    maint_types = st.multiselect("Type de maintenance", sorted(df.maintenance_type.unique()), default=sorted(df.maintenance_type.unique()))
    priorities = st.multiselect("Priorité", sorted(df.priority.unique()), default=sorted(df.priority.unique()))
    st.divider()
    st.caption(f"{len(df):,} lignes chargées · {len(df.columns)} colonnes".replace(",", " "))
    if st.button("Déconnexion", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

filtered = df.copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = date_range
    filtered = filtered[filtered.open_datetime.dt.date.between(start, end)]
if stations: filtered = filtered[filtered.station.isin(stations)]
else: filtered = filtered.iloc[0:0]
if aircraft_types: filtered = filtered[filtered.aircraft_type.isin(aircraft_types)]
else: filtered = filtered.iloc[0:0]
if maint_types: filtered = filtered[filtered.maintenance_type.isin(maint_types)]
else: filtered = filtered.iloc[0:0]
if priorities: filtered = filtered[filtered.priority.isin(priorities)]
else: filtered = filtered.iloc[0:0]
filtered = add_maintenance_group(filtered)
k = calculate_kpis(filtered)

plane_svg = (ROOT / "assets" / "aircraft_silhouette.svg").read_text(encoding="utf-8")
# Chaque famille de modules reçoit un visuel aéronautique photographique dédié.
# Les images sont locales au projet : l'application fonctionne aussi hors ligne.
page_visuals = {
    "Vue d’ensemble": "hangar_hero.jpg",
    "Flotte": "aircraft_hangar.jpg",
    "Activité quotidienne": "maintenance_technician.jpg",
    "Fiabilité": "engine_inspection.jpg",
    "Analyse ATA": "engine_detail.jpg",
    "Atelier & coûts": "engine_detail.jpg",
    "Immobilisation & retards": "aircraft_hangar.jpg",
    "Alertes": "maintenance_technician.jpg",
    "Ordres de travail": "engine_inspection.jpg",
    "Fiches avions interactives": "aircraft_hangar.jpg",
    "Planning de maintenance": "maintenance_technician.jpg",
    "Carte mondiale": "hangar_hero.jpg",
    "AERONEX AI": "engine_detail.jpg",
    "Stocks de pièces": "engine_inspection.jpg",
    "Gestion des techniciens": "maintenance_technician.jpg",
    "Notifications intelligentes": "aircraft_hangar.jpg",
    "Rapports PDF professionnels": "hangar_hero.jpg",
    "Rapports & recommandations": "engine_detail.jpg",
}
hero_file = page_visuals.get(page, "hangar_hero.jpg")
hero_b64 = base64.b64encode((ROOT / "assets" / hero_file).read_bytes()).decode("ascii")
st.markdown(f"""
<div class="hero-banner" style="background-image:linear-gradient(90deg,rgba(4,16,30,.97) 0%,rgba(5,22,39,.86) 52%,rgba(5,22,39,.48) 100%),url('data:image/jpeg;base64,{hero_b64}');background-size:cover;background-position:center;">
  <div class="hero-code">AERONEX / AIRCRAFT MAINTENANCE INTELLIGENCE</div>
  <h1>{page}</h1>
  <p>{APP_SUBTITLE} · Une lecture technique des performances de maintenance de la flotte.</p>
  <div class="hero-plane">{plane_svg}</div>
</div>
""", unsafe_allow_html=True)
nav_home, nav_hint = st.columns([1, 5])
with nav_home:
    if page != "Vue d’ensemble" and st.button("← Dashboard", key="return_dashboard", use_container_width=True):
        st.session_state["requested_page"] = "Vue d’ensemble"
        st.rerun()
with nav_hint:
    if page != "Vue d’ensemble":
        st.caption("Navigation rapide · Retour au tableau de bord")
st.markdown(
    f"<div class='data-ribbon'><span class='data-chip'>SOURCE RÉELLE · <strong>ait_laraik_islam.csv</strong></span>"
    f"<span class='data-chip'>PÉRIODE · <strong>{date_range[0] if isinstance(date_range,(tuple,list)) else min_date} → {date_range[1] if isinstance(date_range,(tuple,list)) else max_date}</strong></span>"
    f"<span class='data-chip'>ÉCHANTILLON FILTRÉ · <strong>{len(filtered):,} lignes</strong></span>"
    f"<span class='data-chip'>CALCULS · <strong>KPI & agrégations Python</strong></span></div>",
    unsafe_allow_html=True
)

if filtered.empty:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés. Modifie les filtres dans la barre latérale.")
    st.stop()

# Common KPI row
def kpi_card(label, value, note, icon):
    st.markdown(f"<div class='kpi'><div class='kpi-label'>{icon} &nbsp;{label}</div><div class='kpi-value'>{value}</div><div class='kpi-note'>{note}</div></div>", unsafe_allow_html=True)

def money(x): return f"${x:,.0f}"
def no(x): return f"{x:,.0f}".replace(",", " ")

def photo_card(filename, title, subtitle):
    image_path = ROOT / "assets" / filename
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return (
        f"<div class='photo-card'><img src='data:image/jpeg;base64,{encoded}' alt='{html.escape(title)}'/>"
        f"<div class='photo-overlay'><div class='photo-title'>{html.escape(title)}</div>"
        f"<div class='photo-subtitle'>{html.escape(subtitle)}</div></div></div>"
    )

if page == "Vue d’ensemble":
    # Cockpit principal : indicateurs et visuels calculés à partir du CSV.
    search_col, info_col = st.columns([2.2, 1])
    with search_col:
        overview_search = st.text_input(
            "⌕  Rechercher un avion, une immatriculation ou un ordre de travail",
            placeholder="Ex. CN-RAK, B737-800, WO...",
            key="overview_global_search"
        )
    with info_col:
        st.markdown(
            f"<div class='cockpit-date'><span>● DONNÉES CHARGÉES</span><strong>{len(filtered):,} enregistrements</strong></div>",
            unsafe_allow_html=True
        )

    if overview_search:
        search_mask = filtered.astype(str).apply(
            lambda col: col.str.contains(overview_search, case=False, na=False)
        ).any(axis=1)
        search_results = filtered[search_mask].head(8)
        st.markdown(f"**{len(filtered[search_mask]):,} résultat(s) trouvé(s)**")
        if not search_results.empty:
            st.dataframe(
                search_results[["work_order_id", "aircraft_reg", "aircraft_type", "station",
                                "ata_system", "priority", "status"]],
                use_container_width=True, hide_index=True
            )

    # Première rangée : flotte, réseau des escales et alertes.
    fleet_count = filtered["aircraft_reg"].nunique()
    fleet_hero_b64 = base64.b64encode((ROOT / "assets" / "aircraft_hangar.jpg").read_bytes()).decode("ascii")
    aog_df = filtered[(filtered.maintenance_type.eq("AOG")) | (filtered.priority.eq("AOG"))]
    urgent_df = filtered[filtered.priority.astype(str).str.lower().eq("high")]
    open_df = filtered[filtered.status.astype(str).str.lower().eq("open")]

    top_left, top_map, top_alerts = st.columns([1.02, 1.62, 0.98], gap="small")
    with top_left:
        st.markdown(
            f"""
            <div class="cockpit-fleet-card">
              <div class="cockpit-card-heading"><span>✈</span> Flotte suivie</div>
              <div class="cockpit-fleet-number">{fleet_count}</div>
              <div class="cockpit-fleet-caption">Immatriculations dans les données filtrées</div>
              <div class="cockpit-fleet-photo" style="background-image:linear-gradient(0deg,rgba(5,17,32,.65),transparent 55%),url('data:image/jpeg;base64,{fleet_hero_b64}')"></div>
              <div class="cockpit-fleet-foot">
                <span><b>{no(k['orders'])}</b> ordres</span>
                <span><b>{no(open_df['work_order_id'].nunique())}</b> ouverts</span>
              </div>
            </div>
            """, unsafe_allow_html=True
        )
        if st.button("Voir la flotte  →", key="overview_to_fleet", use_container_width=True):
            st.session_state["requested_page"] = "Flotte"
            st.rerun()

    with top_map:
        st.markdown("<div class='cockpit-panel-heading'>⌖  Réseau des opérations par escale</div>", unsafe_allow_html=True)
        # Les coordonnées représentent les aéroports du dataset, pas des positions avion en temps réel.
        station_coordinates = {
            "CMN": (33.3675, -7.5898), "RAK": (31.6069, -8.0363),
            "TNG": (35.7269, -5.9169), "AGA": (30.3250, -9.4131),
            "FEZ": (33.9273, -4.9779), "OUD": (34.7872, -1.9239)
        }
        station_counts = filtered.groupby("station").agg(
            orders=("work_order_id", "nunique"),
            aircraft=("aircraft_reg", "nunique")
        ).reset_index()
        station_counts = station_counts[station_counts.station.isin(station_coordinates)]
        map_fig = go.Figure()
        if not station_counts.empty:
            map_fig.add_trace(go.Scattergeo(
                lon=[station_coordinates[x][1] for x in station_counts.station],
                lat=[station_coordinates[x][0] for x in station_counts.station],
                text=[f"{r.station}<br>{int(r.orders)} ordres · {int(r.aircraft)} avions"
                      for r in station_counts.itertuples()],
                mode="markers+text",
                textposition="top center",
                marker=dict(
                    size=[max(12, min(29, 10 + (int(x) ** 0.5))) for x in station_counts.orders],
                    color="#36a9ff", opacity=.92,
                    line=dict(width=1.5, color="#d8f4ff"),
                    sizemode="diameter"
                ),
                hovertemplate="%{text}<extra></extra>",
                name="Escales"
            ))
        # Focus the overview map on Morocco. The former Africa-wide scope
        # distorted the visible region and left Morocco poorly framed.
        map_fig.update_geos(
            projection_type="mercator", projection_scale=3.8,
            center=dict(lat=32.1, lon=-6.4),
            lonaxis_range=[-14.2, -0.7], lataxis_range=[27.0, 36.8],
            showland=True, landcolor="#142d49",
            showocean=True, oceancolor="#071a30",
            showcountries=False, countrycolor="rgba(140,180,210,.32)",
            showcoastlines=True, coastlinecolor="rgba(45,175,255,.65)",
            showframe=False, bgcolor="rgba(0,0,0,0)"
        )
        map_fig.update_layout(
            height=285, margin=dict(l=0, r=0, t=5, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#dcecff", size=10),
            showlegend=False
        )
        st.plotly_chart(map_fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Activité de maintenance par aéroport · aucune position ou trajectoire de vol n’est simulée.")

    with top_alerts:
        st.markdown("<div class='cockpit-panel-heading'>⚠  Alertes & priorités</div>", unsafe_allow_html=True)
        st.markdown(
            f"""<div class="cockpit-alert critical"><span>!</span><div><b>{len(aog_df)}</b><strong>Événement(s) AOG</strong><small>Type ou priorité AOG</small></div></div>
            <div class="cockpit-alert warning"><span>⌁</span><div><b>{len(urgent_df)}</b><strong>Priorité élevée</strong><small>Ordres classés High</small></div></div>
            <div class="cockpit-alert success"><span>✓</span><div><b>{len(open_df)}</b><strong>Ordres ouverts</strong><small>À suivre dans l’atelier</small></div></div>""",
            unsafe_allow_html=True
        )
        if st.button("Centre des alertes  →", key="overview_to_alerts", use_container_width=True):
            st.session_state["requested_page"] = "Alertes"
            st.rerun()

    # Deuxième rangée : comparaison de flotte, journal et raccourcis.
    fleet_panel, journal_panel, actions_panel = st.columns([1.12, 1.48, 0.9], gap="small")
    with fleet_panel:
        st.markdown("<div class='cockpit-panel-heading'>▣  Profil & comparaison de la flotte</div>", unsafe_allow_html=True)
        by_type = filtered.groupby("aircraft_type", as_index=False).agg(
            aircraft=("aircraft_reg", "nunique"),
            orders=("work_order_id", "nunique"),
            cost=("total_cost_usd", "sum")
        ).sort_values("orders", ascending=False)
        if not by_type.empty:
            for _, rec in by_type.head(4).iterrows():
                share = 100 * rec["orders"] / max(by_type["orders"].max(), 1)
                st.markdown(
                    f"""<div class="fleet-compare-row">
                    <div><strong>{html.escape(str(rec['aircraft_type']))}</strong><small>{int(rec['aircraft'])} avion(s) · {int(rec['orders'])} ordres</small></div>
                    <div class="fleet-compare-track"><i style="width:{share:.1f}%"></i></div>
                    </div>""", unsafe_allow_html=True
                )
        st.markdown(
            f"<div class='fleet-compare-total'><span>Coût total observé</span><b>{money(k['cost'])}</b></div>",
            unsafe_allow_html=True
        )
        if st.button("Comparer les avions  →", key="overview_compare", use_container_width=True):
            st.session_state["requested_page"] = "Flotte"
            st.rerun()

    with journal_panel:
        st.markdown("<div class='cockpit-panel-heading'>▣  Journal récent de maintenance</div>", unsafe_allow_html=True)
        recent = filtered.sort_values("open_datetime", ascending=False).head(4)
        for _, rec in recent.iterrows():
            status_class = "done" if str(rec["status"]).lower() != "open" else "pending"
            opened = rec["open_datetime"].strftime("%d/%m · %H:%M") if pd.notna(rec["open_datetime"]) else "—"
            st.markdown(
                f"""<div class="cockpit-timeline-row">
                <span class="timeline-dot {status_class}"></span>
                <div><strong>{html.escape(str(rec['aircraft_reg']))} · {html.escape(str(rec['ata_system']))}</strong>
                <small>{opened} · {html.escape(str(rec['work_order_id']))} · {html.escape(str(rec['priority']))}</small></div>
                </div>""", unsafe_allow_html=True
            )
        if st.button("Ouvrir le journal complet  →", key="overview_daily", use_container_width=True):
            st.session_state["requested_page"] = "Activité quotidienne"
            st.rerun()

    with actions_panel:
        st.markdown("<div class='cockpit-panel-heading'>✦  Actions rapides</div>", unsafe_allow_html=True)
        quick_actions = [
            ("＋", "Ordres de travail", "Ordres de travail"),
            ("▦", "Planification", "Planning de maintenance"),
            ("⌖", "Carte des escales", "Carte mondiale"),
            ("▤", "Rapports", "Rapports PDF professionnels")
        ]
        for idx, (symbol, label, target) in enumerate(quick_actions):
            st.markdown(
                f"<div class='quick-action-tile'><span>{symbol}</span><b>{label}</b></div>",
                unsafe_allow_html=True
            )
            if st.button(f"Ouvrir {label}", key=f"quick_action_{idx}", use_container_width=True):
                st.session_state["requested_page"] = target
                st.rerun()

    st.markdown("### Indicateurs de performance")
    cols = st.columns(4)
    cards = [
        ("Ordres de travail", no(k['orders']), "Ordres distincts", "▣"),
        ("Coût total", money(k['cost']), "Pièces + main-d’œuvre", "$"),
        ("Immobilisation", f"{k['downtime']:,.1f} h", "Heures déclarées", "◷"),
        ("Événements AOG", no(k['aog']), "Type ou priorité AOG", "⚠"),
        ("Retards de vol", f"{no(k['delay'])} min", "Retards associés aux ordres", "↗"),
        ("Défauts répétitifs", f"{k['repeat_rate']:.1f}%", "Part des ordres marqués Yes", "⟳"),
        ("Ordres ouverts", no(k['open']), "Statut Open", "◉"),
        ("Coût pièces", money(k['parts']), "Somme parts_cost_usd", "⚙")
    ]
    for i, item in enumerate(cards):
        with cols[i % 4]:
            kpi_card(*item)

    st.markdown("### Tendances & répartition")
    monthly = filtered.assign(month=filtered.open_datetime.dt.to_period('M').astype(str)).groupby('month', as_index=False).agg(
        work_orders=('work_order_id', 'nunique'), cost=('total_cost_usd', 'sum'))
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line(monthly, 'month', 'work_orders', 'Évolution mensuelle des ordres'), use_container_width=True)
    with c2:
        st.plotly_chart(line(monthly, 'month', 'cost', 'Évolution mensuelle des coûts'), use_container_width=True)
    c3, c4 = st.columns(2)
    with c3:
        t = filtered.groupby('maintenance_type', as_index=False).size().sort_values('size', ascending=False)
        st.plotly_chart(donut(t, 'maintenance_type', 'size', 'Répartition des maintenances'), use_container_width=True)
    with c4:
        ata = filtered.groupby('ata_system', as_index=False).size().nlargest(8, 'size')
        st.plotly_chart(bar(ata, 'size', 'ata_system', 'Top systèmes ATA', orientation='h'), use_container_width=True)

elif page == "Flotte":
    # Fleet Intelligence — all operational figures are computed from the active CSV slice.
    st.markdown("""
    <div class="fleet-hero">
      <div class="fleet-hero-copy">
        <div class="fleet-eyebrow">AERONEX / FLEET INTELLIGENCE</div>
        <div class="fleet-headline">Fleet Overview</div>
        <div class="fleet-subtitle">Vue consolidée des modèles, de la charge maintenance, des coûts et de l’immobilisation.</div>
      </div>
      <div class="fleet-hero-mark">✈</div>
    </div>
    """, unsafe_allow_html=True)

    # Model-specific real aircraft photographs. Sources and licenses are documented
    # in assets/image_sources.md. Remote Wikimedia file paths keep the package light.
    MODEL_PHOTOS = {
        "B737-800": "https://commons.wikimedia.org/wiki/Special:FilePath/B737-800.jpg?width=1400",
        "ATR 72-600": "https://commons.wikimedia.org/wiki/Special:FilePath/An_ATR_72-600.jpg?width=1400",
        "B787-8": "https://commons.wikimedia.org/wiki/Special:FilePath/Boeing_787-8_first_flight_photographers.jpg?width=1400",
        "B787-9": "https://commons.wikimedia.org/wiki/Special:FilePath/ANA_Boeing_787-9.jpg?width=1400",
        "E190": "https://commons.wikimedia.org/wiki/Special:FilePath/AERONAVE_EMBRAER_E-190.jpg?width=1400",
    }
    MODEL_INFO = {
        "B737-800": ("Boeing", "Single-aisle · moyen-courrier", "737 Next Generation"),
        "ATR 72-600": ("ATR", "Turbopropulseur · régional", "ATR 72 Series"),
        "B787-8": ("Boeing", "Gros-porteur · long-courrier", "787 Dreamliner"),
        "B787-9": ("Boeing", "Gros-porteur · long-courrier", "787 Dreamliner"),
        "E190": ("Embraer", "Jet régional · monocouloir", "E-Jets"),
    }
    fleet_types = filtered.groupby("aircraft_type", as_index=False).agg(
        aircraft_count=("aircraft_reg", "nunique"),
        orders=("work_order_id", "nunique"),
        cost=("total_cost_usd", "sum"),
        downtime=("aircraft_downtime_h", "sum"),
        avg_age=("aircraft_age_years", "mean"),
        avg_cost=("total_cost_usd", "mean"),
        repeat_orders=("repeat_defect", lambda x: x.astype(str).str.lower().eq("yes").sum()),
        aog_orders=("priority", lambda x: x.astype(str).str.upper().eq("AOG").sum()),
        open_orders=("status", lambda x: x.astype(str).str.lower().eq("open").sum()),
    )
    fleet_types["cost_per_aircraft"] = fleet_types["cost"] / fleet_types["aircraft_count"].clip(lower=1)
    fleet_types["orders_per_aircraft"] = fleet_types["orders"] / fleet_types["aircraft_count"].clip(lower=1)
    fleet_types["downtime_per_aircraft"] = fleet_types["downtime"] / fleet_types["aircraft_count"].clip(lower=1)
    fleet_types["downtime_per_order"] = fleet_types["downtime"] / fleet_types["orders"].clip(lower=1)
    fleet_types["repeat_rate"] = fleet_types["repeat_orders"] / fleet_types["orders"].clip(lower=1) * 100
    fleet_types["cost_per_order"] = fleet_types["cost"] / fleet_types["orders"].clip(lower=1)
    fleet_types = fleet_types.sort_values("orders", ascending=False)

    fleet_total_aircraft = int(filtered["aircraft_reg"].nunique())
    fleet_total_orders = int(filtered["work_order_id"].nunique())
    fleet_total_cost = float(filtered["total_cost_usd"].sum())
    fleet_total_downtime = float(filtered["aircraft_downtime_h"].sum())
    fleet_avg_age = float(filtered.drop_duplicates("aircraft_reg")["aircraft_age_years"].mean()) if fleet_total_aircraft else 0.0
    aog_total = int(filtered.loc[(filtered.maintenance_type.astype(str).str.upper().eq("AOG")) |
                                 (filtered.priority.astype(str).str.upper().eq("AOG")), "work_order_id"].nunique())
    open_total = int(filtered.loc[filtered.status.astype(str).str.lower().eq("open"), "work_order_id"].nunique())

    st.markdown("### Fleet Overview · Indicateurs clés")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("AIRCRAFT", f"{fleet_total_aircraft:,}")
    k2.metric("AIRCRAFT MODELS", f"{fleet_types.aircraft_type.nunique()}")
    k3.metric("WORK ORDERS", f"{fleet_total_orders:,}")
    k4.metric("MAINTENANCE COST", f"${fleet_total_cost/1_000_000:,.2f}M")
    k5.metric("DOWNTIME", f"{fleet_total_downtime:,.0f} h")
    k6.metric("AOG / OPEN", f"{aog_total:,} / {open_total:,}")
    st.caption(f"Âge moyen observé : {fleet_avg_age:.1f} ans · Données recalculées avec les filtres actifs. Les taux par avion aident à comparer les modèles de tailles différentes.")

    st.markdown("### Aircraft Models")
    st.caption("Photographies réelles par modèle — chaque carte utilise une image distincte. Les images illustrent le modèle et ne prouvent pas l’identité des appareils du CSV.")
    model_cols = st.columns(3)
    for idx, (_, ac) in enumerate(fleet_types.iterrows()):
        model = str(ac["aircraft_type"])
        maker, category, family = MODEL_INFO.get(model, ("Constructeur non précisé", "Catégorie non documentée", model))
        image_url = MODEL_PHOTOS.get(model)
        with model_cols[idx % 3]:
            if image_url:
                st.image(image_url, use_container_width=True)
            else:
                st.image(str(ROOT / "assets" / "aircraft_hangar.jpg"), use_container_width=True)
            cost_share = (float(ac["cost"]) / fleet_total_cost * 100) if fleet_total_cost else 0
            st.markdown(f"""
            <div class="fleet-model-card">
              <div class="fleet-model-top"><span>MODEL / {idx+1:02d} · {html.escape(maker.upper())}</span><b>{int(ac['aircraft_count'])} AIRCRAFT</b></div>
              <div class="fleet-model-name">{html.escape(model)}</div>
              <div class="fleet-model-meta">{html.escape(category)} · {html.escape(family)}</div>
              <div class="fleet-model-metrics">
                <div><small>ORDERS</small><strong>{int(ac['orders']):,}</strong></div>
                <div><small>COST</small><strong>${float(ac['cost'])/1_000_000:.2f}M</strong></div>
                <div><small>DOWNTIME</small><strong>{float(ac['downtime']):,.0f} h</strong></div>
                <div><small>COST / ORDER</small><strong>${float(ac['cost_per_order']):,.0f}</strong></div>
              </div>
              <div class="fleet-model-meta">Part du coût filtré : {cost_share:.1f}% · {float(ac['orders_per_aircraft']):.1f} ordres / avion</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open {model} profile →", key=f"open_model_{idx}", use_container_width=True):
                st.session_state["profile_model"] = model
                st.session_state["requested_page"] = "Fiches avions interactives"
                st.rerun()

    st.markdown("### Visual Analytics")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        cost_plot = fleet_types.sort_values("cost", ascending=True)
        fig_cost = px.bar(cost_plot, x="cost", y="aircraft_type", orientation="h",
                          title="Maintenance cost by aircraft model",
                          labels={"cost":"Total cost (USD)", "aircraft_type":"Aircraft model"},
                          text="cost", color="cost", color_continuous_scale=["#24738a","#36c9dc"])
        fig_cost.update_traces(texttemplate="$%{x:,.0f}", textposition="outside", cliponaxis=False)
        fig_cost.update_layout(height=370, margin=dict(l=8,r=35,t=55,b=10), coloraxis_showscale=False,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#9bb0c5", xaxis=dict(showgrid=True,gridcolor="rgba(148,181,210,.12)"),
                               yaxis=dict(title=None))
        st.plotly_chart(fig_cost, use_container_width=True)
    with chart_right:
        mix = filtered.groupby("maintenance_type", as_index=False).agg(
            orders=("work_order_id","nunique"), cost=("total_cost_usd","sum"))
        fig_mix = px.pie(mix, names="maintenance_type", values="orders", hole=.62,
                         title="Maintenance workload by type")
        fig_mix.update_layout(height=370, margin=dict(l=8,r=8,t=55,b=10),
                              paper_bgcolor="rgba(0,0,0,0)", font_color="#9bb0c5",
                              legend=dict(orientation="h", y=-.15))
        st.plotly_chart(fig_mix, use_container_width=True)

    chart_left, chart_right = st.columns(2)
    with chart_left:
        dt_plot = fleet_types.sort_values("downtime", ascending=True)
        fig_dt = px.bar(dt_plot, x="downtime", y="aircraft_type", orientation="h",
                        title="Aircraft downtime by model",
                        labels={"downtime":"Downtime (hours)", "aircraft_type":"Aircraft model"},
                        color="downtime", color_continuous_scale=["#725c35","#f2a83b"])
        fig_dt.update_layout(height=340, margin=dict(l=8,r=15,t=55,b=10), coloraxis_showscale=False,
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             font_color="#9bb0c5", yaxis=dict(title=None),
                             xaxis=dict(gridcolor="rgba(148,181,210,.12)"))
        st.plotly_chart(fig_dt, use_container_width=True)
    with chart_right:
        maint = filtered.groupby(["aircraft_type","maintenance_type"],as_index=False).agg(
            orders=("work_order_id","nunique"))
        fig_maint = px.bar(maint, x="aircraft_type", y="orders", color="maintenance_type",
                           barmode="stack", title="Maintenance events by model",
                           labels={"aircraft_type":"Aircraft model","orders":"Work orders"})
        fig_maint.update_layout(height=340, margin=dict(l=8,r=8,t=55,b=10),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font_color="#9bb0c5", xaxis=dict(title=None),
                                yaxis=dict(title=None,gridcolor="rgba(148,181,210,.12)"),
                                legend_title=None)
        st.plotly_chart(fig_maint, use_container_width=True)

    st.markdown("### Smart Comparison")
    compare_models = st.multiselect("Select aircraft models", fleet_types.aircraft_type.astype(str).tolist(),
                                    default=fleet_types.aircraft_type.astype(str).tolist()[:min(3,len(fleet_types))],
                                    key="fleet_compare_models_v2")
    compare_metric_label = st.selectbox("Comparison metric", [
        "Maintenance cost", "Cost per aircraft", "Work orders", "Orders per aircraft",
        "Downtime", "Downtime per aircraft", "Downtime per order", "Repeat defect rate"
    ], key="fleet_compare_metric")
    compare_metric = {
        "Maintenance cost":"cost", "Cost per aircraft":"cost_per_aircraft",
        "Work orders":"orders", "Orders per aircraft":"orders_per_aircraft",
        "Downtime":"downtime", "Downtime per aircraft":"downtime_per_aircraft",
        "Downtime per order":"downtime_per_order", "Repeat defect rate":"repeat_rate"
    }[compare_metric_label]
    compare = fleet_types[fleet_types.aircraft_type.astype(str).isin(compare_models)].copy()
    if not compare.empty:
        fig_compare = px.bar(compare.sort_values(compare_metric,ascending=True), x=compare_metric, y="aircraft_type",
                             orientation="h", text=compare_metric, title=f"{compare_metric_label} · model comparison",
                             labels={compare_metric:compare_metric_label,"aircraft_type":"Aircraft model"})
        suffix = " h" if "Downtime" in compare_metric_label else ("%" if compare_metric_label=="Repeat defect rate" else "")
        fig_compare.update_traces(texttemplate="%{x:,.1f}"+suffix, textposition="outside", cliponaxis=False)
        fig_compare.update_layout(height=350, margin=dict(l=8,r=35,t=55,b=10),
                                  paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#9bb0c5",xaxis=dict(gridcolor="rgba(148,181,210,.12)"),
                                  yaxis=dict(title=None))
        st.plotly_chart(fig_compare,use_container_width=True)
        display_cols = ["aircraft_type","aircraft_count","orders","cost","cost_per_aircraft",
                        "orders_per_aircraft","downtime","downtime_per_aircraft","repeat_rate"]
        st.dataframe(compare[display_cols].rename(columns={
            "aircraft_type":"Model","aircraft_count":"Aircraft","orders":"Orders","cost":"Total cost USD",
            "cost_per_aircraft":"Cost / aircraft USD","orders_per_aircraft":"Orders / aircraft",
            "downtime":"Downtime h","downtime_per_aircraft":"Downtime / aircraft h","repeat_rate":"Repeat rate %"
        }).round(2),use_container_width=True,hide_index=True)
    else:
        st.info("Select at least one model to compare.")

    st.markdown("### Fleet Intelligence")
    st.caption("Les classements distinguent le volume brut de la fréquence rapportée au nombre d’avions. Un coût élevé peut refléter une flotte plus grande ou davantage d’ordres, pas nécessairement une fiabilité inférieure.")
    intel_a, intel_b, intel_c = st.columns(3)
    if not fleet_types.empty:
        highest_cost = fleet_types.loc[fleet_types.cost_per_aircraft.idxmax()]
        highest_maintenance = fleet_types.loc[fleet_types.orders_per_aircraft.idxmax()]
        highest_downtime = fleet_types.loc[fleet_types.downtime_per_aircraft.idxmax()]
        intel_a.metric("Highest cost / aircraft", str(highest_cost.aircraft_type),
                       f"${highest_cost.cost_per_aircraft:,.0f} per aircraft")
        intel_b.metric("Most maintenance / aircraft", str(highest_maintenance.aircraft_type),
                       f"{highest_maintenance.orders_per_aircraft:.1f} orders per aircraft")
        intel_c.metric("Highest downtime / aircraft", str(highest_downtime.aircraft_type),
                       f"{highest_downtime.downtime_per_aircraft:,.1f} h per aircraft")
        intelligence_table = fleet_types[["aircraft_type","aircraft_count","orders","cost","cost_per_aircraft",
                                           "orders_per_aircraft","downtime_per_aircraft","repeat_rate"]].copy()
        st.dataframe(intelligence_table.sort_values("cost_per_aircraft",ascending=False).rename(columns={
            "aircraft_type":"Model","aircraft_count":"Aircraft","orders":"Work orders","cost":"Total cost USD",
            "cost_per_aircraft":"Cost / aircraft USD","orders_per_aircraft":"Orders / aircraft",
            "downtime_per_aircraft":"Downtime / aircraft h","repeat_rate":"Repeat defect rows %"
        }).round(2),use_container_width=True,hide_index=True)

    st.markdown("### Aircraft Profile · Quick access")
    reg = filtered.groupby(["aircraft_reg", "aircraft_type"], as_index=False).agg(
        orders=("work_order_id", "nunique"), cost=("total_cost_usd", "sum"),
        downtime=("aircraft_downtime_h", "sum"), age=("aircraft_age_years", "mean"),
        flight_hours=("flight_hours_total", "max"), cycles=("flight_cycles_total", "max"))
    reg = reg.sort_values(["orders", "cost"], ascending=False)
    if not reg.empty:
        selected_reg = st.selectbox("Choose registration", reg["aircraft_reg"].astype(str).tolist(),
                                    key="fleet_selected_registration_v2")
        aircraft = reg[reg.aircraft_reg.astype(str).eq(selected_reg)].iloc[0]
        related = filtered[filtered.aircraft_reg.astype(str).eq(selected_reg)].sort_values("open_datetime", ascending=False)
        st.markdown(f"**{html.escape(selected_reg)}** · {html.escape(str(aircraft['aircraft_type']))} · "
                    f"{int(aircraft['orders'])} work orders · ${float(aircraft['cost']):,.0f} · "
                    f"{float(aircraft['downtime']):,.1f} h downtime")
        st.dataframe(related[["work_order_id","open_datetime","close_datetime","station","ata_system",
                              "finding","priority","status","aircraft_downtime_h"]].head(20),
                     use_container_width=True,hide_index=True)
    else:
        st.info("No aircraft match the active filters.")

    with st.container():
        st.markdown("### Gallery · Aircraft, engines & cabin")
        st.caption("Images supplémentaires sans répétition dans cette galerie. Les visuels locaux sont des illustrations de maintenance ; ils ne sont pas associés à un avion précis.")
        gallery_cols = st.columns(3)
        gallery_items = [
            ("Aircraft on apron", str(ROOT / "assets" / "aircraft_hangar.jpg"), "local"),
            ("Engine detail", str(ROOT / "assets" / "engine_detail.jpg"), "local"),
            ("Engine inspection", str(ROOT / "assets" / "engine_inspection.jpg"), "local"),
            ("Maintenance technician", str(ROOT / "assets" / "maintenance_technician.jpg"), "local"),
            ("ATR 72-600 in flight", "https://commons.wikimedia.org/wiki/Special:FilePath/ATR_72-600_in_flight.jpg?width=1400", "remote"),
            ("Embraer E190 cabin", "https://commons.wikimedia.org/wiki/Special:FilePath/Cabine_do_Embraer_190.jpg?width=1400", "remote"),
        ]
        for i, (label, src, kind) in enumerate(gallery_items):
            with gallery_cols[i % 3]:
                st.image(src, use_container_width=True)
                st.caption(label)

elif page == "Activité quotidienne":
    st.markdown("### Journal quotidien des opérations de maintenance")
    st.caption("Vue reconstruite à partir de la date d’ouverture des ordres de travail. Les cartes représentent des activités de maintenance, pas des vols programmés ni une position avion en temps réel.")

    daily = filtered.copy()
    daily["operation_day"] = daily["open_datetime"].dt.date
    available_days = sorted(daily["operation_day"].dropna().unique(), reverse=True)
    if available_days:
        chosen_day = st.selectbox(
            "Journée à consulter",
            available_days,
            format_func=lambda d: pd.Timestamp(d).strftime("%A %d %B %Y").capitalize()
        )
        day_df = daily[daily["operation_day"] == chosen_day].sort_values("open_datetime")
        day_orders = day_df["work_order_id"].nunique()
        day_aircraft = day_df["aircraft_reg"].nunique()
        day_aog = ((day_df["maintenance_type"].eq("AOG")) | (day_df["priority"].eq("AOG"))).sum()
        day_downtime = day_df["aircraft_downtime_h"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ordres ouverts ce jour", no(day_orders))
        m2.metric("Avions concernés", no(day_aircraft))
        m3.metric("Événements AOG", no(day_aog))
        m4.metric("Immobilisation déclarée", f"{day_downtime:,.1f} h")

        st.markdown(
            f"<div class='daily-heading'><span>✈</span><div><strong>{pd.Timestamp(chosen_day).strftime('%d.%m.%Y')}</strong>"
            f"<small>{len(day_df)} enregistrement(s) · {day_aircraft} immatriculation(s)</small></div>"
            f"<span class='daily-day-tag'>DAILY OPERATIONS</span></div>",
            unsafe_allow_html=True
        )

        # Les cartes utilisent les données observées. Aucun horaire de vol,
        # itinéraire ou statut de tracking n'est inventé.
        for start in range(0, len(day_df), 2):
            pair = day_df.iloc[start:start + 2]
            cols = st.columns(2)
            for col, (_, rec) in zip(cols, pair.iterrows()):
                priority = str(rec["priority"])
                status = str(rec["status"])
                priority_class = "critical" if priority.upper() in ("AOG", "HIGH") else "normal"
                status_class = "open" if status.lower() == "open" else "closed"
                opened = rec["open_datetime"].strftime("%H:%M") if pd.notna(rec["open_datetime"]) else "—"
                closed = rec["close_datetime"].strftime("%H:%M") if pd.notna(rec["close_datetime"]) else "En cours"
                card = f"""
                <div class="daily-aircraft-card">
                  <div class="daily-card-top">
                    <span class="daily-wo">{html.escape(str(rec['work_order_id']))}</span>
                    <span class="daily-priority {priority_class}">{html.escape(priority)}</span>
                  </div>
                  <div class="daily-aircraft-main">
                    <div class="daily-plane-icon">✈</div>
                    <div><div class="daily-registration">{html.escape(str(rec['aircraft_reg']))}</div>
                    <div class="daily-type">{html.escape(str(rec['aircraft_type']))}</div></div>
                  </div>
                  <div class="daily-route">
                    <div><small>ESCALE</small><strong>{html.escape(str(rec['station']))}</strong></div>
                    <div class="daily-route-line">━━━━━━━━━━━━</div>
                    <div><small>SYSTÈME ATA</small><strong>{html.escape(str(rec['ata_system']))}</strong></div>
                  </div>
                  <div class="daily-card-info">
                    <span>◷ Ouverture <b>{opened}</b></span>
                    <span>◷ Clôture <b>{closed}</b></span>
                  </div>
                  <div class="daily-finding">{html.escape(str(rec['finding']))}</div>
                  <div class="daily-card-bottom">
                    <span>{html.escape(str(rec['maintenance_type']))}</span>
                    <span class="daily-status {status_class}">{html.escape(status)}</span>
                  </div>
                </div>
                """
                with col:
                    st.markdown(card, unsafe_allow_html=True)

        st.markdown("#### Répartition de la journée")
        daily_cols = st.columns(3)
        for col, (label, value) in zip(daily_cols, [
            ("Maintenance la plus fréquente", day_df["maintenance_type"].mode().iloc[0] if not day_df.empty else "—"),
            ("Escale la plus active", day_df["station"].mode().iloc[0] if not day_df.empty else "—"),
            ("Système ATA le plus sollicité", day_df["ata_system"].mode().iloc[0] if not day_df.empty else "—")
        ]):
            with col:
                st.markdown(f"<div class='daily-insight'><small>{label}</small><strong>{html.escape(str(value))}</strong></div>", unsafe_allow_html=True)
        display_cols = ["work_order_id", "open_datetime", "close_datetime", "station",
                        "aircraft_reg", "aircraft_type", "maintenance_type", "ata_system",
                        "priority", "status", "aircraft_downtime_h"]
        st.download_button("Exporter cette journée (CSV)", day_df[display_cols].to_csv(index=False).encode("utf-8"),
                           f"aeronex_operations_{chosen_day}.csv", "text/csv")
    else:
        st.info("Aucune opération disponible pour les filtres sélectionnés.")

    st.markdown("#### Activité par jour")
    daily_summary = daily.groupby("operation_day", as_index=False).agg(
        work_orders=("work_order_id", "nunique"),
        aircraft=("aircraft_reg", "nunique"),
        downtime=("aircraft_downtime_h", "sum")
    ).sort_values("operation_day")
    daily_summary["operation_day"] = daily_summary["operation_day"].astype(str)
    st.plotly_chart(line(daily_summary, "operation_day", "work_orders", "Ordres de travail ouverts chaque jour"), use_container_width=True)
    st.caption("Important : le fichier source contient des ordres de maintenance, pas un programme de vols. Les cartes avion illustrent donc les avions concernés par les interventions, sans simuler de vols réels.")

elif page == "Fiabilité":
    st.markdown("### Fiabilité et défauts répétitifs")
    st.markdown(photo_card("engine_inspection.jpg", "Inspection et fiabilité des systèmes",
                           "VISUEL ILLUSTRATIF · INDICATEURS CALCULÉS DEPUIS LES ORDRES"),
                   unsafe_allow_html=True)
    c1,c2=st.columns(2)
    p=filtered.groupby('priority',as_index=False).size()
    with c1: st.plotly_chart(donut(p,'priority','size','Répartition des priorités'),use_container_width=True)
    rep=filtered.groupby('repeat_defect',as_index=False).size()
    with c2: st.plotly_chart(bar(rep,'repeat_defect','size','Ordres avec défaut répétitif'),use_container_width=True)
    top=filtered.groupby('ata_system',as_index=False).size().sort_values('size',ascending=False).head(15)
    st.plotly_chart(pareto(top,'ata_system','size','Pareto des systèmes concernés'),use_container_width=True)
    st.caption("Le marquage repeat_defect est repris tel quel du dataset ; il ne constitue pas à lui seul une analyse causale.")

elif page == "Analyse ATA":
    st.markdown("### Analyse des chapitres et systèmes ATA")
    st.markdown(photo_card("engine_detail.jpg", "Architecture des systèmes aéronautiques",
                           "REPÈRES ATA · ANALYSE DES INTERVENTIONS"),
                   unsafe_allow_html=True)
    ata=filtered.groupby(['ata_chapter','ata_system'],as_index=False).agg(work_orders=('work_order_id','nunique'),cost=('total_cost_usd','sum'),downtime=('aircraft_downtime_h','sum'),repeat=('repeat_defect',lambda s:s.astype(str).str.lower().eq('yes').sum()))
    c1,c2=st.columns(2)
    with c1: st.plotly_chart(bar(ata.groupby('ata_chapter',as_index=False).work_orders.sum().sort_values('work_orders',ascending=False).head(12),'ata_chapter','work_orders','Top chapitres ATA'),use_container_width=True)
    with c2: st.plotly_chart(bar(ata.nlargest(12,'cost'),'cost','ata_system','Systèmes les plus coûteux',orientation='h'),use_container_width=True)
    st.plotly_chart(pareto(ata.nlargest(15,'work_orders'),'ata_system','work_orders','Pareto des interventions par système'),use_container_width=True)
    st.markdown("#### Systèmes à surveiller")
    for _, rec in ata.nlargest(6, "work_orders").iterrows():
        st.markdown(f"<div class='insight-row'><span class='insight-code'>ATA {html.escape(str(rec['ata_chapter']))}</span><div><strong>{html.escape(str(rec['ata_system']))}</strong><small>{int(rec['work_orders'])} ordres · ${rec['cost']:,.0f} · {rec['downtime']:,.1f} h immobilisées</small></div></div>", unsafe_allow_html=True)

elif page == "Atelier & coûts":
    st.markdown("### Analyse des coûts de maintenance")
    c1,c2=st.columns(2)
    with c1: st.plotly_chart(donut(pd.DataFrame({'Type':['Pièces','Main-d’œuvre'],'Coût':[k['parts'],k['labor']]}),'Type','Coût','Structure des coûts'),use_container_width=True)
    cost_type=filtered.groupby('aircraft_type',as_index=False).agg(parts=('parts_cost_usd','sum'),labor=('labor_cost_usd','sum'),total=('total_cost_usd','sum'))
    with c2:
        fig=px.bar(cost_type,x='aircraft_type',y=['parts','labor'],barmode='stack',title='Pièces et main-d’œuvre par type',color_discrete_sequence=PALETTE)
        st.plotly_chart(style(fig),use_container_width=True)
    cost_month=filtered.assign(month=filtered.open_datetime.dt.to_period('M').astype(str)).groupby('month',as_index=False).total_cost_usd.sum()
    st.plotly_chart(line(cost_month,'month','total_cost_usd','Évolution mensuelle du coût total'),use_container_width=True)
    st.markdown("#### Coût par famille d’avion")
    for _, rec in cost_type.sort_values("total", ascending=False).iterrows():
        pct = (rec["total"] / max(cost_type["total"].max(), 1)) * 100
        st.markdown(f"<div class='cost-visual-row'><div><strong>{html.escape(str(rec['aircraft_type']))}</strong><span>${rec['total']:,.0f}</span></div><div class='visual-track'><i style='width:{pct:.1f}%'></i></div><small>Pièces ${rec['parts']:,.0f} · Main-d’œuvre ${rec['labor']:,.0f}</small></div>", unsafe_allow_html=True)

elif page == "Immobilisation & retards":
    st.markdown("### Impact opérationnel")
    st.markdown(photo_card("maintenance_technician.jpg", "Équipe de maintenance", "VISUEL ILLUSTRATIF · NON RATTACHÉ AUX DONNÉES FILTRÉES"), unsafe_allow_html=True)
    c1,c2=st.columns(2)
    by_station=filtered.groupby('station',as_index=False).agg(downtime=('aircraft_downtime_h','sum'),delay=('flight_delay_min','sum'))
    with c1: st.plotly_chart(bar(by_station,'station','downtime','Immobilisation par escale'),use_container_width=True)
    with c2: st.plotly_chart(bar(by_station,'station','delay','Retards par escale'),use_container_width=True)
    grp=filtered.groupby('maintenance_group',as_index=False).agg(orders=('work_order_id','nunique'),downtime=('aircraft_downtime_h','sum'),delay=('flight_delay_min','sum'))
    st.markdown("### Programmée vs non programmée / autre")
    for _, rec in grp.iterrows():
        st.markdown(f"<div class='insight-row'><span class='insight-code'>{html.escape(str(rec['maintenance_group']))}</span><div><strong>{int(rec['orders'])} ordres</strong><small>{rec['downtime']:,.1f} h immobilisées · {rec['delay']:,.0f} min de retard</small></div></div>", unsafe_allow_html=True)
    st.caption("Classification utilisée : Daily Check, Weekly Check, Line Check, A-Check et C-Check = programmée. Les autres types sont regroupés dans non programmée / autre.")

elif page == "Alertes":
    st.markdown("### Centre de surveillance")
    st.caption("Les listes ci-dessous sont construites à partir des champs du CSV (AOG, priorité, MEL, répétitivité et statut). Il s’agit de signaux de suivi calculés, pas d’alertes temps réel ni d’une évaluation de navigabilité.")
    aog=filtered[(filtered.maintenance_type.eq('AOG')) | (filtered.priority.eq('AOG'))]
    high=filtered[filtered.priority.eq('High')]
    repeat=filtered[filtered.repeat_defect.astype(str).str.lower().eq('yes')]
    open_df=filtered[filtered.status.astype(str).str.lower().eq('open')]
    c=st.columns(4)
    for col,label,val in zip(c,['AOG','Priorité High','Défauts répétitifs','Ordres ouverts'],[len(aog),len(high),len(repeat),len(open_df)]):
        with col: st.metric(label,no(val))
    st.markdown("#### Événements AOG")
    for _, rec in aog.head(8).iterrows():
        st.markdown(f"<div class='alert-visual-card'><span class='alert-aog'>AOG</span><div><strong>{html.escape(str(rec['aircraft_reg']))} · {html.escape(str(rec['aircraft_type']))}</strong><small>{html.escape(str(rec['station']))} · {html.escape(str(rec['ata_system']))} · {html.escape(str(rec['finding']))}</small></div><b>{rec['aircraft_downtime_h']:,.1f} h</b></div>", unsafe_allow_html=True)
    st.markdown("#### MEL différés et défauts répétitifs")
    mel=filtered[filtered.mel_deferred.astype(str).str.lower().eq('yes')]
    c1,c2=st.columns(2)
    with c1:
        st.metric("MEL Deferred", no(len(mel)))
        for _, rec in mel.head(5).iterrows():
            st.markdown(f"<div class='insight-row'><span class='insight-code'>MEL</span><div><strong>{html.escape(str(rec['aircraft_reg']))} · {html.escape(str(rec['ata_system']))}</strong><small>{html.escape(str(rec['finding']))}</small></div></div>", unsafe_allow_html=True)
    with c2:
        st.metric("Défauts répétitifs", no(len(repeat)))
        for _, rec in repeat.head(5).iterrows():
            st.markdown(f"<div class='insight-row'><span class='insight-code'>REPEAT</span><div><strong>{html.escape(str(rec['aircraft_reg']))} · {html.escape(str(rec['ata_system']))}</strong><small>{html.escape(str(rec['finding']))}</small></div></div>", unsafe_allow_html=True)

elif page == "Ordres de travail":
    st.markdown("### Explorateur des ordres de travail")
    search=st.text_input("Rechercher un WO, une immatriculation, un défaut ou un système ATA")
    view=filtered.copy()
    if search:
        mask=view.astype(str).apply(lambda col: col.str.contains(search,case=False,na=False)).any(axis=1)
        view=view[mask]
    c1,c2=st.columns(2)
    with c1: st.caption(f"{len(view):,} résultat(s)".replace(',',' '))
    with c2: st.download_button("Télécharger les résultats CSV",view.to_csv(index=False).encode('utf-8'),"work_orders_filtered.csv","text/csv",use_container_width=True)
    st.markdown("#### Résultats sous forme de fiches")
    for _, rec in view.sort_values("open_datetime", ascending=False).head(30).iterrows():
        st.markdown(f"<div class='workorder-visual'><div class='workorder-head'><strong>{html.escape(str(rec['work_order_id']))}</strong><span>{html.escape(str(rec['priority']))}</span></div><div class='workorder-aircraft'>{html.escape(str(rec['aircraft_reg']))} <small>{html.escape(str(rec['aircraft_type']))}</small></div><div class='workorder-desc'>{html.escape(str(rec['finding']))}</div><div class='workorder-foot'><span>{html.escape(str(rec['station']))} · ATA {html.escape(str(rec['ata_chapter']))}</span><span>{html.escape(str(rec['status']))}</span><span>{rec['open_datetime'].strftime('%d/%m/%Y %H:%M')}</span></div></div>", unsafe_allow_html=True)
    if len(view) > 30:
        st.caption("30 premières fiches affichées. Utilise le téléchargement CSV pour récupérer tous les résultats filtrés.")

elif page in {"Fiches avions interactives", "Planning de maintenance", "Carte mondiale", "AERONEX AI", "Stocks de pièces", "Gestion des techniciens", "Notifications intelligentes", "Rapports PDF professionnels"}:
    render_extra_page(page, df, filtered, lang)

else:
    st.markdown("### Synthèse et recommandations basées sur les données filtrées")
    st.markdown(photo_card("hangar_hero.jpg", "Briefing opérationnel AERONEX",
                           "SYNTHÈSE DE FLOTTE · PISTES D'ANALYSE"),
                   unsafe_allow_html=True)
    st.caption("Observations calculées automatiquement à partir des lignes filtrées. Les recommandations sont des pistes d’analyse, non des consignes de maintenance.")
    top_ata=filtered.ata_system.value_counts()
    top_type=filtered.groupby('aircraft_type').parts_cost_usd.sum().sort_values(ascending=False)
    old=filtered.groupby('aircraft_age_years').labor_hours.mean().reset_index()
    st.markdown("#### Observations automatiques")
    if len(top_ata): st.write(f"- Système ATA le plus représenté dans le filtre : **{top_ata.index[0]}** ({int(top_ata.iloc[0])} ordres).")
    if len(top_type): st.write(f"- Type d'avion avec le coût de pièces cumulé le plus élevé dans le filtre : **{top_type.index[0]}** ({money(top_type.iloc[0])}).")
    st.write(f"- Coût total de maintenance observé : **{money(k['cost'])}**.")
    st.write(f"- Immobilisation totale déclarée : **{k['downtime']:,.1f} heures**.")
    st.markdown("#### Pistes d'analyse")
    st.info("Examiner les systèmes ATA les plus fréquents, puis vérifier les findings et les défauts répétitifs associés avant de proposer une action technique.")
    st.info("Comparer les coûts pièces et main-d’œuvre par type et par immatriculation pour repérer les postes qui méritent une investigation.")
    st.info("Suivre les immobilisations et les retards par escale et par type de maintenance ; interpréter ces associations avec le contexte opérationnel.")
    st.caption("Ces pistes sont des axes d'investigation, pas des conclusions de sécurité ni des diagnostics de navigabilité.")

with st.expander("Contrôle qualité des données"):
    q=quality_summary(df)
    c=st.columns(4)
    for col,(label,val) in zip(c,q.items()):
        with col: st.metric(label.replace('_',' ').capitalize(),no(val))
    st.caption("Les 6 dates de clôture manquantes sont conservées : elles peuvent correspondre à des ordres encore ouverts. Aucune ligne n'est supprimée automatiquement.")

st.divider()
st.caption("AERONEX · Projet analytique · Les données opérationnelles proviennent du CSV fourni ; les KPI, regroupements et alertes sont calculés par l’application. Les illustrations et ornements de l’interface sont décoratifs.")
