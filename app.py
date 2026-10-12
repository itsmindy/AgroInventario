import io, os, textwrap
from datetime import date
import pandas as pd
import streamlit as st
import plotly.express as px
from supabase import create_client, Client
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from ai_agent import render_agrobot
from chart_agent import render_chart_agent
from mail_agent import render_mail_agent, start_daily_scheduler
st.set_page_config(page_title='AgroInventario',page_icon='🌿',layout='wide')
# ============================================================
# DISEÑO AGROINVENTARIO — NOVA PURPLE & LIME
# ============================================================
st.markdown(textwrap.dedent("""
<style>
:root {
    --purple-dark: #35105F;
    --purple: #7025B8;
    --purple-2: #A832D9;
    --purple-light: #EAD5FF;
    --lime: #A8F23D;
    --green: #179447;
    --green-dark: #0D6B36;
    --pink: #EF71D8;
    --ink: #241536;
    --muted: #718096;
    --bg: #F8F8FC;
    --white: #FFFFFF;
    --line: #E9E4F1;
}
/* FONDO */
.stApp {
    background:
        radial-gradient(
            circle at 80% 10%,
            rgba(177,255,111,.16),
            transparent 25%
        ),
        radial-gradient(
            circle at 20% 5%,
            rgba(190,92,255,.12),
            transparent 25%
        ),
        #F8F8FC;
}
.block-container {
    max-width: 1550px;
    padding-top: 1.1rem;
    padding-bottom: 3rem;
}
/* SIDEBAR */
[data-testid="stSidebar"] {
    background:
        radial-gradient(
            circle at 80% 15%,
            rgba(168,242,61,.18),
            transparent 25%
        ),
        linear-gradient(
            180deg,
            #35105F 0%,
            #4A167D 48%,
            #173C2D 100%
        );
    border-right: none;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
/* HEADER */
.nova-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255,255,255,.78);
    border: 1px solid #E9E4F1;
    border-radius: 24px;
    padding: 18px 24px;
    margin-bottom: 20px;
    box-shadow:
        0 12px 35px rgba(63,24,96,.07);
}
.nova-welcome {
    display: flex;
    align-items: center;
    gap: 14px;
}
.nova-leaf {
    width: 54px;
    height: 54px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 17px;
    background:
        linear-gradient(
            135deg,
            #D8FFAD,
            #76D84B
        );
    font-size: 1.8rem;
}
.nova-welcome-title {
    color: #241536;
    font-size: 1.55rem;
    font-weight: 900;
}
.nova-welcome-sub {
    color: #241536;
    font-size: .94rem;
    margin-top: 5px;
}
/* HERO */
.nova-hero {
    position: relative;
    overflow: hidden;
    padding: 30px;
    border-radius: 26px;
    color: white;
    background:
        radial-gradient(
            circle at 85% 15%,
            rgba(170,255,90,.55),
            transparent 22%
        ),
        radial-gradient(
            circle at 15% 90%,
            rgba(255,104,231,.42),
            transparent 25%
        ),
        linear-gradient(
            110deg,
            #5420A8 0%,
            #8E2BD0 48%,
            #199447 100%
        );
    box-shadow:
        0 18px 45px rgba(85,31,137,.20);
    margin-bottom: 22px;
}
.nova-hero h1 {
    font-size: 2.25rem;
    font-weight: 900;
    margin: 0;
}
.nova-hero p {
    margin: 7px 0 0;
    opacity: .91;
    font-size: 1rem;
}
/* KPI */
.kpi-card {
    min-height: 132px;
    border-radius: 22px;
    padding: 21px 22px;
    border: 1px solid rgba(255,255,255,.7);
    box-shadow:
        0 10px 30px rgba(55,28,85,.09);
}
.kpi-card.purple {
    background:
        linear-gradient(
            135deg,
            #EDC9FF,
            #DBA9FA
        );
}
.kpi-card.green {
    background:
        linear-gradient(
            135deg,
            #D5FFB7,
            #A8EE85
        );
}
.kpi-card.pink {
    background:
        linear-gradient(
            135deg,
            #FFD3F5,
            #E8B1FA
        );
}
.kpi-icon {
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    background: rgba(112,37,184,.88);
    color: white;
    font-size: 1.25rem;
    margin-bottom: 10px;
}
.kpi-card.green .kpi-icon {
    background: rgba(23,148,71,.88);
}
.kpi-label {
    font-size: .75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .6px;
    color: #5B3479;
}
.kpi-value {
    font-size: 1.75rem;
    font-weight: 950;
    color: #211335;
    margin-top: 5px;
}
/* PANELES — FONDOS LIMPIOS + BORDES DE COLOR */
.nova-panel {
    background: #FFFFFF;
    border: 1.5px solid #A832D9;
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 7px 24px rgba(42,23,67,.045);
    height: 100%;
}
.nova-panel:hover {
    border-color: #179447;
    box-shadow: 0 9px 28px rgba(42,23,67,.075);
}
.nova-panel-title {
    display: flex;
    align-items: center;
    gap: 9px;
    color: #35105F;
    font-size: 1.05rem;
    font-weight: 900;
    margin-bottom: 15px;
}
/* BOTONES — ACENTOS MORADO / VERDE */
.stButton > button {
    border-radius: 12px !important;
    border: 1.5px solid #A832D9 !important;
    background: #FFFFFF !important;
    color: #5420A8 !important;
    font-weight: 800 !important;
    transition: all .2s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow:
        0 7px 18px rgba(100,40,150,.14);
}
/* INPUTS — BORDES */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea,
input {
    border-radius: 12px !important;
    border: 1.5px solid #D8B9F0 !important;
}
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="input"] > div:focus-within,
textarea:focus,
input:focus {
    border-color: #179447 !important;
    box-shadow: 0 0 0 2px rgba(23,148,71,.10) !important;
}
/* METRICS — BORDES */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border-radius: 18px;
    border: 1.5px solid #A832D9;
    padding: 15px;
    box-shadow: 0 7px 22px rgba(48,26,70,.05);
}
/* TABLAS */
[data-testid="stDataFrame"] {
    border: 1.5px solid #A832D9;
    border-radius: 16px;
    overflow: hidden;
}
/* TABS */
button[data-baseweb="tab"] {
    color: #5420A8 !important;
    font-weight: 800 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #179447 !important;
}
/* EXPANDERS */
[data-testid="stExpander"] {
    border: 1.5px solid #D8B9F0;
    border-radius: 16px;
}
/* FORMULARIOS */
[data-testid="stForm"] {
    border: 1.5px solid #A832D9;
    border-radius: 18px;
    padding: 18px;
}
/* SEPARADORES */
hr {
    border-color: #E4D5EF !important;
}
/* ==========================================================
   SALIDAS — TARJETAS PREMIUM
   Solo diseño. NO modifica la lógica.
   ========================================================== */
.salida-info-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin: 12px 0 18px 0;
}
.salida-card {
    min-height: 118px;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
    border-radius: 18px;
    padding: 18px 20px;
    background: #FFFFFF;
    border: 2px solid #A832D9;
    box-shadow: 0 8px 24px rgba(86, 34, 125, .09);
    transition: transform .18s ease, box-shadow .18s ease;
}
.salida-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 28px rgba(86, 34, 125, .14);
}
/* franja superior de color */
.salida-card::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 5px;
    background: linear-gradient(90deg, #A832D9, #EF71D8);
}
.salida-card.stock {
    border-color: #77C83F;
    background: linear-gradient(135deg, #FFFFFF 0%, #F7FFF1 100%);
}
.salida-card.stock::before {
    background: linear-gradient(90deg, #179447, #A8F23D);
}
.salida-card.sale {
    border-color: #A832D9;
    background: linear-gradient(135deg, #FFFFFF 0%, #FCF5FF 100%);
}
.salida-card.sale::before {
    background: linear-gradient(90deg, #7025B8, #EF71D8);
}
.salida-card.cost {
    border-color: #179447;
    background: linear-gradient(135deg, #FFFFFF 0%, #F2FFF7 100%);
}
.salida-card.cost::before {
    background: linear-gradient(90deg, #0D6B36, #A8F23D);
}
.salida-card-top {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #392A49;
    font-size: .76rem;
    font-weight: 900;
    letter-spacing: .45px;
}
.salida-card-icon {
    width: 38px;
    height: 38px;
    flex: 0 0 38px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #EEDCFF;
    color: #7025B8;
    font-size: 1.12rem;
    box-shadow: inset 0 0 0 1px rgba(112,37,184,.08);
}
.salida-card.stock .salida-card-icon {
    background: #DFFFBE;
    color: #16803C;
}
.salida-card.cost .salida-card-icon {
    background: #D9F9E5;
    color: #087A36;
}
.salida-card-value {
    margin-top: 9px;
    font-size: 1.72rem;
    line-height: 1;
    font-weight: 950;
    letter-spacing: -.35px;
    color: #241536;
}
.salida-card.stock .salida-card-value {
    color: #16803C;
}
.salida-card.sale .salida-card-value {
    color: #7025B8;
}
.salida-card.cost .salida-card-value {
    color: #087A36;
}
.salida-card-note {
    margin-top: 7px;
    color: #766B81;
    font-size: .72rem;
    font-weight: 600;
}
/* Total de línea */
.salida-total {
    padding: 13px 17px;
    margin: 8px 0 16px 0;
    border: 1.5px solid #D5B4EF;
    border-left: 5px solid #A832D9;
    border-radius: 13px;
    background: linear-gradient(90deg, #FCF7FF, #FFFFFF);
    color: #33253F;
    font-size: .94rem;
    font-weight: 700;
}
.salida-total strong {
    color: #5420A8;
    font-weight: 900;
}
@media (max-width: 850px) {
    .salida-info-grid {
        grid-template-columns: 1fr;
    }
}
/* RESUMEN DE SALIDA */
div[data-testid="stMetric"] {
    border: 2px solid #A832D9 !important;
    border-radius: 18px !important;
    background: #FFFFFF !important;
}
div[data-testid="stMetricLabel"] {
    color: #4B3B5A !important;
    font-weight: 900 !important;
}
div[data-testid="stMetricValue"] {
    color: #35105F !important;
    font-weight: 950 !important;
}
/* ACCIONES DE SALIDAS */
div[data-testid="stButton"] button[kind="secondary"] {
    border-width: 1.8px !important;
}
/* ==========================================================
   SALIDAS — DISEÑO PREMIUM
   Morado + fucsia + verde lima
   Solo presentación. No modifica la lógica.
   ========================================================== */
.salida-cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    width: 100%;
    margin: 12px 0 18px 0;
}
.salida-card-premium {
    position: relative;
    min-height: 124px;
    padding: 17px 19px 15px 19px;
    box-sizing: border-box;
    overflow: hidden;
    background: #FFFFFF;
    border-radius: 18px;
    border: 2px solid #A832D9;
    box-shadow:
        0 7px 22px rgba(91, 36, 130, .09);
    transition:
        transform .18s ease,
        box-shadow .18s ease;
}
.salida-card-premium:hover {
    transform: translateY(-2px);
    box-shadow:
        0 12px 28px rgba(91, 36, 130, .15);
}
/* Franja superior */
.salida-card-premium::before {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 5px;
    background: linear-gradient(
        90deg,
        #7025B8,
        #A832D9,
        #EF71D8
    );
}
.salida-card-premium.stock-card {
    border-color: #75C93B;
    background: linear-gradient(
        135deg,
        #FFFFFF 0%,
        #F6FFF0 100%
    );
}
.salida-card-premium.stock-card::before {
    background: linear-gradient(
        90deg,
        #179447,
        #A8F23D
    );
}
.salida-card-premium.sale-card {
    border-color: #A832D9;
    background: linear-gradient(
        135deg,
        #FFFFFF 0%,
        #FBF2FF 100%
    );
}
.salida-card-premium.sale-card::before {
    background: linear-gradient(
        90deg,
        #5420A8,
        #EF71D8
    );
}
.salida-card-premium.cost-card {
    border-color: #179447;
    background: linear-gradient(
        135deg,
        #FFFFFF 0%,
        #F1FFF6 100%
    );
}
.salida-card-premium.cost-card::before {
    background: linear-gradient(
        90deg,
        #0D6B36,
        #A8F23D
    );
}
.salida-card-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 2px;
    color: #392A49;
    font-size: .75rem;
    font-weight: 900;
    letter-spacing: .45px;
}
.salida-card-icon {
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 11px;
    background: #EEDCFF;
    color: #7025B8;
    font-size: 1.05rem;
}
.stock-card .salida-card-icon {
    background: #DFFFC4;
    color: #16803C;
}
.cost-card .salida-card-icon {
    background: #D9F9E5;
    color: #087A36;
}
.salida-card-number {
    margin-top: 8px;
    color: #241536;
    font-size: 1.55rem;
    line-height: 1.05;
    font-weight: 950;
    letter-spacing: -.25px;
}
.stock-card .salida-card-number {
    color: #16803C;
}
.sale-card .salida-card-number {
    color: #7025B8;
}
.cost-card .salida-card-number {
    color: #087A36;
}
.salida-card-description {
    margin-top: 6px;
    color: #776D82;
    font-size: .70rem;
    font-weight: 650;
}
/* Total de la línea */
.salida-line-total {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    box-sizing: border-box;
    margin: 8px 0 16px 0;
    padding: 12px 16px;
    border-radius: 13px;
    border: 1.5px solid #D5B4EF;
    border-left: 5px solid #A832D9;
    background: linear-gradient(
        90deg,
        #FCF7FF,
        #FFFFFF
    );
    color: #392A49;
    font-size: .92rem;
    font-weight: 750;
}
.salida-line-total strong {
    color: #5420A8;
    font-weight: 950;
}
/* Resumen TOTAL VENTA / COSTO / UTILIDAD */
.salida-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin: 18px 0;
}
.salida-summary-card {
    min-height: 108px;
    box-sizing: border-box;
    padding: 16px 19px;
    background: #FFFFFF;
    border-radius: 18px;
    border: 2px solid #A832D9;
    box-shadow:
        0 7px 22px rgba(91, 36, 130, .07);
}
.salida-summary-card:nth-child(2) {
    border-color: #179447;
}
.salida-summary-card:nth-child(3) {
    border-color: #A8F23D;
}
.salida-summary-label {
    color: #4B3B5A;
    font-size: .73rem;
    font-weight: 900;
    letter-spacing: .45px;
}
.salida-summary-value {
    margin-top: 8px;
    color: #35105F;
    font-size: 1.65rem;
    line-height: 1;
    font-weight: 950;
}
.salida-summary-card:nth-child(2) .salida-summary-value {
    color: #16803C;
}
.salida-summary-card:nth-child(3) .salida-summary-value {
    color: #5420A8;
}
@media (max-width: 850px) {
    .salida-cards,
    .salida-summary {
        grid-template-columns: 1fr;
    }
}
/* LIMPIEZA */
#MainMenu {
    visibility: hidden;
}
footer {
    visibility: hidden;
}
header[data-testid="stHeader"] {
    background: transparent;
}
/* SCROLLBAR */
::-webkit-scrollbar {
    width: 8px;
}
::-webkit-scrollbar-track {
    background: #F6F3F9;
}
::-webkit-scrollbar-thumb {
    background:
        linear-gradient(
            #A832D9,
            #78D83F
        );
    border-radius: 20px;
}
/* =========================================================
   TIPOGRAFIA GENERAL — 14 PX
   Solo se modifica el tamano de letra.
   ========================================================= */
.stApp p,
.stApp span,
.stApp label,
.stApp li,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] li,
.stButton button,
.stDownloadButton button,
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea,
[data-baseweb="select"] *,
[data-testid="stDataFrame"] *,
[data-testid="stAlert"] *,
[data-testid="stExpander"] *,
button[data-baseweb="tab"],
small {
    font-size: 16px !important;
}
/* Textos propios de AgroInventario */
.nova-welcome-title,
.nova-welcome-sub,
.nova-hero h1,
.nova-hero p,
.nova-panel-title,
.kpi-label,
.kpi-value,
.salida-card-title,
.salida-card-description,
.salida-card-note,
.salida-card-number,
.salida-card-value,
.salida-line-total,
.salida-summary-label,
.salida-summary-value {
    font-size: 16px !important;
}
/* Las metricas mantienen una lectura clara, pero tambien se ajustan a 14 px. */
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    font-size: 16px !important;
}
/* =========================================================
   JERARQUÍA TIPOGRÁFICA DEL SISTEMA
   TÍTULOS: 30 PX
   SUBTÍTULOS: 25 PX
   ESCRITURA GENERAL: 16 PX
   ========================================================= */
/* Escritura general */
.stApp p,
.stApp span,
.stApp label,
.stApp li,
.stApp div,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] li,
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea,
[data-baseweb="select"] *,
[data-testid="stDataFrame"] *,
[data-testid="stAlert"] *,
[data-testid="stExpander"] *,
.stButton button,
.stDownloadButton button,
button[data-baseweb="tab"],
small {
    font-size: 16px !important;
}
/* TÍTULOS PRINCIPALES */
.stApp h1,
.stApp h1 *,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h1 * {
    font-size: 30px !important;
    line-height: 1.2 !important;
    font-weight: 900 !important;
}
/* SUBTÍTULOS */
.stApp h2,
.stApp h2 *,
.stApp h3,
.stApp h3 *,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h2 *,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h3 * {
    font-size: 25px !important;
    line-height: 1.25 !important;
    font-weight: 800 !important;
}
/* Título de bienvenida */
.nova-welcome-title {
    font-size: 30px !important;
    line-height: 1.2 !important;
}
/* Subtítulo de bienvenida */
.nova-welcome-sub {
    font-size: 16px !important;
}
/* Título del banner principal */
.nova-hero h1 {
    font-size: 30px !important;
    line-height: 1.2 !important;
}
/* Texto del banner */
.nova-hero p {
    font-size: 16px !important;
}
/* Títulos de paneles */
.nova-panel-title {
    font-size: 25px !important;
    line-height: 1.25 !important;
}
/* Sidebar */
[data-testid="stSidebar"] .stRadio label {
    font-size: 16px !important;
    font-weight: 700 !important;
}
/* Etiquetas de tarjetas KPI */
.kpi-label {
    font-size: 16px !important;
}
/* Textos de tarjetas de salida */
.salida-card-top,
.salida-card-note,
.salida-total,
.salida-total strong,
.salida-card-title {
    font-size: 16px !important;
}
/* No reducir los valores numéricos de las tarjetas */
.kpi-value,
.salida-card-value {
    font-size: 28px !important;
}
/* Métricas */
[data-testid="stMetricLabel"] {
    font-size: 16px !important;
}
[data-testid="stMetricValue"] {
    font-size: 28px !important;
}
/* TIPOGRAFÍA GLOBAL — títulos 30, subtítulos 25, texto 16 */
html, body, [class*="css"], .stApp, .stMarkdown, .stText, label,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
[data-testid="stDataFrame"], .stSelectbox, .stTextInput, .stNumberInput,
.stDateInput, .stTextArea, .stButton, .stRadio, .stCheckbox, .stCaption {
    font-size: 16px !important;
}
.nova-welcome-title, .nova-hero h1, .hero h1, .section, .section-title,
[data-testid="stHeader"] h1 { font-size: 30px !important; font-weight: 900 !important; }
.nova-welcome-sub, .nova-panel-title, h2, .subtitulo, .section-subtitle {
    font-size: 25px !important; font-weight: 800 !important;
}
h3 { font-size: 22px !important; font-weight: 800 !important; }
[data-testid="stSidebar"] * { font-size: 16px !important; }
[data-testid="stMetricLabel"] { font-size: 16px !important; }
[data-testid="stMetricValue"] { font-size: 28px !important; }
.stCaption, [data-testid="stCaptionContainer"] { font-size: 16px !important; }
/* SIDEBAR NAV — NOVA PURPLE & LIME */
[data-testid="stSidebar"] {
    padding-top: 1rem;
}
.sidebar-group-title {
    margin: 12px 0 7px 2px;
    color: #CFFFA0;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 1px;
}
[data-testid="stSidebar"] [data-testid="stButton"] {
    margin: 3px 0;
}
[data-testid="stSidebar"] [data-testid="stButton"] button {
    min-height: 43px;
    justify-content: flex-start;
    text-align: left;
    border: 1px solid rgba(255,255,255,.12) !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,.06) !important;
    color: #FFFFFF !important;
    font-weight: 750 !important;
    transition: background .18s ease, border-color .18s ease, transform .18s ease;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: rgba(255,255,255,.14) !important;
    border-color: #A8F23D !important;
    transform: translateX(2px);
}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(100deg, #7025B8, #5420A8) !important;
    border-color: #A8F23D !important;
    box-shadow: inset 3px 0 0 #A8F23D, 0 5px 16px rgba(0,0,0,.12);
}
/* Paneles de gráficos: encabezados HTML autocontenidos */
.nova-panel-title {
    display: flex;
    align-items: center;
    gap: 9px;
    color: #35105F;
    font-size: 1.05rem;
    font-weight: 900;
    margin: 0 0 12px 0;
    padding: 12px 14px;
    background: #FFFFFF;
    border: 1.5px solid #D8B9F0;
    border-radius: 14px;
}
</style>
"""), unsafe_allow_html=True)
@st.cache_resource
def db()->Client:
    url=st.secrets.get('SUPABASE_URL',os.getenv('SUPABASE_URL'))
    key=st.secrets.get('SUPABASE_KEY',os.getenv('SUPABASE_KEY'))
    if not url or not key: raise RuntimeError('Configura SUPABASE_URL y SUPABASE_KEY en .streamlit/secrets.toml')
    return create_client(url,key)
try: sb=db()
except Exception as e: st.error(str(e)); st.stop()
# Si las credenciales y el destinatario están configurados, inicia la programación diaria
# al arrancar el proceso. El proceso de Streamlit debe permanecer activo.
try:
    _mail_to = st.secrets.get("GMAIL_REPORT_TO", os.getenv("GMAIL_REPORT_TO"))
    _mail_sender = st.secrets.get("GMAIL_SENDER", os.getenv("GMAIL_SENDER"))
    _mail_password = st.secrets.get("GMAIL_APP_PASSWORD", os.getenv("GMAIL_APP_PASSWORD"))
    if _mail_to and _mail_sender and _mail_password:
        start_daily_scheduler(sb)
except Exception as _mail_scheduler_error:
    # La aplicación principal sigue funcionando; AgroMail mostrará el estado al abrirse.
    pass
def get(table,cols='*',order=None):
    q=sb.table(table).select(cols)
    if order:q=q.order(order)
    return q.execute().data or []
def money(x): return f'S/ {float(x or 0):,.2f}'
def _num(v):
    try: return float(v or 0)
    except Exception: return 0.0
@st.cache_data(ttl=20)
def sales_confirmed_df():
    try:
        d=pd.DataFrame(get('salidas','id,numero,fecha,tipo_salida,id_cliente,id_empleado,numero_documento,estado,total_venta,total_costo,utilidad','fecha'))
        if d.empty: return d
        d=d[(d.tipo_salida=='VENTA') & (d.estado=='CONFIRMADO')].copy()
        for c in ['total_venta','total_costo','utilidad']: d[c]=pd.to_numeric(d[c],errors='coerce').fillna(0)
        return d
    except Exception: return pd.DataFrame()
@st.cache_data(ttl=20)
def sales_detail_df():
    try:
        d=pd.DataFrame(get('detalle_salidas','*'))
        return d
    except Exception: return pd.DataFrame()
@st.cache_data(ttl=20)
def purchase_df():
    try:
        d=pd.DataFrame(get('ingresos','*','fecha'))
        if d.empty: return d
        d=d[d.estado=='CONFIRMADO'].copy()
        if 'total' in d: d['total']=pd.to_numeric(d['total'],errors='coerce').fillna(0)
        return d
    except Exception: return pd.DataFrame()
@st.cache_data(ttl=20)
def intelligent_stock_df():
    d=pd.DataFrame(products())
    if d.empty: return d
    d['stock']=pd.to_numeric(d['stock'],errors='coerce').fillna(0)
    d['stock_minimo']=pd.to_numeric(d['stock_minimo'],errors='coerce').fillna(0)
    d['precio_compra']=pd.to_numeric(d['precio_compra'],errors='coerce').fillna(0)
    d['precio_venta']=pd.to_numeric(d['precio_venta'],errors='coerce').fillna(0)
    d['valor_costo']=d.stock*d.precio_compra
    d['valor_venta']=d.stock*d.precio_venta
    d['utilidad_potencial']=d.valor_venta-d.valor_costo
    d['cobertura_dias']=None
    s=sales_confirmed_df()
    det=sales_detail_df()
    if not s.empty and not det.empty and 'fecha' in s.columns:
        det=det.copy()
        det['cantidad']=pd.to_numeric(det.get('cantidad',0),errors='coerce').fillna(0)
        det=det.merge(s[['id','fecha']],left_on='id_salida',right_on='id',how='inner')
        det['fecha']=pd.to_datetime(det['fecha'],errors='coerce')
        cutoff=pd.Timestamp.today()-pd.Timedelta(days=30)
        det=det[det.fecha>=cutoff]
        cons=det.groupby('id_producto')['cantidad'].sum()/30
        d['consumo_diario_30d']=d['id_producto'].map(cons).fillna(0)
        d['cobertura_dias']=d.apply(lambda r: (r.stock/r.consumo_diario_30d) if r.consumo_diario_30d>0 else None,axis=1)
        def risk(r):
            if r.stock<=0: return 'SIN STOCK'
            if r.stock<=r.stock_minimo: return 'CRÍTICO'
            if r.consumo_diario_30d>0 and r.cobertura_dias<=7: return 'REPOSICIÓN URGENTE'
            if r.consumo_diario_30d>0 and r.cobertura_dias<=15: return 'VIGILANCIA'
            return 'NORMAL'
        d['riesgo']=d.apply(risk,axis=1)
    else:
        d['consumo_diario_30d']=0
        d['riesgo']=d.apply(lambda r:'SIN STOCK' if r.stock<=0 else ('CRÍTICO' if r.stock<=r.stock_minimo else 'NORMAL'),axis=1)
    return d
@st.cache_data(ttl=15)
def products(): return get('v_stock','*','codigo')
@st.cache_data(ttl=30)
def master(t): return get(t,'*','nombre')
@st.cache_data(ttl=30)
def people(t):
    orden = 'apellidos' if t == 'empleados' else 'razon_social'
    return get(t, '*', orden)
def refresh():
    products.clear(); master.clear(); people.clear(); sales_confirmed_df.clear(); sales_detail_df.clear(); purchase_df.clear(); intelligent_stock_df.clear()
def pdf(title,headers,data):
    b=io.BytesIO(); doc=SimpleDocTemplate(b,pagesize=A4,leftMargin=10*mm,rightMargin=10*mm,topMargin=10*mm,bottomMargin=10*mm)
    s=getSampleStyleSheet(); stx=ParagraphStyle('x',parent=s['Title'],fontSize=18,textColor=colors.HexColor('#172A46'))
    story=[Paragraph(title,stx),Spacer(1,8)]
    t=Table([headers]+[[str(v) for v in r] for r in data],repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#172A46')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#CCD3DF')),('FONTSIZE',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F7FA')])]))
    story.append(t);doc.build(story);return b.getvalue()
with st.sidebar:
    st.markdown("## 🌿 AgroInventario")
    st.caption("INVENTARIO · COMPRAS · SALIDAS")
    # Menú único con secciones visuales y navegación estable.
    grupos_menu = {
        "✦ CENTRO INTELIGENTE": [
            "🤖 AgroBot",
            "📈 AgroCharts",
            "✉️ AgroMail",
        ],
        "✦ OPERACIONES": [
            "📊 Dashboard",
            "📦 Productos",
            "📥 Ingresos",
            "📤 Salidas",
            "📜 Kardex",
            "🚨 Alertas",
        ],
        "✦ ADMINISTRACIÓN": [
            "🏢 Proveedores y clientes",
            "👷 Empleados",
            "⚙️ Maestros",
            "📊 Reportes",
        ],
    }
    opciones_menu = [
        opcion
        for opciones in grupos_menu.values()
        for opcion in opciones
    ]
    if st.session_state.get("menu_activo") not in opciones_menu:
        st.session_state["menu_activo"] = "🤖 AgroBot"
    for titulo_grupo, opciones_grupo in grupos_menu.items():
        st.markdown(
            f'<div class="sidebar-group-title">{titulo_grupo}</div>',
            unsafe_allow_html=True,
        )
        for opcion in opciones_grupo:
            activo = st.session_state["menu_activo"] == opcion
            if st.button(
                opcion,
                key=f"nav_{opcion}",
                use_container_width=True,
                type="primary" if activo else "secondary",
            ):
                st.session_state["menu_activo"] = opcion
                st.rerun()
    menu = st.session_state["menu_activo"]
    st.markdown("---")
    if st.button("🔄 Actualizar datos", key="actualizar_datos", use_container_width=True):
        refresh()
        st.rerun()
st.markdown('<div class="hero"><h1>🌿 AgroInventario</h1><p>Control de inventario y operaciones</p></div>',unsafe_allow_html=True)
if menu=='🤖 AgroBot':
    render_agrobot(sb)
elif menu=='📊 Dashboard':
    d=pd.DataFrame(products())
    # ========================================================
    # DASHBOARD PREMIUM — SOLO PRESENTACIÓN Y GRÁFICOS
    # No modifica ninguna de las funciones existentes.
    # ========================================================
    total=len(d)
    stock=float(d.stock.sum()) if not d.empty else 0
    low=int(d.stock_bajo.sum()) if not d.empty else 0
    value=float((d.stock*d.precio_compra).sum()) if not d.empty else 0
    st.markdown(textwrap.dedent("""
    <div class="nova-header">
        <div class="nova-welcome">
            <div class="nova-leaf">🌱</div>
            <div>
                <div class="nova-welcome-title">¡Bienvenida a AgroInventario!</div>
                <div class="nova-welcome-sub">Panel de control general</div>
                <div style="color:#718096;font-size:.76rem;margin-top:4px;">
                    Visualiza el estado de tu inventario de forma rápida y clara.
                </div>
            </div>
        </div>
        <div style="
            background:#F4EFF9;
            padding:11px 18px;
            border-radius:999px;
            color:#5420A8;
            font-weight:800;
            font-size:.80rem;">
            📊 INVENTARIO EN TIEMPO REAL
        </div>
    </div>
    """),unsafe_allow_html=True)
    st.markdown(textwrap.dedent("""
    <div class="nova-hero">
        <div style="position:relative;z-index:2;">
            <div style="font-size:.72rem;font-weight:900;letter-spacing:1.2px;opacity:.85;">
                AGROINVENTARIO
            </div>
            <h1>Control inteligente de tu inventario</h1>
            <p>
                Existencias, valorización y alertas en un solo lugar.
            </p>
        </div>
        <div style="
            position:absolute;
            right:35px;
            bottom:-25px;
            font-size:7rem;
            opacity:.18;">
            🥑
        </div>
    </div>
    """),unsafe_allow_html=True)
    # ========================= KPI ==========================
    a,b,c,e=st.columns(4)
    a.markdown(f"""
    <div class="kpi-card purple">
        <div class="kpi-icon">📦</div>
        <div class="kpi-label">Productos</div>
        <div class="kpi-value">{total:,}</div>
    </div>
    """,unsafe_allow_html=True)
    b.markdown(f"""
    <div class="kpi-card green">
        <div class="kpi-icon">📊</div>
        <div class="kpi-label">Unidades disponibles</div>
        <div class="kpi-value">{stock:,.0f}</div>
    </div>
    """,unsafe_allow_html=True)
    c.markdown(f"""
    <div class="kpi-card pink">
        <div class="kpi-icon">💰</div>
        <div class="kpi-label">Valor del inventario</div>
        <div class="kpi-value">{money(value)}</div>
    </div>
    """,unsafe_allow_html=True)
    e.markdown(f"""
    <div class="kpi-card green">
        <div class="kpi-icon">🚨</div>
        <div class="kpi-label">Stock bajo</div>
        <div class="kpi-value">{low:,}</div>
    </div>
    """,unsafe_allow_html=True)
    # ================= KPIs COMERCIALES =====================
    sv=sales_confirmed_df(); pu=purchase_df()
    ventas_mes=0; utilidad_mes=0; compras_mes=0; margen_mes=0
    if not sv.empty:
        sv['fecha_dt']=pd.to_datetime(sv['fecha'],errors='coerce')
        now=pd.Timestamp.today()
        m=sv[(sv.fecha_dt.dt.year==now.year)&(sv.fecha_dt.dt.month==now.month)]
        ventas_mes=float(m.total_venta.sum()); utilidad_mes=float(m.utilidad.sum())
        margen_mes=(utilidad_mes/ventas_mes*100) if ventas_mes else 0
    if not pu.empty:
        pu['fecha_dt']=pd.to_datetime(pu['fecha'],errors='coerce')
        now=pd.Timestamp.today(); compras_mes=float(pu[(pu.fecha_dt.dt.year==now.year)&(pu.fecha_dt.dt.month==now.month)].total.sum())
    st.markdown('<div class="subtitulo">📈 Indicadores comerciales</div>',unsafe_allow_html=True)
    q1,q2,q3,q4=st.columns(4)
    q1.markdown(f'<div class="kpi-card purple"><div class="kpi-label">VENTAS DEL MES</div><div class="kpi-value">{money(ventas_mes)}</div></div>',unsafe_allow_html=True)
    q2.markdown(f'<div class="kpi-card pink"><div class="kpi-label">UTILIDAD DEL MES</div><div class="kpi-value">{money(utilidad_mes)}</div></div>',unsafe_allow_html=True)
    q3.markdown(f'<div class="kpi-card green"><div class="kpi-label">COMPRAS DEL MES</div><div class="kpi-value">{money(compras_mes)}</div></div>',unsafe_allow_html=True)
    q4.markdown(f'<div class="kpi-card green"><div class="kpi-label">MARGEN DEL MES</div><div class="kpi-value">{margen_mes:.1f}%</div></div>',unsafe_allow_html=True)
    if not sv.empty:
        st.markdown('<div class="subtitulo">📊 Rendimiento comercial</div>',unsafe_allow_html=True)
        cventas,cvendedores=st.columns(2)
        sv['fecha_dt']=pd.to_datetime(sv['fecha'],errors='coerce')
        monthly=sv.groupby(sv.fecha_dt.dt.to_period('M').astype(str),as_index=False).agg(ventas=('total_venta','sum'),utilidad=('utilidad','sum'))
        with cventas:
            figv=px.bar(monthly,x='fecha_dt',y='ventas',text='ventas',labels={'fecha_dt':'Mes','ventas':'Ventas'})
            figv.update_traces(marker_color='#8E2BD0',texttemplate='S/ %{text:,.0f}',textposition='outside')
            figv.update_layout(height=330,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',showlegend=False)
            st.plotly_chart(figv,use_container_width=True,key='ventas_mensuales_analytics')
        with cvendedores:
            em=pd.DataFrame(get('empleados','id,nombres,apellidos','apellidos'))
            rank=sv.groupby('id_empleado',as_index=False).agg(ventas=('total_venta','sum'),utilidad=('utilidad','sum'),operaciones=('id','count'))
            if not em.empty: rank=rank.merge(em,left_on='id_empleado',right_on='id',how='left'); rank['empleado']=rank['nombres'].fillna('')+' '+rank['apellidos'].fillna('')
            else: rank['empleado']='Sin empleado'
            rank=rank.sort_values('ventas',ascending=False).head(7)
            fige=px.bar(rank.sort_values('ventas'),x='ventas',y='empleado',orientation='h',text='ventas',labels={'ventas':'Ventas','empleado':'Empleado'})
            fige.update_traces(marker_color='#A8F23D',texttemplate='S/ %{text:,.0f}',textposition='outside')
            fige.update_layout(height=330,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',showlegend=False)
            st.plotly_chart(fige,use_container_width=True,key='ventas_empleados_analytics')
    st.markdown('<div class="subtitulo">🧠 Salud inteligente del stock</div>',unsafe_allow_html=True)
    intel=intelligent_stock_df()
    if not intel.empty:
        risk_counts=intel.groupby('riesgo').size().reset_index(name='productos')
        rc1,rc2=st.columns([1,1.6])
        with rc1: st.dataframe(risk_counts,use_container_width=True,hide_index=True)
        with rc2:
            critical=intel[intel.riesgo!='NORMAL'][['codigo','nombre','stock','stock_minimo','consumo_diario_30d','cobertura_dias','riesgo']].copy()
            if not critical.empty:
                critical['cobertura_dias']=critical['cobertura_dias'].round(1)
                st.dataframe(critical.sort_values(['riesgo','stock']),use_container_width=True,hide_index=True)
            else: st.success('✅ No hay riesgos de reposición detectados con el consumo reciente.')
    st.markdown("<div style='height:25px'></div>",unsafe_allow_html=True)
    # ================= GRÁFICOS =============================
    if not d.empty:
        # --------- GRÁFICO 1: BARRAS POR CATEGORÍA ---------
        if 'categoria' in d.columns:
            cat=d.groupby('categoria',as_index=False)['stock'].sum()
            cat=cat.sort_values('stock',ascending=False)
            izquierda,derecha=st.columns([1.45,1])
            with izquierda:
                st.markdown(textwrap.dedent("""
                    <div class="nova-panel-title">
                        📊 Stock por categoría
                    </div>
                """),unsafe_allow_html=True)
                fig=px.bar(
                    cat,
                    x='categoria',
                    y='stock',
                    text='stock'
                )
                fig.update_traces(
                    marker_color='#8E2BD0',
                    texttemplate='%{text:,.0f}',
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>Stock: %{y:,.0f}<extra></extra>'
                )
                fig.update_layout(
                    height=370,
                    margin=dict(l=10,r=10,t=20,b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#4B3B5A'),
                    xaxis=dict(title=None,showgrid=False),
                    yaxis=dict(title='Unidades',gridcolor='#EEE8F4'),
                    showlegend=False
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={'displayModeBar':False},
                    key='dashboard_stock_categoria'
                )
            # -------- GRÁFICO 2: CIRCULAR --------------------
            with derecha:
                st.markdown(textwrap.dedent("""
                    <div class="nova-panel-title">
                        🍩 Valor del inventario por categoría
                    </div>
                """),unsafe_allow_html=True)
                # El circular muestra VALOR ECONÓMICO,
                # mientras que el gráfico de barras muestra UNIDADES.
                cat_valor=cat.copy()
                cat_valor['valor_inventario']=cat_valor['stock'] * (
                    d.groupby('categoria')['precio_compra'].first()
                    .reindex(cat_valor['categoria'])
                    .fillna(0)
                    .values
                )
                fig2=px.pie(
                    cat_valor,
                    names='categoria',
                    values='valor_inventario',
                    hole=.58
                )
                fig2.update_traces(
                    textposition='inside',
                    textinfo='percent',
                    hovertemplate='<b>%{label}</b><br>Valor: S/ %{value:,.2f}<br>%{percent}<extra></extra>',
                    marker=dict(
                        colors=[
                            '#A832D9',
                            '#A8F23D',
                            '#EF71D8',
                            '#5420A8',
                            '#179447',
                            '#D8A7FF'
                        ]
                    )
                )
                fig2.update_layout(
                    height=370,
                    margin=dict(l=5,r=5,t=10,b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#4B3B5A'),
                    legend=dict(
                        orientation='h',
                        y=-.05,
                        x=.5,
                        xanchor='center'
                    )
                )
                st.plotly_chart(
                    fig2,
                    use_container_width=True,
                    config={'displayModeBar':False},
                    key='dashboard_stock_circular'
                )
        # -------- GRÁFICO 3: TOP PRODUCTOS -----------------
        nombre='nombre' if 'nombre' in d.columns else 'codigo'
        top=d[['codigo',nombre,'stock']].copy()
        top=top.sort_values('stock',ascending=False).head(7)
        top=top.sort_values('stock',ascending=True)
        st.markdown("<div style='height:22px'></div>",unsafe_allow_html=True)
        st.markdown(textwrap.dedent("""
            <div class="nova-panel-title">
                🏆 Productos con mayor stock
            </div>
        """),unsafe_allow_html=True)
        fig3=px.bar(
            top,
            x='stock',
            y=nombre,
            orientation='h',
            text='stock'
        )
        fig3.update_traces(
            marker_color='#A8F23D',
            texttemplate='%{text:,.0f}',
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Stock: %{x:,.0f}<extra></extra>'
        )
        fig3.update_layout(
            height=380,
            margin=dict(l=10,r=50,t=15,b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#4B3B5A'),
            xaxis=dict(title='Unidades',gridcolor='#EEE8F4'),
            yaxis=dict(title=None,showgrid=False),
            showlegend=False
        )
        st.plotly_chart(
            fig3,
            use_container_width=True,
            config={'displayModeBar':False},
            key='dashboard_top_productos'
        )
        # -------- RESUMEN INFERIOR --------------------------
        st.markdown("<div style='height:22px'></div>",unsafe_allow_html=True)
        r1,r2,r3=st.columns(3)
        r1.markdown(f"""
            <div style="font-size:.75rem;color:#718096;font-weight:800;">
                VALOR A COSTO
            </div>
            <div style="font-size:1.8rem;font-weight:900;color:#35105F;margin-top:7px;">
                {money(value)}
            </div>
            <div style="color:#718096;font-size:.78rem;margin-top:5px;">
                Valorización actual del inventario
            </div>
        </div>
        """,unsafe_allow_html=True)
        venta=float((d.stock*d.precio_venta).sum()) if 'precio_venta' in d.columns else 0
        margen=venta-value
        r2.markdown(f"""
            <div style="font-size:.75rem;color:#718096;font-weight:800;">
                VALOR POTENCIAL DE VENTA
            </div>
            <div style="font-size:1.8rem;font-weight:900;color:#179447;margin-top:7px;">
                {money(venta)}
            </div>
            <div style="color:#718096;font-size:.78rem;margin-top:5px;">
                Venta potencial del stock actual
            </div>
        </div>
        """,unsafe_allow_html=True)
        r3.markdown(f"""
            <div style="font-size:.75rem;color:#718096;font-weight:800;">
                MARGEN POTENCIAL
            </div>
            <div style="font-size:1.8rem;font-weight:900;color:#A832D9;margin-top:7px;">
                {money(margen)}
            </div>
            <div style="color:#718096;font-size:.78rem;margin-top:5px;">
                Diferencia entre venta y costo
            </div>
        </div>
        """,unsafe_allow_html=True)
        st.markdown("<div style='height:22px'></div>",unsafe_allow_html=True)
        st.markdown(textwrap.dedent("""
            <div class="nova-panel-title">
                📋 Vista rápida del inventario
            </div>
        """),unsafe_allow_html=True)
        st.dataframe(
            d[['codigo','nombre','categoria','stock','precio_compra','precio_venta']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay productos disponibles para mostrar el dashboard.")
elif menu=='📦 Productos':
    st.markdown('<div class="section">Productos</div>',unsafe_allow_html=True)
    d=pd.DataFrame(products())
    st.dataframe(d[['codigo','nombre','categoria','marca','unidad','stock','precio_compra','precio_venta','stock_minimo']],use_container_width=True,hide_index=True)
    st.info('🔒 Los precios de compra y venta están establecidos y no son editables.')
elif menu=='📥 Ingresos':
    st.markdown('<div class="section">Nuevo ingreso</div>',unsafe_allow_html=True)
    ps=people('proveedores'); em=people('empleados'); pr=products()
    pm={f"{x['razon_social']}":x['id'] for x in ps}; emap={f"{x['apellidos']}, {x['nombres']}":x['id'] for x in em}; pmap={f"{x['codigo']} — {x['nombre']}":x for x in pr}
    with st.form('ing'):
        a,b,c=st.columns(3);prov=a.selectbox('Proveedor *',list(pm));emp=b.selectbox('Responsable *',list(emap));fecha=c.date_input('Fecha',date.today())
        doc=st.text_input('N.º documento');obs=st.text_area('Observaciones')
        n=st.number_input('Productos diferentes',1,10,1)
        det=[]
        for i in range(int(n)):
            x,y,z=st.columns([3,1,1]);name=x.selectbox(f'Producto {i+1}',list(pmap),key=f'ip{i}');p=pmap[name]
            y.markdown(f'<div class="locked"><div class="label">COSTO ESTABLECIDO 🔒</div><div class="value">{money(p["precio_compra"])}</div></div>',unsafe_allow_html=True)
            q=z.number_input('Cantidad',min_value=.001,value=1.,step=1.,key=f'iq{i}')
            det.append({'id_producto':p['id_producto'],'cantidad':q,'costo_unitario':p['precio_compra']})
        go=st.form_submit_button('📥 Confirmar ingreso',use_container_width=True)
    if go:
        try:
            r=sb.rpc('registrar_ingreso',{'p_proveedor':pm[prov],'p_fecha':str(fecha),'p_empleado':emap[emp],'p_almacen':1,'p_numero_documento':doc,'p_observaciones':obs,'p_detalles':det}).execute()
            refresh();st.success(f'Ingreso registrado: {r.data}');st.rerun()
        except Exception as ex: st.error(str(ex))
elif menu=='📤 Salidas':
    st.markdown('<div class="section">Nueva salida</div>',unsafe_allow_html=True)
    st.caption('En VENTA el precio se toma del catálogo y no se puede editar. Puedes agregar varios productos.')
    cl=people('clientes');em=people('empleados');pr=products()
    cmap={'— Sin cliente —':None}|{x['razon_social']:x['id'] for x in cl}
    emap={'— Sin responsable —':None}|{f"{x['apellidos']}, {x['nombres']}":x['id'] for x in em}
    pmap={f"{x['codigo']} — {x['nombre']}":x for x in pr}
    a,b,c=st.columns(3);tipo=a.selectbox('Tipo de salida *',['VENTA','CONSUMO INTERNO','MERMA','DEVOLUCION','AJUSTE','OTROS']);cliente=b.selectbox('Cliente',list(cmap));emp=c.selectbox('Responsable',list(emap))
    fecha=st.date_input('Fecha',date.today());doc=st.text_input('N.º documento');obs=st.text_area('Observaciones')
    if 'items' not in st.session_state:st.session_state["items"]=[]
    sel=st.selectbox('Producto *',list(pmap));p=pmap[sel];stock=float(p['stock']);price=float(p['precio_venta']);cost=float(p['precio_compra'])
    cards_html = (
        f'<div class="salida-cards">'
        f'<div class="salida-card-premium stock-card"><div class="salida-card-title"><div class="salida-card-icon">📦</div>STOCK DISPONIBLE</div><div class="salida-card-number">{stock:,.0f}</div><div class="salida-card-description">Unidades disponibles</div></div>'
        f'<div class="salida-card-premium sale-card"><div class="salida-card-title"><div class="salida-card-icon">🏷️</div>PRECIO DE VENTA 🔒</div><div class="salida-card-number">{money(price)}</div><div class="salida-card-description">No editable · Precio establecido</div></div>'
        f'<div class="salida-card-premium cost-card"><div class="salida-card-title"><div class="salida-card-icon">💰</div>COSTO UNITARIO 🔒</div><div class="salida-card-number">{money(cost)}</div><div class="salida-card-description">No editable · Costo establecido</div></div>'
        f'</div>'
    )
    st.markdown(cards_html, unsafe_allow_html=True)
    qty=st.number_input('Cantidad *',min_value=.001,max_value=max(stock,.001),value=1.,step=1.)
    total_html = (
        f'<div class="salida-line-total"><strong>🧾 Total línea:</strong> {money(qty*price)} <span class="salida-separator">•</span> <strong>💰 Costo:</strong> {money(qty*cost)}</div>'
    )
    st.markdown(total_html, unsafe_allow_html=True)
    if st.button('➕ Agregar producto',type='primary',use_container_width=True):
        if qty>stock:st.error(f'Stock insuficiente. Disponible: {stock:,.0f}')
        else:
            st.session_state["items"].append({'id_producto':p['id_producto'],'codigo':p['codigo'],'nombre':p['nombre'],'cantidad':qty,'precio_unitario':price,'costo_unitario':cost,'total':qty*price,'costo':qty*cost});st.rerun()
    if st.session_state["items"]:
        d=pd.DataFrame(st.session_state["items"])
        st.dataframe(d[['codigo','nombre','cantidad','precio_unitario','total','costo']],use_container_width=True,hide_index=True)
        summary_html = (
            f'<div class="salida-summary">'
            f'<div class="salida-summary-card"><div class="salida-summary-label">TOTAL VENTA</div><div class="salida-summary-value">{money(d.total.sum())}</div></div>'
            f'<div class="salida-summary-card"><div class="salida-summary-label">COSTO DE VENTA</div><div class="salida-summary-value">{money(d.costo.sum())}</div></div>'
            f'<div class="salida-summary-card"><div class="salida-summary-label">UTILIDAD</div><div class="salida-summary-value">{money(d.total.sum()-d.costo.sum())}</div></div>'
            f'</div>'
        )
        st.markdown(summary_html, unsafe_allow_html=True)
        if st.button('🗑️ Vaciar'):st.session_state["items"]=[];st.rerun()
        if st.button('✅ Confirmar salida',type='primary',use_container_width=True):
            try:
                # El RPC vuelve a validar stock y obtiene los precios desde productos.
                payload=[{'id_producto':i['id_producto'],'cantidad':i['cantidad']} for i in st.session_state["items"]]
                r=sb.rpc('registrar_salida',{'p_fecha':str(fecha),'p_tipo_salida':tipo,'p_cliente':cmap[cliente],'p_empleado':emap[emp],'p_numero_documento':doc,'p_observaciones':obs,'p_detalles':payload}).execute()
                st.session_state["items"]=[];refresh();st.success(f'Salida registrada: {r.data}');st.rerun()
            except Exception as ex:st.error(str(ex))
elif menu=='📜 Kardex':
    st.markdown('<div class="section">Kardex</div>',unsafe_allow_html=True)
    d=pd.DataFrame(get('v_kardex','*','fecha'))
    if d.empty:st.info('Sin movimientos.')
    else:st.dataframe(d,use_container_width=True,hide_index=True)
elif menu=='🚨 Alertas':
    st.markdown('<div class="section">🚨 Alertas inteligentes</div>',unsafe_allow_html=True)
    st.markdown('<div class="subtitulo">Riesgo de inventario basado en stock mínimo y consumo reciente</div>',unsafe_allow_html=True)
    d=intelligent_stock_df()
    if d.empty:
        st.info('No hay información suficiente para calcular alertas.')
    else:
        c1,c2,c3,c4=st.columns(4)
        c1.metric('🔴 Sin stock',int((d.riesgo=='SIN STOCK').sum()))
        c2.metric('🟠 Reposición urgente',int((d.riesgo=='REPOSICIÓN URGENTE').sum()))
        c3.metric('🟡 Vigilancia',int((d.riesgo=='VIGILANCIA').sum()))
        c4.metric('🟢 Normal',int((d.riesgo=='NORMAL').sum()))
        crit=d[d.riesgo!='NORMAL'].copy()
        if crit.empty:
            st.success('✅ No se detectan alertas de reposición.')
        else:
            crit['cobertura_dias']=crit['cobertura_dias'].round(1)
            st.dataframe(crit[['codigo','nombre','stock','stock_minimo','consumo_diario_30d','cobertura_dias','riesgo']],use_container_width=True,hide_index=True)
            st.caption('La cobertura se estima con las salidas de venta confirmadas de los últimos 30 días. Si no existe consumo reciente, no se fuerza una predicción.')
elif menu=='🏢 Proveedores y clientes':
    st.markdown('<div class="section">🏢 Proveedores y clientes</div>',unsafe_allow_html=True)
    st.markdown('<div class="subtitulo">Gestión comercial de abastecedores y compradores</div>',unsafe_allow_html=True)
    t1,t2=st.tabs(['🚚 Proveedores','👥 Clientes'])
    with t1:
        d=pd.DataFrame(get('proveedores','*','razon_social'))
        st.dataframe(d,use_container_width=True,hide_index=True)
    with t2:
        d=pd.DataFrame(get('clientes','*','razon_social'))
        st.dataframe(d,use_container_width=True,hide_index=True)
elif menu=='👷 Empleados':
    st.markdown('<div class="section">Empleados</div>',unsafe_allow_html=True)
    d=pd.DataFrame(get('empleados','*','apellidos'));st.dataframe(d[['nombres','apellidos','cargo','documento']],use_container_width=True,hide_index=True)
elif menu=='⚙️ Maestros':
    st.markdown('<div class="section">Maestros</div>',unsafe_allow_html=True)
    tabs=st.tabs(['Categorías','Marcas','Unidades'])
    for tab,t in zip(tabs,['categorias','marcas','unidades']):
        with tab:
            d=pd.DataFrame(get(t));st.dataframe(d,use_container_width=True,hide_index=True)
elif menu=='📊 Reportes':
    st.markdown('<div class="section">📊 Reportes y análisis</div>',unsafe_allow_html=True)
    st.markdown('<div class="subtitulo">Reportes administrativos y comerciales en PDF</div>',unsafe_allow_html=True)
    tipo=st.selectbox('Tipo de reporte',['Inventario','Ventas','Compras','Kardex','Alertas'])
    if tipo=='Inventario':
        d=pd.DataFrame(products()); cols=['codigo','nombre','categoria','stock','precio_compra','precio_venta']; cols=[c for c in cols if c in d.columns]
        rows=d[cols].values.tolist() if not d.empty else []
        b=pdf('Reporte de inventario',['Código','Producto','Categoría','Stock','Compra','Venta'][:len(cols)],rows)
        st.download_button('📄 Descargar PDF de inventario',b,'inventario.pdf','application/pdf',use_container_width=True)
        st.dataframe(d[cols],use_container_width=True,hide_index=True)
    elif tipo=='Ventas':
        d=sales_confirmed_df()
        if d.empty: st.info('No existen ventas confirmadas.')
        else:
            em=pd.DataFrame(get('empleados','id,nombres,apellidos','apellidos'))
            if not em.empty: d=d.merge(em,left_on='id_empleado',right_on='id',how='left'); d['empleado']=d['nombres'].fillna('')+' '+d['apellidos'].fillna('')
            rows=d[['fecha','numero','empleado','total_venta','total_costo','utilidad']].values.tolist()
            b=pdf('Reporte de ventas confirmadas',['Fecha','Número','Empleado','Venta','Costo','Utilidad'],rows)
            st.download_button('📄 Descargar PDF de ventas',b,'ventas_confirmadas.pdf','application/pdf',use_container_width=True)
            st.dataframe(d[['fecha','numero','empleado','total_venta','total_costo','utilidad']],use_container_width=True,hide_index=True)
    elif tipo=='Compras':
        d=purchase_df()
        if d.empty: st.info('No existen compras confirmadas.')
        else:
            pr=pd.DataFrame(get('proveedores','id,razon_social','razon_social'))
            if not pr.empty: d=d.merge(pr,left_on='id_proveedor',right_on='id',how='left'); d['proveedor']=d['razon_social']
            rows=d[['fecha','numero','proveedor','total']].values.tolist()
            b=pdf('Reporte de compras confirmadas',['Fecha','Número','Proveedor','Total'],rows)
            st.download_button('📄 Descargar PDF de compras',b,'compras_confirmadas.pdf','application/pdf',use_container_width=True)
            st.dataframe(d[['fecha','numero','proveedor','total']],use_container_width=True,hide_index=True)
    elif tipo=='Kardex':
        d=pd.DataFrame(get('v_kardex','*','fecha'))
        cols=['fecha','codigo','nombre','tipo_movimiento','referencia','cantidad_entrada','cantidad_salida','saldo']; cols=[c for c in cols if c in d.columns]
        rows=d[cols].values.tolist() if not d.empty else []
        b=pdf('Reporte de Kardex',['Fecha','Código','Producto','Movimiento','Referencia','Entrada','Salida','Saldo'][:len(cols)],rows)
        st.download_button('📄 Descargar PDF de Kardex',b,'kardex.pdf','application/pdf',use_container_width=True)
        st.dataframe(d[cols],use_container_width=True,hide_index=True)
    else:
        d=intelligent_stock_df(); cols=['codigo','nombre','stock','stock_minimo','consumo_diario_30d','cobertura_dias','riesgo']; cols=[c for c in cols if c in d.columns]; rows=d[d.riesgo!='NORMAL'][cols].values.tolist() if not d.empty else []
        b=pdf('Reporte de alertas de inventario',cols,rows)
        st.download_button('📄 Descargar PDF de alertas',b,'alertas_inventario.pdf','application/pdf',use_container_width=True)
        st.dataframe(d[cols],use_container_width=True,hide_index=True)
elif menu=='📈 AgroCharts':
    render_chart_agent(sb)
elif menu=='✉️ AgroMail':
    render_mail_agent(sb)
