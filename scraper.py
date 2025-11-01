import os
import re
import hashlib
from urllib.parse import urlparse, urljoin, urldefrag, urlunparse
from bs4 import BeautifulSoup

ALLOWED_NETLOCS = (
    "ics.uci.edu",
    "cs.uci.edu",
    "informatics.uci.edu",
    "stat.uci.edu",
)

BLOCKED_EXT_RE = re.compile(
    r".*\.(?:css|js|bmp|gif|jpe?g|ico|png|tiff?|mid|mp2|mp3|mp4|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1|thmx|mso|arff|rtf|jar|csv|rm|smil|wmv|swf|wma|zip|rar|gz)$",
    re.IGNORECASE,
)

BLOCKED_PATH_RE = re.compile(
    r"(?:^|/)~(?:/|$)|(?:/ca/rules)(?:/|$)",
    re.IGNORECASE,
)

DATE_TRAP_SPECIFIC_RE = re.compile(
    r"/events?/tag/talks/day/\d{4}-\d{2}-\d{2}",
    re.IGNORECASE,
)

CAL_TRAP_RE = re.compile(
    r"/(?:calendar|calendars)(?:/|$)|/(?:day|month|year)/\d{4}(?:-\d{2}(?:-\d{2})?)?",
    re.IGNORECASE,
)

WIKI_PARAM_TRAP_KEYS = ("do=", "tab_", "image=", "ns=")

SEARCH_PARAM_RE = re.compile(
    r"(?:^|[&?])(q|s|query|search|keywords?)=",
    re.IGNORECASE,
)

BAD_QUERY_KEYS_RE = re.compile(
    r"(?:^|[&?])(utm_[^=]*|fbclid|gclid|replytocom|session|sid|phpsessid|jsessionid|share|download|view|action|mode|format|rss|feed)=",
    re.IGNORECASE,
)

MAX_HTML_BYTES = 2_000_000
MIN_TEXT_LEN    = 200
MAX_URL_LEN     = 2000
MAX_PATH_DEPTH  = 15
MAX_QUERY_PAIRS = 10
SAVE_HTML = False
SAVE_DIR  = "/tmp/uci_pages"

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [u for u in links if is_valid(u)]

def extract_next_links(url, resp):
    if not resp or resp.status != 200 or not getattr(resp, "raw_response", None):
        return []
    ct = resp.raw_response.headers.get("Content-Type", "") or ""
    if "html" not in ct.lower():
        return []
    cl = resp.raw_response.headers.get("Content-Length")
    try:
        if cl and int(cl) > MAX_HTML_BYTES:
            return []
    except Exception:
        pass
    try:
        body = resp.raw_response.content
        if body and len(body) > MAX_HTML_BYTES:
            return []
        try:
            soup = BeautifulSoup(body, "lxml")
        except Exception:
            soup = BeautifulSoup(body, "html.parser")
    except Exception:
        return []
    out = []
    base = url
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        abs_url = urljoin(base, href)
        abs_url, _ = urldefrag(abs_url)
        if abs_url:
            abs_url = _normalize_url(abs_url)
            out.append(abs_url)
    try:
        text = soup.get_text(separator=" ", strip=True)
        if len(text) < MIN_TEXT_LEN:
            return _dedup(out)
    except Exception:
        pass
    if SAVE_HTML:
        _maybe_save(url, soup)
    return _dedup(out)

def _dedup(urls):
    seen, dedup = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    return dedup

def _int_param(qs, key):
    for part in qs.split("&"):
        if not part:
            continue
        kv = part.split("=", 1)
        if len(kv) == 2 and kv[0].lower() == key:
            try:
                return int(re.sub(r"\D+", "", kv[1]) or "0")
            except Exception:
                return None
    return None

def _normalize_url(u: str) -> str:
    p = urlparse(u)
    host = p.hostname.lower() if p.hostname else ""
    port = ""
    if p.port and not ((p.scheme == "http" and p.port == 80) or (p.scheme == "https" and p.port == 443)):
        port = f":{p.port}"
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((p.scheme, host + port, path, "", p.query, ""))

def _maybe_save(url, soup):
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        h = hashlib.sha1(url.encode("utf-8")).hexdigest()
        with open(os.path.join(SAVE_DIR, f"{h}.html"), "w", encoding="utf-8", errors="ignore") as f:
            f.write(str(soup))
    except Exception:
        pass

def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if len(url) > MAX_URL_LEN:
            return False
        host = (parsed.netloc or "").lower()
        if not any(host == d or host.endswith("." + d) for d in ALLOWED_NETLOCS):
            return False
        path_lower = (parsed.path or "").lower()
        if BLOCKED_EXT_RE.match(path_lower):
            return False
        if path_lower.count("/") > MAX_PATH_DEPTH:
            return False
        if BLOCKED_PATH_RE.search(path_lower):
            return False
        if DATE_TRAP_SPECIFIC_RE.search(path_lower):
            return False
        if CAL_TRAP_RE.search(path_lower):
            return False
        if host.startswith("gitlab.ics.uci.edu"):
            if "/-/" in path_lower:
                return False
            if re.search(r"/(issues|merge_requests|forks|starrers|stars|network)(?:/|$)", path_lower):
                return False
            if re.search(r"/[0-9a-f]{7,40}(?:/|$)", path_lower):
                return False
            if parsed.query and re.search(r"(?:^|[&])(sort|page|per_page|utf8|state|scope)=", parsed.query, re.I):
                return False
        if any(s in path_lower for s in (
            "/wp-login.php", "/wp-admin", "/xmlrpc.php", "/wp-content/plugins",
            "/wp-json", "/wp-includes", "/administration", "/joomla/login",
            "/user/login", "/user/register", "/user/password", "/login", "/logout",
            "/signup", "/register"
        )):
            return False
        if re.search(r"(?:siteexport|allpages|sitemap|dump)\.(?:htm|html|xml|gz|zip)$", path_lower):
            return False
        q = (parsed.query or "")
        if q:
            if q.count("&") > MAX_QUERY_PAIRS:
                return False
            if BAD_QUERY_KEYS_RE.search(q):
                return False
            if "format=ics" in q.lower() or "ical=1" in q.lower():
                return False
            if "wiki.ics.uci.edu" in host:
                if any(k in q for k in WIKI_PARAM_TRAP_KEYS):
                    return False
            if SEARCH_PARAM_RE.search(q) and q.count("&") > 3:
                return False
            page = _int_param(q, "page")
            start = _int_param(q, "start")
            offset = _int_param(q, "offset")
            if page is not None and page > 200:
                return False
            if start is not None and start > 10_000:
                return False
            if offset is not None and offset > 10_000:
                return False
        if re.search(r"/presentations/sld\d+\.(?:htm|html|pdf)$", path_lower):
            return False
        return True
    except Exception:
        return False
