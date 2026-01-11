# 🚀 SCHNELLSTART - Responsa Archiv

## 📋 Schritt-für-Schritt Anleitung

### 1️⃣ GitHub Repository erstellen

1. Gehe zu https://github.com/new
2. Repository Name: `responsa-archive` (oder beliebiger Name)
3. Visibility: Public oder Private
4. ✅ Klicke "Create repository"

### 2️⃣ Code hochladen

**Option A: GitHub Desktop (empfohlen für Anfänger)**
```
1. Downloade GitHub Desktop: https://desktop.github.com/
2. Installiere und melde dich an
3. Klicke "Add" → "Add Existing Repository"
4. Wähle den responsa-archive Ordner
5. Klicke "Publish repository"
```

**Option B: Command Line**
```bash
cd /pfad/zum/responsa-archive
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/DEIN-USERNAME/responsa-archive.git
git push -u origin main
```

### 3️⃣ GitHub Actions konfigurieren

**WICHTIG - Sonst funktioniert die Automatik nicht!**

1. Gehe zu deinem Repository auf GitHub
2. Klicke auf `Settings` (oben rechts)
3. Klicke auf `Actions` → `General` (linke Sidebar)
4. Scrolle runter zu "Workflow permissions"
5. ✅ Wähle: **"Read and write permissions"**
6. ✅ Aktiviere: **"Allow GitHub Actions to create and approve pull requests"**
7. Klicke **"Save"**

### 4️⃣ GitHub Pages aktivieren (für Website)

1. Noch in Settings, klicke auf `Pages` (linke Sidebar)
2. Source: **"Deploy from a branch"**
3. Branch: **main** / Folder: **/ (root)**
4. Klicke **"Save"**

⏱️ Warte 1-2 Minuten...

🎉 **Deine Website ist jetzt live unter:**
```
https://DEIN-USERNAME.github.io/responsa-archive/
```

### 5️⃣ Neue Responsa hinzufügen

**Einfachste Methode - über GitHub Website:**

1. Gehe zu deinem Repository: `https://github.com/DEIN-USERNAME/responsa-archive`
2. Klicke auf den Ordner `responsa`
3. Klicke auf den Ordner `2025` (oder erstelle einen neuen mit "Add file" → "Create new file" → `2026/README.md`)
4. Klicke **"Add file"** → **"Upload files"**
5. Ziehe deine HTML/PDF-Dateien in das Fenster
6. Gib eine Commit-Nachricht ein: z.B. "Neue Teshuvah hinzugefügt"
7. Klicke **"Commit changes"**

### 🤖 Was passiert jetzt automatisch?

1. ✅ GitHub Actions erkennt die neuen Dateien
2. ✅ Das Update-Script läuft automatisch
3. ✅ `responsa.json` wird aktualisiert
4. ✅ Die Website zeigt die neuen Einträge

**Prüfen ob es funktioniert hat:**
- Gehe zu "Actions" Tab im Repository
- Dort solltest du einen grünen Haken ✅ sehen
- Klicke drauf für Details

### 🧪 Lokal testen (optional)

```bash
# 1. Python installieren (falls nicht vorhanden)
# Download: https://www.python.org/downloads/

# 2. Dependencies installieren
pip install beautifulsoup4 lxml

# 3. Test-Script ausführen
python3 test_local.py

# Das Script wird:
# - Test-Dateien erstellen
# - responsa.json updaten
# - Einen lokalen Webserver starten
# - Deinen Browser öffnen
```

---

## 🔥 Wichtigste Befehle

### Neue Datei per Command Line hinzufügen:
```bash
# 1. Datei in responsa/2025/ kopieren
cp meine-neue-teshuvah.html responsa/2025/

# 2. Commit und push
git add responsa/2025/meine-neue-teshuvah.html
git commit -m "Neue Teshuvah: meine-neue-teshuvah"
git push
```

### Manuell responsa.json neu generieren:
```bash
python3 update_responsa.py
```

### Workflow manuell starten:
1. Gehe zu "Actions" Tab
2. Wähle "Update responsa.json"
3. Klicke "Run workflow"

---

## ❓ Häufige Probleme

### ❌ "Action failed" - Workflow schlägt fehl
**Lösung:** Prüfe ob "Read and write permissions" aktiviert ist (siehe Schritt 3)

### ❌ responsa.json wird nicht aktualisiert
**Lösung:** 
1. Gehe zu Actions Tab
2. Klicke auf den fehlgeschlagenen Workflow
3. Lese die Fehler-Logs
4. Meistens: Berechtigungen fehlen (siehe Schritt 3)

### ❌ Website zeigt keine Daten
**Lösung:**
1. Öffne Browser-Konsole (F12)
2. Prüfe auf JavaScript-Fehler
3. Stelle sicher dass `responsa.json` existiert
4. Prüfe ob die Dateipfade korrekt sind

### ❌ Python-Fehler beim lokalen Test
**Lösung:**
```bash
# Python-Version prüfen (sollte 3.7+ sein)
python3 --version

# Dependencies neu installieren
pip install --upgrade beautifulsoup4 lxml
```

---

## 📞 Support

**Bei Problemen:**
1. Lese die ausführliche [README.md](README.md)
2. Prüfe die [Actions Logs](../../actions) auf GitHub
3. Öffne ein Issue im Repository

---

## ✅ Checkliste

- [ ] Repository auf GitHub erstellt
- [ ] Code hochgeladen (alle Dateien)
- [ ] "Read and write permissions" aktiviert
- [ ] GitHub Pages aktiviert
- [ ] Erste Test-Datei hochgeladen
- [ ] Workflow läuft erfolgreich (grüner Haken)
- [ ] Website ist erreichbar
- [ ] Neue Einträge werden angezeigt

**Wenn alle Punkte ✅ sind: Gratulation! 🎉**

---

**Viel Erfolg! 📚✨**
