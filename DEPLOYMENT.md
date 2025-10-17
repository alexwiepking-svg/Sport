# 🚀 Deployment Instructies - Streamlit Community Cloud

## Voorbereiding

### 1. Installeer streamlit-authenticator
```bash
.\.venv\Scripts\pip install streamlit-authenticator
```

### 2. Genereer wachtwoord hashes
```bash
# Bewerk eerst generate_passwords.py en voer uit:
.\.venv\Scripts\python generate_passwords.py
# Kopieer de output naar config.yaml
```

### 3. Maak GitHub repository
1. Ga naar https://github.com/new
2. Maak een **private** repository (naam: sport-dashboard)
3. Push je code:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/JOUW_USERNAME/sport-dashboard.git
git push -u origin main
```

## Deployment naar Streamlit Cloud

### 4. Deploy op Streamlit Community Cloud
1. Ga naar https://share.streamlit.io
2. Klik "New app"
3. Connect je GitHub account
4. Selecteer:
   - Repository: `sport-dashboard`
   - Branch: `main`
   - Main file: `dashboard.py`

### 5. Voeg secrets toe
Klik op "Advanced settings" → "Secrets" en voeg toe:

```toml
# Groq API
GROQ_API_KEY = "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"

# Google Sheets
SHEET_ID = "1nWiAZCG3ZKvVOX50ZlW9z3elubHDERpCFXpcDYxJUE8"

# Google Service Account (hele JSON hier plakken)
[gcp_service_account]
type = "service_account"
project_id = "prefab-grid-467519-e1"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "sporttracker@prefab-grid-467519-e1.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

### 6. Klik "Deploy!"

## Multi-User Setup (Per gebruiker eigen Google Sheet)

Voor aparte sheets per gebruiker:

1. **Maak een tweede Google Sheet** voor je partner
2. **Share met service account** (sporttracker@...)
3. **Voeg Sheet ID toe aan secrets**:
```toml
SHEET_ID_ALEX = "1nWiAZCG3ZKvVOX50ZlW9z3elubHDERpCFXpcDYxJUE8"
SHEET_ID_PARTNER = "nieuwe_sheet_id_hier"
```

4. **Pas dashboard.py aan** om de juiste sheet te laden per gebruiker (komt later)

## Toegang via Telefoon

Zodra deployed:
1. Ga naar de URL: `https://jouw-app-naam.streamlit.app`
2. Log in met username/password
3. Voeg toe aan home screen (iOS: Share → Add to Home Screen)

## Troubleshooting

**Foutmelding "Module not found":**
- Check of alle packages in `requirements.txt` staan

**Authenticatie werkt niet:**
- Check of `config.yaml` correct is
- Check of wachtwoord hashes gegenereerd zijn

**Google Sheets connection failed:**
- Check of service account JSON compleet is in secrets
- Check of service account Editor rechten heeft op sheet

**App is traag:**
- Streamlit Cloud free tier heeft beperkte resources
- Overweeg caching optimalisaties
