FROM continuumio/miniconda3

WORKDIR /app

# Copy environment file and install conda environment
COPY biomni_env/environment.yml ./environment.yml

SHELL ["/bin/bash", "-lc"]

# Create the conda environment (name comes from environment.yml)
RUN conda env create -f environment.yml || conda env update -n biomni_e1 -f environment.yml

# Ensure conda is initialized for future shells
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> /etc/profile.d/conda.sh

# Copy application files
COPY app ./app
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Expose the default Gradio port
EXPOSE 7860

# Add conda env bin to PATH
ENV PATH /opt/conda/envs/biomni_e1/bin:$PATH

# Default command
CMD ["./start.sh"]
