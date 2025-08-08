FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Install tmux and other essential tools
# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code

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

# Install Poetry
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry config virtualenvs.in-project true

# Configure tmux
COPY .devcontainer/tmux.conf /home/vscode/.tmux.conf
RUN chown vscode:vscode /home/vscode/.tmux.conf

# Set up shell aliases
RUN echo 'alias ll="ls -alF"' >> /home/vscode/.zshrc \
    && echo 'alias la="ls -A"' >> /home/vscode/.zshrc \
    && echo 'alias l="ls -CF"' >> /home/vscode/.zshrc \
    && echo 'alias tol="tmux-orc list"' >> /home/vscode/.zshrc \
    && echo 'alias tos="tmux-orc status"' >> /home/vscode/.zshrc \
    && echo 'alias tom="tmux-orc monitor"' >> /home/vscode/.zshrc

# Create workspace directory
WORKDIR /workspace