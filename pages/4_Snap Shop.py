import streamlit as st
from gradio_client import Client, handle_file
import tempfile
import re
import io
import os
import json
from PIL import Image
from rembg import remove
import urllib.parse
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from clarifai.client.model import Model

st.set_page_config(page_title="Snap Shop", page_icon="🛍", layout="wide")
bg_url = "https://logincdn.msftauth.net/shared/5/images/fluent_web_dark_2_bf5f23287bc9f60c9be2.svg"

# Keep ONLY the background image and hidden header CSS
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
    header {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("SNAP SHOP 🛒")
st.caption("Upload an inspiration photo. We'll extract the garment, find it online, and check your wardrobe.")

# ----------- Firebase Init -----------
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ----------- Authentication check -----------
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access this page.")
    if st.button("Login", use_container_width=True):
        st.switch_page("Home.py")
    st.stop()

# Show logged in user and logout in sidebar
st.sidebar.success(f"Logged in as {st.session_state['username']}")
if st.sidebar.button("Logout", use_container_width=True):
    for key in ['authentication_status', 'username', 'show_login_form', 'show_signup_form']:
        st.session_state[key] = None
    st.rerun()

# ----------- Fetch Wardrobe Data -----------
users_ref = db.collection('users')
query = users_ref.where('username', '==', st.session_state['username']).limit(1)
user_docs = query.get()

shirts_data = {}
pants_data = {}

if user_docs:
    user_data = user_docs[0].to_dict()
    shirts_data = user_data.get("shirts", {})
    pants_data = user_data.get("pant", {})

# ----------- Gemini AI Init -----------
GEMINI_API_KEY = "AIzaSyAUiHPFj5lBH4SM-NQMfY03JhdenIwJRCc"
genai.configure(api_key=GEMINI_API_KEY)
json_model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
text_model = genai.GenerativeModel('gemini-2.5-flash')

# ----------- Fix Clarifai HOME env issue (Windows) -----------
if "HOME" not in os.environ:
    os.environ["HOME"] = os.path.expanduser("~")

# ----------- Helper Functions -----------
def save_temp(image, ext="png"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        image.save(tmp, format=ext.upper())
        return tmp.name

def remove_background_locally(image_bytes):
    output_bytes = remove(image_bytes)
    return Image.open(io.BytesIO(output_bytes)).convert("RGBA")

def multi_store_buttons(query):
    # Pure Streamlit implementation using st.link_button and columns
    encoded_query = urllib.parse.quote_plus(query)
    
    cols = st.columns(5)
    cols[0].link_button("Amazon", f"https://www.amazon.in/s?k={encoded_query}", use_container_width=True)
    cols[1].link_button("Flipkart", f"https://www.flipkart.com/search?q={encoded_query}", use_container_width=True)
    cols[2].link_button("Myntra", f"https://www.myntra.com/{encoded_query}", use_container_width=True)
    cols[3].link_button("AJIO", f"https://www.ajio.com/search/?text={encoded_query}", use_container_width=True)
    cols[4].link_button("Meesho", f"https://www.meesho.com/search?q={encoded_query}", use_container_width=True)

def refine_caption_with_gemini(raw_caption):
    prompt = f"""
    You are a fashion search query generator.
    Given this clothing description: "{raw_caption}",
    return a short, keyword-friendly query for searching on fashion websites.
    Remove mentions of people, backgrounds, lighting, and poses.
    Focus only on clothing type, color, material, and style.
    Return ONLY the raw string query, nothing else.
    """
    try:
        response = text_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return raw_caption

def find_similar_in_wardrobe(target_desc, target_category, shirts_db, pants_db):
    wardrobe = []
    
    if target_category == "Shirt":
        for k, v in shirts_db.items():
            wardrobe.append({"id": k, "hex": v.get("hex", "#ffffff"), "img": v.get("img", "")})
    else:
        for k, v in pants_db.items():
            wardrobe.append({"id": k, "hex": v.get("hex", "#ffffff"), "img": v.get("img", "")})
            
    if not wardrobe:
        return []
        
    simplified_wardrobe = [{"id": item["id"], "hex": item["hex"]} for item in wardrobe]
    
    prompt = f"""
    I am looking for clothes similar in color to this description: "{target_desc}".
    Here is my available {target_category} wardrobe with hex color codes: {json.dumps(simplified_wardrobe)}
    
    Find up to 4 items in this list that are the closest color match to the description. Evaluate the hex codes visually.
    Return ONLY a valid JSON list of strings representing the "id"s of the matching items. Example: ["1", "3"]
    """
    try:
        response = json_model.generate_content(prompt)
        matched_ids = json.loads(response.text)
        return [item for item in wardrobe if item["id"] in matched_ids]
    except Exception as e:
        return []

# ----------- Streamlit UI Flow -----------

with st.container(border=True):
    uploaded_file = st.file_uploader("Drop your image here", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")

if uploaded_file:
    st.write("") # Spacer
    original_image = Image.open(uploaded_file).convert("RGB")
    width, height = original_image.size

    buffer = io.BytesIO()
    original_image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    with st.spinner("Extracting garment & analyzing style..."):
        try:
            # Background removal
            bg_removed_image = remove_background_locally(image_bytes)

            # Clarifai apparel detection
            pat = "33d1a403568342b7b4cfb62c84989449"
            apparel_model_url = "https://clarifai.com/clarifai/main/models/apparel-detection"
            apparel_model = Model(url=apparel_model_url, pat=pat)

            prediction = apparel_model.predict_by_bytes(image_bytes, input_type="image")
            regions = prediction.outputs[0].data.regions

            if not regions:
                st.error("No dress detected.")
                st.stop()

            # Categorize labels
            top_labels = ["dress", "gown", "frock", "saree", "shirt", "tshirt", "jacket", "coat", "suit", "blazer", "hoodie", "sweater", "vest", "top"]
            bottom_labels = ["trousers", "jeans", "shorts", "skirt", "pants", "bottom"]
            
            dress_crop = None
            detected_category = None
            
            for region in regions:
                label = region.data.concepts[0].name.lower()
                if label in top_labels:
                    detected_category = "Shirt"
                elif label in bottom_labels:
                    detected_category = "Pant"
                    
                if detected_category:
                    box = region.region_info.bounding_box
                    left = int(box.left_col * width)
                    top = int(box.top_row * height)
                    right = int(box.right_col * width)
                    bottom = int(box.bottom_row * height)
                    dress_crop = bg_removed_image.crop((left, top, right, bottom))
                    break

            if dress_crop is None:
                st.error("No recognizable clothing item detected in the image.")
                st.stop()

            # Convert RGBA → RGB before saving
            dress_crop = dress_crop.convert("RGB")
            temp_path = save_temp(dress_crop, ext="png")

            # Get caption from Gradio Client
            client = Client("ovi054/image-to-prompt")
            image_for_client = handle_file(temp_path)
            caption = client.predict(image=image_for_client, api_name="/predict")
            os.remove(temp_path)

            # Clean and Refine caption
            caption = re.sub(r'[^a-zA-Z0-9\s]', '', caption).strip()
            refined_caption = refine_caption_with_gemini(caption)
            
            # --- RENDER RESULTS (Pure Streamlit Layout) ---
            col1, col2 = st.columns([1, 1.8], gap="large")
            
            with col1:
                with st.container(border=True):
                    st.image(dress_crop, use_container_width=True)
            
            with col2:
                # FIRST BOX: AI Details
                with st.container(border=True):
                    st.subheader("🎯 AI Extraction Details")
                    st.success(f"✓ {detected_category} Detected")
                    
                    st.caption("Optimized Search Query:")
                    st.info(f"**{refined_caption}**")
                
                # SECOND BOX: Find it Online
            with st.container(border=True):
                    st.subheader("🛒 Find it Online")
                    multi_store_buttons(refined_caption)

            # --- WARDROBE SIMILARITY CHECK ---
            st.write("")
            st.write("")
            st.subheader(f"Similar {detected_category}s in Your Wardrobe")
            
            with st.spinner(f"Scanning your {detected_category.lower()} wardrobe for color matches..."):
                matches = find_similar_in_wardrobe(refined_caption, detected_category, shirts_data, pants_data)
            
            if not matches:
                st.info(f"You don't seem to have any {detected_category.lower()}s matching this color in your wardrobe yet.")
            else:
                # Display matches in a native responsive grid
                cols = st.columns(4)
                for index, item in enumerate(matches):
                    with cols[index % 4]:
                        with st.container(border=True):
                            st.image(item['img'], use_container_width=True)
                            
                            # Using Streamlit's native color picker (disabled) as a neat color swatch!
                            col_a, col_b = st.columns([1, 3])
                            with col_a:
                                st.color_picker("Color", item['hex'], disabled=True, label_visibility="collapsed", key=f"color_{index}")
                            with col_b:
                                st.caption("Match Color")

        except Exception as e:
            st.error(f"Error processing image: {str(e)}")

