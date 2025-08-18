import os
import tempfile
from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
import re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB

FONT_PATH = os.path.join('static', 'Tayitu.ttf')
if not os.path.exists(FONT_PATH):
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
def process_pdf_with_geez(file_path):
    with fitz.open(file_path) as doc:
        for i, page in enumerate(doc):
            page_number = i + 1
            width, height = page.rect.width, page.rect.height
            y = height - 35
            geez_number = arabic_to_geez_full(page_number)

            # Remove Arabic numbers at bottom-left/right
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                text_clean = text.strip()
                if re.fullmatch(r"\d{1,3}", text_clean):
                    if y0 > height - 100 and (x0 < 100 or x1 > width - 100):
                        page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1, 1, 1))
            page.apply_redactions()

            # Insert Geez number
            x = 40 if page_number % 2 == 0 else width - 60
            page.insert_text(
                fitz.Point(x, y),
                geez_number,
                fontname="Tayitu",
                fontfile=FONT_PATH,
                fontsize=12,
                color=(0, 0, 0)
            )

        # Save to a temporary file
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc.save(temp_output.name)
        temp_output.close()
        return temp_output.name

# ----------------- Flask Routes -----------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            return render_template('index.html', error="No file selected")

        file = request.files['file']
        if not file.filename.lower().endswith('.pdf'):
            return render_template('index.html', error="Only PDF files are supported")

        # Save uploaded PDF to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
            file.save(temp_input.name)
            temp_input_path = temp_input.name

        try:
            output_pdf_path = process_pdf_with_geez(temp_input_path)
            return send_file(
                output_pdf_path,
                as_attachment=True,
                download_name=f"geez_{file.filename}",
                mimetype='application/pdf'
            )
        finally:
            # Cleanup temporary files
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if os.path.exists(output_pdf_path):
                os.unlink(output_pdf_path)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
