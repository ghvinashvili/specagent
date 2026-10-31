FROM node:22-bookworm
ARG CLAUDE_CODE_VERSION=2.1.281
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv git sudo iptables ipset bubblewrap socat \
    && rm -rf /var/lib/apt/lists/* \
    && echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/firewall
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
RUN chmod 755 /usr/local/bin/init-firewall.sh
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
RUN pip3 install --no-cache-dir --break-system-packages uv jsonschema pyyaml
RUN mkdir -p /etc/claude-code
COPY managed-settings.json /etc/claude-code/managed-settings.json
COPY managed-claude.md /etc/claude-code/CLAUDE.md
ENV DISABLE_AUTOUPDATER=1
USER node
