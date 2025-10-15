# cloud_updates.py
# Fetch latest AWS, Azure, GCP RSS and generate cloud_updates.md

import feedparser
from datetime import datetime

FEEDS = {
    "AWS": "https://aws.amazon.com/new/feed/",
    "Azure": "https://azurecomcdn.azureedge.net/en-us/updates/feed/",
    "GCP": "https://cloud.google.com/blog/topics/announcements/feed"
}

def fetch_updates(max_per_feed=5):
    sections = []
    for name, url in FEEDS.items():
        feed = feedparser.parse(url)
        sections.append(f"# {name} Updates\n")
        for e in feed.entries[:max_per_feed]:
            title = e.get("title", "").replace("\n", " ")
            link = e.get("link", "")
            date = e.get("published", e.get("updated", "N/A"))
            summary = e.get("summary", "").strip()
            sections.append(f"### {title}\n📅 {date}\n🔗 {link}\n\n{summary}\n\n---\n")
    return sections

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    header = [f"# ☁️ Cloud Updates — {now}\n",
              "Automatically generated from AWS, Azure, and GCP feeds.\n",
              "---\n"]
    content = header + fetch_updates()
    with open("cloud_updates.md", "w", encoding="utf-8") as f:
        f.write("\n".join(content))

if __name__ == "__main__":
    main()
