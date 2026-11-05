// Squad and Multiplayer Room Management
let activeRoomCode = "SUMMIT-7";
let currentUserId = 1;
let currentUserName = "Arjun Verma";
let currentUserRole = "Lead Navigator";
let currentUserColor = "#3b82f6";

let squadMembers = [];
let squadWebSocket = null;
let realGpsWatchId = null;

// Connect to WebSocket for real-time squad communication
function connectSquadWebSocket(roomCode) {
    if (squadWebSocket) {
        squadWebSocket.close();
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/group/${roomCode}`;

    squadWebSocket = new WebSocket(wsUrl);

    squadWebSocket.onopen = () => {
        console.log(`[Squad WebSocket] Connected to room: ${roomCode}`);
    };

    squadWebSocket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleSquadMessage(data);
        } catch (e) {
            console.error("Failed to parse squad message", e);
        }
    };

    squadWebSocket.onclose = () => {
        console.log("[Squad WebSocket] Disconnected. Reconnecting in 3s...");
        setTimeout(() => connectSquadWebSocket(roomCode), 3000);
    };
}

// Process incoming WebSocket broadcasts
function handleSquadMessage(data) {
    if (data.type === "SIMULATED_STEP" || data.type === "LOCATION_UPDATE") {
        fetchGroupData(activeRoomCode);
    } else if (data.type === "MEMBER_JOINED") {
        fetchGroupData(activeRoomCode);
    } else if (data.type === "SOS_ALERT") {
        alert(`🚨 EMERGENCY SOS BROADCAST!\n\nTeammate: ${data.user_name}\nLocation: Lat ${data.latitude.toFixed(4)}, Lng ${data.longitude.toFixed(4)}\nMessage: ${data.message}`);
    }
}

// Fetch group roster & live coordinates from backend
async function fetchGroupData(roomCode) {
    try {
        const res = await fetch(`/api/groups/${roomCode}`);
        if (!res.ok) return;
        const data = await res.json();
        
        activeRoomCode = data.room_code;
        squadMembers = data.members || [];

        // Update UI displays
        document.getElementById('navRoomCodeDisplay').innerText = activeRoomCode;
        document.getElementById('lobbyRoomCode').innerText = activeRoomCode;
        document.getElementById('squadCountLabel').innerText = squadMembers.length;
        document.getElementById('squadRadarStatus').innerText = `${squadMembers.length} Teammates Synced`;

        // Update Map Markers
        if (typeof updateSquadMarkers === "function") {
            updateSquadMarkers(squadMembers);
        }

        // Render Sidebar List & Radar HUD
        renderSquadList();
        renderSquadRadarHud();
    } catch (e) {
        console.error("Failed to load group details", e);
    }
}

// Render members list in sidebar
function renderSquadList() {
    const container = document.getElementById('squadMembersList');
    if (!container) return;

    container.innerHTML = squadMembers.map(m => {
        const isMe = m.id === currentUserId || m.user_name.includes(currentUserName);
        return `
            <div class="squad-member-row">
                <div class="squad-member-left">
                    <div class="avatar" style="background:${m.avatar_color || '#3b82f6'}; width:30px; height:30px; font-size:12px;">
                        ${(m.user_name || "T")[0]}
                    </div>
                    <div>
                        <strong>${m.user_name} ${isMe ? '<span style="color:#10b981; font-size:10px;">(You)</span>' : ''}</strong>
                        <div style="font-size:10px; color:#94a3b8;">${m.squad_role}</div>
                    </div>
                </div>
                <div class="squad-member-meta">
                    <span class="battery-tag">🔋 ${m.battery_pct || 90}%</span>
                </div>
            </div>
        `;
    }).join('');
}

// Render HUD overlay on map with distance-to-lead calculations
function renderSquadRadarHud() {
    const container = document.getElementById('squadHudMembers');
    if (!container) return;

    // Identify Leader location
    const leader = squadMembers.find(m => (m.squad_role || "").toLowerCase().includes("lead")) || squadMembers[0];
    const leaderLat = leader ? leader.current_lat : 0;
    const leaderLng = leader ? leader.current_lng : 0;

    container.innerHTML = squadMembers.map(m => {
        // Calculate distance from leader using Haversine
        const distMeters = Math.round(calculateDistanceMeters(leaderLat, leaderLng, m.current_lat, m.current_lng));
        const isLeader = m.id === (leader ? leader.id : null);
        const isStraggler = distMeters > 150 && !isLeader;

        let distText = isLeader ? "Pace Setter (0m)" : `${distMeters}m behind`;
        let warnClass = isStraggler ? "warning" : "";

        return `
            <div class="hud-member-pill">
                <div class="hud-member-avatar" style="background:${m.avatar_color || '#3b82f6'};">
                    ${(m.user_name || "T")[0]}
                </div>
                <div class="hud-member-info">
                    <span class="hud-member-name">${m.user_name}</span>
                    <span class="hud-dist-badge ${warnClass}">
                        ${isStraggler ? '⚠️ ' : ''}${distText}
                    </span>
                </div>
            </div>
        `;
    }).join('');
}

// Haversine formula to compute meters between two coordinates
function calculateDistanceMeters(lat1, lon1, lat2, lon2) {
    if (!lat1 || !lon1 || !lat2 || !lon2) return 0;
    const R = 6371e3; // Earth radius in meters
    const phi1 = lat1 * Math.PI / 180;
    const phi2 = lat2 * Math.PI / 180;
    const deltaPhi = (lat2 - lat1) * Math.PI / 180;
    const deltaLambda = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
              Math.cos(phi1) * Math.cos(phi2) *
              Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

// Simulation Step trigger (moves squad on trail for demo presentation)
async function triggerSimulationStep() {
    try {
        const res = await fetch(`/api/groups/${activeRoomCode}/simulate_step`, {
            method: 'POST'
        });
        if (res.ok) {
            fetchGroupData(activeRoomCode);
        }
    } catch (e) {
        console.error("Simulation step error", e);
    }
}

// Real HTML5 Geolocation toggle
function toggleRealGps(enabled) {
    if (!navigator.geolocation) {
        alert("Geolocation API is not supported in this browser.");
        return;
    }

    if (enabled) {
        realGpsWatchId = navigator.geolocation.watchPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                // Broadcast to backend
                fetch(`/api/groups/${activeRoomCode}/location`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        member_id: currentUserId,
                        latitude: lat,
                        longitude: lng,
                        battery_pct: 95
                    })
                });
            },
            (err) => {
                console.warn("GPS error:", err.message);
                alert("Could not access live device GPS: " + err.message + ". You can use 'Simulate Live Walk' instead!");
                document.getElementById('gpsLiveToggle').checked = false;
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    } else {
        if (realGpsWatchId) {
            navigator.geolocation.clearWatch(realGpsWatchId);
            realGpsWatchId = null;
        }
    }
}

// Emergency SOS Ping button
document.getElementById('btnSOS').addEventListener('click', async () => {
    const me = squadMembers.find(m => m.id === currentUserId) || squadMembers[0];
    const lat = me ? me.current_lat : 31.0625;
    const lng = me ? me.current_lng : 78.3302;

    await fetch(`/api/groups/${activeRoomCode}/sos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            member_id: currentUserId,
            user_name: currentUserName,
            latitude: lat,
            longitude: lng,
            message: "Trekkers need assistance near high trail zone!"
        })
    });
});

// Setup Demo Simulate button in top navbar
document.getElementById('btnSimulate').addEventListener('click', triggerSimulationStep);
