#!/usr/bin/env python3
"""
Einfacher Test für den GUI-Modus des Rechteck-Editors
"""

import tkinter as tk
from test import RectangleEditor

def test_gui():
    """Startet den Rechteck-Editor im GUI-Modus"""
    print("Starte Rechteck-Editor GUI...")
    print("Funktionen:")
    print("1. Öffnen Sie eine Datei (Bild oder PDF)")
    print("2. Verwenden Sie 'Auto-Erkennung' für automatische Rechteckerkennung")
    print("3. Zeichnen Sie neue Rechtecke mit der Maus")
    print("4. Klicken Sie mit der rechten Maustaste auf Rechtecke zum Löschen")
    print("5. Speichern Sie die Ergebnisse")
    print("\nSchließen Sie das Fenster um den Test zu beenden.")
    
    root = tk.Tk()
    app = RectangleEditor(root)
    
    # Automatisch das PDF laden für Demo-Zwecke
    try:
        app.load_file("Parkhaus 1.pdf")
        print("PDF automatisch geladen für Demo.")
    except Exception as e:
        print(f"Konnte PDF nicht automatisch laden: {e}")
    
    root.mainloop()
    print("GUI-Test beendet.")

if __name__ == "__main__":
    test_gui()