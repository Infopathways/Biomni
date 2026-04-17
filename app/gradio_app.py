import os
import argparse
import traceback
import gradio as gr
import sys

STARTUP_ERROR_MESSAGE = None 

try:
    from biomni.agent.a1 import A1
    print("Initializing Biomni agent on startup...")
    HATZ_API_KEY = os.environ.get("HATZ_API_KEY")
    if not HATZ_API_KEY:
        raise ValueError("ERROR: HATZ_API_KEY not found.")

    agent_instance = A1(
        llm='gpt-4-turbo', 
        api_key=HATZ_API_KEY,  
        base_url="https://proxy.hatz.ai/v1",
        timeout_seconds=600
    )
    AGENT_AVAILABLE = True
    print("Successfully initialized Biomni agent.")

except Exception as e:
    STARTUP_ERROR_MESSAGE = traceback.format_exc()
    agent_instance = None
    AGENT_AVAILABLE = False
    print("FAILED TO INITIALIZE BIOMNI AGENT ON STARTUP")
    print(STARTUP_ERROR_MESSAGE)

def respond(message, history):
    if STARTUP_ERROR_MESSAGE:
        return f"ERROR:\n\n{STARTUP_ERROR_MESSAGE}"

    if not AGENT_AVAILABLE or agent_instance is None:
        return "ERROR: The Biomni agent is not available for an unknown reason."
    if not message:
        return "(empty)"
    try:
        final_response = "Agent did not return a response."
        for chunk in agent_instance.go_stream(message):
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
        return final_response
    except Exception as e:
        return f"An error occurred within the agent: {e}"

def main(host: str, port: int):
    theme = gr.themes.Default(primary_hue="orange").set(
        button_primary_background_fill="#ff8800",
        button_primary_background_fill_hover="#e67a00",
        button_primary_text_color="white"
    )
    iface = gr.ChatInterface(
        fn=respond,
        title="Biomni AI Agent",
        description="A specialized AI agent for biology and genetics research. Ask me about genes, diseases, and proteins.",
        theme=theme,
        examples=None, retry_btn=None, undo_btn=None, clear_btn=None
    )
    iface.queue()
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
