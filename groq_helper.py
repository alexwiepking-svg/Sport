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

def parse_nutrition(text: str, maaltijd: str, retry: bool = False) -> Dict[str, Any]:
    """
    Parse voeding input naar gestructureerde data
    
    Args:
        text: Natuurlijke taal beschrijving (bijv. "200g kip, 150g rijst, broccoli")
        maaltijd: Type maaltijd (Ontbijt/Lunch/Avondeten/Tussendoor)
        retry: Internal flag voor retry mechanisme
    
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
    
    # Simpelere prompt bij retry
    if retry:
        prompt = f"""Analyseer deze maaltijd en geef macronutriënten als JSON:

{text}

Antwoord in dit exacte formaat (ALLEEN JSON, geen extra tekst):
{{"omschrijving": "beschrijving", "calorien": 0, "eiwit": 0, "koolhydraten": 0, "vetten": 0, "vezels": 0}}"""
    else:
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
            # Split op ``` en pak het middelste deel
            parts = result.split('```')
            if len(parts) >= 2:
                result = parts[1]
                # Verwijder 'json' aan het begin als dat er staat
                if result.strip().startswith('json'):
                    result = result.strip()[4:].strip()
        
        # Extra cleanup: verwijder trailing text na }
        if '}' in result:
            result = result[:result.rfind('}')+1]
        
        # Remove any text before {
        if '{' in result:
            result = result[result.find('{'):]
        
        try:
            data = json.loads(result)
        except json.JSONDecodeError as je:
            # Als JSON parsing faalt EN we hebben nog niet geretried, probeer opnieuw
            if not retry:
                return parse_nutrition(text, maaltijd, retry=True)
            # Als retry ook faalt, geef duidelijke error
            raise Exception(f"AI kan deze invoer niet verwerken. Probeer het korter/eenvoudiger te formuleren.")
        
        return data
        
    except Exception as e:
        # Als het een retry was die faalde, geef user-friendly error
        if retry or "AI kan deze invoer niet verwerken" in str(e):
            raise Exception("AI kan deze invoer niet verwerken. Probeer: minder ingrediënten, kortere beschrijving, of andere bewoordingen.")
        
        # Als het de eerste poging was, probeer retry met simpelere prompt
        if "Fout bij parsen voeding" not in str(e):
            try:
                return parse_nutrition(text, maaltijd, retry=True)
            except:
                pass
        
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

def generate_insights_and_feedback(current_data, targets, period_stats, name):
    """
    Genereer slimme inzichten EN verbeterpunten/successen voor in de Overzicht tab
    
    Args:
        current_data: Dict met huidige voortgang (nutrition totals), view_mode, date range
        targets: Dict met doelen
        period_stats: Dict met periode statistieken
        name: Naam gebruiker
        
    Returns:
        Dict met 'insights' (list), 'improvements' (list), 'successes' (list)
    """
    try:
        client = get_groq_client()
        
        # Extract data
        nutrition = current_data.get('nutrition', {})
        calories = nutrition.get('calorien', 0)
        protein = nutrition.get('eiwit', 0)
        carbs = nutrition.get('koolhydraten', 0)
        fats = nutrition.get('vetten', 0)
        
        # Get time context
        view_mode = current_data.get('view_mode', '📅 Dag')
        start_date = current_data.get('start_date')
        end_date = current_data.get('end_date')
        
        # Determine period type
        if '📅 Dag' in view_mode:
            period_type = "vandaag"
            period_label = "dagelijkse"
        elif '📊 Week' in view_mode:
            period_type = "deze week"
            period_label = "weekgemiddelde"
        else:  # Maand
            period_type = "deze maand"
            period_label = "maandgemiddelde"
        
        # Calculate remaining calories/macros for the day (only for daily view)
        remaining_context = ""
        if '📅 Dag' in view_mode:
            remaining_cals = targets.get('calories', 2000) - calories
            remaining_protein = targets.get('protein', 160) - protein
            if remaining_cals > 0:
                remaining_context = f"\nResterend vandaag: {remaining_cals:.0f} kcal, {remaining_protein:.0f}g eiwit"
        
        context = f"""Analyseer {name}'s voortgang over {period_type} en geef REALISTISCHE, ACTIONABLE feedback.

TIJDSPERIODE: {period_type.upper()} ({period_label} data)
Dagen in periode: {period_stats.get('days', 1)}

DATA VOOR {period_type.upper()}:
- Calorieën: {calories:.0f}/{targets.get('calories', 2000)} kcal ({period_label})
- Eiwit: {protein:.0f}/{targets.get('protein', 160)}g ({period_label})
- Koolhydraten: {carbs:.0f}/{targets.get('carbs', 180)}g
- Vetten: {fats:.0f}/{targets.get('fats', 60)}g
- Trainingen: {period_stats.get('total_workouts', 0)} (cardio: {period_stats.get('cardio_sessions', 0)}, kracht: {period_stats.get('strength_sessions', 0)}){remaining_context}

DOELEN:
- Huidig gewicht: {targets.get('weight', 106)}kg → Doel: {targets.get('target_weight', 85)}kg

BELANGRIJK:
- Als dit WEEK/MAAND data is: geef TREND feedback, niet dagadvies
- Als calories BOVEN target: geef suggesties om te verminderen (niet "0 calories")
- Wees REALISTISCH: geen extreme adviezen, concrete portiegroottes
- Als iemand al 3000 kcal heeft gehad: adviseer lichte maaltijd (300-400 kcal), niet "0 calories"

Genereer 3 categorieën feedback:

1. **SLIMME INZICHTEN** (2-3 items): Belangrijkste observaties over calorieën, eiwit, training
   Format: [type]|[icon]|[titel]|[bericht]
   Types: success (groen), warning (oranje), info (blauw)
   Iconen: ✅⚠️💡🔥💪

2. **VERBETERPUNTEN** (2-3 items): Concrete, realistische verbeteringen
   Format: 🔴 [urgent probleem] OF 🟡 [minder urgent]
   Voorbeeld: "🟡 Probeer lunch te limiteren tot 600-700 kcal" NIET "eet 0 calories"

3. **WAT GOED GAAT** (2-3 items): Positieve feedback
   Format: 🟢 [succes met detail]

Wees specifiek, realistisch, en gemotiveerd. Max 20 woorden per item."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Je bent een realistische fitness coach die concrete, haalbare feedback geeft. Je past je advies aan op basis van de tijdsperiode (dag/week/maand) en geeft NOOIT extreme adviezen zoals '0 calories'. Als iemand al veel gegeten heeft, adviseer je een lichte maar voedzame maaltijd van 300-500 kcal."},
                {"role": "user", "content": context}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        
        # Parse response
        insights = []
        improvements = []
        successes = []
        
        current_section = None
        for line in content.split('\n'):
            line = line.strip()
            
            # Detect sections
            if 'INZICHT' in line.upper() or 'INSIGHT' in line.upper():
                current_section = 'insights'
                continue
            elif 'VERBETER' in line.upper() or 'IMPROVE' in line.upper():
                current_section = 'improvements'
                continue
            elif 'GOED' in line.upper() or 'SUCCESS' in line.upper() or 'GAAT' in line.upper():
                current_section = 'successes'
                continue
            
            # Parse insights (special format)
            if current_section == 'insights' and '|' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    insights.append({
                        'type': parts[0].strip(),
                        'icon': parts[1].strip(),
                        'title': parts[2].strip(),
                        'message': parts[3].strip()
                    })
            
            # Parse improvements/successes (bullet points)
            elif line.startswith('🔴') or line.startswith('🟡'):
                if current_section == 'improvements':
                    improvements.append(line)
            elif line.startswith('🟢'):
                if current_section == 'successes':
                    successes.append(line)
        
        # Fallback if parsing failed
        if not insights:
            if calories < targets.get('calories', 2000) - 200:
                insights.append({
                    'type': 'warning',
                    'icon': '⚠️',
                    'title': 'Calorieën te laag',
                    'message': f"Je gemiddelde van {calories:.0f} kcal is te laag. Verhoog naar {targets.get('calories', 2000)} voor optimaal resultaat."
                })
            if protein < targets.get('protein', 160):
                insights.append({
                    'type': 'warning',
                    'icon': '⚠️',
                    'title': 'Eiwit te laag',
                    'message': f"Slechts {protein:.0f}g eiwit. Verhoog naar {targets.get('protein', 160)}g+ voor spierbehoud."
                })
        
        if not improvements:
            improvements = [
                f"🔴 Te weinig calorieën: {calories:.0f} kcal is te laag" if calories < 1900 else f"🟡 Eiwit te laag: {protein:.0f}g (doel: {targets.get('protein', 160)}g)",
                "🟡 Voeg meer groenten toe bij elke maaltijd"
            ]
        
        if not successes:
            successes = [
                "🟢 Consistente training en data bijhouden",
                "🟢 Goede discipline in tracking"
            ]
        
        return {
            'insights': insights[:3],  # Max 3
            'improvements': improvements[:4],  # Max 4
            'successes': successes[:4]  # Max 4
        }
        
    except Exception as e:
        # Fallback to basic feedback
        return {
            'insights': [{
                'type': 'info',
                'icon': '💡',
                'title': 'Blijf tracken',
                'message': 'Consistentie is key voor succes!'
            }],
            'improvements': [
                f"🟡 Eiwit verhogen naar {targets.get('protein', 160)}g",
                "🟡 Drink 2-3L water per dag"
            ],
            'successes': [
                "🟢 Data wordt bijgehouden",
                "🟢 Training is consistent"
            ]
        }


def generate_measurement_warning(vet_change, spier_change, current_nutrition, targets, name):
    """
    Genereer AI-powered waarschuwing wanneer vetpercentage stijgt en spiermassa daalt
    
    Args:
        vet_change: Verandering in vetpercentage (positief = gestegen)
        spier_change: Verandering in spiermassa kg (negatief = gedaald)
        current_nutrition: Dict met huidige voeding totals
        targets: Dict met doelen
        name: Naam gebruiker
        
    Returns:
        HTML formatted warning message
    """
    try:
        client = get_groq_client()
        
        calories = current_nutrition.get('calorien', 0)
        protein = current_nutrition.get('eiwit', 0)
        
        context = f"""⚠️ URGENT: {name} verliest spiermassa in plaats van vet!

METINGEN ANALYSE:
- Vetpercentage: +{vet_change:.1f}% (GESTEGEN)
- Spiermassa: {spier_change:.1f} kg (GEDAALD)

HUIDIGE VOEDING:
- Calorieën: {calories:.0f}/{targets.get('calories', 2000)} kcal ({(calories/targets.get('calories', 2000)*100):.0f}%)
- Eiwit: {protein:.0f}/{targets.get('protein', 160)}g ({(protein/targets.get('protein', 160)*100):.0f}%)

Genereer een URGENTE waarschuwing in HTML format:

<h3 style="margin: 0 0 15px 0;">⚠️ [Pakkende titel]</h3>
<p style="margin: 8px 0;"><strong>Vetpercentage gestegen:</strong> +{vet_change:.1f}%</p>
<p style="margin: 8px 0;"><strong>Spiermassa gedaald:</strong> {spier_change:.1f} kg</p>
<p style="margin: 15px 0 0 0; opacity: 0.9;"><strong>Conclusie:</strong> [Concrete diagnose en oplossing - max 2 zinnen]</p>

Wees direct, urgent maar constructief. Noem exacte cijfers en acties."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Je bent een directe fitness coach die urgente maar constructieve waarschuwingen geeft in HTML format."},
                {"role": "user", "content": context}
            ],
            temperature=0.7,
            max_tokens=250
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        # Fallback to simple warning
        return f"""
        <h3 style="margin: 0 0 15px 0;">⚠️ Belangrijke Waarschuwing!</h3>
        <p style="margin: 8px 0;"><strong>Vetpercentage gestegen:</strong> +{vet_change:.1f}%</p>
        <p style="margin: 8px 0;"><strong>Spiermassa gedaald:</strong> {spier_change:.1f} kg</p>
        <p style="margin: 15px 0 0 0; opacity: 0.9;"><strong>Conclusie:</strong> Je verliest spier in plaats van vet! Verhoog je calorieën naar {targets.get('calories', 2000)} en eiwit naar {targets.get('protein', 160)}g.</p>
        """

