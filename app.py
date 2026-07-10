# ============================================================
#  Street Vendor Digitalization Agent — Main Flask Application
#  IBM Watsonx.ai + IBM Granite + RAG + Multilingual Support
# ============================================================

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, send_from_directory
)
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────────────────────
#  Logging Configuration
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("VendorAgent")

# ─────────────────────────────────────────────────────────────
#  Import Agent Config & RAG Engine
# ─────────────────────────────────────────────────────────────
from agent_config import (
    AGENT_INSTRUCTIONS, QUICK_REPLIES, SUPPORTED_LANGUAGES,
    VENDOR_PROFILE_TEMPLATE, ONBOARDING_STEPS
)
from rag.rag_engine import get_rag_engine

# ─────────────────────────────────────────────────────────────
#  Flask App Initialization
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_change_in_production")
CORS(app)

# ─────────────────────────────────────────────────────────────
#  IBM Watsonx.ai Client Setup
# ─────────────────────────────────────────────────────────────
watsonx_client = None
model_id = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")


def initialize_watsonx():
    """Initialize IBM Watsonx.ai client with credentials from .env"""
    global watsonx_client
    api_key = os.getenv("IBM_API_KEY")
    project_id = os.getenv("IBM_PROJECT_ID")
    url = os.getenv("IBM_WATSONX_URL", "https://au-syd.dai.cloud.ibm.com")

    if not api_key or api_key == "your_ibm_cloud_api_key_here":
        logger.warning("IBM_API_KEY not configured — running in demo mode")
        return False

    if not project_id or project_id == "your_watsonx_project_id_here":
        logger.warning("IBM_PROJECT_ID not configured — running in demo mode")
        return False

    try:
        from ibm_watsonx_ai import APIClient, Credentials
        credentials = Credentials(url=url, api_key=api_key)
        watsonx_client = APIClient(credentials=credentials, project_id=project_id)
        logger.info(f"IBM Watsonx.ai initialized — Model: {model_id}")
        return True
    except ImportError:
        logger.warning("ibm-watsonx-ai package not installed — running in demo mode")
        return False
    except Exception as e:
        logger.error(f"Watsonx.ai initialization failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────
#  Vendor Profile Management
# ─────────────────────────────────────────────────────────────
PROFILES_DIR = os.getenv("VENDOR_PROFILES_DIR", "./vendor_profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)


def get_vendor_profile(vendor_id: str) -> Dict:
    """Load or create a vendor profile."""
    profile_path = os.path.join(PROFILES_DIR, f"{vendor_id}.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # New profile
    profile = dict(VENDOR_PROFILE_TEMPLATE)
    profile["vendor_id"] = vendor_id
    profile["created_at"] = datetime.now().isoformat()
    profile["last_active"] = datetime.now().isoformat()
    return profile


def save_vendor_profile(profile: Dict):
    """Persist vendor profile to disk."""
    vendor_id = profile.get("vendor_id", "unknown")
    profile["last_active"] = datetime.now().isoformat()
    profile_path = os.path.join(PROFILES_DIR, f"{vendor_id}.json")
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def extract_profile_info(message: str, profile: Dict) -> Dict:
    """Extract vendor information from conversation messages."""
    msg_lower = message.lower()

    # Extract business type hints
    food_keywords = ["food", "chai", "tea", "stall", "snacks", "samosa", "idli", "vada", "pav", "bhel", "juice", "fruits", "vegetables"]
    clothing_keywords = ["clothes", "garments", "fabric", "saree", "kurta", "fashion"]
    electronics_keywords = ["mobile", "phone", "repair", "electronics", "accessories"]

    if any(kw in msg_lower for kw in food_keywords) and not profile.get("business_type"):
        profile["business_type"] = "Food & Beverages"
    elif any(kw in msg_lower for kw in clothing_keywords) and not profile.get("business_type"):
        profile["business_type"] = "Clothing & Garments"
    elif any(kw in msg_lower for kw in electronics_keywords) and not profile.get("business_type"):
        profile["business_type"] = "Electronics & Repairs"

    return profile


# ─────────────────────────────────────────────────────────────
#  AI Response Generation
# ─────────────────────────────────────────────────────────────
def build_system_prompt(vendor_profile: Dict, rag_context: str) -> str:
    """Build the full system prompt with agent instructions + RAG context."""
    profile_summary = ""
    if vendor_profile.get("business_name"):
        profile_summary = f"\n## CURRENT VENDOR PROFILE\n- Business: {vendor_profile['business_name']}\n- Type: {vendor_profile.get('business_type', 'Unknown')}\n- Location: {vendor_profile.get('city', 'Unknown')}\n"

    return f"""{AGENT_INSTRUCTIONS}
{profile_summary}
{rag_context}

## CURRENT DATE & TIME
{datetime.now().strftime('%B %d, %Y at %I:%M %p IST')}
"""


def generate_response_watsonx(messages: List[Dict], system_prompt: str) -> str:
    """Generate AI response using IBM Watsonx.ai Granite model."""
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

        params = {
            GenParams.MAX_NEW_TOKENS: int(os.getenv("WATSONX_MAX_TOKENS", "2048")),
            GenParams.TEMPERATURE: float(os.getenv("WATSONX_TEMPERATURE", "0.7")),
            GenParams.TOP_P: float(os.getenv("WATSONX_TOP_P", "0.95")),
            GenParams.REPETITION_PENALTY: 1.1,
        }

        model = ModelInference(
            model_id=model_id,
            api_client=watsonx_client,
            params=params
        )

        # Format as chat messages
        formatted = [{"role": "system", "content": system_prompt}]
        formatted.extend(messages)

        response = model.chat(messages=formatted)
        return response["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"Watsonx generation error: {e}")
        return generate_demo_response(messages[-1]["content"] if messages else "")


def generate_demo_response(user_message: str) -> str:
    """
    Demo responses when Watsonx is not configured.
    Returns helpful, structured responses based on keyword matching.
    """
    msg = user_message.lower()

    if any(k in msg for k in ["upi", "payment", "qr", "pay"]):
        return """📱 **Setting Up UPI Payments for Your Shop**

Here's how to get started with **Google Pay (GPay) for Business**:

**Step 1 of 5** — Download the App
- Install **Google Pay** from Play Store (free)

**Step 2 of 5** — Set Up Business Account
- Open GPay → Tap "Business" tab → "Set up business account"

**Step 3 of 5** — Enter Business Details
- Business name, category, and your mobile number

**Step 4 of 5** — Link Bank Account
- Add your savings/current bank account via net banking or debit card

**Step 5 of 5** — Get Your QR Code ✅
- Download your QR code → Print at a photocopy shop for ₹5 → Display at stall!

💡 **Why UPI?**
- ✅ Zero charges for merchants
- ✅ Money transferred instantly to your bank
- ✅ Digital records help you get loans faster!

💡 **Next Step:** Print your QR code and put it where every customer can see it clearly!"""

    if any(k in msg for k in ["scheme", "government", "svanidhi", "loan", "subsidy", "benefit"]):
        return """🏛️ **Government Schemes for Street Vendors**

Here are the **top schemes you should know about**:

### 1. 💳 PM SVANidhi (Most Important!)
- **Loan:** ₹10,000 → ₹20,000 → ₹50,000 (three stages)
- **Interest Subsidy:** 7% back on timely repayment
- **Apply:** pmsvanidhi.mohua.gov.in | Helpline: 1800-11-1979

### 2. 🏪 Udyam Registration (FREE MSME Certificate)
- Unlocks subsidies, priority loans, and government scheme benefits
- **Apply:** udyamregistration.gov.in (takes 10 minutes!)

### 3. 💰 PM MUDRA Loan
- **Shishu:** Up to ₹50,000 | **Kishore:** Up to ₹5 lakh
- Visit nearest bank or apply at mudra.org.in

### 4. 🎯 PMEGP (PM Employment Generation Programme)
- 15–35% subsidy on new business setup costs
- Apply at kviconline.gov.in

💡 **Next Step:** Start with **PM SVANidhi** — it's specifically designed for street vendors like you!"""

    if any(k in msg for k in ["google", "maps", "listing", "online", "profile"]):
        return """🗺️ **Add Your Shop to Google Maps & Google Business Profile**

This is **completely FREE** and brings customers directly to you!

**Step 1:** Go to **business.google.com** on your phone
**Step 2:** Sign in with your Gmail account
**Step 3:** Click "Add your business"
**Step 4:** Enter your shop name and category
**Step 5:** Add your location on the map
**Step 6:** Add phone number and business hours
**Step 7:** Verify via phone call or SMS
**Step 8:** Add 5+ photos of your stall and products ✅

**After Setup — Weekly Tasks:**
- 📸 Upload 1-2 new photos weekly
- ⭐ Ask happy customers for reviews
- 📢 Post special offers and new items
- 💬 Reply to all reviews (even negative ones politely)

**Why this matters:** When someone searches "tea stall near me" or "best chai [your area]" — **your shop shows up!**

💡 **Next Step:** Create your Google Business Profile today — it takes just 15 minutes!"""

    if any(k in msg for k in ["profile", "business profile", "about my business", "describe"]):
        return """📋 **Creating Your Professional Business Profile**

To generate your perfect business profile, I need a few details:

1. **What's your business name?** (or I can suggest one!)
2. **What do you sell?** (food, clothes, vegetables, mobile repair, etc.)
3. **Where is your shop?** (city/neighborhood)
4. **How long have you been running this business?**
5. **Who are your typical customers?** (families, office workers, students, etc.)

**Sample Profile I can generate:**

---
🏪 **[Business Name]**
📍 [Location] | 📞 [Phone]

*"[Catchy one-line description]"*

**About Us:** [Professional 3-4 line description]
**Specialties:** [Top products/services]
**Serving:** [Target customers]
**Hours:** [Business hours]
**Payments Accepted:** Cash | UPI | All apps
---

Share your details and I'll create your personalized profile! 😊

💡 **Next Step:** Tell me your business name and what you sell!"""

    if any(k in msg for k in ["marketing", "promote", "advertise", "customer", "social media"]):
        return """📣 **Digital Marketing Ideas for Your Business**

Here are **free and low-cost ways** to get more customers:

### 📱 WhatsApp Marketing (FREE)
- Set up WhatsApp Business with product catalog
- Send weekly broadcast: "🌟 Today's Special — [Product] ₹[Price]"
- Share your location and operating hours daily

### 📸 Instagram (FREE)
- Post photos of your products daily
- Use hashtags: #[YourCity]Food #StreetFood #LocalBusiness
- Tag your exact location in every post

### 🌟 Google Reviews Strategy
- Ask every happy customer: "Please leave us a Google review!"
- Create a QR code linking to your review page (free at qr-code-generator.com)
- Respond to every review professionally

### 🎉 Festival Campaigns
- **Diwali:** "Festival Special — Buy 2 Get 1 Free 🪔"
- **Holi:** "Holi Offer — ₹50 off on orders above ₹200 🎨"
- **Eid:** "Eid Mubarak — Special Thali ₹[Price] 🌙"

### 💬 Customer Loyalty
- Create a simple stamp card (10 purchases = 1 free)
- WhatsApp "VIP Customer" group with exclusive offers

💡 **Next Step:** Download WhatsApp Business and set up your product catalog today!"""

    if any(k in msg for k in ["price", "pricing", "rate", "charge", "cost"]):
        return """📈 **Pricing Strategy for Your Business**

Here's a simple framework to price your products:

### 💰 Basic Formula
**Selling Price = Cost × 1.5 to 2.5** (50-150% markup depending on product)

### 📊 Profit Margin Guide
| Product Type | Typical Margin |
|---|---|
| Street food | 40-60% |
| Chai/Coffee | 60-80% |
| Vegetables | 15-25% |
| Clothing | 50-150% |

### 🧠 Smart Pricing Tips
1. **Psychological Pricing:** Use ₹49, ₹99, ₹149 instead of ₹50, ₹100, ₹150
2. **Bundle Deals:** "3 pieces for ₹100" sells better than "₹35 each"
3. **Premium Option:** Keep a slightly expensive version to make normal price look attractive
4. **UPI Discount:** Offer ₹5-10 discount for UPI payment — builds digital records!

### 🎯 Competitive Research
- Check 3-5 competitors every week
- Don't just compete on price — hygiene, taste, speed matter more!

Tell me your **specific products and current prices** and I'll give you a detailed analysis!

💡 **Next Step:** List your top 5 products with current prices and let me optimize them!"""

    # Default response
    return """👋 **Namaste! I'm Digi Saathi — Your Street Vendor Digitalization Agent!**

I'm here to help you **grow your business digitally** and access government benefits. Here's what I can help you with:

🏪 **Business Setup**
- Create professional business profiles
- Google Business listing & Google Maps
- WhatsApp Business catalog

💳 **Digital Payments**
- UPI QR code setup (Google Pay, PhonePe, Paytm)
- Step-by-step payment guides

🏛️ **Government Schemes**
- PM SVANidhi loan (₹10,000 to ₹50,000)
- Udyam/MSME registration (FREE)
- Mudra loans and PMEGP subsidies

📈 **Business Growth**
- Pricing strategies
- Digital marketing & promotions
- Local SEO to attract nearby customers

---

**How can I help you today?** You can ask me in **English, Hindi (हिंदी), Telugu, Marathi, or Tamil** too!

💡 **Next Step:** Tell me about your business and let's get started!"""


# ─────────────────────────────────────────────────────────────
#  Flask Routes
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Main landing page."""
    if "vendor_id" not in session:
        session["vendor_id"] = str(uuid.uuid4())
        session["conversation"] = []
    return render_template("index.html",
                           quick_replies=QUICK_REPLIES,
                           languages=SUPPORTED_LANGUAGES,
                           onboarding_steps=ONBOARDING_STEPS,
                           app_name=os.getenv("APP_NAME", "Street Vendor Digitalization Agent"))


@app.route("/dashboard")
def dashboard():
    """Vendor dashboard page."""
    vendor_id = session.get("vendor_id", str(uuid.uuid4()))
    session["vendor_id"] = vendor_id
    profile = get_vendor_profile(vendor_id)
    return render_template("dashboard.html",
                           profile=profile,
                           onboarding_steps=ONBOARDING_STEPS,
                           languages=SUPPORTED_LANGUAGES)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Main chat API endpoint."""
    data = request.get_json()
    user_message = data.get("message", "").strip()
    language = data.get("language", "en")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Session management
    vendor_id = session.get("vendor_id", str(uuid.uuid4()))
    session["vendor_id"] = vendor_id
    if "conversation" not in session:
        session["conversation"] = []

    # Load vendor profile
    profile = get_vendor_profile(vendor_id)
    profile = extract_profile_info(user_message, profile)

    # RAG retrieval
    rag_context = ""
    if os.getenv("ENABLE_RAG", "true").lower() == "true":
        try:
            rag_engine = get_rag_engine()
            docs = rag_engine.retrieve(user_message, top_k=int(os.getenv("RAG_TOP_K", "3")))
            rag_context = rag_engine.format_context(docs)
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # Build conversation history (limited to last N messages)
    max_history = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
    conversation = session["conversation"][-max_history:]

    # Add current message
    conversation.append({"role": "user", "content": user_message})

    # Build system prompt
    system_prompt = build_system_prompt(profile, rag_context)

    # Generate response
    if watsonx_client is not None:
        response_text = generate_response_watsonx(conversation, system_prompt)
    else:
        response_text = generate_demo_response(user_message)

    # Add assistant response to history
    conversation.append({"role": "assistant", "content": response_text})
    session["conversation"] = conversation
    session.modified = True

    # Update and save vendor profile
    profile["conversation_count"] = profile.get("conversation_count", 0) + 1
    save_vendor_profile(profile)

    return jsonify({
        "response": response_text,
        "vendor_id": vendor_id,
        "profile": {
            "business_name": profile.get("business_name", ""),
            "business_type": profile.get("business_type", ""),
            "onboarding_stage": profile.get("onboarding_stage", "new"),
            "completed_steps": profile.get("completed_steps", [])
        },
        "rag_used": bool(rag_context),
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/profile", methods=["GET", "POST"])
def vendor_profile():
    """Get or update vendor profile."""
    vendor_id = session.get("vendor_id")
    if not vendor_id:
        return jsonify({"error": "No session"}), 401

    if request.method == "GET":
        profile = get_vendor_profile(vendor_id)
        return jsonify(profile)

    if request.method == "POST":
        data = request.get_json()
        profile = get_vendor_profile(vendor_id)
        # Update allowed fields
        allowed_fields = ["name", "business_name", "business_type", "location",
                          "city", "state", "products", "upi_id", "phone",
                          "language_preference", "completed_steps", "onboarding_stage"]
        for field in allowed_fields:
            if field in data:
                profile[field] = data[field]
        save_vendor_profile(profile)
        return jsonify({"success": True, "profile": profile})


@app.route("/api/clear-chat", methods=["POST"])
def clear_chat():
    """Clear conversation history."""
    session["conversation"] = []
    session.modified = True
    return jsonify({"success": True})


@app.route("/api/quick-replies", methods=["GET"])
def get_quick_replies():
    """Return quick reply suggestions."""
    return jsonify(QUICK_REPLIES)


@app.route("/api/onboarding-steps", methods=["GET"])
def get_onboarding_steps():
    """Return onboarding steps with completion status."""
    vendor_id = session.get("vendor_id")
    completed = []
    if vendor_id:
        profile = get_vendor_profile(vendor_id)
        completed = profile.get("completed_steps", [])

    steps = []
    for step in ONBOARDING_STEPS:
        steps.append({
            **step,
            "completed": step["id"] in completed
        })
    return jsonify(steps)


@app.route("/api/complete-step", methods=["POST"])
def complete_step():
    """Mark an onboarding step as complete."""
    vendor_id = session.get("vendor_id")
    if not vendor_id:
        return jsonify({"error": "No session"}), 401

    data = request.get_json()
    step_id = data.get("step_id")

    profile = get_vendor_profile(vendor_id)
    completed = profile.get("completed_steps", [])
    if step_id and step_id not in completed:
        completed.append(step_id)
        profile["completed_steps"] = completed

    # Update onboarding stage
    n = len(completed)
    if n == 0:
        profile["onboarding_stage"] = "new"
    elif n <= 2:
        profile["onboarding_stage"] = "basic"
    elif n <= 5:
        profile["onboarding_stage"] = "intermediate"
    else:
        profile["onboarding_stage"] = "advanced"

    save_vendor_profile(profile)
    return jsonify({"success": True, "completed_steps": completed, "stage": profile["onboarding_stage"]})


@app.route("/api/status", methods=["GET"])
def status():
    """Health check and system status endpoint."""
    return jsonify({
        "status": "running",
        "app": os.getenv("APP_NAME", "Street Vendor Digitalization Agent"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "model": model_id,
        "watsonx_connected": watsonx_client is not None,
        "rag_enabled": os.getenv("ENABLE_RAG", "true").lower() == "true",
        "timestamp": datetime.now().isoformat()
    })


# ─────────────────────────────────────────────────────────────
#  Application Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    watsonx_ready = initialize_watsonx()
    mode = "IBM Watsonx.ai (Granite)" if watsonx_ready else "Demo Mode (no API key)"
    logger.info(f"Starting Street Vendor Digitalization Agent — {mode}")
    logger.info(f"Visit: http://localhost:{os.getenv('FLASK_PORT', 5000)}")
    app.run(
        debug=os.getenv("FLASK_DEBUG", "True").lower() == "true",
        port=int(os.getenv("FLASK_PORT", 5000)),
        host="0.0.0.0"
    )
