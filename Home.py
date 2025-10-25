

import streamlit as st
import hashlib
import firebase_admin
from firebase_admin import credentials, firestore
import os


st.set_page_config(
    page_title="FashN8 ",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)
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
# --- Firebase initialization ---
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()



st.markdown('''# FashN8

Welcome to **FashN8** — your AI-powered outfit curator, fit‑check, and snap‑to‑shop assistant!<br>

Use the sidebar to navigate:
- <b>Dress++</b>: Add your clothing; detect the item and save it to your wardrobe.
- <b>Today\'s Drip</b>: Get AI-powered color matches and alternates from your wardrobe, with a short reason for each pick.
- <b>Fit Check</b>: Virtually try on garments using your photo with multiple garment types.
- <b>Snap Shop</b>: Upload any inspiration image; we isolate the garment, create a clean search query, and open one-click searches on Amazon, Flipkart, and Myntra.

Stay stylish!
''', unsafe_allow_html=True)

# --- Remove in-memory user store, use Firestore instead ---

# --- Auth logic ---
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None


# --- Show login/signup only if not authenticated ---
if not st.session_state.get('authentication_status'):
    with st.container():
        col1, col2 = st.columns(2)
        login_clicked = col1.button("Login", key="login_btn", use_container_width=True)
        signup_clicked = col2.button("Signup", key="signup_btn", use_container_width=True)

        # Always update session state on button click
        if login_clicked:
            st.session_state['show_login_form'] = True
            st.session_state['show_signup_form'] = False
        if signup_clicked:
            st.session_state['show_signup_form'] = True
            st.session_state['show_login_form'] = False

    # Show login form if set in session state and not authenticated
    if not st.session_state.get('authentication_status') and st.session_state.get('show_login_form'):
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    # Firestore: query for user by username field
                    users_ref = db.collection('users')
                    query = users_ref.where('username', '==', username).limit(1).stream()
                    user_doc = next(query, None)
                    if user_doc:
                        user = user_doc.to_dict()
                        if user['password'] == password:
                            st.session_state['authentication_status'] = True
                            st.session_state['username'] = username
                            st.success(f"Welcome, {user['username']}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    else:
                        st.info("[DEBUG] No user found with that username.")
                        st.error("Invalid username or password.")

    # Show signup form if set in session state and not authenticated
    elif not st.session_state.get('authentication_status') and st.session_state.get('show_signup_form'):
        with st.form("signup_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Signup")
            if submit:
                if not username or not email or not password or not confirm_password:
                    st.error("All fields are required.")
                else:
                    # Firestore: check if username already exists
                    users_ref = db.collection('users')
                    query = users_ref.where('username', '==', username).limit(1).stream()
                    user_doc = next(query, None)
                    if user_doc:
                        st.error("Username already exists.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        # Add user with random doc ID
                        users_ref.add({
                            'username': username,
                            'password': password,
                            'email': email,
                            'shirts': {},  # Initialize empty collections
                            'pants': {}
                        })
                        st.success("Signup successful! Please log in.")
                        st.session_state['show_signup_form'] = False
                        st.session_state['show_login_form'] = True
                        st.rerun()

# --- If logged in, show logout in sidebar ---
if st.session_state.get('authentication_status'):
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Logout"):
        st.session_state['authentication_status'] = False
        st.session_state['username'] = None
        st.session_state['show_login_form'] = False
        st.session_state['show_signup_form'] = False
        st.rerun()





