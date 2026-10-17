# Streamlit Cloud Deployment Guide 🚀

This guide walks you through deploying the **Track A** Job Search AI Agent to **Streamlit Cloud** (`share.streamlit.io`) in less than 2 minutes.

---

## 📋 Prerequisites
1. A GitHub account.
2. The project pushed to your GitHub repository (e.g., `https://github.com/your-username/job-search-ai-agent`).
3. *(Optional)* A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) for LLM query parsing.

---

## ⚡ Step-by-Step Deployment

### Step 1: Sign in to Streamlit Community Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io).
2. Click **Sign in with GitHub**.

### Step 2: Create a New App
1. Click the **"New app"** button in your Streamlit dashboard.
2. Select your repository: `your-username/job-search-ai-agent`.
3. Set the Branch: `main`.
4. Set the Main file path: `streamlit_app.py`.
5. *(Optional)* Choose a custom App URL (e.g., `indian-job-search-agent.streamlit.app`).

### Step 3: Configure Environment Secrets (Optional)
If you wish to provide API keys securely:
1. Click **Advanced settings...** before clicking deploy (or go to App Settings > Secrets afterwards).
2. Enter your secrets in TOML format:
   ```toml
   GOOGLE_API_KEY = "your-gemini-api-key-here"
   ADZUNA_APP_ID = "optional-adzuna-id"
   ADZUNA_APP_KEY = "optional-adzuna-key"
   RAPIDAPI_KEY = "optional-rapidapi-key"
   ```
   > **Note:** If no API keys are provided, the app automatically runs in resilient demo mode using the rule-based parser and the rate-limited Indian job scraper catalog!

### Step 4: Click Deploy!
- Streamlit Cloud will read `requirements.txt` from the root directory, install all dependencies (`streamlit`, `requests`, `beautifulsoup4`, `langchain`, `pydantic`), and launch your application!
- The app will be accessible worldwide on your custom URL.

---

## 🔍 Verifying the Deployment
Once deployed, test the following:
1. **Chatbot Test:** Ask *"Remote Python jobs in Bengaluru above 8 LPA for a fresher"*. Verify that results appear with formatted LPA salary badges and apply links.
2. **Filter Test:** Switch to the **Filtered Job Explorer** tab, set City to *Pune*, min salary to *6 LPA*, and verify results render properly.
3. **Scraper Inspector:** Navigate to the **Scraper & Rate Limiter Inspector** tab and verify the polite rate limiter metrics are tracking active calls.
4. **Data Export:** Click **Export to CSV** or **Export to JSON** to ensure candidate download works seamlessly.
