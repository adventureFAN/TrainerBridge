FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        binutils \
        ca-certificates \
        curl \
        desktop-file-utils \
        file \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libfuse2 \
        libgl1 \
        libglib2.0-0 \
        libice6 \
        libnss3 \
        libopengl0 \
        libpython3.10 \
        libsm6 \
        libx11-6 \
        libx11-xcb1 \
        libxcb-cursor0 \
        libxcb-glx0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-shm0 \
        libxcb-sync1 \
        libxcb-util1 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
        libxcb1 \
        libxext6 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        libxrender1 \
        python3 \
        python3-pip \
        python3-venv \
        squashfs-tools \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-build.txt /tmp/requirements-build.txt

RUN python3 -m pip install --no-cache-dir \
        --upgrade \
        pip==26.2 \
        wheel==0.47.0 \
    && python3 -m pip install --no-cache-dir \
        -r /tmp/requirements-build.txt

WORKDIR /workspace

ENTRYPOINT ["/bin/bash", "scripts/build_inside_container.sh"]
