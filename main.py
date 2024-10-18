from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rm_chatbot import graph  # Import your improved langgraph agent
from typing import Optional, List, Dict
from langchain_core.messages import HumanMessage
import uuid

app = FastAPI()

# In-memory session storage (replace with a database in production)
sessions: Dict[str, Dict] = {}

class InitializeSession(BaseModel):
    previous_chat_history: List[Dict]

class ChatMessage(BaseModel):
    session_id: str
    user_input: str

class ChatResponse(BaseModel):
    session_id: str
    message: str

@app.post("/initialize_session", response_model=dict)
async def initialize_session(request: InitializeSession):
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    
    # Initialize the session with previous chat history
    output = graph.invoke({
        "prev_chat_history": request.previous_chat_history,
        "messages": []
    }, config)

    print(output)
    
    # Store the session state
    sessions[session_id] = {
        "prev_chat_history_summary": output.get("prev_chat_history_summary", ""),
        "messages": []
    }
    
    return {"session_id": session_id}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    config = {"configurable": {"thread_id": request.session_id}}
    
    input_message = HumanMessage(content=request.user_input)
    session["messages"].append(input_message)
    
    output = graph.invoke({
        "prev_chat_history_summary": session["prev_chat_history_summary"],
        "messages": session["messages"]
    }, config)
    
    ai_message = output['messages'][-1]
    session["messages"].append(ai_message)
    
    # Update session state if summarized
    if "summary" in output:
        session["messages"] = output["messages"]
    
    return ChatResponse(session_id=request.session_id, message=ai_message.content)

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": sessions[session_id]["messages"],"prev_chat_history_summary":sessions[session_id]["prev_chat_history_summary"] }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8080)