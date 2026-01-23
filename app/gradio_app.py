import os
import argparse
import traceback
import gradio as gr

# We will create the agent instance only when it's first needed.
# Initialize agent_instance to None. It will act as our flag.
agent_instance = None
AGENT_AVAILABLE = False
INITIALIZATION_ERROR = None

def initialize_agent():
    """
    This function handles the one-time initialization of the agent.
    It will only be called the first time a user sends a message.
    """
    global agent_instance, AGENT_AVAILABLE, INITIALIZATION_ERROR

    # If already initialized, do nothing.
    if agent_instance is not None:
        return

    print("--- LAZY LOADING: First request received, attempting to initialize Biomni agent... ---")
    try:
        from biomni.agent.a1 import A1
        
        OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            raise ValueError("CRITICAL ERROR: OPENAI_API_KEY environment variable not found. Check deployment settings.")

        # Explicitly configure the agent.
        agent_instance = A1(
            source="OpenAI",
            llm="gpt-4-turbo", # Or "gpt-3.5-turbo"
            api_key=OPENAI_API_KEY
        )
        AGENT_AVAILABLE = True
        print("--- LAZY LOADING: Agent initialized successfully. ---")

    except Exception as e:
        INITIALIZATION_ERROR = e
        AGENT_AVAILABLE = False
        print("--- FATAL: FAILED TO LAZILY INITIALIZE BIOMNI AGENT ---")
        traceback.print_exc()

def respond(text: str) -> str:
    """
    This handler now ensures the agent is initialized, then calls it.
    """
    # This is the key: initialize the agent on the first call.
    initialize_agent()

    # Now check the status after attempting initialization.
    if not AGENT_AVAILABLE or agent_instance is None:
        error_msg = f"Agent failed to initialize. Error: {INITIALIZATION_ERROR}"
        print(error_msg)
        return error_msg
    
    if not text:
        return "(empty)"

    try:
        print(f"Passing message to agent: '{text}'")
        final_response = "Agent did not return a response."
        for chunk in agent_instance.go_stream(text):
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
        
        print(f"Final response from agent: '{final_response}'")
        return final_response
    except Exception as e:
        print(f"--- ERROR DURING AGENT EXECUTION ---")
        traceback.print_exc()
        return f"An error occurred within the agent: {e}"

def main(host: str, port: int):
    iface = gr.Interface(
        fn=respond,
        inputs="text",
        outputs="text",
        title="Biomni Gradio UI",
        description="A minimal Gradio UI for Biomni. This now calls the agent.",
    )
    print(f"Launching Gradio UI on {host}:{port}")
    iface.launch(server_name=host, server_port=port, share=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT") or os.environ.get("WEBSITES_PORT") or 7860))
    args = parser.parse_args()
    main(args.host, args.port)
