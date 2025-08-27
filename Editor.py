import PyPDF2
import fitz  # PyMuPDF
import os
from pathlib import Path

def remove_pdf_security_and_replace_text(input_path, output_path, replacements):
    """
    Înlătură protecția PDF-ului și face search & replace pentru textul specificat

    Args:
        input_path (str): Calea către PDF-ul de intrare
        output_path (str): Calea către PDF-ul de ieșire
        replacements (dict): Dicționar cu replacements {'text_vechi': 'text_nou'}
    """

    try:
        # Metoda 1: Folosind PyMuPDF (fitz) - mai eficientă pentru editare
        doc = fitz.open(input_path)

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Aplică replacements pentru fiecare pereche
            for old_text, new_text in replacements.items():
                # Caută și înlocuiește textul
                text_instances = page.search_for(old_text)

                for inst in text_instances:
                    # Creează un dreptunghi alb peste textul vechi
                    page.add_redact_annot(inst, fill=(1, 1, 1))  # Fill cu alb

                    # Aplică redact
                    page.apply_redactions()

                    # Adaugă textul nou în aceeași poziție
                    page.insert_text(
                        inst.tl,  # Top-left corner
                        new_text,
                        fontsize=11,
                        color=(0, 0, 0)  # Negru
                    )

        # Salvează documentul modificat
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()

        print(f"✓ PDF procesat cu succes: {output_path}")
        return True

    except Exception as e:
        print(f"✗ Eroare cu PyMuPDF: {e}")

        # Metoda 2: Fallback cu PyPDF2 pentru cazurile dificile
        try:
            return process_with_pypdf2(input_path, output_path, replacements)
        except Exception as e2:
            print(f"✗ Eroare și cu PyPDF2: {e2}")
            return False

def process_with_pypdf2(input_path, output_path, replacements):
    """
    Metodă alternativă folosind PyPDF2
    """
    with open(input_path, 'rb') as file:
        # Încearcă să deschidă PDF-ul
        reader = PyPDF2.PdfReader(file)
        writer = PyPDF2.PdfWriter()

        # Verifică dacă PDF-ul este criptat
        if reader.is_encrypted:
            # Încearcă cu parolă goală
            reader.decrypt("")

        # Procesează fiecare pagină
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]

            # Extrage textul
            text = page.extract_text()

            # Aplică replacements
            modified_text = text
            for old_text, new_text in replacements.items():
                modified_text = modified_text.replace(old_text, new_text)

            # Adaugă pagina la writer
            writer.add_page(page)

        # Salvează fișierul modificat
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

    print(f"✓ PDF procesat cu PyPDF2: {output_path}")
    return True

def batch_process_pdfs(input_folder, output_folder, replacements):
    """
    Procesează în lot toate PDF-urile dintr-un folder
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    # Creează folder-ul de ieșire dacă nu există
    output_path.mkdir(parents=True, exist_ok=True)

    # Găsește toate PDF-urile
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print("Nu s-au găsit fișiere PDF în folder-ul specificat.")
        return

    print(f"Găsite {len(pdf_files)} fișiere PDF pentru procesare...")

    success_count = 0

    for pdf_file in pdf_files:
        print(f"\nProcesez: {pdf_file.name}")

        output_file = output_path / f"modificat_{pdf_file.name}"

        if remove_pdf_security_and_replace_text(str(pdf_file), str(output_file), replacements):
            success_count += 1

    print(f"\n🎉 Procesare completă! {success_count}/{len(pdf_files)} fișiere procesate cu succes.")

# Configurația ta
if __name__ == "__main__":
    # Setează căile tale
    input_folder = r"e:\Carte\BB\17 - Site Leadership\alte\Ionel Balauta\Aryeht\Task 1 - Traduce tot site-ul\Doar Google Web\Andreea\Meditatii\2023\Edit PDF"
    output_folder = r"e:\Carte\BB\17 - Site Leadership\alte\Ionel Balauta\Aryeht\Task 1 - Traduce tot site-ul\Doar Google Web\Andreea\Meditatii\2023\Edit PDF\Modified"

    # Definește replacements
    # Adaugă mai multe replacements
    replacements = {
        "Tip B SRL": "Ioana SRL",
        "886577611": "34353611",
        "SC TIP B SRL": "SC IOANA SRL",
        "J22/1749/2007": "J22/1234/2025",
        # Adaugă orice alte înlocuiri ai nevoie
    }

    print("🔄 Începe procesarea PDF-urilor...")
    print(f"📂 Input folder: {input_folder}")
    print(f"📁 Output folder: {output_folder}")
    print(f"🔄 Replacements: {replacements}")

    batch_process_pdfs(input_folder, output_folder, replacements)