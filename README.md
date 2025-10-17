# 💪 Sport & Fitness Dashboard

Een persoonlijke fitness tracking dashboard gebouwd met Streamlit, AI-powered voeding analyse, en Google Sheets integratie.

## ✨ Features

- 📊 **Overzicht Dashboard**: Volg je dagelijkse voeding, cardio, en kracht training
- 🍽️ **AI Voeding Analyse**: Typ wat je hebt gegeten, AI berekent automatisch macros
- 💪 **Kracht Training**: Log je workouts met gewichten, sets, en reps
- 🏃 **Cardio Tracking**: Volg hardlopen, fietsen, en andere cardio activiteiten
- 📈 **Progressie Grafieken**: Visualiseer je vooruitgang over tijd
- 👟 **Stappen Counter**: Dagelijkse stappen tracking
- ⚖️ **Gewicht Tracking**: Monitor je gewicht over tijd
- 🔐 **Multi-user**: Secure login voor meerdere gebruikers

## 🚀 Quick Start

### Lokale Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/JOUW_USERNAME/sport-dashboard.git
   cd sport-dashboard
   ```

2. **Installeer dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Configureer environment**
   ```bash
   # Kopieer .env.example naar .env
   cp .env.example .env
   
   # Bewerk .env en vul je API keys in
   ```

4. **Setup Google Sheets**
   - Maak een Google Sheet met deze tabs: `voeding`, `activiteiten`, `metingen`, `egym`, `stappen`, `gewicht`
   - Volg [deze guide](DEPLOYMENT.md#google-sheets-setup) voor service account setup
   - Download `credentials.json` en plaats in project root

5. **Configureer wachtwoorden**
   ```bash
   # Bewerk generate_passwords.py met je gewenste wachtwoorden
   python generate_passwords.py
   
   # Kopieer de output naar config.yaml
   ```

6. **Start dashboard**
   ```bash
   streamlit run dashboard.py
   ```

## ☁️ Deployment naar Streamlit Cloud

Voor gedetailleerde deployment instructies, zie [DEPLOYMENT.md](DEPLOYMENT.md).

**Quick steps:**
1. Push naar GitHub (private repo)
2. Ga naar [share.streamlit.io](https://share.streamlit.io)
3. Connect je repository
4. Voeg secrets toe in Advanced Settings
5. Deploy! 🎉

## 🔧 Technologie Stack

- **Frontend**: Streamlit 1.50+
- **AI**: Groq (Llama 3.3 70B) voor voeding analyse
- **Database**: Google Sheets (gspread)
- **Visualisatie**: Plotly
- **Auth**: streamlit-authenticator

## 📝 Configuratie

### Environment Variables (.env)
```bash
GROQ_API_KEY=your_groq_api_key
SHEET_ID=your_google_sheet_id
GOOGLE_CREDENTIALS_PATH=credentials.json
```

### User Credentials (config.yaml)
```yaml
credentials:
  usernames:
    alex:
      name: Alex
      password: hashed_password_here
```

## 🎯 Features in Detail

### AI Voeding Analyse
Type natuurlijke taal zoals:
- "250g kwark, banaan, 2 eetlepels lijnzaad"
- "Kip met rijst en broccoli"
- "Pizza margherita, groot"

De AI berekent automatisch:
- Calorieën
- Eiwit, koolhydraten, vetten
- Vezels

### Kracht Training Logging
Beschrijf je workout:
- "Bench press 80kg 4x8"
- "Squats 100kg 5 sets 5 reps"

### Multi-User Support
Elk account heeft:
- Eigen login credentials
- Toegang tot dezelfde Google Sheet (of eigen sheet)
- Persoonlijk welkom bericht

## 📊 Google Sheets Structuur

Voorbeeld sheet structuur:

**voeding**:
| datum | maaltijd | omschrijving | calorien | eiwit | koolhydraten | vetten | vezels |
|-------|----------|--------------|----------|-------|--------------|--------|--------|

**activiteiten**:
| datum | activiteit | type | gewicht | afstand | duur | sets | reps | methode |
|-------|------------|------|---------|---------|------|------|------|---------|

**stappen**:
| datum | stappen | cardio |
|-------|---------|--------|

**gewicht**:
| datum | gewicht |
|-------|---------|

## 🔒 Security

- ⚠️ **Nooit** commit `.env` of `credentials.json` naar Git
- ⚠️ Gebruik sterke wachtwoorden in productie
- ✅ Google Sheet credentials zijn encrypted
- ✅ Wachtwoorden worden gehashed met bcrypt
- ✅ Cookie-based sessie management

## 🤝 Contributing

Dit is een persoonlijk project, maar suggesties zijn welkom!

## 📄 License

MIT License - gebruik vrij voor persoonlijke projecten

## 🙏 Credits

Gebouwd met:
- [Streamlit](https://streamlit.io)
- [Groq](https://groq.com) (Llama 3.3 70B)
- [Plotly](https://plotly.com)
- [gspread](https://gspread.readthedocs.io)

---

**Gemaakt met ❤️ voor een gezonde lifestyle** 💪🏃‍♂️🥗
