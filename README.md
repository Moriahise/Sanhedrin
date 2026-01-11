# 📚 Beit Din Gadol Sanhedrin - Responsa Archiv

Automatisiertes Archiv-System für halachische Teshuvot (Responsa) mit GitHub Actions Integration.

## ✨ Features

- 🔄 **Automatisches Update**: Bei jedem Upload neuer Dateien wird `responsa.json` automatisch aktualisiert
- 🌐 **Zweisprachig**: Hebräisch (RTL) und Englisch
- 🔍 **Suche & Filter**: Nach Kategorie, Jahr und Freitext
- 📱 **Responsiv**: Funktioniert auf Desktop und Mobile
- 🎨 **Schönes Design**: Elegantes Gold-Blau Theme

## 📁 Projektstruktur

```
responsa-archive/
├── .github/
│   └── workflows/
│       └── update-responsa.yml    # GitHub Actions Workflow
├── responsa/                      # Hier Dateien hinzufügen!
│   ├── 2025/                      # Nach Jahr organisiert
│   │   ├── dokument1.html
│   │   ├── dokument2.html
│   │   └── dokument3.pdf
│   └── 2024/
│       └── ...
├── index.html                     # Hauptseite
├── script.js                      # JavaScript Funktionalität
├── styles.css                     # Styling
├── responsa.json                  # Auto-generierte Datenbank
└── update_responsa.py             # Update-Script
```

## 🚀 Setup & Verwendung

### 1. GitHub Repository Setup

1. **Repository erstellen** auf GitHub
2. **Dateien hochladen**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/DEIN-USERNAME/responsa-archive.git
   git push -u origin main
   ```

3. **GitHub Actions aktivieren**:
   - Gehe zu `Settings` → `Actions` → `General`
   - Unter "Workflow permissions":
     - ✅ Wähle "Read and write permissions"
     - ✅ Aktiviere "Allow GitHub Actions to create and approve pull requests"
   - Speichern!

### 2. GitHub Pages aktivieren (Optional - für Website)

1. Gehe zu `Settings` → `Pages`
2. Source: "Deploy from a branch"
3. Branch: `main` / Folder: `/ (root)`
4. Speichern!

Deine Website ist dann verfügbar unter:
`https://DEIN-USERNAME.github.io/responsa-archive/`

### 3. Neue Responsa hinzufügen

**Methode 1: Über GitHub Website** (einfachste Methode)
1. Gehe zu deinem Repository auf GitHub
2. Navigiere zu `responsa/2025/` (oder erstelle einen neuen Jahres-Ordner)
3. Klicke "Add file" → "Upload files"
4. Ziehe deine HTML/PDF-Dateien rein
5. Klicke "Commit changes"
6. ✅ **AUTOMATISCH**: GitHub Actions läuft und aktualisiert `responsa.json`!

**Methode 2: Über Git Command Line**
```bash
# Neue Datei hinzufügen
cp meine-neue-teshuvah.html responsa/2025/

# Commit und Push
git add responsa/2025/meine-neue-teshuvah.html
git commit -m "Neue Teshuvah hinzugefügt"
git push

# ✅ AUTOMATISCH: GitHub Actions aktualisiert responsa.json!
```

### 4. Workflow manuell starten

Du kannst den Update-Prozess auch manuell triggern:
1. Gehe zu "Actions" Tab im Repository
2. Wähle "Update responsa.json"
3. Klicke "Run workflow"

## 🛠️ Lokales Testen

### Voraussetzungen
- Python 3.7+
- Einen lokalen Webserver

### Installation
```bash
# Python Dependencies installieren
pip install beautifulsoup4 lxml

# Update-Script lokal testen
python3 update_responsa.py
```

### Lokalen Webserver starten
```bash
# Mit Python
python3 -m http.server 8000

# Oder mit Node.js
npx http-server

# Dann öffne: http://localhost:8000
```

## 📝 Dateiformat-Anforderungen

### HTML-Dateien
- **Titel**: Aus `<title>` Tag extrahiert
- **Zusammenfassung**: Erste ~50 Wörter des Inhalts
- **Datum**: Datei-Modifikationszeit

### PDF-Dateien
- **Titel**: Aus Dateinamen
- **Zusammenfassung**: (leer)
- **Datum**: Datei-Modifikationszeit

## 🎯 Kategorien

Folgende Kategorien werden unterstützt:
- `ritual` - הלכות עבודה / Ritual Law
- `civil` - דיני ממונות / Civil Law
- `family` - דיני משפחה / Family Law
- `kashrut` - כשרות / Kashrut
- `shabbat` - שבת וחגים / Shabbat & Holidays
- `conversion` - גיור / Conversion
- `halacha-history` - הלכה – תולדות / Halacha – History
- `other` - אחר / Other

**Hinweis**: Neue Dateien erhalten automatisch Kategorie `other`. 
Du kannst die Kategorien in `responsa.json` manuell bearbeiten.

## 🔧 Erweiterte Konfiguration

### Kategorien anpassen
Bearbeite `responsa.json` manuell:
```json
{
    "number": 1,
    "category": "kashrut",          // Kategorie-ID ändern
    "category_he": "כשרות",         // Hebräischer Name
    "category_en": "Kashrut",       // Englischer Name
    ...
}
```

### Titel/Zusammenfassung anpassen
Bearbeite `responsa.json` manuell:
```json
{
    "number": 1,
    "title_he": "Dein hebräischer Titel",
    "title_en": "Your English Title",
    "summary_he": "Hebräische Zusammenfassung...",
    "summary_en": "English summary...",
    ...
}
```

## 🐛 Troubleshooting

### Workflow läuft nicht
- ✅ Prüfe "Workflow permissions" in Settings → Actions → General
- ✅ Stelle sicher, dass "Read and write permissions" aktiviert ist

### responsa.json wird nicht aktualisiert
1. Gehe zu "Actions" Tab
2. Klicke auf den letzten Workflow-Lauf
3. Prüfe die Logs auf Fehler

### Website zeigt keine Daten
- ✅ Prüfe ob `responsa.json` korrekt formatiert ist (JSON Validator)
- ✅ Öffne Browser-Konsole (F12) und prüfe auf JavaScript-Fehler
- ✅ Stelle sicher, dass der Dateipfad in `responsa.json` korrekt ist

### Python Script Fehler
```bash
# Debug-Modus
python3 -u update_responsa.py

# Prüfe Python-Version
python3 --version  # Sollte 3.7+ sein

# Dependencies neu installieren
pip install --upgrade beautifulsoup4 lxml
```

## 📊 Workflow Details

Der GitHub Actions Workflow macht folgendes:

1. ✅ **Checkout** - Repository herunterladen
2. ✅ **Python Setup** - Python 3.11 installieren
3. ✅ **Dependencies** - BeautifulSoup4 + lxml installieren
4. ✅ **Update Script** - `update_responsa.py` ausführen
5. ✅ **Check Changes** - Prüfen ob `responsa.json` geändert wurde
6. ✅ **Commit & Push** - Änderungen automatisch committen (falls vorhanden)
7. ✅ **Summary** - Ergebnis im Actions-Tab anzeigen

## 📄 Lizenz

Alle Rechte vorbehalten © 2025 Beit Din Gadol Sanhedrin

## 💡 Support

Bei Problemen:
1. Prüfe die [Actions Tab](../../actions) für Workflow-Logs
2. Öffne ein Issue im Repository
3. Konsultiere die Troubleshooting-Sektion oben

---

**Viel Erfolg mit dem Responsa-Archiv! 📚✨**
