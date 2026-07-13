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

    # 2. THE TRANSITION SPLIT: Look for common phrases and cut everything BEFORE and INCLUDING them.
    transition_phrases = r'(Now, I will provide.*?|I will now correct this.*?|Here is the (solution|corrected version|response).*?|Below is the.*?)'
    text = re.sub(r'^[\s\S]*?' + transition_phrases + r':?\s*\n+', '', text, flags=re.IGNORECASE)

    # 3. Remove the "Plan:" outlines and standard preambles
    text = re.sub(r'(?im)^Plan:\s*\n(?:[-*]?\s*.*\n)+', '', text)
    text = re.sub(r'^(The user (is asking|asked|requested)|To explain|To answer|My thinking|Thinking Process|Reasoning)[\s\S]*?\n\n', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 4. General cleanup of leftover headers or conversational filler at the top
    text = re.sub(r'={5,}.*?={5,}\n?', '', text)
    text = re.sub(r'</?solution>', '', text)
    text = re.sub(r'^(I understand|I will now|I will provide|I see you|I will comply|I need to include|I\'ll follow).*?\n', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^\d+\.\s+Ask.*?\n', '', text, flags=re.MULTILINE)
    
    # 5. Remove leaked reasoning about execute/solution tags and XML tags
    text = re.sub(r'(?i)(I realize that I mistakenly used a print statement.*?)(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)(I should provide the response as text inside the execute tag.*?)(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)(it\'?s more appropriate to use the .*? tag.*?)(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'</?execute>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?solution>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?i)^\s*(Since this is a direct response|Instead, I should|I realize that)[\s\S]*?\n\n', '', text)
    
    # 6. Catch the "Now, to align with instructions" pattern and everything before it
    text = re.sub(r'(?is)^[\s\S]*?(now,?\s+to\s+align\s+with\s+the?\s+instructions?,?\s+I\s+will\s+fix\s+that\s+response\s+by\s+including\s+the?\s+required\s+tags?\.?\s*\n+)', '', text)
    
    # 7. Catch "I greeted" / "I responded" / "you greeted" reasoning preamble
    text = re.sub(r'(?is)^[\s\S]*?(I\s+(greeted|responded|replied)|You\s+(greeted|responded|said)|Currently,?\s+you\s+greeted)[\s\S]*?\n\n', '', text)
    
    # 8. Catch "Thank you for pointing that out" / "I will make sure to include my thinking process"
    text = re.sub(r'(?is)^[\s\S]*?(Thank\s+you\s+for\s+pointing\s+that\s+out|I\s+will\s+make\s+sure\s+to\s+include\s+my\s+thinking\s+process|followed\s+by\s+the\s+appropriate\s+tag\s+in\s+every\s+response)[\s\S]*?\n\n', '', text)
    
    # 9. Catch any sentence mentioning "thinking process" or "appropriate tag"
    text = re.sub(r'(?i)^.*?(thinking process|appropriate tag|required tag|execute tag|solution tag).*?\n', '', text, flags=re.MULTILINE)
    
    # 10. Generic catch-all - find the first line that looks like an actual answer
    answer_match = re.search(r'(?m)^(Hello!|Hi!|Hey!|Greetings!|Sure!|Of course!|Absolutely!|Yes,?|No,?|The |A |An |I\s+can|Let\s+me|Here\s+is|Here\s+are|You\'?re\s+welcome|Thank\s+you)', text)
    if answer_match and answer_match.start() > 0:
        text = text[answer_match.start():]
    
    # 11. Remove any remaining XML-style tags
    text = re.sub(r'</?\w+>', '', text, flags=re.IGNORECASE)
    
    # 12. Clean up extra blank lines
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
        
        loading_frames = [
            "Biomni agent is analyzing your request.*",
            "Biomni agent is analyzing your request..*",
            "Biomni agent is analyzing your request...*"
        ]
        step_idx = 0
        
        for chunk in agent_instance.go_stream(message):
            print(f"CHUNK KEYS: {chunk.keys()} | output: {chunk.get('output', '')[:100]}")
            if "output" in chunk and isinstance(chunk["output"], str):
                current_text = chunk["output"]
                final_response = current_text
                all_chunks.append(current_text)
                
                yield loading_frames[step_idx % 3]
                step_idx += 1
        
        for c in reversed(all_chunks):
            if c.strip():
                final_response = c
                break

        cleaned_text = clean_response(final_response)
        yield cleaned_text

    except Exception as e:
        print("\nERROR DURING AGENT REQUEST")
        traceback.print_exc()
        yield f"An error occurred within the agent:\n\n{traceback.format_exc()}"

def main(host: str, port: int):
    theme = gr.themes.Default(
        primary_hue="orange",
        font=[gr.themes.GoogleFont("Montserrat"), "sans-serif"],
    ).set(
        button_primary_background_fill="#ff8800",
        button_primary_background_fill_hover="#3662d4",
        button_primary_text_color="white",
        # Force title color in the theme itself
        block_title_text_color="#ff8800",
        block_label_text_color="#ff8800",
    )

    css_content = """
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');

    :root {
        --primary-accent: #ff8800;
        --secondary-accent: #3662d4;
        --background-primary: #f1f4f9;
        --background-card: #ffffff;
        --text-primary: #4b4b4b;
        --text-on-accent: #ffffff;
        --border-color: #e2e8f0;
        --user-bubble-bg: rgba(255, 136, 0, 0.12);
        --stop-red: #e53e3e;
    }

    gradio-app, .gradio-container {
        background-color: var(--background-primary) !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    .gradio-container .main-title-wrap,
    .gradio-container .main-title,
    .gradio-container h1,
    .gradio-container .main-title h1,
    #component-0 h1,
    .wrap h1 {
        color: #ff8800 !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        text-align: center !important;
    }

    .gradio-container .main-title::before {
        content: "";
        display: block;
        width: 80px;
        height: 80px;
        margin-bottom: 15px;
        background-image: url("https://48131155.fs1.hubspotusercontent-na1.net/hubfs/48131155/grey%20logo%20europa.png");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }

    .gradio-container .description {
        color: #8a8a8a !important;
        font-size: 0.95rem !important;
        text-align: center !important;
    }

    [data-testid="user"] {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    [data-testid="user"] .message-bubble,
    [data-testid="user"] .message,
    [data-testid="user"] .chatbot-user-message {
        background-color: var(--user-bubble-bg) !important;
        color: var(--text-primary) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 136, 0, 0.25) !important;
    }
    [data-testid="user"] .message-bubble p,
    [data-testid="user"] .message-bubble span,
    [data-testid="user"] .message-bubble div {
        color: var(--text-primary) !important;
    }

    [data-testid="assistant"] {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    [data-testid="assistant"] .message-bubble,
    [data-testid="assistant"] .message,
    [data-testid="assistant"] .chatbot-bot-message {
        background-color: var(--background-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
    }
    [data-testid="assistant"] .message-bubble p,
    [data-testid="assistant"] .message-bubble span,
    [data-testid="assistant"] .message-bubble div {
        color: var(--text-primary) !important;
    }

    button.primary {
        background-color: var(--primary-accent) !important;
        color: var(--text-on-accent) !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        transition: background-color 0.2s ease, transform 0.1s ease !important;
    }
    button.primary:hover {
        background-color: var(--secondary-accent) !important;
        color: var(--text-on-accent) !important;
    }
    button.primary:active {
        transform: scale(0.97) !important;
    }

    .stop-button,
    button.stop,
    [data-testid="stop-button"],
    .gradio-button.stop,
    button[aria-label="Stop"] {
        background-color: #e53e3e !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s ease !important;
    }
    .stop-button:hover,
    button.stop:hover,
    [data-testid="stop-button"]:hover,
    .gradio-button.stop:hover,
    button[aria-label="Stop"]:hover {
        background-color: #c53030 !important;
    }

    .gradio-textbox textarea {
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        background-color: var(--background-card) !important;
        color: var(--text-primary) !important;
        font-size: 0.95rem !important;
    }
    .gradio-textbox textarea:focus {
        border-color: var(--primary-accent) !important;
        box-shadow: 0 0 0 2px rgba(255, 136, 0, 0.2) !important;
    }

    .prose {
        color: var(--text-primary) !important;
    }
    .prose h1, .prose h2, .prose h3 {
        color: var(--secondary-accent) !important;
    }
    .prose a {
        color: var(--secondary-accent) !important;
    }
    .prose a:hover {
        color: var(--primary-accent) !important;
    }
    .prose p {
        color: var(--text-primary) !important;
    }

    .prose pre {
        background-color: #2d2d2d !important;
        border-radius: 10px !important;
    }
    .prose code {
        color: var(--primary-accent) !important;
    }

    footer {
        display: none !important;
    }
    """

    iface = gr.ChatInterface(
        fn=respond,
        title="Biomni AI Agent",
        description="A specialized AI agent for biology and genetics research. Ask me about genes, diseases, and proteins.",
        theme=theme,
        css=css_content,
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
