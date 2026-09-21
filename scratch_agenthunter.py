import requests
import re
import json
from bs4 import BeautifulSoup

url = 'https://www.agenthunter.io/agent/devra'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')

print("Title:", soup.title.string if soup.title else "")

# Check links
for a in soup.find_all('a', href=True):
    href = a['href']
    text = a.get_text(strip=True)
    if 'agenthunter.io' not in href and href.startswith('http'):
        print(f"Link: '{text}' -> {href}")

# Inspect content under headers
for h2 in soup.find_all('h2'):
    h2_text = h2.get_text(strip=True)
    parent = h2.find_parent()
    print(f"\n=== SECTION: {h2_text} ===")
    if parent:
        # print siblings or text inside parent
        print(parent.get_text("\n", strip=True)[:600])

