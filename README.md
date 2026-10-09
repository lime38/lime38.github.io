# 잘하나 기록 (lime38.github.io)

[잘하나(jalhana.com)](https://jalhana.com/) 블로그의 글을 옮겨 싣는 **GitHub Pages(Jekyll) 거울 사이트**입니다.
이 저장소는 동헌 저장소와 별개이며, GitHub Pages 기본 빌드(화이트리스트 플러그인: `jekyll-sitemap`, `jekyll-seo-tag`, `jekyll-feed`)만 씁니다.
`.nojekyll` 은 두지 않습니다.

## 한 방향 거울(one-way mirror)

- 글을 쓰고 고치는 곳은 **jalhana.com/blog 하나**입니다. 이 사이트의 글은 정본의 사본입니다.
- 모든 글은 `canonical_url: https://jalhana.com/blog/<slug>` 를 가집니다. `jekyll-seo-tag` 가 이를 읽어 `<link rel="canonical">`·`og:url` 을 한 번만 냅니다.
  (jalhana.com 의 글 주소는 끝 슬래시가 **없는** 형태이며, 슬래시를 붙이면 404 입니다. 2026-10-09 실측.)
- 글 본문은 원문 그대로입니다(오타 포함). 바뀌는 것은 이미지 줄뿐입니다:
  `![alt](/blog/images/x.webp)` → `![alt](https://jalhana.com/blog/images/x.webp){: loading="lazy" decoding="async" width="W" height="H"}`.
- 글 끝의 「관련 보기」, 글 머리의 정본 안내, 홈·소개의 링크, 푸터의 jalhana.com·국회 잘하나가 jalhana.com 으로 돌아가는 백링크입니다(설명형 앵커 문구).
- `_posts/` 와 `blog/` 는 직접 고치지 않습니다. 아래 도구가 다시 만듭니다.

## 새 글을 옮기는 절차 (exporter 다시 돌리기)

1. 동헌에서 글을 발행합니다(`branding/blog/publish/` 의 원고 + `_dates.json` 의 날짜·슬러그·태그).
2. `tools/related_links.json` 의 `posts` 에 그 글의 슬러그로 「관련 보기」 링크 2~3개를 추가합니다. jalhana.com 에 실제로 있는 페이지만 씁니다.
3. 저장소 루트에서:

   ```
   python3 tools/export_from_dongheon.py --check-links
   python3 tools/build_preview.py
   ```

   - `_posts/*.md`(글), `blog/index.md`·`blog/page/N/index.md`(목록 쪽, 한 쪽 10편)를 다시 만듭니다. 바뀐 것이 없으면 아무 파일도 건드리지 않습니다(멱등).
   - 글마다 `description`(본문 앞부분 110~150자, 문장 끝에서 자름), `image`(og:image), `last_modified_at`, `canonical_url`, `tags` 를 원문에서만 파생해 씁니다.
   - 본문이 원문과 같은지 자체검증하고, `--check-links` 는 모든 링크·이미지를 GET 으로 확인해 200 이 아니면 실패로 끝냅니다.
   - jalhana.com 이 각 글 페이지에서 내는 `og:image` 와 이미지 가로세로는 `tools/seo_cache.json` 에 저장해 두고 없는 것만 가져옵니다.
     jalhana.com 이 글을 재배포해 이미지가 바뀐 뒤에는 `--refresh`, 네트워크 없이 돌리려면 `--offline`.
   - 원천 위치를 바꾸려면 `--src <publish 폴더>` 또는 환경변수 `JALHANA_BLOG_PUBLISH`(기본 `/home/devuh/dongheon/branding/blog/publish`).
4. `preview/index.html` 을 휴대폰에서 열어 확인하고 커밋·푸시합니다.

도구는 모두 표준 라이브러리만 씁니다(pip·gem 설치 없음).

## 구성

```
_config.yml            minima, 플러그인 3종, SEO(locale·logo·social·twitter·defaults), 글 주소 /blog/:title/
index.md about.md      홈(layout: home, 오른쪽 정사각 로고) · 소개
blog/index.md blog/page/N/index.md   글 목록 쪽(exporter 가 생성)
_posts/                exporter 가 만든 글
_layouts/              post.html(정본 안내) · home.html(로고 히어로)
_includes/             head.html(seo + head-custom) · head-custom.html · header.html · footer.html
                       post-list.html · pagination.html · icons/*.svg
_data/links.json       푸터 채널 목록(순서 = 표시 순서)
assets/                main.scss · favicon.ico · favicon-32.png · apple-touch-icon.png · jalhana-512.png · og-default.png
tools/                 export_from_dongheon.py · related_links.json · seo_cache.json · build_preview.py
preview/index.html     Jekyll 없이 보는 단일 HTML 미리보기
robots.txt             전체 허용 + sitemap
```

## SEO

- `{% seo %}`(jekyll-seo-tag)가 title·description·canonical·Open Graph·Twitter 카드·JSON-LD(BlogPosting, 홈은 WebSite + `social` sameAs)를 냅니다. 손으로 쓴 JSON-LD 는 없습니다.
- 글의 og:image = jalhana.com 이 그 글에서 내는 이미지 → 본문 첫 이미지 → `/assets/og-default.png`(1200×630). publisher 로고는 `/assets/jalhana-512.png`.
- `_includes/head-custom.html`: theme-color(라이트/다크), 파비콘·apple-touch-icon·512 아이콘, `hreflang="ko"`, 목록 쪽의 `rel=prev/next`, 글의 `article:section/tag`.
- 소유 확인: `_config.yml` 의 `google_site_verification`, `bing_site_verification` 에 토큰 문자열만 넣으면 meta 가 나옵니다(비어 있으면 아무것도 내지 않습니다).
- 푸터 채널 목록과 `_config.yml` 의 `social.links` 는 같은 프로필 주소를 씁니다(두 곳을 함께 고칩니다).

## 알아 둘 점

- **푸터 채널**: `_data/links.json` 의 `channels` 에 `icon` 이 있으면 `_includes/icons/<icon>.svg` 인라인 SVG 아이콘 버튼(44px 터치 영역, `currentColor`, `aria-label`·`title`·숨김 텍스트),
  없으면 텍스트 링크입니다. `url` 이 빈 항목은 건너뜁니다. 개인 채널에는 `rel="me noopener"`. 아이콘은 [Simple Icons](https://simpleicons.org/) 13.0.0(CC0)이고 브런치만 직접 그린 모노그램입니다.
- **행감팩 지역 페이지**(`/status/2026-haenggam/<지역>/`)는 Cloudflare Access 뒤라 공개되지 않아(302 로그인) 어디에도 링크하지 않았습니다.
- jalhana.com 의 robots.txt 는 일부 AI 크롤러를 막고 있지만, 이 사이트의 robots.txt 는 요청대로 전체 허용입니다.
- 미리보기는 실제 Jekyll 렌더가 아니라 구조·링크 위치·SEO 태그 형식을 보기 위한 근사본입니다(SEO 패널은 jekyll-seo-tag 출력 형식을 흉내 낸 것).
- 글 `how-to-record-lawmakers-work`(015)는 동헌 작업 트리의 미커밋 수정본(이미지 추가)을 옮긴 것이라, jalhana.com 라이브 본문(이미지 없음)과 다릅니다. 재배포되면 exporter 를 `--refresh` 로 다시 돌립니다.
