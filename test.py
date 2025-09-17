import cv2
import numpy as np
import os
import io
import fitz  # PyMuPDF
from PIL import Image

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
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test.py <image_path_or_pdf_path>")
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