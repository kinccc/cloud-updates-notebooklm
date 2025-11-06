# cloud_updates.py
# Fetch latest AWS, Azure, GCP RSS and generate cloud_updates.md

import feedparser
import os
import re
from datetime import datetime, timedelta, timezone

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
        "https://blog.google/products/google-cloud/rss",
        "https://cloudblog.withgoogle.com/rss",
        "https://status.cloud.google.com/en/feed.atom"  # backup (status + updates)
    ],
    "IBM Cloud": [
        "https://www.ibm.com/cloud/blog/atom.xml",
        "https://www.ibm.com/blogs/cloud-computing/feed/",
        "https://research.ibm.com/rss"
    ]
}


def fetch_updates():
    items = []
    for name, urls in FEEDS.items():
        if isinstance(urls, str):
            urls = [urls]
        section_added = False
        for url in urls:
            try:
                d = feedparser.parse(url)
                if not d.entries:
                    continue
                items.append(f"## {name} Updates\n")
                for e in d.entries[:3]:
                    title = e.get("title", "No title").strip()
                    link = e.get("link", "")
                    # Use 'published' if available, else fallback to 'updated'
                    date = e.get("published", e.get("updated", ""))
                    summary = e.get("summary", "").strip()
                    summary_short = summary[:150] + "..." if len(summary) > 150 else summary
                    items.append(f"- **[{title}]({link})** — {date}\n  {summary_short}")
                items.append("")  # blank line
                section_added = True
                break  # stop if a working feed found
            except Exception as e:
                print(f"⚠️ Error fetching {name} from {url}: {e}")
        if not section_added:
            items.append(f"## {name} Updates\n- (No recent updates found)\n")
    return items

def main():
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")

    header = [
        f"# ☁️ Cloud Updates — {now_str}\n",
        "Automatically generated from AWS, Azure, and GCP feeds.\n",
        "---\n"
    ]
    new_content = header + fetch_updates()
    new_section = "\n".join(new_content)

    output_path = os.path.join(os.getcwd(), "cloud_updates.md")
    combined = new_section

    # If an old file exists, read and filter by date (keep only last 30 days)
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            old_content = f.read()

        # Find all previous date headers
        pattern = r"# ☁️ Cloud Updates — ([0-9\-]+) [0-9:]+ UTC"
        matches = list(re.finditer(pattern, old_content))

        keep_from_index = None
        if matches:
            for match in matches:
                date_str = match.group(1)
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if (now - date) <= timedelta(days=30):
                        keep_from_index = match.start()
                        break
                except ValueError:
                    continue

        # If we found recent updates, keep only them
        if keep_from_index is not None:
            old_trimmed = old_content[keep_from_index:]
            combined = new_section + "\n\n" + old_trimmed
        else:
            combined = new_section

    # Write combined content back
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(combined)

    print(f"✅ Added new updates, kept only last 30 days: {output_path}")

if __name__ == "__main__":
    main()
