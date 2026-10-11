"""
Dashboard Streamlit — Analyse du marché immobilier d'Ames, Iowa.
=================================================================
Application à 3 pages :
  1. 📊 Dashboard BI      : analyse exploratoire interactive
  2. 🤖 Prédiction de prix : estimation via modèle XGBoost
  3. 📈 Performance ML     : comparaison des modèles

Auteur : Abderrahman Amaoulouden
Stack  : Python · Streamlit · Plotly · PostgreSQL · Scikit-learn · XGBoost
"""

import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

# =================================================================
# CONFIGURATION GLOBALE
# =================================================================

load_dotenv()

st.set_page_config(
    page_title="House Prices Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thème Plotly
pio.templates.default = "plotly_dark"

# Config commune à tous les graphiques
PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
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

# Valeurs métier de référence
MEDIAN_PRICE_MARKET = 163_000  # Prix médian du dataset


# =================================================================
# CONNEXION BASE DE DONNÉES
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
    """Exécute une requête SQL (cache 10 min)."""
    return pd.read_sql(query, get_engine())


@st.cache_resource
def load_ml_model():
    """Charge le modèle ML entraîné (cache)."""
    model_path = Path("models/best_model.joblib")
    if not model_path.exists():
        return None
    return joblib.load(model_path)


engine = get_engine()


# =================================================================
# NAVIGATION
# =================================================================

st.sidebar.title("🏠 House Prices")
st.sidebar.caption("Dashboard BI & Machine Learning")

page = st.sidebar.radio(
    "📄 Navigation",
    [
        "📊 Dashboard BI",
        "🤖 Prédiction de prix",
        "📈 Performance du modèle"
    ],
    index=0
)

st.sidebar.markdown("---")


# =================================================================
# PAGE 1 — DASHBOARD BI
# =================================================================

if page == "📊 Dashboard BI":

    # ---------- HEADER ----------
    st.title("🏠 House Prices — Dashboard Analytique")
    st.markdown(
        "Analyse du marché immobilier d'**Ames, Iowa (USA)** "
        "— **1 460 transactions** — "
        "Source : [Kaggle House Prices]"
        "(https://www.kaggle.com/c/house-prices-advanced-regression-techniques)"
    )

    # ---------- SIDEBAR FILTRES ----------
    st.sidebar.header("🔍 Filtres")
    st.sidebar.caption("Affinez votre analyse")

    neighborhoods_df = run_query(
        "SELECT neighborhood_name FROM neighborhoods ORDER BY 1"
    )
    all_neighborhoods = neighborhoods_df['neighborhood_name'].tolist()

    selected_neighborhoods = st.sidebar.multiselect(
        "Quartier",
        options=all_neighborhoods,
        default=all_neighborhoods
    )

    quality_range = st.sidebar.slider(
        "Note de qualité globale",
        min_value=1, max_value=10, value=(1, 10)
    )

    year_range = st.sidebar.slider(
        "Année de construction",
        min_value=1870, max_value=2010, value=(1900, 2010)
    )

    max_price = st.sidebar.slider(
        "Prix maximum ($)",
        min_value=30_000, max_value=800_000,
        value=800_000, step=10_000
    )

    if not selected_neighborhoods:
        st.warning("⚠️ Sélectionnez au moins un quartier dans la barre latérale.")
        st.stop()

    # ---------- CLAUSE WHERE ----------
    neigh_list = "','".join(selected_neighborhoods)
    where_clause = f"""
        n.neighborhood_name IN ('{neigh_list}')
        AND h.overallqual BETWEEN {quality_range[0]} AND {quality_range[1]}
        AND h.yearbuilt BETWEEN {year_range[0]} AND {year_range[1]}
        AND h.saleprice <= {max_price}
    """

    # ---------- KPIs ----------
    kpis = run_query(f"""
        SELECT
            COUNT(*)                                AS total_houses,
            ROUND(AVG(h.saleprice)::numeric, 0)     AS avg_price,
            ROUND(AVG(h.price_per_sf)::numeric, 2)  AS avg_price_per_sf,
            ROUND(AVG(h.total_sf)::numeric, 0)      AS avg_total_sf,
            ROUND(AVG(h.house_age)::numeric, 1)     AS avg_age
        FROM houses h
        JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
        WHERE {where_clause}
    """).iloc[0]

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

    # ---------- LIGNE 1 : Prix par quartier + Distribution ----------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💰 Prix moyen par quartier")
        price_neigh = run_query(f"""
            SELECT n.neighborhood_name,
                   ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price
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
                labels={'saleprice': 'Prix ($)', 'count': 'Nombre'},
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

    # ---------- LIGNE 2 : Scatter + Qualité ----------
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
                   ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price
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
                labels={'overallqual': 'Note de qualité',
                        'avg_price': 'Prix moyen ($)'},
                color='avg_price',
                color_continuous_scale='RdYlGn',
                text='avg_price'
            )
            fig.update_traces(
                texttemplate='$%{text:,.0f}',
                textposition='outside'
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

    # ---------- LIGNE 3 : Évolution temporelle ----------
    st.subheader("📅 Évolution du prix moyen par décennie de construction")
    decade_data = run_query(f"""
        SELECT (h.yearbuilt / 10) * 10 AS decade,
               ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price
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
            hovertemplate='<b>Décennie %{x}</b><br>'
                          'Prix moyen : $%{y:,.0f}<extra></extra>'
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

    # ---------- LIGNE 4 : Impact équipements ----------
    st.subheader("🔎 Impact des équipements sur le prix")
    col1, col2, col3 = st.columns(3)

    def render_equipment_donut(column, col_name, label_map, title, colors_pair):
        """Affiche un donut pour un équipement donné."""
        with column:
            data = run_query(f"""
                SELECT h.{col_name},
                       ROUND(AVG(h.saleprice)::numeric, 0) AS avg_price
                FROM houses h
                JOIN neighborhoods n ON h.neighborhood_id = n.neighborhood_id
                WHERE {where_clause}
                GROUP BY h.{col_name}
            """)
            if not data.empty:
                data['label'] = data[col_name].map(label_map)
                fig = px.pie(
                    data,
                    values='avg_price',
                    names='label',
                    title=title,
                    hole=0.4,
                    color_discrete_sequence=colors_pair
                )
                fig.update_traces(
                    textinfo='percent+label',
                    textposition='inside'
                )
                fig.update_layout(
                    height=350,
                    showlegend=True,
                    margin=dict(l=10, r=10, t=60, b=10),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True,
                                config=PLOTLY_CONFIG)

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

    st.divider()
    st.caption(
        "📊 Dashboard réalisé avec **Streamlit + Plotly + PostgreSQL** "
        "| Dataset : Kaggle House Prices"
    )


# =================================================================
# PAGE 2 — PRÉDICTION DE PRIX
# =================================================================

elif page == "🤖 Prédiction de prix":

    st.title("🤖 Prédiction du prix d'une maison")
    st.markdown(
        "Estimation basée sur un modèle **XGBoost** entraîné sur "
        "**1 460 transactions** — performance : **R² = 0.91**"
    )

    model = load_ml_model()
    if model is None:
        st.error(
            "⚠️ Modèle introuvable.\n\n"
            "Lance d'abord l'entraînement :\n\n"
            "```bash\npython src/train_model.py\n```"
        )
        st.stop()

    st.markdown("### 🏡 Décrivez la maison")

    # ----- FORMULAIRE -----
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 📐 Dimensions")
        gr_liv_area = st.slider("Surface habitable (sqft)", 500, 5000, 1500)
        total_bsmt_sf = st.slider("Surface sous-sol (sqft)", 0, 3000, 1000)
        first_flr_sf = st.slider("Surface 1er étage (sqft)", 300, 3000, 1000)
        second_flr_sf = st.slider("Surface 2ème étage (sqft)", 0, 2000, 500)
        lot_area = st.slider("Terrain (sqft)", 1000, 50000, 9000)
        lot_frontage = st.slider("Façade (ft)", 20, 200, 70)

    with col2:
        st.markdown("#### ⭐ Qualité & équipements")
        overall_qual = st.slider("Qualité globale (1-10)", 1, 10, 6)
        overall_cond = st.slider("État général (1-10)", 1, 10, 5)
        year_built = st.slider("Année de construction", 1870, 2010, 1980)
        year_remod = st.slider("Année de rénovation", 1950, 2010, 1990)
        full_bath = st.slider("Salles de bain complètes", 0, 4, 2)
        half_bath = st.slider("Salles de bain partielles", 0, 3, 1)
        bedroom = st.slider("Chambres", 0, 8, 3)
        tot_rms = st.slider("Pièces totales", 2, 15, 7)
        fireplaces = st.slider("Cheminées", 0, 4, 1)

    with col3:
        st.markdown("#### 🚗 Garage & localisation")
        garage_cars = st.slider("Voitures au garage", 0, 4, 2)
        garage_area = st.slider("Surface garage (sqft)", 0, 1500, 500)

        neighborhood = st.selectbox(
            "Quartier",
            ["NAmes", "CollgCr", "OldTown", "Edwards", "Somerst",
             "Gilbert", "NridgHt", "Sawyer", "NWAmes", "SawyerW",
             "Mitchel", "BrkSide", "Crawfor", "IDOTRR", "Timber",
             "NoRidge", "StoneBr", "ClearCr", "MeadowV", "Blmngtn",
             "SWISU", "NPkVill", "BrDale", "Blueste", "Veenker"]
        )

        st.markdown("#### 🏠 Extérieur")
        mszoning = st.selectbox("Zonage", ["RL", "RM", "FV", "RH", "C (all)"])
        house_style = st.selectbox(
            "Style", ["1Story", "2Story", "1.5Fin", "SLvl", "SFoyer", "2.5Unf"]
        )
        roof_style = st.selectbox("Toit", ["Gable", "Hip", "Flat", "Gambrel"])
        exterior1st = st.selectbox(
            "Revêtement",
            ["VinylSd", "MetalSd", "Wd Sdng", "HdBoard", "BrkFace"]
        )
        bsmt_qual = st.selectbox(
            "Qualité sous-sol", ["Ex", "Gd", "TA", "Fa", "None"]
        )
        central_air = st.selectbox("Climatisation", ["Y", "N"])
        kitchen_qual = st.selectbox("Qualité cuisine", ["Ex", "Gd", "TA", "Fa"])

    # ----- FEATURES DÉRIVÉES -----
    total_sf = total_bsmt_sf + first_flr_sf + second_flr_sf
    total_bath = full_bath + 0.5 * half_bath
    house_age = 2010 - year_built
    remod_age = 2010 - year_remod

    # ----- BOUTON -----
    st.markdown("---")
    predict_clicked = st.button(
        "🎯 Prédire le prix",
        type="primary",
        use_container_width=True
    )

    if predict_clicked:
        input_data = {
            'OverallQual': overall_qual,
            'OverallCond': overall_cond,
            'GrLivArea': gr_liv_area,
            'TotalSF': total_sf,
            'TotalBsmtSF': total_bsmt_sf,
            '1stFlrSF': first_flr_sf,
            '2ndFlrSF': second_flr_sf,
            'GarageArea': garage_area,
            'GarageCars': garage_cars,
            'Fireplaces': fireplaces,
            'FullBath': full_bath,
            'HalfBath': half_bath,
            'BedroomAbvGr': bedroom,
            'TotRmsAbvGrd': tot_rms,
            'LotArea': lot_area,
            'LotFrontage': lot_frontage,
            'YearBuilt': year_built,
            'YearRemodAdd': year_remod,
            'HouseAge': house_age,
            'RemodAge': remod_age,
            'TotalBath': total_bath,
            'WoodDeckSF': 0,
            'OpenPorchSF': 0,
            'Neighborhood': neighborhood,
            'MSZoning': mszoning,
            'HouseStyle': house_style,
            'RoofStyle': roof_style,
            'Exterior1st': exterior1st,
            'BsmtQual': bsmt_qual,
            'CentralAir': central_air,
            'KitchenQual': kitchen_qual,
        }

        try:
            prediction_log = model.predict(pd.DataFrame([input_data]))[0]
            prediction = float(np.expm1(prediction_log))
            diff_pct = (prediction - MEDIAN_PRICE_MARKET) / MEDIAN_PRICE_MARKET * 100

            st.success("### 💰 Prix estimé")
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(
                    f"<h1 style='color: #06A77D; font-size: 3.5em; "
                    f"margin-bottom: 0;'>${prediction:,.0f}</h1>",
                    unsafe_allow_html=True
                )

            with col2:
                st.metric(
                    "Prix / sqft estimé",
                    f"${prediction / total_sf:.2f}"
                )

            with col3:
                st.metric(
                    f"vs médiane (${MEDIAN_PRICE_MARKET // 1000}k)",
                    f"{diff_pct:+.1f}%"
                )

            st.markdown("---")
            direction = "au-dessus" if diff_pct > 0 else "en-dessous"
            st.info(
                f"💡 **Interprétation** : Cette maison est estimée à "
                f"**${prediction:,.0f}**, soit **{direction}** de la "
                f"médiane du marché d'Ames ({abs(diff_pct):.1f} %)."
            )

            with st.expander("📊 Voir les caractéristiques utilisées"):
                st.json(input_data)

        except Exception as e:
            st.error(f"❌ Erreur lors de la prédiction : {e}")

    st.divider()
    st.caption("🤖 Modèle : XGBoost · R² = 0.91 · RMSE ≈ $25 857")


# =================================================================
# PAGE 3 — PERFORMANCE DU MODÈLE
# =================================================================

elif page == "📈 Performance du modèle":

    st.title("📈 Performance du modèle ML")
    st.markdown(
        "Comparaison de **4 modèles de régression** entraînés sur "
        "**1 460 transactions** immobilières."
    )

    metrics_path = Path("models/metrics/results.json")
    if not metrics_path.exists():
        st.error(
            "⚠️ Métriques introuvables.\n\n"
            "Lance d'abord l'entraînement :\n\n"
            "```bash\npython src/train_model.py\n```"
        )
        st.stop()

    with open(metrics_path) as f:
        metrics_data = json.load(f)

    results = pd.DataFrame(metrics_data['all_results'])
    results = results.sort_values('r2', ascending=False)

    # ----- MEILLEUR MODÈLE -----
    st.success(f"🏆 **Meilleur modèle : {metrics_data['best_model']}**")

    # ----- TABLEAU -----
    st.subheader("📊 Comparaison des modèles")

    display_df = results.copy()
    display_df.columns = ["Modèle", "R²", "RMSE ($)", "MAE ($)"]
    st.dataframe(
        display_df.style.format({
            "R²": "{:.4f}",
            "RMSE ($)": "${:,.0f}",
            "MAE ($)": "${:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    # ----- GRAPHIQUES COMPARATIFS -----
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 R² par modèle")
        fig = px.bar(
            results,
            x='model', y='r2',
            color='r2',
            color_continuous_scale='RdYlGn',
            text='r2',
            labels={'model': '', 'r2': 'R²'}
        )
        fig.update_traces(texttemplate='%{text:.4f}', textposition='outside')
        fig.update_layout(
            height=400,
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=30, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_yaxes(range=[0.8, 1.0])
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        st.subheader("📉 RMSE par modèle ($)")
        fig = px.bar(
            results,
            x='model', y='rmse',
            color='rmse',
            color_continuous_scale='RdYlGn_r',
            text='rmse',
            labels={'model': '', 'rmse': 'RMSE ($)'}
        )
        fig.update_traces(
            texttemplate='$%{text:,.0f}',
            textposition='outside'
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=30, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    # ----- EXPLICATIONS -----
    st.markdown("---")
    st.subheader("🎓 Explication des métriques")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
#### 🎯 R²
**Coefficient de détermination**

- `= 1` → prédiction parfaite
- `= 0` → aussi bien que la moyenne
- `< 0` → pire que la moyenne

**Meilleur modèle : 0.91** ✅
""")

    with col2:
        st.markdown("""
#### 📉 RMSE
**Root Mean Squared Error**

Erreur moyenne **en dollars**,
pénalise les grosses erreurs.

**~25 000 \$** sur des prix
moyens de 180 000 \$ (~14 %)
""")

    with col3:
        st.markdown("""
#### 📊 MAE
**Mean Absolute Error**

Erreur absolue moyenne, plus
interprétable que le RMSE.

**~16 000 \$** soit **~9 %**
d'erreur moyenne
""")

    # ----- FEATURES -----
    with st.expander("🔍 Voir les features utilisées par le modèle"):
        features = metrics_data.get('features', {})
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Features numériques**")
            for f in features.get('numeric', []):
                st.markdown(f"- `{f}`")

        with col2:
            st.markdown("**Features catégorielles**")
            for f in features.get('categorical', []):
                st.markdown(f"- `{f}`")

    st.divider()
    st.caption(
        "🤖 Modèles : Ridge · Random Forest · Gradient Boosting · XGBoost"
    )


# =================================================================
# FOOTER
# =================================================================

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 · **Abderrahman Amaoulouden**")
st.sidebar.caption(
    "[🐙 GitHub](https://github.com/abderrahmanamaoulouden533-ops) "
    "· [📊 Dataset](https://www.kaggle.com/c/house-prices-advanced-regression-techniques)"
)