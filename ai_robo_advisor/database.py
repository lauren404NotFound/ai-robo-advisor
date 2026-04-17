"""
database.py
===========
SQLite-based persistence layer for DeepAtomicIQ.
Stores user credentials (hashed) and historical assessment responses.
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime


# Absolute path for the database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robo_advisor.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        dob TEXT,
        preferences_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Assessments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        answers_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_email) REFERENCES users (email)
    )
    """)
    
    # Tickets table for Support inquiries
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_email) REFERENCES users (email)
    )
    """)
    
    # Gracefully add the provider column to existing DB without nuking it
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN provider TEXT DEFAULT 'email'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, name, password, dob, provider="email"):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, name, password_hash, dob, provider) VALUES (?, ?, ?, ?, ?)",
            (email, name, hash_password(password), dob, provider)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def create_user_oauth(email, name, provider):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, name, password_hash, dob, provider) VALUES (?, ?, ?, ?, ?)",
            (email, name, "OAUTH_BYPASS", None, provider)  # Dummy hash because DB requires NOT NULL
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_user_preferences(email, preferences: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET preferences_json = ? WHERE email = ?",
        (json.dumps(preferences), email)
    )
    conn.commit()
    conn.close()

def get_user(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email, name, password_hash, dob, provider FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {
            "email": user[0], 
            "name": user[1], 
            "password_hash": user[2], 
            "dob": user[3],
            "provider": user[4]
        }
    return None

def save_assessment(email, answers: dict, result: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO assessments (user_email, answers_json, result_json) VALUES (?, ?, ?)",
        (email, json.dumps(answers), json.dumps(result))
    )
    conn.commit()
    conn.close()

def save_ticket(email, subject, message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tickets (user_email, subject, message) VALUES (?, ?, ?)",
        (email, subject, message)
    )
    conn.commit()
    conn.close()

def get_latest_assessment(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT answers_json, result_json FROM assessments WHERE user_email = ? ORDER BY created_at DESC LIMIT 1",
        (email,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "answers": json.loads(row[0]),
            "result": json.loads(row[1])
        }
    return None

# Initialize on import
init_db()
