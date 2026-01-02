# cloud_updates.py
# Fetch latest AWS, Azure, GCP RSS and generate cloud_updates.md

import feedparser
import os
import re
from datetime import datetime, timedelta, timezone
import google.generativeai as genai

FEEDS = {
    "AWS": [
        "https://aws.amazon.com/blogs/enterprise-strategy/feed/",
        "https://aws.amazon.com/blogs/architecture/feed/",
        "https://aws.amazon.com/blogs/machine-learning/feed/"
    ],
    "Azure": [
        "https://www.microsoft.com/en-us/research/feed/",
        "https://azurecomcdn.azureedge.net/en-us/updates/feed/",
        "https://azure.microsoft.com/en-us/updates/feed/"  # backup URL
    ],
    "GCP": [
        "https://blog.google/products/google-cloud/rss",
        "http://googleaiblog.blogspot.com/atom.xml",
        "https://cloudblog.withgoogle.com/rss",
        "https://status.cloud.google.com/en/feed.atom"  # backup (status + updates)
    ],
    "IBM Cloud": [
        "https://www.ibm.com/cloud/blog/atom.xml",
        "https://www.ibm.com/blogs/cloud-computing/feed/",
        "https://research.ibm.com/rss"
    ]
}

def generate_5min_digest(raw_updates_list):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not raw_updates_list:
        return "> ⚠️ AI Digest skipped: Missing API Key or no new data.\n\n"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # We only send the titles to keep it fast and save tokens
        titles_only = "\n".join([item.split('\n')[0] for item in raw_updates_list])
        
        prompt = f"Summarize these tech headlines for a CIO in 3 bullet points:\n{titles_only}"
        response = model.generate_content(prompt)
        
        return f"## ⚡ 5-Minute Executive Digest\n> {response.text}\n\n---\n"
    except Exception as e:
        return f"> ⚠️ AI Digest unavailable: {str(e)}\n\n---\n"

def fetch_updates():
    items = []
    # 1. READ EXISTING CONTENT FIRST TO CHECK FOR DUPLICATES
    existing_content = ""
    output_path = os.path.join(os.getcwd(), "cloud_updates.md")
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
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
                    # 2. CHECK IF THE LINK IS ALREADY IN YOUR FILE
                    if link in existing_content:
                        continue # Skip this item, it's already recorded
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

    # 1. Fetch raw updates using your existing function
    raw_updates = fetch_updates() 
    
    # 2. GENERATE THE AI DIGEST (NEW)
    ai_digest = generate_5min_digest(raw_updates)

    # Assemble: Header -> AI Digest -> Detailed Sections
    new_content = "".join(header) + ai_digest + "\n".join(raw_updates)
    new_section = "\n".join(new_content)

    output_path = os.path.join(os.getcwd(), "cloud_updates.md")
    
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            old_full_content = f.read()

        # Split by the header emoji to separate daily updates
        # This is much more reliable than a complex regex
        sections = old_full_content.split("# ☁️")
        valid_sections = []

        for section in sections:
            if not section.strip(): continue
            
            # Extract the date from the first line of the section (YYYY-MM-DD)
            # Using a simpler search for the first 10 digits
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", section)
            if date_match:
                try:
                    section_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    # Keep if within 30 days
                    if (now - section_date) <= timedelta(days=30):
                        valid_sections.append("# ☁️" + section)
                except ValueError:
                    continue # Skip sections with malformed dates

        # Reconstruct the file with the new section at the top
        combined = new_section + "\n\n" + "".join(valid_sections)
    else:
        combined = new_section

    # Final Write
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(combined.strip())

    print(f"✅ Added new updates, kept only last 30 days: {output_path}")

if __name__ == "__main__":
    main()
