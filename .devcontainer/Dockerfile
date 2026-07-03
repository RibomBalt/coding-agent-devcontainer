FROM node:20-slim

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest
ARG NPM_MIRROR=https://registry.npmmirror.com
ARG PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple

# Use tuna mirrors for faster package installation in China
COPY ./debian-tuna.sources /tmp/debian.sources

# Install basic development tools and iptables/ipset
RUN apt-get update && apt-get install -y --no-install-recommends \
  apt-transport-https \
  ca-certificates && \
  # update apt sources to tuna mirrors
  mv /tmp/debian.sources /etc/apt/sources.list.d/debian.sources && \
  # install packages
  apt-get update && apt-get install -y --no-install-recommends \
  curl \
  wget \
  less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  gh \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  nano \
  vim \
  python3 \
  python3-pip \
  chromium \
  # npx playwright install-deps chromium --dry-run
   libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libatspi2.0-0t64 libcairo2 libcups2t64 libdbus-1-3 libdrm2 libgbm1 libglib2.0-0t64 libnspr4 libnss3 libpango-1.0-0 libx11-6 libxcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 xvfb fonts-noto-color-emoji fonts-unifont libfontconfig1 libfreetype6 xfonts-scalable fonts-liberation fonts-ipafont-gothic fonts-wqy-zenhei fonts-tlwg-loma-otf fonts-freefont-ttf \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global \
    /usr/local/share/pnpm-global \
    /ms-playwright \
    && chown -R node:node \
    /usr/local/share \
    /ms-playwright

ARG USERNAME=node

# Persist bash history.
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  && mkdir /commandhistory \
  && touch /commandhistory/.bash_history \
  && chown -R $USERNAME /commandhistory

# Set `DEVCONTAINER` environment variable to help with orientation
ENV DEVCONTAINER=true

# Create workspace and config directories and set permissions
RUN mkdir -p /workspace /home/node/.claude && \
  chown -R node:node /workspace /home/node/.claude

WORKDIR /workspace

ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  sudo dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Set up non-root user
USER node

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Set the default shell to zsh rather than sh
ENV SHELL=/bin/zsh

# Set the default editor and visual
ENV EDITOR=vim
ENV VISUAL=vim

# Default powerline10k theme
ARG ZSH_IN_DOCKER_VERSION=1.2.0
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
  -p git \
  -p fzf \
  -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
  -a "source /usr/share/doc/fzf/examples/completion.zsh" \
  -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  -x

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

ENV PNPM_HOME=/usr/local/share/pnpm-global
ENV PATH=$PNPM_HOME:$PATH

# Use NPM registry in China
RUN npm config set registry "${NPM_MIRROR}" && \
    npm install -g pnpm && \
    pnpm config set registry "${NPM_MIRROR}" && \
    # Install Playwright
    npx -y playwright@1.59.1 install chromium

# # install claude code via shell
# RUN curl -fsSL https://claude.ai/install.sh | bash -s stable

# install opencode via shell
RUN curl -fsSL https://opencode.ai/install | bash && \
    mkdir -p ~/.config/opencode

# Install UV of Python env
RUN wget -qO- https://astral.sh/uv/install.sh | sh && \
    echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> ~/.zshrc && \
    echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> ~/.bashrc && \
    "$HOME/.local/bin/uv" python install 3.13 && \
    mkdir -p $HOME/.config/uv && \
    echo "[[index]]" > $HOME/.config/uv/uv.toml && \
    echo "url = \"https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/\"" >> $HOME/.config/uv/uv.toml && \
    echo "default = true" >> $HOME/.config/uv/uv.toml

# Copy and set up firewall script
COPY init-firewall.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/init-firewall.sh && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall
USER node
