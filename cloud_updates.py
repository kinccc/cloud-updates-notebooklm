# cloud_updates.py
# Fetch latest AWS, Azure, GCP RSS and generate cloud_updates.md

import feedparser
import os
import re
from datetime import datetime, timedelta, timezone
from google.api_core import exceptions
import google.generativeai as genai
import time

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
    """
    Synthesizes raw RSS updates into a CIO Executive Digest.
    Includes failover redundancy and exponential backoff for 429 errors.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not raw_updates_list:
        return "> ⚠️ AI Digest skipped: Missing API Key or no new data to summarize.\n\n"

    # Configure the library
    genai.configure(api_key=api_key)

    # Strategy: Failover from high-demand models to high-availability models
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-flash-lite']
    
    # Context Optimization: Use only headlines to save tokens and speed up processing
    headlines = [item.split('\n')[0] for item in raw_updates_list[:12]]
    context_text = "\n".join(headlines)

    prompt = f"""
    You are a Strategic CIO Advisor. Based on these cloud news headlines, provide:
    1. A 'Big Picture' summary (1 sentence).
    2. Three 'Strategic Impact' bullet points.
    3. One 'Action Item' for the infrastructure team.

    Headlines:
    {context_text}
    """

    for model_name in models_to_try:
        # Try each model with a "Short-Fuse" retry (Exponential Backoff)
        # 1st attempt: Immediate | 2nd attempt: +3s | 3rd attempt: +7s
        for attempt in range(3):
            try:
                if attempt > 0:
                    wait_time = (attempt ** 2) + 2 
                    print(f"🔄 {model_name} quota hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                # Success! Return the summary with the model name for transparency
                return f"## ⚡ 5-Minute Executive Digest ({model_name})\n> {response.text}\n\n---\n"

            except exceptions.ResourceExhausted as e:
                # Error 429: Keep retrying until we hit 3 attempts
                if attempt == 2:
                    print(f"❌ {model_name} exhausted all retries. Failing over...")
                continue 
            
            except Exception as e:
                # If it's a 404 or other error, move to the next model immediately
                print(f"⚠️ {model_name} error: {str(e)[:50]}")
                break 

    return "> ⚠️ AI Digest unavailable: All models hit quota limits. Please check raw updates below.\n\n---\n"

def fetch_updates():
    items = []
    output_path = os.path.join(os.getcwd(), "cloud_updates.md")
    
    existing_content = ""
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

    for name, urls in FEEDS.items():
        if isinstance(urls, str):
            urls = [urls]
            
        provider_has_new_content = False
        
        for url in urls:
            try:
                d = feedparser.parse(url)
                if not d.entries:
                    continue

                # Buffer to hold updates for this specific provider
                temp_updates = []
                
                for e in d.entries[:5]: # Check top 5 instead of 3 for better coverage
                    title = e.get("title", "No title").strip()
                    link = e.get("link", "")
                    
                    if link in existing_content:
                        continue 
                    
                    date = e.get("published", e.get("updated", "Recent"))
                    summary = e.get("summary", "").strip()
                    summary_short = summary[:150] + "..." if len(summary) > 150 else summary
                    
                    temp_updates.append(f"- **[{title}]({link})** — {date}\n  {summary_short}")

                if temp_updates:
                    items.append(f"## {name} Updates\n")
                    items.extend(temp_updates)
                    items.append("") # Spacer
                    provider_has_new_content = True
                    break # Success! We found new content in this URL, move to next provider
                
            except Exception as e:
                print(f"⚠️ Error fetching {name} from {url}: {e}")

        # If we went through all URLs and found nothing NEW
        if not provider_has_new_content:
            print(f"ℹ️ No NEW updates for {name} today.")
            
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
    # 1. Join the list parts into a single string
    header_str = "".join(header)
    updates_str = "\n".join(raw_updates)

    # 2. Combine them simply using +
    new_section = header_str + ai_digest + updates_str

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
