"""
Dashboard Streamlit - Analyse du marché immobilier Ames, Iowa.
================================================================
Source de données : PostgreSQL (base house_prices)
Dataset original : Kaggle House Prices - Advanced Regression Techniques

Auteur  : [Ton nom]
Stack   : Python 3.11+ · Streamlit · Pandas · Plotly · SQLAlchemy · PostgreSQL
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from sqlalchemy import create_engine
from dotenv import load_dotenv

# =================================================================
# CONFIGURATION
# =================================================================

load_dotenv()

st.set_page_config(
    page_title="🏠 House Prices Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thème Plotly global
pio.templates.default = "plotly_dark"

# Config Plotly commune à tous les graphiques
PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "zoomIn2d", "zoomOut2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "house_prices_chart",
        "scale": 2
    }
}

# Palette de couleurs du projet
COLORS = {
    "primary": "#2E86AB",
    "accent": "#E63946",
    "success": "#06A77D",
    "light": "#A8DADC",
    "dark": "#1D3557",
    "warning": "#F4A261",
}


# =================================================================
# CONNEXION À LA BASE DE DONNÉES
# =================================================================

@st.cache_resource
def get_engine():
    """Crée l'engine SQLAlchemy (mis en cache)."""
    url = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=600, show_spinner=False)
def run_query(query: str) -> pd.DataFrame:
    """Exécute une requête SQL et retourne un DataFrame (cache 10 min)."""
    return pd.read_sql(query, get_engine())


engine = get_engine()


# =================================================================
# HEADER
# =================================================================

st.title("🏠 House Prices — Dashboard Analytique")
st.markdown(
    "Analyse du marché immobilier d'**Ames, Iowa (USA)** "
    "— **1 460 transactions** — Source : [Kaggle House Prices]"
    "(https://www.kaggle.com/c/house-prices-advanced-regression-techniques)"
)

# =================================================================
# SIDEBAR — FILTRES
# =================================================================

st.sidebar.header("🔍 Filtres")
st.sidebar.markdown("Affinez votre analyse :")

# --- Filtre quartier ---
neighborhoods_df = run_query(
    "SELECT neighborhood_name FROM neighborhoods ORDER BY 1"
)
all_neighborhoods = neighborhoods_df['neighborhood_name'].tolist()

selected_neighborhoods = st.sidebar.multiselect(
    "Quartier",
    options=all_neighborhoods,
    default=all_neighborhoods,
    help="Sélectionnez un ou plusieurs quartiers d'Ames"
)

# --- Filtre qualité ---
quality_range = st.sidebar.slider(
    "Note de qualité globale",
    min_value=1, max_value=10, value=(1, 10),
    help="1 = très mauvaise · 10 = très excellente"
)

# --- Filtre année ---
year_range = st.sidebar.slider(
    "Année de construction",
    min_value=1870, max_value=2010, value=(1900, 2010)
)

# --- Filtre prix ---
max_price = st.sidebar.slider(
    "Prix maximum ($)",
    min_value=30000, max_value=800000, value=800000, step=10000
)

# Sécurité : aucun quartier sélectionné
if not selected_neighborhoods:
    st.warning("⚠️ Sélectionnez au moins un quartier dans la barre latérale.")
    st.stop()

# =================================================================
# CLAUSE WHERE COMMUNE
# =================================================================

neigh_list = "','".join(selected_neighborhoods)
where_clause = f"""
    n.neighborhood_name IN ('{neigh_list}')
    AND h.overallqual BETWEEN {quality_range[0]} AND {quality_range[1]}
    AND h.yearbuilt BETWEEN {year_range[0]} AND {year_range[1]}
    AND h.saleprice <= {max_price}
"""

# =================================================================
# KPIs
# =================================================================

kpi_query = f"""
SELECT
    COUNT(*)                                AS total_houses,
    ROUND(AVG(h.saleprice)::numeric, 0)     AS avg_price,
    ROUND(AVG(h.price_per_sf)::numeric, 2)  AS avg_price_per_sf,
    ROUND(AVG(h.total_sf)::numeric, 0)      AS avg_total_sf,
    ROUND(AVG(h.house_age)::numeric, 1)     AS avg_age
FROM houses h
JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
WHERE {where_clause}
"""

kpis = run_query(kpi_query).iloc[0]

if kpis['total_houses'] == 0:
    st.warning("Aucune maison ne correspond à ces filtres.")
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🏠 Maisons",       f"{int(kpis['total_houses']):,}")
col2.metric("💰 Prix moyen",    f"${kpis['avg_price']:,.0f}")
col3.metric("📐 Prix / sqft",   f"${kpis['avg_price_per_sf']:.2f}")
col4.metric("📏 Surface moy.",  f"{kpis['avg_total_sf']:,.0f} sqft")
col5.metric("📅 Âge moyen",     f"{kpis['avg_age']:.1f} ans")

st.divider()

# =================================================================
# LIGNE 1 — Prix par quartier + Distribution
# =================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Prix moyen par quartier")

    price_neigh = run_query(f"""
        SELECT n.neighborhood_name,
               ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price,
               COUNT(*) AS nb
        FROM houses h
        JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
        WHERE {where_clause}
        GROUP BY n.neighborhood_name
        ORDER BY avg_price DESC
        LIMIT 15
    """)

    if not price_neigh.empty:
        fig = px.bar(
            price_neigh,
            x='avg_price', y='neighborhood_name',
            orientation='h',
            color='avg_price',
            color_continuous_scale='Blues',
            labels={'avg_price': 'Prix moyen ($)', 'neighborhood_name': ''},
            text='avg_price'
        )
        fig.update_traces(
            texttemplate='$%{text:,.0f}',
            textposition='inside',
            insidetextanchor='end',
            textfont=dict(color='black', size=11)
        )
        fig.update_layout(
            height=520,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'},
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=60, b=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_xaxes(range=[0, price_neigh['avg_price'].max() * 1.15])
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

with col2:
    st.subheader("📊 Distribution des prix")

    prices = run_query(f"""
        SELECT h.saleprice
        FROM houses h
        JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
        WHERE {where_clause}
    """)

    if not prices.empty:
        fig = px.histogram(
            prices, x='saleprice', nbins=40,
            labels={'saleprice': 'Prix ($)', 'count': 'Nombre de maisons'},
            color_discrete_sequence=[COLORS["primary"]]
        )
        fig.update_layout(
            height=520,
            showlegend=False,
            margin=dict(l=10, r=10, t=60, b=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_yaxes(title_text="Nombre de maisons")
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

# =================================================================
# LIGNE 2 — Scatter Prix vs Surface + Prix par qualité
# =================================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Prix vs Surface habitable")

    scatter_data = run_query(f"""
        SELECT h.saleprice, h.grlivarea, h.overallqual,
               n.neighborhood_name
        FROM houses h
        JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
        WHERE {where_clause}
    """)

    if not scatter_data.empty:
        fig = px.scatter(
            scatter_data,
            x='grlivarea', y='saleprice',
            color='overallqual',
            hover_data=['neighborhood_name'],
            labels={
                'grlivarea': 'Surface habitable (sqft)',
                'saleprice': 'Prix ($)',
                'overallqual': 'Qualité'
            },
            color_continuous_scale='Viridis'
        )
        fig.update_layout(
            height=520,
            margin=dict(l=10, r=10, t=60, b=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

with col2:
    st.subheader("⭐ Prix moyen par note de qualité")

    quality_data = run_query(f"""
        SELECT h.overallqual,
               ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price,
               COUNT(*) AS nb
        FROM houses h
        JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
        WHERE {where_clause}
        GROUP BY h.overallqual
        ORDER BY h.overallqual
    """)

    if not quality_data.empty:
        fig = px.bar(
            quality_data,
            x='overallqual', y='avg_price',
            labels={'overallqual': 'Note de qualité', 'avg_price': 'Prix moyen ($)'},
            color='avg_price',
            color_continuous_scale='RdYlGn',
            text='avg_price'
        )
        fig.update_traces(
            texttemplate='$%{text:,.0f}',
            textposition='outside',
            textfont=dict(size=11)
        )
        fig.update_layout(
            height=520,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=60, b=40),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_yaxes(range=[0, quality_data['avg_price'].max() * 1.18])
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

# =================================================================
# LIGNE 3 — Évolution temporelle
# =================================================================

st.subheader("📅 Évolution du prix moyen par décennie de construction")

decade_data = run_query(f"""
    SELECT (h.yearbuilt / 10) * 10 AS decade,
           ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price,
           COUNT(*) AS nb
    FROM houses h
    JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
    WHERE {where_clause} AND h.yearbuilt >= 1900
    GROUP BY decade
    ORDER BY decade
""")

if not decade_data.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=decade_data['decade'],
        y=decade_data['avg_price'],
        mode='lines+markers',
        name='Prix moyen',
        line=dict(color=COLORS["accent"], width=3),
        marker=dict(size=12, line=dict(color='white', width=1)),
        hovertemplate='<b>Décennie %{x}</b><br>Prix moyen : $%{y:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        height=420,
        xaxis_title="Décennie de construction",
        yaxis_title="Prix moyen ($)",
        hovermode='x unified',
        margin=dict(l=10, r=10, t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

# =================================================================
# LIGNE 4 — Impact des équipements (donuts)
# =================================================================

st.subheader("🔎 Impact des équipements sur le prix")
col1, col2, col3 = st.columns(3)

# --- Helper pour factoriser les 3 donuts ---
def render_equipment_donut(column, column_name, label_map, title, colors_pair):
    """Affiche un donut pour un équipement donné."""
    with column:
        data = run_query(f"""
            SELECT h.{column_name},
                   ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price
            FROM houses h
            JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
            WHERE {where_clause}
            GROUP BY h.{column_name}
        """)
        if not data.empty:
            data['label'] = data[column_name].map(label_map)
            fig = px.pie(
                data,
                values='avg_price',
                names='label',
                title=title,
                hole=0.4,
                color_discrete_sequence=colors_pair
            )
            fig.update_traces(textinfo='percent+label', textposition='inside')
            fig.update_layout(
                height=350,
                showlegend=True,
                margin=dict(l=10, r=10, t=60, b=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


render_equipment_donut(
    col1, 'has_garage',
    {0: 'Sans garage', 1: 'Avec garage'},
    'Garage',
    [COLORS["light"], COLORS["dark"]]
)

render_equipment_donut(
    col2, 'has_fireplace',
    {0: 'Sans cheminée', 1: 'Avec cheminée'},
    'Cheminée',
    ['#FFB4A2', COLORS["accent"]]
)

render_equipment_donut(
    col3, 'has_pool',
    {0: 'Sans piscine', 1: 'Avec piscine'},
    'Piscine',
    [COLORS["light"], '#457B9D']
)

# =================================================================
# FOOTER
# =================================================================

st.divider()
st.caption(
    "📊 Dashboard réalisé avec **Streamlit + Plotly + PostgreSQL** "
    "| Dataset : [Kaggle House Prices]"
    "(https://www.kaggle.com/c/house-prices-advanced-regression-techniques) "
    "| © 2026"
)