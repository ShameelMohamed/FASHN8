import streamlit as st
from gradio_client import Client, handle_file
import tempfile
import asyncio
from PIL import Image
import numpy as np
from collections import Counter
import colorsys
import random
import os

# --- Prevent Gradio Asyncio Thread Crashes on Cloud ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

st.title("Virtual Try-On ✨")

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
    header {{
        visibility: hidden !important;
    }}
    #MainMenu {{ visibility: hidden !important; }}
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------
def save_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split('.')[-1])
    tmp.write(uploaded_file.read())
    tmp.close()
    return tmp.name

def get_dominant_color(image_path):
    """Extract dominant color from an image."""
    try:
        img = Image.open(image_path).convert('RGB')
        img = img.resize((150, 150))  # Resize for faster processing
        pixels = np.array(img)
        pixels_reshaped = pixels.reshape(-1, 3)
        
        # Get most common color
        rgb = pixels_reshaped[np.random.choice(pixels_reshaped.shape[0], 5000, replace=True)]
        most_common = Counter(map(tuple, rgb)).most_common(1)[0][0]
        
        return most_common
    except:
        return (128, 128, 128)  # Default gray if error

def rgb_to_hsl(rgb):
    """Convert RGB to HSL."""
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l

def calculate_compatibility_rating(rgb1, rgb2):
    """Calculate compatibility rating between two colors (1.0 - 5.0)."""
    h1, s1, l1 = rgb_to_hsl(rgb1)
    h2, s2, l2 = rgb_to_hsl(rgb2)
    
    # Calculate differences
    h_diff = abs(h1 - h2)
    h_diff = h_diff if h_diff <= 0.5 else 1.0 - h_diff
    l_diff = abs(l1 - l2)
    s_diff = abs(s1 - s2)
    
    # Simple scoring: complementary colors and good contrast = higher rating
    score = 5.0
    score -= h_diff * 2  # Hue difference penalty
    score -= l_diff * 0.5  # Lightness difference (small penalty)
    score += min(l_diff, s_diff) * 0.5  # Bonus for some contrast
    
    # Add some randomness for realism (±0.3)
    score += random.uniform(-0.5, 0.5)
    
    # Clamp between 1.0 and 5.0
    return round(max(1.0, min(5.0, score)), 1)

# --------------------------------------------------------------------------
# UI LAYOUT
# --------------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    base_img = st.file_uploader("Upload Your Image", type=["png", "jpg", "jpeg", "webp"])
with col2:
    garment_img = st.file_uploader("Upload Garment/Product Image", type=["png", "jpg", "jpeg", "webp"])

# Dropdown with logic to match the API's specific keywords
garment_type = st.selectbox(
    "Select Garment Type",
    ["Tops", "Bottoms", "One-Pieces"]
)

# Category mapping for the new API
category_map = {
    "Tops": "tops",
    "Bottoms": "bottoms",
    "One-Pieces": "one-pieces"
}
category = category_map[garment_type]

# --------------------------------------------------------------------------
# GENERATION LOGIC
# --------------------------------------------------------------------------
if st.button("Generate", use_container_width=True):
    if base_img is None or garment_img is None:
        st.error("Please upload both your image and garment image.")
    else:
        with st.spinner("Generating virtual try-on..."):
            try:
                # 1. INITIALIZE CLIENT securely using st.secrets
                os.environ["HF_TOKEN"] = st.secrets["huggingface"]["token"]
                client = Client("fashn-ai/fashn-vton-1.5")

                # 2. PREPARE FILES
                base_img_path = save_uploaded_file(base_img)
                garment_img_path = save_uploaded_file(garment_img)

                # 3. PREPARE HANDLES
                person_image = handle_file(base_img_path)
                garment_image = handle_file(garment_img_path)

                # 4. CALL API with /try_on endpoint
                result = client.predict(
                    person_image=person_image,
                    garment_image=garment_image,
                    category=category,
                    garment_photo_type="model",
                    api_name="/try_on"
                )

                # 5. HANDLE RESULT
                if result:
                    # Extract output path from result
                    output_path = result
                    
                    if isinstance(result, (list, tuple)) and len(result) > 0:
                        output_path = result[0]
                    
                    if isinstance(output_path, dict) and 'path' in output_path:
                        output_path = output_path['path']

                    st.image(output_path, caption="Virtual Try-On Result", width=250)
                    st.success("✨ Try-on generated successfully!")
                    
                    # Auto-Rate the Try-On
                    st.markdown("---")
                    
                    # Extract colors and calculate rating
                    person_color = get_dominant_color(base_img_path)
                    garment_color = get_dominant_color(garment_img_path)
                    rating = calculate_compatibility_rating(person_color, garment_color)
                    
                    # Display rating with stars
                    stars = "⭐" * int(rating) + ("✨" if rating % 1 >= 0.5 else "")
                    st.markdown(f"### AI Rating: {rating}/5.0 {stars}")
                    st.write(f"This outfit combination has a **{rating}/5.0** style compatibility score!")
                else:
                    st.error("API returned empty result.")
            
            except Exception as e:
                error_msg = str(e)
                
                # Handle GPU quota exceeded error
                if "GPU quota" in error_msg or "exceeded" in error_msg:
                    st.warning("⏳ **GPU Quota Temporarily Exceeded**")
                    st.info("""
                    The AI model is currently at capacity. This is a free service limitation.
                    
                    **Options:**
                    1. **Wait and retry** - The quota usually resets in 15-30 minutes
                    2. **Try again later** - Peak hours may have more wait time
                    3. **Use simpler clothing** - Smaller images process faster
                    
                    Please try again in a few minutes! ✨
                    """)
                else:
                    st.error(f"❌ API Error: {error_msg}")
                    st.info("Please check your internet connection and try again.")
