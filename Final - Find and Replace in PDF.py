import pikepdf
import fitz  # PyMuPDF
import zlib
import os
from pathlib import Path

def process_normal_pdf_working_version(input_path, output_path, replacements):
    """
    Versiune care poziționa bine Ioana - cu corecție pentru cifre
    """
    try:
        doc = fitz.open(input_path)
        total_changes = 0

        for page_num in range(len(doc)):
            page = doc[page_num]

            # PASUL 1: Replacement-uri normale pentru text
            for old_text, new_text in replacements.items():
                text_instances = page.search_for(old_text)

                if text_instances:
                    print(f"  Găsit '{old_text}' în {len(text_instances)} poziții")

                    for inst in text_instances:
                        # Șterge cu zonă extinsă pentru acoperire completă
                        expanded_rect = fitz.Rect(
                            inst.x0 - 2, inst.y0 - 2,
                            inst.x1 + 2, inst.y1 + 2
                        )
                        page.add_redact_annot(expanded_rect, fill=(1, 1, 1))
                        total_changes += 1

                    # Aplică redactarea
                    page.apply_redactions()

                    # Adaugă textul nou cu poziționare precisă
                    for inst in text_instances:
                        height = inst.y1 - inst.y0
                        fontsize = min(max(height * 0.7, 8), 12)

                        page.insert_text(
                            fitz.Point(inst.x0 + 1, inst.y1 - 2),
                            new_text,
                            fontsize=fontsize,
                            color=(0, 0, 0),
                            fontname="helv"
                        )

                    print(f"  Înlocuit '{old_text}' → '{new_text}' ({len(text_instances)}x)")

            # PASUL 2: Tratare SEPARATĂ pentru cifre individuale - NU pattern cu spații
            page_text = page.get_text()

            if "Cod unic de inregistrare" in page_text:
                print(f"  Procesez cifre individuale pentru cod unic...")

                # Găsește toate textele de pe pagină pentru a identifica cifrele individuale
                all_text_dict = page.get_text("dict")
                all_digits_found = []

                for block in all_text_dict["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                bbox = span["bbox"]

                                if len(text) == 1 and text.isdigit():
                                    width = bbox[2] - bbox[0]
                                    height = bbox[3] - bbox[1]

                                    all_digits_found.append({
                                        'digit': text,
                                        'x': bbox[0],
                                        'y': bbox[1],
                                        'width': width,
                                        'height': height,
                                        'rect': fitz.Rect(bbox)
                                    })

                # Sortează cifrele de la stânga la dreapta
                all_digits_found.sort(key=lambda x: (x['y'], x['x']))

                # Caută zona cu "Cod unic"
                cod_instances = page.search_for("Cod unic")
                if cod_instances:
                    cod_rect = cod_instances[0]

                    # Filtrează cifre care sunt aproape de "Cod unic" (în același rând)
                    nearby_digits = []

                    for digit_info in all_digits_found:
                        # Verifică dacă cifra este în același rând ca textul "Cod unic" (±30px pe Y)
                        if abs(digit_info['y'] - cod_rect.y0) < 30:
                            # Și la dreapta textului "Cod unic"
                            if digit_info['x'] > cod_rect.x1:
                                nearby_digits.append(digit_info)

                    print(f"  Găsite {len(nearby_digits)} cifre aproape de 'Cod unic'")

                    # Înlocuiește doar primele 8 cifre (secvența completă)
                    if len(nearby_digits) >= 8:
                        new_sequence = ['3', '4', '3', '5', '3', '6', '1', '1']

                        for i, digit_info in enumerate(nearby_digits[:8]):
                            rect = digit_info['rect']
                            new_digit = new_sequence[i]
                            old_digit = digit_info['digit']

                            # Șterge cifra veche
                            clear_rect = fitz.Rect(
                                rect.x0 - 2, rect.y0 - 2,
                                rect.x1 + 2, rect.y1 + 2
                            )
                            page.add_redact_annot(clear_rect, fill=(1, 1, 1))
                            page.apply_redactions()

                            # Adaugă cifra nouă
                            center_x = (rect.x0 + rect.x1) / 2 - 3
                            center_y = rect.y1 - 1

                            page.insert_text(
                                fitz.Point(center_x, center_y),
                                new_digit,
                                fontsize=9,
                                color=(0, 0, 0),
                                fontname="helv"
                            )

                            print(f"    Cifra {i+1}: '{old_digit}' → '{new_digit}'")
                            total_changes += 1

        if total_changes > 0:
            doc.save(output_path)
            print(f"  MODIFICAT: {total_changes} schimbări salvate")
            doc.close()
            return True
        else:
            print(f"  Fără modificări")
            doc.close()
            return False

    except Exception as e:
        print(f"  EROARE: {e}")
        return False

def process_xfa_pdf(input_path, output_path, replacements, pdf):
    """
    Procesare PDF XFA prin modificarea stream-urilor XML
    """
    try:
        xfa = pdf.Root.AcroForm.XFA
        total_changes = 0
        new_xfa_array = []

        for i, item in enumerate(xfa):
            try:
                if hasattr(item, 'read_bytes'):
                    stream_data = item.read_bytes()

                    try:
                        decompressed = zlib.decompress(stream_data)
                        text_data = decompressed.decode('utf-8', errors='ignore')
                        was_compressed = True
                    except:
                        text_data = stream_data.decode('utf-8', errors='ignore')
                        was_compressed = False

                    original_text = text_data
                    modified_text = text_data

                    for old_text, new_text in replacements.items():
                        if old_text in modified_text:
                            count = modified_text.count(old_text)
                            modified_text = modified_text.replace(old_text, new_text)
                            total_changes += count
                            print(f"  XFA: '{old_text}' -> '{new_text}' ({count}x)")

                    if modified_text != original_text:
                        if was_compressed:
                            try:
                                new_data = zlib.compress(modified_text.encode('utf-8'))
                            except:
                                new_data = modified_text.encode('utf-8')
                        else:
                            new_data = modified_text.encode('utf-8')

                        new_stream = pikepdf.Stream(pdf, new_data)
                        new_xfa_array.append(new_stream)
                    else:
                        new_xfa_array.append(item)
                else:
                    new_xfa_array.append(item)

            except Exception as e:
                new_xfa_array.append(item)

        if total_changes > 0:
            pdf.Root.AcroForm.XFA = new_xfa_array
            pdf.save(output_path)
            print(f"  XFA SALVAT: {total_changes} modificări")
            pdf.close()
            return True
        else:
            pdf.close()
            return False

    except Exception as e:
        print(f"  EROARE XFA: {e}")
        pdf.close()
        return False

def process_single_pdf(input_path, output_path, replacements):
    """
    Procesează un singur PDF - detectează tipul și aplică metoda corespunzătoare
    """
    print(f"Procesez: {os.path.basename(input_path)}")

    try:
        pdf = pikepdf.open(input_path)

        if '/AcroForm' not in pdf.Root or '/XFA' not in pdf.Root.AcroForm:
            print(f"  PDF normal - folosesc versiunea care poziționează bine Ioana")
            pdf.close()
            return process_normal_pdf_working_version(input_path, output_path, replacements)
        else:
            print(f"  PDF XFA - procesez XML streams")
            return process_xfa_pdf(input_path, output_path, replacements, pdf)

    except Exception as e:
        print(f"  EROARE: {e}")
        return False

def main():
    input_folder = r"e:\Carte\BB\17 - Site Leadership\alte\Ionel Balauta\Aryeht\Task 1 - Traduce tot site-ul\Doar Google Web\Andreea\Meditatii\2023\Edit PDF"
    output_folder = r"e:\Carte\BB\17 - Site Leadership\alte\Ionel Balauta\Aryeht\Task 1 - Traduce tot site-ul\Doar Google Web\Andreea\Meditatii\2023\Edit PDF\Modified"

    # Toate replacement-urile
    replacements = {
        "SC TIP B SRL": "SC IOANA SRL",
        "Tip B SRL": "Ioana SRL",
        "TIP B SRL": "IOANA SRL",
        "J/22/1740/2007": "J22/1234/2025",
        "886577611": "34353611",
        "21920509": "21920508",
        "FANTANARU NECULAI": "IONUT GHINDA",
        "CONSTANTINESCU DANA": "GHIA LORYDANA",
        "Doina-Daniela": "Doina-Lorydana",
        "Daniela Constantinescu": "Ghia-Lorydana",
    }

    print("PROCESARE TOATE PDF-URILE - VERSIUNEA CARE POZIȚIONA BINE IOANA")

    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_path.glob("*.pdf"))
    successful = 0

    print(f"Găsite {len(pdf_files)} fișiere PDF pentru procesare:")

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf_file.name}")
        output_file = output_path / f"WORKING_{pdf_file.name}"

        if process_single_pdf(str(pdf_file), str(output_file), replacements):
            successful += 1

    print(f"\n=== RAPORT FINAL ===")
    print(f"Procesate cu succes: {successful}/{len(pdf_files)} fișiere")

if __name__ == "__main__":
    main()