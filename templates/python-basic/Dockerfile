FROM python:3.11-slim

# Install dependencies before copying code so Docker can cache this layer.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source.
COPY agent.py .

# Create the writable output directory declared in enclaiv.yaml.
RUN mkdir -p /app/output

# Run as an unprivileged user — Enclaiv's entrypoint wrapper also drops
# privileges, but defence-in-depth starts here.
RUN useradd --create-home --shell /bin/sh agent
USER agent

CMD ["python3", "/app/agent.py"]
