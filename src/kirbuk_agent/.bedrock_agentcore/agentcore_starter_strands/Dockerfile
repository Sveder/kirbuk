FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

# All environment variables in one layer
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1 \
    AWS_REGION=eu-central-1 \
    AWS_DEFAULT_REGION=eu-central-1 \
    DISPLAY=:99

# Install system dependencies for Playwright and FFmpeg
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    ffmpeg \
    xvfb \
    dbus-x11 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install essential international fonts for proper character rendering
# This fixes Hebrew, Arabic, Japanese, Chinese, Korean and other language support
# Using minimal font set to stay under 1GB image size limit
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-noto-cjk \
    fonts-noto-mono \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

COPY requirements.txt requirements.txt
# Install from requirements file
RUN uv pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium




RUN uv pip install aws-opentelemetry-distro>=0.10.1


# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 9000
EXPOSE 8000
EXPOSE 8080

# Copy entire project (respecting .dockerignore)
COPY . .

# Copy background music from repo root (two levels up from kirbuk_agent/)
COPY ../../audio/bg_music /app/audio/bg_music

# Create startup script to run Xvfb and the application
USER root
RUN echo '#!/bin/bash\n\
# Start Xvfb in the background\n\
Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp -nolisten unix &\n\
XVFB_PID=$!\n\
\n\
# Wait for Xvfb to be ready\n\
sleep 2\n\
\n\
# Start dbus\n\
dbus-daemon --system --fork 2>/dev/null || true\n\
\n\
# Run the application\n\
exec opentelemetry-instrument python -m agentcore_starter_strands\n\
' > /app/start.sh && chmod +x /app/start.sh

USER bedrock_agentcore

# Use the full module path
CMD ["/app/start.sh"]
