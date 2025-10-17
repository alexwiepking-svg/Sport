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


def generate_daily_coaching(current_data: Dict[str, Any], targets: Dict[str, Any], name: str = "gebruiker") -> str:
    """
    Genereer een persoonlijk dagcoaching rapport op basis van huidige voortgang
    
    Args:
        current_data: Dictionary met huidige dag data:
            - nutrition: {calories, protein, carbs, fats}
            - workouts: list van trainingen
            - steps: aantal stappen
            - weight: huidige gewicht
        targets: Dictionary met doelen:
            - calories, protein, carbs, fats, weight
        name: Naam van de gebruiker
    
    Returns:
        Markdown-formatted coaching rapport
    """
    try:
        client = get_groq_client()
        
        # Build context voor de AI - gebruik lowercase keys die matchen met calculate_nutrition_totals
        nutrition = current_data.get('nutrition', {})
        calories = nutrition.get('calorien', 0)
        protein = nutrition.get('eiwit', 0)
        carbs = nutrition.get('koolhydraten', 0)
        fats = nutrition.get('vetten', 0)
        
        # Get workout details
        total_workouts = len(current_data.get('workouts', []))
        cardio_sessions = current_data.get('cardio_sessions', [])
        kracht_sessions = current_data.get('kracht_sessions', [])
        
        # Build workout summary
        workout_summary = []
        if cardio_sessions:
            workout_summary.append(f"Cardio: {', '.join(cardio_sessions[:3])}")  # Max 3 shown
        if kracht_sessions:
            workout_summary.append(f"Kracht: {', '.join(kracht_sessions[:3])}")  # Max 3 shown
        workout_details = "; ".join(workout_summary) if workout_summary else "Geen trainingen"
        
        context = f"""Je bent een persoonlijke fitness coach die {name} helpt met hun dagelijkse voortgang.

HUIDIGE STATUS (vandaag tot nu):
- Calorieën: {calories:.0f}/{targets.get('calories', 2000)} kcal ({(calories/targets.get('calories', 2000)*100):.0f}%)
- Eiwitten: {protein:.0f}/{targets.get('protein', 160)}g ({(protein/targets.get('protein', 160)*100):.0f}%)
- Koolhydraten: {carbs:.0f}/{targets.get('carbs', 180)}g
- Vetten: {fats:.0f}/{targets.get('fats', 60)}g
- Stappen: {current_data.get('steps', 0):,}/10.000
- Trainingen: {total_workouts} sessies ({workout_details})
  * Cardio: {len(cardio_sessions)} sessies
  * Kracht: {len(kracht_sessions)} sessies

DOELEN:
- Huidig gewicht: {targets.get('weight', 0):.1f}kg
- Doel gewicht: {targets.get('target_weight', targets.get('weight', 85)):.1f}kg
- Verschil: {abs(targets.get('weight', 0) - targets.get('target_weight', 85)):.1f}kg te gaan
- Dagelijks calorie target: {targets.get('calories', 2000)} kcal
- Eiwit target: {targets.get('protein', 160)}g

Genereer een KORT, MOTIVEREND en PRAKTISCH rapport met:
1. 📊 Snelle analyse van de huidige voortgang (2-3 zinnen, noem specifieke percentages en aantallen)
2. 💡 Specifiek advies voor de rest van de dag (wat moet er NOG gebeuren? Hoeveel calorieën/eiwit nog?)
3. 🍽️ Concrete suggesties voor de volgende maaltijd (met geschatte macros)
4. 💪 Training advies gebaseerd op wat al gedaan is (cardio/kracht balans, suggesties voor vandaag)
5. 🎯 1 motiverende zin om de dag sterk af te sluiten

Gebruik emojis, wees enthousiast maar realistisch. Maximaal 200 woorden.
Schrijf in het Nederlands, spreek de gebruiker direct aan met "je".
"""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Je bent een enthousiaste Nederlandse fitness coach die kort en krachtig advies geeft."
                },
                {
                    "role": "user",
                    "content": context
                }
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"❌ Kon geen coaching rapport genereren: {str(e)}"

def generate_quick_actions(current_data, targets, name):
    """
    Genereer korte, concrete actiepunten voor de sidebar
    
    Args:
        current_data: Dict met huidige voortgang (nutrition, workouts, steps)
        targets: Dict met doelen
        name: Naam gebruiker
        
    Returns:
        Dict met 'nutrition_actions' en 'goals' lists
    """
    try:
        client = get_groq_client()
        
        # Extract data
        nutrition = current_data.get('nutrition', {})
        calories = nutrition.get('calorien', 0)
        protein = nutrition.get('eiwit', 0)
        
        context = f"""Genereer korte actiepunten voor {name} voor morgen/de komende dag.

HUIDIGE STATUS (vandaag):
- Calorieën: {calories:.0f}/{targets.get('calories', 2000)} kcal
- Eiwit: {protein:.0f}/{targets.get('protein', 160)}g
- Trainingen: {len(current_data.get('workouts', []))}
- Stappen: {current_data.get('steps', 0):,}

Genereer:
1. 3-4 concrete VOEDING actiepunten (specifieke hoeveelheden, voedsel suggesties)
2. 3-4 DOEL actiepunten (training frequentie, targets, gewicht)

Format:
🍳 Voeding:
• [actie 1]
• [actie 2]
• [actie 3]

🎯 Doelen:
• [doel 1]
• [doel 2]
• [doel 3]

Wees kort, specifiek en gemotiveerd. Max 10 woorden per actie. Gebruik getallen."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Je bent een fitness coach die korte, concrete actiepunten geeft."},
                {"role": "user", "content": context}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Parse response
        content = response.choices[0].message.content
        
        # Extract lists
        nutrition_actions = []
        goals = []
        
        current_section = None
        for line in content.split('\n'):
            line = line.strip()
            if '🍳' in line or 'Voeding' in line:
                current_section = 'nutrition'
            elif '🎯' in line or 'Doelen' in line or 'Doel' in line:
                current_section = 'goals'
            elif line.startswith('•') or line.startswith('-'):
                cleaned = line.lstrip('•-').strip()
                if cleaned:
                    if current_section == 'nutrition':
                        nutrition_actions.append(cleaned)
                    elif current_section == 'goals':
                        goals.append(cleaned)
        
        # Fallback if parsing failed
        if not nutrition_actions:
            cal_left = targets.get('calories', 2000) - calories
            prot_left = targets.get('protein', 160) - protein
            nutrition_actions = [
                f"Voeg {int(prot_left)}g eiwit toe (kwark/kip)" if prot_left > 0 else "Eiwit op target ✓",
                f"Nog {int(cal_left)} kcal voor vandaag" if cal_left > 0 else "Calorieën goed op schema",
                "Drink 2-3L water"
            ]
        
        if not goals:
            goals = [
                f"{targets.get('calories')} kcal per dag",
                f"{targets.get('protein')}g+ eiwit",
                "4+ trainingen/week"
            ]
        
        return {
            'nutrition_actions': nutrition_actions[:4],  # Max 4
            'goals': goals[:4]  # Max 4
        }
        
    except Exception as e:
        # Fallback to basic recommendations
        return {
            'nutrition_actions': [
                "Eet eiwitrijk (180g+ per dag)",
                "Drink 2-3L water",
                "Eet binnen 30 min na training"
            ],
            'goals': [
                f"{targets.get('calories', 2000)} kcal per dag",
                f"{targets.get('protein', 160)}g+ eiwit",
                "4+ trainingen/week"
            ]
        }

