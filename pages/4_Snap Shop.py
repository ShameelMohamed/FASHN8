import streamlit as st
from gradio_client import Client, handle_file
import tempfile
import re
import io
import os
from PIL import Image
from rembg import remove

import urllib.parse
import requests
st.set_page_config(page_title="Snap Shop", page_icon="🛍")

st.title("SNAP SHOP 🛒")
import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access this page.")
    if st.button("Login", use_container_width=True):
        st.switch_page("Home.py")
    st.stop()
# Show logged in user and logout in sidebar
if st.session_state.get('authentication_status'):
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['authentication_status'] = False
        st.session_state['username'] = None
        st.session_state['show_login_form'] = False
        st.session_state['show_signup_form'] = False
        st.rerun()



# ----------- Fix Clarifai HOME env issue (Windows) -----------
if "HOME" not in os.environ:
    os.environ["HOME"] = os.path.expanduser("~")
from clarifai.client.model import Model
# ----------- Save image to temp file -----------
def save_temp(image, ext="png"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        image.save(tmp, format=ext.upper())
        return tmp.name

# ----------- Remove background locally -----------
def remove_background_locally(image_bytes):
    output_bytes = remove(image_bytes)
    return Image.open(io.BytesIO(output_bytes)).convert("RGBA")

# ----------- Search buttons -----------
def multi_store_buttons(query):
    encoded_query = urllib.parse.quote_plus(query)

    st.markdown("""
    <style>
    .custom-button-container {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 1rem;
    }
    .custom-button {
        flex: 1;
        padding: 12px 24px;
        border-radius: 8px;
        text-align: center;
        text-decoration: none;
        font-weight: 600;
        font-size: 16px;
        color: white !important;
        user-select: none;
        transition: background-color 0.3s ease;
        display: inline-block;
    }
    .amazon { background-color: #FF9900; }
    .amazon:hover { background-color: #e68a00; }
    .flipkart { background-color: #2874F0; }
    .flipkart:hover { background-color: #215ec9; }
    .myntra { background-color: #FF3F6C; }
    .myntra:hover { background-color: #e63662; }
    .ajio { background-color: #2C2C54; }
    .ajio:hover { background-color: #1f1f3b; }
    .meesho { background-color: #E94057; }
    .meesho:hover { background-color: #cc3449; }
    </style>
    """, unsafe_allow_html=True)

    buttons_html = f'''
    <div class="custom-button-container">
        <a href="https://www.amazon.in/s?k={encoded_query}"
           target="_blank" rel="noopener noreferrer"
           class="custom-button amazon">Amazon</a>
        <a href="https://www.flipkart.com/search?q={encoded_query}"
           target="_blank" rel="noopener noreferrer"
           class="custom-button flipkart">Flipkart</a>
        <a href="https://www.myntra.com/{encoded_query}"
           target="_blank" rel="noopener noreferrer"
           class="custom-button myntra">Myntra</a>
        <a href="https://www.ajio.com/search/?text={encoded_query}"
           target="_blank" rel="noopener noreferrer"
           class="custom-button ajio">AJIO</a>
        <a href="https://www.meesho.com/search?q={encoded_query}"
           target="_blank" rel="noopener noreferrer"
           class="custom-button meesho">Meesho</a>
    </div>
    '''
    st.markdown(buttons_html, unsafe_allow_html=True)



# ----------- Gemini 1.5 Flash caption refinement -----------
def refine_caption_with_gemini(raw_caption):
    GEMINI_API_KEY = st.secrets["gemini"]["api_key"]  # <-- replace with your API key
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    prompt = f"""
You are a fashion search query generator.
Given this clothing description: "{raw_caption}",
return a short, keyword-friendly query for searching on fashion websites.
Remove mentions of people, backgrounds, lighting, and poses.
Focus only on clothing type, color, material, and style.
"""

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    response = requests.post(
        f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            st.warning(f"Gemini response parse error: {e}")
            return raw_caption
    else:
        st.warning(f"Gemini API error: {response.text}")
        return raw_caption

# ----------- Streamlit UI -----------
uploaded_file = st.file_uploader("Upload your Inspiration Dress Image", type=["png", "jpg", "jpeg", "webp"])

if uploaded_file:
    original_image = Image.open(uploaded_file).convert("RGB")
    width, height = original_image.size

    buffer = io.BytesIO()
    original_image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    with st.spinner("Finding Similar Dresses ..."):
        try:
            # Background removal
            bg_removed_image = remove_background_locally(image_bytes)

            # Clarifai apparel detection
            pat = st.secrets["clarifai"]["pat"]  # replace with your PAT
            apparel_model_url = "https://clarifai.com/clarifai/main/models/apparel-detection"
            apparel_model = Model(url=apparel_model_url, pat=pat)

            prediction = apparel_model.predict_by_bytes(image_bytes, input_type="image")
            regions = prediction.outputs[0].data.regions

            if not regions:
                st.error("No dress detected.")
                st.stop()

            dress_labels = [
                "dress", "gown", "frock", "saree",
                "shirt", "tshirt", "jacket",
                "coat", "trousers", "jeans",
                "suit", "blazer", "hoodie",
                "sweater", "vest"
            ]
            dress_crop = None
            for region in regions:
                label = region.data.concepts[0].name.lower()
                if label in dress_labels:
                    box = region.region_info.bounding_box
                    left = int(box.left_col * width)
                    top = int(box.top_row * height)
                    right = int(box.right_col * width)
                    bottom = int(box.bottom_row * height)
                    dress_crop = bg_removed_image.crop((left, top, right, bottom))
                    break

            if dress_crop is None:
                st.error("No dress detected in the image.")
                st.stop()

            st.image(dress_crop, caption="Detected Dress", width=200)

            # Convert RGBA → RGB before saving
            dress_crop = dress_crop.convert("RGB")
            temp_path = save_temp(dress_crop, ext="png")

            # -------- Use ovi054/image-to-prompt instead of BLIP --------
            client = Client("ovi054/image-to-prompt")
            image_for_client = handle_file(temp_path)

            caption = client.predict(
                image=image_for_client,
                api_name="/predict"
            )

            # Clean caption
            caption = re.sub(r'[^a-zA-Z0-9\s]', '', caption).strip()

            # Refine caption using Gemini
            refined_caption = refine_caption_with_gemini(caption)

            # Show multi-store search buttons
            multi_store_buttons(refined_caption)

        except Exception as e:
            st.error(f"Error: {str(e)}")



