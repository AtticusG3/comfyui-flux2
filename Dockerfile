# =============================================================================
# Stage 1: builder -- compile C extensions, then discard compilers
# =============================================================================
FROM python:3.12-slim-trixie AS builder

ARG CUDA_VERSION=cu130

ENV DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN uv venv /opt/venv

RUN uv pip install --no-cache \
    torch \
    torchvision \
    torchaudio \
    xformers \
    --index-url https://download.pytorch.org/whl/${CUDA_VERSION}

# =============================================================================
# Stage 2: runtime -- lean image with only what's needed at run time
# =============================================================================
FROM python:3.12-slim-trixie

ARG CUDA_VERSION=cu130

ENV DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    CLI_ARGS=""

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        aria2 \
        jq \
        libgl1 \
        libglib2.0-0 \
        fonts-dejavu-core \
        sudo \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN useradd -m -d /app -s /bin/bash runner && \
    mkdir -p /app /scripts /workflows /opt/venv && \
    chown -R runner:runner /app /scripts /workflows /opt/venv && \
    echo "runner ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/runner && \
    chmod 0440 /etc/sudoers.d/runner

COPY --from=builder --chown=runner:runner /opt/venv /opt/venv

WORKDIR /app
USER runner

COPY --chown=runner:runner scripts/. /scripts/
COPY --chown=runner:runner workflows/. /workflows/

EXPOSE 8188
CMD ["bash","/scripts/entrypoint.sh"]
