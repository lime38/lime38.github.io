#!/usr/bin/env python3
"""export_from_dongheon — 잘하나(동헌) 블로그 원고를 이 저장소로 단방향 미러한다.

원천(읽기 전용): <동헌>/branding/blog/publish/[NNN] 제목 #태그.md + _dates.json
  - 대상 선별·제목·태그·슬러그 규칙은 동헌 scripts/build_blog.py 의 _load() 와 같다.
    (발행일이 _dates.json 에 없는 원고는 draft 라 건너뛴다. 태그는 파일명 #태그 우선, 없으면 _dates.json tags.)

산출(멱등 — 재실행해도 결과가 같다):
  _posts/YYYY-MM-DD-<slug>.md      글 한 편
  blog/index.md, blog/page/N/index.md   글 목록 쪽(한 쪽 10편, 이전/다음/쪽 번호는 _includes/pagination.html)

글(_posts) 규칙
  - 본문 = 원문 그대로. 바뀌는 것은 이미지 줄뿐이다:
      ![alt](/blog/images/x.webp)  ->  ![alt](https://jalhana.com/blog/images/x.webp){: loading="lazy" decoding="async" width="W" height="H"}
    (alt 는 원문 그대로, 가로세로는 이미지 헤더에서 읽을 수 있을 때만)
  - front matter(원문에서만 파생 — 새 문장을 쓰지 않는다):
      title, date, last_modified_at(= _dates.json 의 modified, 없으면 date), tags,
      canonical_url(= https://jalhana.com/blog/<slug>, 끝 슬래시 없음 — 슬래시 형태는 라이브에서 404),
      description(본문 앞부분 평문 110~150자, 문장 끝 또는 단어 경계에서 자름),
      image{path,alt,width,height}(= jalhana.com 이 그 글 페이지에서 실제로 내는 글 이미지·alt. jalhana.com 의 기본 이미지이거나 읽지 못하면
        본문 첫 이미지, 그것도 없으면 이 사이트의 /assets/og-default.png 1200x630).
  - 본문 뒤에 '관련 보기' 블록: tools/related_links.json 의 글별 링크 + 원문 글(canonical) 링크.
  - <link rel="canonical"> 은 minima head 의 jekyll-seo-tag 가 canonical_url 을 읽어 한 번만 낸다.
  - 이 도구가 만든 파일(front matter 에 source_num / generated_by)만 지우거나 덮어쓴다.

네트워크: 글 페이지의 og:image 와 이미지 크기는 tools/seo_cache.json 에 저장해 두고, 없는 것만 가져온다.
  --offline  네트워크를 쓰지 않는다(캐시만; 없으면 본문 첫 이미지·기본 이미지로 대체)
  --refresh  캐시를 무시하고 다시 가져온다(jalhana.com 이 글을 재배포한 뒤)

사용:
  python3 tools/export_from_dongheon.py                 # 내보내기 + 본문 무수정 자체검증
  python3 tools/export_from_dongheon.py --check-links   # 위에 더해 모든 링크·이미지를 GET 으로 확인(200 아니면 실패)
  python3 tools/export_from_dongheon.py --src <publish 폴더>   (또는 환경변수 JALHANA_BLOG_PUBLISH)

표준 라이브러리만 쓴다(pip 설치 없음). 원천 폴더는 읽기만 한다.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SRC = Path(os.environ.get("JALHANA_BLOG_PUBLISH",
                                  "/home/devuh/dongheon/branding/blog/publish"))
SITE = "https://jalhana.com"
JALHANA_DEFAULT_IMAGE = SITE + "/og-image.png"   # jalhana.com 자신의 기본 이미지 = '글 이미지 없음'으로 취급한다
DEFAULT_IMAGE = "/assets/og-default.png"          # 이 사이트의 기본 공유 이미지(1200x630, 저장소 안)
DEFAULT_ALT = "잘하나"
LOCAL_ASSETS = ("assets/og-default.png", "assets/jalhana-512.png", "assets/apple-touch-icon.png",
                "assets/favicon.ico", "assets/favicon-32.png")
PER_PAGE = 10
UA = "jalhana-pages-seo/1.0"
MARK = "<!-- jalhana-mirror:related -->"
IMG_RE = re.compile(r"!\[([^\]]*)\]\((/blog/images/[^)\s]+)\)")
IMG_OUT_RE = re.compile(r"(!\[[^\]]*\]\()" + re.escape(SITE) + r"(/blog/images/[^)\s]+\))\{:[^}]*\}")
NAME_RE = re.compile(r"\[(\d+)\]\s*(.+?)(?:\s*#(\S+))?\.md$")
ALLOWED_PREFIXES = (SITE + "/", "https://github.com/lime38/")
CACHE_PATH = REPO / "tools" / "seo_cache.json"
BLOG_INTRO = ("잘하나 블로그의 글을 옮겨 싣고 있습니다. 글의 정본은 [잘하나 블로그](https://jalhana.com/blog/)에 있고, "
              "각 글 첫머리에 원문 주소를 밝혀 둡니다.")


def canonical_url(slug: str) -> str:
    return f"{SITE}/blog/{slug}"


J = lambda s: json.dumps(s, ensure_ascii=False)  # JSON 문자열 = 유효한 YAML 큰따옴표 문자열


# ---------------------------------------------------------------- 본문에서 파생하는 값
def plain(text: str, n: int = 150) -> str:
    """build_blog._plain 과 같은 평문 추출(이미지·링크·제목 제거). n 은 자르는 길이."""
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"^#+\s.*$", "", s, flags=re.M)
    s = re.sub(r"[*#>\-·\[\]]", " ", s)
    return " ".join(s.split())[:n]


def seo_plain(text: str) -> str:
    """description 용 평문: 이미지·제목·주소 제거, 링크는 글자만 남긴다(원문 문장 외에는 아무것도 더하지 않는다)."""
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"https?://[^\s)\]]+", " ", s)
    s = re.sub(r"^#+\s.*$", "", s, flags=re.M)
    s = re.sub(r"^\s*[-·]\s+", " ", s, flags=re.M)
    s = re.sub(r"[*#>\[\]]", " ", s)
    return " ".join(s.split())


def seo_description(body: str, lo: int = 110, hi: int = 150, floor: int = 70) -> str:
    """본문 앞부분을 hi 자 이내로: 문장 끝(lo~hi) > 더 짧은 문장 끝(floor~lo) > 단어 경계. 말줄임표·단어 중간 절단 없음."""
    s = seo_plain(body)
    if len(s) <= hi:
        return s
    window = s[:hi + 1]
    ends = [m.end() for m in re.finditer(r"[.?!](?=\s)", window) if m.end() <= hi]
    for lo_, hi_ in ((lo, hi), (floor, lo - 1)):
        good = [e for e in ends if lo_ <= e <= hi_]
        if good:
            return s[:max(good)].strip()
    sp = window.rfind(" ")
    if sp >= floor:
        return s[:sp].rstrip(" ,;:")
    return s[:hi].rstrip()


def first_body_image(body: str):
    m = IMG_RE.search(body)
    return (m.group(1), SITE + m.group(2)) if m else None


# ---------------------------------------------------------------- 네트워크 + 캐시(og:image, 이미지 크기)
def http_bytes(url: str, n: int | None = None, headers: dict | None = None, timeout: int = 25) -> bytes:
    h = {"User-Agent": UA}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read(n) if n else r.read()


def image_size_from_bytes(b: bytes):
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        fmt = b[12:16]
        if fmt == b"VP8X":
            return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
        if fmt == b"VP8L":
            bits = int.from_bytes(b[21:25], "little")
            return 1 + (bits & 0x3FFF), 1 + ((bits >> 14) & 0x3FFF)
        if fmt == b"VP8 ":
            return int.from_bytes(b[26:28], "little") & 0x3FFF, int.from_bytes(b[28:30], "little") & 0x3FFF
    return None


class Seo:
    """og:image·이미지 크기 조회 + 디스크 캐시. 같은 URL 은 한 번만 가져온다."""

    def __init__(self, offline: bool, refresh: bool):
        self.offline, self.refresh = offline, refresh
        self.cache = {"og": {}, "sizes": {}}
        if CACHE_PATH.exists():
            self.cache.update(json.loads(CACHE_PATH.read_text(encoding="utf-8")))
        self.seen: set[str] = set()
        self.before = json.dumps(self.cache, ensure_ascii=False, sort_keys=True)

    def og(self, slug: str):
        """jalhana.com 이 그 글 페이지에서 내는 {image, alt}. 없으면 None."""
        known = self.cache["og"].get(slug)
        if known and not (self.refresh and ("og:" + slug) not in self.seen):
            return known
        if self.offline:
            return known
        self.seen.add("og:" + slug)
        try:
            page = http_bytes(canonical_url(slug)).decode("utf-8", "replace")
            head = page[:page.find("</head>")]
            g = lambda prop: (re.search(r"<meta property=%s content=(?:'([^']*)'|\"([^\"]*)\")" % re.escape(prop), head) or [None] * 3)
            im, al = g("og:image"), g("og:image:alt")
            image = im[1] or im[2]
            if image:
                self.cache["og"][slug] = {"image": image, "alt": html.unescape((al[1] or al[2]) or "")}
            time.sleep(0.4)
        except Exception as e:  # 네트워크 실패는 대체값으로 넘어간다
            print(f"  경고: {slug} og:image 를 읽지 못함 ({e})")
        return self.cache["og"].get(slug)

    def size(self, url: str):
        known = self.cache["sizes"].get(url)
        if known and not (self.refresh and ("sz:" + url) not in self.seen):
            return tuple(known)
        if self.offline:
            return tuple(known) if known else None
        self.seen.add("sz:" + url)
        wh = None
        for attempt in range(3):  # 간헐적 연결 끊김(reset)은 다시 시도한다
            try:
                wh = image_size_from_bytes(http_bytes(url, 64, {"Range": "bytes=0-63"}))
                time.sleep(0.2)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  경고: 크기를 읽지 못함 {url} ({e})")
                time.sleep(1.0 + attempt)
        if wh:
            self.cache["sizes"][url] = list(wh)
        return wh

    def save(self):
        after = json.dumps(self.cache, ensure_ascii=False, sort_keys=True)
        if after != self.before:
            CACHE_PATH.write_text(json.dumps(self.cache, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                  encoding="utf-8")


# ---------------------------------------------------------------- 원고 읽기
def load_posts(src: Path) -> list[dict]:
    meta = json.loads((src / "_dates.json").read_text(encoding="utf-8"))
    dates = {k: v for k, v in meta.items() if re.match(r"^\d+$", k)}
    tags = meta.get("tags", {})
    slugs = meta.get("slugs", {})
    modified = meta.get("modified", {})
    posts = []
    for f in sorted(src.glob("[[]*.md")):
        m = NAME_RE.match(f.name)
        if not m:
            continue
        num, title, tag = m.group(1), m.group(2), m.group(3) or tags.get(m.group(1), "")
        date = dates.get(num, "")
        if not date:  # 발행일 없는 원고 = draft
            print(f"  건너뜀(발행일 없음): {f.name}")
            continue
        posts.append({"num": num, "title": title, "tag": tag, "date": date,
                      "modified": modified.get(num, date), "slug": slugs.get(num, num),
                      "body": f.read_text(encoding="utf-8"), "file": f.name})
    posts.sort(key=lambda p: (p["date"], p["num"]))
    return posts


def load_related(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for slug, links in list(data.get("posts", {}).items()) + [("default", data.get("default", []))]:
        for ln in links:
            url, text = ln["url"], ln["text"]
            if not url.startswith(ALLOWED_PREFIXES):
                raise SystemExit(f"허용되지 않은 링크({slug}): {url}")
            if re.search(r"[\[\]]", text):
                raise SystemExit(f"링크 문구에 대괄호 금지({slug}): {text}")
    return data


# ---------------------------------------------------------------- 글 렌더
def related_block(post: dict, related: dict) -> str:
    links = related.get("posts", {}).get(post["slug"])
    if links is None:
        print(f"  경고: related_links.json 에 {post['slug']} 항목이 없어 default 를 씁니다")
        links = related.get("default", [])
    items = [f"- [{ln['text']}]({ln['url']})" for ln in links]
    items.append(f"- [잘하나 블로그 원문 — {post['title']}]({canonical_url(post['slug'])})")
    return (f"\n{MARK}\n\n"
            '<div class="related-links" markdown="1">\n\n'
            "### 관련 보기\n\n" + "\n".join(items) + "\n\n</div>\n")


def default_image_dims(out: Path):
    f = out / DEFAULT_IMAGE.lstrip("/")
    return image_size_from_bytes(f.read_bytes()[:64]) if f.exists() else (1200, 630)


def resolve_image(post: dict, seo: Seo, out: Path) -> dict:
    """og:image 결정: jalhana.com 이 그 글에서 실제로 내는 글 이미지 > 본문 첫 이미지 > 이 사이트 기본 이미지.
    jalhana.com 의 기본 이미지(og-image.png)는 '글 이미지 없음'으로 보고 건너뛴다."""
    live = seo.og(post["slug"])
    first = first_body_image(post["body"])
    if live and live.get("image") and live["image"] != JALHANA_DEFAULT_IMAGE:
        path, alt = live["image"], live.get("alt") or (first[0] if first else "")
    elif first:
        alt, path = first
    else:
        w, h = default_image_dims(out)
        post["og_fallback"] = True
        return {"path": DEFAULT_IMAGE, "alt": DEFAULT_ALT, "width": w, "height": h}
    post["og_fallback"] = False
    wh = seo.size(path)
    # 크기를 모르면 null 로 적어 defaults 의 1200x630 이 섞이지 않게 한다
    return {"path": path, "alt": alt or DEFAULT_ALT,
            "width": wh[0] if wh else None, "height": wh[1] if wh else None}


def front_matter(post: dict, img: dict) -> str:
    tags = "[" + ", ".join(J(t) for t in [post["tag"]] if t) + "]"
    image = "{" + ", ".join(f'{J(k)}: {J(v)}' for k, v in img.items()) + "}"
    return ("---\n"
            "layout: post\n"
            f"title: {J(post['title'])}\n"
            f"date: {post['date']}\n"
            f"last_modified_at: {post['modified']}\n"
            f"tags: {tags}\n"
            f"canonical_url: {canonical_url(post['slug'])}\n"
            f"description: {J(seo_description(post['body']))}\n"
            f"image: {image}\n"
            f"source_num: {J(post['num'])}\n"
            "---\n")


def norm_body(body: str) -> str:
    return body if body.endswith("\n") else body + "\n"


def transform_body(body: str, seo: Seo) -> str:
    def repl(m):
        alt, path = m.groups()
        url = SITE + path
        wh = seo.size(url)
        size = f' width="{wh[0]}" height="{wh[1]}"' if wh else ""
        return f'![{alt}]({url}){{: loading="lazy" decoding="async"{size}}}'
    return IMG_RE.sub(repl, body)


def render_post(post: dict, related: dict, seo: Seo, out: Path) -> str:
    img = resolve_image(post, seo, out)
    return front_matter(post, img) + norm_body(transform_body(post["body"], seo)) + related_block(post, related)


# ---------------------------------------------------------------- 블로그 목록 쪽
def blog_page(i: int, total: int) -> tuple[str, str]:
    url = "/blog/" if i == 1 else f"/blog/page/{i}/"
    path = "blog/index.md" if i == 1 else f"blog/page/{i}/index.md"
    title = "블로그" if i == 1 else f"블로그 — {i}쪽"
    desc = ("잘하나 블로그의 글을 옮겨 싣는 목록입니다. 글의 정본은 jalhana.com/blog에 있습니다." if i == 1 else
            f"잘하나 블로그 글 목록 {i}쪽입니다. 글의 정본은 jalhana.com/blog에 있습니다.")
    nav = []
    if i > 1:
        nav.append(f"prev_url: {'/blog/' if i == 2 else f'/blog/page/{i - 1}/'}")
    if i < total:
        nav.append(f"next_url: /blog/page/{i + 1}/")
    fm = ("---\nlayout: page\n"
          f"title: {J(title)}\n"
          f"description: {J(desc)}\n"
          f"permalink: {url}\n"
          f"page_num: {i}\ntotal_pages: {total}\nper_page: {PER_PAGE}\noffset: {(i - 1) * PER_PAGE}\n"
          + "".join(n + "\n" for n in nav) +
          "generated_by: export_from_dongheon\n---\n")
    body = (f"\n{BLOG_INTRO}\n\n"
            "{% include post-list.html offset=page.offset limit=page.per_page %}\n\n"
            "{% include pagination.html %}\n")
    return path, fm + body


def write_if_changed(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return "unchanged"
    state = "updated" if path.exists() else "created"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return state


def export(src: Path, out: Path, related: dict, seo: Seo):
    posts = load_posts(src)
    posts_dir = out / "_posts"
    posts_dir.mkdir(exist_ok=True)
    counts = {"created": 0, "updated": 0, "unchanged": 0, "removed": 0}
    keep = set()
    for p in posts:
        name = f"{p['date']}-{p['slug']}.md"
        keep.add(name)
        counts[write_if_changed(posts_dir / name, render_post(p, related, seo, out))] += 1
    for f in sorted(posts_dir.glob("*.md")):  # 이 도구가 만든 글만 정리
        if f.name not in keep and re.search(r"^source_num: ", f.read_text(encoding="utf-8"), re.M):
            f.unlink()
            counts["removed"] += 1
    total = max(1, math.ceil(len(posts) / PER_PAGE))
    page_paths = set()
    for i in range(1, total + 1):
        rel, text = blog_page(i, total)
        page_paths.add(rel)
        counts[write_if_changed(out / rel, text)] += 1
    for f in sorted((out / "blog" / "page").glob("*/index.md")) if (out / "blog" / "page").exists() else []:
        rel = f.relative_to(out).as_posix()
        if rel not in page_paths and "generated_by: export_from_dongheon" in f.read_text(encoding="utf-8"):
            f.unlink()
            try:
                f.parent.rmdir()
            except OSError:
                pass
            counts["removed"] += 1
    return posts, counts, total


def verify_bodies(posts: list[dict], out: Path) -> list[str]:
    """미러된 본문이 원문과 같은지(이미지 줄의 절대주소·속성 복원 후) 대조한다."""
    bad = []
    for p in posts:
        f = out / "_posts" / f"{p['date']}-{p['slug']}.md"
        text = f.read_text(encoding="utf-8")
        m = re.match(r"---\n.*?\n---\n", text, re.S)
        if not m or "\n" + MARK + "\n" not in text:
            bad.append(f"{f.name}: front matter 또는 관련 보기 표지 없음")
            continue
        mirrored = IMG_OUT_RE.sub(r"\1\2", text[m.end():text.index("\n" + MARK + "\n")])
        if mirrored != norm_body(p["body"]):
            bad.append(f"{f.name}: 본문이 원문과 다름")
        n_src = len(IMG_RE.findall(p["body"]))
        n_out = text.count('{: loading="lazy" decoding="async"')
        if n_src != n_out:
            bad.append(f"{f.name}: 이미지 {n_src}개 중 속성이 붙은 것 {n_out}개")
    return bad


# ---------------------------------------------------------------- 링크 확인
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def http_status(url: str, timeout: int = 25) -> int:
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def check_links(posts: list[dict], related: dict, out: Path) -> int:
    for rel in LOCAL_ASSETS:
        if not (out / rel).exists():
            print(f"  FAIL 파일 없음: {rel}")
            return 1
    urls: dict[str, str] = {}
    for p in posts:
        urls[canonical_url(p["slug"])] = f"정본 {p['slug']}"
        for ln in related.get("posts", {}).get(p["slug"], related.get("default", [])):
            urls.setdefault(ln["url"], "관련 보기")
        for m in IMG_RE.finditer(p["body"]):
            urls.setdefault(SITE + m.group(2), "이미지")
        fm = (out / "_posts" / f"{p['date']}-{p['slug']}.md").read_text(encoding="utf-8")
        im = re.search(r'^image: \{"path": "(https://[^"]+)"', fm, re.M)
        if im:
            urls.setdefault(im.group(1), "og:image")
    failed = 0
    for i, (u, why) in enumerate(sorted(urls.items()), 1):
        code = http_status(u)
        flag = "ok " if code == 200 else "FAIL"
        if code != 200:
            failed += 1
        print(f"  [{i:3d}/{len(urls)}] {flag} {code} {u}  ({why})")
        time.sleep(0.4)
    print(f"링크 확인: {len(urls)}건 중 실패 {failed}건")
    return failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="branding/blog/publish 폴더")
    ap.add_argument("--out", type=Path, default=REPO, help="Jekyll 사이트 루트(기본: 이 저장소)")
    ap.add_argument("--check-links", action="store_true", help="모든 링크·이미지를 GET 으로 확인")
    ap.add_argument("--offline", action="store_true", help="네트워크 없이 캐시만 사용")
    ap.add_argument("--refresh", action="store_true", help="og:image·이미지 크기 캐시를 무시하고 다시 가져옴")
    args = ap.parse_args()

    if not (args.src / "_dates.json").exists():
        print(f"원천을 찾을 수 없습니다: {args.src}", file=sys.stderr)
        return 2
    related = load_related(args.out / "tools" / "related_links.json")
    seo = Seo(args.offline, args.refresh)
    posts, counts, total = export(args.src, args.out, related, seo)
    seo.save()
    print(f"글 {len(posts)}건, 목록 {total}쪽 — " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    fb = [p["slug"] for p in posts if p.get("og_fallback")]
    print("og:image 가 기본 이미지로 대체된 글:", ", ".join(fb) if fb else "없음")
    bad = verify_bodies(posts, args.out)
    for b in bad:
        print("검증 실패:", b, file=sys.stderr)
    if bad:
        return 1
    print("본문 무수정 검증 통과(이미지 줄만 절대주소·속성으로 치환)")
    if args.check_links and check_links(posts, related, args.out):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
