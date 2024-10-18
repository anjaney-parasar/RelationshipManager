
import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langgraph.graph import END, MessagesState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START
from pprint import pprint

# Database setup
db_path = "state_db/example.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
memory = SqliteSaver(conn)

model = ChatOpenAI(model="gpt-4")

class State(MessagesState):
    prev_chat_history_summary: str
    prev_chat_history:list[dict]
    summary: str

def prev_chat_summariser(state: State):
    prev_chat_history = state.get("prev_chat_history", "")
    if not state.get("prev_chat_history_summary"):
        prompt = ChatPromptTemplate.from_template(
            """Summarise the following conversation between a Human Agent and customer {prev_chat_history}"""
        )
        chain = prompt | model | StrOutputParser()
        prev_chat_history_summary = chain.invoke({"prev_chat_history": prev_chat_history})
        state["prev_chat_history_summary"] = prev_chat_history_summary
    return state

def call_model(state: State):
    prev_chat_history_summary = state.get("prev_chat_history_summary", "")

    messages = state["messages"]
    
    if messages:

        prompt = ChatPromptTemplate.from_template(
            """Travel Dreams Agency specializes in luxury travel experiences.
            We offer customized itineraries, group tours, and cruise packages.
            Our working hours are 9 AM to 5 PM EST, Monday to Friday.
            For urgent matters outside business hours, please email emergency@traveldreams.com.

            Frequently Asked Questions:
            1. How do I book a trip? Visit our website or call us at 1-800-TRAVEL-DREAMS.
            2. What's your cancellation policy? Full refund if cancelled 30 days before the trip.
            3. Do you offer travel insurance? Yes, we partner with TravelSafe Insurance.

            You are a helpful AI assistant for Travel Dreams Agency who responds to user messages when the human agent is unavailable.
            Use the previous chat history between human agent and customer and above information to respond to customer queries
            Previous chat history between human agent and customer: {prev_chat_history_summary}
            The conversation till now: {messages}
            Your response:
            """
        )
        chain = prompt | model | StrOutputParser()
        response = chain.invoke({"messages": messages, "prev_chat_history_summary": prev_chat_history_summary})
        state['messages']=response
    return state

def summarize_conversation(state: State):
    summary = state.get("summary", "")
    if summary:
        summary_message = (
            f"This is summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
    else:
        summary_message = "Create a summary of the conversation above:"

    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    state['summary']=response.content
    state['messages']=delete_messages
    return state

def should_continue(state: State):
    if len(state["messages"]) > 6:
        return "summariser"
    return END

# Define the graph
workflow = StateGraph(State)
workflow.add_node("prev_summary", prev_chat_summariser)
workflow.add_node("conversation", call_model)
workflow.add_node("summariser", summarize_conversation)

workflow.add_edge(START, "prev_summary")
workflow.add_edge("prev_summary", "conversation")
workflow.add_conditional_edges("conversation", should_continue)
workflow.add_edge("summariser", END)

# Compile the graph
graph = workflow.compile(checkpointer=memory)

if __name__=="__main__":
    # Create a thread
    config = {"configurable": {"thread_id": "agdagsdag"}}

    previous_chat_history=[
        {"role": "CUSTOMER", "message": "Hi, my name is jane I wanted to check if there are any flights available to Paris next weekend?"},
        {"role": "AGENT", "message": "Hello! Let me check that for you. Could you please confirm your departure city?"},
        {"role": "CUSTOMER", "message": "Sure, I’m flying from New York."},
        {"role": "AGENT", "message": "Thank you! We have several flights available. Do you have a preferred airline or time of day?"},
        {"role": "CUSTOMER", "message": "No specific airline, but I’d prefer a morning flight."},
        {"role": "AGENT", "message": "Got it. We have a morning flight with Air France departing at 8:30 AM. Would you like me to book that for you?"},
        {"role": "CUSTOMER", "message": "That sounds good! Could you also check if there are any hotel deals in Paris?"},
        {"role": "AGENT", "message": "Of course! Do you have a preferred area in Paris or specific dates for your stay?"},
        {"role": "CUSTOMER", "message": "I’d prefer to stay near the Eiffel Tower, and I’ll be there from the 15th to the 18th."},
        {"role": "AGENT", "message": "Great! I’ve found a few hotels near the Eiffel Tower with special deals during your dates. Would you like a 4-star or 5-star hotel?"},
        {"role": "CUSTOMER", "message": "A 4-star hotel would be fine."},
        {"role": "AGENT", "message": "We have a 4-star hotel available for $200 per night. Would you like to proceed with the booking?"}
    ]

    # Start conversation
    """
    output = graph.invoke({
        "prev_chat_history": previous_chat_history,
        "messages": []
    }, config)

    pprint(output)
    
    """  
    
    
    # input_message = HumanMessage(content="Which area would be the best though?")
    # output = graph.invoke({"prev_chat_history":previous_chat_history ,"messages": [input_message]}, config)  ###Three inputs required
    # for m in output['messages'][-1:]:
    #     m.pretty_print()

    # input_message = HumanMessage(content="what's my name?")
    # output = graph.invoke({"messages": [input_message]}, config)
    # for m in output['messages'][-1:]:
    #     m.pretty_print()

    # input_message = HumanMessage(content="i like the 49ers!")
    # output = graph.invoke({"messages": [input_message]}, config)
    # for m in output['messages'][-1:]:
    #     m.pretty_print()

        
    """Let's confirm that our state is saved locally."""

    input_message = HumanMessage(content="i like the 49ers!")
    output = graph.invoke({"prev_chat_history":previous_chat_history ,"messages": [input_message]}, config)

    from pprint import pprint
    pprint(output)

    # API
    # request/ input= thread_id, message, previous_chat_history
    # output = AI message , summary

    # Create a thread
