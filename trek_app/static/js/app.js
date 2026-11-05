// Main Application Bootstrap & UI Controller
let allTreks = [];
let activeTrekId = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize Map
    initMap();

    // 2. Load Popular & Recommended Trails
    await loadPopularTrails();

    // 3. Connect Squad Room WebSocket & fetch initial lobby
    connectSquadWebSocket(activeRoomCode);
    await fetchGroupData(activeRoomCode);

    // 4. Setup Filter Pills
    setupFilterPills();
});

// Fetch and render the popular & recommended hiking trails
async function loadPopularTrails() {
    try {
        const [popularRes, recRes] = await Promise.all([
            fetch('/api/treks'),
            fetch('/api/treks/recommended')
        ]);
        
        allTreks = await popularRes.json();
        const recommendedTreks = await recRes.json();

        // Merge recommendation tags
        const recMap = {};
        recommendedTreks.forEach(r => recMap[r.id] = r.recommendation_tag);
        allTreks.forEach(t => t.recTag = recMap[t.id] || "Featured Classic");

        renderTrailCards(allTreks);

        // Auto-select and open the first trail on app launch
        if (allTreks.length > 0) {
            selectTrek(allTreks[0].id);
        }
    } catch (e) {
        console.error("Failed to load trails:", e);
        document.getElementById('popularTrailsList').innerHTML = `<div style="color:#ef4444; padding:10px;">Failed to load trail database.</div>`;
    }
}

// Render the trail cards in the horizontal carousel
function renderTrailCards(treksToRender) {
    const container = document.getElementById('popularTrailsList');
    if (!container) return;

    if (!treksToRender.length) {
        container.innerHTML = `<div style="color:#94a3b8; padding:12px;">No trails match this category.</div>`;
        return;
    }

    container.innerHTML = treksToRender.map(trek => {
        const isSelected = trek.id === activeTrekId;
        return `
            <div class="trail-card ${isSelected ? 'selected' : ''}" onclick="selectTrek(${trek.id})">
                <div>
                    <div class="card-top">
                        <span class="trail-badge-rec">${trek.recTag}</span>
                        <span class="trail-rating">★ ${trek.rating}</span>
                    </div>
                    <h3 class="card-title">${trek.title}</h3>
                    <p class="card-region">📍 ${trek.region}</p>
                </div>

                <div>
                    <div class="card-metrics">
                        <div class="metric-item">
                            <span>ALTITUDE</span>
                            <span>${trek.max_altitude_m} m</span>
                        </div>
                        <div class="metric-item">
                            <span>DISTANCE</span>
                            <span>${trek.distance_km} km</span>
                        </div>
                        <div class="metric-item">
                            <span>DAYS</span>
                            <span>${trek.duration_days}D</span>
                        </div>
                        <div class="metric-item">
                            <span>GRADE</span>
                            <span>${trek.difficulty.split(' ')[0]}</span>
                        </div>
                    </div>

                    <button class="card-action-btn">
                        <span>🗺️</span> Open On Map
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Select a trail: Opens in map and populates all sidebar details
async function selectTrek(trekId) {
    activeTrekId = trekId;

    // Highlight selected card in list
    document.querySelectorAll('.trail-card').forEach(el => el.classList.remove('selected'));
    renderTrailCards(allTreks);

    try {
        const res = await fetch(`/api/treks/${trekId}`);
        if (!res.ok) return;
        const trek = await res.json();

        // 1. Update Map with trail path and POIs
        loadTrailOnMap(trek);

        // 2. Update Map Top Bar Info
        document.getElementById('mapTrailTitle').innerText = `${trek.title} (${trek.max_altitude_m.toLocaleString()} m)`;
        document.getElementById('mapTrailSubtitle').innerText = `${trek.distance_km} km • ${trek.duration_days} Days • ${trek.region}`;

        // 3. Update Overview Stats
        document.getElementById('statElevation').innerText = `${trek.max_altitude_m.toLocaleString()} m`;
        document.getElementById('statDifficulty').innerText = trek.difficulty;
        document.getElementById('statDistance').innerText = `${trek.distance_km} km`;
        document.getElementById('statSeason').innerText = trek.best_season;
        document.getElementById('trailOverviewText').innerText = trek.overview;

        // 4. Update Sherpa Guide info
        if (trek.sherpa) {
            document.getElementById('sherpaName').innerText = trek.sherpa.name;
            document.getElementById('sherpaExp').innerText = `${trek.sherpa.experience_years} Yrs Exp • ${trek.sherpa.rating} ★ Rating`;
            document.getElementById('sherpaBadge').innerText = `🏅 ${trek.sherpa.badge}`;
            document.getElementById('sherpaLang').innerText = trek.sherpa.languages;
            document.getElementById('sherpaPhone').innerText = trek.sherpa.phone;
        }

        // 5. Update POI Mini List
        renderPoiMiniList(trek.pois || []);

        // 6. Update Government Permit Details (Prototype Section)
        if (trek.permit_clearance) {
            document.getElementById('permitRefCode').innerText = trek.permit_clearance.permit_code;
            document.getElementById('permitArea').innerText = trek.permit_clearance.protected_area;
            document.getElementById('permitQuota').innerText = trek.permit_clearance.eco_quota_today;
            document.getElementById('permitRadio').innerText = trek.permit_clearance.emergency_radio_channel;
        }

        // 7. Update Reviews
        document.getElementById('reviewsCountBadge').innerText = (trek.reviews || []).length;
        renderReviews(trek.reviews || []);

    } catch (e) {
        console.error("Failed to load trek details", e);
    }
}

// Render POI items in sidebar
function renderPoiMiniList(pois) {
    const container = document.getElementById('poiMiniList');
    if (!container) return;

    if (!pois.length) {
        container.innerHTML = `<span style="font-size:11px; color:#94a3b8;">No dhabas registered along this pass section.</span>`;
        return;
    }

    container.innerHTML = pois.map(p => {
        let icon = "☕";
        const t = (p.poi_type || "").toLowerCase();
        if (t.includes("view") || t.includes("sight")) icon = "🌄";
        if (t.includes("spring") || t.includes("water")) icon = "💧";
        if (t.includes("dhaba")) icon = "🍲";

        return `
            <div class="poi-item">
                <div>
                    <span class="poi-type-icon">${icon}</span>
                    <strong>${p.name}</strong>
                    <div style="font-size:10px; color:#64748b;">${p.description}</div>
                </div>
            </div>
        `;
    }).join('');
}

// Render past reviews and live trail conditions
function renderReviews(reviews) {
    const container = document.getElementById('reviewsContainer');
    if (!container) return;

    if (!reviews.length) {
        container.innerHTML = `<p style="font-size:12px; color:#94a3b8;">No reviews yet. Be the first to report conditions!</p>`;
        return;
    }

    container.innerHTML = reviews.map(r => `
        <div class="review-item">
            <div class="review-top">
                <strong>${r.user_name}</strong>
                <span class="review-stars">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)}</span>
            </div>
            <p class="review-text">${r.comment}</p>
            ${r.trail_condition ? `<span class="review-condition-tag">⚠️ Trail: ${r.trail_condition}</span>` : ''}
        </div>
    `).join('');
}

// Handle submitting a review
async function handleReviewSubmit(e) {
    e.preventDefault();
    if (!activeTrekId) return;

    const author = document.getElementById('reviewAuthor').value.trim();
    const rating = parseInt(document.getElementById('reviewRating').value);
    const condition = document.getElementById('reviewCondition').value.trim();
    const comment = document.getElementById('reviewComment').value.trim();

    try {
        const res = await fetch(`/api/treks/${activeTrekId}/reviews`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_name: author,
                rating: rating,
                comment: comment,
                trail_condition: condition
            })
        });

        if (res.ok) {
            alert("✅ Feedback and trail condition submitted!");
            document.getElementById('reviewComment').value = '';
            document.getElementById('reviewCondition').value = '';
            selectTrek(activeTrekId); // Refresh details
        }
    } catch (err) {
        console.error("Failed to submit review", err);
    }
}

// Tab Switching
function switchSidebarTab(tabName) {
    document.querySelectorAll('.sidebar-tabs .tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    const tabId = 'tab' + tabName.charAt(0).toUpperCase() + tabName.slice(1);
    const targetContent = document.getElementById(tabId);
    if (targetContent) targetContent.classList.add('active');

    // Highlight button
    event.target.classList.add('active');
}

// Filter pills
function setupFilterPills() {
    document.querySelectorAll('.pill').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');

            const filter = btn.getAttribute('data-filter');
            if (filter === 'all') {
                renderTrailCards(allTreks);
            } else if (filter === 'high-pass') {
                renderTrailCards(allTreks.filter(t => t.max_altitude_m >= 5000));
            } else if (filter === 'snow') {
                renderTrailCards(allTreks.filter(t => t.title.toLowerCase().includes('winter') || t.slug.includes('kedarkantha')));
            } else if (filter === 'moderate') {
                renderTrailCards(allTreks.filter(t => t.difficulty.toLowerCase().includes('moderate')));
            }
        });
    });
}

// Squad Modal Helpers
function openSquadModal() {
    switchSidebarTab('squad');
}

function openCreateRoomModal() {
    document.getElementById('createRoomModal').classList.add('active');
}

function openJoinRoomModal() {
    document.getElementById('joinRoomModal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

async function submitCreateRoom() {
    const leaderName = document.getElementById('createLeaderName').value.trim() || "Arjun Verma";
    const leaderRole = document.getElementById('createLeaderRole').value;

    try {
        const res = await fetch('/api/groups/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                trek_id: activeTrekId || 1,
                user_name: leaderName,
                squad_role: leaderRole
            })
        });

        if (res.ok) {
            const data = await res.json();
            activeRoomCode = data.room_code;
            currentUserId = data.member_id;
            currentUserName = leaderName;
            currentUserRole = leaderRole;

            closeModal('createRoomModal');
            connectSquadWebSocket(activeRoomCode);
            await fetchGroupData(activeRoomCode);
            alert(`🎉 Squad Room Created!\n\nRoom Code: ${data.room_code}\nShare this code with your friends to join!`);
        }
    } catch (e) {
        console.error("Create room error", e);
    }
}

async function submitJoinRoom() {
    const code = document.getElementById('joinRoomCode').value.trim();
    const name = document.getElementById('joinUserName').value.trim();
    const role = document.getElementById('joinUserRole').value;

    if (!code || !name) {
        alert("Please enter both the Room Code and your name.");
        return;
    }

    try {
        const res = await fetch('/api/groups/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_code: code,
                user_name: name,
                squad_role: role
            })
        });

        if (res.ok) {
            const data = await res.json();
            activeRoomCode = data.room_code;
            currentUserId = data.member_id;
            currentUserName = name;
            currentUserRole = role;

            closeModal('joinRoomModal');
            connectSquadWebSocket(activeRoomCode);
            await fetchGroupData(activeRoomCode);
            alert(`Joined squad room ${data.room_code}! Your marker is now live on the trail map.`);
        } else {
            alert("Squad room not found. Check the code and try again.");
        }
    } catch (e) {
        console.error("Join room error", e);
    }
}
