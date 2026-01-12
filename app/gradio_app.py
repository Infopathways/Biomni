import os
import argparse
import traceback  # Import traceback for better error logging
import gradio as gr

# --- Step 1: Import and Initialize the Agent ---
# This block runs only once when the application starts up.
try:
    from biomni.agent.a1 import A1
    # Initialize the agent with its default settings.
    # This might take a moment as it loads configurations and checks files.
    print("Initializing Biomni agent...")
    agent_instance = A1() 
    AGENT_AVAILABLE = True
    print("Successfully initialized Biomni agent. The application is ready.")
except Exception as e:
    agent_instance = None
    AGENT_AVAILABLE = False
    print("--- FATAL: FAILED TO INITIALIZE BIOMNI AGENT ---")
    # Print the full error to the logs so we can debug it if it happens.
    traceback.print_exc()
    print("-------------------------------------------------")


# --- Step 2: Define the Core Logic Functions ---

def get_biomni_response(message: str) -> "Generator[str, None, None]":
    """
    Handles getting a response from the Biomni agent using the go_stream method.
    This function is a "generator", which means it can yield responses piece-by-piece.
    """
    if not AGENT_AVAILABLE or agent_instance is None:
        yield "ERROR: The Biomni agent is not available. Please check the application logs for initialization errors."
        return

    try:
        print(f"Passing message to agent: '{message}'")
        
        # --- THE CORRECT CALL TO THE AGENT ---
        # We call the .go_stream() method, which returns a generator.
        final_response = ""
        for chunk in agent_instance.go_stream(message):
            # The agent streams a dictionary; we extract the 'output' key.
            if "output" in chunk and isinstance(chunk["output"], str):
                # The 'output' contains the agent's step-by-step thinking.
                final_response = chunk["output"]
                # Yield the current state of the response to the UI.
                yield final_response

        print(f"Final response from agent: '{final_response}'")

    except Exception as e:
        # If the agent's code fails during execution, show the error.
        print(f"--- ERROR DURING AGENT EXECUTION ---")
        traceback.print_exc()
        print("------------------------------------")
        yield f"An error occurred within the agent: {e}"


def respond(message: str, history: list):
    """
    This is the main function that Gradio's ChatInterface calls.
    It passes the user's message to our logic and streams the response back.
    """
    # 'yield from' is a clean way to pass all the yielded values from 
    # get_biomni_response directly to the Gradio UI.
    yield from get_biomni_response(message)


# --- Step 3: Define the Main Application and UI ---

def main(host: str, port: int):
    """
    Sets up and launches the Gradio user interface.
    """
    # Using gr.ChatInterface provides a polished, modern chatbot look.
    chatbot_ui = gr.ChatInterface(
        fn=respond,
        title="Biomni Agent",
        description="A user-friendly interface for the Biomni agent. Type a message and press Enter to see the agent's thought process and final response.",
        theme="soft",  # A clean, pleasant theme.
        examples=[
            ["What is DESeq2?"], 
            ["Find cell markers for B cells in the immune_human_mouse dataset."],
            ["What datasets are available?"]
        ],
        retry_btn=None,
        undo_btn="Delete Previous",
        clear_btn="Clear Chat",
    )

    # The gr.Blocks context allows for more layout customization if needed later.
    with gr.Blocks(theme="soft", title="Biomni Agent") as demo:
        chatbot_ui.render()

    print(f"Launching Gradio UI on {host}:{port}")
    demo.launch(server_name=host, server_port=port, share=False)


# --- Step 4: Standard Python entry point ---

if __name__ == "__main__":
    # This block runs when the script is executed directly.
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="The host address to run the server on.")
    parser.add_argument(
        "--port",
        type=int,
        # Azure provides the port in an environment variable, so we check for it.
        default=int(os.environ.get("PORT") or os.environ.get("WEBSITES_PORT") or 7860),
        help="The port to run the server on."
    )
    args = parser.parse_args()
    main(args.host, args.port)
