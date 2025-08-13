import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore
import json

st.set_page_config(page_title="Today's Drip", layout="wide")
st.title("Today's Drip")


# Hide Streamlit default header
st.markdown("""
<style>
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Firebase init ---
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Authentication check ---
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access this page.")
    if st.button("Login",use_container_width=True):
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
# --- Fetch clothing data ---
users_ref = db.collection('users')
query = users_ref.where('username', '==', st.session_state['username']).limit(1)
user_docs = query.get()

if not user_docs:
    st.error("No clothing data found for this user.")
    st.stop()

user_data = user_docs[0].to_dict()
shirts_data = user_data.get("shirts", {})
pants_data = user_data.get("pants", {})

shirts_json = json.dumps(shirts_data)
pants_json = json.dumps(pants_data)

# --- HTML + JS ---
carousel_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
body {{
    background: transparent;
    font-family: "Segoe UI", sans-serif;
    color: white;
    margin: 0;
    padding: 0;
}}
.top-bar {{
    display: flex;
    justify-content: flex-start;
    align-items: center;
    padding: 10px;
}}
.toggle-btn {{
    padding: 8px 14px;
    background-color: #007bff;
    border: none;
    color: white;
    border-radius: 5px;
    cursor: pointer;
    font-size: 14px;
}}
.toggle-btn:hover {{
    background-color: #0056b3;
}}
.carousel-container {{
    width: 100%;
    height: 380px;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.carousel {{
    position: relative;
    width: 100%;
    height: 100%;
}}
.card {{
    position: absolute;
    top: 50%;
    left: 50%;
    height: 200px;
    width: 200px;
    background: #222;
    border-radius: 20px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    transform: translate(-50%, -50%) scale(1);
    transition: transform 0.4s ease, z-index 0.3s ease, filter 0.4s ease;
    z-index: 1;
    box-shadow: 0 10px 20px rgba(0,0,0,0.15);
    color: white;
}}
.card img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    background-color: white;
}}
.card-label {{
    position: absolute;
    bottom: 0;
    width: 100%;
    background: rgba(0,0,0,0.75);
    color: white;
    padding: 5px;
    font-size: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
}}
.card.focused {{
    z-index: 10;
    filter: brightness(1);
}}
.card:not(.focused) {{
    filter: brightness(0.5);
}}
.card.selected {{
    box-shadow: 0 0 15px 3px #4CAF50 !important;
    border: 2px solid #4CAF50 !important;
}}
.select-btn {{
    background-color: #007bff;
    border: none;
    color: white;
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 12px;
    cursor: pointer;
}}
.color-picker {{
    width: 28px;
    height: 28px;
    border: none;
    cursor: pointer;
}}
.ai-btn {{
    width: 100%;
    padding: 12px;
    font-size: 18px;
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 6px;
    margin-top: 15px;
    cursor: pointer;
    font-weight: bold;
}}
.ai-btn:hover {{
    background-color: #45a049;
}}
.ai-result {{
    margin-top: 20px;
    padding: 15px;
    border-radius: 8px;
    background: rgba(0,0,0,0.7);
    font-size: 16px;
    line-height: 1.5;
    width: 100%;
    box-sizing: border-box;
    overflow: visible;       
}}
.ai-result img {{
    max-width: 100%;
    height: 175px;
    display: block;
    margin-top: 12px;
    border-radius: 8px;
}}
.alt-btn {{
    width: 100%;
    padding: 10px;
    font-size: 16px;
    font-weight: bold;
    background-color: #ff9800;
    color: white;
    border: none;
    border-radius: 6px;
    margin-top: 12px;
    cursor: pointer;
}}
.alt-btn:hover {{
    background-color: #e68900;
}}
</style>
</head>
<body>

<div class="top-bar">
    <button class="toggle-btn" id="toggleCategoryBtn">Pants</button>
</div>

<div class="carousel-container" id="carouselContainer">
  <div class="carousel" id="carousel"></div>
</div>

<button class="ai-btn" id="aiMatchBtn">AI Match</button>
<div id="aiResult" class="ai-result"></div>

<script>
const GEMINI_API_KEY = '{st.secrets["gemini"]["api_key"]}';  // WARNING: exposes key to users
const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';

const shirts_data = {shirts_json};
const pants_data = {pants_json};

let currentCategory = "shirts";
let currentIndex = 0;
let selectedIndex = null;
let selectedColor = null;
let selectedType = null;
let matchHistory = [];

function buildCards(data, type) {{
    const carousel = document.getElementById("carousel");
    carousel.innerHTML = "";
    Object.entries(data).forEach(([color, url], idx) => {{
        const card = document.createElement("div");
        card.className = "card";
        card.dataset.index = idx;
        card.innerHTML = `
            <img src="${{url}}" alt="${{type}}" />
            <div class="card-label">
                ${{type}}
                <input type="color" class="color-picker" value="${{color}}" data-idx="${{idx}}" />
                <button class="select-btn" data-idx="${{idx}}">Select</button>
            </div>
        `;
        carousel.appendChild(card);
    }});
}}

function updateCarousel() {{
    const cards = Array.from(document.getElementsByClassName("card"));
    const spacing = window.innerWidth < 600 ? 80 : 100;
    const scaleFocused = window.innerWidth < 600 ? 1.5 : 1.6;
    const scaleNeighbor = 1.25;
    cards.forEach((card, index) => {{
        const offset = index - currentIndex;
        let scale = 1;
        if (offset === 0) scale = scaleFocused;
        else if (Math.abs(offset) === 1) scale = scaleNeighbor;
        card.style.transform = `translate(calc(-50% + ${{offset * spacing}}px), -50%) scale(${{scale}})`;
        card.style.zIndex = 10 - Math.abs(offset);
        card.classList.toggle("focused", offset === 0);
        if (selectedIndex !== null && selectedIndex === index) {{
            card.classList.add("selected");
        }} else {{
            card.classList.remove("selected");
        }}
    }});
}}

function scrollCarousel(e) {{
    e.preventDefault();
    const cards = document.getElementsByClassName("card");
    if (e.deltaY > 0 && currentIndex < cards.length - 1) currentIndex++;
    else if (e.deltaY < 0 && currentIndex > 0) currentIndex--;
    updateCarousel();
}}

document.getElementById("carouselContainer").addEventListener("wheel", scrollCarousel, {{ passive: false }});
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
        const idx = parseInt(e.target.dataset.idx);
        const colorInput = document.querySelector(`input.color-picker[data-idx='${{idx}}']`);
        selectedIndex = idx;
        selectedColor = colorInput ? colorInput.value : null;
        selectedType = currentCategory === "shirts" ? "Shirt" : "Pants";
        updateCarousel();
    }}
    if (e.target.id === "toggleCategoryBtn") {{
        currentCategory = currentCategory === "shirts" ? "pants" : "shirts";
        e.target.textContent = currentCategory === "shirts" ? "Pants" : "Shirts";
        currentIndex = 0;
        selectedIndex = null;
        selectedColor = null;
        selectedType = null;
        matchHistory = [];
        document.getElementById("aiResult").innerHTML = "";
        buildCards(currentCategory === "shirts" ? shirts_data : pants_data, currentCategory === "shirts" ? "Shirt" : "Pants");
        updateCarousel();
    }}
}});

async function fetchMatch(excludeColors=[]) {{
    let opposite_dict, opposite_type;
    if (selectedType.toLowerCase() === "shirt") {{
        opposite_dict = pants_data;
        opposite_type = "pants";
    }} else {{
        opposite_dict = shirts_data;
        opposite_type = "shirts";
    }}
    const opposite_colors = Object.keys(opposite_dict).filter(c => !excludeColors.includes(c));
    const prompt = `
        You are a fashion advisor AI assistant.
        From the array ${{JSON.stringify(opposite_colors)}}, pick the best matching ${{opposite_type}}
        for a ${{selectedColor}} ${{selectedType}} and explain why.
        Return your answer in the format: BEST_MATCH:<hexcode>, REASON:<your reason>.
    `;
    const response = await fetch(GEMINI_API_URL + '?key=' + GEMINI_API_KEY, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
            contents: [{{ role: "user", parts: [{{ text: prompt }}] }}]
        }})
    }});
    const data = await response.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    return {{ text, opposite_dict }};
}}

function renderMatch(best_match, reason, imgUrl) {{
    let html = `<strong style="font-size:18px;">Best match:</strong> <span style="font-size:18px;">${{best_match}}</span><br><br>
                <strong style="font-size:16px;">Reason:</strong> <span style="font-size:16px;">${{reason}}</span>`;
    if (imgUrl) {{
        html += `<img src="${{imgUrl}}" alt="Match">`;
    }}
    html += `<button class="alt-btn" id="altBtn">Alternate</button>`;
    document.getElementById("aiResult").innerHTML = html;
}}

document.getElementById("aiMatchBtn").addEventListener("click", async () => {{
    if (selectedIndex === null || !selectedColor || !selectedType) {{
        document.getElementById("aiResult").innerHTML = "<strong>Please select a clothing item first.</strong>";
        return;
    }}
    document.getElementById("aiResult").innerHTML = "Finding your best match...";
    const result = await fetchMatch();
    const text = result.text;
    const opposite_dict = result.opposite_dict;
    if (text.includes("BEST_MATCH:")) {{
        const best_match = text.split("BEST_MATCH:")[1].split(",")[0].trim();
        const reason = text.split("REASON:")[1]?.trim() || "";
        matchHistory.push(best_match);
        renderMatch(best_match, reason, opposite_dict[best_match]);
    }} else {{
        document.getElementById("aiResult").innerHTML = text;
    }}
}});

document.addEventListener("click", async e => {{
    if (e.target.id === "altBtn") {{
        document.getElementById("aiResult").innerHTML = "Finding an alternate match...";
        const result = await fetchMatch(matchHistory);
        const text = result.text;
        const opposite_dict = result.opposite_dict;
        if (text.includes("BEST_MATCH:")) {{
            const best_match = text.split("BEST_MATCH:")[1].split(",")[0].trim();
            const reason = text.split("REASON:")[1]?.trim() || "";
            matchHistory.push(best_match);
            renderMatch(best_match, reason, opposite_dict[best_match]);
        }} else {{
            document.getElementById("aiResult").innerHTML = text;
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

components.html(carousel_html, height=1100, scrolling=False)

