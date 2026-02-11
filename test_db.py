import os
import psycopg2
from dotenv import load_dotenv

# 1. Load the key from your .env file
load_dotenv()
db_url = os.getenv("DATABASE_URL")

try:
    # 2. Connect to Neon
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # 3. Test a simple query
    cursor.execute("SELECT version();")
    record = cursor.fetchone()
    print(f"Success! You are connected to: {record}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
  
