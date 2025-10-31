import re
import analytics
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag

def scraper(url, resp):
    # extract raw links
    links = extract_next_links(url, resp)
    # filter them
    valid_links = [link for link in links if is_valid(link)]

    # (non-breaking) text-extraction probe
    if resp and resp.status == 200 and resp.raw_response:
        try:
            tokens = extract_text_tokens(resp.raw_response.content)
            analytics.record_page(url, tokens)
            # print(f"Extracted {len(tokens)} tokens from {url}")
        except Exception as e:
            print(f"Text extraction failed for {url}: {e}")

    return valid_links

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    links = set()

    # basic response checks
    if resp is None or resp.status != 200 or resp.raw_response is None:
        return []

    # only handle HTML pages
    content_type = resp.raw_response.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        return []

    try:
        body = resp.raw_response.content
        soup = BeautifulSoup(body, "lxml")

        for a in soup.find_all("a", href=True):
            href = a.get("href")

            # resolve relative URLs
            abs_url = urljoin(resp.url or url, href)

            # remove fragments (#section)
            abs_url, _ = urldefrag(abs_url)

            # remove spaces
            abs_url = abs_url.strip()

            if abs_url:
                links.add(abs_url)

    except Exception as e:
        # If parsing fails, just return what we have
        # (Do not crash the crawler)
        # print(f"extract_next_links error at {url}: {e}")
        pass

    return list(links)

ALLOWED_NETLOCS = (
    ".ics.uci.edu",
    ".cs.uci.edu",
    ".informatics.uci.edu",
    ".stat.uci.edu",
)

BLOCKED_EXT_RE = re.compile(
    r".*\.(css|js|bmp|gif|jpe?g|ico"
    r"|png|tiff?|mid|mp2|mp3|mp4"
    r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
    r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
    r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
    r"|epub|dll|cnf|tgz|sha1"
    r"|thmx|mso|arff|rtf|jar|csv"
    r"|rm|smil|wmv|swf|wma|zip|rar|gz)$"
)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        # return not re.match(
        #     r".*\.(css|js|bmp|gif|jpe?g|ico"
        #     + r"|png|tiff?|mid|mp2|mp3|mp4"
        #     + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
        #     + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
        #     + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
        #     + r"|epub|dll|cnf|tgz|sha1"
        #     + r"|thmx|mso|arff|rtf|jar|csv"
        #     + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
        # Netloc must be under the allowed domains
        host = (parsed.netloc or "").lower()

        # allow exact hosts like "ics.uci.edu" and subdomains like "vision.ics.uci.edu"
        if not any(host == d[1:] or host.endswith(d) for d in ALLOWED_NETLOCS):
            return False

        # block unwanted file types by path or query
        path_lower = (parsed.path or "").lower()
        if BLOCKED_EXT_RE.match(path_lower):
            return False

        # simple trap heuristics:
        # 1) very long URLs (likely session or repeated params)
        if len(url) > 2000:
            return False

        # 2) many query parameters (session ids, calendars, search spam)
        q = parsed.query
        if q:
            # more than ~8 params → likely junk
            if q.count("&") > 8 or "session" in q.lower():
                return False
            
            if "ical=1" in q.lower() or "format=ics" in q.lower():
                return False

        # 3) repeating directories or calendars
        path = parsed.path or ""
        if path.count("/") > 15:
            return False
        if re.search(r"/calendar|/events", path.lower()):
            return False

        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise

'''uncomment these when server is up and running'''

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urldefrag
from collections import Counter

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

def normalize_url(u):
    u, _ = urldefrag(u)
    return u.strip()

def subdomain_of(url):
    host = urlparse(url).netloc.lower()
    if host.endswith(".uci.edu"):
        return host
    return None

def count_word_frequencies(tokens):
    from collections import Counter
    return Counter([t for t in tokens if t not in STOPWORDS])
