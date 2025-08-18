import os
import re
import fitz  # PyMuPDF
import tempfile
from flask import Flask, render_template, request, send_file, redirect, url_for

# ----------------- Flask Setup -----------------
app = Flask(__name__)

# ----------------- Paths -----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '../templates')
STATIC_DIR = os.path.join(BASE_DIR, '../static')
FONT_PATH = os.path.join(STATIC_DIR, 'Tayitu.ttf')

if not os.path.isfile(FONT_PATH):
    raise FileNotFoundError(f"Tayitu font not found at {FONT_PATH}")

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
def add_geez_page_numbers(input_pdf_path, output_pdf_path):
    doc = fitz.open(input_pdf_path)

    for i, page in enumerate(doc):
        page_number = i + 1
        width, height = page.rect.width, page.rect.height
        font_size = 12
        y = height - 35  # bottom of page

        # Remove existing Arabic numbers at bottom left/right
        try:
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                clean_text = text.strip()
                if re.fullmatch(r"\d{1,3}", clean_text):
                    if y0 > height - 100 and (x0 < 100 or x1 > width - 100):
                        page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1,1,1))
            page.apply_redactions()
        except Exception as e:
            print(f"Redaction error on page {page_number}: {e}")

        # Insert Geez page number
        geez_number = arabic_to_geez_full(page_number)
        x = width - 60 if page_number % 2 != 0 else 40  # odd -> bottom right, even -> bottom left
        page.insert_text(
            fitz.Point(x, y),
            geez_number,
            fontname="Tayitu",
            fontfile=FONT_PATH,
            fontsize=font_size,
            color=(0,0,0)
        )

    doc.save(output_pdf_path)
    doc.close()

# ----------------- Routes -----------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return redirect(request.url)
        file = request.files['pdf_file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
                file.save(temp_input.name)
                temp_input_path = temp_input.name

            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_output_path = temp_output.name
            temp_output.close()

            add_geez_page_numbers(temp_input_path, temp_output_path)

            return send_file(temp_output_path, as_attachment=True, download_name="Geez_Final.pdf")

    return render_template('index.html')

# ----------------- Run -----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
