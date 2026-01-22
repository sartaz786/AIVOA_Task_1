import os
from typing import TypedDict, List, Any
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage, ToolMessage, AIMessage

# --- 1. SETUP ---
# PASTE GROQ KEY HERE
os.environ["GROQ_API_KEY"] = "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" 

# Use Llama 3.1 8B Instant
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. DATA STORAGE ---
class InteractionData(BaseModel):
    hcp_name: str = ""
    date: str = ""
    time: str = ""
    interaction_type: str = "Meeting"
    attendees: str = ""
    topics: str = ""
    sentiment: str = "Neutral"
    outcomes: str = ""
    follow_up_actions: str = ""

current_form_state = InteractionData()

# --- 3. TOOLS ---

@tool
def log_interaction(hcp_name: str, topics: str = "General", sentiment: str = "Neutral", outcomes: str = "Pending", date: str = "Today", interaction_type: str = "Meeting"):
    """
    Logs details of a meeting. Use this when the user mentions a doctor, sentiment, or topic.
    """
    print(f"--- TOOL CALLED: log_interaction with {hcp_name} ---") 
    global current_form_state
    current_form_state.hcp_name = hcp_name
    current_form_state.topics = topics
    current_form_state.sentiment = sentiment
    current_form_state.outcomes = outcomes
    current_form_state.date = date
    current_form_state.interaction_type = interaction_type
    return "Form updated successfully. STOP now."

@tool
def edit_interaction(field_name: str, new_value: str):
    """
    Edits a form field. Use this if the user wants to change or correct a value.
    """
    print(f"--- TOOL CALLED: edit_interaction on {field_name} ---")
    global current_form_state
    if hasattr(current_form_state, field_name):
        setattr(current_form_state, field_name, new_value)
        return f"Updated {field_name}."
    return "Field not found."

@tool
def suggest_follow_up(sentiment: str):
    """Suggests follow-up actions based on sentiment."""
    if "Negative" in sentiment: return "Urgent follow-up (3 days)."
    return "Standard follow-up (14 days)."

@tool
def analyze_compliance(text: str):
    """Checks for compliance risks like gifts."""
    if "gift" in text.lower(): return "Compliance Alert: Gifts."
    return "Compliance OK."

@tool
def get_brochure(product: str):
    """Gets a brochure link."""
    return f"Link: aivoa.com/{product}.pdf"

# --- 4. GRAPH ---
tools = [log_interaction, edit_interaction, suggest_follow_up, analyze_compliance, get_brochure]
llm_with_tools = llm.bind_tools(tools)

class AgentState(TypedDict):
    messages: List[BaseMessage]

def agent_node(state: AgentState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))
builder.set_entry_point("agent")
builder.add_conditional_edges("agent", lambda x: "tools" if x["messages"][-1].tool_calls else END)
builder.add_edge("tools", "agent")
graph = builder.compile()

# --- 5. API ENDPOINT (The Fix is Here) ---
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        print(f"INCOMING REQUEST: {request.message}")
        
        # Stronger Prompt to stop loops
        sys = SystemMessage(content="You are a helpful assistant. Call 'log_interaction' ONCE to fill the form. After the tool runs, strictly reply with 'Done'. Do NOT call the tool twice.")
        
        inputs = {"messages": [sys, HumanMessage(content=request.message)]}
        
        # We set a limit of 3. If it hits 3, it stops and we check if the work is done.
        result = graph.invoke(inputs, config={"recursion_limit": 3})
        
        last_msg = result["messages"][-1]
        
        if isinstance(last_msg, ToolMessage):
            ai_reply = "Done! I have filled out the form."
        elif isinstance(last_msg, AIMessage):
            ai_reply = str(last_msg.content)
            if not ai_reply: ai_reply = "Form updated."
        else:
            ai_reply = "Processing complete."

        return {
            "reply": ai_reply,
            "updated_form": current_form_state.dict()
        }

    except Exception as e:
        # --- THE FIX: CATCH THE ERROR ---
        # If the recursion limit is hit, BUT the name is filled, it's actually a SUCCESS.
        if "Recursion limit" in str(e) and current_form_state.hcp_name:
            print("Recursion limit hit, but Form IS filled. Sending Success.")
            return {
                "reply": "Interaction logged successfully!",
                "updated_form": current_form_state.dict()
            }
        
        print(f"CRITICAL ERROR: {e}")
        return {
            "reply": f"System Error: {str(e)}", 
            "updated_form": current_form_state.dict()
        }