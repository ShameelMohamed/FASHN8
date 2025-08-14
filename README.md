## FashN8

AI-powered outfit curator, fit-check, and snap-to-shop assistant built with Streamlit. Manage your wardrobe, get smart color matches, virtually try on garments, and search shopping sites from a single app.

![WhatsApp Image 2025-08-14 at 21 31 09_182ef635](https://github.com/user-attachments/assets/20a49905-6549-4c57-84a0-713fa517c6be)


Deployed Version -- fashn8.streamlit.app

### Features

- **Authentication (Firestore)**
  - Simple username/password signup and login stored in Firestore.
  - Sidebar shows session and supports logout.

- **Dress++**
  - Upload a clothing image.
  - Removes background locally.
  - Detects apparel regions using Clarifai’s Apparel Detection model.
  - Extracts dominant color per region.
  - Uploads cropped items to Cloudinary.
  - Saves items to Firestore under `shirts` or `pants` with color hex → image URL.

- **Today’s Drip**
  - Loads your saved wardrobe from Firestore.
  - Visual carousel of items by category.
  - AI picks the best matching complementary item (color-based) using Gemini with a short reason.
  - Supports alternates to avoid repeats.

- **Fit Check**
  - Virtual try-on using a Gradio-hosted VTON workflow.
  - Choose garment type: Top, Full-body, Eyewear, Footwear.
  - Upload user photo and garment image to generate a composite.

- **Snap Shop**
  - Upload an inspiration image.
  - Isolates garment with background removal.
  - Detects dress/top/bottom region via Clarifai.
  - Generates a precise, keyword-friendly query with Gemini.
  - One-click search buttons for Amazon, Flipkart, and Myntra.

### Tech Stack

- **Frontend**: Streamlit
- **Storage/DB**: Firebase Firestore
- **Image Processing**: Pillow, rembg
- **ML APIs**: Clarifai (Apparel Detection), Google Gemini (Generative AI), Gradio (BLIP captioning, VTON)
- **Media Hosting**: Cloudinary


### Prerequisites

- Python 3.9+ recommended
- A Firebase project with Firestore enabled
- Accounts/keys for:
  - Cloudinary
  - Clarifai PAT
  - Google Generative AI (Gemini)
  - Hugging Face token (for BLIP captioning via Gradio)

### Local Setup (Windows PowerShell)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
streamlit run Home.py
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
streamlit run Home.py
```

### Configuration and Secrets

Move all secrets out of code and into Streamlit secrets. Create `.streamlit/secrets.toml`:

```toml
# Firebase
[FIREBASE]
service_account_json = """
{ ... your firebase service account JSON ... }
"""

# Cloudinary
[CLOUDINARY]
cloud_name = "..."
api_key = "..."
api_secret = "..."

# Clarifai
[CLARIFAI]
pat = "..."

# Google Generative AI (Gemini)
[GEMINI]
api_key = "..."

# Hugging Face
[HF]
token = "..."
```

Then, in your code, load from `st.secrets` (suggested refactor):

```python
import streamlit as st
from firebase_admin import credentials

cred_info = st.secrets["FIREBASE"]["service_account_json"]
cred = credentials.Certificate(json.loads(cred_info))

cloud_name = st.secrets["CLOUDINARY"]["cloud_name"]
api_key = st.secrets["CLOUDINARY"]["api_key"]
api_secret = st.secrets["CLOUDINARY"]["api_secret"]

clarifai_pat = st.secrets["CLARIFAI"]["pat"]
gemini_key = st.secrets["GEMINI"]["api_key"]
hf_token = st.secrets["HF"]["token"]
```

Notes:
- Current code reads `firebasee.json` from repo root and includes various keys inline. Replace these with `st.secrets` values.
- Do not commit `firebasee.json` or any secrets to Git.

### Firestore Data Model

- Collection: `users`
  - Document fields:
    - `username`: string
    - `password`: string (plaintext now; see Security)
    - `email`: string
    - `shirts`: map of `<hex color> -> <image URL>`
    - `pants`: map of `<hex color> -> <image URL>`

### Usage Guide

- **Login/Signup**
  - From `Home.py`, choose Login or Signup.
  - After login, sidebar shows your session and logout button.

- **Dress++**
  - Upload a clothing image (`jpg/png/webp`).
  - App removes background, detects apparel regions, extracts dominant color.
  - Click “Upload <Item>” to save the cropped item to Cloudinary and Firestore under `shirts` or `pants`.

- **Today’s Drip**
  - Loads your wardrobe by category.
  - Click “AI Match” to get the best complementary color item with a reason.
  - Click “Alternate” for another suggestion avoiding previously shown colors.

- **Fit Check**
  - Upload your photo and a garment image.
  - Choose garment type, click Generate.
  - Result image is shown if the Gradio service returns a link.

- **Snap Shop**
  - Upload any inspiration outfit image.
  - App isolates the garment, generates a clean search query.
  - Use Amazon, Flipkart, Myntra buttons to search.

### Theming

- Dark theme configured in `streamlit/config.toml`.

### Environment-specific Notes

- Clarifai SDK may require `HOME` env var on Windows. Code sets:
  - `os.environ["HOME"] = os.path.expanduser("~")`
- rembg is CPU-based by default. For performance, see rembg extras or ONNX/GPU options.

### Troubleshooting

- **Firebase credentials**: Ensure service account JSON is valid and accessible. Use `st.secrets` or a path your app can read.
- **Firestore permissions**: Set Firestore rules to allow your intended read/write from server side.
- **Cloudinary upload errors**: Verify `cloud_name`, `api_key`, `api_secret`.
- **Clarifai PAT or model**: Confirm PAT and that the Apparel Detection model endpoint is accessible.
- **Gemini API errors**: Check API key and quotas in Google AI Studio.
- **Gradio model limits**: Public demos can rate-limit or change. Replace with your own Space or endpoint if needed.
- **rembg failures**: Ensure `pip install rembg` succeeded. Consider `pip install onnxruntime` if needed.

### Security Considerations and Suggested Improvements

- Passwords are currently stored in plaintext in Firestore. Replace with a secure hash (e.g., `bcrypt`) or use Firebase Authentication.
- Move all secrets (Firebase JSON, Cloudinary keys, Clarifai PAT, Gemini key, HF token) to `st.secrets` and remove from code.
- Validate and sanitize user uploads.
- Consider rate limiting and monitoring for API usage.
- Consider per-user storage buckets/folders in Cloudinary.

### Deployment

- Streamlit Community Cloud or any VM can host.
- Provide secrets through the platform’s secrets manager (`.streamlit/secrets.toml` on Streamlit Cloud).
- Ensure outbound network access to:
  - Firebase Firestore
  - Cloudinary
  - Clarifai
  - Google Generative AI
  - Hugging Face/Gradio endpoints

### License

MIT

### Acknowledgements

- Clarifai Apparel Detection
- Google Generative AI (Gemini)
- rembg
- Gradio and BLIP image captioning
- Cloudinary
