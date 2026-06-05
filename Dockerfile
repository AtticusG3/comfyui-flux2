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
        g++ \
        git \
        ninja-build \
        pkg-config \
        ca-certificates \
        ffmpeg \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libswscale-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN uv venv /opt/venv

RUN uv pip install --no-cache pip

RUN uv pip install --no-cache \
    torch \
    torchvision \
    torchaudio \
    xformers \
    --index-url https://download.pytorch.org/whl/${CUDA_VERSION}

# av (PyAV), sageattention (SeedVR2), optional flash-attn wheel only (no nvcc in this image).
RUN uv pip install --no-cache packaging wheel setuptools && \
    uv pip install --no-cache av sageattention "cache-dit>=1.2.0" && \
    python -c "import cache_dit; print('[OK] cache-dit available')" && \
    (uv pip install --no-cache --only-binary flash-attn flash-attn && \
        python -c "import flash_attn; print('[OK] flash-attn available')" || \
        echo "[WARN] flash-attn skipped (no prebuilt wheel for torch+cu130); xformers and sageattention are used.")

COPY scripts/lib/. /scripts/lib/
COPY scripts/install_comfyui.sh /scripts/install_comfyui.sh
COPY scripts/packs/. /scripts/packs/

RUN mkdir -p /opt/comfyui-bootstrap && \
    COMFYUI_DIR=/opt/comfyui-bootstrap/ComfyUI \
    CUSTOM_NODES_DIR=/opt/comfyui-bootstrap/ComfyUI/custom_nodes \
    PACKS_DIR=/scripts/packs \
    INSTALL_VRAM_UTILS=true \
    COPY_BUNDLED_WORKFLOWS=false \
    bash /scripts/install_comfyui.sh

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
        build-essential \
        gcc \
        g++ \
        git \
        rsync \
        aria2 \
        jq \
        ffmpeg \
        libgl1 \
        libopengl0 \
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
HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8188/system_stats', timeout=5)" || exit 1

CMD ["bash","/scripts/entrypoint.sh"]
