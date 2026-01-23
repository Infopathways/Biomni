import os
import argparse
import traceback
import gradio as gr

# --- NEW: Read the API key securely from the environment ---
# This line reads the key provided by your azure-deploy.yml file.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- MODIFIED: Import and Initialize the Agent ---
try:
    from biomni.agent.a1 import A1
    print("Initializing Biomni agent...")

    # Check if the API key was found in the environment.
    if not OPENAI_API_KEY:
        raise ValueError("CRITICAL ERROR: OPENAI_API_KEY environment variable was not found by the application.")

    # Explicitly configure the agent to use only OpenAI.
    # This tells the agent which key to use and prevents the authentication error.
    agent_instance = A1(
        source="OpenAI",
        llm="gpt-4-turbo",  # Or another model like "gpt-3.5-turbo"
        api_key=OPENAI_API_KEY
    )
    AGENT_AVAILABLE = True
    print("Successfully initialized Biomni agent with OpenAI configuration.")

except Exception as e:
    agent_instance = None
    AGENT_AVAILABLE = False
    print("--- FATAL: FAILED TO INITIALIZE BIOMNI AGENT ---")
    traceback.print_exc()

# --- The rest of the file defines the web interface logic ---

def respond(text: str) -> str:
    """
    This handler now calls the biomni agent's .go_stream() method
    and returns the final complete response.
    """
    if not AGENT_AVAILABLE or agent_instance is None:
        return "ERROR: The Biomni agent is not available. Please check the application logs for why it failed to start."
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
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT") or os.environ.get("WEBSITES_PORT") or 7860),
    )
    args = parser.parse_args()
    main(args.host, args.port)
