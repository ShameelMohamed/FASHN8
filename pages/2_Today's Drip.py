import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore
import json
import datetime

st.set_page_config(page_title="Today's Drip", layout="wide")
st.title("Today's Drip")
bg_url = "https://logincdn.msftauth.net/shared/5/images/fluent_web_dark_2_bf5f23287bc9f60c9be2.svg"

# Apply background using custom CSS
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("{bg_url}");
        background-attachment: fixed;
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
    }}
    header {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Firebase init (Backend) ---
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Authentication check ---
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access this page.")
    if st.button("Login", use_container_width=True):
        st.switch_page("Home.py")
    st.stop()

# --- Sidebar user info ---
if st.session_state.get('authentication_status'):
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['authentication_status'] = False
        st.session_state['username'] = None
        st.session_state['show_login_form'] = False
        st.session_state['show_signup_form'] = False
        st.rerun()

# --- Fetch clothing data & DOCUMENT ID ---
users_ref = db.collection('users')
query = users_ref.where('username', '==', st.session_state['username']).limit(1)
user_docs = query.get()

if not user_docs:
    st.error("No clothing data found for this user.")
    st.stop()

# THE FIX: Grab the exact document ID to pass to the frontend
user_doc_id = user_docs[0].id 
user_data = user_docs[0].to_dict()

# Match exact keys from your Firestore schema
shirts_data = user_data.get("shirts", {})
pants_data = user_data.get("pant", {}) # DB uses "pant"

shirts_json = json.dumps(shirts_data)
pants_json = json.dumps(pants_data)

current_day = datetime.datetime.now().strftime('%A').lower()

# --- HTML + JS (Full 3D Carousel & AI Logic) ---
carousel_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
body {{ background: transparent; font-family: 'Inter', "Segoe UI", sans-serif; color: white; margin: 0; padding: 0; }}
.top-bar {{ display: flex; justify-content: center; align-items: center; padding: 20px; }}
.toggle-btn {{ padding: 12px 24px; background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); color: white; border-radius: 30px; cursor: pointer; font-size: 16px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
.toggle-btn:hover {{ background: rgba(255, 255, 255, 0.2); transform: translateY(-2px); }}
.carousel-container {{ width: 100%; height: 450px; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
.carousel {{ position: relative; width: 100%; height: 100%; }}
.empty-state {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: rgba(255,255,255,0.6); font-size: 1.2rem; }}
.card {{ position: absolute; top: 50%; left: 50%; height: 320px; width: 260px; background: rgba(30, 30, 30, 0.9); border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; transform: translate(-50%, -50%) scale(1); transition: transform 0.4s ease, z-index 0.3s ease, filter 0.4s ease, box-shadow 0.3s ease; z-index: 1; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); }}
.card-img-container {{ height: 250px; width: 100%; background: #f0f0f0; display: flex; justify-content: center; align-items: center; overflow: hidden; }}
.card img {{ height: 100%; width: 100%; object-fit: cover; }}
.card-details {{ padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: center; }}
.card-actions {{ display: flex; justify-content: space-between; align-items: center; }}
.color-swatch {{ width: 24px; height: 24px; border-radius: 50%; border: 1px solid #fff; box-shadow: 0 0 5px rgba(0,0,0,0.5); }}
.card.focused {{ z-index: 10; filter: brightness(1); }}
.card:not(.focused) {{ filter: brightness(0.4); }}
.card.selected {{ box-shadow: 0 0 20px 5px rgba(76, 175, 80, 0.6) !important; border: 2px solid #4CAF50 !important; }}
.select-btn {{ background-color: #4CAF50; border: none; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: bold; cursor: pointer; transition: background 0.2s; }}
.select-btn:hover {{ background-color: #45a049; }}
.btn-container {{ width: 100%; max-width: 600px; margin: 0 auto; padding: 0 20px; box-sizing: border-box; position: relative; z-index: 20; }}
.ai-btn {{ width: 100%; padding: 15px; font-size: 18px; background: linear-gradient(135deg, #6e8efb, #a777e3); color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: transform 0.2s; }}
.ai-btn:hover {{ transform: scale(1.02); }}
.ai-btn:disabled {{ background: #555; cursor: not-allowed; transform: none; }}
.ai-result {{ max-width: 600px; margin: 20px auto 40px auto; padding: 20px; border-radius: 16px; background: rgba(25, 25, 35, 0.85); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 30px rgba(0,0,0,0.3); font-size: 15px; line-height: 1.6; display: none; height: auto; min-height: fit-content; position: relative; z-index: 20; }}
.match-display {{ display: flex; gap: 20px; align-items: center; }}
.match-img {{ width: 120px; height: 120px; border-radius: 10px; object-fit: cover; background: white; flex-shrink: 0; }}
.match-info {{ flex-grow: 1; }}
.reason-text {{ color: #ddd; margin-top: 8px; font-style: italic; }}
.btn-group {{ display: flex; gap: 12px; margin-top: 20px; }}
.confirm-btn {{ flex: 1; padding: 12px; font-size: 15px; font-weight: bold; background-color: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; transition: all 0.3s; }}
.confirm-btn:hover {{ background-color: #45a049; }}
.alt-btn {{ flex: 1; padding: 12px; font-size: 15px; font-weight: bold; background-color: transparent; border: 2px solid #ff9800; color: #ff9800; border-radius: 8px; cursor: pointer; transition: all 0.3s; }}
.alt-btn:hover {{ background-color: #ff9800; color: white; }}
</style>
</head>
<body>

<div class="top-bar">
    <button class="toggle-btn" id="toggleCategoryBtn">Switch to Pants Wardrobe</button>
</div>

<div class="carousel-container" id="carouselContainer">
  <div class="carousel" id="carousel"></div>
</div>

<div class="btn-container">
    <button class="ai-btn" id="aiMatchBtn">✨ Find AI Match</button>
</div>
<div id="aiResult" class="ai-result"></div>

<script type="module">
// 1. IMPORT FIREBASE WEB SDK (Using doc instead of query)
import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import {{ getFirestore, doc, updateDoc }} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-firestore.js";

// 2. YOUR EXACT CONFIG
const firebaseConfig = {{
    apiKey: "AIzaSyD_8TPV504yiO767R0iZDdQu_uVbLyOaYk",
    authDomain: "fashion8-97039.firebaseapp.com",
    projectId: "fashion8-97039",
    storageBucket: "fashion8-97039.firebasestorage.app",
    messagingSenderId: "1076566189030",
    appId: "1:1076566189030:web:4bf162200095f052c8ec27",
    measurementId: "G-FNVVP1DT7N"
}};

// Initialize Firebase Front-End
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// API Keys & Python Data
const GEMINI_API_KEY = 'AIzaSyAF7X59jBA0CPYlCHw7-GyRORxAQ2G9DX4';
const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent';

const shirts_data = {shirts_json};
const pants_data = {pants_json};
const current_day = "{current_day}";

// THIS IS THE BETTER LOGIC: Pre-fetched document ID straight from Python!
const TARGET_DOC_ID = "{user_doc_id}";

let currentCategory = "shirts";
let currentIndex = 0;
let selectedItem = null; 
let matchHistory = []; 

function buildCards(data, type) {{
    const carousel = document.getElementById("carousel");
    carousel.innerHTML = "";
    const entries = Object.entries(data);
    if (entries.length === 0) {{
        carousel.innerHTML = `<div class="empty-state">No ${{type.toLowerCase()}}s added yet. Head to Dress++!</div>`;
        return;
    }}
    entries.forEach(([id, item], idx) => {{
        const card = document.createElement("div");
        card.className = "card";
        card.dataset.index = idx;
        card.innerHTML = `
            <div class="card-img-container"><img src="${{item.img}}" alt="${{type}}" /></div>
            <div class="card-details">
                <div class="card-actions">
                    <div class="color-swatch" style="background-color: ${{item.hex}};"></div>
                    <button class="select-btn" data-id="${{id}}">Select</button>
                </div>
            </div>
        `;
        carousel.appendChild(card);
    }});
}}

function updateCarousel() {{
    const cards = Array.from(document.getElementsByClassName("card"));
    if(cards.length === 0) return;
    const spacing = window.innerWidth < 600 ? 180 : 240;
    cards.forEach((card, index) => {{
        const offset = index - currentIndex;
        let scale = offset === 0 ? 1.1 : 0.85;
        card.style.transform = `translate(calc(-50% + ${{offset * spacing}}px), -50%) scale(${{scale}})`;
        card.style.zIndex = 10 - Math.abs(offset);
        card.classList.toggle("focused", offset === 0);
        
        const selectBtn = card.querySelector('.select-btn');
        if (selectedItem && selectBtn && selectBtn.dataset.id === selectedItem.id) {{
            card.classList.add("selected");
            selectBtn.innerText = "Selected";
        }} else if(selectBtn) {{
            card.classList.remove("selected");
            selectBtn.innerText = "Select";
        }}
    }});
}}

document.getElementById("carouselContainer").addEventListener("wheel", e => {{
    e.preventDefault();
    const cards = document.getElementsByClassName("card");
    if (e.deltaY > 0 && currentIndex < cards.length - 1) currentIndex++;
    else if (e.deltaY < 0 && currentIndex > 0) currentIndex--;
    updateCarousel();
}}, {{ passive: false }});

let touchStartX = 0;
document.getElementById("carouselContainer").addEventListener("touchstart", e => touchStartX = e.touches[0].clientX);
document.getElementById("carouselContainer").addEventListener("touchend", e => {{
    const delta = e.changedTouches[0].clientX - touchStartX;
    const cards = document.getElementsByClassName("card");
    if (Math.abs(delta) > 40) {{
        if (delta < 0 && currentIndex < cards.length - 1) currentIndex++;
        else if (delta > 0 && currentIndex > 0) currentIndex--;
        updateCarousel();
    }}
}});

document.addEventListener("click", e => {{
    if (e.target.classList.contains("select-btn")) {{
        const id = e.target.dataset.id;
        const dataMap = currentCategory === "shirts" ? shirts_data : pants_data;
        selectedItem = {{ id: id, type: currentCategory === "shirts" ? "Shirt" : "Pant", ...dataMap[id] }};
        updateCarousel();
    }}

    if (e.target.id === "toggleCategoryBtn") {{
        currentCategory = currentCategory === "shirts" ? "pants" : "shirts";
        e.target.textContent = currentCategory === "shirts" ? "Switch to Pants Wardrobe" : "Switch to Shirts Wardrobe";
        currentIndex = 0;
        selectedItem = null;
        matchHistory = [];
        document.getElementById("aiResult").style.display = "none";
        buildCards(currentCategory === "shirts" ? shirts_data : pants_data, currentCategory === "shirts" ? "Shirt" : "Pant");
        updateCarousel();
    }}
}});

async function fetchMatch(excludeIds=[]) {{
    let opposite_dict = selectedItem.type === "Shirt" ? pants_data : shirts_data;
    let opposite_type = selectedItem.type === "Shirt" ? "Pant" : "Shirt";
    
    let available_options = [];
    Object.entries(opposite_dict).forEach(([id, item]) => {{
        if(!excludeIds.includes(id)) available_options.push({{id: id, desc: item.desc, hex: item.hex}});
    }});

    if(available_options.length === 0) return {{ error: "No more items left to match." }};

    const prompt = `
        You are an expert fashion stylist. My current item: A ${{selectedItem.type}} described as "${{selectedItem.desc}}" with color hex ${{selectedItem.hex}}.
        Available ${{opposite_type}} options: ${{JSON.stringify(available_options)}}
        Select the BEST match. Return ONLY a JSON object: {{"best_match_id": "string", "reason": "string"}}.
    `;

    try {{
        const response = await fetch(GEMINI_API_URL + '?key=' + GEMINI_API_KEY, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                contents: [{{ role: "user", parts: [{{ text: prompt }}] }}],
                generationConfig: {{ responseMimeType: "application/json" }}
            }})
        }});
        const data = await response.json();
        const parsed = JSON.parse(data.candidates[0].content.parts[0].text);
        return {{ success: true, match_id: parsed.best_match_id, reason: parsed.reason, opposite_dict }};
    }} catch(err) {{
        return {{ error: "AI response failed." }};
    }}
}}

function renderMatch(match_id, reason, opposite_dict) {{
    const itemInfo = opposite_dict[match_id];
    const resultDiv = document.getElementById("aiResult");
    resultDiv.style.display = "block";
    resultDiv.innerHTML = `
        <div style="margin-bottom: 10px; font-weight:bold; color: #4CAF50;">✨ Curated Match Found!</div>
        <div class="match-display">
            <img src="${{itemInfo.img}}" class="match-img">
            <div class="match-info">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 14px; color: #ccc;">Match Color:</span>
                    <div class="color-swatch" style="background-color: ${{itemInfo.hex}}; width: 18px; height: 18px;"></div>
                </div>
                <div class="reason-text">"${{reason}}"</div>
            </div>
        </div>
        <div class="btn-group">
            <button class="confirm-btn" id="confirmBtn" data-matchid="${{match_id}}">✅ Confirm Outfit</button>
            <button class="alt-btn" id="altBtn">🔄 Alternate</button>
        </div>
    `;
}}

document.getElementById("aiMatchBtn").addEventListener("click", async (e) => {{
    const btn = e.target;
    const resultDiv = document.getElementById("aiResult");
    if (!selectedItem) {{
        resultDiv.style.display = "block";
        resultDiv.innerHTML = "<div style='color: #ff5252;'>⚠️ Please select an item first.</div>";
        return;
    }}
    btn.disabled = true;
    btn.innerText = "Styling... ⌛";
    resultDiv.style.display = "block";
    resultDiv.innerHTML = "Consulting the AI Stylist...";
    const result = await fetchMatch();
    if (result.success) {{
        matchHistory.push(result.match_id);
        renderMatch(result.match_id, result.reason, result.opposite_dict);
    }} else {{
        resultDiv.innerHTML = `<div style='color: #ff5252;'>${{result.error}}</div>`;
    }}
    btn.disabled = false;
    btn.innerText = "✨ Find AI Match";
}});

document.addEventListener("click", async e => {{
    if (e.target.id === "altBtn") {{
        const btn = e.target;
        btn.disabled = true;
        btn.innerText = "Finding alternatives...";
        const result = await fetchMatch(matchHistory);
        if (result.success) {{
            matchHistory.push(result.match_id);
            renderMatch(result.match_id, result.reason, result.opposite_dict);
        }} else {{
            const errDiv = document.createElement("div");
            errDiv.style.color = "#ff5252"; errDiv.innerText = result.error;
            btn.parentNode.appendChild(errDiv); btn.style.display = "none";
        }}
    }}
    
    // --- THE FIX: DIRECT AND ROBUST FIRESTORE WRITE ---
    if (e.target.id === "confirmBtn") {{
        const match_id = e.target.dataset.matchid;
        const btn = e.target;
        
        btn.disabled = true;
        btn.innerText = "Saving to Database... ⌛";
        
        try {{
            let shirt_id, pant_id;
            if (selectedItem.type === "Shirt") {{
                shirt_id = selectedItem.id;
                pant_id = match_id;
            }} else {{
                shirt_id = match_id;
                pant_id = selectedItem.id;
            }}

            // Directly target the exact document (No queries!)
            const userRef = doc(db, "users", TARGET_DOC_ID);
            const updateData = {{}};
            
            // Format: "week.monday.shirt": "1"
            updateData[`week.${{current_day}}.shirt`] = shirt_id;
            updateData[`week.${{current_day}}.pant`] = pant_id;

            // Execute Database Update
            await updateDoc(userRef, updateData);

            btn.innerText = "✅ Locked In for " + current_day.charAt(0).toUpperCase() + current_day.slice(1) + "!";
            btn.style.backgroundColor = "#4CAF50";
            btn.style.color = "white";
            
        }} catch(err) {{
            console.error("Firebase Update Error:", err);
            // This alert will show EXACTLY why it failed if it does!
            alert("Database Error:\\n" + err.message + "\\n\\nPlease verify your Firestore Security Rules allow unauthenticated web writes if using Streamlit.");
            btn.innerText = "Error Saving ❌";
            btn.style.backgroundColor = "#ff5252";
            btn.disabled = false;
        }}
    }}
}});

// Initialize
buildCards(shirts_data, "Shirt");
updateCarousel();
window.addEventListener("resize", updateCarousel);
</script>
</body>
</html>
"""

components.html(carousel_html, height=1050, scrolling=True)

