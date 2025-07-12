from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
import docx
import re
import random

app = Flask(__name__)
app.secret_key = 'study_desk_secret_key'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DUMMY_OPTIONS = ['Mumbai', 'Chennai', 'Kolkata', 'Ahmedabad', 'Hyderabad', 'Lucknow', 'Pune', 'Surat']

def extract_text_from_pdf(path):
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(path):
    doc = docx.Document(path)
    return '\n'.join([para.text for para in doc.paragraphs])

def extract_text_from_txt(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def generate_mcqs(text):
    sentences = re.split(r'(?<=[.?!])\s+', text)
    mcqs = []
    for sentence in sentences:
        if ' is ' in sentence or ' are ' in sentence:
            parts = sentence.split(' is ') if ' is ' in sentence else sentence.split(' are ')
            if len(parts) == 2:
                subject = parts[0].strip()
                answer = parts[1].strip('. ')
                question = f"What {'is' if ' is ' in sentence else 'are'} {subject}?"
                options = random.sample(DUMMY_OPTIONS, 3)
                options.append(answer)
                random.shuffle(options)
                mcqs.append({
                    'question': question,
                    'options': options,
                    'answer': answer
                })
        if len(mcqs) >= 10:
            break
    return mcqs

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('document')
    if not file:
        return jsonify({'questions': 'No file uploaded.'})

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    ext = filename.split('.')[-1].lower()
    if ext == 'pdf':
        text = extract_text_from_pdf(filepath)
    elif ext == 'docx':
        text = extract_text_from_docx(filepath)
    elif ext == 'txt':
        text = extract_text_from_txt(filepath)
    else:
        return jsonify({'questions': 'Unsupported file format.'})

    mcqs = generate_mcqs(text)
    if not mcqs:
        return jsonify({'questions': 'No valid MCQs found in document.'})

    session['mcqs'] = mcqs
    session['current'] = 0
    session['score'] = 0

    return jsonify({'questions': 'MCQs generated. Quiz will begin now.', 'start_quiz': True})

@app.route('/get_question')
def get_question():
    mcqs = session.get('mcqs', [])
    index = session.get('current', 0)
    if index >= len(mcqs):
        return jsonify({'end': True, 'score': session.get('score', 0), 'total': len(mcqs)})
    q = mcqs[index]
    return jsonify({
        'question': q['question'],
        'options': q['options'],
        'qno': index + 1
    })

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    user_answer = data.get('answer')
    mcqs = session.get('mcqs', [])
    index = session.get('current', 0)

    if index >= len(mcqs):
        return jsonify({'end': True})

    correct_answer = mcqs[index]['answer']
    result = 'correct' if user_answer == correct_answer else 'wrong'

    if result == 'correct':
        session['score'] += 1

    session['current'] += 1

    return jsonify({
        'result': result,
        'correct_answer': correct_answer,
        'next': session['current'] < len(mcqs)
    })

@app.route('/restart')
def restart():
    session.clear()
    return redirect(url_for('index'))

# ✅ Render-compatible run
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
