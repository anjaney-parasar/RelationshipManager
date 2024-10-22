import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
from dotenv import load_dotenv
load_dotenv()

# Use a service account.
cred_path=os.getenv("CRED_PATH")
cred = credentials.Certificate(cred_path)

app = firebase_admin.initialize_app(cred)

db = firestore.client()



from functools import lru_cache


# Function to fetch document from Firestore and cache it
@lru_cache(maxsize=1)
def get_agent(agent_id: str):
    try:
        doc_ref = db.collection('Agents').document(agent_id)
        doc = doc_ref.get()
        if doc.exists:
            print("Agent has been found ")
            return doc.to_dict()
        else:
            print("Document not found")
    except Exception as e:
        print(f"Exception {e}")

def create_agent(agent_id, prompt):
   doc_ref=db.collection("Agents").document(agent_id)
   data={
      "prompt":prompt
   }
   doc_ref.set(data)
   print(f"Agent {agent_id} created succesfully.")


def create_session(session_id, prev_chat_history_summary,agent_id):
  doc_ref = db.collection("chatSessions").document(session_id)
  data={
     "messages":[],
     "prev_chat_history_summary":prev_chat_history_summary,
     "current_summary":"",
     "agent_id":agent_id
  }
  doc_ref.set(data)
  print(f"Chat session {session_id} created.")

def update_chat_session(session_id,append=True,new_message=None, current_summary=None):
  doc_ref=db.collection("chatSessions").document(session_id)
  doc = doc_ref.get()
  if doc.exists:
    data=doc.to_dict()
    update_data={}

    if (new_message) and (append):
      updated_messages=data['messages']+new_message
      update_data['messages']=updated_messages
    
    if (new_message) and (not append):
      update_data['messages']=new_message

    if current_summary:
      update_data['current_summary']=current_summary

    doc_ref.update(update_data)
  else :
    print(f"Session {session_id} does not exist.")

def get_chat_session(session_id):
    # Reference the document
    doc_ref = db.collection('chatSessions').document(session_id)
    
    # Get the document
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    else:
        print(f"No chat session found for {session_id}")
        return None
    
def session_exists(session_id):
   doc_ref=db.collection('chatSessions').document(session_id)
   doc=doc_ref.get()

   if doc.exists():
      return True
   else:
      return False



# users_ref = db.collection("chatSessions")
# docs = users_ref.stream()

# for doc in docs:
#     print(f"{doc.id} => {doc.to_dict()}")