import os
import argparse
import traceback  # Import for better error logging
import gradio as gr


# This block runs once when the application starts.
try:
    from biomni.agent.a1 import A1
    print("Initializing Biomni agent...")
    agent_instance = A1()
    AGENT_AVAILABLE = True
    print("Successfully initialized Biomni agent.")
except Exception:
    agent_instance = None
    AGENT_AVAILABLE = False
    print("--- FATAL: FAILED TO INITIALIZE BIOMNI AGENT ---")
    traceback.print_exc()

def respond(text: str) -> str:
    """
    This handler now calls the biomni agent's .go_stream() method
    and returns the final complete response.
    """
    # First, check if the agent loaded correctly during startup.
    if not AGENT_AVAILABLE or agent_instance is None:
        return "ERROR: The Biomni agent is not available. Check application logs."

    # If the user input is empty, don't call the agent.
    if not text:
        return "(empty)"

    try:
        print(f"Passing message to agent: '{text}'")
        
        # Call the agent's .go_stream() method.
        # Since gr.Interface expects a single final string, we loop through the
        # stream and capture only the last (most complete) response.
        final_response = "Agent did not return a response."
        for chunk in agent_instance.go_stream(text):
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
        
        print(f"Final response from agent: '{final_response}'")
        return final_response

    except Exception as e:
        # If the agent fails during execution, print the error and return it to the UI.
        print(f"--- ERROR DURING AGENT EXECUTION ---")
        traceback.print_exc()
        return f"An error occurred within the agent: {e}"


def main(host: str, port: int):
    # The original gr.Interface is kept, but its 'fn' now points to our new respond logic.
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
