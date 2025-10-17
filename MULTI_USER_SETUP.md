# 👥 Multi-User Setup Instructies

De app ondersteunt nu meerdere gebruikers, elk met hun eigen Google Sheet!

## ✅ Wat is al gedaan:

- ✅ Code aangepast voor per-user sheets
- ✅ Alex gebruikt: `SHEET_ID_ALEX` 
- ✅ Partner (Tamara) gebruikt: `SHEET_ID_PARTNER`
- ✅ Automatische sheet selectie op basis van ingelogde gebruiker

## 📋 Setup voor Tweede Gebruiker (Tamara)

### Stap 1: Kopieer Google Sheet Structuur

1. **Open je huidige Google Sheet** (Alex's sheet)
2. **Maak een kopie**:
   - Bestand → Kopie maken
   - Naam: "Sport Tracker - Tamara" 
3. **Noteer de nieuwe Sheet ID**:
   - URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
   - Kopieer het SHEET_ID gedeelte

### Stap 2: Share met Service Account

1. **Klik "Delen"** in de nieuwe sheet
2. **Voeg toe**: `sporttracker@prefab-grid-467519-e1.iam.gserviceaccount.com`
3. **Rechten**: Editor ✅
4. **Verstuur** (notificatie uitzetten is OK)

### Stap 3: Update .env Bestand

Bewerk je `.env` bestand:

```bash
# Groq API Key
GROQ_API_KEY=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

# Google Sheets - Per User
SHEET_ID_ALEX=1nWiAZCG3ZKvVOX50ZlW9z3elubHDERpCFXpcDYxJUE8
SHEET_ID_PARTNER=NIEUWE_SHEET_ID_HIER_PLAKKEN
GOOGLE_CREDENTIALS_PATH=credentials.json
```

### Stap 4: Verwijder oude sheet data (optioneel)

Als je wilt dat Tamara met een lege sheet begint:

1. Open Tamara's sheet
2. Selecteer alle data rijen (NIET de headers!)
3. Delete

Of laat de sample data staan voor demonstratie.

### Stap 5: Test!

1. **Herstart dashboard** (stop + start de app)
2. **Login als alex** → Ziet Alex's data
3. **Logout** (sidebar)
4. **Login als partner** → Ziet Tamara's data

## 🔐 Gebruikers Configuratie

Elke gebruiker heeft:

| Username | Password | Naam | Sheet |
|----------|----------|------|-------|
| alex | sport2025 | Alex Wiepking | SHEET_ID_ALEX |
| partner | fitness2025 | Partner | SHEET_ID_PARTNER |

**Tip**: Verander wachtwoorden met `generate_passwords.py` voor productie!

## ☁️ Streamlit Cloud Deployment

Bij deployment naar Streamlit Cloud, voeg toe aan Secrets:

```toml
# Groq API
GROQ_API_KEY = "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"

# Google Sheets - Per User
SHEET_ID_ALEX = "1nWiAZCG3ZKvVOX50ZlW9z3elubHDERpCFXpcDYxJUE8"
SHEET_ID_PARTNER = "TAMARA_SHEET_ID_HIER"

# Google Service Account (zelfde voor beide users)
[gcp_service_account]
type = "service_account"
project_id = "prefab-grid-467519-e1"
# ... rest van credentials.json ...
```

## ➕ Meer Gebruikers Toevoegen

Wil je later meer gebruikers toevoegen? Volg deze stappen:

### 1. Voeg gebruiker toe aan config.yaml

```yaml
credentials:
  usernames:
    alex:
      email: alex@example.com
      name: Alex
      password: $2b$12$...
    partner:
      email: partner@example.com
      name: Tamara
      password: $2b$12$...
    nieuwe_user:
      email: nieuwe@example.com
      name: Nieuwe Gebruiker
      password: $2b$12$...  # Genereer met generate_passwords.py
```

### 2. Voeg Sheet ID toe aan .env

```bash
SHEET_ID_ALEX=...
SHEET_ID_PARTNER=...
SHEET_ID_NIEUWE_USER=...  # Nieuwe sheet ID
```

### 3. Update code in dashboard.py

Zoek naar `SHEET_MAPPING` (rond regel 75):

```python
SHEET_MAPPING = {
    'alex': os.getenv('SHEET_ID_ALEX'),
    'partner': os.getenv('SHEET_ID_PARTNER'),
    'nieuwe_user': os.getenv('SHEET_ID_NIEUWE_USER')  # Toevoegen
}
```

### 4. Maak nieuwe Google Sheet en share met service account

Volg Stap 1-2 hierboven.

## 🎯 Voordelen Multi-User Setup

✅ **Privacy**: Elke gebruiker ziet alleen zijn/haar eigen data  
✅ **Eigen doelen**: Iedereen kan eigen targets instellen  
✅ **Onafhankelijk**: Data wordt niet vermengd  
✅ **Schaalbaar**: Makkelijk meer gebruikers toevoegen  
✅ **Veilig**: Login vereist, encrypted cookies  

## ❓ Troubleshooting

**"Geen Google Sheet geconfigureerd voor gebruiker 'partner'"**
- Check of SHEET_ID_PARTNER in .env staat
- Restart de app

**Partner ziet Alex's data**
- Check of SHEET_MAPPING correct is (dashboard.py regel ~75)
- Check of je ingelogd bent als de juiste gebruiker

**403 Forbidden Error**
- Service account heeft geen toegang tot de sheet
- Share de sheet met Editor rechten

**Data wordt niet opgeslagen**
- Check of beide sheets de juiste tab names hebben:
  - voeding, activiteiten, metingen, egym, stappen, gewicht
- Check of service account Editor rechten heeft (niet alleen Viewer!)

## 📞 Support

Vragen? Check:
- `README.md` - Algemene documentatie
- `DEPLOYMENT.md` - Deployment instructies
- `DEPLOYMENT_CHECKLIST.md` - Stap-voor-stap checklist

---

**Multi-user setup compleet!** 🎉 Beide gebruikers kunnen nu onafhankelijk hun fitness tracken! 💪
