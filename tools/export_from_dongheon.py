#!/usr/bin/env python3
"""export_from_dongheon — 잘하나(동헌) 블로그 원고를 이 저장소의 _posts/ 로 단방향 미러한다.

원천(읽기 전용): <동헌>/branding/blog/publish/[NNN] 제목 #태그.md + _dates.json
  - 대상 선별·제목·태그·슬러그 규칙은 동헌 scripts/build_blog.py 의 _load() 와 같다.
    (발행일이 _dates.json 에 없는 원고는 draft 라 건너뛴다. 태그는 파일명 #태그 우선, 없으면 _dates.json tags.)

산출: _posts/YYYY-MM-DD-<slug>.md  (재실행해도 결과가 같다 = 멱등)
  - 본문 = 원문 그대로. 바뀌는 것은 이미지 경로 /blog/images/... -> https://jalhana.com/blog/images/... 뿐.
  - front matter: layout/title/date/tags/canonical_url/description/source_num.
    canonical_url 은 jalhana.com 라이브 정본 형태(https://jalhana.com/blog/<slug>, 끝 슬래시 없음)다.
    슬래시를 붙인 주소는 라이브에서 404 라서(2026-10-09 실측) 쓰지 않는다.
    <link rel="canonical"> 은 minima head 의 jekyll-seo-tag 가 canonical_url 을 읽어 한 번만 낸다.
  - 본문 뒤에 '관련 보기' 블록: tools/related_links.json 의 글별 링크 + 원문 글(canonical) 링크.
  - 이 도구가 만든 글(front matter 에 source_num 이 있는 파일)만 지우거나 덮어쓴다. 손으로 쓴 글은 건드리지 않는다.

사용:
  python3 tools/export_from_dongheon.py                 # 내보내기 + 본문 무수정 자체검증
  python3 tools/export_from_dongheon.py --check-links   # 위에 더해 모든 외부 링크·이미지를 GET 으로 확인(200 아니면 실패)
  python3 tools/export_from_dongheon.py --src <publish 폴더>   (또는 환경변수 JALHANA_BLOG_PUBLISH)

표준 라이브러리만 쓴다(pip 설치 없음). 원천 폴더는 읽기만 하고 아무것도 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import json
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
MARK = "<!-- jalhana-mirror:related -->"
IMG_RE = re.compile(r"(!\[[^\]]*\]\()(/blog/images/)")
IMG_ABS_RE = re.compile(r"(!\[[^\]]*\]\()" + re.escape(SITE) + r"(/blog/images/)")
NAME_RE = re.compile(r"\[(\d+)\]\s*(.+?)(?:\s*#(\S+))?\.md$")
ALLOWED_PREFIXES = (SITE + "/", "https://github.com/lime38/")


def canonical_url(slug: str) -> str:
    return f"{SITE}/blog/{slug}"


def plain(text: str, n: int = 150) -> str:
    """build_blog._plain 과 같은 설명문 추출(이미지·링크·제목 제거 후 앞 n자)."""
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"^#+\s.*$", "", s, flags=re.M)
    s = re.sub(r"[*#>\-·\[\]]", " ", s)
    return " ".join(s.split())[:n]


def load_posts(src: Path) -> list[dict]:
    meta = json.loads((src / "_dates.json").read_text(encoding="utf-8"))
    dates = {k: v for k, v in meta.items() if re.match(r"^\d+$", k)}
    tags = meta.get("tags", {})
    slugs = meta.get("slugs", {})
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
        body = f.read_text(encoding="utf-8")
        posts.append({"num": num, "title": title, "tag": tag, "date": date,
                      "slug": slugs.get(num, num), "body": body, "file": f.name})
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


def front_matter(post: dict) -> str:
    j = lambda s: json.dumps(s, ensure_ascii=False)  # JSON 문자열 = 유효한 YAML 큰따옴표 문자열
    tags = "[" + ", ".join(j(t) for t in [post["tag"]] if t) + "]"
    return ("---\n"
            "layout: post\n"
            f"title: {j(post['title'])}\n"
            f"date: {post['date']}\n"
            f"tags: {tags}\n"
            f"canonical_url: {canonical_url(post['slug'])}\n"
            f"description: {j(plain(post['body']))}\n"
            f"source_num: {j(post['num'])}\n"
            "---\n")


def norm_body(body: str) -> str:
    return body if body.endswith("\n") else body + "\n"


def render_post(post: dict, related: dict) -> str:
    body = IMG_RE.sub(r"\1" + SITE + r"\2", post["body"])
    return front_matter(post) + norm_body(body) + related_block(post, related)


def write_if_changed(path: Path, text: str) -> str:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return "unchanged"
    state = "updated" if path.exists() else "created"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return state


def export(src: Path, out: Path, related: dict) -> tuple[list[dict], dict]:
    posts = load_posts(src)
    posts_dir = out / "_posts"
    posts_dir.mkdir(exist_ok=True)
    counts = {"created": 0, "updated": 0, "unchanged": 0, "removed": 0}
    keep = set()
    for p in posts:
        name = f"{p['date']}-{p['slug']}.md"
        keep.add(name)
        counts[write_if_changed(posts_dir / name, render_post(p, related))] += 1
    for f in sorted(posts_dir.glob("*.md")):  # 이 도구가 만든 글만 정리
        if f.name not in keep and re.search(r'^source_num: ', f.read_text(encoding="utf-8"), re.M):
            f.unlink()
            counts["removed"] += 1
    return posts, counts


def verify_bodies(posts: list[dict], out: Path) -> list[str]:
    """미러된 본문이 원문과 같은지(이미지 경로 복원 후) 대조한다."""
    bad = []
    for p in posts:
        f = out / "_posts" / f"{p['date']}-{p['slug']}.md"
        text = f.read_text(encoding="utf-8")
        m = re.match(r"---\n.*?\n---\n", text, re.S)
        if not m or "\n" + MARK + "\n" not in text:
            bad.append(f"{f.name}: front matter 또는 관련 보기 표지 없음")
            continue
        mirrored = text[m.end():text.index("\n" + MARK + "\n")]
        mirrored = IMG_ABS_RE.sub(r"\1\2", mirrored)
        if mirrored != norm_body(p["body"]):
            bad.append(f"{f.name}: 본문이 원문과 다름")
    return bad


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def http_status(url: str, timeout: int = 25) -> int:
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "jalhana-pages-link-check/1.0"})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def check_links(posts: list[dict], related: dict) -> int:
    urls: dict[str, str] = {}
    for p in posts:
        urls[canonical_url(p["slug"])] = f"정본 {p['slug']}"
        for ln in related.get("posts", {}).get(p["slug"], related.get("default", [])):
            urls.setdefault(ln["url"], "관련 보기")
        for m in re.finditer(r"!\[[^\]]*\]\((/blog/images/[^)\s]+)\)", p["body"]):
            urls.setdefault(SITE + m.group(1), "이미지")
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
    args = ap.parse_args()

    if not (args.src / "_dates.json").exists():
        print(f"원천을 찾을 수 없습니다: {args.src}", file=sys.stderr)
        return 2
    related = load_related(args.out / "tools" / "related_links.json")
    posts, counts = export(args.src, args.out, related)
    print(f"글 {len(posts)}건 — " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    bad = verify_bodies(posts, args.out)
    for b in bad:
        print("검증 실패:", b, file=sys.stderr)
    if bad:
        return 1
    print("본문 무수정 검증 통과(이미지 경로만 절대주소로 치환)")
    if args.check_links and check_links(posts, related):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
