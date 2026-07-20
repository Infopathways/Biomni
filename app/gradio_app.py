import os
import argparse
import traceback
import gradio as gr
import sys
import socket
import re

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
AGENT_AVAILABLE = False
agent_instance = None
HATZ_API_KEY = None  # Will be set below

try:
    from biomni.agent.a1 import A1
    import openai

    print("Preparing Biomni agent setup...")
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

    AGENT_AVAILABLE = True
    print("Biomni agent ready for lazy initialization.")
except Exception as e:
    STARTUP_ERROR_MESSAGE = traceback.format_exc()
    agent_instance = None
    AGENT_AVAILABLE = False
    print("FAILED TO PREPARE BIOMNI AGENT")
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
    
    # 4. General cleanup
    text = re.sub(r'={5,}.*?={5,}\n?', '', text)
    text = re.sub(r'</?solution>', '', text)
    text = re.sub(r'^(I understand|I will now|I will provide|I see you|I will comply|I need to include|I\'ll follow).*?\n', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^\d+\.\s+Ask.*?\n', '', text, flags=re.MULTILINE)
    
    # 5. Remove leaked reasoning
    text = re.sub(r'(?i)(I realize that I mistakenly used a print statement.*?)(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)(I should provide the response as text inside the execute tag.*?)(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)(it\'?s more appropriate to use the .*? tag.*?)(?=\n\n|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'</?execute>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</?solution>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?i)^\s*(Since this is a direct response|Instead, I should|I realize that)[\s\S]*?\n\n', '', text)
    
    # 6-11dd. Additional cleanup patterns (simplified for brevity - keep your existing ones)
    text = re.sub(r'</?\w+>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def respond(message, history):
    global agent_instance

    if STARTUP_ERROR_MESSAGE:
        yield f"ERROR:\n\n{STARTUP_ERROR_MESSAGE}"
        return

    if not AGENT_AVAILABLE:
        yield "ERROR: The Biomni agent is not available for an unknown reason."
        return

    if not message:
        yield "(empty)"
        return

    if agent_instance is None:
        try:
            yield "Initializing the Biomni agent and downloading the data lake... This may take a few minutes."
            agent_instance = A1(
                llm='gpt-4.1-mini',
                api_key=HATZ_API_KEY,
                base_url="https://ai.hatz.ai/v1",
                timeout_seconds=600,
                use_tool_retriever=True,
                path="./data"
            )
            yield "Agent initialized! Processing your request..."
        except Exception as e:
            yield f"Failed to initialize the Biomni agent:\n\n{traceback.format_exc()}"
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
    }

    gradio-app, .gradio-container {
        background-color: var(--background-primary) !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Hide default Gradio title */
    .gradio-container h1, .wrap h1, #component-0 h1 { display: none !important; }

    /* Custom header */
    .custom-header {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 15px !important;
        margin-bottom: 10px !important;
    }
    .custom-header img { width: 60px !important; height: 60px !important; }
    .custom-header h1 {
        color: #ff8800 !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        margin: 0 !important;
    }
    .gradio-container .description {
        color: #8a8a8a !important;
        font-size: 0.95rem !important;
        text-align: center !important;
        margin-bottom: 20px !important;
    }

    /* Chat bubbles */
    [data-testid="user"] .message-bubble {
        background-color: var(--user-bubble-bg) !important;
        color: var(--text-primary) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 136, 0, 0.25) !important;
        position: relative !important;
    }
    [data-testid="assistant"] .message-bubble {
        background-color: var(--background-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        position: relative !important;
    }

    button.primary {
        background-color: var(--primary-accent) !important;
        color: var(--text-on-accent) !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
    }
    button.primary:hover {
        background-color: var(--secondary-accent) !important;
    }

    .gradio-textbox textarea {
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        background-color: var(--background-card) !important;
    }

    footer { display: none !important; }

    /* Copy button */
    .copy-btn {
        position: absolute !important;
        top: 8px !important;
        right: 8px !important;
        background: rgba(255, 136, 0, 0.9) !important;
        border: none !important;
        border-radius: 4px !important;
        cursor: pointer !important;
        opacity: 0.8 !important;
        font-size: 11px !important;
        padding: 3px 8px !important;
        z-index: 100 !important;
        color: white !important;
    }
    .copy-btn:hover {
        opacity: 1 !important;
        background: #ff8800 !important;
    }
    """

    js_content = """
    function addCopyButtons() {
        document.querySelectorAll('[data-testid="user"] .message-bubble, [data-testid="assistant"] .message-bubble').forEach(msg => {
            if (msg.querySelector('.copy-btn')) return;
            const btn = document.createElement('button');
            btn.innerHTML = '📋 Copy';
            btn.className = 'copy-btn';
            btn.type = 'button';
            btn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                navigator.clipboard.writeText(msg.innerText).then(() => {
                    btn.innerHTML = '✓ Done';
                    setTimeout(() => btn.innerHTML = '📋 Copy', 1500);
                });
            };
            msg.appendChild(btn);
        });
    }
    new MutationObserver(addCopyButtons).observe(document.body, { childList: true, subtree: true });
    addCopyButtons();
    """

    with gr.Blocks(theme=theme, css=css_content, js=js_content, title="Biomni AI Agent") as demo:
        gr.HTML('<div class="custom-header"><img src="https://48131155.fs1.hubspotusercontent-na1.net/hubfs/48131155/grey%20logo%20europa.png" /><h1>Biomni AI Agent</h1></div>')
        gr.Markdown("A specialized AI agent for biology and genetics research. Ask me about genes, diseases, and proteins.")

        chatbot = gr.Chatbot(label="Chat", bubble_full_width=False)

        with gr.Row():
            msg = gr.Textbox(placeholder="Ask about genes, diseases, proteins...", lines=1, scale=9, show_label=False)
            submit_btn = gr.Button("Send", variant="primary", scale=1)

        gr.ClearButton([msg, chatbot], value="Clear Chat")

        def user(user_message, history):
            return "", history + [[user_message, None]]

        def bot(history):
            for h in respond(history[-1][0], history[:-1]):
                history[-1][1] = h
                yield history

        msg.submit(fn=user, inputs=[msg, chatbot], outputs=[msg, chatbot], queue=False).then(fn=bot, inputs=chatbot, outputs=chatbot, queue=True)
        submit_btn.click(fn=user, inputs=[msg, chatbot], outputs=[msg, chatbot], queue=False).then(fn=bot, inputs=chatbot, outputs=chatbot, queue=True)

    demo.queue()
    print(f"Launching Gradio UI on {host}:{port}")
    demo.launch(server_name=host, server_port=port, share=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT") or os.environ.get("WEBSITES_PORT") or 7860))
    args = parser.parse_args()
    main(args.host, args.port)
