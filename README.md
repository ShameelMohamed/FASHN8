## FashN8 v2 – AI Fashion Companion

FashN8 is an end-to-end **AI-powered fashion assistant** built on Streamlit. It combines wardrobe digitization, outfit recommendation, virtual try‑on, image-based shopping, and a conversational stylist into a single experience.

The app is organized as a multi‑page Streamlit project:

- **Home** – Authentication, onboarding, and global layout.
- **Dress++** – Upload garments, detect clothing items, remove background, auto‑caption, and save items to your digital wardrobe.
- **Today’s Drip** – AI‑curated shirt–pant combinations from your wardrobe with reasons and day‑wise outfit planning.
- **Virtual Try-On** – Upload your photo and a garment image to generate a realistic AI try‑on plus an automatic style‑compatibility score.
- **Snap Shop** – Upload an inspiration photo, extract the garment, generate a refined search query, open multi‑store searches, and find visually similar items in your wardrobe.
- **Ask Pookie** – Multilingual conversational stylist that chats over your wardrobe and suggests looks, with optional voice in/out.

---

## Features

- **User Accounts & Cloud Storage**
  - Email/password auth with **Firebase Firestore** as the main data store.
  - Per‑user wardrobe structure:
    - `shirts` – map of shirt items (`id -> { desc, hex, img }`).
    - `pant` – map of pant items (`id -> { desc, hex, img }`).
    - `week` – weekly planner (`monday..sunday` each storing `shirt` and `pant` ids).

- **Dress++ (Wardrobe Digitization)**
  - Upload clothing images.
  - Remove background using **rembg**.
  - Detect garment regions via **Clarifai Apparel Detection**.
  - For each detected region:
    - Crop the garment from the background‑removed image.
    - Compute dominant color hex.
    - Generate a natural language caption using a **Gradio image‑to‑prompt** model (`ovi054/image-to-prompt`).
    - Upload the crop to **Cloudinary** and store metadata in Firestore.

- **Today’s Drip (AI Outfit Matching)**
  - 3D‑style carousel to browse shirts and pants saved in Firestore.
  - Select an item (shirt or pant) and ask an AI stylist to find the **best matching counterpart** based on color and description.
  - Uses **Gemini 2.5 Flash** to pick a match and return a short justification.
  - One‑click **“Confirm Outfit”** writes the selected shirt/pant ids into the `week.<day>.shirt` and `week.<day>.pant` fields in Firestore for the current weekday.

- **Virtual Try-On**
  - Upload:
    - A **person** image (user photo).
    - A **garment/product** image.
  - Uses a HuggingFace‑hosted **Fashn‑VTON (Virtual Try-On)** Gradio API (`fashn-ai/fashn-vton-1.5`) to generate the try‑on result.
  - Automatically:
    - Extracts dominant colors from both images.
    - Computes a **compatibility rating** (1.0–5.0 stars) based on color theory.

- **Snap Shop**
  - Upload any inspiration/fashion photo.
  - Remove background and detect clothing regions with **Clarifai**.
  - Crop the key garment and send it to **Gradio image‑to‑prompt** for a raw caption.
  - Refine the caption to a compact, search‑friendly phrase with **Gemini 2.5 Flash**.
  - Produce one‑click search buttons for:
    - Amazon, Flipkart, Myntra, Ajio, Meesho.
  - Query your own wardrobe (shirts or pants) via Gemini JSON mode to find **color‑similar items** and display them in a responsive grid.

- **Ask Pookie (Personal Stylist Chat)**
  - Chat interface using **Streamlit chat UI**.
  - Uses **Gemini 2.5 Flash** with a rich system prompt and **hard‑coded wardrobe sample** to simulate a personalized stylist.
  - Supports multiple languages (English, Tamil, Malayalam, Telugu, Hindi) for both:
    - Input (via **Google Speech Recognition**).
    - Output (via **gTTS** voice response and on‑screen text).
  - Outputs outfit suggestions, explanations, and inline images via HTML `<img>` tags.

- **Color Compatibility Model (XGBoost)**
  - Separate **XGBoost regression model** trained on shirt/pant color pairs to predict a compatibility rating.
  - Model served via a **Gradio** `app.py`:
    - Inputs: two hex colors.
    - Output: rating 1.0–5.0 (clamped & rounded to nearest 0.5).

---

## Tech Stack

- **Frontend & Orchestration**: Streamlit (multi‑page app)
- **Cloud & Storage**:
  - Firebase Firestore (users, wardrobe, weekly planner)
  - Cloudinary (garment image hosting)
- **AI / ML Services**:
  - Clarifai Apparel Detection
  - Gemini 2.5 Flash (text, JSON mode)
  - Gradio‑hosted models:
    - `ovi054/image-to-prompt` (image captioning)
    - `fashn-ai/fashn-vton-1.5` (virtual try‑on)
  - XGBoost color compatibility model (local JSON model file)
- **Utilities & Libraries**:
  - `rembg`, `Pillow`, `numpy`, `colorsys`
  - `google-generativeai`, `firebase-admin`, `cloudinary`, `gradio_client`
  - `speech_recognition`, `gTTS`, `requests`, `streamlit.components.v1`

---

## Project Structure (Key Files)

- `Home.py` – Main entry page, authentication, and global layout.
- `pages/1_Dress++.py` – Wardrobe digitization, Clarifai, Cloudinary, Firestore writes.
- `pages/2_Today's Drip.py` – Carousel UI, Gemini outfit matching, Firestore weekly planner updates.
- `pages/3_Virtual TryOn.py` – Virtual try‑on with Fashn‑VTON, color compatibility rating.
- `pages/4_Snap Shop.py` – Garment extraction, search query generation, multi‑store links, wardrobe similarity.
- `pages/5_Ask Pookie.py` – Chat‑based stylist with multi‑language and voice support.
- `model/model-v1(XG)/app.py` – Gradio interface serving the XGBoost color‑matching model.
- `model/model-v1(XG)/fashion_model.json` – Serialized XGBoost model.
- `model/model-v1(XG)/train.py` & `model-v2(NN)/train.py` – Training scripts and datasets.
- `requirements.txt` – Python dependencies for the Streamlit app.
- `firebasee.json` – Firebase service account credentials (not for public repos).
- `streamlit/config.toml` – Streamlit configuration (if used).

---

## Setup & Installation

### 1. Prerequisites

- **Python** 3.9+ recommended.
- A **Firebase** project with Firestore and a service account key JSON.
- Accounts/API keys for:
  - **Clarifai**
  - **Google Gemini (Generative Language API)**
  - **Cloudinary**
  - **HuggingFace** (for the Fashn‑VTON Gradio client)

> ⚠️ **Security note:** In the current codebase, several keys are set directly in Python files. For production use, move all secrets into environment variables or a secrets manager and never commit them to version control.

### 2. Create & Activate Virtual Environment

```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS / Linux
```

### 3. Install Dependencies

From the project root (`FashN8`):

```bash
pip install -r requirements.txt
```

The model sub‑project under `model/model-v1(XG)` has its own `requirements.txt` if you want to retrain or serve the model separately.

### 4. Configure Firebase

1. Download your **service account JSON** from the Firebase console.
2. Save it as `firebasee.json` in the project root (or update the paths in:
   - `Home.py`
   - `pages/1_Dress++.py`
   - `pages/2_Today's Drip.py`
   - `pages/4_Snap Shop.py`
3. Ensure Firestore has a `users` collection; documents follow the structure used in `Home.py` (created automatically on signup).

### 5. Configure External Services

Depending on your deployment target, you can either:

- Keep the existing hard‑coded keys (for local experimentation only), or
- Preferably, set environment variables and adjust the code to read from them.

Key places where configuration is expected:

- **Cloudinary** – `cloudinary.config(...)` in `pages/1_Dress++.py`.
- **Clarifai** – `pat` and model URL in `pages/1_Dress++.py` and `pages/4_Snap Shop.py`.
- **Gemini** – API keys in:
  - `pages/2_Today's Drip.py`
  - `pages/4_Snap Shop.py`
  - `pages/5_Ask Pookie.py`
- **HuggingFace token** – `HF_TOKEN` environment variable in `pages/3_Virtual TryOn.py`.

---

## Running the Application

From the project root:

```bash
streamlit run Home.py
```

Streamlit will start the multi‑page app, and you can access it in your browser (typically at `http://localhost:8501`).

Use the Streamlit sidebar to navigate across:

- `Dress++`
- `Today's Drip`
- `Virtual TryOn`
- `Snap Shop`
- `Ask Pookie`

Authentication is handled on the `Home` page; pages will prompt you to log in if you are not authenticated.

---

## Running the Color Compatibility Model (Optional)

If you want to run the XGBoost color‑matching Gradio app separately:

1. Navigate to the model directory:

   ```bash
   cd model/model-v1(XG)
   pip install -r requirements.txt
   python app.py
   ```

2. Open the Gradio URL in your browser and interactively test shirt/pant color pairs.

You can also integrate the API endpoint exposed by this Gradio app back into the main Streamlit app if you prefer using the learned model instead of heuristic ratings.

---

## Notes & Future Improvements

- **Secret Management** – Externalize all API keys and secrets to environment variables.
- **Error Handling & Quotas** – Some flows (e.g., virtual try‑on) handle GPU quota limits gracefully, but you may want more robust monitoring and retry strategies.
- **Model Upgrades** – `model-v2(NN)` is present as an experimental path for a neural‑network‑based matcher; you can extend the app to use it.
- **Design & Branding** – The app already uses a modern dark background; you can add custom branding, fonts, and theming via Streamlit configuration and CSS.

FashN8 v2 brings together multiple AI components into a cohesive fashion experience—this README reflects the current architecture and is designed to be a base you can evolve as the project grows.

