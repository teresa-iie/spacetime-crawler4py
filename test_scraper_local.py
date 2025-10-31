from types import SimpleNamespace
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urldefrag
from collections import Counter, defaultdict
import argparse
import os

from scraper import extract_next_links, is_valid

STOPWORDS = {
    "a","an","and","are","as","at","be","by","for","from","has","he","in","is","it",
    "its","of","on","that","the","to","was","were","will","with","this","these",
    "those","or","if","but","we","you","your","our","i","they","them","their","she",
    "his","her","not","no","do","does","did","so","than","then","there","here","over",
    "under","up","down","out","into","about","can","could","should","would"
}

def extract_text_tokens(html_bytes):
    soup = BeautifulSoup(html_bytes, "lxml")
    text = soup.get_text(separator=" ")
    buf = []
    for ch in text:
        if ch.isalnum():
            buf.append(ch.lower())
        else:
            buf.append(" ")
    tokens = [w for w in "".join(buf).split() if w]
    return tokens

def subdomain_of(url):
    host = urlparse(url).netloc.lower()
    if host.endswith(".uci.edu"):
        return host
    return None

def normalize_url(u):
    u, _ = urldefrag(u)
    return u.strip()

def fake_resp(base_url, html_bytes):
    return SimpleNamespace(
        url=base_url,
        status=200,
        raw_response=SimpleNamespace(
            headers={"Content-Type": "text/html"},
            content=html_bytes
        )
    )

def builtin_pages():
    # mock pages
    p1 = b"""
    <html><body>
      <h1>Welcome to UCI ICS</h1>
      <p>The Department of Informatics and Computer Science at UCI.</p>
      <p>UCI provides programs in Computer Science, Statistics, and Informatics.</p>
      <a href="https://www.ics.uci.edu/">ICS</a>
      <a href="/about/">About</a>
      <a href="https://www.informatics.uci.edu/people/">Informatics</a>
      <a href="https://google.com/">Google</a>
      <a href="https://www.stat.uci.edu/docs/report.pdf">PDF</a>
    </body></html>
    """
    p2 = b"""
    <html><body>
      <h2>Statistics at UCI</h2>
      <p>The Department of Statistics offers undergraduate and graduate programs.</p>
      <p>Statistics, data, inference, probability, modeling, and computation.</p>
      <a href="https://www.stat.uci.edu/">STAT</a>
      <a href="https://www.cs.uci.edu/">CS</a>
      <a href="https://calendar.ics.uci.edu/events/">Events</a>
    </body></html>
    """
    return [
        ("https://www.ics.uci.edu/sample1", p1),
        ("https://www.stat.uci.edu/sample2", p2),
    ]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append", help="Local HTML file to test (can be repeated)")
    args = ap.parse_args()

    pages = []
    if args.file:
        for i, path in enumerate(args.file, start=1):
            if not os.path.isfile(path):
                print(f"[skip] not a file: {path}")
                continue
            with open(path, "rb") as f:
                html = f.read()
            # fake base URL under allowed domains 
            base = f"https://www.ics.uci.edu/local_{i}"
            pages.append((base, html))
    else:
        pages = builtin_pages()

    unique_pages = set()
    subdomain_pages = defaultdict(set)
    global_counter = Counter()
    per_page_words = {}

    all_valid_links = set()

    for base_url, html in pages:
        resp = fake_resp(base_url, html)

        links = extract_next_links(resp.url, resp)
        valid_links = [u for u in links if is_valid(u)]
        all_valid_links.update(valid_links)

        tokens = extract_text_tokens(html)
        per_page_words[base_url] = len(tokens)

        # unique page by URL (defrag)
        normalized = normalize_url(base_url)
        unique_pages.add(normalized)

        # subdomain count
        sd = subdomain_of(normalized)
        if sd:
            subdomain_pages[sd].add(normalized)

        # word frequency (minus stopwords)
        global_counter.update([t for t in tokens if t not in STOPWORDS])

    #  reports
    print("\n=== Links Extracted (valid only) ===")
    for u in sorted(all_valid_links):
        print(u)

    print("\n=== Unique pages (count) ===")
    print(len(unique_pages))

    print("\n=== Longest page by word count ===")
    if per_page_words:
        longest_url = max(per_page_words, key=lambda k: per_page_words[k])
        print(f"{longest_url} -> {per_page_words[longest_url]} words")

    print("\n=== Top 20 words (minus stopwords) ===")
    for w, c in global_counter.most_common(20):
        print(f"{w}\t{c}")

    print("\n=== Subdomains under uci.edu (unique pages per subdomain) ===")
    for sd in sorted(subdomain_pages):
        print(f"{sd}, {len(subdomain_pages[sd])}")

if __name__ == "__main__":
    main()
