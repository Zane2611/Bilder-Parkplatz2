import cv2
import numpy as np
import os
import io
import sys
import time
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json

class RectangleEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Interaktiver Rechteck-Editor")
        self.master.geometry("1200x800")
        
        # Variablen
        self.current_image = None
        self.display_image = None
        self.photo = None
        self.rectangles = []
        self.current_rect = None
        self.drawing = False
        self.start_x = 0
        self.start_y = 0
        self.selected_rect = None
        self.drag_data = {"x": 0, "y": 0}
        self.scale_factor = 1.0
        self.zoom_factor = 1.0  # Zusätzlicher Zoom-Faktor
        self.canvas_width = 800
        self.canvas_height = 600
        
        self.setup_ui()
        
    def setup_ui(self):
        # Hauptframe
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Buttons Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="Datei öffnen", command=self.open_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Auto-Erkennung", command=self.auto_detect).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Rechtecke laden", command=self.load_rectangles).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Überlappungen zusammenführen", command=self.merge_overlapping).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Ausgewähltes löschen", command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Alle löschen", command=self.clear_all).pack(side=tk.LEFT, padx=(0, 10))
        
        # Zoom Controls
        zoom_frame = ttk.Frame(button_frame)
        zoom_frame.pack(side=tk.LEFT, padx=(20, 10))
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="−", command=self.zoom_out, width=3).pack(side=tk.LEFT, padx=(5, 2))
        self.zoom_label = ttk.Label(zoom_frame, text="100%", width=6)
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=3).pack(side=tk.LEFT, padx=(2, 5))
        ttk.Button(zoom_frame, text="Reset", command=self.zoom_reset, width=5).pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Button(button_frame, text="Rechtecke speichern", command=self.save_rectangles).pack(side=tk.LEFT, padx=(20, 10))
        ttk.Button(button_frame, text="Bild mit Rechtecken speichern", command=self.save_annotated_image).pack(side=tk.LEFT, padx=(0, 10))
        
        # Info Label
        self.info_label = ttk.Label(main_frame, text="Öffnen Sie eine Datei (Bild oder PDF) um zu beginnen")
        self.info_label.pack(pady=(0, 10))
        
        # Canvas Frame mit Scrollbars
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas mit Scrollbars
        self.canvas = tk.Canvas(canvas_frame, bg="white", width=self.canvas_width, height=self.canvas_height)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        # Grid Layout für Canvas und Scrollbars
        self.canvas.grid(row=0, column=0, sticky="nsew")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Mouse Events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)  # Right click to delete
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Mouse wheel zoom
        self.canvas.focus_set()  # Fokus für Tastaturereignisse
        
        # Instruction Label
        instruction_text = ("Anweisungen:\n"
                          "• Linke Maustaste gedrückt halten und ziehen: Neues Rechteck zeichnen\n"
                          "• Linke Maustaste auf Rechteck: Rechteck auswählen (rot markiert)\n"
                          "• Ausgewähltes Rechteck verschieben: Ziehen mit gedrückter linker Maustaste\n"
                          "• Button 'Ausgewähltes löschen': Löscht das aktuell ausgewählte (rote) Rechteck\n"
                          "• Button 'Überlappungen zusammenführen': Kombiniert sich überlappende Rechtecke\n"
                          "• Rechte Maustaste auf Rechteck: Rechteck sofort löschen\n"
                          "• Mausrad: Zoomen (oder +/- Buttons)\n"
                          "• Auto-Erkennung: Automatisch Rechtecke erkennen")
        
        instruction_label = ttk.Label(main_frame, text=instruction_text, justify=tk.LEFT)
        instruction_label.pack(pady=(10, 0))
        
    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Datei auswählen",
            filetypes=[
                ("Alle unterstützten", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.pdf"),
                ("Bilder", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff"),
                ("PDF", "*.pdf"),
                ("Alle Dateien", "*.*")
            ]
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        try:
            if is_pdf_file(file_path):
                # PDF verarbeiten - nur erste Seite für Demo
                pil_images = convert_pdf_to_images(file_path)
                if pil_images:
                    self.current_image = pil_to_opencv(pil_images[0])
                    self.info_label.config(text=f"PDF geladen: {os.path.basename(file_path)} (Seite 1)")
                else:
                    messagebox.showerror("Fehler", "Konnte PDF nicht laden")
                    return
            else:
                # Normales Bild laden
                self.current_image = cv2.imread(file_path)
                if self.current_image is None:
                    messagebox.showerror("Fehler", "Konnte Bild nicht laden")
                    return
                self.info_label.config(text=f"Bild geladen: {os.path.basename(file_path)}")
            
            self.rectangles = []
            self.zoom_factor = 1.0  # Reset zoom when loading new file
            self.display_image_on_canvas()
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Datei: {str(e)}")
    
    def display_image_on_canvas(self):
        if self.current_image is None:
            return
        
        # Bild zu PIL konvertieren
        image_rgb = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Skalierung berechnen um in Canvas zu passen
        img_width, img_height = pil_image.size
        self.scale_factor = min(self.canvas_width / img_width, self.canvas_height / img_height, 1.0)
        
        # Zoom anwenden
        final_scale = self.scale_factor * self.zoom_factor
        
        new_width = int(img_width * final_scale)
        new_height = int(img_height * final_scale)
        
        self.display_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display_image)
        
        # Canvas konfigurieren
        self.canvas.delete("all")
        self.canvas.configure(scrollregion=(0, 0, new_width, new_height))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Zoom-Label aktualisieren
        zoom_percent = int(self.zoom_factor * 100)
        self.zoom_label.config(text=f"{zoom_percent}%")
        
        # Rechtecke neu zeichnen
        self.draw_rectangles()
    
    def auto_detect(self):
        if self.current_image is None:
            messagebox.showwarning("Warnung", "Bitte laden Sie zuerst eine Datei")
            return
        
        # Automatische Rechteckerkennung
        detected_rects = process_image_for_rectangles(self.current_image.copy())
        self.rectangles = detected_rects
        self.draw_rectangles()
        
        messagebox.showinfo("Info", f"{len(detected_rects)} Rechteck(e) automatisch erkannt")
    
    def load_rectangles(self):
        """Lädt Rechtecke aus einer JSON-Datei"""
        file_path = filedialog.askopenfilename(
            title="Rechtecke laden",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'rectangles' in data:
                    # Konvertiere geladene Daten zu Tupeln
                    loaded_rectangles = []
                    for rect in data['rectangles']:
                        if len(rect) == 4:
                            x1, y1, x2, y2 = rect
                            loaded_rectangles.append((int(x1), int(y1), int(x2), int(y2)))
                    
                    self.rectangles = loaded_rectangles
                    self.selected_rect = None
                    self.draw_rectangles()
                    
                    messagebox.showinfo("Erfolg", f"{len(loaded_rectangles)} Rechteck(e) aus {file_path} geladen")
                else:
                    messagebox.showerror("Fehler", "Ungültiges JSON-Format: 'rectangles' Feld nicht gefunden")
                    
            except json.JSONDecodeError as e:
                messagebox.showerror("Fehler", f"JSON-Dekodierungsfehler: {str(e)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden: {str(e)}")
    
    def clear_all(self):
        self.rectangles = []
        self.selected_rect = None
        self.draw_rectangles()
    
    def delete_selected(self):
        """Löscht das aktuell ausgewählte Rechteck"""
        if self.selected_rect is not None and 0 <= self.selected_rect < len(self.rectangles):
            del self.rectangles[self.selected_rect]
            self.selected_rect = None
            self.draw_rectangles()
            messagebox.showinfo("Info", "Ausgewähltes Rechteck wurde gelöscht")
        else:
            messagebox.showwarning("Warnung", "Kein Rechteck ausgewählt. Klicken Sie zuerst auf ein Rechteck um es auszuwählen.")
    
    def rectangles_overlap(self, rect1, rect2, overlap_threshold=0.3):
        """
        Prüft ob zwei Rechtecke sich überlappen
        
        :param rect1: Erstes Rechteck (x1, y1, x2, y2)
        :param rect2: Zweites Rechteck (x1, y1, x2, y2)
        :param overlap_threshold: Mindest-Überlappungsanteil (0.0 bis 1.0)
        :return: True wenn sich überlappen, False sonst
        """
        x1a, y1a, x2a, y2a = rect1
        x1b, y1b, x2b, y2b = rect2
        
        # Sicherstellen dass x1 < x2 und y1 < y2
        x1a, x2a = min(x1a, x2a), max(x1a, x2a)
        y1a, y2a = min(y1a, y2a), max(y1a, y2a)
        x1b, x2b = min(x1b, x2b), max(x1b, x2b)
        y1b, y2b = min(y1b, y2b), max(y1b, y2b)
        
        # Überlappungsbereich berechnen
        overlap_x1 = max(x1a, x1b)
        overlap_y1 = max(y1a, y1b)
        overlap_x2 = min(x2a, x2b)
        overlap_y2 = min(y2a, y2b)
        
        # Keine Überlappung wenn negative Dimensionen
        if overlap_x1 >= overlap_x2 or overlap_y1 >= overlap_y2:
            return False
        
        # Überlappungsfläche
        overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
        
        # Flächen der beiden Rechtecke
        area1 = (x2a - x1a) * (y2a - y1a)
        area2 = (x2b - x1b) * (y2b - y1b)
        
        # Überlappungsanteil berechnen
        smaller_area = min(area1, area2)
        if smaller_area == 0:
            return False
        
        overlap_ratio = overlap_area / smaller_area
        
        return overlap_ratio >= overlap_threshold
    
    def merge_two_rectangles(self, rect1, rect2):
        """
        Führt zwei Rechtecke zu einem zusammen
        
        :param rect1: Erstes Rechteck (x1, y1, x2, y2)
        :param rect2: Zweites Rechteck (x1, y1, x2, y2)
        :return: Zusammengeführtes Rechteck (x1, y1, x2, y2)
        """
        x1a, y1a, x2a, y2a = rect1
        x1b, y1b, x2b, y2b = rect2
        
        # Bounding Box beider Rechtecke
        min_x = min(x1a, x1b, x2a, x2b)
        min_y = min(y1a, y1b, y2a, y2b)
        max_x = max(x1a, x1b, x2a, x2b)
        max_y = max(y1a, y1b, y2a, y2b)
        
        return (min_x, min_y, max_x, max_y)
    
    def merge_overlapping(self):
        """Führt alle sich überlappenden Rechtecke zusammen"""
        if not self.rectangles:
            messagebox.showwarning("Warnung", "Keine Rechtecke zum Zusammenführen vorhanden")
            return
        
        original_count = len(self.rectangles)
        merged = True
        
        while merged:
            merged = False
            new_rectangles = []
            used_indices = set()
            
            for i, rect1 in enumerate(self.rectangles):
                if i in used_indices:
                    continue
                
                current_rect = rect1
                merged_with = [i]
                
                # Suche nach überlappenden Rechtecken
                for j, rect2 in enumerate(self.rectangles):
                    if j <= i or j in used_indices:
                        continue
                    
                    if self.rectangles_overlap(current_rect, rect2):
                        current_rect = self.merge_two_rectangles(current_rect, rect2)
                        merged_with.append(j)
                        merged = True
                
                # Alle zusammengeführten Indizes markieren
                for idx in merged_with:
                    used_indices.add(idx)
                
                new_rectangles.append(current_rect)
            
            self.rectangles = new_rectangles
        
        new_count = len(self.rectangles)
        merged_count = original_count - new_count
        
        # Auswahl zurücksetzen da sich Indizes geändert haben
        self.selected_rect = None
        
        self.draw_rectangles()
        
        if merged_count > 0:
            messagebox.showinfo("Erfolg", f"{merged_count} überlappende Rechtecke zusammengeführt.\n"
                                        f"Vorher: {original_count} Rechtecke\n"
                                        f"Nachher: {new_count} Rechtecke")
        else:
            messagebox.showinfo("Info", "Keine überlappenden Rechtecke gefunden")
    
    def draw_rectangles(self):
        # Lösche alle Rechtecke auf Canvas
        self.canvas.delete("rectangle")
        
        for i, (x1, y1, x2, y2) in enumerate(self.rectangles):
            # Koordinaten skalieren (inklusive Zoom)
            final_scale = self.scale_factor * self.zoom_factor
            scaled_x1 = x1 * final_scale
            scaled_y1 = y1 * final_scale
            scaled_x2 = x2 * final_scale
            scaled_y2 = y2 * final_scale
            
            # Farbe je nach Auswahl
            color = "red" if i == self.selected_rect else "green"
            
            self.canvas.create_rectangle(
                scaled_x1, scaled_y1, scaled_x2, scaled_y2,
                outline=color, width=2, tags="rectangle"
            )
    
    def get_canvas_coordinates(self, event):
        # Canvas Scroll-Position berücksichtigen
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        return canvas_x, canvas_y
    
    def canvas_to_image_coordinates(self, canvas_x, canvas_y):
        # Canvas-Koordinaten zu Originalbildkoordinaten (inklusive Zoom)
        final_scale = self.scale_factor * self.zoom_factor
        image_x = canvas_x / final_scale
        image_y = canvas_y / final_scale
        return int(image_x), int(image_y)
    
    def find_rectangle_at_position(self, x, y):
        # Finde Rechteck an gegebener Position
        for i, (x1, y1, x2, y2) in enumerate(self.rectangles):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return None
    
    def on_click(self, event):
        if self.current_image is None:
            return
        
        canvas_x, canvas_y = self.get_canvas_coordinates(event)
        image_x, image_y = self.canvas_to_image_coordinates(canvas_x, canvas_y)
        
        # Prüfen ob auf existierendes Rechteck geklickt wurde
        rect_index = self.find_rectangle_at_position(image_x, image_y)
        
        if rect_index is not None:
            # Rechteck auswählen für Verschieben
            self.selected_rect = rect_index
            self.drawing = False
            self.drag_data["x"] = image_x
            self.drag_data["y"] = image_y
            print(f"Rechteck {rect_index + 1} ausgewählt")  # Debug-Info
        else:
            # Neues Rechteck beginnen
            self.selected_rect = None
            self.drawing = True
            self.start_x = image_x
            self.start_y = image_y
            self.current_rect = [image_x, image_y, image_x, image_y]
        
        self.draw_rectangles()
    
    def on_drag(self, event):
        if self.current_image is None:
            return
        
        canvas_x, canvas_y = self.get_canvas_coordinates(event)
        image_x, image_y = self.canvas_to_image_coordinates(canvas_x, canvas_y)
        
        if self.drawing and self.current_rect:
            # Neues Rechteck zeichnen
            self.current_rect[2] = image_x
            self.current_rect[3] = image_y
            
            # Temporäres Rechteck anzeigen
            self.draw_rectangles()
            final_scale = self.scale_factor * self.zoom_factor
            scaled_x1 = self.current_rect[0] * final_scale
            scaled_y1 = self.current_rect[1] * final_scale
            scaled_x2 = self.current_rect[2] * final_scale
            scaled_y2 = self.current_rect[3] * final_scale
            
            self.canvas.create_rectangle(
                scaled_x1, scaled_y1, scaled_x2, scaled_y2,
                outline="blue", width=2, tags="temp_rectangle"
            )
        
        elif self.selected_rect is not None:
            # Rechteck verschieben
            dx = image_x - self.drag_data["x"]
            dy = image_y - self.drag_data["y"]
            
            x1, y1, x2, y2 = self.rectangles[self.selected_rect]
            self.rectangles[self.selected_rect] = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
            
            self.drag_data["x"] = image_x
            self.drag_data["y"] = image_y
            self.draw_rectangles()
    
    def on_release(self, event):
        self.canvas.delete("temp_rectangle")
        
        if self.drawing and self.current_rect:
            # Neues Rechteck hinzufügen
            x1, y1, x2, y2 = self.current_rect
            
            # Koordinaten normalisieren
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            
            # Nur hinzufügen wenn Rechteck groß genug
            if abs(max_x - min_x) > 5 and abs(max_y - min_y) > 5:
                self.rectangles.append((min_x, min_y, max_x, max_y))
                self.draw_rectangles()
        
        self.drawing = False
        self.current_rect = None
    
    def on_right_click(self, event):
        if self.current_image is None:
            return
        
        canvas_x, canvas_y = self.get_canvas_coordinates(event)
        image_x, image_y = self.canvas_to_image_coordinates(canvas_x, canvas_y)
        
        # Rechteck an Position finden und löschen
        rect_index = self.find_rectangle_at_position(image_x, image_y)
        if rect_index is not None:
            del self.rectangles[rect_index]
            if self.selected_rect == rect_index:
                self.selected_rect = None
            elif self.selected_rect is not None and self.selected_rect > rect_index:
                self.selected_rect -= 1
            self.draw_rectangles()
    
    def on_mousewheel(self, event):
        """Mausrad-Zoom"""
        if self.current_image is None:
            return
        
        # Zoom-Faktor bestimmen
        zoom_delta = 0.1
        if event.delta > 0:  # Hineinzoomen
            self.zoom_factor = min(self.zoom_factor + zoom_delta, 5.0)  # Max 5x zoom
        else:  # Herauszoomen
            self.zoom_factor = max(self.zoom_factor - zoom_delta, 0.1)  # Min 0.1x zoom
        
        self.display_image_on_canvas()
        self.draw_rectangles()
    
    def zoom_in(self):
        """Hineinzoomen"""
        if self.current_image is None:
            return
        self.zoom_factor = min(self.zoom_factor + 0.2, 5.0)
        self.display_image_on_canvas()
        self.draw_rectangles()
    
    def zoom_out(self):
        """Herauszoomen"""
        if self.current_image is None:
            return
        self.zoom_factor = max(self.zoom_factor - 0.2, 0.1)
        self.display_image_on_canvas()
        self.draw_rectangles()
    
    def zoom_reset(self):
        """Zoom zurücksetzen"""
        if self.current_image is None:
            return
        self.zoom_factor = 1.0
        self.display_image_on_canvas()
        self.draw_rectangles()
    
    def save_rectangles(self):
        if not self.rectangles:
            messagebox.showwarning("Warnung", "Keine Rechtecke zum Speichern vorhanden")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Rechtecke speichern",
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Text Dateien", "*.txt")]
        )
        
        if file_path:
            try:
                # Konvertiere alle Koordinaten zu Python int/float für JSON-Serialisierung
                serializable_rectangles = []
                for i, rect in enumerate(self.rectangles):
                    try:
                        x1, y1, x2, y2 = rect
                        # Explizite Konvertierung zu Python-Typen
                        serializable_rectangles.append([
                            int(float(x1)), 
                            int(float(y1)), 
                            int(float(x2)), 
                            int(float(y2))
                        ])
                    except (ValueError, TypeError) as e:
                        print(f"Warning: Skipping invalid rectangle {i}: {rect} - {e}")
                        continue
                
                data = {
                    "rectangles": serializable_rectangles,
                    "image_size": {
                        "width": int(self.current_image.shape[1]) if self.current_image is not None else 0,
                        "height": int(self.current_image.shape[0]) if self.current_image is not None else 0
                    },
                    "total_count": len(serializable_rectangles),
                    "zoom_factor": float(self.zoom_factor),
                    "export_timestamp": int(time.time())
                }
                
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("Erkannte Rechtecke:\n")
                        for i, (x1, y1, x2, y2) in enumerate(serializable_rectangles, 1):
                            f.write(f"Rechteck {i}: x_min={x1}, y_min={y1}, x_max={x2}, y_max={y2}\n")
                        f.write(f"\nGesamtanzahl: {len(serializable_rectangles)} Rechtecke\n")
                
                messagebox.showinfo("Erfolg", f"Rechtecke gespeichert in: {file_path}")
            except Exception as e:
                error_msg = f"Fehler beim Speichern: {str(e)}"
                messagebox.showerror("Fehler", error_msg)
                print(f"Debug - Serialization error: {e}")
                print(f"Debug - Rectangle count: {len(self.rectangles)}")
                if self.rectangles:
                    print(f"Debug - First rectangle: {self.rectangles[0]}")
                    print(f"Debug - Rectangle types: {[type(coord) for coord in self.rectangles[0]]}")
    
    def save_annotated_image(self):
        if self.current_image is None:
            messagebox.showwarning("Warnung", "Kein Bild geladen")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Annotiertes Bild speichern",
            defaultextension=".png",
            filetypes=[("PNG Dateien", "*.png"), ("JPG Dateien", "*.jpg"), ("Alle Dateien", "*.*")]
        )
        
        if file_path:
            try:
                # Kopie des Bildes erstellen
                annotated_image = self.current_image.copy()
                
                # Rechtecke einzeichnen
                for x1, y1, x2, y2 in self.rectangles:
                    cv2.rectangle(annotated_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                cv2.imwrite(file_path, annotated_image)
                messagebox.showinfo("Erfolg", f"Annotiertes Bild gespeichert: {file_path}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Speichern: {str(e)}")


def is_pdf_file(file_path):
    """
    Überprüft, ob die angegebene Datei eine PDF-Datei ist.
    
    :param file_path: Pfad zur Datei
    :return: True wenn PDF, False sonst
    """
    return file_path.lower().endswith('.pdf')

def convert_pdf_to_images(pdf_path, dpi=200):
    """
    Konvertiert eine PDF-Datei in eine Liste von PIL-Bildern mit PyMuPDF.
    
    :param pdf_path: Pfad zur PDF-Datei
    :param dpi: Auflösung für die Konvertierung (höher = bessere Qualität)
    :return: Liste von PIL-Bildern
    """
    try:
        print("Verwende PyMuPDF für PDF-Verarbeitung...")
        doc = fitz.open(pdf_path)
        print(f"PDF erfolgreich geöffnet. {len(doc)} Seite(n) gefunden.")
        
        images = []
        zoom = dpi / 72.0  # PyMuPDF verwendet 72 DPI als Standard
        matrix = fitz.Matrix(zoom, zoom)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)
            # Konvertiere zu PIL Image
            img_data = pix.tobytes("ppm")
            pil_image = Image.open(io.BytesIO(img_data))
            images.append(pil_image)
            print(f"Seite {page_num + 1} konvertiert (Größe: {pil_image.size})")
        
        doc.close()
        print("PDF-Konvertierung erfolgreich abgeschlossen.")
        return images
        
    except Exception as e:
        print(f"Fehler beim Konvertieren der PDF-Datei: {e}")
        return []

def pil_to_opencv(pil_image):
    """
    Konvertiert ein PIL-Bild zu einem OpenCV-Bild.
    
    :param pil_image: PIL-Bild
    :return: OpenCV-Bild (BGR-Format)
    """
    # PIL-Bild zu numpy array
    open_cv_image = np.array(pil_image)
    # RGB zu BGR konvertieren (OpenCV verwendet BGR)
    open_cv_image = open_cv_image[:, :, ::-1].copy()
    return open_cv_image

def detect_rectangles(file_path, min_area=1000, epsilon_coef=0.02):
    """
    Erkennt Rechtecke in einem Bild oder PDF und gibt deren Bounding-Box-Koordinaten aus.
    
    :param file_path: Pfad zum Eingangsbild oder PDF
    :param min_area: Minimale Fläche eines Konturs, damit es als Rechteck gilt
    :param epsilon_coef: Koeffizient für die Polygon-Approximation
    :return: Liste von Rechtecken als (x_min, y_min, x_max, y_max) pro Seite/Bild
    """
    all_rectangles = []
    
    # Überprüfen, ob es sich um eine PDF-Datei handelt
    if is_pdf_file(file_path):
        print(f"PDF-Datei erkannt: {file_path}")
        pil_images = convert_pdf_to_images(file_path)
        
        if not pil_images:
            print("Fehler: Konnte PDF nicht in Bilder konvertieren.")
            return all_rectangles
            
        print(f"PDF hat {len(pil_images)} Seite(n).")
        
        # Jede Seite der PDF verarbeiten
        for page_num, pil_image in enumerate(pil_images, start=1):
            print(f"\nVerarbeite Seite {page_num}...")
            img = pil_to_opencv(pil_image)
            rectangles = process_image_for_rectangles(img, min_area, epsilon_coef)
            
            # Rechtecke für diese Seite ausgeben
            print(f"Seite {page_num}: {len(rectangles)} Rechteck(e) gefunden")
            for idx, (x1, y1, x2, y2) in enumerate(rectangles, start=1):
                print(f"  Rechteck {idx}: x_min={x1}, y_min={y1}, x_max={x2}, y_max={y2}")
            
            all_rectangles.append(rectangles)
            
            # Visualisierung für jede Seite speichern
            cv2.imwrite(f"detected_rectangles_page_{page_num}.png", img)
    
    else:
        # Normales Bild verarbeiten
        print(f"Bild-Datei erkannt: {file_path}")
        img = cv2.imread(file_path)
        if img is None:
            print(f"Fehler: Konnte Bild nicht laden: {file_path}")
            return all_rectangles
            
        rectangles = process_image_for_rectangles(img, min_area, epsilon_coef)
        
        # Rechtecke ausgeben
        for idx, (x1, y1, x2, y2) in enumerate(rectangles, start=1):
            print(f"Rechteck {idx}: x_min={x1}, y_min={y1}, x_max={x2}, y_max={y2}")
        
        all_rectangles.append(rectangles)
        
        # Visualisierung speichern
        cv2.imwrite("detected_rectangles.png", img)
    
    return all_rectangles

def process_image_for_rectangles(img, min_area=1000, epsilon_coef=0.02):
    """
    Verarbeitet ein OpenCV-Bild und erkennt Rechtecke darin.
    
    :param img: OpenCV-Bild (BGR-Format)
    :param min_area: Minimale Fläche eines Konturs
    :param epsilon_coef: Koeffizient für die Polygon-Approximation
    :return: Liste von Rechtecken als (x_min, y_min, x_max, y_max)
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    rectangles = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        
        # Polygon-Approximation
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon_coef * peri, True)
        
        # Vier Eckpunkte = mögliches Rechteck
        if len(approx) == 4 and cv2.isContourConvex(approx):
            xs = [pt[0][0] for pt in approx]
            ys = [pt[0][1] for pt in approx]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            rectangles.append((x_min, y_min, x_max, y_max))
            
            # Rechtecke im Bild markieren
            cv2.drawContours(img, [approx], -1, (0, 255, 0), 2)
    
    return rectangles

if __name__ == "__main__":
    # GUI-Modus wenn keine Kommandozeilenargumente
    if len(sys.argv) == 1:
        root = tk.Tk()
        app = RectangleEditor(root)
        root.mainloop()
    else:
        # Kommandozeilen-Modus (ursprüngliche Funktionalität)
        if len(sys.argv) < 2:
            print("Usage: python test.py <image_path_or_pdf_path>")
            print("Oder starten Sie ohne Argumente für den GUI-Modus")
            print("Unterstützte Formate:")
            print("  - Bilder: .jpg, .jpeg, .png, .bmp, .tiff, etc.")
            print("  - PDFs: .pdf")
            sys.exit(1)
        
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"Fehler: Datei nicht gefunden: {file_path}")
            sys.exit(1)
        
        print(f"Verarbeite Datei: {file_path}")
        rectangles = detect_rectangles(file_path)
        
        if is_pdf_file(file_path):
            total_rectangles = sum(len(page_rects) for page_rects in rectangles)
            print(f"\nZusammenfassung: {total_rectangles} Rechteck(e) in {len(rectangles)} Seite(n) gefunden.")
        else:
            print(f"\nZusammenfassung: {len(rectangles[0]) if rectangles else 0} Rechteck(e) gefunden.")