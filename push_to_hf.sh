#!/usr/bin/env bash
# Push current main to HuggingFace Space, injecting the required YAML
# frontmatter into README.md only for that commit (reverted immediately after).
set -euo pipefail

HF_FRONTMATTER='---
title: PhdScout
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.25.0"
app_file: app.py
pinned: false
license: mit
---

'

# 1. Prepend frontmatter to README
printf '%s' "$HF_FRONTMATTER" | cat - README.md > README.hf.tmp
mv README.hf.tmp README.md

# 2. Create a temporary commit
git add README.md
git commit -q -m "chore: add HF frontmatter [skip ci]"

# 3. Push to HuggingFace Space
git push space main

# 4. Undo the temporary commit, restore README
git reset --soft HEAD~1
git checkout README.md

echo "Done — HF Space updated, local README unchanged."
