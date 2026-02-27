import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import requests
import speech_recognition as sr
from gtts import gTTS
import os
import re

# --- Configuration ---
GEMINI_API_KEY = "AIzaSyAUiHPFj5lBH4SM-NQMfY03JhdenIwJRCc"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

st.set_page_config(page_title="My Personal Stylist", layout="wide")

# Hide Streamlit default header


# --- Background & CSS ---
bg_url = "https://logincdn.msftauth.net/shared/5/images/fluent_web_dark_2_bf5f23287bc9f60c9be2.svg"
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
    /* Chat bubbles styling */
    .stChatMessage {{
        background-color: rgba(0, 0, 0, 0.6);
        border-radius: 15px;
        padding: 10px;
    }}
    /* Remove black background from chat input */
    .stChatInputContainer {{
        background-color: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Firebase Init ---
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Authentication Check ---
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access your personal stylist.")
    if st.button("Login", use_container_width=True):
        st.switch_page("Home.py")
    st.stop()

# --- Language Configuration Maps ---
LANG_MAP = {
    "English": {"stt": "en-IN", "tts": "en", "prompt": "English"},
    "Tamil": {"stt": "ta-IN", "tts": "ta", "prompt": "Tamil"},
    "Malayalam": {"stt": "ml-IN", "tts": "ml", "prompt": "Malayalam"},
    "Telugu": {"stt": "te-IN", "tts": "te", "prompt": "Telugu"},
    "Hindi": {"stt": "hi-IN", "tts": "hi", "prompt": "Hindi"}
}

# --- Helper Functions ---

def fetch_wardrobe_and_schedule(username):
    """Fetches user shirts, pants, and weekly schedule from Firestore."""
    users_ref = db.collection('users')
    query = users_ref.where('username', '==', username).limit(1)
    user_docs = query.get()
    
    if not user_docs:
        return {}, {}, {}
    
    data = user_docs[0].to_dict()
    # Fetch exact keys "shirts", "pant", and "week" based on your DB schema
    return data.get("shirts", {}), data.get("pant", {}), data.get("week", {})

def query_gemini(history, wardrobe_context, week_schedule, target_language, prompt):
    """
    Sends chat history + wardrobe + schedule + prompt to Gemini, enforcing language and inline images.
    """
    system_instruction = f"""
    You are a professional, high-end Personal Fashion Stylist AI. 
    Your name is Pookie.
    
    **USER'S WARDROBE DATA (Includes image URLs):**
    {json.dumps(wardrobe_context, indent=2)}
    
    **USER'S OUTFIT SCHEDULE THIS WEEK:**
    {json.dumps(week_schedule, indent=2)}
    
    **YOUR INSTRUCTIONS:**
    1. Always act as a friendly, expert stylist.
    2. Suggest outfits by combining specific items from their wardrobe. Use their weekly schedule to advise them on what they are already planning to wear.
    3. Provide detailed and creative responses explaining *why* the colors or styles work together.
    4. **CRITICAL VISUAL RULE:** Whenever you recommend or mention a specific item from their wardrobe, you MUST display its image inline using HTML. Use this exact format: <br><img src="THE_IMG_URL" width="120" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); margin: 10px 0;"><br>
    5. **CRITICAL LANGUAGE RULE:** You MUST reply entirely in {target_language}. Do not use English unless the requested language is English.
    """
    
    contents = [{"role": "user", "parts": [{"text": system_instruction}]}]
    
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
        
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500, # Increased slightly to accommodate HTML image tags
        }
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
        return f"Error contacting Stylist AI: {e}"

def speech_to_text(audio_file, lang_code):
    """Transcribes audio using Google Speech Recognition in the selected language."""
    try:
        recognizer = sr.Recognizer()
        with open("temp_input.wav", "wb") as f:
            f.write(audio_file.read())
        
        with sr.AudioFile("temp_input.wav") as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=lang_code)
            return text
            
    except sr.UnknownValueError:
        return "Error: Could not understand audio. Please speak clearly in the selected language."
    except sr.RequestError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if os.path.exists("temp_input.wav"):
            os.remove("temp_input.wav")

def text_to_speech(text, lang_code):
    """Generates audio using Google TTS in the selected language."""
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        filename = f"response_{lang_code}.mp3"
        tts.save(filename)
        return filename
    except Exception as e:
        st.error(f"TTS Error: {e}")
        return None

# --- Main App Logic ---

# 1. Fetch User Data
username = st.session_state['username']
shirts, pants, weekly_schedule = fetch_wardrobe_and_schedule(username)
wardrobe_context = {"shirts": shirts, "pants": pants}

# 2. Sidebar Controls
st.sidebar.title(f"Stylist for {username}")

st.sidebar.markdown("### Settings")
selected_lang = st.sidebar.radio(
    "Select Language / மொழி / ഭാഷ / భాష / भाषा",
    options=["English", "Tamil", "Malayalam", "Telugu", "Hindi"],
    index=0
)

enable_voice = st.sidebar.checkbox("Enable Voice Mode 🎙️")

if st.sidebar.button("Clear Chat Memory"):
    st.session_state.messages = []
    st.rerun()

# 3. Chat History Init
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Display Chat History
st.title("Ask Pookie ✨")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # unsafe_allow_html=True is REQUIRED here so the AI's <img> tags render properly!
        st.markdown(message["content"], unsafe_allow_html=True)

# 5. Input Handling (Text or Voice)
user_input = None

if enable_voice:
    st.write(f"🎙️ Speak in **{selected_lang}**:")
    audio_value = st.audio_input("Click to record")
    
    if audio_value and st.session_state.get('last_audio_id') != id(audio_value):
        st.session_state.last_audio_id = id(audio_value) 
        with st.spinner("Transcribing..."):
            lang_code_stt = LANG_MAP[selected_lang]["stt"]
            transcribed_text = speech_to_text(audio_value, lang_code_stt)
            
            if "Error" not in transcribed_text:
                user_input = transcribed_text
            else:
                st.error(transcribed_text)

text_input = st.chat_input("Ask me about your wardrobe and outfit suggestions...")
if text_input:
    user_input = text_input

# 6. Process Input
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Styling in progress..."):
            ai_response_text = query_gemini(
                st.session_state.messages[:-1], 
                wardrobe_context,               
                weekly_schedule,                
                LANG_MAP[selected_lang]["prompt"], 
                user_input
            )
            
            # Render response with HTML images allowed
            st.markdown(ai_response_text, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": ai_response_text})

            # Voice Output Logic
            if enable_voice:
                with st.spinner("Generating audio..."):
                    # CRITICAL: We must strip the HTML <img> tags out before sending to TTS.
                    # Otherwise, Pookie will read out "<img src='https...'>" like a robot!
                    clean_text_for_voice = re.sub(r'<[^>]+>', '', ai_response_text)
                    
                    lang_code_tts = LANG_MAP[selected_lang]["tts"]
                    audio_path = text_to_speech(clean_text_for_voice[:400], lang_code_tts) 
                    
                    if audio_path:
                        st.audio(audio_path, format="audio/mp3", autoplay=True)
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
