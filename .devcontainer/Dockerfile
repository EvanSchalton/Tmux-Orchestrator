FROM mcr.microsoft.com/devcontainers/base:jammy

ARG DEBIAN_FRONTEND=noninteractive
ARG USER=vscode

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y build-essential --no-install-recommends make \
        ca-certificates \
        git \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncurses5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code

# Install tmux and other essential tools
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        tmux \
        ripgrep \
        fd-find \
        jq \
        htop \
        ncdu \
        tree \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python and poetry installation
USER root
RUN apt-get update && apt-get install -y sudo \
    && echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $USER
ARG HOME="/home/$USER"
ARG PYTHON_VERSION=3.11
# ARG PYTHON_VERSION=3.10

ENV PYENV_ROOT="${HOME}/.pyenv"
ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${HOME}/.local/bin:$PATH"

RUN echo "done 0" \
    && curl https://pyenv.run | bash \
    && echo "done 1" \
    && pyenv install ${PYTHON_VERSION} \
    && echo "done 2" \
    && pyenv global ${PYTHON_VERSION} \
    && echo "done 3" \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && poetry config virtualenvs.in-project true

# Configure tmux
COPY --chown=vscode:vscode .devcontainer/tmux.conf /home/vscode/.tmux.conf

# Set up shell aliases
RUN touch /home/vscode/.zshrc \
    && echo 'alias ll="ls -alF"' >> /home/vscode/.zshrc \
    && echo 'alias la="ls -A"' >> /home/vscode/.zshrc \
    && echo 'alias l="ls -CF"' >> /home/vscode/.zshrc \
    && echo 'alias tol="tmux-orc list"' >> /home/vscode/.zshrc \
    && echo 'alias tos="tmux-orc status"' >> /home/vscode/.zshrc \
    && echo 'alias tom="tmux-orc monitor"' >> /home/vscode/.zshrc

# Switch back to root for final setup
USER root

# Create workspace directory and set proper ownership
RUN mkdir -p /workspaces && chown vscode:vscode /workspaces
WORKDIR /workspaces

# Switch back to vscode user for runtime
USER vscode
