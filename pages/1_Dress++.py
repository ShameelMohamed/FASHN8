import streamlit as st
import io
import os
import numpy as np
import cloudinary
import cloudinary.uploader
import firebase_admin
from firebase_admin import credentials, firestore
import json
background_css = """
<style>
    
    header {
        visibility: hidden;
    }
</style>
"""
st.markdown(background_css, unsafe_allow_html=True)

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firebase"])
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Configure Cloudinary
cloudinary.config(
    cloud_name=st.secrets["cloudinary"]["cloud_name"],
    api_key=st.secrets["cloudinary"]["api_key"],
    api_secret=st.secrets["cloudinary"]["api_secret"],
)

# Set HOME environment variable for Clarifai
if "HOME" not in os.environ:
    os.environ["HOME"] = os.path.expanduser("~")

# Check if user is logged in
if not st.session_state.get('authentication_status'):
    st.warning("Please log in to access this page.")
    if st.button("Login",use_container_width=True):
        st.switch_page("Home.py")
    st.stop()

from PIL import Image, ImageDraw
from collections import Counter
from rembg import remove
from clarifai.client.model import Model

# Define clothing categories
top_items = ["dress", "top", "vest"]
bottom_items = ["pants", "shorts", "skirt", "hosiery"]
category_colors = {"top": "green", "bottom": "blue"}

# Show logged in user and logout in sidebar
if st.session_state.get('authentication_status'):
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Logout",use_container_width=True):
        st.session_state['authentication_status'] = False
        st.session_state['username'] = None
        st.session_state['show_login_form'] = False
        st.session_state['show_signup_form'] = False
        st.rerun()

# Streamlit UI
st.markdown("<h2>Dress++</h2>", unsafe_allow_html=True)
st.write("Add your outfit to Find AI Match for your dress in Today's Drip.")
uploaded_file = st.file_uploader("Upload a clothing image", type=["jpg", "jpeg", "png", "webp"])

# Color extraction function
def get_dominant_color(image_rgba, alpha_threshold=30, min_brightness=20):
    data = np.array(image_rgba)
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    mask = (a > alpha_threshold) & (brightness > min_brightness)
    if np.count_nonzero(mask) == 0:
        return "#000000", "No visible color"
    filtered_pixels = data[mask]
    rgb_values = [tuple(pixel[:3]) for pixel in filtered_pixels]
    most_common = Counter(rgb_values).most_common(1)[0][0]
    hex_color = '#%02x%02x%02x' % most_common
    return hex_color, "Dominant"

# Background removal
def remove_background_locally(image_bytes):
    output_bytes = remove(image_bytes)
    return Image.open(io.BytesIO(output_bytes)).convert("RGBA")

# Main process
if uploaded_file:
    original_image = Image.open(uploaded_file).convert("RGB")
    width, height = original_image.size

    # Convert image to bytes
    buffer = io.BytesIO()
    original_image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    try:
        with st.spinner("Uploading..."):
            bg_removed_image = remove_background_locally(image_bytes)
            
            # Clarifai setup
            pat = st.secrets["clarifai"]["pat"]
            apparel_model_url = "https://clarifai.com/clarifai/main/models/apparel-detection"
            apparel_model = Model(url=apparel_model_url, pat=pat)

            prediction = apparel_model.predict_by_bytes(image_bytes, input_type="image")
            regions = prediction.outputs[0].data.regions

        if not regions:
            st.warning("No clothing items detected.")
        else:
            draw = ImageDraw.Draw(original_image)
            st.subheader("👕 Detected Items")

            # Create two columns for displaying items
            cols = st.columns(2)
            col_idx = 0  # Track which column we're currently using

            for region in regions:
                concept = region.data.concepts[0]
                label = concept.name
                confidence = concept.value

                if confidence < 0.6:
                    continue

                if label in top_items:
                    category = "top"
                elif label in bottom_items:
                    category = "bottom"
                else:
                    continue

                box = region.region_info.bounding_box
                left = int(box.left_col * width)
                top = int(box.top_row * height)
                right = int(box.right_col * width)
                bottom = int(box.bottom_row * height)

                # Crop from background-removed image
                cropped = bg_removed_image.crop((left, top, right, bottom))
                hex_crop, _ = get_dominant_color(cropped)

                # Upload cropped image to Cloudinary
                buffer = io.BytesIO()
                cropped.save(buffer, format="PNG")
                buffer.seek(0)
                upload_result = cloudinary.uploader.upload(
                    buffer,
                    folder="fashion8",
                    public_id=f"{st.session_state['username']}_{label}_{hex_crop.replace('#', '')}"
                )
                
                # Get the URL of the uploaded image
                image_url = upload_result['secure_url']
                
                # Display in alternating columns
                with cols[col_idx]:
                    st.image(cropped, caption=f"{label.capitalize()} Region", width=200)
                    
                    # Add upload button for each detected item
                    if st.button(f"Upload {label.capitalize()}"):
                        with st.spinner("Uploading..."):
                            # Upload to Cloudinary
                            buffer = io.BytesIO()
                            cropped.save(buffer, format="PNG")
                            buffer.seek(0)
                            upload_result = cloudinary.uploader.upload(
                                buffer,
                                folder="fashion8",
                                public_id=f"{st.session_state['username']}_{label}_{hex_crop.replace('#', '')}"
                            )
                            
                            # Find the user document by username
                            users_ref = db.collection('users')
                            query = users_ref.where('username', '==', st.session_state['username']).limit(1)
                            user_docs = query.get()
                            
                            if not user_docs:
                                st.error("User document not found!")
                                st.stop()
                            
                            user_doc = user_docs[0]
                            user_ref = user_doc.reference

                            # Get existing data
                            collection_name = "shirts" if category == "top" else "pants"
                            current_data = user_doc.to_dict().get(collection_name, {})
                            
                            # Append new color:url to existing data
                            current_data[hex_crop] = upload_result['secure_url']
                            
                            # Update the document with merged data
                            user_ref.update({
                                collection_name: current_data
                            })
                            
                            # Display upload results
                            st.success(f"{label.capitalize()} uploaded successfully!")
                
                # Toggle between columns (0 and 1)
                col_idx = (col_idx + 1) % 2

    except Exception as e:
        st.error(f"❌ Error: {e}")



