from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rm_chatbot import graph  # Import your improved langgraph agent
from typing import Optional, List, Dict
from langchain_core.messages import HumanMessage
from firebase_app import create_session, update_chat_session, session_exists, get_chat_session, get_agent, create_agent
import uuid

app = FastAPI()
def messageFormatConverter(messageList):
    newList=[]
    for i in messageList:
        content=i.content
        type=i.type
        newMessage={"role":type,"content":content}
        newList.append(newMessage)
    return newList

# In-memory session storage (replace with a database in production)
sessions: Dict[str, Dict] = {}

class InitializeSession(BaseModel):
    previous_chat_history: List[Dict]
    agent_id:str

class ChatMessage(BaseModel):
    session_id: str
    user_input: str

class ChatResponse(BaseModel):
    session_id: str
    message: str
    current_summary: Optional[str]

class CreateAgent(BaseModel):
    name:str
    role:str
    scope: str
    company_name: str
    company_description: str
    custom_prompt: Optional[str]= Field(default=None)

@app.post("/create_agent",response_model=dict)
async def create_agent_endpoint(request:CreateAgent):
    agent_id=str(uuid.uuid4())
    name, identity,scope,company_name,company_description=request.name, request.role,request.scope,request.company_name,request.company_description
    custom_prompt=request.custom_prompt
    prompt=f"Your name is {name} , and you are a {identity} at {company_name}, a {company_description}. Your task is to assist humans on {scope}."
    if custom_prompt:
        prompt=custom_prompt
    # agent[agent_id]=prompt
    create_agent(agent_id,prompt)

    return {"agent_id":agent_id,"behaviour":prompt}





@app.post("/initialize_session", response_model=dict)
async def initialize_session(request: InitializeSession):
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    
    # Initialize the session with previous chat history
    output = graph.invoke({
        "prev_chat_history": request.previous_chat_history,
        "messages": []
    }, config)

    previous_chat_history_summary=output.get("prev_chat_history_summary", "")
    agent_id=request.agent_id
    create_session(session_id,previous_chat_history_summary,agent_id)
    # Store the session state
    # sessions[session_id] = {
    #     "prev_chat_history_summary": output.get("prev_chat_history_summary", ""),
    #     "messages": [],
    #     "current_summary":""
    # }
    
    return {"session_id": session_id,"agent_id":agent_id}



@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    # if request.session_id not in sessions:
    session_id=request.session_id
    
    session=get_chat_session(session_id)
    # print("the session looks something like", session)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # session = sessions[request.session_id]
    config = {"configurable": {"thread_id": session_id}}
    
    # input_message = HumanMessage(content=request.user_input)
    # input_message=input_message.to_json()
    # print(input_message)

    input_message={"role":"human","content":request.user_input}

    #update message 1

    # update_chat_session(session_id,new_message=input_message)
    session["messages"].append(input_message)
    # print("after updating the input message", session)
    agent_id=session['agent_id']
    agent=get_agent(agent_id)
    prompt=agent['prompt']


    output = graph.invoke({
        "prev_chat_history_summary": session["prev_chat_history_summary"],
        "messages": session["messages"],
        "agent_prompt": prompt
    }, config)


    # print(output)
    # print("here we are getting index error,", output)
    ai_message = output['messages'][-1]
    # print('ai message before ', ai_message)
    ai_message_converted = {
    "role": "ai",
    "content": ai_message.content
    }
    # print("ai message after",ai_message_converted)

    #update message 2    
    update_chat_session(session_id,new_message=[input_message,ai_message_converted],append=True)
    # session["messages"].append(ai_message)
    summary=output.get("summary","")

    #update summary
    
    # session['current_summary']=summary
    
    # Update session state if summarized
    if "summary" in output:
        update_chat_session(session_id,current_summary=summary)
        output_messages=output["messages"]

        # print("This  is the output messages ",output_messages)

        output_messages_converted=messageFormatConverter(output_messages)
        # updating messages again, not appending because this time some have been deleted
        update_chat_session(session_id,new_message=output_messages_converted,append=False)
        # session["messages"] = output["messages"]
    
    return ChatResponse(session_id=request.session_id, message=ai_message.content,current_summary=summary)

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    session=get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, 
            "history": session["messages"],
            "prev_chat_history_summary":session["prev_chat_history_summary"],
            "current_summary":session["current_summary"] }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8080, reload=True)