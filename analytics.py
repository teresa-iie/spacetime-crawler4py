import atexit, json
from collections import Counter, defaultdict
from urllib.parse import urlparse, urldefrag

REPORT_PATH = "report.json"

STOPWORDS = {
    "a","an","and","are","as","at","be","by","for","from","has","he","in","is","it",
    "its","of","on","that","the","to","was","were","will","with","this","these",
    "those","or","if","but","we","you","your","our","i","they","them","their","she",
    "his","her","not","no","do","does","did","so","than","then","there","here","over",
    "under","up","down","out","into","about","can","could","should","would"
}

_unique_pages = set()
_subdomain_pages = defaultdict(set)
_global_counter = Counter()
_longest_url = None
_longest_count = 0

def _normalize_url(u: str) -> str:
    u, _ = urldefrag(u)
    return u.strip()

def _subdomain_of(u: str):
    host = urlparse(u).netloc.lower()
    return host if host.endswith(".uci.edu") else None

def record_page(url: str, tokens: list[str]):
    global _longest_url, _longest_count
    norm = _normalize_url(url)
    _unique_pages.add(norm)

    sd = _subdomain_of(norm)
    if sd:
        _subdomain_pages[sd].add(norm)

    clean = [t for t in tokens if t not in STOPWORDS]
    _global_counter.update(clean)

    wc = len(tokens)
    if wc > _longest_count:
        _longest_count = wc
        _longest_url = norm

def save_report():
    subdomains_list = sorted((sd, len(urls)) for sd, urls in _subdomain_pages.items())
    top50 = _global_counter.most_common(50)
    report = {
        "unique_pages": len(_unique_pages),
        "longest_page": {"url": _longest_url, "word_count": _longest_count},
        "top_50_words": top50,
        "subdomains": subdomains_list,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

atexit.register(save_report)
