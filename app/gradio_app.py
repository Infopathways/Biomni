import os
import argparse
import traceback
import gradio as gr

# --- Lazy-loading setup ---
# We start with the agent as None. It will be created only when first needed.
agent_instance = None
AGENT_AVAILABLE = False
INITIALIZATION_ERROR = None # This will store the error message if initialization fails.

def initialize_agent():
    """
    This function handles the one-time, delayed initialization of the agent.
    """
    global agent_instance, AGENT_AVAILABLE, INITIALIZATION_ERROR

    # If the agent is already loaded, do nothing.
    if agent_instance is not None:
        return

    print("--- LAZY LOADING: First request received, attempting to initialize Biomni agent... ---")
    try:
        # 1. Import the agent class.
        from biomni.agent.a1 import A1
        
        # 2. Securely read the API key from the environment (set in Azure Portal).
        OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            raise ValueError("CRITICAL ERROR: OPENAI_API_KEY environment variable not found in Azure Configuration.")

        # 3. Initialize the agent, explicitly telling it which AI provider to use.
        agent_instance = A1(
            source="OpenAI",
            llm="gpt-4-turbo", # Or "gpt-3.5-turbo" if you prefer
            api_key=OPENAI_API_KEY
        )
        
        AGENT_AVAILABLE = True
        print("--- LAZY LOADING: Agent initialized successfully. ---")

    except Exception as e:
        # If any part of the above fails, store the error and log it.
        INITIALIZATION_ERROR = e
        AGENT_AVAILABLE = False
        print("--- FATAL: FAILED TO LAZILY INITIALIZE BIOMNI AGENT ---")
        traceback.print_exc()

def respond(text: str) -> str:
    """
    This is the main function called by the UI for every message.
    """
    # This is the key: it ensures the agent is loaded before proceeding.
    # It only does the heavy work on the very first call.
    initialize_agent()

    # After attempting to load, check the status.
    if not AGENT_AVAILABLE or agent_instance is None:
        # Return a helpful error message to the user.
        return f"Agent failed to initialize. Error: {INITIALIZATION_ERROR}"
    
    if not text:
        return "(empty)"

    try:
        # If initialization succeeded, call the agent's stream method.
        final_response = "Agent did not return a response."
        for chunk in agent_instance.go_stream(text):
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
        
        return final_response
    except Exception as e:
        traceback.print_exc()
        return f"An error occurred while the agent was running: {e}"

def main(host: str, port: int):
    # This uses the simple gr.Interface, as in your original file.
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
