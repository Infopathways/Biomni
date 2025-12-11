import os
import argparse

import gradio as gr


def respond(text: str) -> str:
    """Simple handler. Attempts to detect if biomni agent can be imported but otherwise echoes."""
    try:
        # Attempt to import the agent to let the UI indicate availability.
        from biomni.agent.a1 import A1  # type: ignore
        agent_available = True
    except Exception:
        agent_available = False

    prefix = "[Agent available] " if agent_available else "[No agent] "
    return prefix + (text or "(empty)")


def main(host: str, port: int):
    iface = gr.Interface(
        fn=respond,
        inputs="text",
        outputs="text",
        title="Biomni Gradio UI",
        description="A minimal Gradio UI for Biomni. Replace respond() with real calls into the agent.",
    )

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
