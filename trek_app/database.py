import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "trek_quest.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT,
        avatar_color TEXT DEFAULT '#10b981',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS treks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        region TEXT NOT NULL,
        max_altitude_m INTEGER,
        difficulty TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        distance_km REAL NOT NULL,
        best_season TEXT,
        overview TEXT,
        start_lat REAL NOT NULL,
        start_lng REAL NOT NULL,
        waypoints_json TEXT NOT NULL,
        is_popular INTEGER DEFAULT 1,
        rating REAL DEFAULT 4.8,
        reviews_count INTEGER DEFAULT 0,
        permit_protected_area TEXT,
        permit_fee INTEGER DEFAULT 350
    );

    CREATE TABLE IF NOT EXISTS points_of_interest (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trek_id INTEGER NOT NULL,
        poi_type TEXT NOT NULL,
        name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        description TEXT,
        FOREIGN KEY(trek_id) REFERENCES treks(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sherpas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        experience_years INTEGER NOT NULL,
        languages TEXT NOT NULL,
        speciality_region TEXT,
        rating REAL DEFAULT 4.9,
        phone TEXT,
        badge TEXT,
        assigned_trek_id INTEGER,
        FOREIGN KEY(assigned_trek_id) REFERENCES treks(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS trek_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT UNIQUE NOT NULL,
        trek_id INTEGER NOT NULL,
        created_by_user_id INTEGER,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trek_id) REFERENCES treks(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        squad_role TEXT DEFAULT 'Explorer',
        avatar_color TEXT DEFAULT '#3b82f6',
        current_lat REAL,
        current_lng REAL,
        battery_pct INTEGER DEFAULT 95,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(group_id) REFERENCES trek_groups(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trek_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        trail_condition TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trek_id) REFERENCES treks(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS permits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        permit_code TEXT UNIQUE NOT NULL,
        trek_id INTEGER NOT NULL,
        applicant_name TEXT NOT NULL,
        id_proof_number TEXT NOT NULL,
        status TEXT DEFAULT 'APPROVED',
        issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trek_id) REFERENCES treks(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema successfully created!")
