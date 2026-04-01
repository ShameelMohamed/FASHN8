import streamlit as st
import json
import requests

# --- Configuration & Constants ---
# SECURITY WARNING: API key hidden via st.secrets to protect your account on GitHub.
GEMINI_API_KEY = st.secrets["gemini"]["api_key"]
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Updated Wardrobe Data (5 Pants, 5 Shirts)
WARDROBE_DATA = {
    "pants": {
        "1": {"desc": "Navy blue button-down shirt and light blue trousers with multiple pockets and relaxed fit.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772189744/fashion8/tess_pants_182546_1.png", "hex": "#182546"},
        "2": {"desc": "Black high-waisted trousers, slim fit, cuffed at ankles.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772189948/fashion8/tess_pants_131716_3.png", "hex": "#131716"},
        "3": {"desc": "Beige trousers with patchwork design, relaxed fit.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772209726/fashion8/tess_pants_f8f3ed_1.png", "hex": "#f8f3ed"},
        "4": {"desc": "Black trousers, lightweight fabric, slim fit, button and zipper closure.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772262219/fashion8/tess_pants_252728_2.png", "hex": "#252728"},
        "5": {"desc": "Beige loose-fitting slim fit trousers, slightly tapered, adjustable waistband.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1774459213/fashion8/tess_pants_e0d5bf_3.png", "hex": "#e0d5bf"}
    },
    "shirts": {
        "1": {"desc": "Navy blue button-down shirt, long sleeves, lightweight.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772189718/fashion8/tess_top_1e2d51_0.png", "hex": "#1e2d51"},
        "2": {"desc": "White button-down shirt with unique chest design, long sleeves.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772189893/fashion8/tess_top_d0d0d0_0.png", "hex": "#d0d0d0"},
        "3": {"desc": "Maroon long-sleeved t-shirt with small chest pocket, relaxed fit.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772209773/fashion8/tess_top_721c25_2.png", "hex": "#721c25"},
        "4": {"desc": "Beige button-down shirt, long sleeves, subtle texture.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1772262260/fashion8/tess_top_b1927d_3.png", "hex": "#b1927d"},
        "5": {"desc": "Long-sleeved green button-down shirt.", "img": "https://res.cloudinary.com/djj1sw8rh/image/upload/v1774459176/fashion8/tess_top_275030_1.png", "hex": "#275030"}
    }
}

st.set_page_config(page_title="Wardrobe Summary ✨", layout="wide")

# --- UI Styling ---
st.markdown("""
<style>
    header {visibility: hidden;}
    .stApp {
        background-image: url("https://logincdn.msftauth.net/shared/5/images/fluent_web_dark_2_bf5f23287bc9f60c9be2.svg");
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
        background-position: center;
    }
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: rgba(0, 0, 0, 0.7) !important;
        border-radius: 15px !important;
        padding: 25px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    div[data-testid="stVerticalBlock"] > div[style*="border"] p, 
    div[data-testid="stVerticalBlock"] > div[style*="border"] li {
        font-size: 1.15rem !important;
        line-height: 1.6 !important;
    }
    div[data-testid="stVerticalBlock"] > div[style*="border"] h3 {
        font-size: 1.5rem !important;
        margin-top: 1rem !important;
        margin-bottom: 0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Authentication Check ---
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access this page.")
    if st.button("Login", use_container_width=True):
        st.switch_page("Home.py")
    st.stop()

if st.session_state.get('authentication_status'):
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['authentication_status'] = False
        st.session_state['username'] = None
        st.session_state['show_login_form'] = False
        st.session_state['show_signup_form'] = False
        st.rerun()

# --- Helper Functions ---
def get_wardrobe_analysis(wardrobe_context):
    """Sends a highly optimized, token-efficient prompt to Gemini."""
    
    compact_wardrobe = json.dumps(wardrobe_context, separators=(',', ':'))
    
    system_instruction = f"""
    You are an elite AI Fashion Analyst for MEN'S FORMAL & SMART-CASUAL WEAR.
    Analyze this wardrobe data: {compact_wardrobe}
    
    **CRITICAL INSTRUCTIONS:**
    Keep your response extremely brief, strictly formal, and objective. 
    You MUST respond with exactly 3 sections. Each section MUST contain exactly 3 single-line bullet points for each of three following subheadings. No introductory or concluding text.
    
    Format exactly like this:
    
    ### 👔 Style Analysis
    * [Brief point on dominant colors]
    * [Brief point on overall professional vibe]
    * [Brief point on the image conveyed]
    
    ### 🔍 Wardrobe Gaps
    * [Brief point on missing staple 1]
    * [Brief point on missing staple 2]
    * [Brief point on missing staple 3]
    
    ### 🛍️ Recommendations
    * [Briefly recommend specific item 1 and what it pairs with]
    * [Briefly recommend specific item 2 and what it pairs with]
    * [Briefly recommend specific item 3 and what it pairs with]
    """
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": system_instruction}]}],
    }

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Add basic error handling for the 429 specifically
        if response.status_code == 429:
            return "**Error:** API Rate Limit Exceeded (429). You are making requests too quickly. Please wait a minute and try again."
            
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"**Error:** Unable to complete the wardrobe analysis. ({e})"

# --- Main Page Layout ---

st.title("Wardrobe Summary 📊")
st.write("Initiate a professional audit of your closet to identify style patterns, wardrobe gaps, and strategic acquisition recommendations.")

# The Big Button
if st.button("Generate Wardrobe Analysis", use_container_width=True, type="primary"):
    
    num_shirts = len(WARDROBE_DATA.get("shirts", {}))
    num_pants = len(WARDROBE_DATA.get("pants", {}))
    total_items = num_shirts + num_pants
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Items", value=total_items)
    with col2:
        st.metric(label="Shirts/Topwear", value=num_shirts)
    with col3:
        st.metric(label="Trousers/Bottomwear", value=num_pants)
    
    st.divider()

    with st.spinner("Analyzing wardrobe data... 👔"):
        analysis_result = get_wardrobe_analysis(WARDROBE_DATA)
        
        with st.container(border=True):
            st.markdown(analysis_result)
