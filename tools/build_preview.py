#!/usr/bin/env python3
"""build_preview — preview/index.html 을 만든다(Jekyll 없이 보는 단일 HTML 미리보기).

내용: 홈 · 블로그 목록 · 소개 · 푸터 · 샘플 글 2편(관련 보기 블록 포함).
  - _posts/*.md, index.md, about.md, blog.md, _data/links.json 을 읽어 그대로 그린다(문구를 따로 베끼지 않는다).
  - 외부 요청 0: 이미지는 자리표시 상자로 대체하고, CSS·JS 는 모두 인라인이다. <a href> 로 나가는 링크만 있다.
  - 모바일 우선, prefers-color-scheme 라이트/다크(+ 수동 전환 버튼), 백링크 강조 버튼.
  - 실제 Jekyll/minima 렌더와 픽셀이 같지는 않다. 구조(헤더·본문·관련 보기·푸터)와 링크 위치를 판단하기 위한 것이다.

사용: python3 tools/build_preview.py [--samples deficit-bus how-to-record-lawmakers-work]
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARK = "<!-- jalhana-mirror:related -->"
DEFAULT_SAMPLES = ["how-to-record-lawmakers-work", "deficit-bus"]

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
.pg-label{display:block;color:var(--mut);font-size:12px;margin-bottom:10px}
.js .pg-label{display:none}
h1{font-size:1.7rem;line-height:1.35;letter-spacing:-.02em;margin:0 0 .5em}
h2{font-size:1.3rem;line-height:1.4;margin:1.9em 0 .6em;padding-bottom:.3em;border-bottom:1px solid var(--line)}
h3{font-size:1.08rem;margin:1.4em 0 .4em}
p{margin:0 0 1em}
ul,ol{margin:0 0 1.1em;padding-left:1.35em}li{margin-bottom:.3em}
.post-meta{color:var(--mut);font-size:14px;margin:0 0 .6em}
.post-list{list-style:none;margin:0 0 1.2em;padding:0}
.post-list li{margin:0 0 1.15em}
.post-list h3{margin:.05em 0 0;font-size:1.12rem;font-weight:600}
.post-list .soft{color:var(--fg)}
.mirror-note{margin:.9em 0 1.6em;padding:.7em .9em;font-size:14px;line-height:1.6;color:var(--mut);background:var(--card);border-left:4px solid var(--brand);border-radius:0 6px 6px 0}
.post-content h1{font-size:1.45rem}
.ph{margin:1.4em 0}
.ph-box{display:flex;align-items:center;justify-content:center;text-align:center;min-height:120px;padding:14px;border:1px dashed var(--cardline);border-radius:8px;background:var(--card);color:var(--mut);font-size:13px;line-height:1.5}
.related-links{margin:2.6em 0 1em;padding:1em 1.2em;background:var(--card);border:1px solid var(--cardline);border-radius:10px}
.related-links h3{margin:0 0 .5em;font-size:1.05rem}
.related-links ul{margin:0}
.btn{display:inline-block;font:inherit;color:var(--brand);background:transparent;border:1px solid var(--cardline);border-radius:8px;padding:6px 12px;cursor:pointer}
.site-footer{border-top:1px solid var(--line);padding:28px 0 40px;font-size:15px}
.footer-heading{font-weight:700;margin:0 0 14px}
.footer-cols{display:flex;flex-wrap:wrap;margin:0 -15px}
.footer-col{flex:1 1 200px;padding:0 15px;margin-bottom:14px}
.footer-title{margin:0 0 6px;font-weight:700;font-size:14px}
.footer-links{list-style:none;margin:0;padding:0}.footer-links li{margin-bottom:6px}
.footer-note{margin:6px 0 0;font-size:13px;color:var(--mut)}
.hl a[href^="https://jalhana.com"],.hl a[href^="https://github.com/lime38"]{background:var(--hl);border-radius:3px;box-shadow:0 0 0 2px var(--hl)}
@media (min-width:700px){body{font-size:17px}.wrap{padding:0 30px}.footer-cols{margin:0 -15px}}
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
 var top=id.indexOf('pg-post')===0?'pg-blog':id;
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


# ---------------------------------------------------------------- markdown (이 사이트가 쓰는 부분집합)
def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)",
               lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def md_blocks(text: str) -> str:
    """kramdown(GFM, hard_wrap) 와 같은 모양으로: 줄바꿈 = <br>, 이미지 = 자리표시."""
    out: list[str] = []
    para: list[str] = []
    lst: str | None = None

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
        elif (m := re.fullmatch(r"!\[([^\]]*)\]\([^)]+\)", s.strip())):
            flush_para(); close_list()
            out.append('<figure class="ph"><div class="ph-box" role="img" aria-label="{a}">[이미지] {a}</div></figure>'
                       .format(a=html.escape(m.group(1))))
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
            "tags": json.loads(fm.get("tags", "[]")), "canonical": fm["canonical_url"],
            "body": body, "related": related,
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def sections(md: str) -> list[tuple[str, str]]:
    """'## 제목' 단위로 쪼갠다. 첫 항목의 제목은 ''(머리말)."""
    parts = re.split(r"^## (.+)$", md, flags=re.M)
    res = [("", parts[0])]
    for i in range(1, len(parts), 2):
        res.append((parts[i].strip(), parts[i + 1]))
    return res


def site_meta() -> dict:
    cfg = (REPO / "_config.yml").read_text(encoding="utf-8")
    g = lambda k: re.search(rf"^{k}:\s*(.+)$", cfg, re.M).group(1).strip()
    return {"title": g("title"), "description": g("description")}


# ---------------------------------------------------------------- 조각 렌더
def post_list(posts: list[dict], samples: set[str], limit: int | None) -> str:
    items = []
    for p in posts[:limit]:
        tags = "".join(f" · #{html.escape(t)}" for t in p["tags"])
        t = html.escape(p["title"])
        title = (f'<a href="#pg-post-{p["slug"]}" data-go="pg-post-{p["slug"]}">{t}</a>'
                 if p["slug"] in samples else f'<span class="soft">{t}</span>')
        items.append(f'<li><span class="post-meta">{p["date"]}{tags}</span><h3>{title}</h3></li>')
    return '<ul class="post-list">' + "".join(items) + "</ul>"


def render_post(p: dict) -> str:
    tags = "".join(f" · #{html.escape(t)}" for t in p["tags"])
    rel = "".join(f'<li><a href="{html.escape(u)}">{html.escape(t)}</a></li>' for t, u in p["related"])
    return (f'<section class="pg" id="pg-post-{p["slug"]}"><span class="pg-label">▼ 글 — {html.escape(p["title"])}</span>'
            f'<article><h1>{html.escape(p["title"])}</h1>'
            f'<p class="post-meta"><time>{p["date"]}</time>{tags}</p>'
            f'<p class="mirror-note">이 글은 잘하나 블로그의 글을 옮겨 실은 것입니다. 정본은 '
            f'<a href="{p["canonical"]}">잘하나 블로그 원문 — {html.escape(p["title"])}</a>입니다.</p>'
            f'<div class="post-content">{md_blocks(p["body"])}'
            f'<div class="related-links"><h3>관련 보기</h3><ul>{rel}</ul></div></div></article></section>')


def render_footer(links: dict, title: str) -> str:
    li = lambda k: f'<li><a href="{links[k]["url"]}">{html.escape(links[k]["text"])}</a></li>'
    regions = ""
    for r in links["pack_regions"]:
        if r.get("pack_url"):
            regions += f'<li><a href="{r["pack_url"]}">{html.escape(r["name"])} 행감팩</a></li>'
        else:
            regions += f'<li><a href="{r["url"]}">{html.escape(r["name"])} 기록</a></li>'
    return ('<footer class="site-footer"><div class="wrap">'
            f'<p class="footer-heading">{html.escape(title)} — 잘하나 블로그의 글을 옮겨 실은 사이트입니다</p>'
            '<div class="footer-cols">'
            f'<div class="footer-col"><p class="footer-title">잘하나</p><ul class="footer-links">{li("home")}{li("blog")}{li("principles")}{li("rules")}</ul></div>'
            f'<div class="footer-col"><p class="footer-title">행감팩 대상 지역</p><ul class="footer-links">{li("packs")}{regions}</ul></div>'
            f'<div class="footer-col"><p class="footer-title">공개 자료</p><ul class="footer-links">{li("resources")}{li("github")}{li("faq")}{li("copyright")}</ul></div>'
            '</div>'
            '<p class="footer-note">잘하나는 편집은 하되 판정은 하지 않습니다. 이 사이트의 글은 모두 jalhana.com/blog 의 원문을 정본으로 합니다.</p>'
            '</div></footer>')


def build(sample_slugs: list[str]) -> str:
    meta = site_meta()
    links = json.loads((REPO / "_data" / "links.json").read_text(encoding="utf-8"))
    posts = load_posts()
    by_slug = {p["slug"]: p for p in posts}
    for s in sample_slugs:
        if s not in by_slug:
            raise SystemExit(f"샘플 글을 찾을 수 없음: {s}")
    samples = set(sample_slugs)

    # 홈
    _, index_md = split_front((REPO / "index.md").read_text(encoding="utf-8"))
    home = ""
    for head, body in sections(index_md):
        if head == "":
            home += md_blocks(body)
        elif head == "최근 글":
            home += ("<h2>최근 글</h2>" + post_list(posts, samples, 5)
                     + '<p><a class="btn" href="#pg-blog" data-go="pg-blog">전체 글 보기</a></p>')
        else:
            home += f"<h2>{inline(head)}</h2>" + md_blocks(body)
    # 블로그
    fm, blog_md = split_front((REPO / "blog.md").read_text(encoding="utf-8"))
    blog_intro = md_blocks(blog_md.split("{% include")[0])
    # 소개
    fm_a, about_md = split_front((REPO / "about.md").read_text(encoding="utf-8"))

    note = ('<p class="post-meta" style="margin-top:-6px">미리보기에는 글 %d편만 열립니다. '
            '제목이 링크인 글을 눌러 보세요.</p>' % len(samples))
    pages = [
        f'<section class="pg" id="pg-home"><span class="pg-label">▼ 홈</span><h1>{html.escape(meta["title"])}</h1>{home}</section>',
        f'<section class="pg" id="pg-blog"><span class="pg-label">▼ 블로그 목록</span><h1>{html.escape(fm["title"])}</h1>{blog_intro}{note}{post_list(posts, samples, None)}</section>',
        f'<section class="pg" id="pg-about"><span class="pg-label">▼ 소개</span><h1>{html.escape(fm_a["title"])}</h1>{md_blocks(about_md)}</section>',
    ] + [render_post(by_slug[s]) for s in sample_slugs]

    body = "\n".join(pages)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(meta["title"])} — 미리보기</title>
<style>{CSS}</style>
</head>
<body>
<div class="pv"><div class="wrap"><b>미리보기</b><button id="th" type="button">테마: 자동</button><button id="hl" type="button" aria-pressed="false">백링크 강조</button><span class="cnt" id="cnt"></span></div></div>
<header class="site-header"><div class="wrap"><a class="site-title" href="#pg-home" data-go="pg-home">{html.escape(meta["title"])}</a>
<nav class="site-nav" aria-label="주 메뉴"><a href="#pg-home" data-go="pg-home">홈</a><a href="#pg-blog" data-go="pg-blog">블로그</a><a href="#pg-about" data-go="pg-about">소개</a></nav></div></header>
<main><div class="wrap">
{body}
</div></main>
{render_footer(links, meta["title"])}
<script>{JS}</script>
</body>
</html>
"""


def check_no_external_requests(doc: str) -> None:
    """자동 로드되는 외부 자원이 없는지 확인(링크 <a href> 는 요청이 아니다)."""
    bad = re.findall(r"<(?:img|script|iframe|source|video|audio|embed|object)\b[^>]*\b(?:src|data)=[\"']?(?:https?:)?//", doc)
    bad += re.findall(r"<link\b[^>]*\bhref=", doc)
    bad += re.findall(r"url\(\s*[\"']?(?:https?:)?//", doc)
    bad += re.findall(r"@import", doc)
    if bad:
        raise SystemExit(f"외부 요청 가능성 발견: {bad[:3]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", nargs="+", default=DEFAULT_SAMPLES, help="전문을 보여줄 글 슬러그")
    ap.add_argument("--out", type=Path, default=REPO / "preview" / "index.html")
    args = ap.parse_args()
    doc = build(args.samples)
    check_no_external_requests(doc)
    size = len(doc.encode("utf-8"))
    if size >= 1_000_000:
        raise SystemExit(f"미리보기가 1MB 를 넘음: {size}")
    args.out.parent.mkdir(exist_ok=True)
    args.out.write_text(doc, encoding="utf-8")
    print(f"{args.out} 작성 ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
