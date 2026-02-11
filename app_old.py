# Lines 1-19: All your imports
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, make_response
import hashlib
from datetime import datetime, date
import json
from flask_mail import Mail, Message
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import pickle
from flask_cors import CORS
import numpy as np
import os
from xhtml2pdf import pisa
from dotenv import load_dotenv
from io import BytesIO
import googlemaps
# Line 19
from flask import Flask
from health_assessment_complete import comprehensive_health_assessment

@app.route('/api/health-assessment', methods=['POST'])
def health_assessment_api():
    try:
        data = request.json
        
        # Check if user provided actual BP
        has_bp = data.get('has_bp_measurement', False)
        measured_bp = None
        
        if has_bp and data.get('systolic') and data.get('diastolic'):
            measured_bp = {
                'systolic': int(data['systolic']),
                'diastolic': int(data['diastolic'])
            }
        
        # Run comprehensive assessment
        result = comprehensive_health_assessment(
            data, 
            has_bp_measurement=has_bp,
            measured_bp=measured_bp
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ADD THESE NEW LINES HERE:
app = Flask(__name__)
CORS(app)
gmaps = googlemaps.Client(key='YOUR_API_KEY_HERE')

# Line 21 (now this will work!)
@app.route('/api/health-assessment', methods=['POST'])
def health_assessment():
    # Get user's daily routine data
    data = request.json
    
    # Run ML prediction
    risk_score = ml_model.predict(data['routine_data'])
    
    # If high risk, automatically suggest nearby facilities
    if risk_score > 0.7:  # High risk threshold
        nearby_facilities = gmaps.places_nearby(
            location=(data['latitude'], data['longitude']),
            radius=5000,
            type='hospital'
        )
        
        return jsonify({
            'risk_score': float(risk_score),
            'risk_level': 'High',
            'recommendation': 'Please consult a doctor soon',
            'nearby_hospitals': nearby_facilities['results'][:5]
        })
    
    return jsonify({
        'risk_score': float(risk_score),
        'risk_level': 'Low' if risk_score < 0.3 else 'Medium'
    })

app = Flask(__name__)
CORS(app)

# Initialize Google Maps client
gmaps = googlemaps.Client(key='YOUR_API_KEY_HERE')

@app.route('/api/nearby-facilities', methods=['POST'])
def get_nearby_facilities():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    facility_type = data.get('type', 'hospital')  # hospital or pharmacy
    radius = data.get('radius', 5000)  # 5km default
    
    try:
        # Search nearby places
        places_result = gmaps.places_nearby(
            location=(latitude, longitude),
            radius=radius,
            type=facility_type
        )
        
        facilities = []
        for place in places_result.get('results', []):
            facilities.append({
                'name': place.get('name'),
                'address': place.get('vicinity'),
                'location': place.get('geometry', {}).get('location'),
                'rating': place.get('rating'),
                'place_id': place.get('place_id')
            })
        
        return jsonify({
            'success': True,
            'facilities': facilities
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# --- 1. DB CONFIGURATION ---
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

def get_db_connection():
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        return conn
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn: return
    c = conn.cursor()
    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, age INTEGER, emergency_contact TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Assessments (ML Data)
    c.execute('''CREATE TABLE IF NOT EXISTS assessments (id SERIAL PRIMARY KEY, user_id INTEGER, bp_sys INTEGER, bp_dias INTEGER, glucose REAL, bmi REAL, smoking INTEGER, alcohol TEXT, sleep_hours REAL, screen_time REAL, activity_mins INTEGER, stress_level INTEGER, risk_heart_rate TEXT, risk_diabetes TEXT, risk_hypertension TEXT, risk_sleep_apnea TEXT, risk_anxiety TEXT, risk_obesity TEXT, overall_score INTEGER, overall_risk TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Feedback
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, rating INTEGER, comment TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Recovery Logs (Tracker)
    c.execute('''CREATE TABLE IF NOT EXISTS recovery_logs (id SERIAL PRIMARY KEY, user_id INTEGER, disease_name TEXT, date DATE, diet_quality INTEGER, exercise_mins INTEGER, symptom_severity INTEGER, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- 2. EXPANDED DISEASE DATABASE (10+ Diseases) ---
HEALTH_KNOWLEDGE_BASE = {
    # --- MAJOR DISEASES (ML PREDICTED) ---
    'Diabetes Type 2': {
        'title': 'Type 2 Diabetes', 'icon': 'fa-tint', 'color': 'warning',
        'symptoms': ['Thirst', 'Frequent Urination', 'Blurry Vision', 'Slow Healing'],
        'struggle': 'Energy crashes, dizziness, constant hunger.',
        'daily_plan': {'Phase 1': 'Low Carb Diet. 15m walk.', 'Phase 2': 'Intermittent Fasting.', 'Phase 3': 'Strength training.'},
        'recovery': {'yoga': [{'name': 'Mandukasana'}], 'diet': {'good': ['Bitter Gourd', 'Methi'], 'bad': ['Rice', 'Sugar']}}
    },
    'Heart Disease': {
        'title': 'Heart Disease', 'icon': 'fa-heartbeat', 'color': 'danger',
        'symptoms': ['Chest Pain', 'Shortness of Breath', 'Palpitations', 'Left Arm Pain'],
        'struggle': 'Difficulty climbing stairs, fatigue.',
        'daily_plan': {'Phase 1': 'Salt Restriction. Rest.', 'Phase 2': 'Pranayama Yoga.', 'Phase 3': '45m Brisk Walk.'},
        'recovery': {'yoga': [{'name': 'Shavasana'}], 'diet': {'good': ['Garlic', 'Flaxseeds'], 'bad': ['Fried Food', 'Red Meat']}}
    },
    'Sleep Insomnia': {
        'title': 'Chronic Insomnia', 'icon': 'fa-moon', 'color': 'primary',
        'symptoms': ['Can\'t Sleep', 'Waking up early', 'Irritability', 'Brain Fog'],
        'struggle': 'Low focus, mood swings.',
        'daily_plan': {'Phase 1': 'No Screens 9PM.', 'Phase 2': 'Sunlight 8AM.', 'Phase 3': 'Magnesium Diet.'},
        'recovery': {'yoga': [{'name': 'Yoga Nidra'}], 'diet': {'good': ['Warm Milk', 'Banana'], 'bad': ['Coffee', 'Alcohol']}}
    },
    
    # --- COMMON DISEASES (MANUAL SYMPTOM CHECKER) ---
    'Hypertension': {
        'title': 'High Blood Pressure', 'icon': 'fa-tachometer-alt', 'color': 'danger',
        'symptoms': ['Severe Headache', 'Nosebleed', 'Vision Problems', 'Buzzing in ears'],
        'struggle': 'Anxiety, flushing, heat.',
        'daily_plan': {'Phase 1': 'DASH Diet (No Salt).', 'Phase 2': 'Slow Breathing.', 'Phase 3': 'Weight Loss.'},
        'recovery': {'yoga': [{'name': 'Balasana'}], 'diet': {'good': ['Beetroot', 'Spinach'], 'bad': ['Pickles', 'Chips']}}
    },
    'Migraine': {
        'title': 'Migraine', 'icon': 'fa-bolt', 'color': 'dark',
        'symptoms': ['One-sided Headache', 'Light Sensitivity', 'Nausea', 'Aura'],
        'struggle': 'Cannot function in light/noise.',
        'daily_plan': {'Phase 1': 'Dark Room Rest.', 'Phase 2': 'Ginger Tea.', 'Phase 3': 'Neck Stretches.'},
        'recovery': {'yoga': [{'name': 'Shishuasana'}], 'diet': {'good': ['Water', 'Ginger'], 'bad': ['Cheese', 'Chocolate']}}
    },
    'Gastritis': {
        'title': 'Gastritis / GERD', 'icon': 'fa-fire', 'color': 'warning',
        'symptoms': ['Burning Stomach', 'Bloating', 'Acid Reflux', 'Nausea'],
        'struggle': 'Pain after eating, uneasiness.',
        'daily_plan': {'Phase 1': 'Bland Diet (Curd Rice).', 'Phase 2': 'Small Meals.', 'Phase 3': 'Dinner 7PM.'},
        'recovery': {'yoga': [{'name': 'Vajrasana'}], 'diet': {'good': ['Cold Milk', 'Banana'], 'bad': ['Spicy Food', 'Tea']}}
    },
    'Asthma': {
        'title': 'Asthma / Respiratory', 'icon': 'fa-lungs', 'color': 'info',
        'symptoms': ['Wheezing', 'Shortness of Breath', 'Tight Chest', 'Coughing'],
        'struggle': 'Difficulty breathing in cold/dust.',
        'daily_plan': {'Phase 1': 'Steam Inhalation.', 'Phase 2': 'Breathing Exercises.', 'Phase 3': 'Indoor Cardio.'},
        'recovery': {'yoga': [{'name': 'Anulom Vilom'}], 'diet': {'good': ['Ginger', 'Turmeric'], 'bad': ['Ice Cream', 'Cold Drinks']}}
    },
    'Arthritis': {
        'title': 'Arthritis / Joint Pain', 'icon': 'fa-bone', 'color': 'secondary',
        'symptoms': ['Joint Pain', 'Stiffness', 'Swelling', 'Reduced Motion'],
        'struggle': 'Pain when moving, morning stiffness.',
        'daily_plan': {'Phase 1': 'Hot Compress.', 'Phase 2': 'Gentle Stretching.', 'Phase 3': 'Swimming.'},
        'recovery': {'yoga': [{'name': 'Trikonasana'}], 'diet': {'good': ['Fish Oil', 'Walnuts'], 'bad': ['Sugar', 'Processed Food']}}
    },
    'Anxiety Disorder': {
        'title': 'Anxiety & Stress', 'icon': 'fa-brain', 'color': 'success',
        'symptoms': ['Restlessness', 'Rapid Heartbeat', 'Excessive Worry', 'Trembling'],
        'struggle': 'Overthinking, panic attacks.',
        'daily_plan': {'Phase 1': '4-7-8 Breathing.', 'Phase 2': 'Meditation.', 'Phase 3': 'Nature Walks.'},
        'recovery': {'yoga': [{'name': 'Sukhasana'}], 'diet': {'good': ['Chamomile Tea', 'Dark Chocolate'], 'bad': ['Caffeine', 'Soda']}}
    },
    'Common Cold': {
        'title': 'Viral Flu / Cold', 'icon': 'fa-thermometer', 'color': 'danger',
        'symptoms': ['Runny Nose', 'Sore Throat', 'Fever', 'Body Ache'],
        'struggle': 'Weakness, congestion.',
        'daily_plan': {'Phase 1': 'Complete Bed Rest.', 'Phase 2': 'Hydration (Soup).', 'Phase 3': 'Vitamin C.'},
        'recovery': {'yoga': [{'name': 'Matsyasana'}], 'diet': {'good': ['Chicken Soup', 'Honey'], 'bad': ['Cold Water', 'Yogurt']}}
    }
}

# --- 3. ML MODEL ---
try:
    with open('health_model.pkl', 'rb') as f:
        artifacts = pickle.load(f)
        ml_model = artifacts['model']
        label_encoder = artifacts['encoder']
except: ml_model = None

class HealthPredictor:
    def predict(self, data):
        score = 0
        risks = {}
        # Simple rule-based fallback + ML
        if data['bmi'] > 30: risks['obesity'] = {'level':'High','color':'red'}
        if data['bp_sys'] > 140: risks['hypertension'] = {'level':'High','color':'red'}
        
        # ML Prediction
        df = pd.DataFrame([{'age':30, 'bmi':data['bmi'], 'sleep_hours':data['sleep_hours'], 'activity_mins':data['activity_mins'], 'stress_level':data['stress'], 'bp_sys':data['bp_sys'], 'bp_dias':data['bp_dias'], 'screen_time':data['screen_time']}])
        if ml_model:
            pred = label_encoder.inverse_transform([ml_model.predict(df)[0]])[0]
            if pred == 'Diabetes Type 2': risks['diabetes'] = {'level':'High', 'color':'red'}; score+=80
            if pred == 'Heart Disease': risks['heart'] = {'level':'High', 'color':'red'}; score+=80
            if pred == 'Sleep Insomnia': risks['sleep'] = {'level':'High', 'color':'red'}; score+=60
            
        # Defaults
        for k in ['heart','diabetes','sleep','hypertension','obesity']:
            if k not in risks: risks[k] = {'level':'Low', 'color':'green'}
            
        return risks, min(score+10, 100), {}

predictor = HealthPredictor()
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USE_TLS']=True
app.config['MAIL_USERNAME']=os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD']=os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# --- 4. ROUTES (ALL INCLUDED) ---

@app.route('/')
def home(): return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        conn = get_db_connection()
        try:
            conn.cursor().execute("INSERT INTO users (name, email, password, age, emergency_contact) VALUES (%s, %s, %s, %s, %s)", 
                                  (request.form['name'], request.form['email'], hashlib.sha256(request.form['password'].encode()).hexdigest(), request.form['age'], request.form.get('emergency_contact')))
            conn.commit()
            return redirect(url_for('login'))
        except: conn.rollback()
    return render_template('auth/register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=%s AND password=%s", (request.form['email'], hashlib.sha256(request.form['password'].encode()).hexdigest()))
        u = c.fetchone()
        if u:
            session['user_id'], session['user_name'] = u[0], u[1]
            return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM assessments WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session['user_id'],))
    hist = c.fetchall()
    dates = [h[20].strftime("%Y-%m-%d") for h in reversed(hist)]
    scores = [h[18] for h in reversed(hist)]
    
    # Dashboard Logic: Suggest Plan based on last result
    recovery_plan = None
    if hist:
        latest = hist[0]
        primary = None
        if latest[13] == 'High': primary = 'Diabetes Type 2'
        elif latest[12] == 'High': primary = 'Heart Disease'
        elif latest[15] == 'High': primary = 'Sleep Insomnia'
        
        if primary and primary in HEALTH_KNOWLEDGE_BASE:
            data = HEALTH_KNOWLEDGE_BASE[primary]
            recovery_plan = {
                'issue': data['title'],
                'insight': f"High risk detected. Recommended Plan: {data['title']}",
                'yoga': [y['name'] for y in data['recovery']['yoga']],
                'diet': data['recovery']['diet']['good']
            }
    
    return render_template('dashboard/index.html', user={'name':session['user_name']}, dates=dates, scores=scores, last_risk=hist[0][19] if hist else 'N/A', avg_score=sum(scores)/len(scores) if scores else 0, total_assessments=len(hist), recovery=recovery_plan)

# --- WHO STANDARDS ROUTE (Restored) ---
@app.route('/who-regulations')
def who_regulations():
    return render_template('pages/who.html')

# --- RECOMMENDATIONS ROUTE (Restored) ---
@app.route('/recommendations')
def recommendations():
    return render_template('pages/recommendations.html')

# --- CALCULATORS ROUTE (Restored) ---
@app.route('/calculators')
def calculators():
    return render_template('pages/calculators.html')

# --- FIND DISEASES (SYMPTOM CHECKER) ---
@app.route('/symptom-checker', methods=['GET','POST'])
def symptom_checker():
    diagnosis = None
    if request.method=='POST':
        sel = request.form.getlist('symptoms')
        best, max_m = None, 0
        for d, data in HEALTH_KNOWLEDGE_BASE.items():
            # Check how many symptoms match
            cnt = sum(1 for s in data['symptoms'] if s in sel)
            if cnt > max_m: max_m, best = cnt, d
        
        if best:
            session['active_disease'] = best
            diagnosis = {'name': HEALTH_KNOWLEDGE_BASE[best]['title'], 'plan': HEALTH_KNOWLEDGE_BASE[best]['daily_plan']}
            
    # List all symptoms from DB for checkboxes
    all_sym = sorted(list(set([s for d in HEALTH_KNOWLEDGE_BASE.values() for s in d['symptoms']])))
    return render_template('pages/symptom_checker.html', symptoms=all_sym, diagnosis=diagnosis)

# --- DAILY TRACKER ---
@app.route('/tracker', methods=['GET','POST'])
def tracker():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    disease = session.get('active_disease', 'Heart Disease') # Default if none selected
    plan = HEALTH_KNOWLEDGE_BASE.get(disease, HEALTH_KNOWLEDGE_BASE['Heart Disease']).get('daily_plan', {})
    
    conn = get_db_connection()
    if request.method=='POST':
        conn.cursor().execute("INSERT INTO recovery_logs (user_id, disease_name, date, diet_quality, exercise_mins, symptom_severity, notes) VALUES (%s,%s,CURRENT_DATE,%s,%s,%s,%s)",
                              (session['user_id'], disease, request.form['diet'], request.form['exercise'], request.form['severity'], request.form['notes']))
        conn.commit()
        return redirect(url_for('tracker'))
        
    c = conn.cursor()
    c.execute("SELECT date, symptom_severity FROM recovery_logs WHERE user_id=%s ORDER BY date ASC LIMIT 7", (session['user_id'],))
    hist = c.fetchall()
    return render_template('pages/tracker.html', disease=disease, plan=plan, dates=[h[0].strftime('%a') for h in hist], severity=[h[1] for h in hist], date=date.today().strftime('%A, %B %d'))

@app.route('/encyclopedia')
def encyclopedia():
    return render_template('pages/encyclopedia.html', diseases=HEALTH_KNOWLEDGE_BASE)

@app.route('/assess', methods=['GET','POST'])
def assess():
    if request.method=='POST':
        data = {k: request.form[k] for k in request.form}
        risks, score, recs = predictor.predict({
            'bmi':float(data['bmi']), 'sleep_hours':float(data['sleep_hours']), 
            'activity_mins':int(data['activity_mins']), 'stress':int(data['stress']),
            'bp_sys':int(data['bp_sys']), 'bp_dias':int(data['bp_dias']), 'screen_time':float(data['screen_time'])
        })
        conn = get_db_connection()
        conn.cursor().execute("INSERT INTO assessments (user_id, overall_score, overall_risk, risk_heart_rate, risk_diabetes, risk_sleep_apnea, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                              (session['user_id'], score, 'High' if score>70 else 'Low', risks['heart']['level'], risks['diabetes']['level'], risks['sleep']['level']))
        conn.commit()
        # View Data
        d_view = [{'name': 'Heart', 'risk_level': risks['heart']['level'], 'color': risks['heart']['color']},
                  {'name': 'Diabetes', 'risk_level': risks['diabetes']['level'], 'color': risks['diabetes']['color']}]
        return render_template('prediction/result.html', overall_score=score, overall_risk='High' if score>70 else 'Low', diseases=d_view, recommendations={})
    return render_template('prediction/form.html')

@app.route('/profile')
def profile():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    return render_template('profile/index.html', user=c.fetchone())

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/download_report')
def download_report():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = c.fetchone()
    c.execute("SELECT * FROM assessments WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (session['user_id'],))
    assessment = c.fetchone()
    conn.close()
    if not assessment: return "No data"
    rendered = render_template('pages/report_pdf.html', user=user, assessment=assessment, date=datetime.now())
    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(rendered.encode('utf-8')), dest=pdf)
    resp = make_response(pdf.getvalue())
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = 'attachment; filename=report.pdf'
    return resp

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)