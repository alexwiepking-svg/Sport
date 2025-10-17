import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import plotly.io as pio
from scipy.stats import linregress
import numpy as np
import os
from dotenv import load_dotenv
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# Load environment variables
load_dotenv()

# Import helper modules
try:
    import sheets_helper
    import groq_helper
    HELPERS_AVAILABLE = True
except ImportError:
    HELPERS_AVAILABLE = False
    st.warning("Helper modules niet gevonden. Data Invoer functionaliteit is beperkt.")

# Page config
st.set_page_config(
    page_title="Fitness Coach Dashboard",
    page_icon="💪",
    layout="wide"
)

# ============================================
# MOBILE-FIRST CSS
# ============================================
st.markdown("""
<style>
    /* Mobile optimizations */
    @media (max-width: 768px) {
        /* Minimize padding */
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Smaller headers with minimal spacing */
        h1 { font-size: 1.3rem !important; margin-bottom: 0.3rem !important; margin-top: 0.3rem !important; }
        h2 { font-size: 1.15rem !important; margin-bottom: 0.3rem !important; margin-top: 0.3rem !important; }
        h3 { font-size: 1rem !important; margin-bottom: 0.25rem !important; margin-top: 0.25rem !important; }
        
        /* Compact metrics */
        [data-testid="stMetricValue"] {
            font-size: 1.3rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
        }
        
        /* Full-width buttons with minimal spacing */
        .stButton button {
            width: 100% !important;
            padding: 0.5rem !important;
            font-size: 0.95rem !important;
            margin-bottom: 0.3rem !important;
        }
        
        /* Compact inputs */
        .stTextInput input, .stTextArea textarea {
            font-size: 0.95rem !important;
            padding: 0.5rem !important;
        }
        
        /* Stack columns vertically on mobile with minimal spacing */
        [data-testid="column"] {
            width: 100% !important;
            flex: 100% !important;
            margin-bottom: 0.25rem !important;
        }
        
        /* Reduce spacing between stacked column content */
        [data-testid="column"] > div {
            margin-bottom: 0.3rem !important;
        }
        
        /* Minimize element container spacing */
        .element-container {
            margin-bottom: 0.25rem !important;
        }
        
        /* Smaller tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem !important;
            overflow-x: auto !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.4rem 0.6rem !important;
            font-size: 0.85rem !important;
            white-space: nowrap !important;
        }
        
        /* Hide AI Coach on mobile - too much content */
        .ai-coach-section {
            display: none !important;
        }
        
        /* Compact plotly graphs */
        .js-plotly-plot {
            height: 250px !important;
            max-width: 100vw !important;
        }
        
        .js-plotly-plot .plotly {
            width: 100% !important;
        }
        
        /* Hide horizontal scrollbars on graphs */
        .user-select-none {
            overflow-x: hidden !important;
        }
        
        /* Minimize divider spacing */
        hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Compact info/warning boxes */
        [data-testid="stAlert"] {
            padding: 0.5rem !important;
            margin-bottom: 0.3rem !important;
        }
        
        /* Compact expanders */
        [data-testid="stExpander"] {
            margin-bottom: 0.3rem !important;
        }
    }
    
    /* Touch-friendly buttons (all screens) */
    .stButton button {
        min-height: 44px !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }
    
    /* Hide Quick Actions tip on desktop (show only on mobile) */
    @media (min-width: 769px) {
        .quick-action-tip {
            display: none !important;
        }
    }
    
    /* Compact table styling */
    .dataframe {
        font-size: 0.85rem !important;
        max-width: 100% !important;
        overflow-x: auto !important;
    }
    
    /* Reduce spacing between elements (all screens) */
    .element-container {
        margin-bottom: 0.3rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# AUTHENTICATION
# ============================================
# Load config from secrets (Streamlit Cloud) or local file
import os

# Helper function to convert Streamlit Secrets to regular dict
def secrets_to_dict(secrets_obj):
    """Recursively convert Streamlit Secrets object to regular dict"""
    if hasattr(secrets_obj, 'to_dict'):
        return secrets_obj.to_dict()
    elif isinstance(secrets_obj, dict):
        return {k: secrets_to_dict(v) for k, v in secrets_obj.items()}
    else:
        return secrets_obj

# Check if running on Streamlit Cloud (secrets available)
if 'credentials' in st.secrets:
    # Streamlit Cloud: convert secrets to regular dicts
    config = {
        'credentials': {
            'usernames': {
                username: {
                    'email': str(st.secrets['credentials']['usernames'][username]['email']),
                    'name': str(st.secrets['credentials']['usernames'][username]['name']),
                    'password': str(st.secrets['credentials']['usernames'][username]['password'])
                }
                for username in st.secrets['credentials']['usernames'].keys()
            }
        },
        'cookie': {
            'name': str(st.secrets['cookie']['name']),
            'key': str(st.secrets['cookie']['key']),
            'expiry_days': int(st.secrets['cookie']['expiry_days'])
        },
        'preauthorized': {
            'emails': list(st.secrets.get('preauthorized', {}).get('emails', []))
        }
    }
else:
    # Local: use config.yaml file
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login widget
try:
    authenticator.login(location='main')
except Exception as e:
    st.error(f"Login error: {e}")

# Check authentication status
if st.session_state.get("authentication_status") == False:
    st.error('Username/password is incorrect')
    st.stop()
elif st.session_state.get("authentication_status") == None:
    st.warning('Please enter your username and password')
    st.stop()

# User is authenticated - show logout button in sidebar
name = st.session_state.get("name")
username = st.session_state.get("username")

# ============================================
# USER-SPECIFIC SHEET SELECTION
# ============================================
# Map username to their Google Sheet ID
SHEET_MAPPING = {
    'alex': os.getenv('SHEET_ID_ALEX'),
    'tamara': os.getenv('SHEET_ID_PARTNER')
}

# Get the sheet ID for the current user
USER_SHEET_ID = SHEET_MAPPING.get(username)

if not USER_SHEET_ID:
    st.error(f"⚠️ Geen Google Sheet geconfigureerd voor gebruiker '{username}'!")
    st.info("Voeg SHEET_ID_{USERNAME} toe aan je .env bestand")
    st.stop()

# Store in session state for use throughout the app
st.session_state.user_sheet_id = USER_SHEET_ID

with st.sidebar:
    st.write(f'Welkom *{name}*')
    st.caption(f"📊 Jouw persoonlijke sheet")
    authenticator.logout(location='sidebar')

# Set default Plotly template with white text and dark tooltips
pio.templates["custom_dark"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=12),
        title=dict(font=dict(color='white', size=16)),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)',
            tickfont=dict(color='white', size=12),
            title=dict(font=dict(color='white', size=14))
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)',
            tickfont=dict(color='white', size=12),
            title=dict(font=dict(color='white', size=14))
        ),
        legend=dict(
            font=dict(color='white'),
            bgcolor='rgba(0,0,0,0.3)'
        ),
        hoverlabel=dict(
            bgcolor='rgba(0, 0, 0, 0.9)',
            font=dict(color='white', size=13),
            bordercolor='rgba(139, 92, 246, 0.8)'
        ),
        colorway=['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ef4444']
    )
)
pio.templates.default = "custom_dark"

# Dutch month names for beautiful date formatting
DUTCH_MONTHS = {
    1: 'januari', 2: 'februari', 3: 'maart', 4: 'april',
    5: 'mei', 6: 'juni', 7: 'juli', 8: 'augustus',
    9: 'september', 10: 'oktober', 11: 'november', 12: 'december'
}

def format_date_nl(date_obj):
    """Format date in Dutch: 16 oktober 2025"""
    if pd.isna(date_obj):
        return ""
    if isinstance(date_obj, str):
        try:
            date_obj = pd.to_datetime(date_obj, dayfirst=True)
        except:
            return date_obj
    return f"{date_obj.day} {DUTCH_MONTHS[date_obj.month]} {date_obj.year}"

def format_date_short_nl(date_obj):
    """Format date in Dutch short: 16 okt"""
    if pd.isna(date_obj):
        return ""
    if isinstance(date_obj, str):
        try:
            date_obj = pd.to_datetime(date_obj, dayfirst=True)
        except:
            return date_obj
    month_short = DUTCH_MONTHS[date_obj.month][:3]
    return f"{date_obj.day} {month_short}"


def make_chart_responsive(fig):
    """Make plotly chart responsive for mobile"""
    fig.update_layout(
        autosize=True,
        margin=dict(l=20, r=20, t=40, b=20),
        height=300,  # Will be overridden by CSS on mobile
    )
    fig.update_xaxes(fixedrange=False, automargin=True)
    fig.update_yaxes(fixedrange=False, automargin=True)
    return fig


# Custom CSS
st.markdown("""
<style>
    /* Dark gradient background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e) !important;
    }
    .main {
        background: transparent !important;
    }
    
    /* Remove white bar at top */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    
    /* Fix toolbar */
    .stAppToolbar {
        background: transparent !important;
    }
    
    /* All text white by default */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label {
        color: #ffffff !important;
    }
    
    /* Metrics styling - glassmorphism to match charts */
    .stMetric {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05)) !important;
        padding: 18px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(139, 92, 246, 0.15) !important;
        backdrop-filter: blur(10px) !important;
    }
    .stMetric label {
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    .stMetric [data-testid="stMetricDelta"] {
        font-weight: 600 !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px 24px;
        color: white !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #8b5cf6, #ec4899) !important;
    }
    
    /* DataFrames - Glassmorphism styling to match charts */
    div[data-testid="stDataFrame"] {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05)) !important;
        border-radius: 12px !important;
        padding: 15px !important;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(139, 92, 246, 0.15) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Force all nested divs to be transparent */
    div[data-testid="stDataFrame"] > div,
    div[data-testid="stDataFrame"] div[data-testid="stDataFrameResizable"],
    div[data-testid="stDataFrame"] div[class*="glideDataEditor"] {
        background: transparent !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    
    /* Target the actual data grid cells */
    div[data-testid="stDataFrame"] div[role="grid"],
    div[data-testid="stDataFrame"] div[role="row"],
    div[data-testid="stDataFrame"] div[role="gridcell"],
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        background: transparent !important;
        color: white !important;
    }
    
    /* Header cells styling */
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.5), rgba(99, 102, 241, 0.4)) !important;
        color: white !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.5px !important;
        padding: 14px 12px !important;
        border-bottom: 2px solid rgba(139, 92, 246, 0.6) !important;
    }
    
    /* Data cells styling */
    div[data-testid="stDataFrame"] div[role="gridcell"] {
        background: rgba(20, 20, 40, 0.3) !important;
        color: rgba(255, 255, 255, 0.95) !important;
        padding: 12px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Hover effect on rows */
    div[data-testid="stDataFrame"] div[role="row"]:hover div[role="gridcell"] {
        background: rgba(139, 92, 246, 0.2) !important;
        transition: background 0.2s ease !important;
    }
    
    /* Legacy table support (if regular HTML tables are used) */
    div[data-testid="stDataFrame"] table {
        color: white !important;
        background: transparent !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    div[data-testid="stDataFrame"] thead {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.5), rgba(99, 102, 241, 0.4)) !important;
    }
    div[data-testid="stDataFrame"] th {
        color: white !important;
        background: transparent !important;
        font-weight: 600 !important;
        padding: 14px 12px !important;
        border-bottom: 2px solid rgba(139, 92, 246, 0.6) !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stDataFrame"] td {
        color: rgba(255, 255, 255, 0.95) !important;
        background: rgba(20, 20, 40, 0.3) !important;
        padding: 12px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    div[data-testid="stDataFrame"] tbody tr:hover td {
        background: rgba(139, 92, 246, 0.2) !important;
        transition: background 0.2s ease !important;
    }
    div[data-testid="stDataFrame"] tbody tr:first-child td {
        border-top: 1px solid rgba(139, 92, 246, 0.3) !important;
    }
    /* Beautiful scrollbar in dataframes */
    div[data-testid="stDataFrame"] ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-track {
        background: rgba(20, 20, 40, 0.4);
        border-radius: 6px;
        margin: 4px;
    }
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.6), rgba(99, 102, 241, 0.6));
        border-radius: 6px;
        border: 2px solid rgba(20, 20, 40, 0.4);
    }
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.8), rgba(99, 102, 241, 0.8));
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.8) !important;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Buttons */
    .stButton button {
        background: rgba(255, 255, 255, 0.1);
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .stButton button:hover {
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    /* ALL Input fields - DARK BACKGROUND with WHITE TEXT */
    input, textarea, select {
        background: rgba(30, 30, 60, 0.8) !important;
        color: white !important;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        -webkit-text-fill-color: white !important;
    }
    
    /* Specific input types */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox select,
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] select {
        background: rgba(30, 30, 60, 0.8) !important;
        color: white !important;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        -webkit-text-fill-color: white !important;
    }
    
    /* Fix all input labels */
    .stTextInput label,
    .stTextArea label,
    .stNumberInput label,
    .stSelectbox label,
    div[data-testid="stNumberInput"] label,
    div[data-baseweb="input"] label,
    label[data-testid="stWidgetLabel"] {
        color: white !important;
    }
    
    /* Input hover states */
    input:hover, textarea:hover, select:hover {
        border: 1px solid rgba(139, 92, 246, 0.5) !important;
    }
    
    /* Input focus states */
    input:focus, textarea:focus, select:focus {
        border: 1px solid rgba(139, 92, 246, 0.7) !important;
        box-shadow: 0 0 0 1px rgba(139, 92, 246, 0.3) !important;
    }
    
    /* Fix expander - dark background and white text */
    .streamlit-expanderHeader {
        color: white !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    div[data-testid="stExpander"] {
        background: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    div[data-testid="stExpander"] details {
        background: transparent !important;
    }
    div[data-testid="stExpander"] details summary {
        color: white !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }
    div[data-testid="stExpander"] details summary:hover {
        background: rgba(255, 255, 255, 0.1) !important;
    }
    div[data-testid="stExpander"] details[open] summary {
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px 8px 0 0 !important;
    }
    div[data-testid="stExpander"] details[open] > div {
        background: transparent !important;
        padding: 15px !important;
    }
    div[data-testid="stExpander"] p,
    div[data-testid="stExpander"] strong,
    div[data-testid="stExpander"] span,
    div[data-testid="stExpander"] div,
    div[data-testid="stExpander"] .stMarkdown {
        color: white !important;
    }
    
    /* Fix date input */
    .stDateInput label {
        color: white !important;
    }
    .stDateInput input {
        color: #333 !important;
        background: white !important;
    }
    
    /* Fix radio buttons */
    .stRadio label {
        color: white !important;
    }
    .stRadio div[role="radiogroup"] label {
        color: white !important;
    }
    
    /* Force Plotly charts to have white text */
    .js-plotly-plot .plotly text {
        fill: white !important;
    }
    .js-plotly-plot .plotly .xtick text,
    .js-plotly-plot .plotly .ytick text,
    .js-plotly-plot .plotly .g-xtitle text,
    .js-plotly-plot .plotly .g-ytitle text,
    .js-plotly-plot .plotly .g-y2title text {
        fill: white !important;
    }
    
    /* Plotly hover tooltips - dark background with white text */
    g.hoverlayer g.hovertext path,
    .hoverlayer .hovertext path {
        fill: rgba(15, 12, 41, 0.95) !important;
        stroke: rgba(139, 92, 246, 0.9) !important;
        stroke-width: 2px !important;
    }
    g.hoverlayer g.hovertext text,
    .hoverlayer .hovertext text,
    .hoverlayer text,
    svg.main-svg g.hoverlayer g.hovertext text,
    .hoverlayer .hovertext .name,
    .hoverlayer .hovertext .nums {
        fill: white !important;
        font-weight: 500 !important;
    }
    
    /* Selectbox dropdown styling */
    .stSelectbox label {
        color: white !important;
    }
    .stSelectbox div[data-baseweb="select"],
    .stSelectbox div[data-baseweb="select"] > div {
        color: white !important;
        background: rgba(255, 255, 255, 0.1) !important;
    }
    div[role="listbox"] {
        background: rgba(15, 12, 41, 0.95) !important;
        border: 1px solid rgba(139, 92, 246, 0.5) !important;
    }
    div[role="listbox"] li {
        color: white !important;
        background: transparent !important;
    }
    div[role="listbox"] li:hover {
        background: rgba(139, 92, 246, 0.3) !important;
    }
    div[role="listbox"] li[aria-selected="true"] {
        background: rgba(139, 92, 246, 0.5) !important;
    }
    
    /* Additional number input fixes */
    .stNumberInput input[type="number"] {
        color: white !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    .stNumberInput input[type="number"]:focus {
        border-color: rgba(139, 92, 246, 0.8) !important;
        box-shadow: 0 0 0 1px rgba(139, 92, 246, 0.5) !important;
    }
    
    /* Fix expander content area */
    div[data-testid="stExpander"] div[role="button"] {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    div[data-testid="stExpander"] div[role="button"]:hover {
        background: rgba(255, 255, 255, 0.15) !important;
    }
    
    /* Beautiful table styling for all tables */
    table {
        background: transparent !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    table th {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.5), rgba(99, 102, 241, 0.4)) !important;
        color: white !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.5px !important;
        padding: 14px 12px !important;
    }
    table td {
        background: rgba(20, 20, 40, 0.3) !important;
        color: rgba(255, 255, 255, 0.95) !important;
        padding: 12px !important;
    }
    table tr:hover td {
        background: rgba(139, 92, 246, 0.2) !important;
        transition: background 0.2s ease !important;
    }
    
    /* Clean progress bars */
    .stProgress > div > div {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px !important;
        height: 8px !important;
    }
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #8b5cf6, #6366f1) !important;
        border-radius: 6px !important;
    }
    .stProgress p {
        color: white !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }
    
    /* Beautiful framed charts with glassmorphism */
    .js-plotly-plot {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05)) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        padding: 10px !important;
        box-shadow: 0 8px 32px 0 rgba(139, 92, 246, 0.15) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Hide Plotly modebar completely */
    .modebar-container {
        display: none !important;
    }
    .modebar {
        display: none !important;
    }
    .modebar-group {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Google Sheets Connection
@st.cache_resource
def get_google_sheets_client():
    """
    Setup Google Sheets connection.
    Voor nu gebruiken we publieke sheet access via URL.
    """
    return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_sheet_data(sheet_id):
    """
    Load data from Google Sheets using public CSV export
    """
    try:
        base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
        
        data = {}
        sheets = ['voeding', 'activiteiten', 'metingen', 'egym', 'stappen', 'gewicht']
        
        for sheet_name in sheets:
            try:
                url = base_url + sheet_name
                df = pd.read_csv(url)
                data[sheet_name] = df
            except Exception as e:
                st.warning(f"Kon {sheet_name} niet laden: {str(e)}")
                data[sheet_name] = pd.DataFrame()
        
        return data
    except Exception as e:
        st.error(f"Fout bij laden data: {str(e)}")
        return None

# Helper functions voor Data Invoer tab
def get_voeding_data():
    """Haal voeding data op via load_sheet_data"""
    import streamlit as st
    import os
    sheet_id = st.session_state.get('user_sheet_id', os.getenv('SHEET_ID_ALEX'))
    data = load_sheet_data(sheet_id)
    if data and 'voeding' in data:
        return data['voeding']
    return pd.DataFrame()

def get_activiteiten_data():
    """Haal activiteiten data op via load_sheet_data"""
    import streamlit as st
    import os
    sheet_id = st.session_state.get('user_sheet_id', os.getenv('SHEET_ID_ALEX'))
    data = load_sheet_data(sheet_id)
    if data and 'activiteiten' in data:
        return data['activiteiten']
    return pd.DataFrame()

def get_stappen_data():
    """Haal stappen data op via load_sheet_data"""
    import streamlit as st
    import os
    sheet_id = st.session_state.get('user_sheet_id', os.getenv('SHEET_ID_ALEX'))
    data = load_sheet_data(sheet_id)
    if data and 'stappen' in data:
        return data['stappen']
    return pd.DataFrame()

def get_gewicht_data():
    """Haal gewicht data op via load_sheet_data"""
    import streamlit as st
    import os
    sheet_id = st.session_state.get('user_sheet_id', os.getenv('SHEET_ID_ALEX'))
    data = load_sheet_data(sheet_id)
    if data and 'gewicht' in data:
        return data['gewicht']
    return pd.DataFrame()

def get_chart_layout_defaults():
    """
    Get default layout settings for all charts with consistent styling and readable tooltips.
    Consolidated from previous separate functions for better maintainability.
    """
    return {
        'template': 'custom_dark',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': dict(color='white'),
        'xaxis': dict(gridcolor='rgba(255,255,255,0.1)'),
        'yaxis': dict(gridcolor='rgba(255,255,255,0.1)'),
        'hoverlabel': dict(
            bgcolor='rgba(0, 0, 0, 0.95)',
            font=dict(color='white', size=14, family='Arial'),
            bordercolor='rgba(139, 92, 246, 1)',
            align='left'
        )
    }

def calculate_nutrition_totals(nutrition_df, date):
    """
    Calculate nutrition totals for a specific date.
    
    Args:
        nutrition_df: DataFrame with nutrition data
        date: Date string to filter by
        
    Returns:
        dict: Nutrition totals with keys: calorien, eiwit, koolhydraten, vetten
    """
    default_totals = {'calorien': 0, 'eiwit': 0, 'koolhydraten': 0, 'vetten': 0}
    
    if nutrition_df is None or nutrition_df.empty or date is None:
        return default_totals
    
    try:
        day_data = nutrition_df[nutrition_df['datum'] == date]
        
        totals = {
            'calorien': float(day_data['calorien'].sum()) if 'calorien' in day_data else 0,
            'eiwit': float(day_data['eiwit'].sum()) if 'eiwit' in day_data else 0,
            'koolhydraten': float(day_data['koolhydraten'].sum()) if 'koolhydraten' in day_data else 0,
            'vetten': float(day_data['vetten'].sum()) if 'vetten' in day_data else 0
        }
        return totals
    except Exception as e:
        st.warning(f"Fout bij berekenen voeding totalen: {str(e)}")
        return default_totals

def render_dataframe_html(df, max_height="400px"):
    """Render a pandas DataFrame as styled HTML table"""
    # Build headers
    headers = ''.join([f'<th style="color: white; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; padding: 14px 12px; text-align: left; border-bottom: 2px solid rgba(139, 92, 246, 0.6);">{col}</th>' for col in df.columns])
    
    # Build rows
    rows = []
    for idx, row in df.iterrows():
        cells = ''.join([f'<td style="color: rgba(255, 255, 255, 0.95); background: rgba(20, 20, 40, 0.3); padding: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">{row[col]}</td>' for col in df.columns])
        rows.append(f'<tr style="transition: background 0.2s ease;" onmouseover="this.style.background=\'rgba(139, 92, 246, 0.2)\'" onmouseout="this.style.background=\'transparent\'">{cells}</tr>')
    
    rows_html = ''.join(rows)
    
    html = f'''<div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05)); border-radius: 12px; padding: 15px; border: 1px solid rgba(139, 92, 246, 0.3); box-shadow: 0 8px 32px 0 rgba(139, 92, 246, 0.15); backdrop-filter: blur(10px); max-height: {max_height}; overflow-y: auto;"><table style="width: 100%; border-collapse: collapse;"><thead><tr style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.5), rgba(99, 102, 241, 0.4));">{headers}</tr></thead><tbody>{rows_html}</tbody></table></div>'''
    
    return html

def analyze_measurements(metingen_df):
    """Analyze body composition trends"""
    if metingen_df.empty:
        return None
    
    # Get date columns (exclude 'categorie')
    date_cols = [col for col in metingen_df.columns if col != 'categorie']
    
    if len(date_cols) < 2:
        return None
    
    gewicht = metingen_df[metingen_df['categorie'] == 'Gewicht']
    vet_pct = metingen_df[metingen_df['categorie'] == 'Vet %']
    spier = metingen_df[metingen_df['categorie'] == 'Skeletspiermassa']
    
    if gewicht.empty or vet_pct.empty or spier.empty:
        return None
    
    first_date = date_cols[0]
    last_date = date_cols[-1]
    
    trends = {
        'gewicht_change': float(gewicht[last_date].values[0]) - float(gewicht[first_date].values[0]),
        'vet_change': float(vet_pct[last_date].values[0]) - float(vet_pct[first_date].values[0]),
        'spier_change': float(spier[last_date].values[0]) - float(spier[first_date].values[0]),
        'dates': date_cols
    }
    
    return trends

def calculate_body_projections(metingen_df, weeks_ahead=4):
    """
    Calculate body composition projections using linear regression
    Returns projections for weight, fat%, and muscle mass
    """
    if metingen_df.empty:
        return None
    
    # Get date columns (exclude 'categorie')
    date_cols = [col for col in metingen_df.columns if col != 'categorie']
    
    # Need at least 3 data points for reliable projection
    if len(date_cols) < 3:
        return {
            'error': 'insufficient_data',
            'message': 'Minimaal 3 metingen nodig voor betrouwbare projecties',
            'current_measurements': len(date_cols)
        }
    
    try:
        # Parse dates and convert to days since first measurement
        dates = []
        parsed_indices = []  # Track which columns were successfully parsed
        current_year = datetime.now().year
        
        for idx, date_str in enumerate(date_cols):
            parsed = False
            date_str_clean = str(date_str).strip()
            
            # Try multiple date formats
            for fmt in ['%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y', '%Y-%m-%d', '%d.%m.%Y', '%d.%m.%y']:
                try:
                    dates.append(datetime.strptime(date_str_clean, fmt))
                    parsed_indices.append(idx)
                    parsed = True
                    break
                except:
                    continue
            
            # Try dd/mm format (without year) - assume current year
            if not parsed and '/' in date_str_clean and len(date_str_clean.split('/')) == 2:
                try:
                    day, month = date_str_clean.split('/')
                    # Assume current year, but if month is in the future, use previous year
                    parsed_date = datetime(current_year, int(month), int(day))
                    if parsed_date > datetime.now():
                        parsed_date = datetime(current_year - 1, int(month), int(day))
                    dates.append(parsed_date)
                    parsed_indices.append(idx)
                    parsed = True
                except:
                    pass
            
            # Try dd-mm format (without year)
            if not parsed and '-' in date_str_clean and len(date_str_clean.split('-')) == 2:
                try:
                    day, month = date_str_clean.split('-')
                    parsed_date = datetime(current_year, int(month), int(day))
                    if parsed_date > datetime.now():
                        parsed_date = datetime(current_year - 1, int(month), int(day))
                    dates.append(parsed_date)
                    parsed_indices.append(idx)
                    parsed = True
                except:
                    pass
            
            if not parsed:
                # Try pandas to_datetime as last resort
                try:
                    import pandas as pd
                    date_obj = pd.to_datetime(date_str_clean, dayfirst=True)
                    dates.append(date_obj.to_pydatetime())
                    parsed_indices.append(idx)
                except:
                    continue
        
        if len(dates) < 3:
            return {
                'error': 'date_parse_error',
                'message': f'Kan niet genoeg datums parsen (gevonden: {len(dates)}, nodig: 3). Formaten: {date_cols[:3]}',
                'current_measurements': len(dates)
            }
        
        # Convert to days since first measurement
        first_date = dates[0]
        days = np.array([(d - first_date).days for d in dates])
        
        # Get measurements
        gewicht = metingen_df[metingen_df['categorie'] == 'Gewicht']
        vet_pct = metingen_df[metingen_df['categorie'] == 'Vet %']
        spier = metingen_df[metingen_df['categorie'] == 'Skeletspiermassa']
        
        if gewicht.empty or vet_pct.empty or spier.empty:
            return {
                'error': 'missing_categories',
                'message': 'Niet alle categorieën (Gewicht, Vet %, Skeletspiermassa) gevonden'
            }
        
        # Extract values for valid dates (only use successfully parsed date columns)
        gewicht_vals = np.array([float(gewicht[date_cols[i]].values[0]) for i in parsed_indices])
        vet_vals = np.array([float(vet_pct[date_cols[i]].values[0]) for i in parsed_indices])
        spier_vals = np.array([float(spier[date_cols[i]].values[0]) for i in parsed_indices])
        
        # Perform linear regression for each metric
        gewicht_reg = linregress(days, gewicht_vals)
        vet_reg = linregress(days, vet_vals)
        spier_reg = linregress(days, spier_vals)
        
        # Calculate projection dates (weekly intervals for next X weeks)
        last_date = dates[-1]
        projection_dates = [last_date + timedelta(weeks=i+1) for i in range(weeks_ahead)]
        projection_days = np.array([(d - first_date).days for d in projection_dates])
        
        # Calculate projected values
        gewicht_projected = gewicht_reg.slope * projection_days + gewicht_reg.intercept
        vet_projected = vet_reg.slope * projection_days + vet_reg.intercept
        spier_projected = spier_reg.slope * projection_days + spier_reg.intercept
        
        # Calculate confidence (R² value - how well the line fits)
        gewicht_confidence = gewicht_reg.rvalue ** 2
        vet_confidence = vet_reg.rvalue ** 2
        spier_confidence = spier_reg.rvalue ** 2
        
        # Calculate changes from current to end of projection
        current_gewicht = gewicht_vals[-1]
        current_vet = vet_vals[-1]
        current_spier = spier_vals[-1]
        
        projected_gewicht_change = gewicht_projected[-1] - current_gewicht
        projected_vet_change = vet_projected[-1] - current_vet
        projected_spier_change = spier_projected[-1] - current_spier
        
        return {
            'historical': {
                'dates': dates,
                'days': days,
                'gewicht': gewicht_vals,
                'vet_pct': vet_vals,
                'spier': spier_vals
            },
            'projections': {
                'dates': projection_dates,
                'days': projection_days,
                'gewicht': gewicht_projected,
                'vet_pct': vet_projected,
                'spier': spier_projected
            },
            'regression': {
                'gewicht': {'slope': gewicht_reg.slope, 'r_squared': gewicht_confidence},
                'vet_pct': {'slope': vet_reg.slope, 'r_squared': vet_confidence},
                'spier': {'slope': spier_reg.slope, 'r_squared': spier_confidence}
            },
            'summary': {
                'current_gewicht': current_gewicht,
                'current_vet': current_vet,
                'current_spier': current_spier,
                'projected_gewicht': gewicht_projected[-1],
                'projected_vet': vet_projected[-1],
                'projected_spier': spier_projected[-1],
                'gewicht_change': projected_gewicht_change,
                'vet_change': projected_vet_change,
                'spier_change': projected_spier_change,
                'weeks_ahead': weeks_ahead
            }
        }
        
    except Exception as e:
        return {
            'error': 'calculation_error',
            'message': f'Fout bij berekenen projecties: {str(e)}'
        }

def estimate_calories_burned(activity_type, activiteit, afstand, duur, gewicht_kg=None, sets=None, reps=None):
    """
    Estimate calories burned based on activity type and duration
    Using MET (Metabolic Equivalent of Task) values
    Formula: Calories = MET × weight(kg) × time(hours)
    """
    # Use session state weight if not provided
    if gewicht_kg is None:
        import streamlit as st
        gewicht_kg = st.session_state.get('targets', {}).get('weight', 106.2)
    
    hours = 0
    
    # Parse duration (format: HH:MM:SS or MM:SS)
    if pd.notna(duur) and duur != '':
        try:
            time_parts = str(duur).split(':')
            if len(time_parts) == 3:
                hours = int(time_parts[0]) + int(time_parts[1])/60 + int(time_parts[2])/3600
            elif len(time_parts) == 2:
                hours = int(time_parts[0])/60 + int(time_parts[1])/3600
        except:
            hours = 0
    
    # For strength training without duration, estimate based on sets and reps
    if hours == 0 and activity_type.lower() == 'kracht':
        if pd.notna(sets) and pd.notna(reps):
            try:
                # Estimate: 3-4 seconds per rep + 90 seconds rest between sets
                total_sets = int(float(sets))
                total_reps = int(float(reps))
                work_time = total_sets * total_reps * 4  # 4 seconds per rep
                rest_time = (total_sets - 1) * 90  # 90 seconds rest between sets
                total_seconds = work_time + rest_time
                hours = total_seconds / 3600
            except:
                # Default estimate: 5 minutes per exercise
                hours = 5 / 60
        else:
            # If no sets/reps data, estimate 5 minutes per exercise
            hours = 5 / 60
    
    if hours == 0:
        return 0
    
    # Parse distance if available
    distance_km = 0
    if pd.notna(afstand) and afstand != '':
        try:
            distance_km = float(str(afstand).replace(',', '.'))
        except:
            distance_km = 0
    
    # MET values for different activities (more realistic)
    met_values = {
        # Cardio activities
        'walking': 3.5,
        'cross trainer': 7.0,  # Moderate to vigorous elliptical
        'running': 9.0,
        'cycling': 7.5,
        'swimming': 7.0,
        
        # Strength training (Kracht)
        'strength': 5.0,  # General weight lifting with moderate effort
        'negative': 5.5,  # Negative reps are slightly more intense
        'regular': 5.0
    }
    
    # Determine MET value based on activity
    met = 5.0  # Default (moderate intensity)
    
    if activity_type.lower() == 'cardio':
        activiteit_lower = activiteit.lower() if pd.notna(activiteit) else ''
        
        if 'cross' in activiteit_lower or 'elliptical' in activiteit_lower:
            met = 7.0  # Moderate to vigorous intensity
        elif 'walk' in activiteit_lower or 'wandel' in activiteit_lower:
            met = 3.5
        elif 'run' in activiteit_lower or 'hardlopen' in activiteit_lower:
            met = 9.0
        elif 'cycle' in activiteit_lower or 'fiets' in activiteit_lower:
            met = 7.5
        elif 'zwem' in activiteit_lower or 'swim' in activiteit_lower:
            met = 7.0
        else:
            # Estimate from distance if available
            if distance_km > 0 and hours > 0:
                speed = distance_km / hours
                if speed < 5:  # Walking pace
                    met = 3.5
                elif speed < 8:  # Jogging
                    met = 7.0
                else:  # Running
                    met = 9.0
    
    elif activity_type.lower() == 'kracht':
        met = 5.0  # Strength training with moderate intensity
    
    # Calculate calories
    calories = met * gewicht_kg * hours
    
    return round(calories)

def calculate_total_calories_burned(activities_df, date=None):
    """Calculate total calories burned for activities"""
    if activities_df.empty:
        return 0, pd.DataFrame()
    
    # Filter by date if provided
    if date:
        activities = activities_df[activities_df['datum'] == date].copy()
    else:
        activities = activities_df.copy()
    
    if activities.empty:
        return 0, pd.DataFrame()
    
    # Calculate calories for each activity
    activities['calories_burned'] = activities.apply(
        lambda row: estimate_calories_burned(
            row.get('type', ''),
            row.get('activiteit', ''),
            row.get('afstand', ''),
            row.get('duur', ''),
            sets=row.get('sets'),
            reps=row.get('reps')
        ),
        axis=1
    )
    
    return activities['calories_burned'].sum(), activities

def filter_by_date_range(df, start_date, end_date, date_column='datum'):
    """Filter dataframe by date range"""
    if df.empty or date_column not in df.columns:
        return df
    
    try:
        # Convert dates to datetime for comparison
        df_copy = df.copy()
        
        # Try multiple date formats
        # First try standard format with slash
        df_copy['date_obj'] = pd.to_datetime(df_copy[date_column], format='%d/%m/%Y', errors='coerce')
        
        # If that failed (NaT values), try with dash format (e.g., 13-10)
        if df_copy['date_obj'].isna().all():
            # Parse dates like "13-10" and add current year
            current_year = datetime.now().year
            df_copy['date_obj'] = pd.to_datetime(
                df_copy[date_column].astype(str) + f'-{current_year}',
                format='%d-%m-%Y',
                errors='coerce'
            )
        
        # If still NaT, try dayfirst auto-parse
        if df_copy['date_obj'].isna().any():
            df_copy['date_obj'] = pd.to_datetime(df_copy[date_column], dayfirst=True, errors='coerce')
        
        start_dt = pd.to_datetime(start_date).normalize()  # Remove time component
        end_dt = pd.to_datetime(end_date).normalize()
        
        # Normalize dataframe dates too (remove time)
        df_copy['date_obj'] = df_copy['date_obj'].dt.normalize()
        
        # Filter with inclusive bounds
        filtered = df_copy[(df_copy['date_obj'] >= start_dt) & (df_copy['date_obj'] <= end_dt)]
        filtered = filtered.drop('date_obj', axis=1)
        
        return filtered
    except Exception as e:
        return df

def generate_insights(period_stats, totals, view_mode, targets):
    """Generate smart insights based on data"""
    insights = []
    
    # Calorie insights - Dynamic based on targets
    cal_min = targets['calories'] - 200
    cal_max = targets['calories'] + 300
    
    if totals['calorien'] < cal_min:
        insights.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'Calorieën te laag',
            'message': f"Je gemiddelde van {totals['calorien']:.0f} kcal is te laag. Verhoog naar {targets['calories']}-{targets['calories']+200} voor optimaal vetverbranding met spierbehoud."
        })
    elif totals['calorien'] >= cal_min and totals['calorien'] <= cal_max:
        insights.append({
            'type': 'success',
            'icon': '✅',
            'title': 'Goed calorie bereik',
            'message': f"Met {totals['calorien']:.0f} kcal zit je in een gezond bereik voor vetverbranding ({cal_min}-{cal_max} kcal)."
        })
    elif totals['calorien'] > cal_max:
        insights.append({
            'type': 'info',
            'icon': '💡',
            'title': 'Calorieën iets hoog',
            'message': f"Met {totals['calorien']:.0f} kcal zit je boven target. Voor snellere vetverbranding: richting {targets['calories']}-{targets['calories']+200} kcal."
        })
    
    # Protein insights
    if totals['eiwit'] >= targets['protein']:
        insights.append({
            'type': 'success',
            'icon': '💪',
            'title': 'Uitstekende eiwitinname',
            'message': f"Met {totals['eiwit']:.0f}g eiwit bescherm je je Spiermassa perfect!"
        })
    elif totals['eiwit'] < targets['protein'] - 20:
        insights.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'Eiwit te laag',
            'message': f"Slechts {totals['eiwit']:.0f}g eiwit. Verhoog naar {targets['protein']}g+ voor spierbehoud."
        })
    
    # Activity insights
    if view_mode != "📅 Dag":
        workouts_per_week = (period_stats['total_workouts'] / period_stats['days']) * 7
        if workouts_per_week >= 4:
            insights.append({
                'type': 'success',
                'icon': '🔥',
                'title': 'Consistente training',
                'message': f"Gemiddeld {workouts_per_week:.1f} trainingen per week - geweldig tempo!"
            })
        elif workouts_per_week < 3:
            insights.append({
                'type': 'info',
                'icon': '💡',
                'title': 'Meer beweging',
                'message': f"Slechts {workouts_per_week:.1f} trainingen per week. Probeer 4+ sessies te halen."
            })
        
        # Cardio vs Strength balance
        if period_stats['cardio_sessions'] > 0 and period_stats['strength_sessions'] > 0:
            ratio = period_stats['strength_sessions'] / period_stats['cardio_sessions']
            if ratio >= 1.5:
                insights.append({
                    'type': 'success',
                    'icon': '💪',
                    'title': 'Goede kracht focus',
                    'message': f"Mooie balans met {period_stats['strength_sessions']} kracht vs {period_stats['cardio_sessions']} cardio sessies."
                })
    
    # Fat intake
    if totals['vetten'] > targets['fats'] + 10:
        insights.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'Vetten te hoog',
            'message': f"{totals['vetten']:.0f}g vetten is te veel. Beperk zuivel en kookroom tot max {targets['fats']}g."
        })
    
    return insights

def generate_action_recommendations(totals, period_stats, targets):
    """Generate dynamic action recommendations based on current data"""
    nutrition_actions = []
    goals = []
    
    # Calculate deltas
    cal_delta = targets['calories'] - totals['calorien']
    protein_delta = targets['protein'] - totals['eiwit']
    fat_delta = totals['vetten'] - targets['fats']
    
    # Nutrition recommendations based on actual needs
    if protein_delta > 20:
        # Need significantly more protein
        protein_needed = int(protein_delta)
        nutrition_actions.append(f"Voeg {protein_needed}g eiwit toe (bijv. 200g kwark of 150g kip)")
    elif protein_delta > 0:
        nutrition_actions.append(f"Verhoog eiwit met {int(protein_delta)}g (bijv. extra ei of kwark)")
    elif totals['eiwit'] >= targets['protein']:
        nutrition_actions.append("Eiwit op doel - goed bezig! 💪")
    
    if fat_delta > 10:
        # Too much fat
        nutrition_actions.append(f"Verlaag vetten met {int(fat_delta)}g (kies magere zuivel)")
    elif fat_delta > 0:
        nutrition_actions.append(f"Vetten iets hoog, probeer {int(fat_delta)}g minder")
    
    if cal_delta > 200:
        # Need more calories
        nutrition_actions.append(f"Verhoog calorieën met ~{int(cal_delta)} kcal voor optimale energie")
    elif cal_delta < -200:
        # Too many calories
        nutrition_actions.append(f"Verlaag calorieën met ~{int(abs(cal_delta))} kcal voor snellere voortgang")
    
    if len(nutrition_actions) == 0:
        nutrition_actions.append("Je voeding is goed op schema - doorgaan zo! 🎯")
    
    # Always add vegetables reminder if not perfect
    if totals.get('koolhydraten', 0) < 150:
        nutrition_actions.append("Meer groenten voor vezels en verzadiging")
    
    # Goals based on current status
    cal_range_low = max(1900, int(targets['calories'] - 100))
    cal_range_high = int(targets['calories'] + 100)
    goals.append(f"{cal_range_low}-{cal_range_high} kcal")
    goals.append(f"{targets['protein']}g+ eiwit")
    
    if fat_delta > 0:
        goals.append(f"Max {targets['fats']}g vetten")
    else:
        goals.append("Vetten onder controle ✓")
    
    # Activity goal
    if period_stats.get('total_workouts', 0) > 0:
        workouts_pw = (period_stats['total_workouts'] / period_stats.get('days', 1)) * 7
        if workouts_pw < 4:
            goals.append(f"4+ trainingen/week (nu {workouts_pw:.1f})")
        else:
            goals.append(f"Training frequentie ✓ ({workouts_pw:.1f}/week)")
    else:
        goals.append("4+ trainingen per week")
    
    return {
        'nutrition_actions': nutrition_actions,
        'goals': goals
    }

def calculate_period_stats(nutrition_df, activities_df, start_date, end_date):
    """Calculate statistics for a period"""
    # Filter data
    period_nutrition = filter_by_date_range(nutrition_df, start_date, end_date)
    period_activities = filter_by_date_range(activities_df, start_date, end_date)
    
    # Calculate stats
    stats = {
        'days': (end_date - start_date).days + 1,
        'total_calories': 0,
        'avg_calories': 0,
        'total_protein': 0,
        'avg_protein': 0,
        'total_carbs': 0,
        'total_fats': 0,
        'total_calories_burned': 0,
        'avg_calories_burned': 0,
        'total_workouts': 0,
        'cardio_sessions': 0,
        'strength_sessions': 0
    }
    
    if not period_nutrition.empty:
        # Group by date and sum
        daily_nutrition = period_nutrition.groupby('datum').agg({
            'calorien': 'sum',
            'eiwit': 'sum',
            'koolhydraten': 'sum',
            'vetten': 'sum'
        }).reset_index()
        
        stats['total_calories'] = daily_nutrition['calorien'].sum()
        stats['avg_calories'] = daily_nutrition['calorien'].mean()
        stats['total_protein'] = daily_nutrition['eiwit'].sum()
        stats['avg_protein'] = daily_nutrition['eiwit'].mean()
        stats['total_carbs'] = daily_nutrition['koolhydraten'].sum()
        stats['total_fats'] = daily_nutrition['vetten'].sum()
        stats['days_logged'] = len(daily_nutrition)
    
    if not period_activities.empty:
        # Calculate calories burned
        calories_burned, _ = calculate_total_calories_burned(period_activities)
        stats['total_calories_burned'] = calories_burned
        stats['avg_calories_burned'] = calories_burned / stats['days']
        stats['total_workouts'] = len(period_activities)
        stats['cardio_sessions'] = len(period_activities[period_activities['type'].str.lower() == 'cardio'])
        stats['strength_sessions'] = len(period_activities[period_activities['type'].str.lower() == 'kracht'])
    
    return stats

# Main App
def main():
    # Get current user info from session state
    username = st.session_state.get("username", "alex")
    name = st.session_state.get("name", "Alex")
    
    # Get user-specific sheet ID
    user_sheet_id = st.session_state.get('user_sheet_id')
    if not user_sheet_id:
        st.error("⚠️ Geen sheet ID gevonden. Log opnieuw in.")
        st.stop()
    
    # Initialize session state for targets
    if 'targets' not in st.session_state:
        st.session_state.targets = {
            'calories': 2000,
            'protein': 160,
            'carbs': 180,
            'fats': 60,
            'weight': 106.2
        }
    
    st.title("💪 Fitness Coach Dashboard")
    st.markdown(f"**{name} - Dashboard**")
    
    # ============================================
    # QUICK ACTIONS - Mobile Friendly
    # ============================================
    st.markdown("### ⚡ Snelle Acties")
    
    # Initialize quick action in session state
    if 'quick_action' not in st.session_state:
        st.session_state.quick_action = None
    
    # Quick action info - simple text instructions (only show on mobile)
    st.markdown('<div class="quick-action-tip">', unsafe_allow_html=True)
    st.info("💡 **Tip**: Scroll naar beneden naar de **📝 Data Invoer** tab om snel iets toe te voegen!")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuratie")
        
        # Show user's sheet ID (read-only)
        st.text_input(
            "Jouw Google Sheets ID",
            value=user_sheet_id,
            disabled=True,
            help="Jouw persoonlijke sheet (automatisch geselecteerd)"
        )
        
        if st.button("🔄 Data Verversen", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Date Range Selector
        st.markdown("### 📅 Periode Selectie")
        
        view_mode = st.radio(
            "Weergave",
            ["📅 Dag", "📊 Week", "📈 Maand", "🗓️ Aangepast"],
            label_visibility="collapsed"
        )
        
        today = datetime.now().date()
        
        # Navigation buttons using session state
        if 'current_date' not in st.session_state:
            st.session_state.current_date = today
        
        if view_mode == "📅 Dag":
            # Navigation buttons
            col_prev, col_date, col_next = st.columns([1, 3, 1])
            
            with col_prev:
                if st.button("◀", key="prev_day", use_container_width=True):
                    st.session_state.current_date = st.session_state.current_date - timedelta(days=1)
                    st.rerun()
            
            with col_date:
                selected_date = st.date_input(
                    "Selecteer datum",
                    value=st.session_state.current_date,
                    max_value=today,
                    key=f"date_picker_{st.session_state.current_date}"
                )
                if selected_date != st.session_state.current_date:
                    st.session_state.current_date = selected_date
                    st.rerun()
            
            with col_next:
                can_go_forward = st.session_state.current_date < today
                if st.button("▶", key="next_day", use_container_width=True, disabled=not can_go_forward):
                    if can_go_forward:
                        st.session_state.current_date = st.session_state.current_date + timedelta(days=1)
                        st.rerun()
            
            start_date = st.session_state.current_date
            end_date = st.session_state.current_date
            date_range_text = st.session_state.current_date.strftime("%d/%m/%Y")
        
        elif view_mode == "📊 Week":
            # Get start of current week (Monday)
            if 'current_week' not in st.session_state:
                st.session_state.current_week = today - timedelta(days=today.weekday())
            
            col_prev, col_date, col_next = st.columns([1, 3, 1])
            
            with col_prev:
                if st.button("◀", key="prev_week", use_container_width=True):
                    st.session_state.current_week = st.session_state.current_week - timedelta(days=7)
                    st.rerun()
            
            with col_date:
                selected_week = st.date_input(
                    "Week startdatum (maandag)",
                    value=st.session_state.current_week,
                    max_value=today,
                    key=f"week_picker_{st.session_state.current_week}"
                )
                if selected_week != st.session_state.current_week:
                    st.session_state.current_week = selected_week - timedelta(days=selected_week.weekday())
                    st.rerun()
            
            with col_next:
                next_week = st.session_state.current_week + timedelta(days=7)
                can_go_forward = next_week <= today
                if st.button("▶", key="next_week", use_container_width=True, disabled=not can_go_forward):
                    if can_go_forward:
                        st.session_state.current_week = next_week
                        st.rerun()
            
            start_date = st.session_state.current_week - timedelta(days=st.session_state.current_week.weekday())
            end_date = start_date + timedelta(days=6)
            date_range_text = f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
        
        elif view_mode == "📈 Maand":
            if 'current_month' not in st.session_state:
                st.session_state.current_month = today.replace(day=1)
            
            col_prev, col_date, col_next = st.columns([1, 3, 1])
            
            with col_prev:
                if st.button("◀", key="prev_month", use_container_width=True):
                    # Go to previous month
                    if st.session_state.current_month.month == 1:
                        st.session_state.current_month = st.session_state.current_month.replace(year=st.session_state.current_month.year - 1, month=12)
                    else:
                        st.session_state.current_month = st.session_state.current_month.replace(month=st.session_state.current_month.month - 1)
                    st.rerun()
            
            with col_date:
                selected_month = st.date_input(
                    "Selecteer maand",
                    value=st.session_state.current_month,
                    max_value=today,
                    key=f"month_picker_{st.session_state.current_month}"
                )
                if selected_month.replace(day=1) != st.session_state.current_month:
                    st.session_state.current_month = selected_month.replace(day=1)
                    st.rerun()
            
            with col_next:
                # Calculate next month
                if st.session_state.current_month.month == 12:
                    next_month = st.session_state.current_month.replace(year=st.session_state.current_month.year + 1, month=1)
                else:
                    next_month = st.session_state.current_month.replace(month=st.session_state.current_month.month + 1)
                
                can_go_forward = next_month <= today
                if st.button("▶", key="next_month", use_container_width=True, disabled=not can_go_forward):
                    if can_go_forward:
                        st.session_state.current_month = next_month
                        st.rerun()
            
            start_date = st.session_state.current_month
            # Get last day of month
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
            
            # Consistent date format: dd/mm - dd/mm/yyyy
            date_range_text = f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
        
        else:  # Aangepast
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Van", value=today - timedelta(days=7), max_value=today)
            with col2:
                end_date = st.date_input("Tot", value=today, max_value=today)
            date_range_text = f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
        
        st.info(f"📊 **{date_range_text}**")
        
        st.markdown("---")
        
        # Focus Mode Toggle
        st.markdown("### 🎯 Weergave Modus")
        if 'focus_mode' not in st.session_state:
            st.session_state.focus_mode = "detailed"
        
        focus_mode = st.radio(
            "Kies weergave",
            ["🎯 Quick View", "📊 Detailed"],
            index=0 if st.session_state.focus_mode == "quick" else 1,
            label_visibility="collapsed",
            key="focus_mode_radio"
        )
        st.session_state.focus_mode = "quick" if focus_mode == "🎯 Quick View" else "detailed"
        
        if st.session_state.focus_mode == "quick":
            st.caption("✨ Alleen essentiële metrics en insights")
        else:
            st.caption("📈 Volledige grafieken en analyses")
        
        st.markdown("---")
        st.markdown("### 🎯 Dagelijkse Doelen")
        
        # Editable targets
        targets = st.session_state.targets
        
        with st.expander("⚙️ Doelen Aanpassen", expanded=False):
            st.markdown('<p style="color: white; font-weight: bold; font-size: 16px; margin-bottom: 10px;">**Voeding Doelen**</p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                new_calories = st.number_input("Calorieën (kcal)", min_value=1200, max_value=4000, value=targets['calories'], step=50, key="cal_input")
                new_carbs = st.number_input("Koolhydraten (g)", min_value=50, max_value=400, value=targets['carbs'], step=10, key="carbs_input")
            with col2:
                new_protein = st.number_input("Eiwit (g)", min_value=80, max_value=300, value=targets['protein'], step=5, key="prot_input")
                new_fats = st.number_input("Vetten (g)", min_value=30, max_value=150, value=targets['fats'], step=5, key="fats_input")
            
            st.markdown('<p style="color: white; font-weight: bold; font-size: 16px; margin-top: 15px; margin-bottom: 10px;">**Persoonlijke Info**</p>', unsafe_allow_html=True)
            new_weight = st.number_input("Huidige Gewicht (kg)", min_value=50.0, max_value=200.0, value=targets['weight'], step=0.1, key="weight_input")
            
            if st.button("💾 Doelen Opslaan", use_container_width=True):
                st.session_state.targets = {
                    'calories': new_calories,
                    'protein': new_protein,
                    'carbs': new_carbs,
                    'fats': new_fats,
                    'weight': new_weight
                }
                st.success("✅ Doelen opgeslagen!")
                st.rerun()
        
        # Display current targets
        st.metric("🔥 Calorieën", f"{targets['calories']} kcal")
        st.metric("💪 Eiwit", f"{targets['protein']}g")
        st.metric("🌾 Koolhydraten", f"{targets['carbs']}g")
        st.metric("🥑 Vetten", f"{targets['fats']}g")
    
    # Load data OUTSIDE sidebar
    with st.sidebar:
        if st.button("🔄 Ververs Data", help="Herlaad data van Google Sheets"):
            st.cache_data.clear()
            st.rerun()
    
    with st.spinner("Data laden..."):
        # Use user-specific sheet ID (already set at top of function)
        data = load_sheet_data(user_sheet_id)
    
    if data is None:
        st.error("❌ Kon data niet laden. Controleer of je sheet publiek is!")
        st.info("💡 Ga naar je Google Sheet → Delen → 'Iedereen met de link' → Weergever")
        return
    
    # Get latest weight from daily tracking
    gewicht_df = data.get('gewicht', pd.DataFrame())
    current_weight = 106.2  # Default fallback
    
    if not gewicht_df.empty and 'datum' in gewicht_df.columns and 'gewicht' in gewicht_df.columns:
        try:
            # Parse dates and sort to get most recent
            gewicht_df_copy = gewicht_df.copy()
            gewicht_df_copy['date_obj'] = pd.to_datetime(gewicht_df_copy['datum'], dayfirst=True, errors='coerce')
            gewicht_df_copy = gewicht_df_copy.dropna(subset=['date_obj'])
            
            if not gewicht_df_copy.empty:
                gewicht_df_copy = gewicht_df_copy.sort_values('date_obj', ascending=False)
                latest_weight = gewicht_df_copy.iloc[0]['gewicht']
                if pd.notna(latest_weight):
                    current_weight = float(latest_weight)
        except:
            pass
    
    # Update session state with current weight
    st.session_state.targets['weight'] = current_weight
    
    # Calculate data for sidebar actions (before tabs)
    nutrition_df = data.get('voeding', pd.DataFrame())
    activities_df = data.get('activiteiten', pd.DataFrame())
    period_stats = calculate_period_stats(nutrition_df, activities_df, start_date, end_date)
    
    if view_mode == "📅 Dag":
        today_str = start_date.strftime("%d/%m/%Y")
        totals = calculate_nutrition_totals(nutrition_df, today_str)
    else:
        totals = {
            'calorien': period_stats['avg_calories'],
            'eiwit': period_stats['avg_protein'],
            'koolhydraten': period_stats['total_carbs'] / max(period_stats['days'], 1),
            'vetten': period_stats['total_fats'] / max(period_stats['days'], 1)
        }
    
    # Generate recommendations and ADD TO SIDEBAR
    recommendations = generate_action_recommendations(totals, period_stats, targets)
    
    # Add default actions if empty
    if not recommendations['nutrition_actions']:
        recommendations['nutrition_actions'] = [
            "Blijf je eiwitinname hoog houden (minimaal 180g)",
            "Drink minimaal 2-3 liter water",
            "Eet binnen 30 min na training voor optimaal herstel"
        ]
    
    if not recommendations['goals']:
        recommendations['goals'] = [
            "Plan je trainingen voor de komende week",
            "Track alle maaltijden voor beter inzicht",
            "4+ trainingen deze week voor optimaal resultaat"
        ]
    
    # Add actions to sidebar NOW
    with st.sidebar:
        st.markdown("---")
        with st.expander("🎯 Acties voor Morgen", expanded=True):
            st.markdown("**🍳 Voeding**")
            for action in recommendations['nutrition_actions']:
                st.markdown(f"• {action}")
            
            st.markdown("")
            st.markdown("**🎯 Doelen**")
            for goal in recommendations['goals']:
                st.markdown(f"• {goal}")
    
    # ============================================
    # AI DAGCOACH (Hidden on mobile to reduce clutter)
    # ============================================
    st.markdown('<div class="ai-coach-section">', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🤖 AI Dagcoach")
    
    col_coach1, col_coach2 = st.columns([3, 1])
    
    with col_coach1:
        st.markdown("**Krijg een persoonlijk advies voor de rest van je dag** 🎯")
    
    with col_coach2:
        if st.button("🔮 Genereer Advies", use_container_width=True, type="secondary"):
            with st.spinner("🤖 AI analyseert je dag..."):
                try:
                    # Verzamel huidige dag data
                    today = datetime.now().date()
                    today_str = today.strftime('%d-%m-%Y')
                    voeding_data = get_voeding_data()
                    
                    # Get nutrition totals using the existing function
                    current_nutrition = calculate_nutrition_totals(voeding_data, today_str)
                    
                    # Verzamel workout data
                    workouts_today = []
                    try:
                        kracht_data = get_kracht_data()
                        if kracht_data is not None and not kracht_data.empty:
                            today_workouts = kracht_data[kracht_data['Datum'] == today.strftime('%d-%m-%Y')]
                            workouts_today = today_workouts['Oefening'].tolist() if not today_workouts.empty else []
                    except:
                        pass
                    
                    # Verzamel stappen
                    steps_today = 0
                    try:
                        stappen_data = get_stappen_data()
                        if stappen_data is not None and not stappen_data.empty:
                            today_steps = stappen_data[stappen_data['Datum'] == today.strftime('%d-%m-%Y')]
                            steps_today = int(today_steps['Stappen'].sum()) if not today_steps.empty else 0
                    except:
                        pass
                    
                    # Build data dictionary
                    current_data = {
                        'nutrition': current_nutrition,
                        'workouts': workouts_today,
                        'steps': steps_today
                    }
                    
                    # Genereer coaching
                    if HELPERS_AVAILABLE:
                        coaching_report = groq_helper.generate_daily_coaching(
                            current_data=current_data,
                            targets=st.session_state.targets,
                            name=name
                        )
                        
                        st.markdown("---")
                        st.markdown(coaching_report)
                        st.markdown("---")
                        st.caption(f"🕐 Gegenereerd op {datetime.now().strftime('%H:%M')}")
                    else:
                        st.error("AI Dagcoach is niet beschikbaar (groq_helper niet geladen)")
                        
                except Exception as e:
                    st.error(f"❌ Fout bij genereren rapport: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close AI coach section
    
    # Remove old quick action messages - simplified now
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overzicht", 
        "🍽️ Voeding", 
        "❤️ Cardio", 
        "💪 Kracht", 
        "📈 Progressie",
        "📝 Data Invoer"
    ])
    
    # Get targets for use in tabs
    targets = st.session_state.targets
    
    # TAB 1: OVERZICHT
    with tab1:
        # Show period header
        st.markdown(f"""
        <div style="background: rgba(139, 92, 246, 0.2); padding: 15px; border-radius: 10px; 
                    border-left: 4px solid #8b5cf6; margin-bottom: 20px;">
            <h3 style="margin: 0;">📊 Overzicht: {date_range_text}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        nutrition_df = data.get('voeding', pd.DataFrame())
        activities_df = data.get('activiteiten', pd.DataFrame())
        
        # Calculate period statistics
        period_stats = calculate_period_stats(nutrition_df, activities_df, start_date, end_date)
        
        # For single day view, show daily data
        if view_mode == "📅 Dag":
            today_str = start_date.strftime("%d/%m/%Y")
            totals = calculate_nutrition_totals(nutrition_df, today_str)
        else:
            # For multi-day view, show averages
            totals = {
                'calorien': period_stats['avg_calories'],
                'eiwit': period_stats['avg_protein'],
                'koolhydraten': period_stats['total_carbs'] / max(period_stats['days'], 1),
                'vetten': period_stats['total_fats'] / max(period_stats['days'], 1)
            }
        
        # Calculate calories burned from activities
        if view_mode == "📅 Dag":
            calories_burned, activities_with_calories = calculate_total_calories_burned(activities_df, today_str)
        else:
            # For period view, calculate total and average
            filtered_activities = filter_by_date_range(activities_df, start_date, end_date)
            calories_burned = period_stats['avg_calories_burned']
            activities_with_calories = filtered_activities
        
        # Calculate net calories (consumed - burned)
        net_calories = totals['calorien'] - calories_burned
        
        # Metrics with colored backgrounds
        # Show if it's average or daily
        metric_label = "gemiddeld per dag" if view_mode != "📅 Dag" else "vandaag"
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cal_progress_pct = totals['calorien']/targets['calories']*100 if targets['calories'] > 0 else 0
            is_over = cal_progress_pct > 110
            
            # Bereken bar breedtes - altijd genormaliseerd naar 100%
            if cal_progress_pct <= 100:
                # Onder 100%: toon alleen groene balk van X%
                cal_green_width = cal_progress_pct
                cal_red_width = 0
                cal_gray_width = 100 - cal_progress_pct  # EXPLICIETE GRIJZE BALK
            else:
                # Boven 100%: groen = (100/totaal)*100, rood = rest
                cal_green_width = (100 / cal_progress_pct) * 100
                cal_red_width = 100 - cal_green_width
                cal_gray_width = 0  # Geen grijze balk nodig
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(220, 38, 38, 0.1)); 
                        padding: 18px 20px 15px 20px; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.3);
                        text-align: center; height: 160px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🔥 Calorieën</div>
                <div style="font-size: 30px; font-weight: bold; color: #fb923c; margin: 8px 0;">{totals['calorien']:.0f}</div>
                <div style="font-size: 12px; opacity: 0.7; margin-bottom: 5px;">
                    / {targets['calories']} doel • <span style="font-weight: bold; color: {'#ef4444' if is_over else '#22c55e'};">{cal_progress_pct:.0f}%</span> {'⚠️' if is_over else '✓'}
                </div>
                <div style="height: 8px; background: transparent; border-radius: 4px; overflow: hidden; width: 100%; margin-top: 8px; display: flex;">
                    <div style="height: 100%; background: linear-gradient(90deg, #22c55e, #10b981); width: {cal_green_width:.1f}%; flex-shrink: 0;"></div>
                    {f'<div style="height: 100%; background: linear-gradient(90deg, #ef4444, #dc2626); width: {cal_red_width:.1f}%; flex-shrink: 0;"></div>' if cal_red_width > 0 else ''}
                    {f'<div style="height: 100%; background: #3a3a3a; width: {cal_gray_width:.1f}%; flex-shrink: 0;"></div>' if cal_gray_width > 0 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            protein_progress_pct = totals['eiwit']/targets['protein']*100 if targets['protein'] > 0 else 0
            is_over = protein_progress_pct > 130
            # Bereken bar breedtes - altijd genormaliseerd naar 100%
            if protein_progress_pct <= 100:
                # Onder 100%: toon alleen blauwe balk van X%
                protein_green_width = protein_progress_pct
                protein_red_width = 0
                protein_gray_width = 100 - protein_progress_pct  # EXPLICIETE GRIJZE BALK
            else:
                # Boven 100%: blauw = (100/totaal)*100, rood = rest
                protein_green_width = (100 / protein_progress_pct) * 100
                protein_red_width = 100 - protein_green_width
                protein_gray_width = 0  # Geen grijze balk nodigdth
                protein_gray_width = 0  # Geen grijs nodig
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(99, 102, 241, 0.1)); 
                        padding: 18px 20px 15px 20px; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.3);
                        text-align: center; height: 160px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">💪 Eiwit</div>
                <div style="font-size: 30px; font-weight: bold; color: #60a5fa; margin: 8px 0;">{totals['eiwit']:.0f}<span style="font-size: 16px; opacity: 0.7;"> g</span></div>
                <div style="font-size: 12px; opacity: 0.7; margin-bottom: 5px;">
                    / {targets['protein']}g doel • <span style="font-weight: bold; color: {'#ef4444' if is_over else '#22c55e'};">{protein_progress_pct:.0f}%</span> {'⚠️' if is_over else '✓'}
                </div>
                <div style="height: 8px; background: transparent; border-radius: 4px; overflow: hidden; width: 100%; margin-top: 8px; display: flex;">
                    <div style="height: 100%; background: linear-gradient(90deg, #60a5fa, #3b82f6); width: {protein_green_width:.1f}%; flex-shrink: 0;"></div>
                    {f'<div style="height: 100%; background: linear-gradient(90deg, #ef4444, #dc2626); width: {protein_red_width:.1f}%; flex-shrink: 0;"></div>' if protein_red_width > 0 else ''}
                    {f'<div style="height: 100%; background: #3a3a3a; width: {protein_gray_width:.1f}%; flex-shrink: 0;"></div>' if protein_gray_width > 0 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            carbs_progress_pct = totals['koolhydraten']/targets['carbs']*100 if targets['carbs'] > 0 else 0
            is_over = carbs_progress_pct > 110
            
            # Bereken bar breedtes - altijd genormaliseerd naar 100%
            if carbs_progress_pct <= 100:
                carbs_green_width = carbs_progress_pct
                carbs_red_width = 0
                carbs_gray_width = 100 - carbs_progress_pct  # Vul lege ruimte met grijs
            else:
                carbs_green_width = (100 / carbs_progress_pct) * 100
                carbs_red_width = 100 - carbs_green_width
                carbs_gray_width = 0  # Geen grijs nodig
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.1)); 
                        padding: 18px 20px 15px 20px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);
                        text-align: center; height: 160px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🌾 Koolhydraten</div>
                <div style="font-size: 30px; font-weight: bold; color: #34d399; margin: 8px 0;">{totals['koolhydraten']:.0f}<span style="font-size: 16px; opacity: 0.7;"> g</span></div>
                <div style="font-size: 12px; opacity: 0.7; margin-bottom: 5px;">
                    / {targets['carbs']}g doel • <span style="font-weight: bold; color: {'#ef4444' if is_over else '#22c55e'};">{carbs_progress_pct:.0f}%</span> {'⚠️' if is_over else '✓'}
                </div>
                <div style="height: 8px; background: transparent; border-radius: 4px; overflow: hidden; width: 100%; margin-top: 8px; display: flex;">
                    {f'<div style="height: 100%; background: linear-gradient(90deg, #34d399, #10b981); width: {carbs_green_width:.1f}%; flex-shrink: 0;"></div>' if carbs_green_width > 0 else ''}
                    {f'<div style="height: 100%; background: linear-gradient(90deg, #ef4444, #dc2626); width: {carbs_red_width:.1f}%; flex-shrink: 0;"></div>' if carbs_red_width > 0 else ''}
                    {f'<div style="height: 100%; background: #555555; width: {carbs_gray_width:.1f}%; flex-shrink: 0;"></div>' if carbs_gray_width > 0 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            fats_progress_pct = totals['vetten']/targets['fats']*100 if targets['fats'] > 0 else 0
            is_over = fats_progress_pct > 110
            
            # Bereken bar breedtes - altijd genormaliseerd naar 100%
            if fats_progress_pct <= 100:
                fats_green_width = fats_progress_pct
                fats_red_width = 0
                fats_gray_width = 100 - fats_progress_pct  # Vul lege ruimte met grijs
            else:
                fats_green_width = (100 / fats_progress_pct) * 100
                fats_red_width = 100 - fats_green_width
                fats_gray_width = 0  # Geen grijs nodig
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.1)); 
                        padding: 18px 20px 15px 20px; border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.3);
                        text-align: center; height: 160px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🥑 Vetten</div>
                <div style="font-size: 30px; font-weight: bold; color: #a78bfa; margin: 8px 0;">{totals['vetten']:.0f}<span style="font-size: 16px; opacity: 0.7;"> g</span></div>
                <div style="font-size: 12px; opacity: 0.7; margin-bottom: 5px;">
                    / {targets['fats']}g doel • <span style="font-weight: bold; color: {'#ef4444' if is_over else '#22c55e'};">{fats_progress_pct:.0f}%</span> {'⚠️' if is_over else '✓'}
                </div>
                <div style="height: 8px; background: transparent; border-radius: 4px; overflow: hidden; width: 100%; margin-top: 8px; display: flex;">
                    <div style="height: 100%; background: linear-gradient(90deg, #a78bfa, #8b5cf6); width: {fats_green_width:.1f}%; flex-shrink: 0;"></div>
                    {f'<div style="height: 100%; background: linear-gradient(90deg, #ef4444, #dc2626); width: {fats_red_width:.1f}%; flex-shrink: 0;"></div>' if fats_red_width > 0 else ''}
                    {f'<div style="height: 100%; background: #3a3a3a; width: {fats_gray_width:.1f}%; flex-shrink: 0;"></div>' if fats_gray_width > 0 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Calories burned section
        col1, col2, col3 = st.columns(3)
        
        with col1:
            calories_label = "door activiteiten" if view_mode != "📅 Dag" else "door activiteiten vandaag"
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(185, 28, 28, 0.1)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.3);
                        text-align: center; height: 160px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🏃 Calorieën Verbrand</div>
                <div style="font-size: 30px; font-weight: bold; color: #ef4444; margin: 12px 0;">{calories_burned:.0f}<span style="font-size: 16px; opacity: 0.7;"> kcal</span></div>
                <div style="font-size: 12px; opacity: 0.7; margin-top: 8px;">{calories_label} ({metric_label})</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            net_color = "#4ade80" if net_calories > 0 else "#f87171"
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(20, 184, 166, 0.2), rgba(13, 148, 136, 0.1)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(20, 184, 166, 0.3);
                        text-align: center; height: 160px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">⚖️ Netto Calorieën</div>
                <div style="font-size: 30px; font-weight: bold; color: {net_color}; margin: 12px 0;">{net_calories:.0f}<span style="font-size: 16px; opacity: 0.7;"> kcal</span></div>
                <div style="font-size: 12px; opacity: 0.7; margin-top: 8px;">gegeten - verbrand ({metric_label})</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Calculate activity count for the period
            if view_mode == "📅 Dag":
                if not activities_with_calories.empty:
                    cardio_count = len(activities_with_calories[activities_with_calories['type'].str.lower() == 'cardio'])
                    kracht_count = len(activities_with_calories[activities_with_calories['type'].str.lower() == 'kracht'])
                    activity_summary = f"{cardio_count} cardio + {kracht_count} kracht"
                    label = "sessies vandaag"
                else:
                    activity_summary = "Geen activiteiten"
                    label = ""
            else:
                activity_summary = f"{period_stats['cardio_sessions']} cardio + {period_stats['strength_sessions']} kracht"
                label = f"totaal ({period_stats['total_workouts']} sessies)"
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(126, 34, 206, 0.1)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(168, 85, 247, 0.3);
                        text-align: center; height: 160px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">💪 Activiteiten</div>
                <div style="font-size: 28px; font-weight: bold; color: #a855f7; margin: 12px 0;">{activity_summary}</div>
                <div style="font-size: 12px; opacity: 0.7; margin-top: 8px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Period Summary Stats (for multi-day views) - always show this
        if view_mode != "📅 Dag":
            st.markdown("### 📊 Periode Samenvatting")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div style="background: rgba(59, 130, 246, 0.2); padding: 15px; border-radius: 8px; 
                            border: 1px solid rgba(59, 130, 246, 0.3); text-align: center;">
                    <div style="font-size: 30px; font-weight: bold; color: #3b82f6;">{period_stats['days']}</div>
                    <div style="font-size: 14px; opacity: 0.8; margin-top: 5px;">Dagen</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: rgba(16, 185, 129, 0.2); padding: 15px; border-radius: 8px; 
                            border: 1px solid rgba(16, 185, 129, 0.3); text-align: center;">
                    <div style="font-size: 30px; font-weight: bold; color: #10b981;">{period_stats['total_workouts']}</div>
                    <div style="font-size: 14px; opacity: 0.8; margin-top: 5px;">Trainingen</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                avg_cals_per_day = period_stats['avg_calories']
                st.markdown(f"""
                <div style="background: rgba(249, 115, 22, 0.2); padding: 15px; border-radius: 8px; 
                            border: 1px solid rgba(249, 115, 22, 0.3); text-align: center;">
                    <div style="font-size: 30px; font-weight: bold; color: #f97316;">{avg_cals_per_day:.0f}</div>
                    <div style="font-size: 14px; opacity: 0.8; margin-top: 5px;">Ø Calorieën/dag</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                avg_protein_per_day = period_stats['avg_protein']
                st.markdown(f"""
                <div style="background: rgba(139, 92, 246, 0.2); padding: 15px; border-radius: 8px; 
                            border: 1px solid rgba(139, 92, 246, 0.3); text-align: center;">
                    <div style="font-size: 30px; font-weight: bold; color: #8b5cf6;">{avg_protein_per_day:.0f}g</div>
                    <div style="font-size: 14px; opacity: 0.8; margin-top: 5px;">Ø Eiwit/dag</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Period Charts (for week/month/custom views) - only in detailed mode
        if view_mode != "📅 Dag" and not nutrition_df.empty and st.session_state.focus_mode == "detailed":
            st.markdown("### 📈 Periode Overzicht")
            
            # Filter data for period
            period_nutrition = filter_by_date_range(nutrition_df, start_date, end_date)
            period_activities = filter_by_date_range(activities_df, start_date, end_date)
            
            if not period_nutrition.empty:
                # Daily nutrition chart
                daily_nutrition = period_nutrition.groupby('datum').agg({
                    'calorien': 'sum',
                    'eiwit': 'sum',
                    'koolhydraten': 'sum',
                    'vetten': 'sum'
                }).reset_index()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Calorie trend
                    fig_cal = go.Figure()
                    fig_cal.add_trace(go.Scatter(
                        x=daily_nutrition['datum'], 
                        y=daily_nutrition['calorien'],
                        mode='lines+markers',
                        name='Calorieën',
                        line=dict(color='#f97316', width=3),
                        marker=dict(size=8)
                    ))
                    fig_cal.add_hline(y=targets['calories'], line_dash="dash", line_color="white", 
                                     annotation_text=f"Doel: {targets['calories']} kcal", annotation_position="right")
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'title': "Dagelijkse Calorie-inname",
                        'xaxis_title': "Datum",
                        'yaxis_title': "Calorieën",
                        'height': 300
                    })
                    fig_cal.update_layout(**layout)
                    st.plotly_chart(fig_cal, key="tab1_cal", use_container_width=True, config={"displayModeBar": False})
                
                with col2:
                    # Macros pie chart (average)
                    avg_protein = daily_nutrition['eiwit'].mean()
                    avg_carbs = daily_nutrition['koolhydraten'].mean()
                    avg_fats = daily_nutrition['vetten'].mean()
                    
                    fig_macro = go.Figure(data=[go.Pie(
                        labels=['Eiwit', 'Koolhydraten', 'Vetten'],
                        values=[avg_protein * 4, avg_carbs * 4, avg_fats * 9],  # Convert to calories
                        marker=dict(colors=['#3b82f6', '#10b981', '#8b5cf6']),
                        hole=0.4
                    )])
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'title': "Gemiddelde Macro Verdeling",
                        'height': 300,
                        'showlegend': True
                    })
                    fig_macro.update_layout(**layout)
                    st.plotly_chart(fig_macro, key="tab1_macro", use_container_width=True, config={"displayModeBar": False})
                
                # Protein trend
                fig_protein = go.Figure()
                fig_protein.add_trace(go.Bar(
                    x=daily_nutrition['datum'],
                    y=daily_nutrition['eiwit'],
                    name='Eiwit',
                    marker_color='#3b82f6'
                ))
                fig_protein.add_hline(y=targets['protein'], line_dash="dash", line_color="white",
                                     annotation_text=f"Doel: {targets['protein']}g", annotation_position="right")
                layout = get_chart_layout_defaults()
                layout.update({
                    'title': "Dagelijkse Eiwitinname",
                    'xaxis_title': "Datum",
                    'yaxis_title': "Eiwit (g)",
                    'height': 300
                })
                fig_protein.update_layout(**layout)
                st.plotly_chart(fig_protein, key="tab1_protein", use_container_width=True, config={"displayModeBar": False})
            
            # Activity summary for period
            if not period_activities.empty:
                st.markdown("### 🏃 Activiteiten Overzicht")
                
                # Calculate daily calories burned
                activities_by_date = []
                current_date = start_date
                while current_date <= end_date:
                    date_str = current_date.strftime("%d/%m/%Y")
                    day_activities = period_activities[period_activities['datum'] == date_str]
                    
                    if not day_activities.empty:
                        cals, _ = calculate_total_calories_burned(day_activities)
                        cardio = len(day_activities[day_activities['type'].str.lower() == 'cardio'])
                        kracht = len(day_activities[day_activities['type'].str.lower() == 'kracht'])
                    else:
                        cals = 0
                        cardio = 0
                        kracht = 0
                    
                    activities_by_date.append({
                        'datum': date_str,
                        'calories': cals,
                        'cardio': cardio,
                        'kracht': kracht,
                        'total': cardio + kracht
                    })
                    current_date += timedelta(days=1)
                
                activities_chart_df = pd.DataFrame(activities_by_date)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Calories burned chart
                    fig_burn = go.Figure()
                    fig_burn.add_trace(go.Bar(
                        x=activities_chart_df['datum'],
                        y=activities_chart_df['calories'],
                        name='Calorieën Verbrand',
                        marker_color='#ef4444'
                    ))
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'title': "Calorieën Verbrand per Dag",
                        'xaxis_title': "Datum",
                        'yaxis_title': "Calorieën",
                        'height': 300
                    })
                    fig_burn.update_layout(**layout)
                    st.plotly_chart(fig_burn, key="tab1_burn", use_container_width=True, config={"displayModeBar": False})
                
                with col2:
                    # Workout frequency
                    fig_workouts = go.Figure()
                    fig_workouts.add_trace(go.Bar(
                        x=activities_chart_df['datum'],
                        y=activities_chart_df['cardio'],
                        name='Cardio',
                        marker_color='#10b981'
                    ))
                    fig_workouts.add_trace(go.Bar(
                        x=activities_chart_df['datum'],
                        y=activities_chart_df['kracht'],
                        name='Kracht',
                        marker_color='#8b5cf6'
                    ))
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'title': "Trainingen per Dag",
                        'xaxis_title': "Datum",
                        'yaxis_title': "Aantal",
                        'barmode': "stack",
                        'height': 300
                    })
                    fig_workouts.update_layout(**layout)
                    st.plotly_chart(fig_workouts, key="tab1_workouts", use_container_width=True, config={"displayModeBar": False})
        
        # Progress bars with beautiful styling
        st.markdown("<br>", unsafe_allow_html=True)
        progress_title = "📊 Voortgang Vandaag" if view_mode == "📅 Dag" else "📊 Gemiddelde Voortgang"
        st.markdown(f"### {progress_title}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cal_progress_pct = (totals['calorien'] / targets['calories'] * 100) if targets['calories'] > 0 else 0
            cal_actual = totals['calorien']
            cal_target = targets['calories']
            
            # Bereken bar breedtes - altijd genormaliseerd naar 100%
            if cal_progress_pct <= 100:
                cal_green_width = cal_progress_pct
                cal_red_width = 0
                cal_gray_width = 100 - cal_progress_pct  # Vul lege ruimte met grijs
            else:
                cal_green_width = (100 / cal_progress_pct) * 100
                cal_red_width = 100 - cal_green_width
                cal_gray_width = 0  # Geen grijs nodig
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.1), rgba(251, 146, 60, 0.05)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.3);
                        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.1);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-weight: 600; font-size: 14px;">🔥 Calorieën</span>
                    <span style="font-weight: 700; color: {'#ef4444' if cal_progress_pct > 110 else '#22c55e'};">{cal_actual:.0f} / {cal_target} kcal</span>
                </div>
                <div style="background: transparent; border-radius: 10px; height: 12px; overflow: hidden; display: flex;">
                    {f'<div style="background: linear-gradient(90deg, #22c55e, #10b981); width: {cal_green_width:.1f}%; height: 100%; flex-shrink: 0;"></div>' if cal_green_width > 0 else ''}
                    {f'<div style="background: linear-gradient(90deg, #ef4444, #dc2626); width: {cal_red_width:.1f}%; height: 100%; flex-shrink: 0;"></div>' if cal_red_width > 0 else ''}
                    {f'<div style="background: #666666; width: {cal_gray_width:.1f}%; height: 100%; flex-shrink: 0;"></div>' if cal_gray_width > 0 else ''}
                </div>
                <div style="text-align: right; margin-top: 5px; font-size: 12px; opacity: 0.8;">
                    {cal_progress_pct:.0f}% behaald
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            protein_progress_pct = (totals['eiwit'] / targets['protein'] * 100) if targets['protein'] > 0 else 0
            protein_actual = totals['eiwit']
            protein_target = targets['protein']
            
            # Bereken bar breedtes - altijd genormaliseerd naar 100%
            if protein_progress_pct <= 100:
                protein_green_width = protein_progress_pct
                protein_red_width = 0
                protein_gray_width = 100 - protein_progress_pct  # Vul lege ruimte met grijs
            else:
                protein_green_width = (100 / protein_progress_pct) * 100
                protein_red_width = 100 - protein_green_width
                protein_gray_width = 0  # Geen grijs nodig
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(96, 165, 250, 0.05)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.3);
                        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-weight: 600; font-size: 14px;">💪 Eiwit</span>
                    <span style="font-weight: 700; color: {'#ef4444' if protein_progress_pct > 130 else '#22c55e'};">{protein_actual:.0f} / {protein_target}g</span>
                </div>
                <div style="background: transparent; border-radius: 10px; height: 12px; overflow: hidden; display: flex;">
                    {f'<div style="background: linear-gradient(90deg, #60a5fa, #3b82f6); width: {protein_green_width:.1f}%; height: 100%; flex-shrink: 0;"></div>' if protein_green_width > 0 else ''}
                    {f'<div style="background: linear-gradient(90deg, #ef4444, #dc2626); width: {protein_red_width:.1f}%; height: 100%; flex-shrink: 0;"></div>' if protein_red_width > 0 else ''}
                    {f'<div style="background: #666666; width: {protein_gray_width:.1f}%; height: 100%; flex-shrink: 0;"></div>' if protein_gray_width > 0 else ''}
                </div>
                <div style="text-align: right; margin-top: 5px; font-size: 12px; opacity: 0.8;">
                    {protein_progress_pct:.0f}% behaald
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Smart Insights
        insights = generate_insights(period_stats, totals, view_mode, targets)
        
        if insights:
            st.markdown("### 🤖 Slimme Inzichten")
            
            for insight in insights:
                if insight['type'] == 'success':
                    bg_color = "rgba(34, 197, 94, 0.2)"
                    border_color = "#22c55e"
                elif insight['type'] == 'warning':
                    bg_color = "rgba(249, 115, 22, 0.2)"
                    border_color = "#f97316"
                else:  # info
                    bg_color = "rgba(59, 130, 246, 0.2)"
                    border_color = "#3b82f6"
                
                st.markdown(f"""
                <div style="background: {bg_color}; padding: 15px; border-radius: 8px; 
                            border-left: 4px solid {border_color}; margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">
                        {insight['icon']} {insight['title']}
                    </div>
                    <div style="opacity: 0.9; font-size: 14px;">
                        {insight['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Alerts
        metingen_df = data.get('metingen', pd.DataFrame())
        trends = analyze_measurements(metingen_df)
        
        if trends and (trends['vet_change'] > 0.5 or trends['spier_change'] < -0.5):
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.2)); 
                        padding: 18px; border-radius: 10px; border-left: 4px solid #ef4444; margin: 20px 0;">
                <h3 style="margin: 0 0 15px 0;">⚠️ Belangrijke Waarschuwing!</h3>
                <p style="margin: 8px 0;"><strong>Vetpercentage gestegen:</strong> +{trends['vet_change']:.1f}%</p>
                <p style="margin: 8px 0;"><strong>Spiermassa gedaald:</strong> {trends['spier_change']:.1f} kg</p>
                <p style="margin: 15px 0 0 0; opacity: 0.9;"><strong>Conclusie:</strong> Je verliest spier in plaats van vet! Dit komt door te weinig calorieën en/of eiwit.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Action items - only in detailed mode
        if st.session_state.focus_mode == "detailed":
            st.markdown("---")
            st.markdown("### 📋 Analyse & Feedback")
            
            # Verbeterpunten data
            issues = []
            if totals['calorien'] < 1900:
                issues.append(f"🔴 Te weinig calorieën: {totals['calorien']:.0f} kcal is te laag voor training")
            if totals['vetten'] > 65:
                issues.append(f"🔴 Te veel vetten: {totals['vetten']:.0f}g (doel: 60g). Beperk zuivel en kookroom")
            if totals['eiwit'] < 140:
                issues.append(f"🟡 Eiwit te laag: {totals['eiwit']:.0f}g (doel: 160g)")
            issues.append("🟡 Voeg meer groenten toe bij elke maaltijd")
            
            # Successen data
            successes = []
            if totals['eiwit'] >= 140:
                successes.append(f"🟢 Uitstekende eiwitinname: {totals['eiwit']:.0f}g!")
            if totals['calorien'] >= 1900:
                successes.append("🟢 Goede calorie-inname voor training")
            successes.append("🟢 Consistente training en data bijhouden")
            
            # Render beide boxen in een flexbox container
            st.markdown(f"""
            <div style="display: flex; gap: 20px; align-items: stretch;">
                <div style="flex: 1; background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(239, 68, 68, 0.15)); 
                            padding: 18px; border-radius: 10px; border-left: 4px solid #fbbf24;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column;">
                    <h4 style="margin: 0 0 15px 0; color: #fbbf24;">⚠️ Verbeterpunten</h4>
                    <div style="line-height: 1.8; flex: 1;">
                        {'<br>'.join(issues)}
                    </div>
                </div>
                <div style="flex: 1; background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(16, 185, 129, 0.15)); 
                            padding: 18px; border-radius: 10px; border-left: 4px solid #22c55e;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column;">
                    <h4 style="margin: 0 0 15px 0; color: #22c55e;">✅ Wat Goed Gaat</h4>
                    <div style="line-height: 1.8; flex: 1;">
                        {'<br>'.join(successes)}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
    
    # TAB 2: VOEDING
    with tab2:
        st.header("🍽️ Voeding Overzicht")
        
        # Summary cards with glassmorphism styling
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(251, 146, 60, 0.1)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.3);
                        text-align: center; height: 120px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🔥 Calorieën</div>
                <div style="font-size: 30px; font-weight: bold; color: #fb923c; margin: 12px 0;">{totals['calorien']:.0f}<span style="font-size: 16px; opacity: 0.7;"> kcal</span></div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(96, 165, 250, 0.1)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.3);
                        text-align: center; height: 120px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">💪 Eiwit</div>
                <div style="font-size: 30px; font-weight: bold; color: #60a5fa; margin: 12px 0;">{totals['eiwit']:.0f}<span style="font-size: 16px; opacity: 0.7;"> g</span></div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(74, 222, 128, 0.1)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);
                        text-align: center; height: 120px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🌾 Koolhydraten</div>
                <div style="font-size: 30px; font-weight: bold; color: #34d399; margin: 12px 0;">{totals['koolhydraten']:.0f}<span style="font-size: 16px; opacity: 0.7;"> g</span></div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(234, 179, 8, 0.2), rgba(250, 204, 21, 0.1)); 
                        padding: 18px; border-radius: 12px; border: 1px solid rgba(234, 179, 8, 0.3);
                        text-align: center; height: 120px; box-sizing: border-box;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🥑 Vetten</div>
                <div style="font-size: 30px; font-weight: bold; color: #facc15; margin: 12px 0;">{totals['vetten']:.0f}<span style="font-size: 16px; opacity: 0.7;"> g</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not nutrition_df.empty:
            # Filter for selected date/period
            if view_mode == "📅 Dag":
                selected_date_str = start_date.strftime("%d/%m/%Y")
                today_meals = nutrition_df[nutrition_df['datum'] == selected_date_str]
                period_label = selected_date_str
            else:
                today_meals = filter_by_date_range(nutrition_df, start_date, end_date)
                period_label = date_range_text
            
            if not today_meals.empty:
                st.markdown(f"### 🍽️ Maaltijden: {period_label}")
                for _, meal in today_meals.iterrows():
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; 
                                border-left: 4px solid #8b5cf6; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                            <div>
                                <h4 style="margin: 0 0 5px 0; font-size: 18px;">{meal['maaltijd']}</h4>
                                <p style="margin: 0; opacity: 0.8; font-size: 14px;">{meal['omschrijving']}</p>
                            </div>
                            <div style="text-align: right;">
                                <div style="color: #f97316; font-weight: bold; font-size: 18px;">{meal['calorien']:.0f} kcal</div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 15px; font-size: 14px; opacity: 0.7;">
                            <span>💪 {meal['eiwit']}g eiwit</span>
                            <span>🌾 {meal['koolhydraten']}g kh</span>
                            <span>🥑 {meal['vetten']}g vet</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Weekly trend
                st.markdown("### 📈 Voeding Trend (Laatste 7 dagen)")
                
                # Group by date
                if 'datum' in nutrition_df.columns:
                    daily_totals = nutrition_df.groupby('datum').agg({
                        'calorien': 'sum',
                        'eiwit': 'sum',
                        'koolhydraten': 'sum',
                        'vetten': 'sum'
                    }).reset_index()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=daily_totals['datum'], y=daily_totals['calorien'], name='Calorieën'))
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'title': "Dagelijkse Calorie-inname",
                        'xaxis_title': "Datum",
                        'yaxis_title': "Calorieën"
                    })
                    fig.update_layout(**layout)
                    st.plotly_chart(fig, key="chart_line_2081", use_container_width=True, config={"displayModeBar": False})
            else:
                st.info(f"Geen voeding data voor {period_label}")
        else:
            st.warning("Geen voeding data beschikbaar")
    
    # TAB 3: CARDIO
    with tab3:
        st.header("❤️ Cardio Activiteiten")
        
        activities_df = data.get('activiteiten', pd.DataFrame())
        
        if not activities_df.empty:
            # Filter by selected date range
            period_activities = filter_by_date_range(activities_df, start_date, end_date)
            
            # Case-insensitive filtering for cardio
            cardio = period_activities[period_activities['type'].str.lower() == 'cardio']
            
            # Calculate week-over-week comparison for cardio
            prev_week_start = start_date - timedelta(days=7)
            prev_week_end = end_date - timedelta(days=7)
            prev_week_activities = filter_by_date_range(activities_df, prev_week_start, prev_week_end)
            prev_week_cardio = prev_week_activities[prev_week_activities['type'].str.lower() == 'cardio']
            
            if not cardio.empty:
                # Calculate calories for cardio activities
                cardio_with_cals = cardio.copy()
                cardio_with_cals['Calorieën Verbrand'] = cardio_with_cals.apply(
                    lambda row: estimate_calories_burned(
                        row.get('type', ''),
                        row.get('activiteit', ''),
                        row.get('afstand', ''),
                        row.get('duur', '')
                    ),
                    axis=1
                )
                
                # Display cardio activities with calories
                display_cardio = cardio_with_cals[['datum', 'activiteit', 'afstand', 'duur', 'Calorieën Verbrand']].copy()
                display_cardio.columns = ['Datum', 'Activiteit', 'Afstand (km)', 'Duur', 'Calorieën Verbrand']
                
                # Format calories
                display_cardio['Calorieën Verbrand'] = display_cardio['Calorieën Verbrand'].apply(lambda x: f"{x:.0f} kcal")
                
                st.markdown(render_dataframe_html(display_cardio), unsafe_allow_html=True)
                
                # Calculate comparisons
                sessions_change = len(cardio) - len(prev_week_cardio)
                sessions_arrow = "↑" if sessions_change > 0 else "↓" if sessions_change < 0 else "→"
                sessions_badge_bg = "rgba(34, 197, 94, 0.2)" if sessions_change > 0 else "rgba(239, 68, 68, 0.2)" if sessions_change < 0 else "rgba(148, 163, 184, 0.2)"
                sessions_badge_border = "rgba(34, 197, 94, 0.4)" if sessions_change > 0 else "rgba(239, 68, 68, 0.4)" if sessions_change < 0 else "rgba(148, 163, 184, 0.4)"
                sessions_color = "#4ade80" if sessions_change > 0 else "#f87171" if sessions_change < 0 else "#94a3b8"
                
                # Helper function for parsing distance
                def parse_distance(val):
                    if pd.isna(val) or val == '':
                        return 0
                    try:
                        return float(str(val).replace(',', '.'))
                    except:
                        return 0
                
                # Calculate distance comparison
                total_distance = cardio['afstand'].apply(parse_distance).sum() if 'afstand' in cardio.columns else 0
                prev_week_distance = prev_week_cardio['afstand'].apply(parse_distance).sum() if 'afstand' in prev_week_cardio.columns and not prev_week_cardio.empty else 0
                
                distance_change = 0
                distance_change_pct = 0
                if prev_week_distance > 0:
                    distance_change = total_distance - prev_week_distance
                    distance_change_pct = (distance_change / prev_week_distance) * 100
                
                distance_arrow = "↑" if distance_change > 0 else "↓" if distance_change < 0 else "→"
                distance_badge_bg = "rgba(34, 197, 94, 0.2)" if distance_change > 0 else "rgba(239, 68, 68, 0.2)" if distance_change < 0 else "rgba(148, 163, 184, 0.2)"
                distance_badge_border = "rgba(34, 197, 94, 0.4)" if distance_change > 0 else "rgba(239, 68, 68, 0.4)" if distance_change < 0 else "rgba(148, 163, 184, 0.4)"
                distance_color = "#4ade80" if distance_change > 0 else "#f87171" if distance_change < 0 else "#94a3b8"
                
                # Summary with glassmorphism styling and comparisons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(236, 72, 153, 0.2), rgba(251, 113, 133, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(236, 72, 153, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🏃 Sessies</div>
                        <div style="font-size: 30px; font-weight: bold; color: #f472b6; margin: 12px 0;">{len(cardio)}</div>
                        <div style="display: inline-block; background: {sessions_badge_bg}; border: 1px solid {sessions_badge_border}; 
                                    padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; color: {sessions_color}; margin-top: 8px;">
                            {sessions_arrow} {sessions_change:+d} vs vorige week
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    comparison_badge = f"""<div style="display: inline-block; background: {distance_badge_bg}; border: 1px solid {distance_badge_border}; 
                                                    padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; color: {distance_color};">
                                                {distance_arrow} {distance_change_pct:+.0f}% vs vorige week
                                            </div>""" if prev_week_distance > 0 else '<div style="min-height: 28px;"></div>'
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(96, 165, 250, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">📏 Afstand</div>
                        <div style="font-size: 30px; font-weight: bold; color: #60a5fa; margin: 12px 0;">{total_distance:.1f}<span style="font-size: 16px; opacity: 0.7;"> km</span></div>
                        {comparison_badge}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    total_cardio_cals = cardio_with_cals['Calorieën Verbrand'].sum()
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(251, 146, 60, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🔥 Calorieën</div>
                        <div style="font-size: 30px; font-weight: bold; color: #fb923c; margin: 12px 0;">{total_cardio_cals:.0f}<span style="font-size: 16px; opacity: 0.7;"> kcal</span></div>
                        <div style="min-height: 18px;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                        # Calculate stats
                # Performance Analysis
                st.markdown("### 📊 Prestatie Analyse")
                
                # Calculate speed/pace for each session
                cardio_analysis = []
                for _, row in cardio.iterrows():
                    # Parse distance
                    try:
                        distance = float(str(row['afstand']).replace(',', '.')) if pd.notna(row['afstand']) and row['afstand'] != '' else 0
                    except:
                        distance = 0
                    
                    # Parse duration
                    duration_minutes = 0
                    if pd.notna(row['duur']) and row['duur'] != '':
                        try:
                            time_parts = str(row['duur']).split(':')
                            if len(time_parts) == 3:
                                duration_minutes = int(time_parts[0]) * 60 + int(time_parts[1]) + int(time_parts[2])/60
                            elif len(time_parts) == 2:
                                duration_minutes = int(time_parts[0]) + int(time_parts[1])/60
                        except:
                            duration_minutes = 0
                    
                    if distance > 0 and duration_minutes > 0:
                        speed = (distance / duration_minutes) * 60  # km/h
                        pace = duration_minutes / distance  # min/km
                        
                        cardio_analysis.append({
                            'datum': row['datum'],
                            'activiteit': row['activiteit'],
                            'afstand': distance,
                            'duur_min': duration_minutes,
                            'snelheid': speed,
                            'tempo': pace
                        })
                
                if cardio_analysis:
                    analysis_df = pd.DataFrame(cardio_analysis)
                    
                    # Convert datum to datetime for proper formatting
                    analysis_df['date_obj'] = pd.to_datetime(analysis_df['datum'], dayfirst=True, errors='coerce')
                    
                    # Group by activity type
                    for activity_type in analysis_df['activiteit'].unique():
                        activity_data = analysis_df[analysis_df['activiteit'] == activity_type].copy()
                        
                        if len(activity_data) > 0:
                            avg_speed = activity_data['snelheid'].mean()
                            avg_distance = activity_data['afstand'].mean()
                            best_speed = activity_data['snelheid'].max()
                            best_session = activity_data[activity_data['snelheid'] == best_speed].iloc[0]
                            
                            # Determine if improving
                            if len(activity_data) >= 2:
                                recent_avg = activity_data.tail(3)['snelheid'].mean()
                                older_avg = activity_data.head(3)['snelheid'].mean()
                                trend = "📈" if recent_avg > older_avg else "📉" if recent_avg < older_avg else "➡️"
                            else:
                                trend = "➡️"
                            
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2)); 
                                        padding: 18px; border-radius: 10px; border-left: 4px solid #10b981; margin-bottom: 15px;">
                                <h4 style="margin: 0 0 15px 0;">{trend} {activity_type}</h4>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                    <div>
                                        <div style="font-size: 12px; opacity: 0.8;">Gemiddelde Snelheid</div>
                                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">{avg_speed:.2f} km/h</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 12px; opacity: 0.8;">Gemiddelde Afstand</div>
                                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">{avg_distance:.2f} km</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 12px; opacity: 0.8;">Beste Prestatie</div>
                                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">{best_speed:.2f} km/h</div>
                                        <div style="font-size: 11px; opacity: 0.7;">op {best_session['datum']}</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 12px; opacity: 0.8;">Sessies</div>
                                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">{len(activity_data)}</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Trend chart for this activity
                            if len(activity_data) > 1:
                                # Sort by date
                                activity_data_sorted = activity_data.sort_values('date_obj')
                                
                                # Create Dutch date labels
                                date_labels = [format_date_nl(d) for d in activity_data_sorted['date_obj']]
                                
                                fig_trend = go.Figure()
                                fig_trend.add_trace(go.Scatter(
                                    x=activity_data_sorted['date_obj'],
                                    y=activity_data_sorted['snelheid'],
                                    mode='lines+markers',
                                    name='Snelheid',
                                    line=dict(color='#10b981', width=3),
                                    marker=dict(size=10),
                                    customdata=date_labels,
                                    hovertemplate='<b>%{customdata}</b><br>Snelheid: %{y:.2f} km/h<extra></extra>'
                                ))
                                fig_trend.add_trace(go.Scatter(
                                    x=activity_data_sorted['date_obj'],
                                    y=activity_data_sorted['afstand'],
                                    mode='lines+markers',
                                    name='Afstand',
                                    line=dict(color='#3b82f6', width=3),
                                    marker=dict(size=10),
                                    yaxis='y2',
                                    customdata=date_labels,
                                    hovertemplate='<b>%{customdata}</b><br>Afstand: %{y:.2f} km<extra></extra>'
                                ))
                                layout = get_chart_layout_defaults()
                                layout.update({
                                    'title': f"{activity_type} - Progressie",
                                    'xaxis_title': "",
                                    'yaxis_title': "Snelheid (km/h)",
                                    'yaxis2': dict(title="Afstand (km)", overlaying='y', side='right', gridcolor="rgba(255,255,255,0.1)"),
                                    'height': 350
                                })
                                fig_trend.update_layout(**layout)
                                st.plotly_chart(fig_trend, key=f"cardio_trend_{activity_type}", use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Geen cardio activiteiten gevonden")
                # Set empty cardio for stappen calculation below
                cardio = pd.DataFrame()
        else:
            st.warning("Geen activiteiten data beschikbaar")
            cardio = pd.DataFrame()
        
        # STAPPEN SECTIE - Always show, independent of cardio
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🚶 Dagelijkse Activiteit")
        
        stappen_df = data.get('stappen', pd.DataFrame())
        
        if not stappen_df.empty and 'datum' in stappen_df.columns:
            # Filter stappen for selected period
            period_stappen = filter_by_date_range(stappen_df, start_date, end_date)
            
            if not period_stappen.empty:
                # Calculate stats
                total_steps = period_stappen['stappen'].sum() if 'stappen' in period_stappen.columns else 0
                avg_steps = period_stappen['stappen'].mean() if 'stappen' in period_stappen.columns else 0
                
                # Calculate cardio steps to subtract (from walking activities)
                cardio_steps_total = 0
                if not cardio.empty and 'afstand' in cardio.columns:
                    # For each cardio walking session, estimate steps (1 km ≈ 1250 stappen)
                    for _, row in cardio.iterrows():
                        try:
                            distance = float(str(row['afstand']).replace(',', '.')) if pd.notna(row['afstand']) and row['afstand'] != '' else 0
                            # Convert km to steps (average: 1250 steps per km)
                            cardio_steps_total += distance * 1250
                        except:
                            pass
                
                # Split by cardio yes/no
                if 'cardio' in period_stappen.columns:
                    # Normalize cardio column (handle ja/yes/nee/no)
                    period_stappen['cardio_normalized'] = period_stappen['cardio'].astype(str).str.lower().str.strip()
                    
                    non_cardio_days = period_stappen[period_stappen['cardio_normalized'].isin(['nee', 'no', 'n'])]
                    cardio_days = period_stappen[period_stappen['cardio_normalized'].isin(['ja', 'yes', 'j'])]
                    
                    # For non-cardio days: just use the steps as-is
                    non_cardio_steps = non_cardio_days['stappen'].sum() if not non_cardio_days.empty else 0
                    
                    # For cardio days: subtract estimated cardio walking steps from total
                    cardio_day_steps = cardio_days['stappen'].sum() if not cardio_days.empty else 0
                    cardio_day_steps_adjusted = max(0, cardio_day_steps - cardio_steps_total)
                    
                    # Combined: non-cardio days + adjusted cardio days
                    non_cardio_steps_combined = non_cardio_steps + cardio_day_steps_adjusted
                    
                    # Average per day
                    total_days = len(period_stappen)
                    avg_non_cardio = non_cardio_steps_combined / total_days if total_days > 0 else 0
                else:
                    non_cardio_days = period_stappen
                    non_cardio_steps_combined = total_steps
                    avg_non_cardio = avg_steps
                
                # Calculate distances and calories more accurately
                # Non-cardio steps to km (average: 0.0008 km per step = 1250 steps/km)
                non_cardio_distance = non_cardio_steps_combined * 0.0008
                
                # Calories: 0.04 kcal per step for non-cardio steps only (cardio already counted)
                non_cardio_calories = non_cardio_steps_combined * 0.04
                
                # Total steps calories (for display)
                steps_calories = total_steps * 0.04
                
                # Display cards
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(74, 222, 128, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(34, 197, 94, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">👣 Totaal Stappen</div>
                        <div style="font-size: 30px; font-weight: bold; color: #4ade80; margin: 12px 0;">{total_steps:,.0f}</div>
                        <div style="font-size: 12px; opacity: 0.7;">~{steps_calories:.0f} kcal verbrand</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(96, 165, 250, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">📊 Gemiddeld/Dag</div>
                        <div style="font-size: 30px; font-weight: bold; color: #60a5fa; margin: 12px 0;">{avg_steps:,.0f}</div>
                        <div style="font-size: 12px; opacity: 0.7;">{len(period_stappen)} dagen getracked</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(192, 132, 252, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(168, 85, 247, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🚶 Excl. Cardio</div>
                        <div style="font-size: 30px; font-weight: bold; color: #c084fc; margin: 12px 0;">{non_cardio_steps_combined:,.0f}</div>
                        <div style="font-size: 12px; opacity: 0.7;">Ø {avg_non_cardio:,.0f}/dag</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    # Goal progress (10,000 steps/day is common goal)
                    goal_steps = 10000
                    goal_progress = (avg_steps / goal_steps * 100) if goal_steps > 0 else 0
                    goal_color = "#4ade80" if goal_progress >= 100 else "#fb923c" if goal_progress >= 70 else "#f87171"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(251, 146, 60, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🎯 Doel Progressie</div>
                        <div style="font-size: 30px; font-weight: bold; color: {goal_color}; margin: 12px 0;">{goal_progress:.0f}%</div>
                        <div style="font-size: 12px; opacity: 0.7;">Doel: {goal_steps:,} stappen/dag</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Stappen details en grafieken
                col_left, col_right = st.columns([2, 1])
                
                with col_left:
                    st.markdown("#### 📈 Stappen Trend")
                    
                    # Create daily breakdown with cardio indication
                    daily_breakdown = []
                    for _, row in period_stappen.iterrows():
                        datum = row['datum']
                        stappen = row['stappen'] if 'stappen' in row and pd.notna(row['stappen']) else 0
                        is_cardio = row.get('cardio_normalized', 'nee') in ['ja', 'yes', 'j']
                        
                        # Find matching cardio distance for this date
                        cardio_dist = 0
                        if is_cardio and not cardio.empty:
                            matching_cardio = cardio[cardio['datum'] == datum]
                            if not matching_cardio.empty and 'afstand' in matching_cardio.columns:
                                for _, c_row in matching_cardio.iterrows():
                                    try:
                                        dist = float(str(c_row['afstand']).replace(',', '.')) if pd.notna(c_row['afstand']) and c_row['afstand'] != '' else 0
                                        cardio_dist += dist
                                    except:
                                        pass
                        
                        # Calculate splits
                        cardio_steps_est = cardio_dist * 1250
                        background_steps = max(0, stappen - cardio_steps_est)
                        
                        daily_breakdown.append({
                            'datum': datum,
                            'Achtergrond': background_steps,
                            'Cardio Training': cardio_steps_est,
                            'Totaal': stappen
                        })
                    
                    breakdown_df = pd.DataFrame(daily_breakdown)
                    
                    # Stacked bar chart
                    fig = go.Figure()
                    
                    # Background steps (purple)
                    fig.add_trace(go.Bar(
                        x=breakdown_df['datum'],
                        y=breakdown_df['Achtergrond'],
                        name='Achtergrond activiteit',
                        marker=dict(color='rgba(168, 85, 247, 0.8)'),
                        hovertemplate='<b>%{x}</b><br>Achtergrond: %{y:,.0f} stappen<extra></extra>'
                    ))
                    
                    # Cardio steps (green)
                    fig.add_trace(go.Bar(
                        x=breakdown_df['datum'],
                        y=breakdown_df['Cardio Training'],
                        name='Cardio training',
                        marker=dict(color='rgba(34, 197, 94, 0.8)'),
                        hovertemplate='<b>%{x}</b><br>Cardio: %{y:,.0f} stappen<extra></extra>'
                    ))
                    
                    # Add 10k goal line
                    fig.add_hline(
                        y=10000,
                        line_dash="dash",
                        line_color="rgba(251, 146, 60, 0.6)",
                        annotation_text="Doel: 10.000",
                        annotation_position="right"
                    )
                    
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'barmode': 'stack',
                        'title': 'Dagelijkse Stappen Breakdown',
                        'xaxis_title': 'Datum',
                        'yaxis_title': 'Stappen',
                        'showlegend': True,
                        'legend': dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    })
                    fig.update_layout(**layout)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="stappen_breakdown_chart")
                
                with col_right:
                    st.markdown("#### 💡 Inzichten")
                    
                    # Insights box
                    avg_goal_pct = (avg_non_cardio / 10000) * 100
                    
                    if avg_non_cardio >= 10000:
                        insight_color = "rgba(34, 197, 94, 0.2)"
                        insight_border = "rgba(34, 197, 94, 0.4)"
                        insight_icon = "🎉"
                        insight_text = f"Geweldig! Je achtergrond activiteit zit gemiddeld op <b>{avg_non_cardio:,.0f}</b> stappen per dag, boven het doel!"
                    elif avg_non_cardio >= 7000:
                        insight_color = "rgba(59, 130, 246, 0.2)"
                        insight_border = "rgba(59, 130, 246, 0.4)"
                        insight_icon = "👍"
                        insight_text = f"Goed bezig! Je zit op <b>{avg_non_cardio:,.0f}</b> stappen/dag. Nog <b>{10000 - avg_non_cardio:,.0f}</b> stappen naar je doel."
                    else:
                        insight_color = "rgba(249, 115, 22, 0.2)"
                        insight_border = "rgba(249, 115, 22, 0.4)"
                        insight_icon = "💪"
                        insight_text = f"Focus op beweging! Je zit op <b>{avg_non_cardio:,.0f}</b> stappen/dag. Probeer meer te lopen tussen trainingen door."
                    
                    st.markdown(f"""
                    <div style="background: {insight_color}; padding: 18px; border-radius: 12px; 
                                border-left: 4px solid {insight_border}; margin-bottom: 15px;">
                        <div style="font-size: 30px; margin-bottom: 10px;">{insight_icon}</div>
                        <div style="font-size: 14px; line-height: 1.6;">{insight_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Stats breakdown
                    st.markdown(f"""
                    <div style="background: rgba(139, 92, 246, 0.15); padding: 15px; border-radius: 10px;">
                        <div style="font-size: 13px; font-weight: 600; margin-bottom: 12px; opacity: 0.9;">📊 Statistieken</div>
                        <div style="font-size: 12px; line-height: 2;">
                            <div style="display: flex; justify-content: space-between;">
                                <span>🚶 Achtergrond afstand:</span>
                                <span style="font-weight: 600;">{non_cardio_distance:.1f} km</span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span>🔥 Extra calorieën:</span>
                                <span style="font-weight: 600;">{non_cardio_calories:.0f} kcal</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2);">
                                <span>📅 Dagen met cardio:</span>
                                <span style="font-weight: 600;">{len(cardio_days) if 'cardio' in period_stappen.columns else 0}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span>📅 Dagen zonder cardio:</span>
                                <span style="font-weight: 600;">{len(non_cardio_days) if 'cardio' in period_stappen.columns else len(period_stappen)}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.info(f"Geen stappen data voor {period_label}")
        else:
            st.info("Geen stappen data beschikbaar")
    
    # TAB 4: KRACHT
    with tab4:
        st.header("💪 Kracht Training Analytics")
        
        if not activities_df.empty:
            # Filter by selected date range
            period_activities = filter_by_date_range(activities_df, start_date, end_date)
            
            # Case-insensitive filtering for strength
            strength = period_activities[period_activities['type'].str.lower() == 'kracht']
            
            if not strength.empty:
                # Calculate calories and volume
                strength_cals_total, strength_with_cals = calculate_total_calories_burned(strength)
                
                # Calculate week-over-week comparison
                prev_week_start = start_date - timedelta(days=7)
                prev_week_end = end_date - timedelta(days=7)
                prev_week_activities = filter_by_date_range(activities_df, prev_week_start, prev_week_end)
                prev_week_strength = prev_week_activities[prev_week_activities['type'].str.lower() == 'kracht']
                
                # Calculate total volume and find PRs
                total_volume = 0
                prev_week_volume = 0
                exercise_stats = {}
                
                # Calculate previous week volume
                for _, row in prev_week_strength.iterrows():
                    try:
                        weight = float(str(row.get("gewicht", 0)).replace(",", ".")) if pd.notna(row.get("gewicht")) else 0
                        sets = int(row.get("sets", 0)) if pd.notna(row.get("sets")) else 0
                        reps = int(row.get("reps", 0)) if pd.notna(row.get("reps")) else 0
                        prev_week_volume += weight * sets * reps
                    except:
                        pass
                
                # Calculate current week
                for _, row in strength.iterrows():
                    try:
                        exercise = row.get('activiteit', 'Unknown')
                        weight = float(str(row.get("gewicht", 0)).replace(",", ".")) if pd.notna(row.get("gewicht")) else 0
                        sets = int(row.get("sets", 0)) if pd.notna(row.get("sets")) else 0
                        reps = int(row.get("reps", 0)) if pd.notna(row.get("reps")) else 0
                        volume = weight * sets * reps
                        total_volume += volume
                        
                        # Track per exercise
                        if exercise not in exercise_stats:
                            exercise_stats[exercise] = {
                                'max_weight': weight,
                                'total_volume': 0,
                                'count': 0,
                                'dates': []
                            }
                        
                        exercise_stats[exercise]['max_weight'] = max(exercise_stats[exercise]['max_weight'], weight)
                        exercise_stats[exercise]['total_volume'] += volume
                        exercise_stats[exercise]['count'] += 1
                        exercise_stats[exercise]['dates'].append(row.get('datum'))
                    except:
                        pass
                
                # Calculate comparison
                volume_change = 0
                volume_change_pct = 0
                if prev_week_volume > 0:
                    volume_change = total_volume - prev_week_volume
                    volume_change_pct = (volume_change / prev_week_volume) * 100
                
                volume_arrow = "↑" if volume_change > 0 else "↓" if volume_change < 0 else "→"
                volume_badge_bg = "rgba(34, 197, 94, 0.2)" if volume_change > 0 else "rgba(239, 68, 68, 0.2)" if volume_change < 0 else "rgba(148, 163, 184, 0.2)"
                volume_badge_border = "rgba(34, 197, 94, 0.4)" if volume_change > 0 else "rgba(239, 68, 68, 0.4)" if volume_change < 0 else "rgba(148, 163, 184, 0.4)"
                volume_color = "#4ade80" if volume_change > 0 else "#f87171" if volume_change < 0 else "#94a3b8"
                
                sessions_change = len(strength) - len(prev_week_strength)
                sessions_arrow = "↑" if sessions_change > 0 else "↓" if sessions_change < 0 else "→"
                sessions_badge_bg = "rgba(34, 197, 94, 0.2)" if sessions_change > 0 else "rgba(239, 68, 68, 0.2)" if sessions_change < 0 else "rgba(148, 163, 184, 0.2)"
                sessions_badge_border = "rgba(34, 197, 94, 0.4)" if sessions_change > 0 else "rgba(239, 68, 68, 0.4)" if sessions_change < 0 else "rgba(148, 163, 184, 0.4)"
                sessions_color = "#4ade80" if sessions_change > 0 else "#f87171" if sessions_change < 0 else "#94a3b8"
                
                # Summary metrics with better styling
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(167, 139, 250, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">💪 Oefeningen</div>
                        <div style="font-size: 30px; font-weight: bold; color: #a78bfa; margin: 12px 0;">{len(strength)}</div>
                        <div style="display: inline-block; background: {sessions_badge_bg}; border: 1px solid {sessions_badge_border}; 
                                    padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; color: {sessions_color}; margin-top: 8px;">
                            {sessions_arrow} {sessions_change:+d} vs vorige week
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    comparison_badge = f"""<div style="display: inline-block; background: {volume_badge_bg}; border: 1px solid {volume_badge_border}; 
                                                    padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; color: {volume_color};">
                                                {volume_arrow} {volume_change_pct:+.0f}% vs vorige week
                                            </div>""" if prev_week_volume > 0 else '<div style="min-height: 28px;"></div>'
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(96, 165, 250, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🏋️ Volume</div>
                        <div style="font-size: 30px; font-weight: bold; color: #60a5fa; margin: 12px 0;">{total_volume:.0f}<span style="font-size: 16px; opacity: 0.7;"> kg</span></div>
                        {comparison_badge}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(251, 146, 60, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🔥 Calorieën</div>
                        <div style="font-size: 30px; font-weight: bold; color: #fb923c; margin: 12px 0;">{strength_cals_total:.0f}<span style="font-size: 16px; opacity: 0.7;"> kcal</span></div>
                        <div style="min-height: 18px;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    unique_exercises = len(exercise_stats)
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(74, 222, 128, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(34, 197, 94, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">🎯 Variatie</div>
                        <div style="font-size: 30px; font-weight: bold; color: #4ade80; margin: 12px 0;">{unique_exercises}</div>
                        <div style="min-height: 18px;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Volume progression chart
                if len(strength) > 1:
                    st.markdown("### 📈 Volume Progressie")
                    
                    # Calculate daily volume
                    daily_volume = {}
                    for _, row in strength.iterrows():
                        try:
                            date = row.get('datum')
                            weight = float(str(row.get("gewicht", 0)).replace(",", ".")) if pd.notna(row.get("gewicht")) else 0
                            sets = int(row.get("sets", 0)) if pd.notna(row.get("sets")) else 0
                            reps = int(row.get("reps", 0)) if pd.notna(row.get("reps")) else 0
                            volume = weight * sets * reps
                            
                            if date not in daily_volume:
                                daily_volume[date] = 0
                            daily_volume[date] += volume
                        except:
                            pass
                    
                    if daily_volume:
                        dates = sorted(daily_volume.keys())
                        volumes = [daily_volume[d] for d in dates]
                        
                        fig_volume = go.Figure()
                        fig_volume.add_trace(go.Bar(
                            x=dates,
                            y=volumes,
                            name='Volume',
                            marker_color='#8b5cf6',
                            hovertemplate='<b>%{x}</b><br>Volume: %{y:.0f} kg<extra></extra>'
                        ))
                        
                        layout = get_chart_layout_defaults()
                        layout.update({
                            'title': 'Totaal Volume per Training',
                            'xaxis_title': 'Datum',
                            'yaxis_title': 'Volume (kg)',
                            'height': 300
                        })
                        fig_volume.update_layout(**layout)
                        st.plotly_chart(fig_volume, key="kracht_volume", use_container_width=True, config={"displayModeBar": False})
                
                # Top exercises by volume
                st.markdown("### 🏆 Top Oefeningen")
                
                col_left, col_right = st.columns(2)
                
                with col_left:
                    # Sort by total volume
                    top_exercises = sorted(exercise_stats.items(), key=lambda x: x[1]['total_volume'], reverse=True)[:5]
                    
                    st.markdown("**💎 Meeste Volume**")
                    for exercise, stats in top_exercises:
                        percentage = (stats['total_volume'] / total_volume * 100) if total_volume > 0 else 0
                        st.markdown(f"""
                        <div style="background: rgba(139, 92, 246, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 5px;
                                    border-left: 3px solid #8b5cf6;">
                            <div style="font-weight: 600; margin-bottom: 4px;">{exercise}</div>
                            <div style="font-size: 13px; opacity: 0.8;">
                                {stats['total_volume']:.0f} kg ({percentage:.0f}%) • {stats['count']}x gedaan
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col_right:
                    # Sort by max weight (PRs)
                    top_prs = sorted(exercise_stats.items(), key=lambda x: x[1]['max_weight'], reverse=True)[:5]
                    
                    st.markdown("**� Personal Records**")
                    for exercise, stats in top_prs:
                        if stats['max_weight'] > 0:
                            st.markdown(f"""
                            <div style="background: rgba(249, 115, 22, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 5px;
                                        border-left: 3px solid #f97316;">
                                <div style="font-weight: 600; margin-bottom: 4px;">{exercise}</div>
                                <div style="font-size: 13px; opacity: 0.8;">
                                    PR: {stats['max_weight']:.0f} kg
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Full table
                st.markdown("### 📋 Alle Trainingen")
                
                display_df = strength[['datum', 'activiteit', 'gewicht', 'sets', 'reps', 'methode']].copy()
                
                if 'sets' in display_df.columns and 'reps' in display_df.columns:
                    display_df['Sets × Reps'] = display_df.apply(
                        lambda row: f"{int(row['sets'])} × {int(row['reps'])}" if pd.notna(row['sets']) and pd.notna(row['reps']) else '', 
                        axis=1
                    )
                
                display_subset = display_df[['datum', 'activiteit', 'gewicht', 'Sets × Reps', 'methode']].copy()
                display_subset.columns = ['Datum', 'Oefening', 'Gewicht (kg)', 'Volume', 'Methode']
                display_subset['Gewicht (kg)'] = display_subset['Gewicht (kg)'].apply(lambda x: f"{x:.0f} kg" if pd.notna(x) else '')
                
                st.markdown(render_dataframe_html(display_subset), unsafe_allow_html=True)
                
            else:
                st.info("Geen kracht training gevonden in deze periode")
        else:
            st.warning("Geen activiteiten data beschikbaar")
    
    # TAB 5: PROGRESSIE
    with tab5:
        st.header("📈 Progressie & metingen")
        
        # Get all relevant data
        metingen_df = data.get('metingen', pd.DataFrame())
        gewicht_df = data.get('gewicht', pd.DataFrame())
        
        # HERO DASHBOARD: "Waar sta ik NU?"
        st.markdown("### 🎯 Waar sta ik nu?")
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        
        if not metingen_df.empty or not gewicht_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            # Get latest weight from daily tracking (most recent)
            current_weight = None
            week_weight_change = 0
            if not gewicht_df.empty and 'datum' in gewicht_df.columns and 'gewicht' in gewicht_df.columns:
                gewicht_daily = gewicht_df.copy()
                gewicht_daily['date_obj'] = pd.to_datetime(gewicht_daily['datum'], dayfirst=True, errors='coerce')
                gewicht_daily = gewicht_daily.dropna(subset=['date_obj', 'gewicht'])
                gewicht_daily = gewicht_daily.sort_values('date_obj')
                
                if len(gewicht_daily) > 0:
                    current_weight = float(gewicht_daily.iloc[-1]['gewicht'])
                    
                    # Calculate week-over-week change
                    week_ago = gewicht_daily.iloc[-1]['date_obj'] - pd.Timedelta(days=7)
                    week_ago_data = gewicht_daily[gewicht_daily['date_obj'] <= week_ago]
                    if len(week_ago_data) > 0:
                        week_ago_weight = float(week_ago_data.iloc[-1]['gewicht'])
                        week_weight_change = current_weight - week_ago_weight
            
            # Get vet % and Spiermassa from official measurements
            current_fat = None
            current_muscle = None
            week_fat_change = 0
            week_muscle_change = 0
            
            if not metingen_df.empty:
                date_cols = [col for col in metingen_df.columns if col != 'categorie']
                if date_cols:
                    latest_date = date_cols[-1]
                    
                    vet_pct = metingen_df[metingen_df['categorie'] == 'Vet %']
                    spier = metingen_df[metingen_df['categorie'] == 'Skeletspiermassa']
                    
                    if not vet_pct.empty:
                        current_fat = float(vet_pct[latest_date].values[0])
                    if not spier.empty:
                        current_muscle = float(spier[latest_date].values[0])
            
            # CARD 1: Current Weight (with week-over-week)
            with col1:
                if current_weight:
                    change_icon = "📉" if week_weight_change < 0 else "📈" if week_weight_change > 0 else "→"
                    change_color = "#22c55e" if week_weight_change < 0 else "#ef4444" if week_weight_change > 0 else "#94a3b8"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(79, 70, 229, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(99, 102, 241, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center;">
                        <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">📊 Huidig Gewicht</div>
                        <div style="font-size: 30px; font-weight: bold; color: #818cf8; margin-bottom: 5px;">{current_weight:.1f} kg</div>
                        <div style="font-size: 11px; color: {change_color}; font-weight: bold;">
                            {change_icon} {week_weight_change:+.1f} kg
                        </div>
                        <div style="font-size: 9px; opacity: 0.6; margin-top: 2px;">week-over-week</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # CARD 2: Vet % (with week-over-week from projections)
            with col2:
                if current_fat:
                    change_icon = "📉" if week_fat_change < 0 else "📈" if week_fat_change > 0 else "→"
                    change_color = "#22c55e" if week_fat_change < 0 else "#ef4444" if week_fat_change > 0 else "#94a3b8"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(217, 119, 6, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(245, 158, 11, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center;">
                        <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">📉 Vet %</div>
                        <div style="font-size: 30px; font-weight: bold; color: #fbbf24; margin-bottom: 5px;">{current_fat:.1f}%</div>
                        <div style="font-size: 11px; color: {change_color}; font-weight: bold;">
                            {change_icon} {week_fat_change:+.1f}%
                        </div>
                        <div style="font-size: 9px; opacity: 0.6; margin-top: 2px;">gemiddelde trend</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # CARD 3: Spiermassa (with week-over-week from projections)
            with col3:
                if current_muscle:
                    change_icon = "📈" if week_muscle_change > 0 else "📉" if week_muscle_change < 0 else "→"
                    change_color = "#22c55e" if week_muscle_change > 0 else "#ef4444" if week_muscle_change < 0 else "#94a3b8"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(34, 197, 94, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center;">
                        <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">💪 Spiermassa</div>
                        <div style="font-size: 30px; font-weight: bold; color: #4ade80; margin-bottom: 5px;">{current_muscle:.1f} kg</div>
                        <div style="font-size: 11px; color: {change_color}; font-weight: bold;">
                            {change_icon} {week_muscle_change:+.1f} kg
                        </div>
                        <div style="font-size: 9px; opacity: 0.6; margin-top: 2px;">gemiddelde trend</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # CARD 4: Progress to Goal
            with col4:
                if current_weight and 'weight' in st.session_state.targets:
                    target_weight = st.session_state.targets['weight']
                    weight_to_go = current_weight - target_weight
                    progress_pct = min(100, max(0, (1 - (weight_to_go / 20)) * 100))  # Assuming ~20kg total to lose
                    
                    status_icon = "🎯" if weight_to_go > 0 else "✅"
                    status_text = "te gaan" if weight_to_go > 0 else "bereikt!"
                    status_color = "#fbbf24" if weight_to_go > 0 else "#22c55e"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(167, 139, 250, 0.1)); 
                                padding: 18px; border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.3);
                                text-align: center; height: 160px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center;">
                        <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">{status_icon} Target Voortgang</div>
                        <div style="font-size: 30px; font-weight: bold; color: {status_color}; margin-bottom: 5px;">{abs(weight_to_go):.1f} kg</div>
                        <div style="font-size: 11px; font-weight: bold; color: {status_color};">
                            {status_text}
                        </div>
                        <div style="font-size: 9px; opacity: 0.6; margin-top: 2px;">doel: {target_weight:.0f} kg</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
        
        # COMBINED TIMELINE: "Waar GA ik heen?"
        st.markdown("### 🎯 Waar ga ik heen?")
        st.markdown("<p style='font-size: 13px; opacity: 0.7; margin-top: -10px;'>Combinatie van dagelijkse wegingen, officiële metingen en 4-weken projectie</p>", unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        
        if not metingen_df.empty:
            projections = calculate_body_projections(metingen_df, weeks_ahead=4)
            
            if projections and 'error' not in projections:
                # Create projection visualization
                hist = projections['historical']
                proj = projections['projections']
                summary = projections['summary']
                regression = projections['regression']
                
                # Three columns for insight cards
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    gewicht_icon = "📉" if summary['gewicht_change'] < 0 else "📈"
                    gewicht_color = "#22c55e" if summary['gewicht_change'] < 0 else "#ef4444"
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(79, 70, 229, 0.2)); 
                                padding: 18px; border-radius: 10px; border-left: 4px solid #6366f1;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">{gewicht_icon} Gewicht Projectie</div>
                        <div style="font-size: 28px; font-weight: bold; margin-bottom: 10px;">
                            {summary['projected_gewicht']:.1f} kg
                        </div>
                        <div style="font-size: 16px; color: {gewicht_color}; font-weight: bold;">
                            {summary['gewicht_change']:+.1f} kg
                        </div>
                        <div style="font-size: 12px; opacity: 0.7; margin-top: 5px;">
                            over {summary['weeks_ahead']} weken
                        </div>
                        <div style="font-size: 11px; opacity: 0.6; margin-top: 8px;">
                            Betrouwbaarheid: {regression['gewicht']['r_squared']:.1%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    vet_icon = "📉" if summary['vet_change'] < 0 else "📈"
                    vet_color = "#22c55e" if summary['vet_change'] < 0 else "#ef4444"
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(217, 119, 6, 0.2)); 
                                padding: 18px; border-radius: 10px; border-left: 4px solid #f59e0b;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">{vet_icon} Vet % Projectie</div>
                        <div style="font-size: 28px; font-weight: bold; margin-bottom: 10px;">
                            {summary['projected_vet']:.1f}%
                        </div>
                        <div style="font-size: 16px; color: {vet_color}; font-weight: bold;">
                            {summary['vet_change']:+.1f}%
                        </div>
                        <div style="font-size: 12px; opacity: 0.7; margin-top: 5px;">
                            over {summary['weeks_ahead']} weken
                        </div>
                        <div style="font-size: 11px; opacity: 0.6; margin-top: 8px;">
                            Betrouwbaarheid: {regression['vet_pct']['r_squared']:.1%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    spier_icon = "📈" if summary['spier_change'] > 0 else "📉"
                    spier_color = "#22c55e" if summary['spier_change'] > 0 else "#ef4444"
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.2)); 
                                padding: 18px; border-radius: 10px; border-left: 4px solid #22c55e;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">{spier_icon} Spiermassa Projectie</div>
                        <div style="font-size: 28px; font-weight: bold; margin-bottom: 10px;">
                            {summary['projected_spier']:.1f} kg
                        </div>
                        <div style="font-size: 16px; color: {spier_color}; font-weight: bold;">
                            {summary['spier_change']:+.1f} kg
                        </div>
                        <div style="font-size: 12px; opacity: 0.7; margin-top: 5px;">
                            over {summary['weeks_ahead']} weken
                        </div>
                        <div style="font-size: 11px; opacity: 0.6; margin-top: 8px;">
                            Betrouwbaarheid: {regression['spier']['r_squared']:.1%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Create projection charts
                st.markdown("#### 📊 Projectie Visualisaties")
                
                # Combine historical and projected data for charts
                all_dates = list(hist['dates']) + list(proj['dates'])
                
                # Weight projection chart
                fig_gewicht = go.Figure()
                
                # Combine all weight data into one unified line
                all_dates = []
                all_weights = []
                official_dates = []
                official_weights = []
                
                # Add daily weight data if available
                if not gewicht_df.empty and 'datum' in gewicht_df.columns and 'gewicht' in gewicht_df.columns:
                    gewicht_daily = gewicht_df.copy()
                    gewicht_daily['date_obj'] = pd.to_datetime(gewicht_daily['datum'], dayfirst=True, errors='coerce')
                    gewicht_daily = gewicht_daily.dropna(subset=['date_obj', 'gewicht'])
                    gewicht_daily = gewicht_daily.sort_values('date_obj')
                    
                    if len(gewicht_daily) > 0:
                        all_dates.extend(gewicht_daily['date_obj'].tolist())
                        all_weights.extend(gewicht_daily['gewicht'].astype(float).tolist())
                
                # Add official measurements to combined data AND track for markers
                for i, date in enumerate(hist['dates']):
                    all_dates.append(date)
                    all_weights.append(hist['gewicht'][i])
                    official_dates.append(date)
                    official_weights.append(hist['gewicht'][i])
                
                # Sort combined data by date
                if all_dates:
                    combined = sorted(zip(all_dates, all_weights))
                    all_dates, all_weights = zip(*combined)
                    
                    # Create Dutch date labels for hover
                    date_labels = [format_date_nl(d) for d in all_dates]
                    
                    # Main line: all weight data (daily + official combined)
                    fig_gewicht.add_trace(go.Scatter(
                        x=all_dates,
                        y=all_weights,
                        mode='lines+markers',
                        name='Gewicht',
                        line=dict(color='rgba(96, 165, 250, 0.8)', width=2.5),
                        marker=dict(size=5, color='rgba(96, 165, 250, 0.9)'),
                        customdata=date_labels,
                        hovertemplate='<b>%{customdata}</b><br>Gewicht: %{y:.1f} kg<extra></extra>'
                    ))
                    
                    # Overlay small markers for official measurements
                    if official_dates:
                        official_labels = [format_date_nl(d) for d in official_dates]
                        fig_gewicht.add_trace(go.Scatter(
                            x=official_dates,
                            y=official_weights,
                            mode='markers',
                            name='Officiële meting',
                            marker=dict(
                                size=10,
                                color='rgba(249, 115, 22, 0.9)',
                                symbol='star',
                                line=dict(color='rgba(249, 115, 22, 1)', width=1)
                            ),
                            customdata=official_labels,
                            hovertemplate='<b>%{customdata}</b><br>Officieel: %{y:.1f} kg<extra></extra>'
                        ))
                
                # Projection
                proj_labels = [format_date_nl(d) for d in proj['dates']]
                fig_gewicht.add_trace(go.Scatter(
                    x=[all_dates[-1]] + list(proj['dates']) if all_dates else list(proj['dates']),
                    y=[all_weights[-1]] + list(proj['gewicht']) if all_weights else list(proj['gewicht']),
                    mode='lines+markers',
                    name='Projectie (4 weken)',
                    line=dict(color='rgba(34, 197, 94, 0.7)', width=2.5, dash='dash'),
                    marker=dict(size=7, color='rgba(34, 197, 94, 0.9)', symbol='diamond'),
                    customdata=[date_labels[-1]] + proj_labels if all_dates else proj_labels,
                    hovertemplate='<b>%{customdata}</b><br>Projectie: %{y:.1f} kg<extra></extra>'
                ))
                
                # Target weight line (if set)
                if 'weight' in st.session_state.targets:
                    target_weight = st.session_state.targets['weight']
                    # Get date range for target line
                    all_dates_for_target = []
                    if all_dates:
                        all_dates_for_target.append(min(all_dates))
                    all_dates_for_target.append(proj['dates'][-1])
                    
                    fig_gewicht.add_trace(go.Scatter(
                        x=[min(all_dates_for_target), max(all_dates_for_target)],
                        y=[target_weight, target_weight],
                        mode='lines',
                        name=f'Target ({target_weight:.0f} kg)',
                        line=dict(color='rgba(239, 68, 68, 0.6)', width=2, dash='dot'),
                        hovertemplate=f'<b>Target</b><br>{target_weight:.1f} kg<extra></extra>'
                    ))
                
                layout = get_chart_layout_defaults()
                layout.update({
                    'title': "Gewicht progressie & target",
                    'xaxis_title': "",
                    'yaxis_title': "Gewicht (kg)",
                    'hovermode': "x unified",
                    'showlegend': True,
                    'legend': dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    'height': 450
                })
                fig_gewicht.update_layout(**layout)
                
                st.plotly_chart(fig_gewicht, key="progressie_gewicht", use_container_width=True, config={"displayModeBar": False})
                
                # SMART INSIGHTS BOX
                st.markdown("#### 💡 Slimme inzichten")
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
                insights = []
                
                # Calculate time to target with more detail
                if current_weight and 'weight' in st.session_state.targets:
                    target_weight = st.session_state.targets['weight']
                    weight_to_go = current_weight - target_weight
                    
                    if weight_to_go > 0:
                        if week_weight_change < 0:  # Losing weight (good!)
                            weeks_to_target = abs(weight_to_go / week_weight_change)
                            target_date = pd.Timestamp.now() + pd.Timedelta(weeks=weeks_to_target)
                            insights.append(f"✅ **Op koers naar je doel!** Nog {weight_to_go:.1f} kg te gaan tot {target_weight:.0f} kg. Bij dit tempo (-{abs(week_weight_change):.1f} kg/week) bereik je je target rond {format_date_nl(target_date)}.")
                        elif week_weight_change > 0:  # Gaining weight (bad)
                            insights.append(f"⚠️ **Waarschuwing**: Je gewicht stijgt momenteel (+{week_weight_change:.1f} kg/week). Je bent {weight_to_go:.1f} kg van je target ({target_weight:.0f} kg). Focus op calorie deficit!")
                        else:  # No change
                            insights.append(f"➡️ **Stabiel gewicht**: Je gewicht blijft gelijk. Nog {weight_to_go:.1f} kg te gaan tot {target_weight:.0f} kg. Verhoog je deficit om progressie te maken.")
                    else:
                        insights.append(f"🎉 **Gefeliciteerd!** Je hebt je doel van {target_weight:.0f} kg bereikt! Tijd voor een nieuwe uitdaging?")
                
                # Analyze body composition trend with more context
                if current_fat and current_muscle and len(date_cols) > 1:
                    prev_fat = float(vet_pct[date_cols[-2]].values[0]) if not vet_pct.empty else current_fat
                    prev_muscle = float(spier[date_cols[-2]].values[0]) if not spier.empty else current_muscle
                    fat_change = current_fat - prev_fat
                    muscle_change = current_muscle - prev_muscle
                    
                    if fat_change < -0.3 and muscle_change >= -0.1:
                        insights.append(f"💪 **Uitstekende recomp!** Je verliest vet ({fat_change:.1f}%) en behoudt spiermassa ({muscle_change:+.1f} kg). Blijf dit volhouden!")
                    elif fat_change < 0 and muscle_change < -0.3:
                        insights.append(f"⚠️ **Spierverlies gedetecteerd**: Vet daalt ({fat_change:.1f}%) maar je verliest ook spier ({muscle_change:.1f} kg). Verhoog je eiwitinname (2g per kg) en krachttrain 3-4x per week.")
                    elif fat_change >= 0 and muscle_change > 0.3:
                        insights.append(f"🏋️ **Bulking succesvol**: +{muscle_change:.1f} kg spier, {fat_change:+.1f}% vet. Goede muscle-to-fat ratio!")
                    elif fat_change > 0.5:
                        insights.append(f"📊 **Vet stijgt**: +{fat_change:.1f}% lichaamsvet. Check je calorie-inname en verhoog je cardio.")
                
                # Show projected weight with confidence
                if projections and 'error' not in projections and len(proj['gewicht']) > 0:
                    next_week_weight = proj['gewicht'][0]
                    next_week_date = proj['dates'][0]
                    weight_change_projected = next_week_weight - current_weight
                    change_text = f"{weight_change_projected:+.1f} kg" if weight_change_projected != 0 else "stabiel"
                    insights.append(f"🔮 **Projectie**: Verwacht gewicht op {format_date_nl(next_week_date)}: ~{next_week_weight:.1f} kg ({change_text}).")
                
                # Display insights
                if insights:
                    for insight in insights:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05)); 
                                    padding: 15px; border-radius: 8px; margin-bottom: 10px;
                                    border-left: 4px solid #3b82f6;">
                            {insight}
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # DETAIL SECTION: "Hoe kom ik daar?"
                st.markdown("### 📊 Hoe kom ik daar?")
                st.markdown("<p style='font-size: 13px; opacity: 0.7; margin-top: -10px;'>Gedetailleerde analyse van lichaamssamenstelling en krachtontwikkeling</p>", unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
                
                # Two columns: Body Composition Details | Kracht Ontwikkeling
                col_left, col_right = st.columns([1, 1])
                
                with col_left:
                    st.markdown("#### 📉 Lichaamssamenstelling")
                    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
                    
                    # Fat % projection chart
                    fig_vet = go.Figure()
                    
                    fig_vet.add_trace(go.Scatter(
                        x=hist['dates'], 
                        y=hist['vet_pct'],
                        mode='lines+markers',
                        name='Gemeten',
                        line=dict(color='#f59e0b', width=3),
                        marker=dict(size=8)
                    ))
                    
                    fig_vet.add_trace(go.Scatter(
                        x=[hist['dates'][-1]] + list(proj['dates']),
                        y=[hist['vet_pct'][-1]] + list(proj['vet_pct']),
                        mode='lines+markers',
                        name='Projectie',
                        line=dict(color='#fbbf24', width=2, dash='dash'),
                        marker=dict(size=6, symbol='diamond')
                    ))
                    
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'title': "Vetpercentage",
                        'xaxis_title': "",
                        'yaxis_title': "Vet %",
                        'hovermode': "x unified",
                        'showlegend': True,
                        'height': 300
                    })
                    fig_vet.update_layout(**layout)
                    
                    st.plotly_chart(fig_vet, key="progressie_vet", use_container_width=True, config={"displayModeBar": False})
                    
                    # Muscle mass projection chart
                    fig_spier = go.Figure()
                    
                    fig_spier.add_trace(go.Scatter(
                        x=hist['dates'], 
                        y=hist['spier'],
                        mode='lines+markers',
                        name='Gemeten',
                        line=dict(color='#22c55e', width=3),
                        marker=dict(size=8)
                    ))
                    
                    fig_spier.add_trace(go.Scatter(
                        x=[hist['dates'][-1]] + list(proj['dates']),
                        y=[hist['spier'][-1]] + list(proj['spier']),
                        mode='lines+markers',
                        name='Projectie',
                        line=dict(color='#86efac', width=2, dash='dash'),
                        marker=dict(size=6, symbol='diamond')
                    ))
                    
                    layout = get_chart_layout_defaults()
                    layout.update({
                        'title': "Spiermassa",
                        'xaxis_title': "",
                        'yaxis_title': "Spiermassa (kg)",
                        'hovermode': "x unified",
                        'showlegend': True,
                        'height': 300
                    })
                    fig_spier.update_layout(**layout)
                    
                    st.plotly_chart(fig_spier, key="progressie_spier", use_container_width=True, config={"displayModeBar": False})
                
                # Right column: E-gym Kracht Ontwikkeling
                with col_right:
                    st.markdown("#### 💪 Krachtontwikkeling")
                    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
                    
                    # E-gym Progress - Always visible (no expander)
                    egym_df = data.get('egym', pd.DataFrame())
                    
                    if not egym_df.empty:
                        col1_egym, col2_egym = st.columns(2)
                        
                        with col1_egym:
                            st.markdown("""
                            <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.2)); 
                                        padding: 12px; border-radius: 8px; border-left: 3px solid #22c55e; margin-bottom: 12px;">
                                <div style="margin: 0; font-size: 13px; font-weight: 600;">🟢 Groen circuit</div>
                                <div style="margin: 2px 0 0 0; font-size: 11px; opacity: 0.7;">Machines groep A</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            groen = egym_df[egym_df['circuit'] == 'groen']
                            if not groen.empty:
                                for _, row in groen.iterrows():
                                    progress_pct = ""
                                    progress_color = "#10b981"
                                    if pd.notna(row.get('meting3')):
                                        change = ((row['meting3'] - row['meting1']) / row['meting1'] * 100)
                                        progress_pct = f"{change:+.1f}%"
                                        progress_color = "#22c55e" if change > 0 else "#ef4444"
                                    
                                    meting2 = int(row.get('meting2')) if pd.notna(row.get('meting2')) else '?'
                                    meting3 = int(row.get('meting3')) if pd.notna(row.get('meting3')) else '?'
                                    
                                    st.markdown(f"""
                                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 6px; margin-bottom: 5px;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <div>
                                                <div style="font-weight: bold; font-size: 13px;">{row['machine']}</div>
                                                <div style="font-size: 11px; opacity: 0.7; margin-top: 3px;">
                                                    {int(row['meting1'])} → {meting2} → {meting3} kg
                                                </div>
                                            </div>
                                            <div style="text-align: right;">
                                                <div style="font-size: 16px; font-weight: bold; color: {progress_color};">
                                                    {progress_pct if progress_pct else '—'}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        with col2_egym:
                            st.markdown("""
                            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.2)); 
                                        padding: 12px; border-radius: 8px; border-left: 3px solid #3b82f6; margin-bottom: 12px;">
                                <div style="margin: 0; font-size: 13px; font-weight: 600;">🔵 Blauw circuit</div>
                                <div style="margin: 2px 0 0 0; font-size: 11px; opacity: 0.7;">Machines groep B</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            blauw = egym_df[egym_df['circuit'] == 'blauw']
                            if not blauw.empty:
                                for _, row in blauw.iterrows():
                                    progress_pct = ""
                                    progress_color = "#3b82f6"
                                    if pd.notna(row.get('meting2')):
                                        change = ((row['meting2'] - row['meting1']) / row['meting1'] * 100)
                                        progress_pct = f"{change:+.1f}%"
                                        progress_color = "#22c55e" if change > 0 else "#ef4444"
                                    
                                    meting2 = int(row.get('meting2')) if pd.notna(row.get('meting2')) else '?'
                                    meting3 = int(row.get('meting3')) if pd.notna(row.get('meting3')) else '?'
                                    
                                    st.markdown(f"""
                                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 6px; margin-bottom: 5px;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <div>
                                                <div style="font-weight: bold; font-size: 13px;">{row['machine']}</div>
                                                <div style="font-size: 11px; opacity: 0.7; margin-top: 3px;">
                                                    {int(row['meting1'])} → {meting2} → {meting3} kg
                                                </div>
                                            </div>
                                            <div style="text-align: right;">
                                                <div style="font-size: 16px; font-weight: bold; color: {progress_color};">
                                                    {progress_pct if progress_pct else '—'}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                    else:
                        st.info("💪 E-gym data wordt geladen zodra je eerste metingen hebt gedaan!")
            
            elif projections and 'error' in projections:
                st.info(f"ℹ️ {projections['message']}")
        
        # Body Measurements Chart in Expander (LEGACY - kan later verwijderd worden)
        if not metingen_df.empty:
            with st.expander("📊 Lichaamssamenstelling Trend", expanded=False):
                # Create chart data
                date_cols = [col for col in metingen_df.columns if col != 'categorie']
                
                gewicht = metingen_df[metingen_df['categorie'] == 'Gewicht']
                vet_pct = metingen_df[metingen_df['categorie'] == 'Vet %']
                spier = metingen_df[metingen_df['categorie'] == 'Skeletspiermassa']
                
                if not gewicht.empty and not vet_pct.empty and not spier.empty:
                    chart_data = pd.DataFrame({
                        'Datum': date_cols,
                    'Gewicht (kg)': gewicht[date_cols].values[0],
                    'Vet %': vet_pct[date_cols].values[0],
                        'Spiermassa (kg)': spier[date_cols].values[0]
                    })
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=chart_data['Datum'], y=chart_data['Gewicht (kg)'], 
                                            mode='lines+markers', name='Gewicht'))
                    fig.add_trace(go.Scatter(x=chart_data['Datum'], y=chart_data['Vet %'], 
                                            mode='lines+markers', name='Vet %', yaxis='y2'))
                    fig.add_trace(go.Scatter(x=chart_data['Datum'], y=chart_data['Spiermassa (kg)'], 
                                            mode='lines+markers', name='Spiermassa'))
                    
                    fig.update_layout(
                    title="Lichaamssamenstelling Trend",
                    xaxis_title="Datum",
                    yaxis_title="Gewicht / Spiermassa (kg)",
                    yaxis2=dict(title="Vet %", overlaying="y", side="right"),
                    template="custom_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="white"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
                        hovermode="x"
                    )
                    
                    st.plotly_chart(fig, key="chart_line_3635", use_container_width=True, config={"displayModeBar": False})
                    
                    # Table
                    st.markdown(render_dataframe_html(chart_data, max_height="300px"), unsafe_allow_html=True)

    # TAB 6: DATA INVOER
    with tab6:
        st.markdown("### 📝 Data Invoer")
        st.markdown("Typ wat je hebt gegeten of gedaan, en de AI verwerkt het automatisch naar je Google Sheets.")
        
        # Check of helpers beschikbaar zijn
        if not HELPERS_AVAILABLE:
            st.error("⚠️ Helper modules niet geladen. Controleer of sheets_helper.py en groq_helper.py aanwezig zijn.")
            st.stop()
        
        # Setup status checker
        import os
        groq_configured = bool(os.getenv('GROQ_API_KEY') or st.secrets.get('GROQ_API_KEY'))
        # Check if credentials exist locally OR in secrets
        sheets_configured = (
            os.path.exists(os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')) or 
            'gcp_service_account' in st.secrets
        )
        
        # Status indicator
        if not groq_configured or not sheets_configured:
            st.warning("⚠️ Setup is nog niet compleet!")
            with st.expander("📋 Wat ontbreekt er?", expanded=True):
                if not groq_configured:
                    st.error("❌ **Groq API Key** niet ingesteld in `.env` of Streamlit Secrets")
                    st.markdown("""
                    **Wat moet je doen?**
                    1. Ga naar: https://console.groq.com
                    2. Maak een (gratis) account aan
                    3. Klik "API Keys" → "Create API Key"
                    4. Kopieer de key (begint met `gsk_...`)
                    5. **Lokaal**: Open `.env` bestand en plak: `GROQ_API_KEY=gsk_jouw_key_hier`
                    6. **Cloud**: Voeg toe aan Streamlit Secrets
                    
                    📄 Zie **DEPLOYMENT.md** voor meer info!
                    """)
                else:
                    st.success("✅ Groq API Key is ingesteld")
                
                if not sheets_configured:
                    st.error("❌ **Google Sheets Credentials** niet gevonden")
                    st.markdown("""
                    **Wat moet je doen?**
                    1. Ga naar: https://console.cloud.google.com
                    2. Maak een Service Account aan
                    3. Download de JSON credentials
                    4. **Lokaal**: Hernoem naar `credentials.json` en plaats in project folder
                    5. **Cloud**: Voeg toe aan Streamlit Secrets onder `[gcp_service_account]`
                    6. Deel je Google Sheet met het service account email!
                    
                    📄 Zie **DEPLOYMENT.md** voor meer info!
                    """)
                else:
                    st.success("✅ Google Sheets Credentials gevonden")
                    # Show service account email if available
                    try:
                        import json
                        # Try local file first
                        if os.path.exists('credentials.json'):
                            with open('credentials.json', 'r') as f:
                                creds = json.load(f)
                        # Fallback to secrets
                        elif 'gcp_service_account' in st.secrets:
                            creds = dict(st.secrets['gcp_service_account'])
                            if 'client_email' in creds:
                                st.info(f"📧 Service account: `{creds['client_email']}`\n\n"
                                       f"⚠️ Heb je dit email toegevoegd aan je Google Sheet met Editor rechten?")
                    except:
                        pass
        
        st.markdown("---")
        
        # Check for quick action and show relevant hint
        quick_action = st.session_state.get('quick_action', None)
        if quick_action:
            st.success(f"⚡ **Snelle Actie**: Selecteer de **{quick_action.title()}** tab hieronder!")
            # Clear quick action after showing
            if st.button("✅ Begrepen, verberg deze melding", key="clear_quick_action"):
                st.session_state.quick_action = None
                st.rerun()
        
        # Tabs voor verschillende input types
        input_tab1, input_tab2, input_tab3, input_tab4, input_tab5, input_tab6 = st.tabs([
            "🍽️ Voeding",
            "💪 Kracht",
            "🏃 Cardio",
            "👟 Stappen",
            "⚖️ Gewicht",
            "📏 Metingen"
        ])
        
        # TAB: VOEDING INPUT
        with input_tab1:
            st.markdown("#### 🍽️ Voeding Toevoegen")
            st.markdown("Beschrijf wat je hebt gegeten, de AI berekent automatisch de macros.")
            
            maaltijd_type = st.selectbox(
                "Maaltijd type",
                ["Ontbijt", "Lunch", "Avondeten", "Tussendoor"],
                key="voeding_maaltijd"
            )
            
            # Check of er een success flag is en wis de input
            if 'voeding_success' in st.session_state and st.session_state.voeding_success:
                voeding_default = ""
                st.session_state.voeding_success = False
            else:
                voeding_default = st.session_state.get('voeding_input_value', "")
            
            voeding_input = st.text_area(
                "Wat heb je gegeten?",
                placeholder="Bijvoorbeeld: 250g vetvrije kwark, 1 banaan, 2 eetlepels lijnzaad",
                height=100,
                value=voeding_default,
                key="voeding_input"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("➕ Toevoegen aan Google Sheets", key="voeding_submit", type="primary"):
                    if not voeding_input.strip():
                        st.error("Vul eerst in wat je hebt gegeten!")
                    else:
                        try:
                            with st.spinner("AI analyseert en schrijft naar Google Sheets..."):
                                # Parse met AI
                                parsed_data = groq_helper.parse_nutrition(voeding_input, maaltijd_type)
                                
                                # Voeg datum toe
                                parsed_data['datum'] = datetime.now().strftime('%d/%m/%Y')
                                parsed_data['maaltijd'] = maaltijd_type
                                
                                # Toon preview
                                st.info(f"""
                                **Preview:**
                                - Omschrijving: {parsed_data['omschrijving']}
                                - Calorieën: {parsed_data['calorien']}
                                - Eiwit: {parsed_data['eiwit']}g
                                - Koolhydraten: {parsed_data['koolhydraten']}g
                                - Vetten: {parsed_data['vetten']}g
                                - Vezels: {parsed_data['vezels']}g
                                """)
                                
                                # Schrijf naar sheet met user-specific sheet ID
                                user_sheet_id = st.session_state.get('user_sheet_id')
                                sheets_helper.write_to_voeding(parsed_data, sheet_id=user_sheet_id)
                                
                                st.success("✅ Succesvol toegevoegd aan Google Sheets!")
                                st.balloons()
                                
                                # Set success flag voor volgende run
                                st.session_state.voeding_success = True
                                st.session_state.voeding_input_value = ""
                                
                                # Clear cache om nieuwe data te laden
                                st.cache_data.clear()
                                
                        except Exception as e:
                            st.error(f"❌ Fout: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh Data", key="voeding_refresh"):
                    st.cache_data.clear()
                    # Verwijder st.rerun() om page jump te voorkomen
            
            # Toon recente geschiedenis
            st.markdown("---")
            st.markdown("### 📜 Recente Invoer (laatste 10)")
            try:
                # Haal voeding data op
                voeding_df = get_voeding_data()
                if not voeding_df.empty:
                    # Sorteer op datum (nieuwste eerst) en pak laatste 10
                    recent_df = voeding_df.sort_values('datum', ascending=False).head(10)
                    # Toon als mooie tabel met custom styling
                    display_df = recent_df[['datum', 'maaltijd', 'omschrijving', 'calorien', 'eiwit', 'koolhydraten', 'vetten']].copy()
                    st.markdown(render_dataframe_html(display_df, max_height="400px"), unsafe_allow_html=True)
                else:
                    st.info("Nog geen voeding data gevonden.")
            except Exception as e:
                st.warning(f"Kon geschiedenis niet laden: {str(e)}")
        
        # TAB: KRACHT INPUT
        with input_tab2:
            st.markdown("#### 💪 Kracht Training Toevoegen")
            st.markdown("Beschrijf je oefening, sets, reps en gewicht.")
            
            kracht_input = st.text_area(
                "Welke oefening heb je gedaan?",
                placeholder="Bijvoorbeeld: Bench press 80kg, 3 sets van 8 reps, negative",
                height=100,
                key="kracht_input"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("➕ Toevoegen aan Google Sheets", key="kracht_submit", type="primary"):
                    if not kracht_input.strip():
                        st.error("Vul eerst je oefening in!")
                    else:
                        try:
                            with st.spinner("AI analyseert en schrijft naar Google Sheets..."):
                                # Parse met AI
                                parsed_data = groq_helper.parse_exercise(kracht_input)
                                
                                # Voeg datum toe
                                parsed_data['datum'] = datetime.now().strftime('%d/%m/%Y')
                                
                                # Toon preview
                                preview_text = f"""
                                **Preview:**
                                - Oefening: {parsed_data['activiteit']}
                                - Type: {parsed_data['type']}
                                """
                                if parsed_data.get('gewicht'):
                                    preview_text += f"\n- Gewicht: {parsed_data['gewicht']}kg"
                                if parsed_data.get('sets'):
                                    preview_text += f"\n- Sets: {parsed_data['sets']}"
                                if parsed_data.get('reps'):
                                    preview_text += f"\n- Reps: {parsed_data['reps']}"
                                if parsed_data.get('methode'):
                                    preview_text += f"\n- Methode: {parsed_data['methode']}"
                                
                                st.info(preview_text)
                                
                                # Schrijf naar sheet met user-specific sheet ID
                                user_sheet_id = st.session_state.get('user_sheet_id')
                                sheets_helper.write_to_activiteiten(parsed_data, sheet_id=user_sheet_id)
                                
                                st.success("✅ Succesvol toegevoegd aan Google Sheets!")
                                st.balloons()
                                
                                # Clear cache om nieuwe data te laden
                                st.cache_data.clear()
                                
                        except Exception as e:
                            st.error(f"❌ Fout: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh Data", key="kracht_refresh"):
                    st.cache_data.clear()
            
            # Toon recente geschiedenis
            st.markdown("---")
            st.markdown("### 📜 Recente Kracht Training (laatste 10)")
            try:
                activiteiten_df = get_activiteiten_data()
                if not activiteiten_df.empty:
                    # Filter alleen kracht
                    kracht_df = activiteiten_df[activiteiten_df['type'] == 'Kracht']
                    if not kracht_df.empty:
                        recent_df = kracht_df.sort_values('datum', ascending=False).head(10)
                        display_df = recent_df[['datum', 'activiteit', 'gewicht', 'sets', 'reps', 'methode']].copy()
                        st.markdown(render_dataframe_html(display_df, max_height="400px"), unsafe_allow_html=True)
                    else:
                        st.info("Nog geen kracht training data gevonden.")
                else:
                    st.info("Nog geen kracht training data gevonden.")
            except Exception as e:
                st.warning(f"Kon geschiedenis niet laden: {str(e)}")
        
        # TAB: CARDIO INPUT
        with input_tab3:
            st.markdown("#### 🏃 Cardio Toevoegen")
            st.markdown("Beschrijf je cardio activiteit, duur en afstand.")
            
            cardio_input = st.text_area(
                "Welke cardio heb je gedaan?",
                placeholder="Bijvoorbeeld: 30 minuten hardlopen, 6.5 kilometer",
                height=100,
                key="cardio_input"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("➕ Toevoegen aan Google Sheets", key="cardio_submit", type="primary"):
                    if not cardio_input.strip():
                        st.error("Vul eerst je cardio activiteit in!")
                    else:
                        try:
                            with st.spinner("AI analyseert en schrijft naar Google Sheets..."):
                                # Parse met AI
                                parsed_data = groq_helper.parse_cardio(cardio_input)
                                
                                # Voeg datum toe
                                parsed_data['datum'] = datetime.now().strftime('%d/%m/%Y')
                                
                                # Toon preview
                                preview_text = f"""
                                **Preview:**
                                - Activiteit: {parsed_data['activiteit']}
                                - Type: {parsed_data['type']}
                                """
                                if parsed_data.get('afstand'):
                                    preview_text += f"\n- Afstand: {parsed_data['afstand']}km"
                                if parsed_data.get('duur'):
                                    preview_text += f"\n- Duur: {parsed_data['duur']}"
                                
                                st.info(preview_text)
                                
                                # Schrijf naar sheet met user-specific sheet ID
                                user_sheet_id = st.session_state.get('user_sheet_id')
                                sheets_helper.write_to_activiteiten(parsed_data, sheet_id=user_sheet_id)
                                
                                st.success("✅ Succesvol toegevoegd aan Google Sheets!")
                                st.balloons()
                                
                                # Clear cache om nieuwe data te laden
                                st.cache_data.clear()
                                
                        except Exception as e:
                            st.error(f"❌ Fout: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh Data", key="cardio_refresh"):
                    st.cache_data.clear()
            
            # Toon recente geschiedenis
            st.markdown("---")
            st.markdown("### 📜 Recente Cardio (laatste 10)")
            try:
                activiteiten_df = get_activiteiten_data()
                if not activiteiten_df.empty:
                    # Filter alleen cardio
                    cardio_df = activiteiten_df[activiteiten_df['type'] == 'Cardio']
                    if not cardio_df.empty:
                        recent_df = cardio_df.sort_values('datum', ascending=False).head(10)
                        display_df = recent_df[['datum', 'activiteit', 'afstand', 'duur']].copy()
                        st.markdown(render_dataframe_html(display_df, max_height="400px"), unsafe_allow_html=True)
                    else:
                        st.info("Nog geen cardio data gevonden.")
                else:
                    st.info("Nog geen cardio data gevonden.")
            except Exception as e:
                st.warning(f"Kon geschiedenis niet laden: {str(e)}")
        
        # TAB: STAPPEN INPUT
        with input_tab4:
            st.markdown("#### 👟 Stappen Toevoegen")
            st.markdown("Voer je stappen van vandaag in.")
            
            # Use text_input instead of number_input for better styling control
            stappen_str = st.text_input(
                "Aantal stappen",
                value="0",
                key="stappen_input",
                placeholder="Bijv. 10000"
            )
            
            # Validate and convert to integer
            try:
                stappen_input = int(stappen_str) if stappen_str else 0
                if stappen_input < 0:
                    st.error("Aantal stappen moet positief zijn!")
                    stappen_input = 0
            except ValueError:
                st.error("Vul een geldig getal in!")
                stappen_input = 0
            
            cardio_gedaan = st.checkbox("Heb je vandaag ook cardio gedaan?", key="stappen_cardio")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("➕ Toevoegen aan Google Sheets", key="stappen_submit", type="primary"):
                    if stappen_input == 0:
                        st.error("Vul eerst je aantal stappen in!")
                    else:
                        try:
                            with st.spinner("Schrijft naar Google Sheets..."):
                                cardio_str = "ja" if cardio_gedaan else "nee"
                                
                                # Toon preview
                                st.info(f"""
                                **Preview:**
                                - Stappen: {stappen_input:,}
                                - Cardio gedaan: {cardio_str}
                                - Datum: {datetime.now().strftime('%d/%m/%Y')}
                                """)
                                
                                # Schrijf naar sheet met user-specific sheet ID
                                user_sheet_id = st.session_state.get('user_sheet_id')
                                sheets_helper.write_to_stappen(stappen_input, cardio_str, sheet_id=user_sheet_id)
                                
                                st.success("✅ Succesvol toegevoegd aan Google Sheets!")
                                st.balloons()
                                
                        except Exception as e:
                            st.error(f"❌ Fout: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh Data", key="stappen_refresh"):
                    st.cache_data.clear()
            
            # Toon recente geschiedenis
            st.markdown("---")
            st.markdown("### 📜 Recente Stappen (laatste 10)")
            try:
                stappen_df = get_stappen_data()
                if not stappen_df.empty:
                    recent_df = stappen_df.sort_values('datum', ascending=False).head(10)
                    st.markdown(render_dataframe_html(recent_df, max_height="400px"), unsafe_allow_html=True)
                else:
                    st.info("Nog geen stappen data gevonden.")
            except Exception as e:
                st.warning(f"Kon geschiedenis niet laden: {str(e)}")
        
        # TAB: GEWICHT INPUT
        with input_tab5:
            st.markdown("#### ⚖️ Gewicht Toevoegen")
            st.markdown("Voer je huidige gewicht in.")
            
            # Use text_input instead of number_input for better styling control
            gewicht_str = st.text_input(
                "Gewicht (kg)",
                value="0.0",
                key="gewicht_input",
                placeholder="Bijv. 75.5"
            )
            
            # Validate and convert to float
            try:
                gewicht_input = float(gewicht_str) if gewicht_str else 0.0
                if gewicht_input < 0:
                    st.error("Gewicht moet positief zijn!")
                    gewicht_input = 0.0
                elif gewicht_input > 300:
                    st.error("Gewicht lijkt onrealistisch hoog!")
                    gewicht_input = 0.0
            except ValueError:
                st.error("Vul een geldig getal in (gebruik punt voor decimalen)!")
                gewicht_input = 0.0
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("➕ Toevoegen aan Google Sheets", key="gewicht_submit", type="primary"):
                    if gewicht_input == 0.0:
                        st.error("Vul eerst je gewicht in!")
                    else:
                        try:
                            with st.spinner("Schrijft naar Google Sheets..."):
                                # Toon preview
                                st.info(f"""
                                **Preview:**
                                - Gewicht: {gewicht_input:.1f}kg
                                - Datum: {datetime.now().strftime('%d/%m/%Y')}
                                """)
                                
                                # Schrijf naar sheet met user-specific sheet ID
                                user_sheet_id = st.session_state.get('user_sheet_id')
                                sheets_helper.write_to_gewicht(gewicht_input, sheet_id=user_sheet_id)
                                
                                st.success("✅ Succesvol toegevoegd aan Google Sheets!")
                                st.balloons()
                                
                        except Exception as e:
                            st.error(f"❌ Fout: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh Data", key="gewicht_refresh"):
                    st.cache_data.clear()
            
            # Toon recente geschiedenis
            st.markdown("---")
            st.markdown("### 📜 Recent Gewicht (laatste 10)")
            try:
                gewicht_df = get_gewicht_data()
                if not gewicht_df.empty:
                    recent_df = gewicht_df.sort_values('datum', ascending=False).head(10)
                    st.markdown(render_dataframe_html(recent_df, max_height="400px"), unsafe_allow_html=True)
                else:
                    st.info("Nog geen gewicht data gevonden.")
            except Exception as e:
                st.warning(f"Kon geschiedenis niet laden: {str(e)}")
        
        # TAB: METINGEN INPUT
        with input_tab6:
            st.markdown("#### 📏 Metingen Toevoegen")
            st.markdown("Beschrijf je metingen, de AI herkent automatisch de verschillende waarden.")
            
            metingen_input = st.text_area(
                "Welke metingen heb je gedaan?",
                placeholder="Bijvoorbeeld: Gewicht 105.6kg, Vet% 27.9, Buikomvang 95cm, Skeletspiermassa 45.2kg",
                height=100,
                key="metingen_input"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("➕ Toevoegen aan Google Sheets", key="metingen_submit", type="primary"):
                    if not metingen_input.strip():
                        st.error("Vul eerst je metingen in!")
                    else:
                        try:
                            with st.spinner("AI analyseert en schrijft naar Google Sheets..."):
                                # Parse met AI
                                parsed_data = groq_helper.parse_measurements(metingen_input)
                                
                                # Toon preview
                                preview_text = "**Preview:**\n"
                                for key, value in parsed_data.items():
                                    preview_text += f"- {key}: {value}\n"
                                preview_text += f"- Datum: {datetime.now().strftime('%d/%m')}"
                                
                                st.info(preview_text)
                                
                                # Schrijf naar sheet met user-specific sheet ID
                                user_sheet_id = st.session_state.get('user_sheet_id')
                                sheets_helper.write_to_metingen(parsed_data, sheet_id=user_sheet_id)
                                
                                st.success("✅ Succesvol toegevoegd aan Google Sheets!")
                                st.balloons()
                                
                                # Clear cache om nieuwe data te laden
                                st.cache_data.clear()
                                
                        except Exception as e:
                            st.error(f"❌ Fout: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh Data", key="metingen_refresh"):
                    st.cache_data.clear()

if __name__ == "__main__":
    main()


