#!/usr/bin/env python3
"""build_preview — preview/index.html 을 만든다(Jekyll 없이 보는 단일 HTML 미리보기).

내용: 홈 · 블로그 목록(10편씩 쪽 나눔) · 소개 · 푸터 · 샘플 글 2편(관련 보기 블록 포함).
  - _posts/*.md, index.md, about.md, blog/index.md, _data/links.json, _config.yml 을 읽어 그대로 그린다(문구를 따로 베끼지 않는다).
  - 홈과 샘플 글마다 접이식 「SEO 태그 보기」: 이 사이트가 내는 head 의 meta/OG/twitter/JSON-LD 를 같은 데이터로 그린다.
    Jekyll 이 없으므로 jekyll-seo-tag 출력 형식을 흉내 낸 것이며, 실제 출력은 빌드 후 확인해야 한다(패널에도 적어 둠).
  - 「OG 카드 미리보기」: 카카오·슬랙 링크 카드처럼 이미지+제목+설명+도메인.
  - 외부 요청: 샘플 글의 첫 이미지와 OG 카드 이미지(jalhana.com)만 불러온다. 나머지 이미지는 자리표시, 사이트 기본 이미지는 data URI.
  - 모바일 우선, prefers-color-scheme 라이트/다크(+ 수동 전환), 백링크 강조 버튼.

사용: python3 tools/build_preview.py [--samples deficit-bus how-to-record-lawmakers-work]
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARK = "<!-- jalhana-mirror:related -->"
DEFAULT_SAMPLES = ["how-to-record-lawmakers-work", "deficit-bus"]
SITE_URL = "https://lime38.github.io"
CARD_DOMAIN = "lime38.github.io"

CSS = """
:root{--bg:#fdfdfd;--fg:#1b1f24;--mut:#667085;--line:#e6e8eb;--card:#f5f7fa;--cardline:#dfe5ec;--brand:#2a7ae2;--visited:#1d56a8;--hl:rgba(255,190,0,.38);--bar:#111827;--barfg:#f3f4f6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171c;--fg:#e4e7eb;--mut:#a3adbb;--line:#2b3340;--card:#1c222b;--cardline:#2b3340;--brand:#8bb6ff;--visited:#b7a6ff;--hl:rgba(255,190,0,.30);--bar:#0b0d10;--barfg:#e4e7eb}}
:root[data-theme="dark"]{--bg:#14171c;--fg:#e4e7eb;--mut:#a3adbb;--line:#2b3340;--card:#1c222b;--cardline:#2b3340;--brand:#8bb6ff;--visited:#b7a6ff;--hl:rgba(255,190,0,.30);--bar:#0b0d10;--barfg:#e4e7eb}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif;word-break:keep-all;overflow-wrap:anywhere}
a{color:var(--brand);text-decoration:none}a:visited{color:var(--visited)}a:hover{text-decoration:underline}
.wrap{max-width:800px;margin:0 auto;padding:0 16px}
.pv{position:sticky;top:0;z-index:5;background:var(--bar);color:var(--barfg);font-size:12.5px;line-height:1.3}
.pv .wrap{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;padding-top:7px;padding-bottom:7px}
.pv b{font-weight:700;margin-right:2px}
.pv button{font:inherit;color:inherit;background:transparent;border:1px solid rgba(255,255,255,.35);border-radius:999px;padding:3px 10px;cursor:pointer}
.pv button[aria-pressed="true"]{background:rgba(255,190,0,.9);color:#111;border-color:transparent}
.pv .cnt{opacity:.85;margin-left:auto}
.site-header{border-top:5px solid #424242;border-bottom:1px solid var(--line)}
.site-header .wrap{display:flex;align-items:center;justify-content:space-between;min-height:56px;flex-wrap:wrap}
.site-title{font-size:1.25rem;font-weight:700;color:var(--fg)!important;letter-spacing:-.01em}
.site-nav a{margin-left:14px;color:var(--fg);padding:6px 0;border-bottom:2px solid transparent}
.site-nav a.on{border-bottom-color:var(--brand)}
main{padding:24px 0 36px}
.pg{display:block}
.pg+.pg{margin-top:44px;padding-top:30px;border-top:2px dashed var(--line)}
.js .pg{display:none}.js .pg.on{display:block}.js .pg+.pg{margin-top:0;padding-top:0;border-top:0}
.home-hero-img{float:right;width:160px;height:160px;margin:0 0 8px 20px;border-radius:10px}
.home h2{clear:both}
@media (max-width:699px){.home-hero-img{width:60px;height:60px;margin:2px 0 4px 14px}}
.pg-label{display:block;color:var(--mut);font-size:12px;margin-bottom:10px}
.js .pg-label{display:none}
h1{font-size:1.7rem;line-height:1.35;letter-spacing:-.02em;margin:0 0 .5em}
h2{font-size:1.3rem;line-height:1.4;margin:1.9em 0 .6em;padding-bottom:.3em;border-bottom:1px solid var(--line)}
h3{font-size:1.08rem;margin:1.4em 0 .4em}
p{margin:0 0 1em}
ul,ol{margin:0 0 1.1em;padding-left:1.35em}li{margin-bottom:.3em}
.post-meta{color:var(--mut);font-size:14px;margin:0 0 .6em}
.post-list{list-style:none;margin:0 0 1.2em;padding:0}
.post-list li{margin:0 0 20px}
.post-list h3{margin:2px 0 0;font-size:16px;font-weight:600}
.post-list .soft{color:var(--fg)}
.mirror-note{margin:.9em 0 1.6em;padding:.7em .9em;font-size:14px;line-height:1.6;color:var(--mut);background:var(--card);border-left:4px solid var(--brand);border-radius:0 6px 6px 0}
.post-content h1{font-size:1.45rem}
.ph{margin:1.4em 0}
.ph-box{display:flex;align-items:center;justify-content:center;text-align:center;min-height:120px;padding:14px;border:1px dashed var(--cardline);border-radius:8px;background:var(--card);color:var(--mut);font-size:13px;line-height:1.5}
.ph img{display:block;max-width:100%;height:auto;border-radius:8px;margin:0 auto}
.related-links{margin:2.6em 0 1em;padding:1em 1.2em;background:var(--card);border:1px solid var(--cardline);border-radius:10px}
.related-links h3{margin:0 0 .5em;font-size:1.05rem}
.related-links ul{margin:0}
.btn{display:inline-block;font:inherit;color:var(--brand);background:transparent;border:1px solid var(--cardline);border-radius:8px;padding:6px 12px;cursor:pointer}
.pagination{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:4px 14px;margin:2em 0 1em}
.pg-nums{display:inline-flex;gap:6px}
.pg-num,.pg-step{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;padding:0 10px;border-radius:8px}
.pg-num.current{font-weight:700;background:var(--card);color:var(--fg)}
.pg-step.disabled,.pg-sep{color:var(--mut);opacity:.7}
.pv-only{margin:2.4em 0 0;padding-top:1.2em;border-top:2px dashed var(--line)}
.pv-only h3{margin:0 0 .6em;font-size:.95rem;color:var(--mut)}
.ogcard{display:block;max-width:520px;border:1px solid var(--cardline);border-radius:10px;overflow:hidden;background:var(--card);color:var(--fg)}
.ogcard img{display:block;width:100%;aspect-ratio:1200/630;object-fit:cover;background:var(--line)}
.og-txt{display:block;padding:10px 14px 12px;line-height:1.45}
.og-dom{display:block;font-size:12px;color:var(--mut);text-transform:lowercase}
.og-title{display:block;font-weight:700;font-size:15px;margin:2px 0}
.og-desc{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:13px;color:var(--mut)}
details.seo{margin-top:1.1em;border:1px solid var(--cardline);border-radius:8px;background:var(--card)}
details.seo summary{cursor:pointer;padding:9px 14px;font-weight:600}
details.seo .seo-note{margin:0;padding:0 14px 8px;font-size:12.5px;color:var(--mut)}
details.seo pre{margin:0;padding:10px 14px 14px;font:12px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-all;overflow-wrap:anywhere}
.site-footer{border-top:1px solid var(--line);padding:28px 0 40px;font-size:15px}
.footer-heading{font-weight:700;margin:0 0 10px}
.footer-channels{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;margin:0 0 10px}
.footer-title{font-weight:700;font-size:14px}
.footer-icon,.footer-icon:visited{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:50%;color:var(--fg);opacity:.85}
.footer-icon:hover{color:var(--brand);background:var(--card);opacity:1;text-decoration:none}
.footer-icon svg{width:24px;height:24px;display:block}

.visually-hidden{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.footer-note{margin:6px 0 0;font-size:13px;color:var(--mut)}
.hl a[href^="https://jalhana.com"],.hl a[href^="https://github.com/lime38"]{background:var(--hl);border-radius:3px;box-shadow:0 0 0 2px var(--hl)}
@media (min-width:700px){body{font-size:17px}.wrap{padding:0 30px}}
"""

JS = """
(function(){
var R=document.documentElement,d=document;R.classList.add('js');
var pages=[].slice.call(d.querySelectorAll('.pg')),navs=[].slice.call(d.querySelectorAll('.site-nav a'));
var SEL='a[href^="https://jalhana.com"],a[href^="https://github.com/lime38"]',FSEL='footer a[href^="https://jalhana.com"],footer a[href^="https://github.com/lime38"]';
function count(){var on=d.querySelector('.pg.on'),a=on?on.querySelectorAll(SEL).length:0,b=d.querySelectorAll(FSEL).length;
 d.getElementById('cnt').textContent='이 화면의 잘하나 링크: 본문 '+a+' + 푸터 '+b;}
function show(id,noscroll){var ok=false;pages.forEach(function(p){var m=p.id===id;p.classList.toggle('on',m);if(m)ok=true;});
 if(!ok){id='pg-home';d.getElementById(id).classList.add('on');}
 var top=(id.indexOf('pg-post')===0||id.indexOf('pg-blog')===0)?'pg-blog':id;
 navs.forEach(function(n){n.classList.toggle('on',n.getAttribute('data-go')===top);});
 if(!noscroll)window.scrollTo(0,0);count();}
d.addEventListener('click',function(e){var t=e.target.closest('[data-go]');if(!t)return;e.preventDefault();var id=t.getAttribute('data-go');show(id);try{history.replaceState(null,'','#'+id.slice(3));}catch(_){}});
var th=d.getElementById('th'),modes=['auto','light','dark'],mi=0;
th.addEventListener('click',function(){mi=(mi+1)%3;if(modes[mi]==='auto')R.removeAttribute('data-theme');else R.setAttribute('data-theme',modes[mi]);th.textContent='테마: '+['자동','라이트','다크'][mi];});
var hb=d.getElementById('hl');
hb.addEventListener('click',function(){var on=R.classList.toggle('hl');hb.setAttribute('aria-pressed',on?'true':'false');});
var h=location.hash.slice(1);show(h?(h.indexOf('pg-')===0?h:'pg-'+h):'pg-home');
})();
"""

esc = lambda s: html.escape(str(s), quote=True)


# ---------------------------------------------------------------- markdown (이 사이트가 쓰는 부분집합)
def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)",
               lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


IMG_LINE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)(?:\{:([^}]*)\})?")


def md_blocks(text: str, real_first_image: bool = False) -> str:
    """kramdown(GFM, hard_wrap) 와 같은 모양으로: 줄바꿈 = <br>. 이미지 = 자리표시(옵션: 첫 이미지만 실제 이미지)."""
    out: list[str] = []
    para: list[str] = []
    lst: str | None = None
    n_img = 0

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + "<br>".join(para) + "</p>")
            para = []

    def close_list():
        nonlocal lst
        if lst:
            out.append(f"</{lst}>")
            lst = None

    for line in text.split("\n"):
        s = line.rstrip()
        if (m := re.match(r"^(#{1,4}) (.+)$", s)):
            flush_para(); close_list()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2).strip())}</h{n}>")
        elif (m := IMG_LINE.fullmatch(s.strip())):
            flush_para(); close_list()
            alt, url, attrs = m.group(1), m.group(2), m.group(3) or ""
            if real_first_image and n_img == 0 and url.startswith("https://jalhana.com/"):
                wh = "".join(f' {k}="{v}"' for k, v in re.findall(r'(width|height)="(\d+)"', attrs))
                out.append(f'<figure class="ph"><img src="{esc(url)}" alt="{esc(alt)}"{wh} loading="lazy" decoding="async"></figure>')
            else:
                out.append('<figure class="ph"><div class="ph-box" role="img" aria-label="{a}">[이미지] {a}</div></figure>'
                           .format(a=esc(alt)))
            n_img += 1
        elif (m := re.match(r"^- (.+)$", s)):
            flush_para()
            if lst != "ul":
                close_list(); out.append("<ul>"); lst = "ul"
            out.append(f"<li>{inline(m.group(1))}</li>")
        elif (m := re.match(r"^\d+\. (.+)$", s)):
            flush_para()
            if lst != "ol":
                close_list(); out.append("<ol>"); lst = "ol"
            out.append(f"<li>{inline(m.group(1))}</li>")
        elif s.strip() == "---":
            flush_para(); close_list(); out.append("<hr>")
        elif not s.strip():
            flush_para(); close_list()
        else:
            para.append(inline(s))
    flush_para(); close_list()
    return "\n".join(out)


# ---------------------------------------------------------------- 입력 읽기
def split_front(text: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fm = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(": ")
        fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def load_posts() -> list[dict]:
    posts = []
    for f in sorted((REPO / "_posts").glob("*.md")):
        fm, rest = split_front(f.read_text(encoding="utf-8"))
        body, _, tail = rest.partition("\n" + MARK + "\n")
        related = re.findall(r"^- \[([^\]]+)\]\(([^)\s]+)\)$", tail, re.M)
        posts.append({
            "slug": f.stem[11:], "title": json.loads(fm["title"]), "date": fm["date"],
            "modified": fm.get("last_modified_at", fm["date"]),
            "tags": json.loads(fm.get("tags", "[]")), "canonical": fm["canonical_url"],
            "description": json.loads(fm["description"]), "image": json.loads(fm["image"]),
            "body": body, "related": related,
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def sections(md: str) -> list[tuple[str, str]]:
    parts = re.split(r"^## (.+)$", md, flags=re.M)
    res = [("", parts[0])]
    for i in range(1, len(parts), 2):
        res.append((parts[i].strip(), parts[i + 1]))
    return res


def site_cfg() -> dict:
    cfg = (REPO / "_config.yml").read_text(encoding="utf-8")
    g = lambda pat: re.search(pat, cfg, re.M).group(1).strip()
    return {
        "title": g(r"^title:\s*(.+)$"), "description": g(r"^description:\s*(.+)$"),
        "locale": g(r"^locale:\s*(\S+)"), "logo": g(r"^logo:\s*(\S+)"),
        "author": g(r"^author:\s*\n\s+name:\s*(.+)$"), "twitter": g(r"^twitter:\s*\n\s+username:\s*(\S+)"),
        "sameas": re.findall(r"^    - (https://\S+)$", cfg[cfg.index("social:"):cfg.index("theme:")], re.M),
    }


def data_uri(rel: str) -> str:
    return "data:image/png;base64," + base64.b64encode((REPO / rel).read_bytes()).decode()


def abs_url(u: str) -> str:
    return SITE_URL + u if u.startswith("/") else u


# ---------------------------------------------------------------- SEO 태그(jekyll-seo-tag 출력 형식 흉내)
def seo_head(cfg: dict, *, title: str, desc: str, url: str, image: dict, kind: str,
             date: str = "", modified: str = "", tags: list[str] | None = None) -> str:
    img = abs_url(image["path"])
    tags = tags or []
    L = [f"<title>{esc(title)} | {esc(cfg['title'])}</title>" if kind == "article" else f"<title>{esc(cfg['title'])}</title>",
         '<meta name="generator" content="Jekyll v3.10.0" />',
         f'<meta property="og:title" content="{esc(title)}" />',
         f'<meta name="author" content="{esc(cfg["author"])}" />',
         f'<meta property="og:locale" content="{esc(cfg["locale"])}" />',
         f'<meta name="description" content="{esc(desc)}" />',
         f'<meta property="og:description" content="{esc(desc)}" />',
         f'<link rel="canonical" href="{esc(url)}" />',
         f'<meta property="og:url" content="{esc(url)}" />',
         f'<meta property="og:site_name" content="{esc(cfg["title"])}" />',
         f'<meta property="og:image" content="{esc(img)}" />']
    if image.get("height"):
        L.append(f'<meta property="og:image:height" content="{image["height"]}" />')
    if image.get("width"):
        L.append(f'<meta property="og:image:width" content="{image["width"]}" />')
    L.append(f'<meta property="og:image:alt" content="{esc(image["alt"])}" />')
    if kind == "article":
        L += ['<meta property="og:type" content="article" />',
              f'<meta property="article:published_time" content="{date}T00:00:00+09:00" />']
    else:
        L.append('<meta property="og:type" content="website" />')
    L += ['<meta name="twitter:card" content="summary_large_image" />',
          f'<meta property="twitter:image" content="{esc(img)}" />',
          f'<meta name="twitter:image:alt" content="{esc(image["alt"])}" />',
          f'<meta property="twitter:title" content="{esc(title)}" />',
          f'<meta name="twitter:site" content="@{esc(cfg["twitter"])}" />']
    logo = {"@type": "ImageObject", "url": abs_url(cfg["logo"])}
    if kind == "article":
        ld = {"@context": "https://schema.org", "@type": "BlogPosting",
              "author": {"@type": "Person", "name": cfg["author"]},
              "dateModified": f"{modified}T00:00:00+09:00", "datePublished": f"{date}T00:00:00+09:00",
              "description": desc, "headline": title, "image": img,
              "mainEntityOfPage": {"@type": "WebPage", "@id": url},
              "publisher": {"@type": "Organization", "logo": logo, "name": cfg["author"]}, "url": url}
        lds = [ld]
    else:
        lds = [{"@context": "https://schema.org", "@type": "WebSite", "description": desc,
                "headline": title, "name": cfg["title"], "url": url},
               {"@context": "https://schema.org", "@type": "Organization", "name": cfg["author"],
                "url": url, "logo": abs_url(cfg["logo"]), "sameAs": cfg["sameas"]}]
    for ld in lds:
        L.append('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False, separators=(",", ":")) + "</script>")
    custom = ['<meta name="theme-color" content="#fdfdfd" media="(prefers-color-scheme: light)">',
              '<meta name="theme-color" content="#14171c" media="(prefers-color-scheme: dark)">',
              '<link rel="icon" href="/assets/favicon.ico" sizes="any">',
              '<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">',
              '<link rel="icon" type="image/png" sizes="512x512" href="/assets/jalhana-512.png">',
              '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">',
              f'<link rel="alternate" hreflang="ko" href="{esc(url)}">']
    if kind == "article":
        if tags:
            custom.append(f'<meta property="article:section" content="{esc(tags[0])}">')
        custom += [f'<meta property="article:tag" content="{esc(t)}">' for t in tags]
    return ("<!-- Begin Jekyll SEO tag (jekyll-seo-tag 출력 형식을 흉내 낸 것) -->\n" + "\n".join(L) +
            "\n<!-- End Jekyll SEO tag -->\n\n<!-- _includes/head-custom.html -->\n" + "\n".join(custom))


def pv_only(cfg: dict, *, title: str, desc: str, image: dict, head: str) -> str:
    path = image["path"]
    src = data_uri(path.lstrip("/")) if path.startswith("/assets/") else path
    card = (f'<div class="ogcard"><img src="{esc(src)}" alt="{esc(image["alt"])}" loading="lazy" decoding="async">'
            f'<span class="og-txt"><span class="og-dom">{CARD_DOMAIN}</span>'
            f'<span class="og-title">{esc(title)}</span><span class="og-desc">{esc(desc)}</span></span></div>')
    return ('<aside class="pv-only"><h3>미리보기 전용 — 실제 사이트에는 나오지 않는 영역</h3>'
            f'<p class="post-meta">OG 카드 미리보기(카카오·슬랙 링크 카드 모양)</p>{card}'
            '<details class="seo"><summary>SEO 태그 보기</summary>'
            '<p class="seo-note">Jekyll 이 설치돼 있지 않아 jekyll-seo-tag 의 출력 형식을 같은 데이터(front matter·_config.yml)로 흉내 낸 것입니다. '
            '속성 순서·세부 형태는 실제 빌드와 다를 수 있으니, 배포 후 보기 소스로 확인하세요.</p>'
            f'<pre><code>{html.escape(head)}</code></pre></details></aside>')


# ---------------------------------------------------------------- 조각 렌더
def post_list(posts: list[dict], samples: set[str]) -> str:
    items = []
    for p in posts:
        tags = "".join(f" · #{html.escape(t)}" for t in p["tags"])
        t = html.escape(p["title"])
        title = (f'<a href="#pg-post-{p["slug"]}" data-go="pg-post-{p["slug"]}">{t}</a>'
                 if p["slug"] in samples else f'<span class="soft">{t}</span>')
        items.append(f'<li><span class="post-meta">{p["date"]}{tags}</span><h3>{title}</h3></li>')
    return '<ul class="post-list">' + "".join(items) + "</ul>"


def pagination(cur: int, total: int) -> str:
    pid = lambda n: "pg-blog" if n == 1 else f"pg-blog-{n}"
    step = lambda n, label, rel: (f'<a class="pg-step" rel="{rel}" href="#{pid(n)}" data-go="{pid(n)}">{label}</a>'
                                  if 1 <= n <= total else f'<span class="pg-step disabled" aria-hidden="true">{label}</span>')
    nums = "".join(f'<span class="pg-num current" aria-current="page">{n}</span>' if n == cur else
                   f'<a class="pg-num" href="#{pid(n)}" data-go="{pid(n)}">{n}</a>' for n in range(1, total + 1))
    return ('<nav class="pagination" aria-label="글 목록 쪽 이동">' + step(cur - 1, "← 이전", "prev") +
            '<span class="pg-sep" aria-hidden="true">·</span>' + f'<span class="pg-nums">{nums}</span>' +
            '<span class="pg-sep" aria-hidden="true">·</span>' + step(cur + 1, "다음 →", "next") + "</nav>")


def render_post(p: dict, cfg: dict) -> str:
    tags = "".join(f" · #{html.escape(t)}" for t in p["tags"])
    rel = "".join(f'<li><a href="{html.escape(u)}">{html.escape(t)}</a></li>' for t, u in p["related"])
    head = seo_head(cfg, title=p["title"], desc=p["description"], url=p["canonical"], image=p["image"],
                    kind="article", date=p["date"], modified=p["modified"], tags=p["tags"])
    return (f'<section class="pg" id="pg-post-{p["slug"]}"><span class="pg-label">▼ 글 — {html.escape(p["title"])}</span>'
            f'<article><h1>{html.escape(p["title"])}</h1>'
            f'<p class="post-meta"><time>{p["date"]}</time>{tags}</p>'
            f'<p class="mirror-note">이 글은 잘하나 블로그의 글을 옮겨 실은 것입니다. 정본은 '
            f'<a href="{p["canonical"]}">잘하나 블로그 원문 — {html.escape(p["title"])}</a>입니다.</p>'
            f'<div class="post-content">{md_blocks(p["body"], real_first_image=True)}'
            f'<div class="related-links"><h3>관련 보기</h3><ul>{rel}</ul></div></div>'
            f'{pv_only(cfg, title=p["title"], desc=p["description"], image=p["image"], head=head)}</article></section>')


def render_footer(links: dict, title: str) -> str:
    """_includes/footer.html 과 같은 모양: 사이트 한 줄 + 채널 한 줄(아이콘 버튼 + 텍스트 링크) + 안내문."""
    chans = ""
    for c in links["channels"]:
        if not c.get("url"):
            continue
        rel = f' rel="{html.escape(c["rel"])}"' if c.get("rel") else ""
        label = html.escape(c["label"])
        url = html.escape(c["url"])
        if c.get("icon"):
            svg = (REPO / "_includes" / "icons" / f"{c['icon']}.svg").read_text(encoding="utf-8").strip()
            chans += (f'<a class="footer-icon" href="{url}"{rel} aria-label="{label}" title="{label}">'
                      f'{svg}<span class="visually-hidden">{label}</span></a>')
        else:
            pass   # 텍스트 링크는 푸터에 싣지 않는다(10-10 사용자: 깃헙 아이콘까지만)
    return ('<footer class="site-footer"><div class="wrap">'
            f'<p class="footer-heading">{html.escape(title)} — 잘하나 블로그의 글을 옮겨 실은 사이트입니다</p>'
            f'<nav class="footer-channels" aria-label="채널">{chans}</nav>'
            '<p class="footer-note">© 2026 <a href="https://jalhana.com/">jalhana.com</a></p>'
            '</div></footer>')


def build(sample_slugs: list[str]) -> str:
    cfg = site_cfg()
    links = json.loads((REPO / "_data" / "links.json").read_text(encoding="utf-8"))
    posts = load_posts()
    by_slug = {p["slug"]: p for p in posts}
    for s in sample_slugs:
        if s not in by_slug:
            raise SystemExit(f"샘플 글을 찾을 수 없음: {s}")
    samples = set(sample_slugs)

    # 홈
    fm_i, index_md = split_front((REPO / "index.md").read_text(encoding="utf-8"))
    home = ""
    for head, body in sections(index_md):
        if head == "":
            home += md_blocks(body)
        elif head == "최근 글":
            home += ("<h2>최근 글</h2>" + post_list(posts[:5], samples)
                     + '<p><a class="btn" href="#pg-blog" data-go="pg-blog">전체 글 보기</a></p>')
        else:
            home += f"<h2>{inline(head)}</h2>" + md_blocks(body)
    home_desc = json.loads(fm_i["description"])
    home_img = {"path": "/assets/og-default.png", "alt": "잘하나", "width": 1200, "height": 630}
    home_head = seo_head(cfg, title=cfg["title"], desc=home_desc, url=SITE_URL + "/", image=home_img, kind="website")
    home += pv_only(cfg, title=cfg["title"], desc=home_desc, image=home_img, head=home_head)

    # 블로그(쪽 나눔 — blog/index.md 의 per_page/total_pages 를 따른다)
    fm_b, blog_md = split_front((REPO / "blog" / "index.md").read_text(encoding="utf-8"))
    per, total = int(fm_b["per_page"]), int(fm_b["total_pages"])
    intro = md_blocks(blog_md.split("{% include")[0])
    note = ('<p class="post-meta" style="margin-top:-6px">미리보기에는 글 %d편만 열립니다. '
            '제목이 링크인 글을 눌러 보세요.</p>' % len(samples))
    hero = (f'<img class="home-hero-img" src="{data_uri("assets/jalhana-512.png")}" alt="잘하나" width="512" height="512" '
            'loading="eager" decoding="async">')
    pages = [f'<section class="pg" id="pg-home"><span class="pg-label">▼ 홈</span><div class="home">{hero}'
             f'<h1>{html.escape(cfg["title"])}</h1>{home}</div></section>']
    for n in range(1, total + 1):
        title = "블로그" if n == 1 else f"블로그 — {n}쪽"
        chunk = posts[(n - 1) * per: n * per]
        pid = "pg-blog" if n == 1 else f"pg-blog-{n}"
        pages.append(f'<section class="pg" id="{pid}"><span class="pg-label">▼ 블로그 목록 {n}/{total}쪽</span>'
                     f'<h1>{title}</h1>{intro}{note if n == 1 else ""}{post_list(chunk, samples)}{pagination(n, total)}</section>')
    # 소개
    fm_a, about_md = split_front((REPO / "about.md").read_text(encoding="utf-8"))
    pages.append(f'<section class="pg" id="pg-about"><span class="pg-label">▼ 소개</span><h1>{html.escape(fm_a["title"])}</h1>{md_blocks(about_md)}</section>')
    pages += [render_post(by_slug[s], cfg) for s in sample_slugs]

    body = "\n".join(pages)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(cfg["title"])} — 미리보기</title>
<style>{CSS}</style>
</head>
<body>
<div class="pv"><div class="wrap"><b>미리보기</b><button id="th" type="button">테마: 자동</button><button id="hl" type="button" aria-pressed="false">백링크 강조</button><span class="cnt" id="cnt"></span></div></div>
<header class="site-header"><div class="wrap"><a class="site-title" href="#pg-home" data-go="pg-home">{html.escape(cfg["title"])}</a>
<nav class="site-nav" aria-label="주 메뉴"><a href="#pg-home" data-go="pg-home">홈</a><a href="#pg-blog" data-go="pg-blog">블로그</a><a href="#pg-about" data-go="pg-about">소개</a></nav></div></header>
<main><div class="wrap">
{body}
</div></main>
{render_footer(links, cfg["title"])}
<script>{JS}</script>
</body>
</html>
"""


def check_external_requests(doc: str) -> list[str]:
    """자동 로드되는 외부 자원은 jalhana.com 이미지(샘플 글 첫 이미지·OG 카드)만 허용한다. 그 URL 목록을 돌려준다."""
    bad = re.findall(r"<(?:script|iframe|source|video|audio|embed|object)\b[^>]*\b(?:src|data)=[\"']?(?:https?:)?//", doc)
    bad += re.findall(r"<link\b[^>]*\bhref=", doc)
    bad += re.findall(r"url\(\s*[\"']?(?:https?:)?//", doc)
    bad += re.findall(r"@import", doc)
    imgs = re.findall(r"<img\b[^>]*\bsrc=\"(https?://[^\"]+)\"", doc)
    bad += [u for u in imgs if not u.startswith("https://jalhana.com/")]
    if bad:
        raise SystemExit(f"허용되지 않은 외부 요청 가능성: {bad[:3]}")
    return imgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", nargs="+", default=DEFAULT_SAMPLES, help="전문을 보여줄 글 슬러그")
    ap.add_argument("--out", type=Path, default=REPO / "preview" / "index.html")
    args = ap.parse_args()
    doc = build(args.samples)
    ext = check_external_requests(doc)
    size = len(doc.encode("utf-8"))
    if size >= 1_000_000:
        raise SystemExit(f"미리보기가 1MB 를 넘음: {size}")
    args.out.parent.mkdir(exist_ok=True)
    args.out.write_text(doc, encoding="utf-8")
    print(f"{args.out} 작성 ({size:,} bytes) — 외부 이미지 요청 {len(ext)}건: " + ", ".join(sorted(set(u.split('/')[-1] for u in ext))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
