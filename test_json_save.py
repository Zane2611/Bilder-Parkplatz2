#!/usr/bin/env python3
"""
Test für JSON-Serialisierung der Rechtecke
"""

import json
import numpy as np
from test import RectangleEditor
import tkinter as tk

def test_json_serialization():
    """Teste die JSON-Serialisierung mit verschiedenen Datentypen"""
    
    # Simuliere verschiedene Rechteck-Datentypen die Probleme verursachen könnten
    test_rectangles = [
        (10, 20, 100, 200),  # normale ints
        (10.5, 20.7, 100.3, 200.8),  # floats
        (np.int32(15), np.int32(25), np.int32(105), np.int32(205)),  # numpy ints
        (np.float64(12.1), np.float64(22.1), np.float64(102.1), np.float64(202.1)),  # numpy floats
    ]
    
    print("Testing JSON serialization...")
    
    for i, rect in enumerate(test_rectangles):
        try:
            x1, y1, x2, y2 = rect
            # Konvertierung wie in der save_rectangles Funktion
            serializable_rect = [
                int(float(x1)), 
                int(float(y1)), 
                int(float(x2)), 
                int(float(y2))
            ]
            
            # Test JSON serialization
            data = {
                "rectangle": serializable_rect,
                "original_types": [str(type(coord)) for coord in rect]
            }
            
            json_str = json.dumps(data, indent=2)
            print(f"✓ Rectangle {i+1}: {rect} -> {serializable_rect}")
            print(f"  Types: {[str(type(coord)) for coord in rect]} -> {[str(type(coord)) for coord in serializable_rect]}")
            
        except Exception as e:
            print(f"✗ Rectangle {i+1} FAILED: {rect} - Error: {e}")
    
    print("\nTesting complete rectangle list serialization...")
    try:
        # Wie in der echten save_rectangles Funktion
        serializable_rectangles = []
        for rect in test_rectangles:
            x1, y1, x2, y2 = rect
            serializable_rectangles.append([
                int(float(x1)), 
                int(float(y1)), 
                int(float(x2)), 
                int(float(y2))
            ])
        
        data = {
            "rectangles": serializable_rectangles,
            "total_count": len(serializable_rectangles)
        }
        
        json_str = json.dumps(data, indent=2)
        print(f"✓ Complete list serialization successful!")
        print(f"JSON output sample:\n{json_str}")
        
    except Exception as e:
        print(f"✗ Complete list serialization FAILED: {e}")

if __name__ == "__main__":
    test_json_serialization()