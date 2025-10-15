# summarize.py
# Optional: uses OpenAI API key (OPENAI_API_KEY) to summarize cloud_updates.md
# This script expects OPENAI_API_KEY to be set as an environment variable.

import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    print("No OPENAI_API_KEY set; skipping summary.")
    exit(0)

with open("cloud_updates.md", "r", encoding="utf-8") as f:
    text = f.read()

prompt = (
    "Summarize the following cloud updates. "
    "Produce up to 5 concise bullet points per provider (AWS, Azure, GCP). "
    "Keep each bullet one short sentence.\n\n" + text
)

resp = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=512
)

summary = resp["choices"][0]["message"]["content"].strip()

with open("cloud_updates.md", "w", encoding="utf-8") as f:
    f.write("# 🧭 Cloud Updates Summary\n\n")
    f.write(summary + "\n\n---\n\n")
    f.write(text)

print("Summary added to cloud_updates.md")
