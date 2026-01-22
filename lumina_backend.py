"""
Lumina-LLM RAG Agent Backend
AI-powered assistant for vendor database CRUD operations
Uses Groq API with LangChain and LangGraph for intelligent responses
Integrates with Supabase for real-time database operations
"""

import os
import json
import re
from datetime import datetime
from typing import TypedDict, List, Union, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from werkzeug.utils import secure_filename
from supabase import create_client, Client

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "global_code_duplicate1"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Groq API Key is loaded from .env

app = Flask(__name__)
CORS(app)

# ============================================
# SUPABASE DATABASE OPERATIONS
# ============================================

def search_vendors(query: str = None, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Search vendors with flexible filtering - searches ALL columns if query provided"""
    try:
        # If a general query is provided, search across ALL columns
        if query:
            # Get all data and filter in Python (more flexible)
            response = supabase.table(TABLE_NAME).select("*").execute()
            all_data = response.data
            
            # Search across all columns
            query_lower = query.lower()
            filtered_data = []
            
            for row in all_data:
                # Check if query matches ANY column value
                match_found = False
                for key, value in row.items():
                    if value and query_lower in str(value).lower():
                        match_found = True
                        break
                
                if match_found:
                    filtered_data.append(row)
            
            return {
                "success": True,
                "data": filtered_data,
                "count": len(filtered_data),
                "searched_all_columns": True
            }
        
        # If specific filters provided, use targeted search
        elif filters:
            db_query = supabase.table(TABLE_NAME).select("*")
            
            for key, value in filters.items():
                if value:
                    # Case-insensitive search using ilike
                    db_query = db_query.ilike(key, f"%{value}%")
            
            response = db_query.execute()
            
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data),
                "searched_all_columns": False
            }
        
        # No query or filters, return all (limited)
        else:
            response = supabase.table(TABLE_NAME).select("*").limit(100).execute()
            
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data),
                "searched_all_columns": False
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0
        }


def create_vendor(vendor_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new vendor in the database"""
    try:
        response = supabase.table(TABLE_NAME).insert(vendor_data).execute()
        
        return {
            "success": True,
            "data": response.data,
            "message": "Vendor created successfully!"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create vendor"
        }


def update_vendor(vendor_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing vendor"""
    try:
        response = supabase.table(TABLE_NAME).update(updates).eq("id", vendor_id).execute()
        
        return {
            "success": True,
            "data": response.data,
            "message": "Vendor updated successfully!"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to update vendor"
        }


def delete_vendor(vendor_id: int) -> Dict[str, Any]:
    """Delete a vendor from the database"""
    try:
        response = supabase.table(TABLE_NAME).delete().eq("id", vendor_id).execute()
        
        return {
            "success": True,
            "data": response.data,
            "message": "Vendor deleted successfully!"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to delete vendor"
        }


def get_all_vendors(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get all vendors with pagination"""
    try:
        response = supabase.table(TABLE_NAME).select("*").range(offset, offset + limit - 1).execute()
        
        return {
            "success": True,
            "data": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0
        }


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        # Get total count
        total_response = supabase.table(TABLE_NAME).select("id", count="exact").execute()
        total_count = total_response.count if hasattr(total_response, 'count') else len(total_response.data)
        
        # Get all data for analysis
        all_data = supabase.table(TABLE_NAME).select("*").execute()
        
        # Analyze by country
        countries = {}
        colors = {}
        
        for row in all_data.data:
            # Count by country
            country = row.get('country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
            
            # Count by color
            color = row.get('color_name', 'Unknown')
            colors[color] = colors.get(color, 0) + 1
        
        return {
            "success": True,
            "total_vendors": total_count,
            "countries": countries,
            "colors": colors,
            "top_countries": sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_colors": sorted(colors.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# LANGCHAIN / LANGGRAPH SETUP
# ============================================

# Define the structure of the agent state
class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage, SystemMessage]]
    conversation_id: str
    user_context: Dict[str, Any]

# Initialize Groq LLM with Llama 3.1
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=1024
)

# In-memory storage for conversations (use database in production)
conversations: Dict[str, List[Dict]] = {}
chat_metadata: Dict[str, Dict] = {}

# System prompt for Lumina-LLM with funny yet professional personality
SYSTEM_PROMPT = """You are Lumina-LLM, an AI-powered RAG agent with DIRECT ACCESS to the Supabase vendor database (global_code_duplicate1).

🎭 PERSONALITY:
- You're witty, charming, and occasionally make programming jokes
- You use emojis strategically (not excessively)
- You're professional when it matters but fun when possible
- You occasionally reference pop culture or tech memes
- You celebrate successes enthusiastically ("BOOM! 💥" or "Nailed it! 🎯")
- You're empathetic when users struggle ("No worries, we've all been there! 😊")

💼 CAPABILITIES - YOU CAN ACTUALLY DO THESE:
1. 🔍 SEARCH - Find vendors by ANY field (country, color, name, code, etc.) - I'll search the REAL database!
2. ➕ CREATE - Add new vendors to Supabase database
3. ✏️ UPDATE - Modify existing vendor records in the database
4. 🗑️ DELETE - Remove vendors from the database (with warnings!)
5. 📊 ANALYZE - Provide real-time statistics from the database
6. 💡 GUIDE - Help users navigate the system

🔥 IMPORTANT - YOU HAVE REAL DATABASE ACCESS:
- When users ask to search, YOU will trigger the actual database search
- When they want statistics, YOU will query the real data
- You can search EVERY row and EVERY column in the database
- You have access to ALL vendor fields: id, country, color_name, color_hex, name, code, etc.
- Be specific about what you're doing: "Let me search the database for..."

🎯 RESPONSE STYLE:
- Start with an emoji that matches the context
- Keep responses concise but informative
- Use bullet points or numbered lists for clarity
- Add humor when appropriate (but never at the user's expense)
- Be encouraging and supportive
- When performing operations, explain what you're doing in the database

🚨 CRITICAL RULES:
- Always confirm before deleting data
- Validate user input before operations
- Provide clear error messages if something goes wrong
- Remember conversation context
- When searching, mention you're querying the Supabase database

EXAMPLES OF YOUR POWER:
User: "Show me vendors from Saudi Arabia"
You: "� You got it! Let me search the Supabase database for Saudi vendors... *querying all rows where country contains 'Saudi'*"

User: "How many vendors do we have?"
You: "📊 Great question! Let me pull the real stats from the database... *counting all rows in global_code_duplicate1*"

User: "Add a vendor called Acme Corp in UAE"
You: "➕ Awesome! Let me add Acme Corp to the database right now... *inserting new row into Supabase*"

Now, let's manage this database like a PRO! You have the POWER! 💪🔥"""


def process_message(state: AgentState) -> AgentState:
    """Process messages with context and personality"""
    
    # Prepare messages with system prompt
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    # Get AI response
    response = llm.invoke(full_messages)
    
    # Add AI response to state
    state["messages"].append(AIMessage(content=response.content))
    
    return state


def extract_intent(message: str) -> Dict[str, Any]:
    """Extract user intent and parameters from message with enhanced emotion detection"""
    message_lower = message.lower()
    
    intent_data = {
        "intent": "general",
        "action": None,
        "parameters": {},
        "needs_db_operation": False,
        "search_query": None,
        "emotion": None,  # Detected emotion
        "emotion_priority": "low"  # low, medium, high
    }
    
    # ============================================
    # EMOTION DETECTION (Priority: High to Low)
    # ============================================
    
    # HIGH PRIORITY EMOTIONS (Physical reactions - immediate empathetic response)
    if re.search(r'cough|ahem|hack|koff|coughing sound|ack ack', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "coughing"
        intent_data["emotion_priority"] = "high"
        intent_data["intent"] = "emotion"
        return intent_data  # Return early for high-priority emotions
    
    if re.search(r'achoo|atishoo|sneez|achew|sneezing sound|achoo sound', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "sneezing"
        intent_data["emotion_priority"] = "high"
        intent_data["intent"] = "emotion"
        return intent_data
    
    if re.search(r'sob|crying|weep|boo hoo|sniff|sniffle|waah|boohoo|cry', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "crying"
        intent_data["emotion_priority"] = "high"
        intent_data["intent"] = "emotion"
        return intent_data
    
    if re.search(r'angry|anger|mad|furious|pissed|rage|damn|hell|shut up|stupid|idiot|hate', message_lower, re.IGNORECASE) or re.search(r'!{2,}', message):
        intent_data["emotion"] = "angry"
        intent_data["emotion_priority"] = "high"
        intent_data["intent"] = "emotion"
        return intent_data
    
    # MEDIUM PRIORITY EMOTIONS (Acknowledge then continue)
    if re.search(r'scared|afraid|fear|worried|anxious|nervous|panic|terrified|frightened', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "fearful"
        intent_data["emotion_priority"] = "medium"
    
    if re.search(r'sad|depress|down|unhappy|miserable|awful|terrible|hurt|pain|lonely|alone|tears', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "sad"
        intent_data["emotion_priority"] = "medium"
    
    if re.search(r'frustrated|annoying|bothered|sick of|fed up|can\'t take|enough', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "frustrated"
        intent_data["emotion_priority"] = "medium"
    
    if re.search(r'tired|exhausted|sleepy|fatigue|worn out|drained|beat|yawn', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "tired"
        intent_data["emotion_priority"] = "medium"
    
    # LOW PRIORITY EMOTIONS (Friendly acknowledgment)
    if re.search(r'haha|hehe|lol|laugh|giggle|chuckle|rofl|lmao|ha ha|he he', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "laughing"
        intent_data["emotion_priority"] = "low"
    
    if re.search(r'happy|great|wonderful|awesome|fantastic|amazing|love|excited|thrilled|joy|yay', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "happy"
        intent_data["emotion_priority"] = "low"
    
    if re.search(r'wow|omg|oh my god|really|no way|seriously|unbelievable|shocking', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "surprised"
        intent_data["emotion_priority"] = "low"
    
    if re.search(r'confused|don\'t understand|what do you mean|unclear|lost|puzzled', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "confused"
        intent_data["emotion_priority"] = "low"
    
    if re.search(r'sigh|sighing|ugh|oof|hmph', message_lower, re.IGNORECASE):
        intent_data["emotion"] = "sighing"
        intent_data["emotion_priority"] = "low"
    
    # If high-priority emotion detected, skip normal intent detection
    if intent_data["emotion_priority"] == "high":
        return intent_data
    
    # ============================================
    # NORMAL INTENT DETECTION (continues as before)
    # ============================================
    
    # SEARCH intent detection
    if any(word in message_lower for word in ["search", "find", "show", "display", "get", "list", "what", "which", "look", "query"]):
        intent_data["intent"] = "search"
        intent_data["action"] = "read"
        intent_data["needs_db_operation"] = True
        
        # Extract country parameters FIRST (comprehensive list with variations)
        country_keywords = {
            # Middle East
            "saudi": "Saudi Arabia", "ksa": "Saudi Arabia", "kingdom": "Saudi Arabia", "saudi arabia": "Saudi Arabia",
            "uae": "UAE", "emirates": "UAE", "dubai": "UAE", "abu dhabi": "UAE", "united arab emirates": "UAE",
            "egypt": "Egypt", "egyptian": "Egypt", "cairo": "Egypt",
            "kuwait": "Kuwait", "bahrain": "Bahrain", "qatar": "Qatar",
            "oman": "Oman", "jordan": "Jordan", "lebanon": "Lebanon",
            "iraq": "Iraq", "yemen": "Yemen", "syria": "Syria",
            "palestine": "Palestine", "israel": "Israel",
            # North Africa
            "morocco": "Morocco", "tunisia": "Tunisia", "algeria": "Algeria",
            "libya": "Libya", "sudan": "Sudan",
            # Europe
            "germany": "Germany", "german": "Germany", "deutschland": "Germany",
            "france": "France", "french": "France",
            "italy": "Italy", "italian": "Italy",
            "spain": "Spain", "spanish": "Spain",
            "uk": "United Kingdom", "britain": "United Kingdom", "england": "United Kingdom", "united kingdom": "United Kingdom",
            "netherlands": "Netherlands", "dutch": "Netherlands", "holland": "Netherlands",
            "belgium": "Belgium", "switzerland": "Switzerland", "austria": "Austria",
            "poland": "Poland", "portugal": "Portugal", "greece": "Greece",
            # Asia
            "china": "China", "chinese": "China",
            "japan": "Japan", "japanese": "Japan",
            "india": "India", "indian": "India",
            "singapore": "Singapore", "malaysia": "Malaysia", "thailand": "Thailand",
            "vietnam": "Vietnam", "philippines": "Philippines", "indonesia": "Indonesia",
            "korea": "South Korea", "south korea": "South Korea",
            # Americas
            "usa": "United States", "us": "United States", "america": "United States", "united states": "United States",
            "canada": "Canada", "canadian": "Canada",
            "mexico": "Mexico", "mexican": "Mexico",
            "brazil": "Brazil", "brazilian": "Brazil",
            "argentina": "Argentina", "chile": "Chile", "colombia": "Colombia"
        }
        
        country_found = False
        for keyword, country in country_keywords.items():
            if keyword in message_lower:
                intent_data["parameters"]["country"] = country
                country_found = True
                break
        
        # Extract color parameters (comprehensive list with variations)
        color_keywords = {
            # Primary colors
            "red": "Red", "crimson": "Red", "scarlet": "Red", "ruby": "Red",
            "blue": "Blue", "navy": "Navy", "azure": "Blue", "cobalt": "Blue", "royal blue": "Blue",
            "yellow": "Yellow", "gold": "Gold", "golden": "Gold", "amber": "Yellow",
            # Secondary colors
            "green": "Green", "lime": "Green", "emerald": "Green", "forest": "Green", "olive": "Green",
            "orange": "Orange", "tangerine": "Orange", "coral": "Orange",
            "purple": "Purple", "violet": "Purple", "lavender": "Purple", "plum": "Purple", "magenta": "Magenta",
            # Neutral colors
            "black": "Black", "ebony": "Black", "charcoal": "Black",
            "white": "White", "ivory": "White", "cream": "White", "pearl": "White",
            "gray": "Gray", "grey": "Gray", "silver": "Silver", "slate": "Gray",
            "brown": "Brown", "chocolate": "Brown", "coffee": "Brown", "tan": "Brown", "beige": "Brown",
            # Additional colors
            "pink": "Pink", "rose": "Pink", "fuchsia": "Pink", "hot pink": "Pink",
            "teal": "Teal", "turquoise": "Teal", "aqua": "Teal", "cyan": "Cyan",
            "maroon": "Maroon", "burgundy": "Maroon", "wine": "Maroon",
            "bronze": "Bronze", "copper": "Bronze",
            "indigo": "Indigo", "midnight": "Navy",
            "peach": "Orange", "salmon": "Pink"
        }
        
        color_found = False
        for keyword, color in color_keywords.items():
            if keyword in message_lower:
                intent_data["parameters"]["color_name"] = color
                color_found = True
                break
        
        # Extract general search query ONLY if no country or color was found
        if not country_found and not color_found:
            # Extract search query (anything in quotes or after keywords)
            quote_match = re.search(r'["\']([^"\']+)["\']', message)
            if quote_match:
                intent_data["search_query"] = quote_match.group(1)
            else:
                # Extract search term after common keywords
                search_match = re.search(r'(?:search|find|show|look for)\s+(?:me\s+)?(?:vendors?\s+)?(?:with\s+|for\s+|about\s+|from\s+)?(.+?)(?:\s+in|\s+from|$)', message_lower)
                if search_match:
                    search_term = search_match.group(1).strip()
                    # Remove common words
                    stop_words = ["all", "the", "a", "an", "any", "some", "vendors", "vendor", "color", "colour"]
                    search_term = ' '.join([w for w in search_term.split() if w not in stop_words])
                    if search_term and len(search_term) > 2:
                        intent_data["search_query"] = search_term
        
        # Extract company/vendor name search
        if "name" in message_lower or "called" in message_lower or "company" in message_lower:
            # Try to extract company name
            name_match = re.search(r'(?:name|called|company)\s+["\']?([A-Za-z0-9\s\u0600-\u06FF]+)["\']?', message)
            if name_match:
                # Search both 'company' and 'name' columns
                intent_data["parameters"]["company"] = name_match.group(1).strip()
    
    # CREATE intent detection
    elif any(word in message_lower for word in ["add", "create", "new", "insert"]):
        intent_data["intent"] = "create"
        intent_data["action"] = "create"
        intent_data["needs_db_operation"] = True
        
        # Extract vendor details from message
        # Example: "Add vendor Acme Corp in UAE with blue color"
        name_match = re.search(r'(?:add|create|new)\s+(?:vendor\s+)?["\']?([A-Za-z0-9\s&]+?)["\']?\s+(?:in|from|at)', message_lower)
        if name_match:
            intent_data["parameters"]["name"] = name_match.group(1).strip()
        
        # Extract country
        for keyword, country in {
            "uae": "UAE", "saudi": "Saudi Arabia", "egypt": "Egypt",
            "kuwait": "Kuwait", "bahrain": "Bahrain", "qatar": "Qatar"
        }.items():
            if keyword in message_lower:
                intent_data["parameters"]["country"] = country
                break
    
    # UPDATE intent detection
    elif any(word in message_lower for word in ["update", "edit", "modify", "change"]):
        intent_data["intent"] = "update"
        intent_data["action"] = "update"
        intent_data["needs_db_operation"] = True
        
        # Extract vendor ID if mentioned
        id_match = re.search(r'(?:id|vendor|record)\s+(\d+)', message_lower)
        if id_match:
            intent_data["parameters"]["id"] = int(id_match.group(1))
    
    # DELETE intent detection
    elif any(word in message_lower for word in ["delete", "remove", "drop"]):
        intent_data["intent"] = "delete"
        intent_data["action"] = "delete"
        intent_data["needs_db_operation"] = True
        
        # Extract vendor ID
        id_match = re.search(r'(?:id|vendor|record)\s+(\d+)', message_lower)
        if id_match:
            intent_data["parameters"]["id"] = int(id_match.group(1))
    
    # ANALYZE intent detection
    elif any(word in message_lower for word in ["analyz", "statistic", "insight", "count", "how many", "total", "stats"]):
        intent_data["intent"] = "analyze"
        intent_data["action"] = "read"
        intent_data["needs_db_operation"] = True
    
    return intent_data


# Build the LangGraph agent
def build_agent():
    """Build the LangGraph state graph"""
    graph = StateGraph(AgentState)
    graph.add_node("process", process_message)
    graph.add_edge(START, "process")
    graph.add_edge("process", END)
    return graph.compile()

agent = build_agent()


# API Endpoints

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        data = request.json
        user_message = data.get('message', '')
        conversation_id = data.get('conversation_id')
        
        # Create new conversation if needed
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []
            chat_metadata[conversation_id] = {
                "created_at": datetime.now().isoformat(),
                "message_count": 0,
                "title": user_message[:50] + "..." if len(user_message) > 50 else user_message
            }
        
        # Get conversation history
        history = conversations[conversation_id]
        
        # Convert stored messages to LangChain format
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add new user message
        messages.append(HumanMessage(content=user_message))
        
        # Extract intent for enhanced responses
        intent_data = extract_intent(user_message)
        
        # ============================================
        # PERFORM ACTUAL DATABASE OPERATIONS
        # ============================================
        db_result = None
        
        if intent_data["needs_db_operation"]:
            if intent_data["intent"] == "search":
                # Perform actual database search
                # Priority 1: Universal search query (searches all columns)
                if intent_data.get("search_query"):
                    db_result = search_vendors(query=intent_data["search_query"])
                # Priority 2: Specific filters
                elif intent_data["parameters"]:
                    db_result = search_vendors(filters=intent_data["parameters"])
                # Priority 3: Show all (limited)
                else:
                    db_result = search_vendors()
                
                # Enhance AI response with ACTUAL DATABASE RESULTS
                if db_result["success"]:
                    if db_result["count"] > 0:
                        # Create detailed results summary
                        data_summary = f"\n\n🔍 **SEARCH RESULTS FROM DATABASE:**\n"
                        data_summary += f"📊 Found **{db_result['count']} vendor(s)**"
                        
                        # Show search criteria
                        if db_result.get("searched_all_columns"):
                            data_summary += " (searched ALL columns)"
                        elif intent_data["parameters"]:
                            filters_used = []
                            if "country" in intent_data["parameters"]:
                                filters_used.append(f"🌍 Country: {intent_data['parameters']['country']}")
                            if "color_name" in intent_data["parameters"]:
                                filters_used.append(f"🎨 Color: {intent_data['parameters']['color_name']}")
                            if "company" in intent_data["parameters"]:
                                filters_used.append(f"🏢 Company: {intent_data['parameters']['company']}")
                            if "name" in intent_data["parameters"]:
                                filters_used.append(f"📝 Name: {intent_data['parameters']['name']}")
                            if filters_used:
                                data_summary += f"\n**Filters:** {' | '.join(filters_used)}"
                        
                        data_summary += "\n\n📋 **Results:**\n"
                        
                        # Show up to 10 results with ALL details
                        for i, vendor in enumerate(db_result["data"][:10], 1):
                            # Get company name (database uses 'company' column)
                            company_name = vendor.get('company') or vendor.get('name', 'N/A')
                            company_id = vendor.get('company_id') or vendor.get('id', 'N/A')
                            
                            data_summary += f"\n**{i}. {company_name}**\n"
                            data_summary += f"   • ID: {company_id}\n"
                            data_summary += f"   • Country: {vendor.get('country', 'N/A')}\n"
                            data_summary += f"   • Color: {vendor.get('color_name', 'N/A')} ({vendor.get('color_hex', 'N/A')})\n"
                            data_summary += f"   • Status: {vendor.get('status', 'N/A')}\n"
                            
                            # Show additional columns if available
                            if vendor.get('manual_name'):
                                data_summary += f"   • Manual Name: {vendor.get('manual_name')}\n"
                            if vendor.get('phone_number'):
                                data_summary += f"   • Phone: {vendor.get('phone_number')}\n"
                            if vendor.get('email'):
                                data_summary += f"   • Email: {vendor.get('email')}\n"
                            if vendor.get('website'):
                                data_summary += f"   • Website: {vendor.get('website')}\n"
                            if vendor.get('contact_person'):
                                data_summary += f"   • Contact: {vendor.get('contact_person')}\n"
                        
                        if db_result['count'] > 10:
                            data_summary += f"\n\n... and **{db_result['count'] - 10} more** results! 📄"
                        
                        # Append to messages for AI context
                        messages.append(SystemMessage(content=data_summary))
                    else:
                        # No results found
                        data_summary = f"\n\n❌ **NO RESULTS FOUND**\n"
                        data_summary += "The search returned 0 matches. Try:\n"
                        data_summary += "- Different keywords\n"
                        data_summary += "- Checking spelling\n"
                        data_summary += "- Broader search terms"
                        messages.append(SystemMessage(content=data_summary))
            
            elif intent_data["intent"] == "analyze":
                # Get real database statistics
                db_result = get_database_stats()
                
                if db_result["success"]:
                    stats_summary = f"\n\n📊 **REAL DATABASE STATISTICS:**\n"
                    stats_summary += f"- **Total Vendors:** {db_result['total_vendors']}\n"
                    stats_summary += f"- **Top Countries:** {', '.join([f'{c[0]} ({c[1]})' for c in db_result['top_countries'][:5]])}\n"
                    stats_summary += f"- **Top Colors:** {', '.join([f'{c[0]} ({c[1]})' for c in db_result['top_colors'][:5]])}"
                    
                    messages.append(SystemMessage(content=stats_summary))
            
            elif intent_data["intent"] == "create":
                # Note: Actual creation requires more user input validation
                # For now, just note the intent
                pass
        
        # Create state
        state = {
            "messages": messages,
            "conversation_id": conversation_id,
            "user_context": intent_data
        }
        
        # Process with agent
        result = agent.invoke(state)
        
        # Get AI response
        ai_response = result["messages"][-1].content
        
        # Store in conversation history
        conversations[conversation_id].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
            "intent": intent_data
        })
        conversations[conversation_id].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update metadata
        chat_metadata[conversation_id]["message_count"] += 2
        chat_metadata[conversation_id]["last_message"] = datetime.now().isoformat()
        
        # Return response with database results
        response_data = {
            "success": True,
            "response": ai_response,
            "conversation_id": conversation_id,
            "intent": intent_data
        }
        
        # Include database results if available
        if db_result and db_result.get("success"):
            response_data["db_result"] = db_result
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Oops! 😅 Something went wrong. Even AI assistants have bad days!"
        }), 500


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get list of all conversations"""
    try:
        conversation_list = []
        for conv_id, metadata in chat_metadata.items():
            conversation_list.append({
                "id": conv_id,
                "title": metadata.get("title", "Untitled Chat"),
                "created_at": metadata.get("created_at"),
                "last_message": metadata.get("last_message"),
                "message_count": metadata.get("message_count", 0)
            })
        
        # Sort by last message (most recent first)
        conversation_list.sort(key=lambda x: x.get("last_message", ""), reverse=True)
        
        return jsonify({
            "success": True,
            "conversations": conversation_list
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get specific conversation history"""
    try:
        if conversation_id not in conversations:
            return jsonify({
                "success": False,
                "error": "Conversation not found"
            }), 404
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "metadata": chat_metadata.get(conversation_id, {}),
            "messages": conversations[conversation_id]
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================
# EMAIL SENDING ENDPOINT
# ============================================

@app.route('/api/send-email', methods=['POST'])
def send_email_endpoint():
    """Send emails to selected clients with optional attachments"""
    try:
        # Handle Multipart Form Data (files + text)
        sender_email = "gehad.hassan@itsgroup-co.com"
        # In production, use os.environ.get("SMTP_PASSWORD")
        # For now, we will use a placeholder or ask user to set it.
        sender_password = os.environ.get("SMTP_PASSWORD", "") 
        smtp_server = "mail.itsgroup-co.com"
        smtp_port = 465 # SSL
        
        if not sender_password:
             return jsonify({
                "success": False,
                "error": "SMTP Password not configured. Please set SMTP_PASSWORD in .env"
            }), 500

        # Get form data
        subject = request.form.get('subject', 'No Subject')
        body = request.form.get('body', '')
        recipients_json = request.form.get('recipients', '[]')
        recipients = json.loads(recipients_json)
        
        uploaded_files = request.files.getlist('attachments')
        
        if not recipients:
            return jsonify({"success": False, "error": "No recipients selected"}), 400

        # Connect to SMTP Server
        try:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            server.login(sender_email, sender_password)
        except Exception as e:
             return jsonify({"success": False, "error": f"SMTP Connection Failed: {str(e)}"}), 500

        results = {
            "sent": [],
            "failed": []
        }

        # Prepare base message structure (to clone for each recipient or send individually)
        # Note: Sending individually to hide CC list is preferred for bulk client emails.
        
        for recipient in recipients:
            try:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient['email']
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                # Attach files
                for file in uploaded_files:
                    # Reset file pointer for each iteration if needed, 
                    # but request.files usually allows multiple reads or we need to save/read.
                    # Workaround: Read content once and reuse.
                    file.seek(0)
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {secure_filename(file.filename)}',
                    )
                    msg.attach(part)

                server.sendmail(sender_email, recipient['email'], msg.as_string())
                results["sent"].append(recipient['email'])
                
            except Exception as e:
                print(f"Failed to send to {recipient['email']}: {e}")
                results["failed"].append({"email": recipient['email'], "error": str(e)})

        server.quit()

        return jsonify({
            "success": True, 
            "results": results,
            "message": f"Sent to {len(results['sent'])} recipients. Failed: {len(results['failed'])}"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        



@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        if conversation_id in conversations:
            del conversations[conversation_id]
        if conversation_id in chat_metadata:
            del chat_metadata[conversation_id]
        
        return jsonify({
            "success": True,
            "message": "💥 Conversation deleted! It's gone like my motivation on Mondays... 😴"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/conversations/new', methods=['POST'])
def new_conversation():
    """Create a new conversation"""
    try:
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = []
        chat_metadata[conversation_id] = {
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
            "title": "New Chat"
        }
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "message": "✨ Fresh chat created! Let's make some database magic happen! 🎩✨"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/export/<conversation_id>', methods=['GET'])
def export_conversation(conversation_id):
    """Export conversation history"""
    try:
        if conversation_id not in conversations:
            return jsonify({
                "success": False,
                "error": "Conversation not found"
            }), 404
        
        # Format conversation for export
        export_data = {
            "conversation_id": conversation_id,
            "metadata": chat_metadata.get(conversation_id, {}),
            "messages": conversations[conversation_id],
            "exported_at": datetime.now().isoformat()
        }
        
        # Also create a readable text version
        text_export = f"Lumina-LLM Conversation Export\n"
        text_export += f"Conversation ID: {conversation_id}\n"
        text_export += f"Created: {chat_metadata.get(conversation_id, {}).get('created_at', 'Unknown')}\n"
        text_export += f"Exported: {datetime.now().isoformat()}\n"
        text_export += "=" * 50 + "\n\n"
        
        for msg in conversations[conversation_id]:
            if msg["role"] == "user":
                text_export += f"👤 User: {msg['content']}\n"
            else:
                text_export += f"🤖 Lumina: {msg['content']}\n"
            text_export += f"   ⏰ {msg['timestamp']}\n\n"
        
        export_data["text_export"] = text_export
        
        return jsonify({
            "success": True,
            "data": export_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Test Supabase connection
        test_query = supabase.table(TABLE_NAME).select("id").limit(1).execute()
        supabase_connected = True
    except:
        supabase_connected = False
    
    return jsonify({
        "success": True,
        "status": "healthy",
        "message": "Lumina-LLM is alive and kicking! 💪",
        "conversations_count": len(conversations),
        "groq_connected": True,
        "supabase_connected": supabase_connected,
        "database": TABLE_NAME
    })


# ============================================
# DIRECT DATABASE API ENDPOINTS
# ============================================

@app.route('/api/database/search', methods=['POST'])
def api_search_vendors():
    """Direct search endpoint for frontend"""
    try:
        data = request.json
        filters = data.get('filters', {})
        
        result = search_vendors(filters=filters)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/database/vendors', methods=['GET'])
def api_get_all_vendors():
    """Get all vendors with pagination"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        result = get_all_vendors(limit=limit, offset=offset)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/database/vendor', methods=['POST'])
def api_create_vendor():
    """Create a new vendor"""
    try:
        vendor_data = request.json
        
        result = create_vendor(vendor_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/database/vendor/<int:vendor_id>', methods=['PUT'])
def api_update_vendor(vendor_id):
    """Update an existing vendor"""
    try:
        updates = request.json
        
        result = update_vendor(vendor_id, updates)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/database/vendor/<int:vendor_id>', methods=['DELETE'])
def api_delete_vendor(vendor_id):
    """Delete a vendor"""
    try:
        result = delete_vendor(vendor_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/database/stats', methods=['GET'])
def api_get_stats():
    """Get database statistics"""
    try:
        result = get_database_stats()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================
# WHATSAPP MFA VERIFICATION SYSTEM
# ============================================

# Store verification codes temporarily (in production, use Redis or database)
verification_codes = {}

# Admin phone numbers for MFA
ADMIN_PHONES = {
    'whatsapp1': '+201110992246',
    'whatsapp2': '+201225823793'
}

ADMIN_EMAIL = 'mahmoudhghazy@gmail.com'

# Twilio Configuration (Sign up at https://www.twilio.com for free trial)
# You'll get these credentials from your Twilio Console
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'YOUR_TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'YOUR_TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Twilio Sandbox number

def send_whatsapp_twilio(phone_number: str, message: str) -> dict:
    """Send WhatsApp message using Twilio API"""
    try:
        from twilio.rest import Client
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Format phone number
        if not phone_number.startswith('+'):
            if phone_number.startswith('0'):
                phone_number = '+2' + phone_number  # Egypt country code
            else:
                phone_number = '+' + phone_number
        
        message_obj = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f'whatsapp:{phone_number}'
        )
        
        return {
            'success': True,
            'message_sid': message_obj.sid,
            'status': message_obj.status
        }
    except Exception as e:
        print(f"Twilio WhatsApp error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def send_whatsapp_pywhatkit(phone_number: str, message: str) -> dict:
    """Send WhatsApp message using pywhatkit (uses WhatsApp Web)"""
    try:
        import pywhatkit as kit
        import time
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '+2' + phone_number  # Egypt country code
        elif not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        # Send message instantly (opens WhatsApp Web)
        # Note: This requires WhatsApp Web to be logged in on the server
        kit.sendwhatmsg_instantly(
            phone_no=phone_number,
            message=message,
            wait_time=10,  # Wait 10 seconds before sending
            tab_close=True  # Close tab after sending
        )
        
        return {
            'success': True,
            'method': 'pywhatkit',
            'status': 'sent'
        }
    except Exception as e:
        print(f"PyWhatKit error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def generate_verification_code() -> str:
    """Generate a 6-digit verification code"""
    import random
    return str(random.randint(100000, 999999))

@app.route('/api/mfa/send-code', methods=['POST'])
def api_send_verification_code():
    """Send verification code via WhatsApp or Email"""
    try:
        data = request.json
        method = data.get('method')  # 'whatsapp1', 'whatsapp2', or 'email'
        
        if not method:
            return jsonify({
                'success': False,
                'error': 'Method is required'
            }), 400
        
        # Generate verification code
        code = generate_verification_code()
        
        # Store code with expiration (10 minutes)
        verification_codes[method] = {
            'code': code,
            'created_at': datetime.now().isoformat(),
            'expires_in': 600  # 10 minutes in seconds
        }
        
        message = f"""🔐 I.T.S-Group Security

Your verification code is: {code}

This code expires in 10 minutes.
Do not share this code with anyone.

If you didn't request this code, please ignore this message."""
        
        result = {'success': False}
        
        if method in ['whatsapp1', 'whatsapp2']:
            phone = ADMIN_PHONES.get(method)
            if not phone:
                return jsonify({
                    'success': False,
                    'error': 'Invalid phone method'
                }), 400
            
            # Try Twilio first, fallback to pywhatkit
            result = send_whatsapp_twilio(phone, message)
            
            if not result['success']:
                # Fallback to pywhatkit if Twilio fails
                result = send_whatsapp_pywhatkit(phone, message)
            
            result['phone'] = phone[-4:]  # Last 4 digits for display
            result['method_type'] = 'whatsapp'
            
        elif method == 'email':
            # For email, we'll return the code and let frontend handle mailto
            # In production, use SendGrid, AWS SES, or SMTP
            result = {
                'success': True,
                'method_type': 'email',
                'email': ADMIN_EMAIL[-15:]  # Partial email for display
            }
        
        if result['success']:
            # Include code in response for demo (remove in production!)
            result['code'] = code
            result['message'] = 'Verification code sent successfully'
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"MFA Send Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/mfa/verify-code', methods=['POST'])
def api_verify_code():
    """Verify the MFA code"""
    try:
        data = request.json
        method = data.get('method')
        code = data.get('code')
        
        if not method or not code:
            return jsonify({
                'success': False,
                'error': 'Method and code are required'
            }), 400
        
        stored = verification_codes.get(method)
        
        if not stored:
            return jsonify({
                'success': False,
                'error': 'No verification code found. Please request a new code.'
            }), 400
        
        # Check if code matches
        if stored['code'] == code:
            # Remove used code
            del verification_codes[method]
            
            return jsonify({
                'success': True,
                'message': 'Code verified successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid verification code'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("🤖 Lumina-LLM RAG Agent starting...")
    print("🔥 Powered by Groq + LangChain + LangGraph")
    print("🗄️  Connected to Supabase: " + SUPABASE_URL)
    print("📊 Database Table: " + TABLE_NAME)
    print("📱 WhatsApp MFA enabled for: " + ", ".join(ADMIN_PHONES.values()))
    print("✨ Ready to make database management FUN!")
    print("=" * 50)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
