FROM node:20-slim

ARG TZ
ENV TZ="$TZ"

ARG PLAYWRIGHT_VERSION=1.59.1

ARG NPM_MIRROR=https://registry.npmmirror.com
ARG PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple

ARG DEBIAN_FRONTEND=noninteractive

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
  openssh-server \
  fd-find \
  build-essential \
  ccache \
  ripgrep \
  rsync \
  tree \
  locales \
  && npx playwright@${PLAYWRIGHT_VERSION} install-deps chromium \
  && npm cache clean --force \
  && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
  && locale-gen en_US.UTF-8 \
  && update-locale LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8 \
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
RUN mkdir -p /workspace && \
  chown -R node:node /workspace && \
  usermod -s /bin/zsh node

WORKDIR /workspace

ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
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
    # # Install Playwright
    # pnpx playwright@${PLAYWRIGHT_VERSION} install chromium && \
    npm cache clean --force && \
    pnpm store prune

# install opencode via shell
# move opencode install to postCreateCommand and use pnpm cache
# RUN curl -fsSL https://opencode.ai/install | bash

# Install UV of Python env
RUN wget -qO- https://astral.sh/uv/install.sh | sh && \
    echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> ~/.zshrc && \
    echo "export PATH=\"$HOME/.local/bin:\$PATH\"" >> ~/.bashrc && \
    mkdir -p $HOME/.config/uv && \
    echo "[[index]]" > $HOME/.config/uv/uv.toml && \
    echo "url = \"${PYPI_MIRROR}\"" >> $HOME/.config/uv/uv.toml && \
    echo "default = true" >> $HOME/.config/uv/uv.toml

# Install Golang
ARG GO_VERSION=1.26.5
RUN wget -O /tmp/golang.tar.gz https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz && \
    tar -C $HOME/.local -xzf /tmp/golang.tar.gz && \
    rm -f /tmp/golang.tar.gz && \
    echo "export PATH=\"\$PATH\":$HOME/.local/go/bin" >> ~/.zshrc && \
    echo "export PATH=\"\$PATH\":$HOME/.local/go/bin" >> ~/.bashrc && \
    $HOME/.local/go/bin/go env -w GO111MODULE=on && \
    $HOME/.local/go/bin/go env -w GOPROXY=https://goproxy.cn,direct && \
    GOPATH=$HOME/go && \
    $HOME/.local/go/bin/go env -w GOPATH=$GOPATH && \
    echo "export PATH=\"\$PATH\":$GOPATH/bin" >> ~/.zshrc && \
    echo "export PATH=\"\$PATH\":$GOPATH/bin" >> ~/.bashrc

# Copy and set up firewall script / openssh access
COPY init-firewall.sh /usr/local/bin/
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
  && apt-get clean && rm -rf /var/lib/apt/lists/* && \
  # Set zsh as the default shell for the node user and configure sudoers for firewall script
  # Set up firewall script and sudoers for node user
  chmod +x /usr/local/bin/init-firewall.sh && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall
USER node
COPY init-ssh.sh /tmp
COPY start-opencode-web.py /tmp
# ssh
RUN cp /tmp/init-ssh.sh /home/node/.local/bin/init-ssh.sh && \
  chmod +x /home/node/.local/bin/init-ssh.sh && \
  cp /tmp/start-opencode-web.py /home/node/.local/bin/start-opencode-web.py && \
  chmod +x /home/node/.local/bin/start-opencode-web.py && \
  mkdir -p /home/node/.ssh/host_ssh_key && \
  chmod 700 /home/node/.ssh && \
  chmod 700 /home/node/.ssh/host_ssh_key && \
  touch /home/node/.ssh/authorized_keys && \
  chmod 600 /home/node/.ssh/authorized_keys && \
  # vimrc
  echo "set number" > /home/node/.vimrc && \
  echo "set tabstop=4" >> /home/node/.vimrc && \
  echo "set shiftwidth=4" >> /home/node/.vimrc && \
  echo "set expandtab" >> /home/node/.vimrc && \
  echo "set autoindent" >> /home/node/.vimrc && \
  echo "set smartindent" >> /home/node/.vimrc && \
  echo "set cursorline" >> /home/node/.vimrc && \
  echo "set encoding=utf-8" >> /home/node/.vimrc && \
  echo "set fileencoding=utf-8" >> /home/node/.vimrc && \
  echo "syntax on" >> /home/node/.vimrc && \
  echo "set mouse=a" >> /home/node/.vimrc && \
  # uv cache
  mkdir -p /home/node/.cache/uv && \
  # opencode local share / config / cache
  mkdir -p /home/node/.local/share/opencode && \
  mkdir -p ~/.config/opencode && \
  mkdir -p ~/.cache/opencode && \
  # git global config
  git config --global user.name "opencode" && \
  git config --global user.email "dev@opencode.ai" && \
  # geant4 pybind data
  mkdir -p /home/node/.geant4_pybind
