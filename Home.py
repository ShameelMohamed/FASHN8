import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(
    page_title="FashN8",
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
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Firebase initialization ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"🔥 Firebase Error: Failed to connect. Did you add your secrets to the Streamlit Cloud dashboard? {e}")
    st.stop()

st.markdown('''# FashN8

Welcome to **FashN8** — your AI-powered outfit curator, fit-check, and snap-to-shop assistant!<br>

Use the sidebar to navigate:
- **Dress++**: Add your clothing; detect the item and save it to your wardrobe.
- **Today's Drip**: Get AI-powered color matches and alternates from your wardrobe, with a short reason for each pick.
- **Virtual Try-On**: Virtually try on garments using your photo with multiple garment types.
- **Snap Shop**: Upload any inspiration image; we isolate the garment, create a clean search query, and open one-click searches on Amazon, Flipkart, and Myntra.
- **Ask Pookie & Wardrobe Summary**: Get AI styling advice and a professional analysis of your current wardrobe patterns.

Stay stylish!
''', unsafe_allow_html=True)

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
    if st.session_state.get('show_login_form'):
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
                        if user.get('password') == password:
                            st.session_state['authentication_status'] = True
                            st.session_state['username'] = username
                            st.success(f"Welcome, {user['username']}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    else:
                        st.error("Invalid username or password.")

    # Show signup form if set in session state and not authenticated
    elif st.session_state.get('show_signup_form'):
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
                        # Add user with initialized database structure
                        users_ref.add({
                            'username': username,
                            'password': password,
                            'email': email,
                            'shirts': {},  # Initialize empty map for shirts
                            'pant': {},    # Initialize empty map for pants (matching your DB key 'pant')
                            'week': {      # Initialize the weekly planner with empty slots
                                'monday': {'pant': '', 'shirt': ''},
                                'tuesday': {'pant': '', 'shirt': ''},
                                'wednesday': {'pant': '', 'shirt': ''},
                                'thursday': {'pant': '', 'shirt': ''},
                                'friday': {'pant': '', 'shirt': ''},
                                'saturday': {'pant': '', 'shirt': ''},
                                'sunday': {'pant': '', 'shirt': ''}
                            }
                        })
                        st.success("Signup successful! Please log in.")
                        st.session_state['show_signup_form'] = False
                        st.session_state['show_login_form'] = True
                        st.rerun()

# --- If logged in, show logout in sidebar ---
if st.session_state.get('authentication_status'):
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Logout", use_container_width=True):
        for key in ['authentication_status', 'username', 'show_login_form', 'show_signup_form']:
            st.session_state[key] = None
        st.rerun()
