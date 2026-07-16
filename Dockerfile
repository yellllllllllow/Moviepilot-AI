# ============================================================
# Stage 1: 构建前端
# ============================================================
FROM node:20-bookworm AS build_frontend

WORKDIR /frontend

# 复制依赖配置并安装
COPY frontend/package.json frontend/yarn.lock* ./
RUN yarn install --frozen-lockfile || yarn install

# 复制前端源码并构建
COPY frontend/ .
RUN yarn build:icons && yarn build

# ============================================================
# Stage 2: Python基础镜像
# ============================================================
FROM python:3.12.13-slim-bookworm AS base

ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    HOME="/moviepilot" \
    CONFIG_DIR="/config" \
    TERM="xterm" \
    DISPLAY=:987 \
    PUID=0 \
    PGID=0 \
    UMASK=000 \
    VENV_PATH="/opt/venv"

ENV PATH="${VENV_PATH}/bin:${PATH}"

# 安装系统工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    gettext-base \
    locales \
    procps \
    gosu \
    bash \
    ca-certificates \
    curl \
    wget \
    git \
    gh \
    busybox \
    tini \
    cron \
    jq \
    ripgrep \
    less \
    unzip \
    fuse3 \
    rsync \
    openssh-client \
    iproute2 \
    netcat-openbsd \
    lsof \
    nano \
    unar \
    libjemalloc2 \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && curl https://rclone.org/install.sh | bash \
    && ln -s /usr/lib/*-linux-gnu/libjemalloc.so.2 /usr/local/lib/libjemalloc.so \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf \
    /tmp/* \
    /var/lib/apt/lists/* \
    /var/tmp/*

# ============================================================
# Stage 3: 构建 Python 虚拟环境
# ============================================================
FROM base AS prepare_venv

ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    VENV_PATH="/opt/venv"

ENV PATH="${VENV_PATH}/bin:${PATH}"

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    busybox \
    jq \
    wget

# 安装 Python 依赖
WORKDIR /app
COPY backend/requirements.in requirements.in
COPY backend/scripts/uv-pip-compat.sh /usr/local/bin/uv-pip-compat
RUN python3 -m venv ${VENV_PATH} \
    && env UV_INSTALL_DIR=/usr/local/bin sh -c "$(curl -LsSf https://astral.sh/uv/install.sh)" \
    && chmod +x /usr/local/bin/uv-pip-compat \
    && ln -sf /usr/local/bin/uv ${VENV_PATH}/bin/uv \
    && ln -sf /usr/local/bin/uv-pip-compat ${VENV_PATH}/bin/pip \
    && ln -sf /usr/local/bin/uv-pip-compat ${VENV_PATH}/bin/pip3 \
    && ln -sf /usr/local/bin/uv-pip-compat ${VENV_PATH}/bin/pip3.12 \
    && ln -sf /usr/local/bin/uv-pip-compat ${VENV_PATH}/bin/pip-compile \
    && ln -sf /usr/local/bin/uv-pip-compat ${VENV_PATH}/bin/pip-sync \
    && pip-compile requirements.in -o requirements.txt \
    && pip install -r requirements.txt

# ============================================================
# Stage 4: 准备运行代码
# ============================================================
FROM base AS prepare_code

WORKDIR /app

# 复制后端代码
COPY backend/ .

# 复制前端构建产物（从 Stage 1）
COPY --from=build_frontend /frontend/dist /public

# 安装插件（可选，扩展功能）
RUN curl -sL "https://github.com/jxxghp/MoviePilot-Plugins/archive/refs/heads/main.zip" | busybox unzip -d /tmp - 2>/dev/null || true \
    && if [ -d "/tmp/MoviePilot-Plugins-main" ]; then \
        mv -f /tmp/MoviePilot-Plugins-main/plugins.v2/* /app/app/plugins/ 2>/dev/null || true; \
        cat /tmp/MoviePilot-Plugins-main/package.json 2>/dev/null | jq -r 'to_entries[] | select(.value.v2 == true) | .key' | awk '{print tolower($0)}' | \
        while read -r i; do if [ ! -d "/app/app/plugins/$i" ]; then mv "/tmp/MoviePilot-Plugins-main/plugins/$i" "/app/app/plugins/" 2>/dev/null || true; else echo "跳过 $i"; fi; done || true; \
    fi \
    && curl -sL "https://raw.githubusercontent.com/jxxghp/MoviePilot-Resources/main/resources.v2/user.sites.v2.bin" -o /app/app/helper/user.sites.v2.bin 2>/dev/null || true

# ============================================================
# Stage 5: 最终镜像
# ============================================================
FROM base AS final

ENV LD_PRELOAD="/usr/local/lib/libjemalloc.so" \
    MOVIEPILOT_DOCKER_KEEPALIVE_ON_FAILURE="true"

# ffmpeg
COPY --from=mwader/static-ffmpeg:8.1.1 /ffmpeg /usr/local/bin/
COPY --from=mwader/static-ffmpeg:8.1.1 /ffprobe /usr/local/bin/

# Python 环境
COPY --from=prepare_venv --chmod=777 ${VENV_PATH} ${VENV_PATH}
COPY --from=prepare_venv /usr/local/bin/uv /usr/local/bin/uv
COPY --from=prepare_venv /usr/local/bin/uv-pip-compat /usr/local/bin/uv-pip-compat

# 浏览器运行依赖
RUN playwright install-deps chromium \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf \
    /tmp/* \
    /var/lib/apt/lists/* \
    /var/tmp/*

# 配置运行代码
WORKDIR /app

COPY --from=prepare_code /app /app
COPY --from=prepare_code /public /public

RUN cp -f /app/docker/nginx.common.conf /etc/nginx/common.conf \
    && cp -f /app/docker/nginx.template.conf /etc/nginx/nginx.template.conf \
    && cp -f /app/docker/update.sh /usr/local/bin/mp_update.sh \
    && cp -f /app/docker/entrypoint.sh /entrypoint.sh \
    && cp -f /app/docker/docker_http_proxy.conf /etc/nginx/docker_http_proxy.conf \
    && printf '%s\n' '#!/usr/bin/env bash' 'set -euo pipefail' 'cd /app' 'exec "${VENV_PATH:-/opt/venv}/bin/python3" -m app.cli "$@"' > /usr/local/bin/moviepilot \
    && chmod +x /entrypoint.sh /usr/local/bin/mp_update.sh /usr/local/bin/moviepilot \
    && mkdir -p ${HOME} \
    && groupadd -r moviepilot -g 918 \
    && useradd -r moviepilot -g moviepilot -d ${HOME} -s /bin/bash -u 918 \
    && python_ver=$(python3 -V | awk '{print $2}') \
    && echo "/app/" > ${VENV_PATH}/lib/python${python_ver%.*}/site-packages/app.pth \
    && echo 'fs.inotify.max_user_watches=5242880' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=5242880' >> /etc/sysctl.conf \
    && echo "zh_CN.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen zh_CN.UTF-8

EXPOSE 3000
VOLUME [ "${CONFIG_DIR}" ]
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD curl -fsS "http://127.0.0.1:${PORT:-3001}/api/v1/system/global?token=moviepilot" >/dev/null || exit 1
ENTRYPOINT [ "/usr/bin/tini", "-g", "--", "/entrypoint.sh" ]
