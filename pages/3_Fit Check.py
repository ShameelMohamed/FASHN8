import streamlit as st
from gradio_client import Client, handle_file
import tempfile
import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

st.title("FIT CHECK")
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
        color: white;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
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
def save_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split('.')[-1])
    tmp.write(uploaded_file.read())
    tmp.close()
    return tmp.name

# Two uploaders in same row using columns
col1, col2 = st.columns(2)
with col1:
    base_img = st.file_uploader("Upload Your Image", type=["png", "jpg", "jpeg", "webp"])
with col2:
    garment_img = st.file_uploader("Upload Dress Image", type=["png", "jpg", "jpeg","webp"])

# Dropdown selector for garment type
garment_type = st.selectbox(
    "Select Garment Type",
    ["Top Garment", "Full-body Garment","Eyewear","Footwear"  ]
)

# Default workflow_choice based on dropdown selection
workflow_map = {
    "Footwear": "footwear",
    "Eyewear": "eyewear",
    "Top Garment": "top",
    "Full-body Garment": "full-body"
}
workflow_choice = workflow_map[garment_type]

if st.button("Generate", use_container_width=True):
    if base_img is None or garment_img is None:
        st.error("Please upload both base image and garment image.")
    else:
        with st.spinner("Generating output image... Please wait for 30 secs..."):
            client = Client("sm4ll-VTON/sm4ll-VTON-Demo")

            base_img_path = save_uploaded_file(base_img)
            garment_img_path = save_uploaded_file(garment_img)

            base_img_dict = handle_file(base_img_path)
            garment_img_dict = handle_file(garment_img_path)

            
            result = client.predict(
                base_img=base_img_dict,
                garment_img=garment_img_dict,
                workflow_choice=workflow_choice,
                mask_img=None,  # no mask_img input
                api_name="/generate"
            )

        if result and isinstance(result, str):
            st.image(result, caption="Generated Output", width=250)
            st.success("Image generated successfully!")
        else:
            st.error("Failed to get output image.")






