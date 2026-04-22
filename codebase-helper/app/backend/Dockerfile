FROM python:3.12-slim

# claude-agent-sdk (Python) spawns the Claude Code CLI under the hood,
# so we need Node + the CLI in the image. `git` is needed to clone /
# update the Memgraph repos the agent searches through. `ripgrep` powers
# the Grep tool.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg git ripgrep \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# /data/repos is the volume mount point for the cloned Memgraph repos.
RUN mkdir -p /data/repos && useradd -m -u 1000 app && chown -R app:app /app /data
USER app

ENV PORT=8001
ENV REPO_ROOT=/data/repos
EXPOSE 8001

CMD ["python3", "main.py"]
