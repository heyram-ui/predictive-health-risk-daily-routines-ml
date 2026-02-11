from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, make_response
import hashlib
from datetime import datetime, date
import json
from flask_mail import Mail, Message
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd 
import pickle
import numpy as np
import os
from xhtml2pdf import pisa
from dotenv import load_dotenv 
from io import BytesIO
import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask # Assuming you are using Flask

# 1. Load the environment variables from your .env file
load_dotenv()

app = Flask(__name__)

# 2. Get the Neon Connection String
DATABASE_URL = os.getenv("DATABASE_URL")

# 3. Create a helper function to connect to the database
def get_db_connection():
    # The 'sslmode=require' is important for Neon security
    conn = psycopg2.connect(DATABASE_URL)
    return conn

@app.route('/')
def index():
    return "Health Predictor is connected to Neon!"
    
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# --- 1. DB CONFIGURATION (From .env) ---
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

def get_db_connection():
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        return conn
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        print("❌ Database setup skipped: Connection failed. Please start PostgreSQL service.")
        return
    
    c = conn.cursor()
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, age INTEGER, emergency_contact TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Assessments Table
    c.execute('''CREATE TABLE IF NOT EXISTS assessments (id SERIAL PRIMARY KEY, user_id INTEGER, bp_sys INTEGER, bp_dias INTEGER, glucose REAL, bmi REAL, smoking INTEGER, alcohol TEXT, sleep_hours REAL, screen_time REAL, activity_mins INTEGER, stress_level INTEGER, risk_heart_rate TEXT, risk_diabetes TEXT, risk_hypertension TEXT, risk_sleep_apnea TEXT, risk_anxiety TEXT, risk_obesity TEXT, overall_score INTEGER, overall_risk TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Feedback Table
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, rating INTEGER, comment TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Recovery Logs Table
    c.execute('''CREATE TABLE IF NOT EXISTS recovery_logs (id SERIAL PRIMARY KEY, user_id INTEGER, disease_name TEXT, date DATE, diet_quality INTEGER, exercise_mins INTEGER, symptom_severity INTEGER, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    print("✅ Database Initialized Successfully")

# --- 2. ML MODEL LOADER ---
try:
    with open('health_model.pkl', 'rb') as f:
        artifacts = pickle.load(f)
        ml_model = artifacts['model']
        label_encoder = artifacts['encoder']
    print("✅ ML Model Loaded")
except:
    print("⚠️ ML Model not found. Using rule-based fallback.")
    ml_model = None

# --- 3. MASTER KNOWLEDGE BASE (Supports Encyclopedia & Tracker) ---
HEALTH_KNOWLEDGE_BASE = {
    'Diabetes Type 2': {
        'title': 'Type 2 Diabetes', 'icon': 'fa-tint', 'color': 'warning',
        'symptoms': ['Thirst', 'Frequent Urination', 'Blurry Vision', 'Fatigue'],
        'struggle': 'Energy crashes, dizziness, constant hunger.',
        'daily_plan': {'Phase 1': 'Strict Low Carb Diet. 15 mins walking.', 'Phase 2': 'Intermittent Fasting (16:8).', 'Phase 3': 'Strength training 3x week.'},
        'recovery': {'yoga': [{'name': 'Kapalbhati'}, {'name': 'Dhanurasana'}], 'diet': {'good': ['Leafy Greens', 'Bitter Gourd'], 'bad': ['Sugar', 'Rice']}}
    },
    'Heart Disease': {
        'title': 'Heart Disease', 'icon': 'fa-heartbeat', 'color': 'danger',
        'symptoms': ['Chest Pain', 'Shortness of Breath', 'Palpitations', 'Fatigue'],
        'struggle': 'Difficulty climbing stairs, tiredness.',
        'daily_plan': {'Phase 1': 'Complete Rest. No salt.', 'Phase 2': 'Light Yoga (Pranayama).', 'Phase 3': 'Brisk walking 45 mins.'},
        'recovery': {'yoga': [{'name': 'Tadasana'}, {'name': 'Shavasana'}], 'diet': {'good': ['Oats', 'Salmon', 'Berries'], 'bad': ['Fried foods', 'Salt']}}
    },
    'Sleep Insomnia': {
        'title': 'Insomnia', 'icon': 'fa-bed', 'color': 'primary',
        'symptoms': ['Can\'t Sleep', 'Irritability', 'Headaches', 'Focus issues'],
        'struggle': 'Chronic fatigue, brain fog.',
        'daily_plan': {'Phase 1': 'No Screens after 8 PM.', 'Phase 2': 'Wake up at same time daily.', 'Phase 3': 'Magnesium supplements.'},
        'recovery': {'yoga': [{'name': 'Yoga Nidra'}, {'name': 'Viparita Karani'}], 'diet': {'good': ['Warm Milk', 'Almonds'], 'bad': ['Caffeine', 'Phone']}}
    },
    'Hypertension': {
        'title': 'Hypertension', 'icon': 'fa-tachometer-alt', 'color': 'danger',
        'symptoms': ['Headache', 'Nosebleed', 'Vision issues', 'Chest pain'],
        'struggle': 'Dizziness, flushing.',
        'daily_plan': {'Phase 1': 'DASH Diet (Low Sodium).', 'Phase 2': 'Slow breathing exercises.', 'Phase 3': 'Weight management.'},
        'recovery': {'yoga': [{'name': 'Balasana'}, {'name': 'Sukhasana'}], 'diet': {'good': ['Bananas', 'Beetroot'], 'bad': ['Pickles', 'Salt']}}
    },
    'Migraine': {
        'title': 'Migraine', 'icon': 'fa-brain', 'color': 'info',
        'symptoms': ['Throbbing Headache', 'Sensitivity to Light', 'Nausea'],
        'struggle': 'Cannot tolerate light/sound.',
        'daily_plan': {'Phase 1': 'Dark room rest. Hydration.', 'Phase 2': 'Avoid caffeine/chocolate.', 'Phase 3': 'Regular sleep schedule.'},
        'recovery': {'yoga': [{'name': 'Shishuasana'}, {'name': 'Setu Bandhasana'}], 'diet': {'good': ['Ginger Tea', 'Water'], 'bad': ['Cheese', 'Wine']}}
    },
    'Obesity': {
        'title': 'Obesity', 'icon': 'fa-weight', 'color': 'warning',
        'symptoms': ['Breathlessness', 'Joint pain', 'Snoring'],
        'struggle': 'Low stamina, body pain.',
        'daily_plan': {'Phase 1': 'Calorie Deficit. High Protein.', 'Phase 2': '10k Steps Daily.', 'Phase 3': 'Strength Training.'},
        'recovery': {'yoga': [{'name': 'Surya Namaskar'}, {'name': 'Virabhadrasana'}], 'diet': {'good': ['High Protein', 'Fiber'], 'bad': ['Sugary drinks', 'Junk']}}
    },
    'Common Cold': {
        'title': 'Common Cold', 'icon': 'fa-snowflake', 'color': 'info',
        'symptoms': ['Runny Nose', 'Sore Throat', 'Fever', 'Cough'],
        'struggle': 'Weakness, congestion.',
        'daily_plan': {'Phase 1': 'Bed rest. Ginger tea.', 'Phase 2': 'Steam inhalation.', 'Phase 3': 'Vitamin C supplements.'},
        'recovery': {'yoga': [{'name': 'Matsyasana'}, {'name': 'Viparita Karani'}], 'diet': {'good': ['Soup', 'Garlic'], 'bad': ['Cold drinks', 'Dairy']}}
    }
}

# --- 4. PREDICTOR ENGINE ---
class HealthPredictor:
    def predict(self, data):
        risks = {}
        score = 0
        
        # 1. Fallback Logic (If ML fails or for basics)
        if data['bmi'] > 30: risks['obesity'] = {'level':'High','color':'red'}
        if data['bp_sys'] > 140: risks['hypertension'] = {'level':'High','color':'red'}
        if data['stress'] > 7: risks['mental'] = {'level':'High','color':'orange'}
        
        # 2. ML Prediction
        df = pd.DataFrame([{
            'age':30, 'bmi':data['bmi'], 'sleep_hours':data['sleep_hours'], 
            'activity_mins':data['activity_mins'], 'stress_level':data['stress'], 
            'bp_sys':data['bp_sys'], 'bp_dias':data['bp_dias'], 'screen_time':data['screen_time']
        }])
        
        if ml_model:
            pred = label_encoder.inverse_transform([ml_model.predict(df)[0]])[0]
            if pred == 'Diabetes Type 2': risks['diabetes']={'level':'High','color':'red'}; score+=80
            elif pred == 'Heart Disease': risks['heart']={'level':'High','color':'red'}; score+=80
            elif pred == 'Sleep Insomnia': risks['sleep']={'level':'High','color':'red'}; score+=60
        
        # 3. Defaults
        for k in ['diabetes','heart','sleep','hypertension','obesity','mental']: 
            if k not in risks: risks[k]={'level':'Low','color':'green'}
        
        return risks, min(score+10, 100), {}

predictor = HealthPredictor()
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USE_TLS']=True
app.config['MAIL_USERNAME']=os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD']=os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# --- 5. ROUTES ---

@app.route('/')
def home(): return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        # SAFEGUARD: Check if DB is running
        if not conn:
            flash("System Error: Cannot connect to Database. Is PostgreSQL running?", "danger")
            return render_template('auth/register.html')
            
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (name, email, password, age, emergency_contact) VALUES (%s, %s, %s, %s, %s)", 
                        (request.form['name'], request.form['email'], hashlib.sha256(request.form['password'].encode()).hexdigest(), request.form['age'], request.form.get('emergency_contact')))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash('Email already registered or DB error.', 'danger')
            print(e)
        finally:
            conn.close()
    return render_template('auth/register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed.", "danger")
            return render_template('auth/login.html')
            
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=%s AND password=%s", (request.form['email'], hashlib.sha256(request.form['password'].encode()).hexdigest()))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    return render_template('auth/login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    dates, scores, history = [], [], []
    recovery_plan = None
    
    if conn:
        c = conn.cursor()
        c.execute("SELECT * FROM assessments WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session['user_id'],))
        history = c.fetchall()
        conn.close()
        
        # Graph Data
        dates = [h[20].strftime("%Y-%m-%d") for h in reversed(history)]
        scores = [h[18] for h in reversed(history)]
        
        # Recovery Logic
        if history:
            latest = history[0]
            primary = None
            # Check high risks columns in DB order
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

    return render_template('dashboard/index.html', 
                           user={'name':session['user_name']}, 
                           dates=dates, scores=scores, 
                           last_risk=history[0][19] if history else 'N/A', 
                           avg_score=sum(scores)/len(scores) if scores else 0, 
                           total_assessments=len(history), 
                           recovery=recovery_plan)

# --- RESTORED ROUTES ---
@app.route('/who-regulations')
def who_regulations(): return render_template('pages/who.html')

@app.route('/recommendations')
def recommendations(): return render_template('pages/recommendations.html')

@app.route('/calculators')
def calculators(): return render_template('pages/calculators.html')

@app.route('/encyclopedia')
def encyclopedia():
    # Pass the full knowledge base so the template can loop through recovery/yoga
    return render_template('pages/encyclopedia.html', diseases=HEALTH_KNOWLEDGE_BASE)

# --- TRACKER & SYMPTOM CHECKER ---
@app.route('/tracker', methods=['GET','POST'])
def tracker():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    disease = session.get('active_disease', 'Heart Disease')
    # Safe fetch of plan
    plan = HEALTH_KNOWLEDGE_BASE.get(disease, HEALTH_KNOWLEDGE_BASE['Heart Disease']).get('daily_plan', {})
    
    conn = get_db_connection()
    if request.method=='POST':
        if conn:
            conn.cursor().execute("INSERT INTO recovery_logs (user_id, disease_name, date, diet_quality, exercise_mins, symptom_severity, notes) VALUES (%s,%s,CURRENT_DATE,%s,%s,%s,%s)",
                                  (session['user_id'], disease, request.form['diet'], request.form['exercise'], request.form['severity'], request.form['notes']))
            conn.commit()
            flash("Daily Log Saved!", "success")
            return redirect(url_for('tracker'))
        
    dates, severity = [], []
    if conn:
        c = conn.cursor()
        c.execute("SELECT date, symptom_severity FROM recovery_logs WHERE user_id=%s ORDER BY date ASC LIMIT 7", (session['user_id'],))
        hist = c.fetchall()
        dates = [h[0].strftime('%a') for h in hist]
        severity = [h[1] for h in hist]
        conn.close()
        
    # DATE FIX: Passing today's date correctly
    return render_template('pages/tracker.html', 
                           disease=disease, plan=plan, 
                           dates=dates, severity=severity, 
                           date=date.today().strftime('%A, %B %d'))

@app.route('/symptom-checker', methods=['GET','POST'])
def symptom_checker():
    if 'user_id' not in session: return redirect(url_for('login'))
    diagnosis = None
    if request.method=='POST':
        sel = request.form.getlist('symptoms')
        best, max_m = None, 0
        for d, data in HEALTH_KNOWLEDGE_BASE.items():
            cnt = sum(1 for s in data['symptoms'] if s in sel)
            if cnt > max_m: max_m, best = cnt, d
        
        if best:
            session['active_disease'] = best
            diagnosis = {'name': HEALTH_KNOWLEDGE_BASE[best]['title'], 'plan': HEALTH_KNOWLEDGE_BASE[best]['daily_plan']}
            
    all_sym = sorted(list(set([s for d in HEALTH_KNOWLEDGE_BASE.values() for s in d['symptoms']])))
    return render_template('pages/symptom_checker.html', symptoms=all_sym, diagnosis=diagnosis)

@app.route('/assess', methods=['GET','POST'])
def assess():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method=='POST':
        data = {k: request.form[k] for k in request.form}
        
        risks, score, recs = predictor.predict({
            'bmi':float(data['bmi']), 'sleep_hours':float(data['sleep_hours']), 
            'activity_mins':int(data['activity_mins']), 'stress':int(data['stress']),
            'bp_sys':int(data['bp_sys']), 'bp_dias':int(data['bp_dias']), 'screen_time':float(data['screen_time'])
        })
        
        conn = get_db_connection()
        if conn:
            conn.cursor().execute("INSERT INTO assessments (user_id, overall_score, overall_risk, risk_heart_rate, risk_diabetes, risk_sleep_apnea, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                                  (session['user_id'], score, 'High' if score>70 else 'Low', risks['heart']['level'], risks['diabetes']['level'], risks['sleep']['level']))
            conn.commit()
            conn.close()
            
        d_view = [{'name': 'Heart', 'risk_level': risks['heart']['level'], 'color': risks['heart']['color']},
                  {'name': 'Diabetes', 'risk_level': risks['diabetes']['level'], 'color': risks['diabetes']['color']}]
        return render_template('prediction/result.html', overall_score=score, overall_risk='High' if score>70 else 'Low', diseases=d_view, recommendations={})
    return render_template('prediction/form.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    user = None
    if conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
        user = c.fetchone()
        conn.close()
    return render_template('profile/index.html', user=user)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/download_report')
def download_report():
    if 'user_id' not in session: return redirect(url_for('login'))
    # PDF Logic (Simplified placeholder for brevity, use previous full code if needed)
    return "PDF Download Feature Active"

if __name__ == '__main__':
    init_db()
    print("🚀 Health System Active. Running on Port 5000.")
    app.run(debug=True, port=5000)
