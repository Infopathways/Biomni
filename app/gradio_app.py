import os
import argparse
import traceback
import gradio as gr
import sys
import socket

# Force correct OpenAI client settings before any imports
os.environ["OPENAI_API_TYPE"] = "openai"
os.environ["OPENAI_API_BASE"] = "https://ai.hatz.ai/v1"
os.environ["OPENAI_BASE_URL"] = "https://ai.hatz.ai/v1"

# === DNS DIAGNOSTIC ===
print("=== DNS DIAGNOSTIC ===")
try:
    result = socket.getaddrinfo("ai.hatz.ai", 443)
    print(f"DNS OK: ai.hatz.ai resolves to {result[0][4][0]}")
except Exception as e:
    print(f"DNS FAILED: {e}")

print(f"OPENAI_API_BASE: {os.getenv('OPENAI_API_BASE')}")
print(f"OPENAI_API_TYPE: {os.getenv('OPENAI_API_TYPE')}")

try:
    import urllib.request
    urllib.request.urlopen("https://ai.hatz.ai/v1", timeout=5)
    print("HTTP CONNECT OK: ai.hatz.ai is reachable")
except Exception as e:
    print(f"HTTP CONNECT FAILED: {e}")

print("=== END DIAGNOSTIC ===")
# === END DNS DIAGNOSTIC ===

STARTUP_ERROR_MESSAGE = None
try:
    from biomni.agent.a1 import A1
    import openai

    print("Initializing Biomni agent on startup...")
    HATZ_API_KEY = os.environ.get("HATZ_API_KEY")
    if not HATZ_API_KEY:
        raise ValueError("ERROR: HATZ_API_KEY not found.")

    # Patch the OpenAI client to use X-API-Key header
    original_init = openai.OpenAI.__init__
    def patched_init(self, *args, **kwargs):
        existing = kwargs.get("default_headers") or {}
        existing["X-API-Key"] = HATZ_API_KEY
        kwargs["default_headers"] = existing
        original_init(self, *args, **kwargs)
    openai.OpenAI.__init__ = patched_init

    agent_instance = A1(
        llm='gpt-4o',
        api_key=HATZ_API_KEY,
        base_url="https://ai.hatz.ai/v1",
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
        print("\nERROR DURING AGENT REQUEST")
        traceback.print_exc()
        detailed_error_message = traceback.format_exc()
        return f"An error occurred within the agent:\n\n{detailed_error_message}"

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
