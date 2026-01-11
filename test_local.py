#!/usr/bin/env python3
"""
Test-Script für lokale Entwicklung

Dieses Script:
1. Erstellt Test-HTML-Dateien im responsa-Ordner
2. Führt update_responsa.py aus
3. Startet einen lokalen Webserver
4. Öffnet die Website im Browser

Verwendung:
    python3 test_local.py
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

# ANSI Farben
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ️  {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def create_test_files():
    """Erstellt Test-HTML-Dateien"""
    print_header("Erstelle Test-Dateien")
    
    root = Path(__file__).parent
    test_dir = root / "responsa" / "2025"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Test-HTML erstellen
    test_html = test_dir / "test-teshuvah-1.html"
    if not test_html.exists():
        content = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>שאלה לדוגמה - הלכות שבת</title>
</head>
<body>
    <h1>שאלה לדוגמה - הלכות שבת</h1>
    <p>
        זוהי שאלה לדוגמה בנושא הלכות שבת. התוכן כאן משמש להדגמה בלבד.
        השאלה עוסקת בנושא מסוים בהלכה ומביאה מקורות שונים מהגמרא והראשונים.
        הפסק נותן הכרעה ברורה בנושא זה על פי השיטות השונות.
    </p>
</body>
</html>"""
        test_html.write_text(content, encoding='utf-8')
        print_success(f"Test-Datei erstellt: {test_html.name}")
    else:
        print_info(f"Test-Datei existiert bereits: {test_html.name}")

def run_update_script():
    """Führt update_responsa.py aus"""
    print_header("Führe update_responsa.py aus")
    
    try:
        result = subprocess.run(
            [sys.executable, "update_responsa.py"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print_success("Update-Script erfolgreich ausgeführt")
            return True
        else:
            print_error("Update-Script fehlgeschlagen")
            return False
    except Exception as e:
        print_error(f"Fehler beim Ausführen: {e}")
        return False

def start_webserver():
    """Startet lokalen Webserver"""
    print_header("Starte Webserver")
    
    port = 8000
    print_info(f"Starte Server auf Port {port}...")
    print_info("Drücke Ctrl+C zum Beenden")
    print_info(f"Website öffnet sich automatisch...")
    
    time.sleep(2)
    webbrowser.open(f'http://localhost:{port}')
    
    try:
        subprocess.run([
            sys.executable, '-m', 'http.server', str(port)
        ])
    except KeyboardInterrupt:
        print_info("\nServer gestoppt")

def main():
    print_header("Responsa Archive - Lokaler Test")
    
    # Prüfe ob wir im richtigen Verzeichnis sind
    if not Path('update_responsa.py').exists():
        print_error("update_responsa.py nicht gefunden!")
        print_info("Bitte führe dieses Script im Projekt-Root aus")
        sys.exit(1)
    
    # 1. Test-Dateien erstellen
    create_test_files()
    
    # 2. Update-Script ausführen
    if not run_update_script():
        sys.exit(1)
    
    # 3. Webserver starten
    start_webserver()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_info("\n\nTest beendet")
        sys.exit(0)
