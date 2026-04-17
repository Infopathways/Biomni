import os
import argparse
import traceback
import gradio as gr
import sys
from biomni.agent.a1 import A1

agent_instance = None
AGENT_AVAILABLE = False

def respond(message, history):
    
    if not message:
        return "(empty)"

    try:
        print("Initializing Biomni agent for this request.")
        HATZ_API_KEY = os.environ.get("HATZ_API_KEY")
        if not HATZ_API_KEY:
            raise ValueError("HATZ_API_KEY not found.")

        current_agent = A1(
            llm='gpt-4-turbo', 
            api_key=HATZ_API_KEY,  
            base_url="https://proxy.hatz.ai/v1",
            timeout_seconds=30 
        )
        print("Agent initialized. Calling go_stream.")

        final_response = "Agent did not return a response."
        # Or does it hang here?
        for chunk in current_agent.go_stream(message):
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
        
        print("go_stream finished.")
        return final_response

    except Exception as e:
        print("ERROR DURING REQUEST")
        traceback.print_exc()
        return f"An error occurred: {traceback.format_exc()}"


def main(host: str, port: int):
    theme = gr.themes.Default(
        primary_hue="orange" 
    ).set(
        button_primary_background_fill="#ff8800",
        button_primary_background_fill_hover="#e67a00",
        button_primary_text_color="white"
    )
    
    iface = gr.ChatInterface(
        fn=respond,
        title="Biomni AI Assistant (Debug Mode)",
        description="A specialized AI agent for biology and genetics research. Ask me about genes, diseases, and proteins.",
        theme=theme,
        examples=None,
        retry_btn=None,
        undo_btn=None,
        clear_btn=None
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
