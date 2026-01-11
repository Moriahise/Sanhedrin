#!/usr/bin/env python3
"""
Automatisches Update-Script für responsa.json

Dieses Script scannt den responsa-Ordner nach neuen HTML/PDF-Dateien und
aktualisiert automatisch die responsa.json-Datei.

Features:
- Extrahiert Titel und Zusammenfassung aus HTML-Dateien
- Unterstützt PDF-Dateien
- Vergibt automatisch fortlaufende Nummern
- Vermeidet Duplikate
- Sortiert Einträge nach Nummer

Verwendung:
    python3 update_responsa.py
"""

import os
import json
import datetime
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# BeautifulSoup für HTML-Parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False
    print("⚠️  BeautifulSoup nicht verfügbar - verwende Fallback-Parsing")


def extract_metadata_from_html(path: Path) -> Tuple[str, str]:
    """
    Extrahiert Titel und Zusammenfassung aus HTML-Datei.
    
    Returns:
        (title, summary) Tuple
    """
    title = path.stem
    summary = ""
    
    if not BS4_AVAILABLE:
        return title, summary
    
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Titel extrahieren
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            title = title_tag.get_text(strip=True)
        
        # Zusammenfassung extrahieren (erste ~50 Wörter)
        for tag in soup(["script", "style", "meta", "link"]):
            tag.decompose()
        
        text = soup.get_text(separator=" ", strip=True)
        words = text.split()
        
        if words:
            summary = " ".join(words[:50])
            if len(words) > 50:
                summary += "..."
    
    except Exception as e:
        print(f"⚠️  Fehler beim Parsen von {path.name}: {e}")
        title = path.stem
        summary = ""
    
    return title, summary


def extract_metadata(path: Path) -> Dict:
    """
    Erstellt Metadaten-Dictionary für eine Datei.
    
    Args:
        path: Pfad zur Datei
        
    Returns:
        Dictionary mit allen Metadaten
    """
    ext = path.suffix.lower()
    file_type = "html" if ext in {".html", ".htm"} else "pdf"
    
    # Datum aus Datei-Modifikationszeit
    mtime = path.stat().st_mtime
    dt = datetime.datetime.fromtimestamp(mtime)
    date_str = dt.strftime("%d/%m/%Y")
    year = dt.year
    
    # Titel und Zusammenfassung parsen
    if file_type == "html":
        title, summary = extract_metadata_from_html(path)
    else:
        title = path.stem
        summary = ""
    
    # Entry zusammenstellen
    entry = {
        "title_he": title,
        "title_en": title,
        "summary_he": summary,
        "summary_en": summary,
        "category": "other",
        "category_he": "אחר",
        "category_en": "Other",
        "date": date_str,
        "year": year,
        "file": str(path.as_posix()),
        "type": file_type,
    }
    
    return entry


def main() -> int:
    """Hauptfunktion"""
    print("🔄 Starte responsa.json Update...")
    print("=" * 60)
    
    # Projektverzeichnis bestimmen
    root = Path(__file__).resolve().parent
    responsa_dir = root / "responsa"
    json_path = root / "responsa.json"
    
    # Prüfe ob responsa-Ordner existiert
    if not responsa_dir.is_dir():
        print("❌ Kein 'responsa'-Ordner gefunden!")
        print(f"   Erwartet: {responsa_dir}")
        print("\n💡 Erstelle Beispiel-Struktur...")
        responsa_dir.mkdir(exist_ok=True)
        (responsa_dir / "2025").mkdir(exist_ok=True)
        print(f"✅ Ordner erstellt: {responsa_dir}")
        print("   Füge nun HTML/PDF-Dateien in Unterordner ein (z.B. responsa/2025/)")
        return 0
    
    # Lade bestehende JSON-Daten
    existing_data: List[Dict] = []
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"📂 Bestehende Einträge geladen: {len(existing_data)}")
        except Exception as e:
            print(f"⚠️  Fehler beim Laden der JSON: {e}")
            print("   Starte mit leerer Liste...")
            existing_data = []
    else:
        print("📝 Neue responsa.json wird erstellt...")
    
    # Mapping bekannter Dateien
    existing_map = {
        entry.get("file"): entry 
        for entry in existing_data 
        if isinstance(entry, dict)
    }
    
    # Nächste Nummer bestimmen
    existing_numbers = [
        entry.get("number", 0) 
        for entry in existing_data 
        if isinstance(entry.get("number"), int)
    ]
    next_number = max(existing_numbers, default=0) + 1
    
    # Scanne responsa-Ordner
    new_entries: List[Dict] = []
    supported_extensions = {".html", ".htm", ".pdf"}
    
    print(f"\n🔍 Scanne Ordner: {responsa_dir}")
    print(f"   Unterstützte Dateitypen: {', '.join(supported_extensions)}")
    
    for file_path in sorted(responsa_dir.rglob("*")):
        if not file_path.is_file():
            continue
        
        ext = file_path.suffix.lower()
        if ext not in supported_extensions:
            continue
        
        rel_path = file_path.relative_to(root).as_posix()
        
        # Überspringe bekannte Dateien
        if rel_path in existing_map:
            print(f"   ⏭️  Überspringe: {rel_path} (bereits vorhanden)")
            continue
        
        # Extrahiere Metadaten
        print(f"   ✨ Neu gefunden: {rel_path}")
        metadata = extract_metadata(file_path)
        metadata["file"] = rel_path
        metadata["number"] = next_number
        next_number += 1
        
        new_entries.append(metadata)
        print(f"      Titel: {metadata['title_he']}")
        print(f"      Typ: {metadata['type'].upper()}")
        print(f"      Datum: {metadata['date']}")
    
    # Ergebnis
    print("\n" + "=" * 60)
    if not new_entries:
        print("✅ Keine neuen Dateien gefunden - responsa.json ist aktuell")
        return 0
    
    # Kombiniere und sortiere
    updated_data = existing_data + new_entries
    updated_data.sort(key=lambda x: x.get("number", 0))
    
    # Schreibe JSON
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ {len(new_entries)} neue{'r Eintrag' if len(new_entries) == 1 else ' Einträge'} hinzugefügt!")
        print(f"📊 Gesamt: {len(updated_data)} Einträge in responsa.json")
        print(f"💾 Gespeichert: {json_path}")
        
        # Details der neuen Einträge
        print("\n📋 Neue Einträge:")
        for entry in new_entries:
            print(f"   #{entry['number']}: {entry['title_he']} ({entry['type'].upper()})")
        
        return 0
    
    except Exception as e:
        print(f"❌ Fehler beim Schreiben der JSON: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
