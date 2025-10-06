# app.py

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from deepface import DeepFace
import numpy as np
import cv2
import base64
import logging
import random

logging.getLogger('tensorflow').setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_proteger_sesiones'

PREGUNTAS_BASE = [
    "Cuéntame sobre ti y tu experiencia profesional.",
    "¿Por qué quieres trabajar en esta empresa?",
    "¿Cuál es tu mayor fortaleza?",
    "¿Cuál ha sido tu mayor reto y cómo lo superaste?",
    "¿Dónde te ves en cinco años?",
    "¿Cómo manejas el estrés en el trabajo?"
]

# --- RUTAS DE AUTENTICACIÓN Y NAVEGACIÓN ---

@app.route('/')
def home():
    if session.get('logged_in'):
        return redirect(url_for('interview'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('interview'))

    error = None
    if request.method == 'POST':
        if request.form['username'] == 'usuario' and request.form['password'] == '1234':
            session['logged_in'] = True
            return redirect(url_for('interview'))
        else:
            error = 'Credenciales inválidas. Inténtalo de nuevo.'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('emotion_log', None) # Limpiamos también el log de emociones
    return redirect(url_for('login'))

# --- RUTAS PROTEGIDAS DE LA APLICACIÓN ---

@app.route('/interview')
def interview():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    session['preguntas'] = random.sample(PREGUNTAS_BASE, 3)
    session['pregunta_actual'] = -1
    session['emotion_log'] = [] # Se inicializa el log de emociones aquí
    return render_template('index.html')

@app.route('/get-pregunta', methods=['GET'])
def get_pregunta():
    if not session.get('logged_in'): return jsonify({'error': 'No autorizado'}), 401

    preguntas = session.get('preguntas', [])
    indice_actual = session.get('pregunta_actual', -1)
    nuevo_indice = indice_actual + 1

    if nuevo_indice < len(preguntas):
        session['pregunta_actual'] = nuevo_indice
        return jsonify({'pregunta': preguntas[nuevo_indice], 'fin': False})
    else:
        return jsonify({
            'pregunta': 'Hemos terminado la entrevista. ¡Muchas gracias!', 
            'fin': True,
            'url_resultados': url_for('results')
        })

@app.route('/analizar_emocion', methods=['POST'])
def analizar_emocion_endpoint():
    if not session.get('logged_in'): return jsonify({'error': 'No autorizado'}), 401
    
    data = request.json
    try:
        image_data = base64.b64decode(data['image'].split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        emocion = result[0]['dominant_emotion']
        
        if 'emotion_log' in session:
            log = session['emotion_log']
            log.append(emocion)
            session['emotion_log'] = log

        return jsonify({'emocion': emocion})
    except Exception:
        return jsonify({'emocion': 'neutral'})

@app.route('/results')
def results():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    log = session.get('emotion_log', [])
    emociones_disponibles = ["happy", "sad", "angry", "fear", "neutral", "surprise", "disgust"]
    resumen = {emocion: log.count(emocion) for emocion in emociones_disponibles}
    
    return render_template('resultados.html', resumen_emociones=resumen)

# --- INICIO DE LA APLICACIÓN ---
if __name__ == '__main__':
    app.run(debug=True)