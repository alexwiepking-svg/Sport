"""
Helper functies voor Groq AI integratie
Gebruikt Groq's Llama 3.1 70B model voor het parsen van natuurlijke taal naar gestructureerde data
"""
import os
import json
from typing import Dict, Any, Optional
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_groq_client():
    """Maak verbinding met Groq API"""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY niet gevonden in .env bestand\n"
            "Zie SETUP_INSTRUCTIONS.md voor meer informatie"
        )
    return Groq(api_key=api_key)

def parse_nutrition(text: str, maaltijd: str) -> Dict[str, Any]:
    """
    Parse voeding input naar gestructureerde data
    
    Args:
        text: Natuurlijke taal beschrijving (bijv. "200g kip, 150g rijst, broccoli")
        maaltijd: Type maaltijd (Ontbijt/Lunch/Avondeten/Tussendoor)
    
    Returns:
        {
            'omschrijving': str,
            'calorien': int,
            'eiwit': int,
            'koolhydraten': int,
            'vetten': int,
            'vezels': int
        }
    """
    client = get_groq_client()
    
    prompt = f"""Je bent een professionele voedingsdeskundige. Analyseer de volgende maaltijd en geef REALISTISCHE, NAUWKEURIGE macronutriënten.

Maaltijd type: {maaltijd}
Beschrijving: {text}

BELANGRIJKE RICHTLIJNEN:
1. Gebruik standaard Nederlandse portiegrootten als er geen gewicht wordt genoemd
2. Bereken calorieën nauwkeurig op basis van de macros: (eiwit×4) + (koolhydraten×4) + (vetten×9)
3. Wees conservatief maar realistisch - geen extreme lage of hoge schattingen
4. Voor vlees/vis: gemiddeld 25-30g eiwit per 100g
5. Voor sauzen zoals mayonaise: zeer hoog in vetten (bijv. 1 eetlepel mayo = ~10g vet = ~90 cal)
6. Voor gebraden/gebakken voedsel: voeg extra vetten toe voor de bereiding

VOORBEELDEN:
- "Gebraden kip met mayonaise" = kip (200g) + mayo (2el) = ongeveer:
  * Eiwit: 50g (kip) 
  * Vetten: 25g (kip + mayo)
  * Koolhydraten: 0-2g
  * Calorieën: (50×4) + (2×4) + (25×9) = 200 + 8 + 225 = ~435 cal

- "250g kwark, banaan, 2el lijnzaad" = 
  * Eiwit: 32g
  * Koolhydraten: 38g  
  * Vetten: 8g
  * Calorieën: ~336 cal

Geef de output als JSON met de volgende structuur:
{{
    "omschrijving": "korte beschrijving van de maaltijd",
    "calorien": <geschat aantal calorieën (moet kloppen met de macros!)>,
    "eiwit": <gram eiwit>,
    "koolhydraten": <gram koolhydraten>,
    "vetten": <gram vetten>,
    "vezels": <gram vezels>
}}

Geef ALLEEN de JSON output, geen extra tekst."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content.strip()
        
        # Verwijder eventuele markdown code blocks
        if result.startswith('```'):
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
        
        data = json.loads(result)
        return data
        
    except Exception as e:
        raise Exception(f"Fout bij parsen voeding: {str(e)}")

def parse_exercise(text: str) -> Dict[str, Any]:
    """
    Parse kracht training input naar gestructureerde data
    
    Args:
        text: Natuurlijke taal beschrijving (bijv. "Bench press 80kg, 3 sets van 8 reps, negative")
    
    Returns:
        {
            'activiteit': str,
            'type': 'Kracht',
            'gewicht': int (optional),
            'sets': int (optional),
            'reps': int (optional),
            'methode': str (optional)
        }
    """
    client = get_groq_client()
    
    prompt = f"""Je bent een fitness expert. Analyseer de volgende kracht training oefening.

Beschrijving: {text}

Geef de output als JSON met de volgende structuur:
{{
    "activiteit": "naam van de oefening",
    "type": "Kracht",
    "gewicht": <gewicht in kg, of null als niet vermeld>,
    "sets": <aantal sets, of null als niet vermeld>,
    "reps": <aantal reps per set, of null als niet vermeld>,
    "methode": <trainingsmethode zoals 'Negative', 'Drop set', etc., of null als niet vermeld>
}}

Vertaal Engelse oefeningen naar Nederlands waar mogelijk (bijv. "Bench press" -> "Bankdrukken").

Geef ALLEEN de JSON output, geen extra tekst."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.startswith('```'):
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
        
        data = json.loads(result)
        return data
        
    except Exception as e:
        raise Exception(f"Fout bij parsen oefening: {str(e)}")

def parse_cardio(text: str) -> Dict[str, Any]:
    """
    Parse cardio activiteit input naar gestructureerde data
    
    Args:
        text: Natuurlijke taal beschrijving (bijv. "30 minuten hardlopen, 6.5km")
    
    Returns:
        {
            'activiteit': str,
            'type': 'Cardio',
            'afstand': float (optional),
            'duur': str (optional, HH:MM:SS formaat)
        }
    """
    client = get_groq_client()
    
    prompt = f"""Je bent een fitness expert. Analyseer de volgende cardio activiteit.

Beschrijving: {text}

Geef de output als JSON met de volgende structuur:
{{
    "activiteit": "naam van de activiteit (hardlopen, fietsen, zwemmen, etc.)",
    "type": "Cardio",
    "afstand": <afstand in km als decimaal, of null als niet vermeld>,
    "duur": <duur in HH:MM:SS formaat, of null als niet vermeld>
}}

Converteer tijd altijd naar HH:MM:SS formaat (bijv. "30 minuten" -> "00:30:00", "1 uur 15 min" -> "01:15:00").

Geef ALLEEN de JSON output, geen extra tekst."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.startswith('```'):
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
        
        data = json.loads(result)
        return data
        
    except Exception as e:
        raise Exception(f"Fout bij parsen cardio: {str(e)}")

def parse_measurements(text: str) -> Dict[str, Any]:
    """
    Parse metingen input naar gestructureerde data
    
    Args:
        text: Natuurlijke taal beschrijving (bijv. "Gewicht: 105.6kg, Vet%: 27.9, Buik: 95cm")
    
    Returns:
        {
            'Gewicht': float,
            'Vet %': float,
            'Skeletspiermassa': float,
            'Buikomvang': int,
            # ... andere metingen
        }
    """
    client = get_groq_client()
    
    prompt = f"""Je bent een expert in lichaamsmetingen. Analyseer de volgende metingen.

Beschrijving: {text}

Mogelijke metingen om te herkennen:
- Gewicht (in kg)
- Vet % (vetpercentage)
- Skeletspiermassa (in kg)
- Visceraal vetniveau (getal)
- Vetmassa (in kg)
- Lichaamsvocht (in L)
- Buikomvang (in cm)
- BMI

Geef de output als JSON met alleen de metingen die worden genoemd:
{{
    "Gewicht": <waarde in kg>,
    "Vet %": <percentage als decimaal, bijv. 27.9>,
    "Buikomvang": <waarde in cm>,
    ...
}}

Gebruik exact deze namen voor de keys. Laat metingen weg die niet worden genoemd.

Geef ALLEEN de JSON output, geen extra tekst."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.startswith('```'):
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
        
        data = json.loads(result)
        return data
        
    except Exception as e:
        raise Exception(f"Fout bij parsen metingen: {str(e)}")

def test_groq_connection() -> Dict[str, Any]:
    """Test de Groq API connectie"""
    try:
        # Check of API key is ingesteld
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {
                'success': False,
                'message': f'❌ GROQ_API_KEY niet gevonden in .env bestand\n\n'
                          f'📍 .env bestand: {os.path.abspath(".env")}\n\n'
                          f'👉 Zie QUICKSTART.md stap 1 voor het aanmaken van een Groq API key'
            }
        
        # Test connectie
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Zeg 'OK' als je dit begrijpt."}],
            temperature=0.1,
            max_tokens=10
        )
        
        return {
            'success': True,
            'message': '✅ Groq API verbinding succesvol! 🚀\n\nJe kunt nu AI-powered data invoer gebruiken!'
        }
    except Exception as e:
        error_msg = str(e)
        if 'authentication' in error_msg.lower() or 'api key' in error_msg.lower():
            return {
                'success': False,
                'message': f'❌ Groq API key is ongeldig\n\n'
                          f'👉 Maak een nieuwe key aan op: https://console.groq.com\n'
                          f'👉 Update de key in .env bestand'
            }
        return {
            'success': False,
            'message': f'❌ Groq API verbinding mislukt: {error_msg}'
        }
