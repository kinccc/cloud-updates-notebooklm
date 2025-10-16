# cloud_updates.py
# Fetch latest AWS, Azure, GCP RSS and generate cloud_updates.md

import feedparser
from datetime import datetime

FEEDS = {
    "AWS": [
        "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
    ],
    "Azure": [
        "https://www.microsoft.com/releasecommunications/api/v2/azure/rss",
        "https://azurecomcdn.azureedge.net/en-us/updates/feed/",
        "https://azure.microsoft.com/en-us/updates/feed/"  # backup URL
    ],
    "GCP": [
        "https://cloud.google.com/feeds/announcements.xml",
        "https://status.cloud.google.com/en/feed.atom"  # backup (status + updates)
    ]
}


def fetch_updates():
    items = []
    for name, urls in FEEDS.items():
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                d = feedparser.parse(url)
                if not d.entries:
                    continue
                latest = d.entries[:3]
                items.append(f"## {name} Updates\n")
                for e in latest:
                    title = e.get("title", "No title")
                    link = e.get("link", "")
                    date = e.get("published", "")
                    items.append(f"- **[{title}]({link})** — {date}")
                items.append("")
                break  # stop if we found entries from a working feed
            except Exception as e:
                print(f"Error fetching {name} from {url}: {e}")
    return items


def main():
    import os
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    header = [f"# ☁️ Cloud Updates — {now}\n",
              "Automatically generated from AWS, Azure, and GCP feeds.\n",
              "---\n"]
    content = header + fetch_updates()

    # Make sure we save to the repo's root directory
    output_path = os.path.join(os.getcwd(), "cloud_updates.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    print(f"Wrote updates to: {output_path}")

if __name__ == "__main__":
    main()
