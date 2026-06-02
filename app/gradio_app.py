import os
import argparse
import traceback
import gradio as gr
import sys
import socket
import re

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

STARTUP_ERROR_MESSAGE = None
try:
    from biomni.agent.a1 import A1
    import openai

    print("Initializing Biomni agent on startup...")
    HATZ_API_KEY = os.environ.get("HATZ_API_KEY")
    if not HATZ_API_KEY:
        raise ValueError("ERROR: HATZ_API_KEY not found.")

    original_init = openai.OpenAI.__init__
    def patched_init(self, *args, **kwargs):
        existing = kwargs.get("default_headers") or {}
        existing["X-API-Key"] = HATZ_API_KEY
        kwargs["default_headers"] = existing
        original_init(self, *args, **kwargs)
    openai.OpenAI.__init__ = patched_init

    agent_instance = A1(
        llm='gpt-4.1-mini',
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

def clean_response(text):
    escaped_message = re.escape(original_message)
    text = re.sub(r'^\s*' + escaped_message, '', text, flags=re.IGNORECASE)

    # Delete the leaked backend instruction.
    text = re.sub(r'Each response must include thinking process.*?\n', '', text, flags=re.DOTALL)

    # Delete the "Thinking Process" paragraph in its various forms.
    text = re.sub(r'^(The user asked|To explain|To answer|My thinking|Thinking Process|Reasoning)[\s\S]*?\n\n', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # If there are multiple paragraphs/sections, take only the last meaningful one
    # Remove AI message headers
    text = re.sub(r'={5,}.*?={5,}\n?', '', text)
    # Remove tag wrappers
    text = re.sub(r'</?solution>', '', text)
    # Remove thinking/reasoning preambles - match until double newline
    text = re.sub(r'^(My thinking|Thinking Process|Reasoning|I understand the instruction[^:]*):.*?\n\n', '', text, flags=re.DOTALL | re.MULTILINE)
    # Remove lines that start with "I understand" or "I see you"
    text = re.sub(r'^(I understand|I see you|I will comply|I need to include|I\'ll follow).*?\n', '', text, flags=re.MULTILINE)
    # Remove numbered preamble lines like "1. Ask what biomedical..."
    text = re.sub(r'^\d+\.\s+Ask.*?\n', '', text, flags=re.MULTILINE)
    # Clean up extra blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def respond(message, history):
    if STARTUP_ERROR_MESSAGE:
        return f"ERROR:\n\n{STARTUP_ERROR_MESSAGE}"
    if not AGENT_AVAILABLE or agent_instance is None:
        return "ERROR: The Biomni agent is not available for an unknown reason."
    if not message:
        return "(empty)"
     try:
        final_response = "Agent did not return a response."
        all_chunks = []
        for chunk in agent_instance.go_stream(message):
            print(f"CHUNK KEYS: {chunk.keys()} | output: {chunk.get('output', '')[:100]}")
            if "output" in chunk and isinstance(chunk["output"], str):
                final_response = chunk["output"]
                all_chunks.append(chunk["output"])
        
        # Use the last non-empty chunk output as it's most likely the final answer
        for c in reversed(all_chunks):
            if c.strip():
                final_response = c
                break

        final_response = clean_response(final_response, message)
        return final_response
    except Exception as e:
        print("\nERROR DURING AGENT REQUEST")
        traceback.print_exc()
        return f"An error occurred within the agent:\n\n{traceback.format_exc()}"

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
