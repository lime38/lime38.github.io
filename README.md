# 잘하나 기록 (lime38.github.io 초안)

[잘하나(jalhana.com)](https://jalhana.com/) 블로그의 글을 옮겨 싣는 **GitHub Pages(Jekyll) 거울 사이트**의 로컬 초안입니다.
아직 GitHub 저장소를 만들거나 올리지 않았습니다. 이 폴더는 동헌 저장소와 별개의 독립 git 저장소입니다.

## 한 방향 거울(one-way mirror)

- 글을 쓰고 고치는 곳은 **jalhana.com/blog 하나**입니다. 이 사이트의 글은 정본의 사본입니다.
- 모든 글은 `canonical_url: https://jalhana.com/blog/<slug>` 를 가집니다. `jekyll-seo-tag`(minima head)가 이를 읽어
  `<link rel="canonical">` 을 한 번 냅니다. 그래서 검색 엔진에는 중복 글이 아니라 사본으로 전달됩니다.
  (jalhana.com 의 글 주소는 끝 슬래시가 **없는** 형태이며, 슬래시를 붙이면 404 입니다. 2026-10-09 실측.)
- 글 본문은 원문 그대로입니다(오타 포함). 바뀌는 것은 이미지 경로(`/blog/images/...` → `https://jalhana.com/blog/images/...`) 뿐입니다.
- 글 끝의 「관련 보기」 블록, 글 머리의 정본 안내, 홈·소개의 링크, 푸터의 jalhana.com 이 jalhana.com 으로 돌아가는 백링크입니다(설명형 앵커 문구).
- `_posts/` 는 직접 고치지 않습니다. 아래 도구로 다시 만듭니다.

## 새 글을 옮기는 절차

1. 동헌에서 글을 발행합니다(`branding/blog/publish/` + `_dates.json` 의 날짜·슬러그).
2. `tools/related_links.json` 의 `posts` 에 그 글의 슬러그로 「관련 보기」 링크 2~3개를 추가합니다.
   jalhana.com 에 실제로 있는 페이지만 씁니다(없는 주소 금지).
3. 내보내기 + 링크 확인:

   ```
   python3 tools/export_from_dongheon.py --check-links
   ```

   - `_posts/` 를 다시 만듭니다(멱등: 바뀐 것이 없으면 아무 파일도 건드리지 않습니다).
   - 본문이 원문과 같은지 자체검증하고, 모든 링크·이미지를 GET 으로 확인해 200 이 아니면 실패로 끝냅니다.
   - 원천 위치를 바꾸려면 `--src <publish 폴더>` 또는 환경변수 `JALHANA_BLOG_PUBLISH`.
4. `python3 tools/build_preview.py` 로 `preview/index.html` 을 갱신해 휴대폰에서 확인합니다.
5. 커밋합니다. 올리는 일은 사용자가 정할 때 따로 합니다.

도구는 모두 표준 라이브러리만 씁니다(pip·gem 설치 없음).

## 구성

```
_config.yml            minima, jekyll-sitemap / jekyll-seo-tag / jekyll-feed, 글 주소 /blog/:title/
index.md blog.md about.md   홈 · 블로그 · 소개
_includes/             header.html(한국어 메뉴) · footer.html(텍스트 링크) · post-list.html
_layouts/post.html     글 머리에 정본 안내
_data/links.json       푸터 채널 목록(SNS 등)
_posts/                도구가 만든 글(손대지 않음)
assets/main.scss       minima 위 최소 덧칠(다크 모드 포함)
tools/                 export_from_dongheon.py · related_links.json · build_preview.py
preview/index.html     Jekyll 없이 보는 단일 HTML 미리보기(외부 요청 없음)
robots.txt             전체 허용 + sitemap
```

`.nojekyll` 은 두지 않습니다(Jekyll 로 빌드합니다).

## 알아 둘 점

- **푸터**: 사이트 한 줄 + 채널 한 줄(Threads · Instagram · X · LinkedIn · 브런치 · Velog · GitHub · jalhana.com) + 안내문입니다.
  채널은 `_data/links.json` 의 `channels` 에서 오며 `url` 이 빈 항목은 건너뜁니다. 개인 채널에는 `rel="me noopener"` 를 붙였습니다.
  같은 프로필 주소가 `_config.yml` 의 `social.links` 에도 있어 jekyll-seo-tag 가 홈 JSON-LD 의 sameAs 로 냅니다(두 곳을 함께 고칩니다).
- **행감팩 지역 페이지**(`/status/2026-haenggam/<지역>/`)는 현재 Cloudflare Access 뒤라 공개되지 않아(302 로그인) 어디에도 링크하지 않았습니다.
- jalhana.com 의 robots.txt 는 일부 AI 크롤러를 막고 있지만, 이 사이트의 robots.txt 는 요청대로 전체 허용입니다.
- 미리보기(`preview/`)는 실제 Jekyll 렌더가 아니라 구조·링크 위치를 보기 위한 근사본입니다.
