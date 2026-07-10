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
    # 1. Delete the leaked backend instruction.
    text = re.sub(r'Each response must include thinking process.*?\n', '', text, flags=re.DOTALL)

    # 2. THE TRANSITION SPLIT: Look for common phrases the agent uses right before the real answer.
    # If it finds one of these, it throws away everything before it.
    transition_regex = r'(Now, I will provide.*?|I will now correct this.*?|Here is the solution:)\s*\n+'
    parts = re.split(transition_regex, text, flags=re.IGNORECASE)
    if len(parts) > 1:
        # If the split worked, the actual answer is the last part of the list.
        text = parts[-1]

    # 3. Remove the new "Plan:" outlines
    text = re.sub(r'(?im)^Plan:\s*\n(?:[-*]?\s*.*\n)+', '', text)

    # 4. Remove standard preambles
    text = re.sub(r'^(The user (is asking|asked|requested)|To explain|To answer|My thinking|Thinking Process|Reasoning)[\s\S]*?\n\n', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 5. General cleanup
    text = re.sub(r'={5,}.*?={5,}\n?', '', text)
    text = re.sub(r'</?solution>', '', text)
    text = re.sub(r'^(I understand|I will now|I will provide|I see you|I will comply|I need to include|I\'ll follow).*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+Ask.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def respond(message, history):
    if STARTUP_ERROR_MESSAGE:
        yield f"ERROR:\n\n{STARTUP_ERROR_MESSAGE}"
        return
    if not AGENT_AVAILABLE or agent_instance is None:
        yield "ERROR: The Biomni agent is not available for an unknown reason."
        return
    if not message:
        yield "(empty)"
        return
        
    try:
        final_response = "Agent did not return a response."
        all_chunks = []
        
        # STREAMING PHASE: Show the raw text subtly so you know it's working
        for chunk in agent_instance.go_stream(message):
            print(f"CHUNK KEYS: {chunk.keys()} | output: {chunk.get('output', '')[:100]}")
            if "output" in chunk and isinstance(chunk["output"], str):
                current_text = chunk["output"]
                final_response = current_text
                all_chunks.append(current_text)
                
                # Yield the intermediate text formatted subtly
                yield f"Biomni agent is thinking..._\n\n---\n\n_{current_text}_"
        
        # Use the last non-empty chunk output as it's most likely the final answer
        for c in reversed(all_chunks):
            if c.strip():
                final_response = c
                break

        # CLEANUP PHASE: Run our aggressive cleaner on the complete text
        cleaned_text = clean_response(final_response)

        # FINAL YIELD: Overwrite the "thinking" text with the final, clean answer
        yield cleaned_text

    except Exception as e:
        print("\nERROR DURING AGENT REQUEST")
        traceback.print_exc()
        yield f"An error occurred within the agent:\n\n{traceback.format_exc()}"

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
