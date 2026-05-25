#!/usr/bin/env bash
# Symlink every skill in this directory into .claude/skills/ so Claude Code
# discovers them as slash commands (e.g. /add-best-practice).
#
# Run from the repo root:  ./skills/install.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
SKILLS_DST="$REPO_ROOT/.claude/skills"

mkdir -p "$SKILLS_DST"

for skill in "$SKILLS_SRC"/*/; do
  name="$(basename "$skill")"
  ln -sfn "../../skills/$name" "$SKILLS_DST/$name"
  echo "linked: .claude/skills/$name -> skills/$name"
done
