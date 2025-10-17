"""
Helper functies voor Google Sheets integratie
"""
import os
from datetime import datetime
from typing import Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Sheets scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_sheets_client():
    """Maak verbinding met Google Sheets API"""
    try:
        # Try Streamlit secrets first (for cloud deployment)
        try:
            import streamlit as st
            if 'gcp_service_account' in st.secrets:
                creds = Credentials.from_service_account_info(
                    st.secrets['gcp_service_account'],
                    scopes=SCOPES
                )
                client = gspread.authorize(creds)
                return client
        except Exception:
            pass
        
        # Fallback to local credentials.json file
        creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                f"Credentials bestand niet gevonden: {creds_path}\n"
                "Zie SETUP_INSTRUCTIONS.md voor meer informatie"
            )
        
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        raise Exception(f"Fout bij verbinden met Google Sheets: {str(e)}")

def get_spreadsheet(sheet_id: Optional[str] = None):
    """Haal de sport tracking spreadsheet op"""
    if not sheet_id:
        # Fallback naar SHEET_ID_ALEX als geen sheet_id is opgegeven
        sheet_id = os.getenv('SHEET_ID_ALEX') or os.getenv('SHEET_ID')
    
    if not sheet_id:
        raise ValueError("Geen SHEET_ID gevonden. Zet SHEET_ID_ALEX of SHEET_ID in .env bestand")
    
    client = get_sheets_client()
    return client.open_by_key(sheet_id)

def write_to_voeding(data: Dict[str, Any], sheet_id: Optional[str] = None) -> bool:
    """
    Schrijf voeding data naar de 'voeding' sheet
    
    Expected data format:
    {
        'datum': '17/10/2025',
        'maaltijd': 'Ontbijt',
        'omschrijving': '250g kwark, banaan',
        'calorien': 320,
        'eiwit': 32,
        'koolhydraten': 38,
        'vetten': 6,
        'vezels': 8
    }
    """
    try:
        spreadsheet = get_spreadsheet(sheet_id)
        sheet = spreadsheet.worksheet('voeding')
        
        # Zorg voor datum in juiste formaat (ZONDER apostrofe voor Google Sheets)
        if 'datum' not in data:
            data['datum'] = datetime.now().strftime('%d/%m/%Y')
        
        # Maak row aan met juiste volgorde
        row = [
            data.get('datum', ''),
            data.get('maaltijd', ''),
            data.get('omschrijving', ''),
            data.get('calorien', 0),
            data.get('eiwit', 0),
            data.get('koolhydraten', 0),
            data.get('vetten', 0),
            data.get('vezels', 0)
        ]
        
        # Append row met value_input_option='USER_ENTERED' zodat datums als datums worden opgeslagen
        sheet.append_row(row, value_input_option='USER_ENTERED')
        return True
        
    except Exception as e:
        raise Exception(f"Fout bij schrijven naar voeding sheet: {str(e)}")

def write_to_activiteiten(data: Dict[str, Any], sheet_id: Optional[str] = None) -> bool:
    """
    Schrijf activiteit data naar de 'activiteiten' sheet
    
    Expected data format:
    {
        'datum': '17/10/2025',
        'activiteit': 'Bench press',
        'type': 'Kracht',  # of 'Cardio'
        'gewicht': 80,  # optional
        'afstand': None,  # optional
        'duur': '00:45:00',  # optional
        'sets': 3,  # optional
        'reps': 8,  # optional
        'methode': 'Negative'  # optional
    }
    """
    try:
        spreadsheet = get_spreadsheet(sheet_id)
        sheet = spreadsheet.worksheet('activiteiten')
        
        if 'datum' not in data:
            data['datum'] = datetime.now().strftime('%d/%m/%Y')
        
        row = [
            data.get('datum', ''),
            data.get('activiteit', ''),
            data.get('type', ''),
            data.get('gewicht', ''),
            data.get('afstand', ''),
            data.get('duur', ''),
            data.get('sets', ''),
            data.get('reps', ''),
            data.get('methode', '')
        ]
        
        sheet.append_row(row, value_input_option='USER_ENTERED')
        return True
        
    except Exception as e:
        raise Exception(f"Fout bij schrijven naar activiteiten sheet: {str(e)}")

def write_to_stappen(stappen: int, cardio: str, datum: Optional[str] = None, sheet_id: Optional[str] = None) -> bool:
    """
    Schrijf stappen data naar de 'stappen' sheet
    
    Args:
        stappen: Aantal stappen
        cardio: 'ja' of 'nee'
        datum: Datum in DD/MM/YYYY formaat (default: vandaag)
        sheet_id: Google Sheet ID (optional)
    """
    try:
        spreadsheet = get_spreadsheet(sheet_id)
        sheet = spreadsheet.worksheet('stappen')
        
        if not datum:
            datum = datetime.now().strftime('%d/%m/%Y')
        
        row = [datum, stappen, cardio]
        sheet.append_row(row, value_input_option='USER_ENTERED')
        return True
        
    except Exception as e:
        raise Exception(f"Fout bij schrijven naar stappen sheet: {str(e)}")

def write_to_gewicht(gewicht: float, datum: Optional[str] = None, sheet_id: Optional[str] = None) -> bool:
    """
    Schrijf gewicht data naar de 'gewicht' sheet
    
    Args:
        gewicht: Gewicht in kg
        datum: Datum in DD/MM/YYYY formaat (default: vandaag)
        sheet_id: Google Sheet ID (optional)
    """
    try:
        spreadsheet = get_spreadsheet(sheet_id)
        sheet = spreadsheet.worksheet('gewicht')
        
        if not datum:
            datum = datetime.now().strftime('%d/%m/%Y')
        
        row = [datum, gewicht]
        sheet.append_row(row, value_input_option='USER_ENTERED')
        return True
        
    except Exception as e:
        raise Exception(f"Fout bij schrijven naar gewicht sheet: {str(e)}")

def write_to_metingen(data: Dict[str, Any], datum: Optional[str] = None, sheet_id: Optional[str] = None) -> bool:
    """
    Schrijf metingen data naar de 'metingen' sheet
    Voegt een nieuwe kolom toe met de datum als header
    
    Expected data format:
    {
        'Gewicht': 105.6,
        'Vet %': 27.9,
        'Skeletspiermassa': 45.2,
        'Buikomvang': 95,
        # ... andere metingen
    }
    """
    try:
        spreadsheet = get_spreadsheet(sheet_id)
        sheet = spreadsheet.worksheet('metingen')
        
        if not datum:
            datum = datetime.now().strftime('%d/%m')
        
        # Haal huidige headers op (eerste rij)
        headers = sheet.row_values(1)
        
        # Check of deze datum al bestaat
        if datum in headers:
            # Update bestaande kolom
            col_index = headers.index(datum) + 1
        else:
            # Voeg nieuwe kolom toe
            col_index = len(headers) + 1
            sheet.update_cell(1, col_index, datum)
        
        # Haal categorieën op (eerste kolom)
        categories = sheet.col_values(1)
        
        # Update elke meting
        for category, value in data.items():
            if category in categories:
                row_index = categories.index(category) + 1
                sheet.update_cell(row_index, col_index, value)
        
        return True
        
    except Exception as e:
        raise Exception(f"Fout bij schrijven naar metingen sheet: {str(e)}")

def test_connection() -> Dict[str, Any]:
    """Test de Google Sheets connectie"""
    try:
        # Check of credentials bestand bestaat
        creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        if not os.path.exists(creds_path):
            return {
                'success': False,
                'message': f'❌ Credentials bestand niet gevonden: {creds_path}\n\n'
                          f'📍 Verwacht op: {os.path.abspath(creds_path)}\n\n'
                          f'👉 Zie QUICKSTART.md stap 2 voor het aanmaken van credentials.json'
            }
        
        # Test connectie
        spreadsheet = get_spreadsheet()
        sheets = [ws.title for ws in spreadsheet.worksheets()]
        
        return {
            'success': True,
            'message': f'✅ Verbinding succesvol!\n\n📊 Gevonden sheets: {", ".join(sheets)}'
        }
    except Exception as e:
        error_msg = str(e)
        if '404' in error_msg:
            return {
                'success': False,
                'message': f'❌ Google Sheet niet gevonden (404)\n\n'
                          f'Mogelijke oorzaken:\n'
                          f'1️⃣ Sheet ID is verkeerd in .env\n'
                          f'2️⃣ Service account heeft geen toegang tot de sheet\n\n'
                          f'👉 Deel je Google Sheet met het service account email!\n'
                          f'    Zie QUICKSTART.md stap 2 (punt 17-22)'
            }
        return {
            'success': False,
            'message': f'❌ Verbinding mislukt: {error_msg}'
        }
