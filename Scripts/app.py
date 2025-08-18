import os
import io
import tempfile
import re
from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

# ----------------- PDF Processor -----------------
def process_pdf_with_geez(input_path):
    doc = fitz.open(input_path)
    font_path = os.path.join('static', 'Tayitu.ttf')
    font_name = "Tayitu"

    temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_output_path = temp_output.name
    temp_output.close()

    for i, page in enumerate(doc):
        page_number = i + 1
        width, height = page.rect.width, page.rect.height
        font_size = 12
        y = height - 35  # Bottom margin for Geez number

        # ---------------- Remove Arabic numbers at bottom ----------------
        blocks = page.get_text("blocks")
        for b in blocks:
            x0, y0, x1, y1, text, *_ = b
            clean_text = text.strip()
            if re.fullmatch(r"\d{1,3}", clean_text):
                if y0 > height - 120:  # bottom 120 points
                    page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1,1,1))
        page.apply_redactions()

        # ---------------- Add Geez number ----------------
        geez_number = arabic_to_geez_full(page_number)
        x = width - 60 if page_number % 2 != 0 else 40  # odd -> right, even -> left
        page.insert_text(
            fitz.Point(x, y),
            geez_number,
            fontname=font_name,
            fontfile=font_path,
            fontsize=font_size,
            color=(0, 0, 0),
        )

    doc.save(temp_output_path)
    doc.close()
    return temp_output_path

# ----------------- Flask Routes -----------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', error='No file selected')

        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error='No file selected')
        if not file.filename.lower().endswith('.pdf'):
            return render_template('index.html', error='Only PDF files are supported')

        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
                temp_input.write(file.read())
                temp_input_path = temp_input.name

            # Process PDF
            result_pdf_path = process_pdf_with_geez(temp_input_path)

            # Send file to user
            output_name = f"geez_{file.filename}"
            return send_file(
                result_pdf_path,
                as_attachment=True,
                download_name=output_name,
                mimetype='application/pdf'
            )

        finally:
            # Clean up temp files
            for path in [temp_input_path, result_pdf_path]:
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except PermissionError:
                        pass

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
