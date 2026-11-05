// Map state and layer management
let map = null;
let trailPolyline = null;
let waypointMarkers = [];
let poiMarkers = [];
let squadMarkers = {}; // member_id -> L.marker
let currentTrekData = null;

// Initialize Leaflet Map
function initMap() {
    if (map) return;

    // Default center in Himalayas (Garhwal / Kinnaur)
    map = L.map('map', {
        zoomControl: true,
        attributionControl: false
    }).setView([31.0625, 78.3302], 12);

    // High quality OpenStreetMap topo / Dark tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '© OpenStreetMap'
    }).addTo(map);

    // Custom attribution badge
    const attr = L.control({position: 'bottomright'});
    attr.onAdd = function() {
        const div = L.DomUtil.create('div', 'map-attr-badge');
        div.innerHTML = `<span style="background:rgba(0,0,0,0.7); color:#94a3b8; font-size:10px; padding:2px 6px; border-radius:4px;">OSM Cartography & Topo Elevation</span>`;
        return div;
    };
    attr.addTo(map);
}

// Render a selected trail onto the map
function loadTrailOnMap(trek) {
    if (!map) initMap();
    currentTrekData = trek;

    // 1. Clear previous trail lines & waypoints
    if (trailPolyline) {
        map.removeLayer(trailPolyline);
        trailPolyline = null;
    }
    waypointMarkers.forEach(m => map.removeLayer(m));
    waypointMarkers = [];

    const waypoints = trek.waypoints || [];
    if (!waypoints.length) return;

    // 2. Build coordinates array for polyline
    const latlngs = waypoints.map(wp => [wp.lat, wp.lng]);

    // Outer glow line
    const glowLine = L.polyline(latlngs, {
        color: '#06b6d4',
        weight: 8,
        opacity: 0.35,
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(map);
    waypointMarkers.push(glowLine);

    // Primary bright trail line
    trailPolyline = L.polyline(latlngs, {
        color: '#10b981',
        weight: 4,
        opacity: 0.95,
        dashArray: '8, 8',
        lineCap: 'round'
    }).addTo(map);

    // 3. Add Waypoint markers along the trail
    waypoints.forEach((wp, idx) => {
        const isStart = idx === 0;
        const isSummit = idx === waypoints.length - 3 || wp.alt >= 4500;
        const isEnd = idx === waypoints.length - 1;

        let iconEmoji = "🏕️";
        let markerColor = "#3b82f6";
        if (isStart) { iconEmoji = "🏁"; markerColor = "#10b981"; }
        else if (isSummit) { iconEmoji = "🚩"; markerColor = "#ef4444"; }
        else if (isEnd) { iconEmoji = "🏁"; markerColor = "#8b5cf6"; }

        const customIcon = L.divIcon({
            className: 'custom-waypoint-icon',
            html: `
                <div style="background:${markerColor}; width:26px; height:26px; border-radius:50%; border:2px solid #fff; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(0,0,0,0.5); font-size:12px;">
                    ${iconEmoji}
                </div>
            `,
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });

        const marker = L.marker([wp.lat, wp.lng], { icon: customIcon }).addTo(map);
        marker.bindPopup(`
            <div style="font-family:'Plus Jakarta Sans',sans-serif; min-width:180px;">
                <strong style="color:#0f172a; font-size:13px;">${wp.name}</strong><br/>
                <span style="color:#64748b; font-size:11px;">Day ${wp.day || idx+1} • Altitude: <strong>${wp.alt} m</strong></span>
            </div>
        `);
        waypointMarkers.push(marker);
    });

    // 4. Smoothly Pan and Zoom map to fit the trail bounds
    map.fitBounds(trailPolyline.getBounds(), { padding: [60, 60], maxZoom: 14 });

    // 5. Render POIs (Cafes, Dhabas, Springs)
    renderPois(trek.pois || []);
}

// Render Cafes, Viewpoints, and Springs
function renderPois(pois) {
    poiMarkers.forEach(m => map.removeLayer(m));
    poiMarkers = [];

    pois.forEach(poi => {
        let emoji = "☕";
        let poiClass = "cafe";
        const typeLower = (poi.poi_type || "").toLowerCase();

        if (typeLower.includes("sight") || typeLower.includes("view")) {
            emoji = "🌄";
            poiClass = "sightseeing";
        } else if (typeLower.includes("spring") || typeLower.includes("water")) {
            emoji = "💧";
            poiClass = "spring";
        } else if (typeLower.includes("dhaba")) {
            emoji = "🍲";
            poiClass = "cafe";
        }

        const poiIcon = L.divIcon({
            className: 'custom-poi-marker',
            html: `<div class="poi-pin ${poiClass}" data-poi-type="${poiClass}">${emoji}</div>`,
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });

        const marker = L.marker([poi.latitude, poi.longitude], { icon: poiIcon }).addTo(map);
        marker.poiType = poiClass;
        marker.bindPopup(`
            <div style="font-family:'Plus Jakarta Sans',sans-serif; min-width:200px;">
                <span style="background:#f1f5f9; color:#475569; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; text-transform:uppercase;">${poi.poi_type}</span>
                <h4 style="margin:4px 0 2px; font-size:13px; color:#0f172a;">${poi.name}</h4>
                <p style="margin:0; font-size:11px; color:#64748b; line-height:1.4;">${poi.description || "Mountain rest point with snacks and fresh refill."}</p>
            </div>
        `);
        poiMarkers.push(marker);
    });
}

// Toggle POI visibility from checkboxes
function togglePoiLayer(type) {
    poiMarkers.forEach(marker => {
        if (marker.poiType === type) {
            if (map.hasLayer(marker)) {
                map.removeLayer(marker);
            } else {
                map.addLayer(marker);
            }
        }
    });
}

// Render and animate squad members on the map
function updateSquadMarkers(members) {
    if (!map) return;

    members.forEach(member => {
        const id = member.id;
        const lat = member.current_lat;
        const lng = member.current_lng;
        const initial = (member.user_name || "T")[0].toUpperCase();
        const role = member.squad_role || "Explorer";
        const color = member.avatar_color || "#3b82f6";

        if (squadMarkers[id]) {
            // Animate move to new coordinates
            squadMarkers[id].setLatLng([lat, lng]);
        } else {
            // Create custom animated avatar marker
            const markerIcon = L.divIcon({
                className: 'custom-squad-marker',
                html: `
                    <div class="marker-pin" style="background:${color};">
                        <span>${initial}</span>
                        <div class="marker-label">${member.user_name.split(' ')[0]}</div>
                    </div>
                `,
                iconSize: [32, 32],
                iconAnchor: [16, 16]
            });

            const marker = L.marker([lat, lng], { icon: markerIcon }).addTo(map);
            marker.bindPopup(`
                <div style="font-family:'Plus Jakarta Sans',sans-serif; min-width:180px;">
                    <strong style="color:#0f172a; font-size:13px;">${member.user_name}</strong><br/>
                    <span style="color:#3b82f6; font-size:11px; font-weight:700;">Role: ${role}</span><br/>
                    <span style="color:#10b981; font-size:11px;">🔋 Battery: ${member.battery_pct || 90}%</span>
                </div>
            `);
            squadMarkers[id] = marker;
        }
    });
}

// Download Trail Offline Pack (Tile Caching Simulation for mountain areas)
function downloadTrailOfflinePack() {
    if (!currentTrekData) return;
    const btn = document.getElementById('btnDownloadOffline');
    const textSpan = document.getElementById('offlineBtnText');
    
    textSpan.innerText = "Downloading...";
    btn.style.borderColor = "#f59e0b";

    setTimeout(() => {
        // Store offline payload in localStorage
        const offlinePack = {
            trekId: currentTrekData.id,
            title: currentTrekData.title,
            waypoints: currentTrekData.waypoints,
            pois: currentTrekData.pois,
            cachedAt: new Date().toISOString(),
            tilesCached: 48 // simulated count of bounding box tiles
        };
        localStorage.setItem(`offline_trek_${currentTrekData.id}`, JSON.stringify(offlinePack));

        textSpan.innerText = "✓ Offline Cached";
        btn.style.borderColor = "#10b981";
        btn.style.color = "#10b981";

        alert(`✅ Offline Trail Pack Downloaded!\n\nTrail: ${currentTrekData.title}\nWaypoints: ${currentTrekData.waypoints.length} route coordinates cached.\nTile Pack: 48 local zoom tiles saved into browser offline cache.`);
    }, 1000);
}

document.getElementById('btnDownloadOffline').addEventListener('click', downloadTrailOfflinePack);
