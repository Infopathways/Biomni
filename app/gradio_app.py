import os
import argparse
import traceback
import gradio as gr

# This block runs once when the application starts.
try:
    from biomni.agent.a1 import A1
    print("Initializing Biomni agent on startup...")

    # Attempt to read the API key from the environment.
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("CRITICAL ERROR: OPENAI_API_KEY not found. This must be set in the Azure Portal Configuration.")

    # If the key is found, attempt to configure the agent.
    agent_instance = A1(
        source="OpenAI",
        llm="gpt-4-turbo",
        api_key=OPENAI_API_KEY
    )
    AGENT_AVAILABLE = True
    print("Successfully initialized Biomni agent.")

except Exception as e:
    # If any part of the above fails, set the agent to unavailable and log the real error.
    agent_instance = None
    AGENT_AVAILABLE = False
    print("--- FATAL: FAILED TO INITIALIZE BIOMNI AGENT ON STARTUP ---")
    traceback.print_exc()


def respond(text: str) -> str:
    """
    This handler checks if the agent was successfully loaded during startup.
    If not, it returns a standard error message.
    """
    # First, check if the agent loaded correctly.
    if not AGENT_AVAILABLE or agent_instance is None:
        return "ERROR: The Biomni agent is not available. Please check the application logs for the startup failure reason."

    # If the agent is available, proceed.
    if not text:
        return "(empty)"
    try:
        final_response = "Agent did not return a response."
        for chunk in agent_instance.go_stream(text):
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
        return final_response
    except Exception as e:
        return f"An error occurred within the agent: {e}"

def main(host: str, port: int):
    iface = gr.Interface(
        fn=respond,
        inputs="text",
        outputs="text",
        title="Biomni Agent",
        description="Chat with Biomni",
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
