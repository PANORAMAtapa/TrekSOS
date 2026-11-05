import os
import re
import json
from database import get_db, init_db

TXT_DIR = os.path.join(os.path.dirname(__file__), "data", "treks_txt")

SHERPAS_CATALOG = [
    {
        "name": "Tenzing Dorje",
        "experience_years": 14,
        "languages": "Hindi, English, Garhwali, Tibetan",
        "speciality_region": "Uttarakhand & Garhwal High Passes",
        "rating": 4.96,
        "phone": "+91 98765-43210",
        "badge": "UIAA Certified Alpine Lead Guide & High Altitude First Responder"
    },
    {
        "name": "Pasang Norbu",
        "experience_years": 11,
        "languages": "Hindi, English, Kinnauri, Spitian",
        "speciality_region": "Himachal & Spiti Valleys",
        "rating": 4.92,
        "phone": "+91 98451-22345",
        "badge": "HMI Darjeeling Master Mountaineer & Glacier Rescue Specialist"
    },
    {
        "name": "Kalyan Singh Rawat",
        "experience_years": 16,
        "languages": "Hindi, Garhwali, Kumaoni",
        "speciality_region": "Uttarakhand National Parks",
        "rating": 4.98,
        "phone": "+91 94120-77889",
        "badge": "Senior Wilderness First Responder & Forest Dept Certified Guide"
    },
    {
        "name": "Stanzin Angchuk",
        "experience_years": 9,
        "languages": "Hindi, English, Ladakhi",
        "speciality_region": "Ladakh & Zanskar Trails",
        "rating": 4.89,
        "phone": "+91 99069-12344",
        "badge": "Winter Ice Trek Specialist & Expedition Leader"
    }
]

SAMPLE_REVIEWS = [
    {
        "user_name": "Aarav Sharma",
        "rating": 5,
        "comment": "Mind-blowing experience! The transition from pine forest to snowy col was breathtaking. The trail is well marked.",
        "trail_condition": "Path clear till Camp 3. Light fresh snow near the pass summit, crampons recommended."
    },
    {
        "user_name": "Dr. Sneha Banerjee",
        "rating": 5,
        "comment": "Completed with our 4-person squad. Having offline maps was a lifesaver because Airtel and Jio lost all signal 3km after basecamp.",
        "trail_condition": "Glacial stream at KM 12 has high current after 2 PM; cross early in the morning."
    },
    {
        "user_name": "Rohan Mehra",
        "rating": 4,
        "comment": "Challenging climb on Day 4. The local dhaba near Seema served the most heavenly hot ginger lemon tea.",
        "trail_condition": "Mild loose scree on the descent. Walking poles strongly recommended."
    }
]

def parse_txt_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    data = {}
    
    # Extract Title
    title_match = re.search(r"Trek Name:\s*(.*)", content, re.IGNORECASE)
    data["title"] = title_match.group(1).strip() if title_match else os.path.basename(filepath).replace(".txt", "").replace("-", " ").title()
    data["slug"] = re.sub(r'[^a-zA-Z0-9]+', '-', data["title"].lower()).strip('-')

    # Extract Region
    region_match = re.search(r"Region:\s*(.*)", content, re.IGNORECASE)
    data["region"] = region_match.group(1).strip() if region_match else "Himalayas, India"

    # Extract Max Altitude
    alt_match = re.search(r"Max Altitude:\s*(\d+)\s*m", content, re.IGNORECASE)
    data["max_altitude_m"] = int(alt_match.group(1)) if alt_match else 4000

    # Extract Difficulty / Grade
    diff_match = re.search(r"(?:Grade|Difficulty):\s*(.*)", content, re.IGNORECASE)
    data["difficulty"] = diff_match.group(1).strip() if diff_match else "Moderate"

    # Extract Duration
    dur_match = re.search(r"Duration:\s*(\d+)", content, re.IGNORECASE)
    data["duration_days"] = int(dur_match.group(1)) if dur_match else 5

    # Extract Distance
    dist_match = re.search(r"Total Distance:\s*([\d\.]+)", content, re.IGNORECASE)
    data["distance_km"] = float(dist_match.group(1)) if dist_match else 35.0

    # Extract Best Season
    season_match = re.search(r"Best Season:\s*(.*)", content, re.IGNORECASE)
    data["best_season"] = season_match.group(1).strip() if season_match else "May to October"

    # Extract Overview
    overview_match = re.search(r"Overview:\s*([\s\S]*?)(?=Trail Route Coordinates:|$)", content, re.IGNORECASE)
    data["overview"] = overview_match.group(1).strip() if overview_match else "An awe-inspiring Himalayan trekking expedition."

    # Extract Waypoints JSON
    coords_match = re.search(r"Trail Route Coordinates:\s*(\[[\s\S]*?\])", content, re.IGNORECASE)
    if coords_match:
        try:
            waypoints = json.loads(coords_match.group(1))
        except Exception:
            waypoints = []
    else:
        waypoints = []

    data["waypoints"] = waypoints
    if waypoints:
        data["start_lat"] = waypoints[0].get("lat", 31.0)
        data["start_lng"] = waypoints[0].get("lng", 78.0)
    else:
        data["start_lat"] = 31.0625
        data["start_lng"] = 78.3302

    # Extract Points of interest
    pois = []
    pois_block = re.search(r"Points of Interest:\s*([\s\S]*)$", content, re.IGNORECASE)
    if pois_block:
        lines = pois_block.group(1).strip().split("\n")
        for line in lines:
            if line.strip().startswith("-"):
                # Format: - Type: Cafe | Name: ... | Lat: ... | Lng: ... | Desc: ...
                parts = {}
                for item in line.strip().lstrip("-").split("|"):
                    if ":" in item:
                        k, v = item.split(":", 1)
                        parts[k.strip().lower()] = v.strip()
                if "name" in parts and "lat" in parts and "lng" in parts:
                    try:
                        pois.append({
                            "poi_type": parts.get("type", "Sightseeing"),
                            "name": parts["name"],
                            "latitude": float(parts["lat"]),
                            "longitude": float(parts["lng"]),
                            "description": parts.get("desc", "")
                        })
                    except ValueError:
                        continue
    data["pois"] = pois
    return data

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing data to allow clean re-import
    cursor.execute("DELETE FROM permits")
    cursor.execute("DELETE FROM reviews")
    cursor.execute("DELETE FROM group_members")
    cursor.execute("DELETE FROM trek_groups")
    cursor.execute("DELETE FROM sherpas")
    cursor.execute("DELETE FROM points_of_interest")
    cursor.execute("DELETE FROM treks")
    cursor.execute("DELETE FROM users")

    # 1. Seed Demo Users
    users_to_add = [
        ("summit_seeker", "Arjun Verma (Lead)", "arjun@trekmail.com", "#3b82f6"),
        ("mountain_goat", "Rhea Sen (Medic)", "rhea@trekmail.com", "#10b981"),
        ("trail_blazer", "Kabir Roy (Sweeper)", "kabir@trekmail.com", "#f59e0b"),
        ("shutter_trek", "Ananya Das (Scout)", "ananya@trekmail.com", "#ec4899")
    ]
    cursor.executemany(
        "INSERT INTO users (username, full_name, email, avatar_color) VALUES (?, ?, ?, ?)",
        users_to_add
    )
    conn.commit()

    # 2. Ingest Kaggle Text Files
    txt_files = [f for f in os.listdir(TXT_DIR) if f.endswith(".txt")]
    inserted_treks = []
    sherpa_idx = 0

    for idx, filename in enumerate(sorted(txt_files)):
        filepath = os.path.join(TXT_DIR, filename)
        trek_data = parse_txt_file(filepath)
        
        permit_area = f"Govind & Sanctuary Range Wildlife Eco-Zone #{idx + 104}"
        
        cursor.execute("""
        INSERT INTO treks (
            slug, title, region, max_altitude_m, difficulty, duration_days,
            distance_km, best_season, overview, start_lat, start_lng,
            waypoints_json, is_popular, rating, reviews_count, permit_protected_area, permit_fee
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            trek_data["slug"],
            trek_data["title"],
            trek_data["region"],
            trek_data["max_altitude_m"],
            trek_data["difficulty"],
            trek_data["duration_days"],
            trek_data["distance_km"],
            trek_data["best_season"],
            trek_data["overview"],
            trek_data["start_lat"],
            trek_data["start_lng"],
            json.dumps(trek_data["waypoints"]),
            round(4.7 + (idx * 0.05) % 0.25, 2),
            len(SAMPLE_REVIEWS) + idx * 4,
            permit_area,
            350 + (idx * 50)
        ))
        
        trek_id = cursor.lastrowid
        inserted_treks.append(trek_id)

        # Insert POIs
        for poi in trek_data["pois"]:
            cursor.execute("""
            INSERT INTO points_of_interest (trek_id, poi_type, name, latitude, longitude, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (trek_id, poi["poi_type"], poi["name"], poi["latitude"], poi["longitude"], poi["description"]))

        # Assign a certified Sherpa
        sherpa_info = SHERPAS_CATALOG[sherpa_idx % len(SHERPAS_CATALOG)]
        cursor.execute("""
        INSERT INTO sherpas (name, experience_years, languages, speciality_region, rating, phone, badge, assigned_trek_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sherpa_info["name"],
            sherpa_info["experience_years"],
            sherpa_info["languages"],
            sherpa_info["speciality_region"],
            sherpa_info["rating"],
            sherpa_info["phone"],
            sherpa_info["badge"],
            trek_id
        ))
        sherpa_idx += 1

        # Seed reviews
        for rev in SAMPLE_REVIEWS:
            cursor.execute("""
            INSERT INTO reviews (trek_id, user_name, rating, comment, trail_condition)
            VALUES (?, ?, ?, ?, ?)
            """, (trek_id, rev["user_name"], rev["rating"], rev["comment"], rev["trail_condition"]))

    # 3. Seed an active Multiplayer Trek Group (Room Code: SUMMIT-7)
    if inserted_treks:
        primary_trek_id = inserted_treks[0] # Borasu Pass
        cursor.execute("""
        INSERT INTO trek_groups (room_code, trek_id, created_by_user_id, status)
        VALUES ('SUMMIT-7', ?, 1, 'ACTIVE')
        """, (primary_trek_id,))
        group_id = cursor.lastrowid

        # Seed group members on the trail
        # Fetch the waypoints of the primary trek to place them naturally
        cursor.execute("SELECT waypoints_json FROM treks WHERE id = ?", (primary_trek_id,))
        row = cursor.fetchone()
        wps = json.loads(row["waypoints_json"]) if row else []
        
        if len(wps) >= 3:
            p1 = wps[1] # Seema Camp
            p2 = {"lat": p1["lat"] - 0.003, "lng": p1["lng"] - 0.002}
            p3 = {"lat": p1["lat"] - 0.007, "lng": p1["lng"] - 0.005}
            p4 = {"lat": p1["lat"] - 0.012, "lng": p1["lng"] - 0.008}
        else:
            p1 = {"lat": 31.0625, "lng": 78.3302}
            p2 = {"lat": 31.0610, "lng": 78.3290}
            p3 = {"lat": 31.0595, "lng": 78.3275}
            p4 = {"lat": 31.0570, "lng": 78.3250}

        squad_seed = [
            (group_id, 1, "Arjun Verma", "Lead Navigator", "#3b82f6", p1["lat"], p1["lng"], 88),
            (group_id, 2, "Rhea Sen", "Medic", "#10b981", p2["lat"], p2["lng"], 92),
            (group_id, 3, "Kabir Roy", "Sweeper (Rear Guard)", "#f59e0b", p3["lat"], p3["lng"], 64),
            (group_id, 4, "Ananya Das", "Scout", "#ec4899", p4["lat"], p4["lng"], 77)
        ]
        cursor.executemany("""
        INSERT INTO group_members (group_id, user_id, user_name, squad_role, avatar_color, current_lat, current_lng, battery_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, squad_seed)

    conn.commit()
    conn.close()
    print(f"Successfully parsed {len(txt_files)} Kaggle trek description files and seeded database!")

if __name__ == "__main__":
    seed_database()
