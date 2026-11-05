# 🏔️ TrekQuest: Smart Mountain GPS & Squad Trail Navigation

> **College Capstone Project**  
> An innovative high-altitude trekking platform featuring **multiplayer squad room lobbies (like online gaming)**, **offline trail tile caching**, **raw Kaggle text dataset ETL pipeline**, **real-time mountain POIs**, and **government protected-area e-clearance**.

---

## 🌟 Key Innovations & Features

1. **Multiplayer Squad Room Code (`SUMMIT-7`)**:
   - Similar to an *Among Us* or *PUBG* lobby, members join a squad using a 6-digit room code.
   - Live location sharing on the mountain trail with role badges (*Lead Navigator, Scout, Medic, Sweeper*).
   - **Distance-to-Leader Radar**: Computes real-time separation using the Haversine formula; flags an automatic **"⚠️ Straggler Warning"** if any member falls more than 150m behind!
   - **Demo Simulator**: A "Simulate Live Walk" button moves teammates along the trail during a classroom viva presentation.

2. **Kaggle 250 Trek Dataset ETL Ingestion**:
   - Ingests unstructured `.txt` files from the [Kaggle 250 Trek Description Dataset](https://www.kaggle.com/datasets/iamrahulpatil/250-trek-description) (including *Borasu Pass*, *Hampta Pass*, *Kedarkantha*, *Roopkund*).
   - Regex-based Python pipeline transforms unstructured mountain lore into structured SQLite records.

3. **Complete Functional Leaflet Map & Offline Trail Pack**:
   - High-contrast topographic OpenStreetMap view with custom waypoint pins (Basecamp, River crossing, Summit Col).
   - **"Offline Pack Download"**: Caches trail coordinates, bounding box zoom tiles, and POIs into browser storage for zero-connectivity zones.

4. **Real-Time Mountain Cafes & Sightseeing POIs**:
   - Interactive POI filters for ☕ *Mountain Dhabas & Cafes* (hot maggi, tea), 🌄 *Scenic Viewpoints*, 💧 *Natural Glacial Springs*, and 🏕️ *Alpine Campsites*.

5. **Auto-Assigned Certified Sherpa / Alpine Guide**:
   - Automatically pairs the trail with a certified guide (UIAA / HMI Darjeeling Master Mountaineers) with contact radio frequency, language skills, and safety badges.

6. **Prototype Government Protected-Area Clearance (No QR needed)**:
   - Dedicated digital clearance section showing official Ministry Forest Sanctuary approval status, eco-quota allocations, environmental tax receipt, and emergency VHF bands.

7. **Trekkers Feedback & Condition Reporting**:
   - Past trekker ratings, trail difficulty comments, and live trail hazard reports (*e.g., "Loose scree on descent"*, *"Glacial stream high current"*).

---

## 🏗️ Technology Stack

- **Backend**: Python 3.14 + **FastAPI** + **Uvicorn**
- **Real-Time Sync**: WebSockets (`/ws/group/{room_code}`)
- **Database**: **SQLite** (Medium complexity schema with 7 relational tables & WAL mode)
- **Frontend**: Responsive Single Page App (HTML5, Vanilla ES6+, CSS3 Glassmorphism)
- **Mapping**: **Leaflet.js** + OpenStreetMap Topo layers + Haversine Geospatial computation

---

## 🚀 How to Run the Project

1. Open your terminal in the `trek_app` folder:
   ```powershell
   cd "trek_app"
   python run.py
   ```
2. Open your web browser at:
   ```
   http://127.0.0.1:8000
   ```

3. **Presentation / Viva Tips**:
   - **Show Discovery**: Browse popular trails (Borasu Pass, Hampta Pass, Kedarkantha, Roopkund) and filter by "High Passes" or "Snow".
   - **Show Interactive Map**: Click any trail card — watch the map automatically pan and animate the polyline route with waypoints and dhabas.
   - **Show Live Squad**: Click **"Simulate Live Walk"** on the top bar — observe the 4 teammates move on the map and watch the **Squad Distance Radar HUD** at the bottom calculate their distances in real-time.
   - **Show Govt Permit**: Click the **"Govt Permit"** tab in the right panel to show the protected area clearance certificate.
   - **Show Feedback**: Post a new trail condition report under the **"Reviews"** tab.
