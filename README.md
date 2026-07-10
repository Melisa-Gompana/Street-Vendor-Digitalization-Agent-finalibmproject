# Street Vendor Digitalization Agent

## 🏪 Powered by IBM Watsonx.ai · IBM Granite Models

A full-stack AI-powered web application that helps street vendors, hawkers, and micro-entrepreneurs across India digitalize their businesses — from UPI payments to government scheme access.

---

## 📋 Features

| Feature | Description |
|---|---|
| 🤖 **IBM Granite AI** | Conversational AI using IBM Watsonx.ai Granite models |
| 🔍 **RAG System** | Real-time retrieval from curated knowledge base |
| 📱 **UPI Guidance** | Step-by-step QR code payment setup |
| 🏛️ **Govt Schemes** | PM SVANidhi, Mudra, PMEGP, Udyam |
| 🗺️ **Google Business** | Local listing and maps optimization |
| 📈 **Local SEO** | Strategies to rank in nearby searches |
| 💬 **7 Languages** | English, Hindi, Telugu, Marathi, Tamil, Kannada, Bengali |
| 📊 **Dashboard** | Vendor profiles and onboarding progress |
| 🌙 **Dark Mode** | Full dark/light theme support |
| 📱 **Mobile First** | Responsive Bootstrap 5 design |

---

## 🚀 Quick Start

### 1. Clone / Download the Project

```bash
git clone <repo-url>
cd street-vendor-digitalization-agent
```

### 2. Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` with your IBM Cloud credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
IBM_PROJECT_ID=your_watsonx_project_id_here
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
FLASK_SECRET_KEY=change_this_to_a_random_secret_key
```

### 5. Run the Application

```bash
python app.py
```

Visit: **http://localhost:5000**

---

## 🔑 IBM Watsonx.ai Setup (Step-by-Step)

### Step 1: Create IBM Cloud Account
1. Go to [cloud.ibm.com](https://cloud.ibm.com)
2. Click "Create a free account"
3. Verify your email

### Step 2: Get IBM API Key
1. Go to **IBM Cloud → Manage → Access (IAM) → API Keys**
2. Click **"Create an IBM Cloud API key"**
3. Name it: `street-vendor-agent`
4. Copy and save the key to your `.env` file as `IBM_API_KEY`

### Step 3: Create Watsonx.ai Project
1. Go to [dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com)
2. Click **"New project"** → **"Create an empty project"**
3. Name it: `Street Vendor Agent`
4. Click the project → **"Manage"** tab → Copy the **Project ID**
5. Paste it in `.env` as `IBM_PROJECT_ID`

### Step 4: Enable Watsonx.ai (Lite Plan - FREE)
1. In IBM Cloud, search for **"Watson Machine Learning"**
2. Select Lite (Free) plan
3. Create the service
4. Associate it with your Watsonx project

---

## 📂 Project Structure

```
street-vendor-digitalization-agent/
├── app.py                    # Flask backend — main entry point
├── agent_config.py           # AGENT_INSTRUCTIONS, quick replies, languages
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
│
├── rag/
│   ├── __init__.py
│   └── rag_engine.py         # RAG system with ChromaDB + knowledge base
│
├── templates/
│   ├── index.html            # Main chat interface
│   └── dashboard.html        # Vendor dashboard
│
├── static/
│   ├── css/
│   │   └── style.css         # Dark mode + animations
│   └── js/
│       ├── app.js            # Chat, dark mode, profile logic
│       └── markdown.js       # Markdown → HTML renderer
│
├── data/
│   └── chroma_db/            # Vector database (auto-created)
│
└── vendor_profiles/          # JSON vendor profiles (auto-created)
```

---

## ⚙️ Customizing Agent Behavior

Edit [`agent_config.py`](agent_config.py) to customize:

```python
# Change response style, tone, language rules
AGENT_INSTRUCTIONS = """
You are the Street Vendor Digitalization Agent...
# Edit this to change how the AI responds
"""

# Add/remove quick reply buttons
QUICK_REPLIES = [
    {"label": "📱 Setup UPI", "message": "Help me setup UPI payments"},
    # Add more...
]

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": {"name": "English", ...},
    "hi": {"name": "हिंदी", ...},
    # Add more languages
}
```

---

## 🧠 RAG Knowledge Base

The knowledge base in [`rag/rag_engine.py`](rag/rag_engine.py) contains curated information about:

- PM SVANidhi scheme
- Udyam/MSME Registration
- UPI payment setup
- Google Business Profile
- WhatsApp Business
- PMEGP subsidies
- Digital onboarding checklist
- Pricing strategies
- Local SEO guide
- Mudra Loans

**To add new knowledge:**

```python
# In rag/rag_engine.py — append to KNOWLEDGE_BASE list
{
    "id": "your_unique_id",
    "category": "government_scheme",
    "source": "official-portal.gov.in",
    "title": "Your Scheme Name",
    "content": "Full details about the scheme...",
    "tags": ["tag1", "tag2"],
    "updated": "2024-01-01"
}
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main chat interface |
| `GET` | `/dashboard` | Vendor dashboard |
| `POST` | `/api/chat` | Send a message to AI |
| `GET/POST` | `/api/profile` | Get/update vendor profile |
| `POST` | `/api/clear-chat` | Clear conversation history |
| `GET` | `/api/quick-replies` | Get quick reply suggestions |
| `GET` | `/api/onboarding-steps` | Get onboarding checklist |
| `POST` | `/api/complete-step` | Mark onboarding step complete |
| `GET` | `/api/status` | Health check + system status |

### Chat API Example

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is PM SVANidhi scheme?", "language": "en"}'
```

Response:
```json
{
  "response": "PM SVANidhi is a micro-credit scheme...",
  "vendor_id": "uuid-here",
  "rag_used": true,
  "timestamp": "2024-01-01T10:00:00"
}
```

---

## 🚢 Deployment

### Option 1: IBM Code Engine (Recommended for IBM Cloud)

```bash
# Build and push to IBM Container Registry
ibmcloud cr login
docker build -t us.icr.io/<namespace>/vendor-agent:latest .
docker push us.icr.io/<namespace>/vendor-agent:latest

# Deploy to Code Engine
ibmcloud ce application create \
  --name vendor-agent \
  --image us.icr.io/<namespace>/vendor-agent:latest \
  --port 5000 \
  --env-from-secret vendor-agent-secrets
```

### Option 2: Gunicorn (Production)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 3: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t vendor-agent .
docker run -p 5000:5000 --env-file .env vendor-agent
```

### Option 4: Render / Railway / Fly.io

1. Push to GitHub
2. Connect the repo to Render/Railway
3. Set environment variables from `.env.example`
4. Deploy — the app starts automatically

---

## 🎛️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `IBM_API_KEY` | — | IBM Cloud API key (required for AI) |
| `IBM_PROJECT_ID` | — | Watsonx project ID (required for AI) |
| `IBM_WATSONX_URL` | `us-south.ml.cloud.ibm.com` | Watsonx region URL |
| `WATSONX_MODEL_ID` | `ibm/granite-3-8b-instruct` | IBM Granite model to use |
| `WATSONX_MAX_TOKENS` | `2048` | Max response length |
| `WATSONX_TEMPERATURE` | `0.7` | Creativity (0=factual, 1=creative) |
| `FLASK_SECRET_KEY` | — | Flask session encryption key |
| `FLASK_PORT` | `5000` | Port to run on |
| `ENABLE_RAG` | `true` | Enable/disable RAG retrieval |
| `RAG_TOP_K` | `5` | Number of RAG results to retrieve |
| `MAX_CONVERSATION_HISTORY` | `20` | Messages to keep in memory |

---

## 🤝 IBM Granite Model Options

| Model | Use Case |
|---|---|
| `ibm/granite-3-8b-instruct` | Best for chat, balanced performance |
| `ibm/granite-13b-chat-v2` | Deeper reasoning, larger context |
| `ibm/granite-20b-multilingual` | Best for Indian language support |
| `ibm/granite-3-2b-instruct` | Faster, lower resource usage |

Change `WATSONX_MODEL_ID` in `.env` to switch models.

---

## 🇮🇳 Supported Languages

| Code | Language | Script |
|---|---|---|
| `en` | English | Latin |
| `hi` | Hindi | देवनागरी |
| `te` | Telugu | తెలుగు |
| `mr` | Marathi | मराठी |
| `ta` | Tamil | தமிழ் |
| `kn` | Kannada | ಕನ್ನಡ |
| `bn` | Bengali | বাংলা |

The IBM Granite multilingual model handles all these languages natively.

---

## 🔒 Security Notes

- Never commit `.env` to version control (it's gitignored)
- Rotate `FLASK_SECRET_KEY` in production
- Use HTTPS in production deployments
- The app stores vendor profiles locally in JSON — use a proper database for production

---

## 📜 License

MIT License — Free to use, modify, and distribute.

---

*Built to empower India's 10 crore+ street vendors with AI technology 🇮🇳*
*Powered by IBM Watsonx.ai · IBM Granite Foundation Models*
