import os
import re
import time
import gc
import fitz  # PyMuPDF
from flask import Flask, render_template, request, send_file, flash, redirect
from werkzeug.utils import secure_filename
import tempfile

# ----------------- Paths -----------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
FONT_PATH = os.path.join(STATIC_DIR, 'Tayitu.ttf')

if not os.path.isfile(FONT_PATH):
    raise FileNotFoundError(f"Tayitu font not found at {FONT_PATH}")

# ----------------- Flask App -----------------
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = "supersecretkey"  # for flash messages
UPLOAD_EXTENSIONS = ['.pdf']

# ----------------- Geez Conversion -----------------
def arabic_to_geez_full(n):
    ones = ['', '፩', '፪', '፫', '፬', '፭', '፮', '፯', '፰', '፱']
    tens = ['', '፲', '፳', '፴', '፵', '፶', '፷', '፸', '፹', '፺']
    hundred = '፻'

    if n < 10:
        return ones[n]
    elif n < 100:
        t, o = divmod(n, 10)
        return tens[t] + ones[o]
    elif n == 100:
        return hundred
    elif n < 200:
        t, o = divmod(n - 100, 10)
        return hundred + tens[t] + ones[o]
    else:
        h, rem = divmod(n, 100)
        t, o = divmod(rem, 10)
        return ones[h] + hundred + tens[t] + ones[o]

# ----------------- PDF Processing -----------------
def add_geez_page_numbers(input_path, output_path):
    doc = fitz.open(input_path)
    font_name = "Tayitu"
    font_size = 12

    for i, page in enumerate(doc):
        page_number = i + 1
        width, height = page.rect.width, page.rect.height
        y = height - 35
        geez_number = arabic_to_geez_full(page_number)

        # Remove existing Arabic page numbers
        try:
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                if re.fullmatch(r"\d{1,3}", text.strip()):
                    if y0 > height - 100 and (x0 < 100 or x1 > width - 100):
                        page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1,1,1))
            page.apply_redactions()
        except Exception:
            pass

        # Insert Geez number
        x = width - 60 if page_number % 2 != 0 else 40
        page.insert_text(
            fitz.Point(x, y),
            geez_number,
            fontname=font_name,
            fontfile=FONT_PATH,
            fontsize=font_size,
            color=(0,0,0)
        )

    doc.save(output_path)
    doc.close()
    gc.collect()

# ----------------- Routes -----------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('pdf_file')
        if not file:
            flash("No file selected")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in UPLOAD_EXTENSIONS:
            flash("Invalid file type. Only PDFs allowed.")
            return redirect(request.url)

        # Save temp input file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
            temp_input.write(file.read())
            temp_input_path = temp_input.name

        # Output temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_output:
            temp_output_path = temp_output.name

        try:
            add_geez_page_numbers(temp_input_path, temp_output_path)
            return send_file(temp_output_path, as_attachment=True, download_name="Geez_Final.pdf")
        finally:
            # Clean up input file
            try:
                os.unlink(temp_input_path)
            except:
                pass

    return render_template('index.html')

# ----------------- Run -----------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
