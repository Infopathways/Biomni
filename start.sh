#!/bin/bash
set -e

# Determine port (supports Azure WEBSITES_PORT or PORT env vars)
PORT=${PORT:-${WEBSITES_PORT:-7860}}

# Activate conda environment
source /opt/conda/etc/profile.d/conda.sh
conda activate biomni_e1

echo "Starting Gradio on 0.0.0.0:${PORT}"

# Run the Gradio app. Use exec so container PID 1 is the python process.
exec python -u app/gradio_app.py --host 0.0.0.0 --port ${PORT}
