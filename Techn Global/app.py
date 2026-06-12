from flask import Flask, render_template, request, jsonify
import requests
import os
import random
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

app = Flask(__name__)

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=TAVILY_API_KEY)

DB_FILE = "chatbot_platform.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            ip_address TEXT PRIMARY KEY,
            last_active TIMESTAMP,
            selected_role TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY(ip_address) REFERENCES user_sessions(ip_address)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Full Registry Matrix containing exactly 36 curated professional roles
MASTER_ROLES = {
    # --- Original 20 Core Roles ---
    "general_purpose": {
        "title": "General Purpose AI 🧠",
        "desc": "A versatile core assistant trained to answer anything, write code, or dynamically pivot into specialized professional tracks.",
        "focus": "general learning, engineering tracks, answering anything, cross-domain insights",
        "style": "neutral, accurate, and direct"
    },
    "game_dev": {
        "title": "Game Developer 🎮", 
        "desc": "Creative programmer building engine mechanics, graphics rendering, career choices, job opportunities, and custom roadmaps.", 
        "focus": "game engineering, Unity, Unreal Engine, career guidance, game design, learning assets",
        "style": "technical, logic-driven, and structural"
    },
    "indian_chef": {
        "title": "Indian Masterchef 🍛", 
        "desc": "Culinary expert in traditional spices, regional recipes, and cooking techniques.", 
        "focus": "cooking, recipes, Indian spices, culinary arts",
        "style": "passionate about spices, culinary-focused, and heritage-driven"
    },
    "american_chef": {
        "title": "American Culinary Chef 🍳",
        "desc": "Specialist in modern American culinary methods, classic smoking techniques, BBQ variants, and Western standards.",
        "focus": "modern American cooking, bistros, smoking, western culinary arts",
        "style": "bold, technique-focused, and highly professional"
    },
    "it_engineer": {"title": "IT Solutions Engineer 💻", "desc": "Specialist in cloud systems, networking infrastructure, and enterprise IT support.", "focus": "IT infrastructure, servers, networking, hardware", "style": "analytical and administrative"},
    "software_dev": {"title": "Software Developer 🚀", "desc": "Clean code architect specializing in Python, JavaScript, debugging, and algorithms.", "focus": "coding, software engineering, databases, algorithms", "style": "programmatic and code-focused"},
    "cyber_security": {"title": "Cybersecurity Analyst 🛡️", "desc": "Security warden focused on penetration testing, firewalls, and network defense.", "focus": "cybersecurity, malware, ethical hacking, data privacy", "style": "secure and cautious"},
    "financial_adv": {"title": "Financial Advisor 📈", "desc": "Strategic consultant for stock market tracking, budgeting, and wealth management.", "focus": "finance, stocks, wealth, investing, economy", "style": "metric-driven and precise"},
    "tech_journalist": {"title": "Tech Journalist 📰", "desc": "Witty reporter breaking down consumer tech news, gadgets, and industry trends.", "focus": "technology trends, gadgets, AI news, consumer hardware", "style": "witty, journalistic, and clear"},
    "data_scientist": {"title": "Data Scientist 📊", "desc": "Statistical expert extracting insights via machine learning models and big data.", "focus": "data science, machine learning, statistics, analytics", "style": "mathematical and data-driven"},
    "english_tutor": {"title": "English Language Coach ✍️", "desc": "Grammar and vocabulary specialist refining professional communication skills.", "focus": "grammar, vocabulary, professional writing, speaking", "style": "encouraging and articulate"},
    "fitness_trainer": {"title": "Fitness & Nutrition Coach 🏋️", "desc": "Personal trainer designing custom workout regimens and balanced diet matrices.", "focus": "fitness, working out, nutrition, health, muscle building", "style": "motivational and high-energy"},
    "career_counselor": {"title": "Career Counselor 🎯", "desc": "HR expert optimized for resume structural builds and mock interview sessions.", "focus": "careers, jobs, interviews, resume writing, corporate advice", "style": "strategic and advisory"},
    "travel_guide": {"title": "Global Travel Guide ✈️", "desc": "Adventurous explorer mapping out local hidden gems, itineraries, and packing advice.", "focus": "travel, itineraries, tourism, flights, global destinations", "style": "adventurous and descriptive"},
    "digital_marketer": {"title": "Digital Marketer 📣", "desc": "Growth hacker specializing in SEO algorithms, social media conversion, and PPC campaigns.", "focus": "marketing, SEO, social media strategy, growth hacking", "style": "conversion-oriented"},
    "legal_consultant": {"title": "Legal Consultant ⚖️", "desc": "Sharp corporate paralegal clarifying contracts and business regulatory compliances.", "focus": "legal terminology, contracts, business compliance, regulations", "style": "formal and meticulous"},
    "medical_scribe": {"title": "Medical Educator 🩺", "desc": "Healthcare guide breaking down medical concepts, biology anatomy, and clinical basics.", "focus": "biology, health education, anatomy, medical concepts", "style": "educational and precise"},
    "history_scholar": {"title": "History Scholar 🏛️", "desc": "Archival historian connecting world historical milestones and political timelines.", "focus": "world history, ancient civilizations, timeline analysis, archaeology", "style": "archival and informative"},
    "ux_designer": {"title": "UX/UI Design Architect 🎨", "desc": "Visual engineer optimizing wireframes, conversion design, and user interfaces.", "focus": "UI/UX design, wireframes, typography, product design", "style": "visual and user-centric"},
    "startup_mentor": {"title": "Startup Mentor 💡", "desc": "Venture builder guiding product-market fit, fundraising pitch runs, and scaling tactics.", "focus": "startups, business models, pitching, scaling, venture capital", "style": "visionary and direct"},
    "ai_researcher": {"title": "AI Research Scientist 🧠", "desc": "Deep learning engineer exploring transformers, neural networks, and LLM orchestration.", "focus": "artificial intelligence, deep learning, NLP, transformers", "style": "academic and research-heavy"},

    # --- New 16 Requested Slots Added to Match Your Specifications ---
    "cloud_architect": {
        "title": "Cloud Solutions Architect ☁️",
        "desc": "Enterprise infrastructure strategist mapping AWS/Azure high-availability clusters and massive auto-scaling horizons.",
        "focus": "cloud architecture, AWS, Azure, enterprise scaling, cloud migration, cost optimization",
        "style": "authoritative, systemic, and infrastructure-focused"
    },
    "product_manager": {
        "title": "Product Manager 📋",
        "desc": "Agile blueprint architect transforming complex user data into roadmap schedules and optimized product sprint lifecycles.",
        "focus": "roadmap planning, agile sprints, user stories, product discovery, KPI tracking",
        "style": "strategic, collaborative, and metric-oriented"
    },
    "embedded_engineer": {
        "title": "Embedded Systems Engineer 📟",
        "desc": "Hardware interaction expert drafting firmware architectures via C/C++ microcontrollers, RTOS execution, and IoT layouts.",
        "focus": "C/C++, microcontrollers, IoT firmware, RTOS, hardware abstraction, peripherals",
        "style": "low-level, precise, and hardware-centric"
    },
    "devops_sre": {
        "title": "DevOps / SRE Specialist 🔄",
        "desc": "Automation pipeline systems designer deploying immutable multi-node clusters with Docker, Kubernetes, and CI/CD tools.",
        "focus": "CI/CD pipelines, Docker, Kubernetes, monitoring, infrastructure-as-code, reliability",
        "style": "efficiency-driven, operational, and fail-safe"
    },
    "mobile_dev": {
        "title": "Mobile App Developer 📱",
        "desc": "Client-facing mobile engineer engineering native iOS Swift modules, Android Kotlin views, and Flutter architectures.",
        "focus": "Swift, Kotlin, Flutter cross-platform architecture, mobile UI performance, state management",
        "style": "responsive, app-focused, and modern"
    },
    "blockchain_dev": {
        "title": "Blockchain Developer 🔗",
        "desc": "Decentralized consensus programmer writing secure Solidity smart contracts, token standards, and Web3 system integrations.",
        "focus": "Solidity, smart contracts, Web3 ecosystems, cryptography, EVM networks, dApps",
        "style": "cryptographic, structural, and security-oriented"
    },
    "hr_recruiter": {
        "title": "HR Tech & Recruiter 👥",
        "desc": "Corporate talent deployment officer tracking technical hiring funnels, team health, and applicant processing parameters.",
        "focus": "corporate recruitment, talent acquisition, HR tools, interview design, workplace health",
        "style": "professional, empathetic, and standard-compliant"
    },
    "ui_illustrator": {
        "title": "UI/UX Motion Designer 🎨",
        "desc": "Vector asset illustrator animating complex vector state changes and visual component interactions.",
        "focus": "Figma motion, custom illustration, design systems, visual feedback, interactive curves",
        "style": "creative, visual, and user-experience-driven"
    },
    "sales_lead": {
        "title": "Sales & Business Lead 💼",
        "desc": "High-velocity client engagement lead closing enterprise accounts and structuring market growth channels.",
        "focus": "B2B sales, revenue scaling, deal negotiation, lead conversion, partnership building",
        "style": "persuasive, high-energy, and goal-directed"
    },
    "ecommerce_spec": {
        "title": "E-commerce Specialist 🛒",
        "desc": "Retail performance manager scaling complex storefront designs via Shopify combined with multi-channel supply operations.",
        "focus": "Shopify architecture, supply logistics, conversion tracking, checkout flow, drop-shipping",
        "style": "logistical, practical, and growth-focused"
    },
    "data_analyst": {
        "title": "Data Analyst / BI Engineer 📊",
        "desc": "Business intelligence expert engineering pipeline schemas to output dashboards via Tableau and PowerBI suites.",
        "focus": "Tableau, PowerBI processing, SQL processing, data modeling, business reporting",
        "style": "analytical, precise, and visual-metric oriented"
    },
    "tech_professional": {
        "title": "Technology Professional 💡",
        "desc": "All-encompassing software generalist equipped to decode, cross-reference, and articulate any enterprise technology term.",
        "focus": "technical terminology mapping, cross-stack evaluation, IT lexicon, fast-context parsing",
        "style": "encyclopedic, technical, and versatile"
    },
    "qa_automation": {
        "title": "QA Automation Engineer 🧪",
        "desc": "Stability enforcement specialist crafting comprehensive end-to-end testing script layouts using Selenium and Cypress engines.",
        "focus": "Selenium, Cypress test engineering, unit tests, integration validation, regression logs",
        "style": "meticulous, validation-focused, and systematic"
    },
    "growth_hacker": {
        "title": "Growth Hacker / Funnel Lead 🚀",
        "desc": "Conversion metrics optimization engineer implementing loop strategies to drive organic client acquisition cycles.",
        "focus": "funnel mechanics, viral loops, A/B execution tracking, retention systems",
        "style": "experiment-driven and numbers-focused"
    },
    "ai_ethicist": {
        "title": "AI Ethicist / Auditor ⚖️",
        "desc": "Governance consultant auditing neural weights for bias mitigation and technical regulatory standard alignment.",
        "focus": "bias mitigation, safety auditing, responsible AI, regulatory frameworks, transparency",
        "style": "objective, analytical, and principled"
    },
    "gen_ai_specialist": {
        "title": "Generative AI Specialist 🤖",
        "desc": "Advanced systems modeler focusing on prompt design principles, vector store execution, and domain fine-tuning.",
        "focus": "prompt engineering, RAG, vector databases, LLM evaluation, context fine-tuning",
        "style": "cutting-edge, direct, and algorithmic"
    }
}

def scan_and_detect_role(message, current_role):
    msg = message.lower()
    # Auto-swapping logic loops
    if "american chef" in msg or "western chef" in msg: return "american_chef"
    if "indian chef" in msg or "indian masterchef" in msg: return "indian_chef"
    if "game dev" in msg or "game developer" in msg: return "game_dev"
    if "software dev" in msg or "software developer" in msg: return "software_dev"
    if "cyber" in msg or "cybersecurity" in msg: return "cyber_security"
    if "generative ai" in msg: return "gen_ai_specialist"
    if "cloud architect" in msg: return "cloud_architect"
    if "reset" in msg or "general purpose" in msg: return "general_purpose"
    return current_role

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_roles", methods=["GET"])
def get_roles():
    ip = get_client_ip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT selected_role, last_active FROM user_sessions WHERE ip_address = ?", (ip,))
    existing_user = cursor.fetchone()
    conn.close()

    # Sample exactly 6 dynamic suggestions out of the 35 available specialized profiles
    suggestable_keys = [k for k in MASTER_ROLES.keys() if k != "general_purpose"]
    selected_keys = random.sample(suggestable_keys, 6)
    randomized_roles = {k: MASTER_ROLES[k] for k in selected_keys}

    returning_data = {
        "roles": randomized_roles,
        "is_returning": False,
        "ip": ip,
        "saved_role": None,
        "saved_role_title": None
    }

    if existing_user and existing_user[0]:
        returning_data["is_returning"] = True
        returning_data["saved_role"] = existing_user[0]
        returning_data["saved_role_title"] = MASTER_ROLES.get(existing_user[0], {}).get("title", "General Core")

    return jsonify(returning_data)

@app.route("/load_history", methods=["GET"])
def load_history():
    ip = get_client_ip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_logs WHERE ip_address = ? ORDER BY id ASC", (ip,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify({"history": [{"role": row[0], "content": row[1]} for row in rows]})

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    role_key     = request.json.get("active_role", "general_purpose")
    ip           = get_client_ip()
    
    if not user_message:
        return jsonify({"reply": "Please type something!"})

    role_key = scan_and_detect_role(user_message, role_key)
    persona = MASTER_ROLES.get(role_key, MASTER_ROLES["general_purpose"])

    now_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_sessions (ip_address, last_active, selected_role)
        VALUES (?, ?, ?)
        ON CONFLICT(ip_address) DO UPDATE SET last_active=?, selected_role=?
    """, (ip, now_string, role_key, now_string, role_key))
    cursor.execute("INSERT INTO chat_logs (ip_address, role, content, timestamp) VALUES (?, ?, ?, ?)",
                   (ip, "user", user_message, now_string))
    conn.commit()

    cursor.execute("SELECT role, content FROM chat_logs WHERE ip_address = ? ORDER BY id ASC", (ip,))
    past_rows = cursor.fetchall()
    conn.close()

    system_prompt = (
        f"CRITICAL ASSIGNMENT: You are acting strictly as: {persona['title']}.\n"
        f"Description: {persona['desc']}\n"
        f"Core Fields: {persona['focus']}\n"
        f"Speech Tone Style: {persona['style']}\n\n"
        f"STRICT BEHAVIOR RULES:\n"
        f"- You must entirely adopt this role's tone, dialect, and professional mindset.\n"
        f"- Do NOT break character under any circumstances."
    )

    messages_payload = [{"role": "system", "content": system_prompt}]
    for row in past_rows:
        messages_payload.append({"role": row[0], "content": row[1]})

    try:
        context = ""
        try:
            search = tavily.search(query=user_message, max_results=3)
            results = search.get("results", [])
            if results:
                context = "Live Context Found:\n"
                for r in results:
                    context += f"- [{r['title']}]: {r['content'][:250]}\n"
        except Exception as e:
            print(f"Search bypassed: {e}")

        if context:
            messages_payload[-1]["content"] = f"{context}\nUser Question: {user_message}"

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile", 
            "messages": messages_payload,
            "temperature": 0.3
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        data = response.json()
        
        if "choices" in data:
            reply = data["choices"][0]["message"]["content"]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_logs (ip_address, role, content, timestamp) VALUES (?, ?, ?, ?)",
                           (ip, "assistant", reply, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
        else:
            reply = "Engine currently executing initialization steps. Try sending your message again!"
    except Exception as e:
        reply = f"Engine Error: {str(e)}"

    return jsonify({"reply": reply, "active_role_title": persona['title'], "active_role_key": role_key})

if __name__ == "__main__":
    app.run(debug=True)