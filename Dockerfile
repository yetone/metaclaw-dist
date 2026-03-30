FROM python:3.12-slim

WORKDIR /app

# Install git for skill installation from GitHub
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies first (layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[all-channels]"

# Copy source
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir -e .

# Create data directories
RUN mkdir -p /data /root/.metaclaw/skills

# Default config and env locations
ENV METACLAW_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["metaclaw", "start"]
