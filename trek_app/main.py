import os
import json
import random
import string
import asyncio
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import get_db, init_db
from kaggle_parser import seed_database

app = FastAPI(title="TrekQuest API", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# WebSocket Connection Manager for Multiplayer Squads
class ConnectionManager:
    def __init__(self):
        # room_code -> list of active WebSockets
        self.active_rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_code: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.active_rooms:
            self.active_rooms[room_code] = []
        self.active_rooms[room_code].append(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.active_rooms:
            if websocket in self.active_rooms[room_code]:
                self.active_rooms[room_code].remove(websocket)
            if not self.active_rooms[room_code]:
                del self.active_rooms[room_code]

    async def broadcast_to_room(self, room_code: str, message: dict):
        if room_code in self.active_rooms:
            dead_connections = []
            for connection in self.active_rooms[room_code]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect(room_code, dead)

manager = ConnectionManager()

# Pydantic Schemas
class CreateGroupRequest(BaseModel):
    trek_id: int
    user_name: str
    squad_role: Optional[str] = "Lead Navigator"
    avatar_color: Optional[str] = "#3b82f6"

class JoinGroupRequest(BaseModel):
    room_code: str
    user_name: str
    squad_role: Optional[str] = "Explorer"
    avatar_color: Optional[str] = "#10b981"

class UpdateLocationRequest(BaseModel):
    member_id: int
    latitude: float
    longitude: float
    battery_pct: Optional[int] = 90

class SOSRequest(BaseModel):
    member_id: int
    user_name: str
    latitude: float
    longitude: float
    message: Optional[str] = "Emergency SOS Alert Triggered!"

class AddReviewRequest(BaseModel):
    user_name: str
    rating: int
    comment: str
    trail_condition: Optional[str] = "Good"


# ---------------- API ENDPOINTS ----------------

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/api/treks")
def get_popular_treks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, slug, title, region, max_altitude_m, difficulty, duration_days,
           distance_km, best_season, overview, start_lat, start_lng, is_popular, rating, reviews_count
    FROM treks
    ORDER BY is_popular DESC, rating DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/treks/recommended")
def get_recommended_treks():
    conn = get_db()
    cursor = conn.cursor()
    # Provide recommendations with badges like "Beginner Friendly", "Peak Adventure", "Snow Summit"
    cursor.execute("""
    SELECT id, slug, title, region, max_altitude_m, difficulty, duration_days,
           distance_km, best_season, overview, rating, reviews_count
    FROM treks
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    for r in rows:
        if r["max_altitude_m"] >= 5000:
            r["recommendation_tag"] = "High Altitude Thrill"
        elif "winter" in r["title"].lower() or "kedarkantha" in r["slug"].lower():
            r["recommendation_tag"] = "Top Snow Summit"
        elif r["difficulty"].lower().startswith("easy"):
            r["recommendation_tag"] = "Best For Beginners"
        else:
            r["recommendation_tag"] = "Scenic Valley Classic"
    return rows

@app.get("/api/treks/{identifier}")
def get_trek_details(identifier: str):
    conn = get_db()
    cursor = conn.cursor()
    
    if identifier.isdigit():
        cursor.execute("SELECT * FROM treks WHERE id = ?", (int(identifier),))
    else:
        cursor.execute("SELECT * FROM treks WHERE slug = ?", (identifier,))
    
    trek_row = cursor.fetchone()
    if not trek_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Trek not found")
    
    trek = dict(trek_row)
    trek["waypoints"] = json.loads(trek["waypoints_json"])
    del trek["waypoints_json"]

    # Fetch POIs
    cursor.execute("""
    SELECT id, poi_type, name, latitude, longitude, description
    FROM points_of_interest WHERE trek_id = ?
    """, (trek["id"],))
    trek["pois"] = [dict(r) for r in cursor.fetchall()]

    # Fetch Sherpa
    cursor.execute("""
    SELECT id, name, experience_years, languages, speciality_region, rating, phone, badge
    FROM sherpas WHERE assigned_trek_id = ?
    LIMIT 1
    """, (trek["id"],))
    sherpa_row = cursor.fetchone()
    trek["sherpa"] = dict(sherpa_row) if sherpa_row else None

    # Fetch Reviews
    cursor.execute("""
    SELECT id, user_name, rating, comment, trail_condition, created_at
    FROM reviews WHERE trek_id = ?
    ORDER BY id DESC
    """, (trek["id"],))
    trek["reviews"] = [dict(r) for r in cursor.fetchall()]

    # Prototype Protected Area Government Permit info
    trek["permit_clearance"] = {
        "protected_area": trek["permit_protected_area"] or "Himalayan Forest Bio-Reserve",
        "permit_code": f"IND-FOR-{trek['id']*100 + 42}-CLR",
        "authority": "Ministry of Environment, Forest & Climate Change (Himalayan Division)",
        "status": "CLEARANCE_GRANTED_ACTIVE",
        "environmental_tax_status": "Paid (Swachh Bharat Trekker Pass)",
        "eco_quota_today": f"{random.randint(12, 18)} of 35 permits issued",
        "emergency_radio_channel": "VHF 144.800 MHz (Local Forest Guard Post)",
        "badge_title": "Eco-Certified Himalayan Trail"
    }

    conn.close()
    return trek

@app.post("/api/treks/{trek_id}/reviews")
def add_review(trek_id: int, req: AddReviewRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO reviews (trek_id, user_name, rating, comment, trail_condition)
    VALUES (?, ?, ?, ?, ?)
    """, (trek_id, req.user_name, req.rating, req.comment, req.trail_condition))
    
    # Update trek review count & re-average rating
    cursor.execute("SELECT AVG(rating), COUNT(id) FROM reviews WHERE trek_id = ?", (trek_id,))
    avg_rating, count = cursor.fetchone()
    cursor.execute("""
    UPDATE treks SET rating = ?, reviews_count = ? WHERE id = ?
    """, (round(avg_rating or 5.0, 2), count, trek_id))
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Review added successfully"}


# ---------------- MULTIPLAYER SQUAD / ROOM CODE ----------------

@app.post("/api/groups/create")
async def create_group(req: CreateGroupRequest):
    conn = get_db()
    cursor = conn.cursor()
    
    # Generate 6-char room code like 'TREK-7B'
    chars = string.ascii_uppercase + "23456789"
    suffix = "".join(random.choices(chars, k=3))
    room_code = f"TREK-{suffix}"

    cursor.execute("""
    INSERT INTO trek_groups (room_code, trek_id, status)
    VALUES (?, ?, 'ACTIVE')
    """, (room_code, req.trek_id))
    group_id = cursor.lastrowid

    # Place member at trek start coordinates
    cursor.execute("SELECT start_lat, start_lng FROM treks WHERE id = ?", (req.trek_id,))
    t_row = cursor.fetchone()
    start_lat = t_row["start_lat"] if t_row else 31.0625
    start_lng = t_row["start_lng"] if t_row else 78.3302

    cursor.execute("""
    INSERT INTO group_members (group_id, user_name, squad_role, avatar_color, current_lat, current_lng, battery_pct)
    VALUES (?, ?, ?, ?, ?, ?, 98)
    """, (group_id, req.user_name, req.squad_role or "Lead Navigator", req.avatar_color or "#3b82f6", start_lat, start_lng))
    member_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "room_code": room_code,
        "group_id": group_id,
        "member_id": member_id,
        "squad_role": req.squad_role or "Lead Navigator"
    }

@app.post("/api/groups/join")
async def join_group(req: JoinGroupRequest):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, trek_id FROM trek_groups WHERE room_code = ?", (req.room_code.strip().upper(),))
    group = cursor.fetchone()
    if not group:
        conn.close()
        raise HTTPException(status_code=404, detail="Squad room code not found!")

    group_id = group["id"]
    trek_id = group["trek_id"]

    cursor.execute("SELECT start_lat, start_lng FROM treks WHERE id = ?", (trek_id,))
    t_row = cursor.fetchone()
    # Offset slightly so markers don't overlap exactly
    lat_offset = random.uniform(-0.002, 0.002)
    lng_offset = random.uniform(-0.002, 0.002)
    current_lat = (t_row["start_lat"] if t_row else 31.0625) + lat_offset
    current_lng = (t_row["start_lng"] if t_row else 78.3302) + lng_offset

    cursor.execute("""
    INSERT INTO group_members (group_id, user_name, squad_role, avatar_color, current_lat, current_lng, battery_pct)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (group_id, req.user_name, req.squad_role, req.avatar_color or "#10b981", current_lat, current_lng, random.randint(70, 95)))
    member_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Broadcast new member joined via WebSocket
    await manager.broadcast_to_room(req.room_code.strip().upper(), {
        "type": "MEMBER_JOINED",
        "member": {
            "id": member_id,
            "user_name": req.user_name,
            "squad_role": req.squad_role,
            "current_lat": current_lat,
            "current_lng": current_lng
        }
    })

    return {
        "status": "success",
        "room_code": req.room_code.strip().upper(),
        "group_id": group_id,
        "member_id": member_id,
        "trek_id": trek_id
    }

@app.get("/api/groups/{room_code}")
def get_group_details(room_code: str):
    conn = get_db()
    cursor = conn.cursor()
    code = room_code.strip().upper()
    cursor.execute("SELECT id, room_code, trek_id, status, created_at FROM trek_groups WHERE room_code = ?", (code,))
    group = cursor.fetchone()
    if not group:
        conn.close()
        raise HTTPException(status_code=404, detail="Room code not found")

    g_dict = dict(group)

    # Fetch associated trek summary
    cursor.execute("SELECT id, title, slug, region, max_altitude_m, waypoints_json FROM treks WHERE id = ?", (g_dict["trek_id"],))
    trek_row = cursor.fetchone()
    if trek_row:
        g_dict["trek"] = {
            "id": trek_row["id"],
            "title": trek_row["title"],
            "slug": trek_row["slug"],
            "region": trek_row["region"],
            "max_altitude_m": trek_row["max_altitude_m"],
            "waypoints": json.loads(trek_row["waypoints_json"])
        }

    # Fetch members
    cursor.execute("""
    SELECT id, user_name, squad_role, avatar_color, current_lat, current_lng, battery_pct, last_seen
    FROM group_members WHERE group_id = ?
    """, (g_dict["id"],))
    g_dict["members"] = [dict(m) for m in cursor.fetchall()]

    conn.close()
    return g_dict

@app.post("/api/groups/{room_code}/location")
async def update_location(room_code: str, req: UpdateLocationRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE group_members
    SET current_lat = ?, current_lng = ?, battery_pct = ?, last_seen = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (req.latitude, req.longitude, req.battery_pct, req.member_id))
    conn.commit()
    conn.close()

    # Real-time WebSocket broadcast to all teammates
    await manager.broadcast_to_room(room_code.strip().upper(), {
        "type": "LOCATION_UPDATE",
        "member_id": req.member_id,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "battery_pct": req.battery_pct
    })

    return {"status": "success"}

@app.post("/api/groups/{room_code}/sos")
async def broadcast_sos(room_code: str, req: SOSRequest):
    # Immediate emergency ping to all squad members
    await manager.broadcast_to_room(room_code.strip().upper(), {
        "type": "SOS_ALERT",
        "member_id": req.member_id,
        "user_name": req.user_name,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "message": req.message
    })
    return {"status": "broadcasted"}

@app.post("/api/groups/{room_code}/simulate_step")
async def simulate_step(room_code: str):
    """
    Simulation feature: Steps the members along their trail coordinates.
    Essential for presenting the live squad tracking feature during a college viva demo!
    """
    conn = get_db()
    cursor = conn.cursor()
    code = room_code.strip().upper()
    cursor.execute("SELECT id, trek_id FROM trek_groups WHERE room_code = ?", (code,))
    group = cursor.fetchone()
    if not group:
        conn.close()
        raise HTTPException(status_code=404, detail="Room not found")

    cursor.execute("SELECT waypoints_json FROM treks WHERE id = ?", (group["trek_id"],))
    trek_row = cursor.fetchone()
    waypoints = json.loads(trek_row["waypoints_json"]) if trek_row else []

    cursor.execute("SELECT id, user_name, current_lat, current_lng, battery_pct FROM group_members WHERE group_id = ?", (group["id"],))
    members = [dict(m) for m in cursor.fetchall()]

    updated_members = []
    for idx, m in enumerate(members):
        # Nudge coordinates along waypoints or jitter realistically
        lat_shift = random.uniform(0.0008, 0.0018) * (1 if idx % 2 == 0 else -0.8)
        lng_shift = random.uniform(0.0008, 0.0018) * (1 if idx % 2 == 0 else 0.9)
        new_lat = round(m["current_lat"] + lat_shift, 6)
        new_lng = round(m["current_lng"] + lng_shift, 6)
        new_battery = max(20, (m["battery_pct"] or 90) - random.randint(0, 1))

        cursor.execute("""
        UPDATE group_members
        SET current_lat = ?, current_lng = ?, battery_pct = ?, last_seen = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (new_lat, new_lng, new_battery, m["id"]))

        updated_members.append({
            "id": m["id"],
            "user_name": m["user_name"],
            "current_lat": new_lat,
            "current_lng": new_lng,
            "battery_pct": new_battery
        })

    conn.commit()
    conn.close()

    await manager.broadcast_to_room(code, {
        "type": "SIMULATED_STEP",
        "members": updated_members
    })

    return {"status": "stepped", "updated_members": updated_members}

# ---------------- WEBSOCKET ENDPOINT ----------------

@app.websocket("/ws/group/{room_code}")
async def websocket_group_endpoint(websocket: WebSocket, room_code: str):
    code = room_code.strip().upper()
    await manager.connect(code, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                # Echo / broadcast incoming updates to all peers in room
                await manager.broadcast_to_room(code, payload)
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
        await manager.broadcast_to_room(code, {"type": "PEER_DISCONNECTED"})

# ---------------- KAGGLE ETL / RE-SYNC API ----------------

@app.post("/api/treks/reparse")
def trigger_reparse():
    seed_database()
    return {"status": "success", "message": "Parsed all Kaggle text files & updated database successfully!"}

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
