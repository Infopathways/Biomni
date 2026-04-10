import os
import argparse
import traceback
import gradio as gr

try:
    from biomni.agent.a1 import A1
    print("Initializing Biomni agent on startup...")
    HATZ_API_KEY = os.environ.get("HATZ_API_KEY")
    if not HATZ_API_KEY:
        raise ValueError("CRITICAL ERROR: HATZ_API_KEY not found. This must be set in the Azure Portal Configuration.")

    agent_instance = A1(
        llm='gpt-4-turbo', 
        api_key=os.environ.get("HATZ_API_KEY"),  
        base_url="https://proxy.hatz.ai/v1",
        timeout_seconds=600
    )
    AGENT_AVAILABLE = True
    print("Successfully initialized Biomni agent.")
except Exception as e:
    agent_instance = None
    AGENT_AVAILABLE = False
    print("--- FATAL: FAILED TO INITIALIZE BIOMNI AGENT ON STARTUP ---")
    traceback.print_exc()

def respond(message, history):
    if not AGENT_AVAILABLE or agent_instance is None:
        return "ERROR: The Biomni agent is not available. Please check the application logs for the startup failure reason."
    if not message:
        return "(empty)"
    try:
        final_response = "Agent did not return a response."
        for chunk in agent_instance.go_stream(message):
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
        return final_response
    except Exception as e:
        # Return the error message to be displayed in the chat.
        return f"An error occurred within the agent: {e}"

def main(host: str, port: int):
    theme = gr.themes.Default(
        primary_hue="orange" 
    ).set(
        button_primary_background_fill="#ff8800",
        button_primary_text_color="white"
    )
    
    iface = gr.ChatInterface(
        fn=respond,
        title="Biomni Agent",
        description="A specialized AI agent for biology and genetics research. Ask me about genes, diseases, and proteins.",
        examples=[
            "What genes are associated with Alzheimer's disease?",
            "Show me the protein expression for TP53.",
            "What is the function of the BRCA1 gene?"
        ],
        theme=theme,
        examples=None,
        retry_btn=None, 
        undo_btn=None,  
        clear_btn=None
    )

    iface.queue()

    print(f"Launching Gradio UI on {host}:{port}")
    iface.launch(server_name=host, server_port=port, share=True)

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
