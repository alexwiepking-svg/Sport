# 🎯 Deployment Checklist

## ✅ Voorbereiding Compleet!

### Wat is VEILIG (niet in Git):
- ✅ `.env` - Je echte API keys
- ✅ `credentials.json` - Google service account
- ✅ `config.yaml` - Je echte wachtwoorden
- ✅ `.venv/` - Virtual environment
- ✅ `__pycache__/` - Python cache

### Wat WEL in Git gaat:
- ✅ `dashboard.py` - Hoofdapplicatie
- ✅ `groq_helper.py` - AI helper
- ✅ `sheets_helper.py` - Google Sheets helper
- ✅ `requirements.txt` - Dependencies
- ✅ `.env.example` - Voorbeeld config (zonder secrets)
- ✅ `config.yaml.example` - Voorbeeld credentials (zonder echte passwords)
- ✅ `generate_passwords.py` - Password hash generator
- ✅ `README.md` - Documentatie
- ✅ `DEPLOYMENT.md` - Deployment instructies
- ✅ `.gitignore` - Git ignore rules

## 🚀 Volgende Stappen

### 1. Git Setup (Lokaal)
```bash
git add .
git commit -m "Initial commit: Sport Dashboard with authentication"
```

### 2. GitHub Repository
1. Ga naar https://github.com/new
2. Repository naam: `sport-dashboard`
3. **Belangrijk**: Maak het **PRIVATE** (voor je privacy)
4. GEEN README, .gitignore of license toevoegen (hebben we al)

### 3. Push naar GitHub
```bash
git remote add origin https://github.com/JOUW_USERNAME/sport-dashboard.git
git branch -M main
git push -u origin main
```

### 4. Deploy naar Streamlit Cloud
1. Ga naar https://share.streamlit.io
2. Klik "New app"
3. Connect je GitHub account
4. Selecteer:
   - Repository: `sport-dashboard`
   - Branch: `main`
   - Main file path: `dashboard.py`

### 5. Voeg Secrets toe in Streamlit Cloud

Klik "Advanced settings" → "Secrets" en plak:

```toml
# Groq API
GROQ_API_KEY = "your-groq-api-key-here"

# Google Sheets
SHEET_ID = "your-google-sheet-id-here"

# Google Service Account
# Open credentials.json en plak HELE inhoud hieronder als TOML format:
[gcp_service_account]
type = "service_account"
project_id = "prefab-grid-467519-e1"
private_key_id = "KOPIEER_UIT_CREDENTIALS_JSON"
private_key = "-----BEGIN PRIVATE KEY-----\nKOPIEER_UIT_CREDENTIALS_JSON\n-----END PRIVATE KEY-----\n"
client_email = "sporttracker@prefab-grid-467519-e1.iam.gserviceaccount.com"
client_id = "KOPIEER_UIT_CREDENTIALS_JSON"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "KOPIEER_UIT_CREDENTIALS_JSON"
universe_domain = "googleapis.com"
```

### 6. Deploy!
Klik "Deploy" en wacht 2-3 minuten.

## 📱 Toegang

Na deployment:
- URL: `https://sport-dashboard-RANDOM.streamlit.app`
- Login: `alex` / `sport2025`
- Login: `partner` / `fitness2025`

### Telefoon Setup
1. Open de URL in je browser
2. Log in
3. iOS: Klik Share → "Add to Home Screen"
4. Android: Menu → "Add to Home screen"

Nu heb je een app icon! 📱💪

## 🔐 Security Tips

1. **Verander wachtwoorden** voor productie:
   - Bewerk `generate_passwords.py`
   - Run het script
   - Update `config.yaml` lokaal

2. **Update Streamlit Cloud secrets** als je iets verandert:
   - Ga naar app settings
   - Edit secrets
   - Save

3. **Google Sheet privacy**:
   - Alleen service account heeft toegang
   - Share niet publiekelijk

## 🆘 Hulp Nodig?

**App start niet:**
- Check Streamlit Cloud logs
- Verify alle secrets zijn correct
- Check of alle dependencies in requirements.txt staan

**Login werkt niet:**
- Verify config.yaml is correct geüpload (via secrets)
- Check wachtwoord hashes

**Google Sheets error:**
- Verify service account heeft Editor rechten
- Check of SHEET_ID correct is

**Groq API error:**
- Check of API key geldig is
- Verify rate limits (14,400 requests/dag gratis)

## 🎉 Klaar!

Je app is nu:
- ✅ Veilig (private repo, secrets apart)
- ✅ Online (Streamlit Cloud)
- ✅ Multi-user (login voor 2 personen)
- ✅ Mobiel (responsive design)
- ✅ Gratis (Streamlit Cloud free tier)

Veel plezier met tracken! 💪🏃‍♂️🥗
