import streamlit as st
import json
import requests
import re
import speech_recognition as sr
from gtts import gTTS
import os

# --- Configuration & Constants ---
# SECURITY WARNING: API key hidden via st.secrets to protect your account on GitHub.
GEMINI_API_KEY = st.secrets["gemini"]["api_key"]
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

LANG_MAP = {
    "English": "en-US", "Tamil": "ta-IN", "Malayalam": "ml-IN", "Telugu": "te-IN", "Hindi": "hi-IN"
}

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

st.set_page_config(page_title="Ask Pookie✨", layout="wide")

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
    .stChatMessage { 
        background-color: rgba(0, 0, 0, 0.6); 
        border-radius: 15px; 
        padding: 10px;
    }
    .stChatInputContainer {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Authentication Check & Sidebar Profile ---
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access your personal stylist.")
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
def query_gemini(wardrobe_context, prompt, target_lang):
    """Sends ONLY the current prompt and compressed wardrobe to Gemini to save tokens."""
    
    # Compact the JSON to remove unnecessary whitespace/newlines and save tokens
    compact_wardrobe = json.dumps(wardrobe_context, separators=(',', ':'))
    
    system_instruction = f"""
    You are Pookie, an elite Personal Fashion Stylist AI. 
    You have access to the user's digital wardrobe database.
    
    **USER'S WARDROBE DATA:**
    {compact_wardrobe}
    
    **CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE:**
    1. Reply ONLY in {target_lang}.
    2. You specialize EXCLUSIVELY in MEN'S FORMAL and SMART-CASUAL WEAR. Tailor your language, advice, and outfit combinations strictly for a sharp, sophisticated, masculine, and professional aesthetic.
    3. Suggest a complete outfit by combining specific Shirts and Pants from the wardrobe data above.
    4. Provide detailed responses explaining *why* the styles, colors, and textures work together for a professional or smart-casual setting.
    5. **NO LENGTH LIMITS:** Provide a full, comprehensive answer. Do not cut your response short.
    6. **IMAGE REQUIREMENT:** You ABSOLUTELY MUST show the images of the items you are recommending. Find the "img" URL for the item in the wardrobe data, and display it using exactly this HTML tag:
       <br><img src="INSERT_IMG_URL_HERE" width="150" style="border-radius:10px; margin: 10px 0;"><br>
       Do NOT use markdown for images. Only use the exact HTML tag above.
    7. i want the output response short and to the point with a little explanation for choice and must include images in response   
    **USER PROMPT:** {prompt}
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
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Sorry, Pookie is having trouble connecting right now: {e}"

def speech_to_text(audio_file, lang_code):
    """Transcribes audio using Google Speech Recognition, adapted for the selected language."""
    try:
        recognizer = sr.Recognizer()
        with open("temp_input.wav", "wb") as f:
            f.write(audio_file.read())
        
        with sr.AudioFile("temp_input.wav") as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=lang_code)
            return text
            
    except sr.UnknownValueError:
        return "Error: Could not understand audio. Please speak clearly."
    except Exception as e:
        return f"Error: {str(e)}"

def play_voice(text, lang_code):
    """Generates audio from text using gTTS and plays it."""
    try:
        clean_text = re.sub(r'<[^>]+>', '', text)
        short_lang = lang_code.split('-')[0] 
        tts = gTTS(text=clean_text, lang=short_lang) 
        tts.save("temp_out.mp3")
        st.audio("temp_out.mp3", format="audio/mp3", autoplay=True)
    except Exception as e:
        st.error(f"Voice generation failed: {e}")

# --- Main App Logic ---

username = st.session_state.get('username', 'Guest')
wardrobe_context = WARDROBE_DATA

# Sidebar Controls (Below the login status)
st.sidebar.divider()
selected_lang_name = st.sidebar.selectbox("Language", list(LANG_MAP.keys()))
selected_lang_code = LANG_MAP[selected_lang_name]

enable_voice = st.sidebar.checkbox("Voice Mode 🎙️")

if st.sidebar.button("Clear Chat Memory"):
    st.session_state.messages = []
    st.rerun()

# Chat History Init
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History (UI Only)
st.title("Ask Pookie ✨")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# Input Handling
user_input = None

if enable_voice:
    st.write("🎙️ Record your message:")
    audio_value = st.audio_input("Click to record")
    if audio_value:
        with st.spinner("Transcribing..."):
            transcribed_text = speech_to_text(audio_value, selected_lang_code)
            if "Error" not in transcribed_text:
                user_input = transcribed_text
                st.success(f"Heard: {user_input}")
            else:
                st.error(transcribed_text)

# Text Input Option
if not user_input:
    user_input = st.chat_input("What should I wear today?")

# Process Input
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Pookie is thinking..."):
            ai_response_text = query_gemini(
                wardrobe_context,               
                user_input,
                selected_lang_name
            )
            
            st.markdown(ai_response_text, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
            
            if enable_voice:
                with st.spinner("Generating audio..."):
                    play_voice(ai_response_text, selected_lang_code)
