import streamlit as st
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai

st.set_page_config(page_title="Today's Drip", layout="wide")

# Hide Streamlit header
st.markdown("""
<style>
    header {visibility: hidden;}
    .card.selected {
        box-shadow: 0 0 12px 2px #4CAF50 !important;
        border: 2px solid #4CAF50 !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ FIREBASE INIT ------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase"])
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ------------------ AUTH CHECK ------------------
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access this page.")
    if st.button("Login"):
        st.switch_page("Home.py")
    st.stop()

st.sidebar.success(f"Logged in as {st.session_state['username']}")
if st.sidebar.button("Logout"):
    st.session_state['authentication_status'] = False
    st.session_state['username'] = None
    st.session_state['show_login_form'] = False
    st.session_state['show_signup_form'] = False
    st.experimental_rerun()

# ------------------ SESSION DEFAULTS ------------------
if "category" not in st.session_state:
    st.session_state.category = "shirts"
if "selected_card_index" not in st.session_state:
    st.session_state.selected_card_index = None
if "selected_card_color" not in st.session_state:
    st.session_state.selected_card_color = None
if "best_match_history" not in st.session_state:
    st.session_state.best_match_history = []

# ------------------ HEADER ------------------
col1, _, col3 = st.columns([4, 1, 1])
with col1:
    st.markdown("# Today's Drip")
with col3:
    if st.session_state.category == "shirts":
        if st.button("Pants", key="pants_btn"):
            st.session_state.category = "pants"
            st.experimental_rerun()
    else:
        if st.button("Shirts", key="shirts_btn"):
            st.session_state.category = "shirts"
            st.experimental_rerun()

# ------------------ FETCH USER CLOTHING ------------------
users_ref = db.collection('users')
query = users_ref.where('username', '==', st.session_state['username']).limit(1)
user_docs = query.get()
if not user_docs:
    st.error("No clothing data found for this user.")
    st.stop()

user_data = user_docs[0].to_dict()
shirts_data = user_data.get("shirts", {})
pants_data = user_data.get("pants", {})

# Filter based on category
cards_data = []
if st.session_state.category == "shirts":
    for color, url in shirts_data.items():
        cards_data.append({"type": "Shirt", "color": color, "url": url})
else:
    for color, url in pants_data.items():
        cards_data.append({"type": "Pants", "color": color, "url": url})

if not cards_data:
    st.info(f"You haven't uploaded any {st.session_state.category} yet!")
    st.stop()

# ------------------ BUILD CARDS HTML ------------------
cards_html = ""
for idx, item in enumerate(cards_data):
    cards_html += f"""
    <div class="card" data-index="{idx}">
        <img src="{item['url']}" alt="{item['type']}" />
        <div class="card-label">
            {item['type']}
            <input type="color" class="color-picker" value="{item['color']}" data-idx="{idx}" />
            <button class="select-btn" data-idx="{idx}">Select</button>
        </div>
    </div>
    """

# ------------------ CAROUSEL HTML + JS ------------------
carousel_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
* {{box-sizing: border-box; margin: 0; padding: 0;}}
html, body {{height: 100%; width: 100%; background: transparent; font-family: "Segoe UI", sans-serif;}}
.carousel-container {{width: 100vw; height: 380px; display: flex; align-items: center; justify-content: center; overflow: hidden;}}
.carousel {{position: relative; width: 100%; height: 100%;}}
.card {{
  position: absolute; top: 50%; left: 50%; height: 200px; width: 200px; background: #222;
  border-radius: 20px; overflow: hidden; display: flex; flex-direction: column; align-items: center;
  justify-content: flex-end; transform: translate(-50%, -50%) scale(1);
  transition: transform 0.4s ease, z-index 0.3s ease, filter 0.4s ease;
  box-shadow: 0 10px 20px rgba(0,0,0,0.15); color: white; z-index: 1;
}}
.card img {{width: 100%; height: 100%; object-fit: contain; background-color: white;}}
.card-label {{
  position: absolute; bottom: 0; width: 100%; background: rgba(0,0,0,0.75);
  color: white; padding: 5px; font-size: 14px; display: flex; justify-content: space-between; align-items: center;
}}
.card.focused {{z-index: 10; filter: brightness(1);}}
.card:not(.focused) {{filter: brightness(0.5);}}
.select-btn {{
  background-color: #007bff; border: none; color: white; padding: 3px 8px;
  border-radius: 5px; font-size: 12px; cursor: pointer; transition: background-color 0.3s ease;
}}
.select-btn:hover {{background-color: #0056b3;}}
.color-picker {{width: 28px; height: 28px; border: none; cursor: pointer; background: none;}}
.card.selected {{box-shadow: 0 0 12px 2px #4CAF50 !important; border: 2px solid #4CAF50 !important;}}
</style>
</head>
<body>
<div class="carousel-container" id="carouselContainer">
  <div class="carousel" id="carousel">
    {cards_html}
  </div>
</div>
<script>
const carousel = document.getElementById("carousel");
const cards = Array.from(carousel.getElementsByClassName("card"));
let currentIndex = 0;
let selectedIndex = null;

function updateCarousel() {{
  const isMobile = window.innerWidth < 600;
  const spacing = isMobile ? 80 : 100;
  const scaleFocused = isMobile ? 1.5 : 1.6;
  const scaleNeighbor = 1.25;

  cards.forEach((card, index) => {{
    const offset = index - currentIndex;
    let scale = offset === 0 ? scaleFocused : Math.abs(offset) === 1 ? scaleNeighbor : 1;
    card.style.transform = `translate(calc(-50% + ${{offset * spacing}}px), -50%) scale(${{scale}})`;
    card.style.zIndex = 10 - Math.abs(offset);
    card.classList.toggle("focused", offset === 0);
    if (selectedIndex === index) card.classList.add("selected");
    else card.classList.remove("selected");
  }});
}}

document.getElementById("carouselContainer").addEventListener("wheel", e => {{
  e.preventDefault();
  if (e.deltaY > 0 && currentIndex < cards.length - 1) currentIndex++;
  else if (e.deltaY < 0 && currentIndex > 0) currentIndex--;
  updateCarousel();
}}, {{ passive: false }});

let touchStartX = 0;
document.getElementById("carouselContainer").addEventListener("touchstart", e => {{
  touchStartX = e.touches[0].clientX;
}});
document.getElementById("carouselContainer").addEventListener("touchend", e => {{
  const delta = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(delta) > 40) {{
    if (delta < 0 && currentIndex < cards.length - 1) currentIndex++;
    else if (delta > 0 && currentIndex > 0) currentIndex--;
    updateCarousel();
  }}
}});

carousel.addEventListener("click", e => {{
  if (e.target.classList.contains("select-btn")) {{
    const idx = parseInt(e.target.dataset.idx);
    const colorInput = carousel.querySelector(`input.color-picker[data-idx='${{idx}}']`);
    const selectedColor = colorInput ? colorInput.value : null;
    selectedIndex = idx;
    updateCarousel();
    window.parent.postMessage({{type: "cardSelected", index: idx, color: selectedColor}}, "*");
  }}
}});

updateCarousel();
</script>
</body>
</html>
"""

components.html(carousel_html, height=400, scrolling=False)

# ------------------ SHOW SELECTED CARD ------------------
if st.session_state.selected_card_index is not None:
    sel_idx = st.session_state.selected_card_index
    sel_color = st.session_state.selected_card_color
    sel_type = cards_data[sel_idx]["type"]
    st.info(f"Selected card: **{sel_type}** with color **{sel_color}**")

# ------------------ AI MATCH LOGIC ------------------
genai.configure(api_key="YOUR_GEMINI_API_KEY")

def run_ai_match(exclude_colors=None):
    selected_card = cards_data[st.session_state.selected_card_index]
    focused_color = st.session_state.selected_card_color
    focused_type = selected_card["type"]

    if focused_type.lower() == "shirt":
        opposite_dict = pants_data
        opposite_type = "pants"
    else:
        opposite_dict = shirts_data
        opposite_type = "shirts"

    opposite_colors = list(opposite_dict.keys())
    exclude_str = f"Exclude these colors: {exclude_colors}." if exclude_colors else ""

    prompt = (
        f"You are a fashion advisor AI assistant. {exclude_str} "
        f"From the array {opposite_colors}, pick the best matching {opposite_type} "
        f"for a {focused_color} {focused_type} and explain why. "
        f"Return in format BEST_MATCH:<hexcode>, REASON:<reason>."
    )

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    if response and response.text:
        text = response.text.strip()
        if "BEST_MATCH:" in text:
            best_match = text.split("BEST_MATCH:")[1].split(",")[0].strip()
            reason = text.split("REASON:")[1].strip()

            if best_match not in st.session_state.best_match_history:
                st.session_state.best_match_history.append(best_match)

            st.info(f"**Best match:** {best_match}\n\n**Reason:** {reason}")
            if best_match in opposite_dict:
                st.image(opposite_dict[best_match], caption=f"{opposite_type.title()} - {best_match}")
            else:
                st.warning(f"No image found for {best_match}.")
        else:
            st.info(text)
    else:
        st.warning("No response from AI.")

if st.button("AI Match"):
    if st.session_state.selected_card_index is None:
        st.error("Please select a card first.")
    else:
        run_ai_match()

if st.button("Alternate"):
    if st.session_state.selected_card_index is None:
        st.error("Please select a card first.")
    else:
        run_ai_match(exclude_colors=st.session_state.best_match_history)

