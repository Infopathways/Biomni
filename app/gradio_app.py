import os
import argparse
import traceback
import gradio as gr

try:
    from biomni.agent.a1 import A1
    print("Initializing Biomni agent on startup...")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("CRITICAL ERROR: OPENAI_API_KEY not found. This must be set in the Azure Portal Configuration.")
    agent_instance = A1(
        source="OpenAI",
        llm="gpt-4-turbo",
        api_key=OPENAI_API_KEY
    )
    AGENT_AVAILABLE = True
    print("Successfully initialized Biomni agent.")
except Exception as e:
    agent_instance = None
    AGENT_AVAILABLE = False
    print("--- FATAL: FAILED TO INITIALIZE BIOMNI AGENT ON STARTUP ---")
    traceback.print_exc()

def respond(text: str) -> str:
    if not AGENT_AVAILABLE or agent_instance is None:
        return "ERROR: The Biomni agent is not available. Please check the application logs for the startup failure reason."
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
    # This print statement proves the app is starting with the new code.
    print("--- [DIAGNOSTIC CHECK] Application starting with the single-function handler. ---")

    with gr.Blocks(css="style.css") as iface: 
        gr.Markdown("# Biomni Agent")
        gr.Markdown("A specialized AI agent for biology and genetics research. Ask me about genes, diseases, and proteins.")

        chatbot = gr.Chatbot()
        msg = gr.Textbox(label="Your Question")
        clear = gr.ClearButton([msg, chatbot])

        # This single function has diagnostic print statements inside.
        def handle_user_message(user_message, history):
            print(f"--- [DIAGNOSTIC CHECK] handle_user_message function was called. ---")
            print(f"--- [DIAGNOSTIC CHECK] History received by function: {history}")

            history.append([user_message, None])
            bot_response = respond(user_message)
            history[-1][1] = bot_response
            
            print(f"--- [DIAGNOSTIC CHECK] History being returned: {history}")
            return "", history

        msg.submit(handle_user_message, [msg, chatbot], [msg, chatbot])

        gr.Examples(
            examples=[
                "What genes are associated with Alzheimer's disease?",
                "Show me the protein expression for TP53.",
                "What is the function of the BRCA1 gene?"
            ],
            inputs=msg
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
