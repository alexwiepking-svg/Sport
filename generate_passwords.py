"""
Script om wachtwoord hashes te genereren voor config.yaml
Voer dit uit en kopieer de output naar config.yaml
"""
import bcrypt

print("\n=== Wachtwoord Hash Generator ===\n")
print("Dit script genereert veilige hashes voor je wachtwoorden.")
print("Kopieer de output naar config.yaml\n")

# Genereer hashes voor beide gebruikers
# VERANDER DEZE WACHTWOORDEN VOORDAT JE HET SCRIPT UITVOERT!
passwords_to_hash = {
    'alex': 'sport2025',  # Demo wachtwoord - VERANDER DIT!
    'partner': 'fitness2025'  # Demo wachtwoord - VERANDER DIT!
}

print("⚠️  BELANGRIJK: Verander eerst de wachtwoorden in dit bestand!\n")
print("Gegenereerde hashes:\n")

for username, password in passwords_to_hash.items():
    # Genereer bcrypt hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    print(f"{username}:")
    print(f"  password: {hashed.decode('utf-8')}\n")

print("\n📋 Kopieer deze hashes naar config.yaml onder credentials -> usernames")
print("💡 TIP: Kies sterke wachtwoorden voor productie gebruik!")
