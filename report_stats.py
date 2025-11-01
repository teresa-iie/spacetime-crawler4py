import sys, os, re, collections, datetime
from urllib.parse import urlparse, urldefrag
from bs4 import BeautifulSoup

STOP = {
"the","and","to","of","a","in","for","is","on","that","with","as","by","at","be","are","this","from","or","an",
"it","we","you","your","our","their","they","he","she","i","was","were","will","can","could","should","would",
"not","no","yes","but","if","about","into","over","under","more","most","other","than","then","so","such",
"these","those","has","have","had","do","does","did","may","might","been","being","all","any","each","every",
"some","many","much","there","here","which","who","whom","whose","when","where","why","how","up","out","off",
"also","both","between","within","per","via","new","use","used","using","users","page","pages","home","menu",
"read","view","views","login","logout","register","search","results","copyright","contact","email"
}

def read_manifest(root):
    man = os.path.join(root, "manifest.tsv")
    if not os.path.exists(man):
        return [], {}
    urls, id2url = [], {}
    with open(man, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            h,u = line.split("\t",1)
            urls.append(u)
            id2url[h]=u
    return urls, id2url

def load_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "lxml")
        return soup.get_text(separator=" ", strip=True)
    except:
        return ""

def tokens(txt):
    for w in re.findall(r"[A-Za-z][A-Za-z']{1,}", txt):
        lw = w.lower()
        if lw in STOP: continue
        yield lw

def main():
    root = sys.argv[1] if len(sys.argv)>1 else "/tmp/uci_pages"
    urls, id2url = read_manifest(root)
    unique_pages = set()
    sub_count = collections.Counter()
    longest_len = -1
    longest_url = ""
    freq = collections.Counter()
    for h,u in id2url.items():
        u_nf,_ = urldefrag(u)
        unique_pages.add(u_nf)
        host = (urlparse(u_nf).hostname or "").lower()
        if host.endswith(".uci.edu"):
            sub_count[host] += 1
        p = os.path.join(root, f"{h}.html")
        txt = load_text(p)
        wc = len(re.findall(r"[A-Za-z]+", txt))
        if wc > longest_len:
            longest_len = wc
            longest_url = u_nf
        for t in tokens(txt):
            freq[t] += 1
    top = freq.most_common(50)
    subs = sorted(sub_count.items(), key=lambda x:x[0])
    report_path = os.path.join(root, "report.txt")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append(f"Report generated: {now}")
    lines.append(f"Data directory: {root}")
    lines.append("")
    lines.append("1) Unique pages (fragment ignored):")
    lines.append(str(len(unique_pages)))
    lines.append("")
    lines.append("2) Longest page by word count (HTML ignored):")
    lines.append(longest_url if longest_url else "")
    lines.append(f"Word count: {longest_len if longest_len>=0 else 0}")
    lines.append("")
    lines.append("3) Top 50 most common words (stopwords removed):")
    for w,c in top:
        lines.append(f"{w}\t{c}")
    lines.append("")
    lines.append("4) Subdomains under uci.edu (host, unique pages):")
    for h,c in subs:
        lines.append(f"{h}, {c}")
    with open(report_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write("\n".join(lines))
    print(report_path)

if __name__ == "__main__":
    main()
