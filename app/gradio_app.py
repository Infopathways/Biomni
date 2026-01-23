import os
import argparse
import json  # Import the json library

# --- Debugging Setup ---
# We will not try to load the agent at all in this version.
# We will focus ONLY on inspecting the environment.
has_dumped_env = False

# --- Debugging Function ---
def respond(text: str) -> str:
    """
    This is a special debugging handler.
    On the first run, it will dump all environment variables to the UI.
    On subsequent runs, it will just echo.
    """
    global has_dumped_env

    if not has_dumped_env:
        print("--- DUMPING ALL ENVIRONMENT VARIABLES ---")
        
        # Get all environment variables as a dictionary
        all_vars = dict(os.environ)
        
        # Format the dictionary as a nicely indented JSON string
        # This makes it easy to read in the Gradio UI.
        pretty_json_string = json.dumps(all_vars, indent=2, sort_keys=True)
        
        # Set the flag so we don't do this again
        has_dumped_env = True
        
        # Return the full list to the UI
        return pretty_json_string
    else:
        # On subsequent calls, just echo.
        return "Environment has been dumped. Echoing: " + text

# --- The rest of the file is standard UI setup ---
def main(host: str, port: int):
    iface = gr.Interface(
        fn=respond,
        inputs="text",
        outputs="text",
        title="Biomni - Environment Inspector",
        description="Send any message to see all environment variables available to the container.",
    )
    print(f"Launching Gradio UI on {host}:{port}")
    iface.launch(server_name=host, server_port=port, share=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT") or os.environ.get("WEBSITES_PORT") or 7860))
    args = parser.parse_args()
    main(args.host, args.port)
