#!/usr/bin/env python3
"""Refresh generated sections of the profile README from the GitHub API."""
import html, json, os, re, sys, urllib.request

USER   = os.environ.get("GH_USER", "durpyneko")
TOKEN  = os.environ.get("GITHUB_TOKEN")
README = os.environ.get("README", "README.md")
MAX_REPOS = int(os.environ.get("MAX_REPOS", "8"))
DESC_MAX  = int(os.environ.get("DESC_MAX", "44"))
LANG_MODE = os.environ.get("LANG_MODE", "bytes")   # bytes | repos
BAR_W     = 24

def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", USER + "-profile")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def fetch_repos():
    out, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&sort=pushed")
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return [r for r in out
            if not r["fork"] and not r["archived"] and not r["private"]
            and r["name"].lower() != USER.lower()]      # skip the profile repo itself

def clip(t):
    return t if len(t) <= DESC_MAX else t[:DESC_MAX-1].rstrip() + "…"

def projects_table(repos):
    rows = repos[:MAX_REPOS]
    if not rows:
        return "<pre>\nno public repos\n</pre>"
    names = [r["name"] for r in rows]
    langs = [(r["language"] or "-").lower() for r in rows]
    descs = [clip((r["description"] or "").strip().lower()) for r in rows]
    NW = max(len(x) for x in names + ["repo"])
    LW = max(len(x) for x in langs + ["lang"])
    DW = max(len(x) for x in descs + ["description"])
    out = ["<pre>",
           "┌─" + "─"*NW + "─┬─" + "─"*LW + "─┬─" + "─"*DW + "─┐",
           "│ " + "repo".ljust(NW) + " │ " + "lang".ljust(LW) + " │ " + "description".ljust(DW) + " │",
           "├─" + "─"*NW + "─┼─" + "─"*LW + "─┼─" + "─"*DW + "─┤"]
    for r, n, l, d in zip(rows, names, langs, descs):
        link = f'<a href="{r["html_url"]}">{html.escape(n)}</a>' + " "*(NW-len(n))
        out.append("│ " + link + " │ " + html.escape(l).ljust(LW) + " │ " + html.escape(d).ljust(DW) + " │")
    out.append("└─" + "─"*NW + "─┴─" + "─"*LW + "─┴─" + "─"*DW + "─┘")
    out.append("</pre>")
    return "\n".join(out)

def language_chart(repos):
    totals = {}
    if LANG_MODE == "repos":                        # one vote per repo, by primary language
        for r in repos:
            if r["language"]:
                totals[r["language"]] = totals.get(r["language"], 0) + 1
    else:                                           # weighted by bytes of code
        for r in repos:
            try:
                for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
                    totals[lang] = totals.get(lang, 0) + n
            except Exception as e:                  # one bad repo must not kill the run
                print(f"  ! languages for {r['name']}: {e}", file=sys.stderr)
    if not totals:
        return "```\nno language data\n```"
    grand = sum(totals.values())
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:6]
    NW = max(len(k) for k, _ in top)
    out = ["```"]
    for lang, n in top:
        pct = n / grand * 100
        fill = round(BAR_W * n / grand)
        out.append(f"{lang.lower().ljust(NW)}  {'█'*fill}{'░'*(BAR_W-fill)}  {pct:5.1f}%")
    out.append("```")
    return "\n".join(out)

MISSING = []

def splice(text, key, body):
    pat = re.compile(f"(<!-- {key}:START -->).*?(<!-- {key}:END -->)", re.S)
    if not pat.search(text):
        MISSING.append(key)
        return text
    return pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), text)

def main():
    repos = fetch_repos()
    print(f"{len(repos)} public source repos")
    doc = open(README, encoding="utf-8").read()
    doc = splice(doc, "PROJECTS", projects_table(repos))
    doc = splice(doc, "LANGS", language_chart(repos))
    if MISSING:                                  # fail loudly: a silent no-op hid a lost README once
        print(f"::error::markers missing from {README}: {', '.join(MISSING)}", file=sys.stderr)
        sys.exit(1)
    open(README, "w", encoding="utf-8").write(doc)
    print("readme updated")

if __name__ == "__main__":
    main()
