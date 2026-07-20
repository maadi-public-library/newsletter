#!/usr/bin/env python3
"""
generate.py  —  Maadi Public Library Newsletter Auto-Generator
============================================================
실행 위치: 레포지토리 루트
동작:
  1. assets/covers/ 에서 YYYY-MM-cover.* 파일 목록 수집
  2. 대응하는 PDF가 YYYY/MM/ 에 있는지 확인
  3. index.html  재생성
  4. viewer/YYYY-MM-ar_view.html  재생성 (없는 것만)

파일 네이밍 규칙 (반드시 지켜야 함):
  커버 이미지 : assets/covers/YYYY-MM-cover.jpg  (또는 .png)
  다운로드 PDF: YYYY/MM/maadi-YYYY-MM-newsletter-ar_down.pdf
  뷰어 PDF    : YYYY/MM/maadi-YYYY-MM-newsletter-ar_view.pdf
"""

import os, re, json
from pathlib import Path
from datetime import datetime

# ── 월 이름 매핑 ──────────────────────────────────────────────
MONTH_EN = {
    "01":"January","02":"February","03":"March","04":"April",
    "05":"May","06":"June","07":"July","08":"August",
    "09":"September","10":"October","11":"November","12":"December",
}
MONTH_AR = {
    "01":"يناير","02":"فبراير","03":"مارس","04":"أبريل",
    "05":"مايو","06":"يونيو","07":"يوليو","08":"أغسطس",
    "09":"سبتمبر","10":"أكتوبر","11":"نوفمبر","12":"ديسمبر",
}

ROOT = Path(__file__).parent.parent   # 레포 루트

# ── 통계(GoatCounter) 설정 ────────────────────────────────────
# https://www.goatcounter.com/ 에서 가입 후 받은 사이트 코드를 넣으세요.
# 예: 사이트 주소가 https://maadi-newsletter.goatcounter.com 이면 코드는 "maadi-newsletter"
GOATCOUNTER_CODE = "maadi-public-library"
GOATCOUNTER_SCRIPT = f"""\
  <script data-goatcounter="https://{GOATCOUNTER_CODE}.goatcounter.com/count"
          async src="//gc.zgo.at/count.js"></script>"""

# 페이스북에서 이미 집계된 기존 조회수/다운로드수 (GoatCounter 실측치에 더해서 표시)
FACEBOOK_TOTAL_VISITOR_OFFSET = 6500  # 전체 방문자수 오프셋

FACEBOOK_OFFSETS = {
    # "YYYY-MM": (조회수, 다운로드수)
    "2025-12": (1950, 720),
    "2026-01": (1022, 501),
    "2026-02": (2052, 892),
    "2026-03": (1954, 458),
    "2026-04": (1580, 351),
    "2026-05": (1003, 458),
    "2026-06": (2043, 825),
}

# ── 1. 커버 이미지 스캔 ──────────────────────────────────────
cover_pattern = re.compile(r"^(\d{4})-(\d{2})-cover\.(jpg|jpeg|png|webp)$", re.IGNORECASE)

issues = []   # { year, month, cover_ext, has_down, has_view }
seen = set()  # 중복 방지

covers_dir = ROOT / "assets" / "covers"
if covers_dir.exists():
    for f in sorted(covers_dir.iterdir()):
        m = cover_pattern.match(f.name)
        if not m:
            continue
        year, month, ext = m.group(1), m.group(2), m.group(3)

        if (year, month) in seen:
            print(f"  [skip] Duplicate cover ignored: {f.name}")
            continue
        seen.add((year, month))

        pdf_dir = ROOT / year / month
        has_down = (pdf_dir / f"maadi-{year}-{month}-newsletter-ar_down.pdf").exists()
        has_view = (pdf_dir / f"maadi-{year}-{month}-newsletter-ar_view.pdf").exists()

        issues.append({
            "year": year,
            "month": month,
            "cover_ext": ext.lower(),
            "has_down": has_down,
            "has_view": has_view,
        })

# 최신순 정렬
issues.sort(key=lambda x: (x["year"], x["month"]), reverse=True)

print(f"[generate.py] Found {len(issues)} issues: " +
      ", ".join(f"{i['year']}-{i['month']}" for i in issues))

# ── 2. 뷰어 HTML 생성 ────────────────────────────────────────
viewer_dir = ROOT / "viewer"
viewer_dir.mkdir(exist_ok=True)

VIEWER_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{month_en} {year} - {month_ar} {year}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
{goatcounter_script}
  <style>
    html,body{{height:100%;margin:0;overflow:hidden;}}
    body{{background:#f4f6f8;font-family:Arial,sans-serif;display:flex;flex-direction:column;align-items:center;}}
    header{{padding:12px;font-size:16px;font-weight:bold;color:#1F3C6D;}}
    #viewer{{position:relative;width:100%;max-width:800px;height:calc(100vh - 120px);
             margin:0 auto;background:#fff;overflow:hidden;
             display:flex;align-items:flex-start;justify-content:center;}}
    canvas{{display:block;transition:opacity .2s ease;opacity:1;}}
    #loading{{position:absolute;inset:0;background:rgba(255,255,255,.9);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              z-index:10;font-size:14px;color:#1F3C6D;}}
    .spinner{{width:32px;height:32px;border:4px solid #dce3ec;border-top-color:#0B5FA5;
              border-radius:50%;animation:spin .8s linear infinite;margin-bottom:10px;}}
    @keyframes spin{{to{{transform:rotate(360deg);}}}}
    .controls{{margin:12px 0 20px;}}
    button{{padding:8px 14px;margin:0 6px;font-size:14px;cursor:pointer;}}
    button:disabled{{opacity:.4;cursor:not-allowed;}}
  </style>
</head>
<body>
<header>{month_en} {year} - {month_ar} {year}</header>
<div id="viewer">
  <div id="loading"><div class="spinner"></div><div>Loading newsletter…</div></div>
  <canvas id="pdf-canvas"></canvas>
</div>
<div class="controls">
  <button id="prev">◀ Previous</button>
  <button id="next">Next ▶</button>
</div>
<script>
const url="../{year}/{month}/maadi-{year}-{month}-newsletter-ar_view.pdf";
let pdfDoc=null,pageNum=1,baseScale=null,rendering=false;
const container=document.getElementById("viewer");
const canvas=document.getElementById("pdf-canvas");
const ctx=canvas.getContext("2d");
const loading=document.getElementById("loading");

pdfjsLib.getDocument({{url,disableStream:false,disableAutoFetch:false}}).promise.then(pdf=>{{
  pdfDoc=pdf; renderPage(pageNum);
}});

function renderPage(num){{
  if(rendering||!pdfDoc)return;
  rendering=true;
  canvas.style.opacity=0;
  loading.style.display="flex";
  pdfDoc.getPage(num).then(page=>{{
    const uv=page.getViewport({{scale:1}});
    if(!baseScale){{
      if(!container.clientWidth||!container.clientHeight){{
        rendering=false; requestAnimationFrame(()=>renderPage(num)); return;
      }}
      const sw=container.clientWidth/uv.width;
      const sh=container.clientHeight/uv.height;
      baseScale=(window.innerWidth<=768)?sw:sh;
    }}
    const es=(num===1)?baseScale*.9:baseScale;
    const vp=page.getViewport({{scale:es}});
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.floor(vp.width*dpr);
    canvas.height=Math.floor(vp.height*dpr);
    canvas.style.width=Math.floor(vp.width)+"px";
    canvas.style.height=Math.floor(vp.height)+"px";
    ctx.setTransform(dpr,0,0,dpr,0,0);
    page.render({{canvasContext:ctx,viewport:vp}}).promise.then(()=>{{
      rendering=false; canvas.style.opacity=1;
      loading.style.display="none"; updateButtons();
    }});
  }});
}}
document.getElementById("prev").onclick=()=>{{if(pageNum>1){{pageNum--;renderPage(pageNum);}}}};
document.getElementById("next").onclick=()=>{{if(pageNum<pdfDoc.numPages){{pageNum++;renderPage(pageNum);}}}};
function updateButtons(){{
  document.getElementById("prev").disabled=(pageNum<=1);
  document.getElementById("next").disabled=(pageNum>=pdfDoc.numPages);
}}
const ro=new ResizeObserver(()=>{{baseScale=null;renderPage(pageNum);}});
ro.observe(container);
</script>
</body>
</html>
"""

for issue in issues:
    if not issue["has_view"]:
        continue   # 뷰어 PDF 없으면 뷰어 HTML 불필요
    y, mo = issue["year"], issue["month"]
    viewer_path = viewer_dir / f"{y}-{mo}-ar_view.html"
    if viewer_path.exists():
        continue   # 이미 있으면 건너뜀 (덮어쓰지 않음)
    content = VIEWER_TEMPLATE.format(
        year=y, month=mo,
        month_en=MONTH_EN[mo],
        month_ar=MONTH_AR[mo],
        goatcounter_script=GOATCOUNTER_SCRIPT,
    )
    viewer_path.write_text(content, encoding="utf-8")
    print(f"  [viewer] Created {viewer_path.name}")

# ── 3. index.html 재생성 ──────────────────────────────────────
def card_html(issue):
    y, mo = issue["year"], issue["month"]
    cover_src = f"assets/covers/{y}-{mo}-cover.{issue['cover_ext']}"
    viewer_href = f"viewer/{y}-{mo}-ar_view.html"
    down_href   = f"{y}/{mo}/maadi-{y}-{mo}-newsletter-ar_down.pdf"

    view_btn = (f'<a class="button" href="{viewer_href}" target="_blank">View</a>'
                if issue["has_view"] else
                '<span class="button btn-disabled">View</span>')
    down_btn = (f'<a class="button" href="{down_href}" download '
                f'data-goatcounter-click="download-{y}-{mo}">Download</a>'
                if issue["has_down"] else
                '<span class="button btn-disabled">Download</span>')

    # 실측치(GoatCounter) + 페이스북 기존 집계 오프셋을 더해서 표시할 placeholder
    fb_views, fb_downloads = FACEBOOK_OFFSETS.get(f"{y}-{mo}", (0, 0))
    view_badge = (f'<span class="stat-badge" '
                  f'data-gc-path="{viewer_href}" data-gc-offset="{fb_views}" '
                  f'data-gc-label="👁 views">👁 {fb_views}</span>'
                  if issue["has_view"] else "")
    down_badge = (f'<span class="stat-badge" '
                  f'data-gc-path="download-{y}-{mo}" data-gc-offset="{fb_downloads}" '
                  f'data-gc-label="⬇ downloads">⬇ {fb_downloads}</span>'
                  if issue["has_down"] else "")

    return f"""\
<div class="news-card" data-date="{y}-{mo}">
  <div class="news-cover">
    <a href="{viewer_href}" target="_blank">
      <img src="{cover_src}" alt="{MONTH_EN[mo]} {y}" loading="lazy">
    </a>
  </div>
  <div class="news-content">
    <div class="month">{MONTH_EN[mo]} {y}</div>
    <div class="month-ar">{MONTH_AR[mo]} {y}</div>
    <div class="button-group">
      {view_btn}
      {view_badge}
      {down_btn}
      {down_badge}
    </div>
  </div>
</div>"""

cards_html = "\n\n".join(card_html(i) for i in issues)

# 생성 시각 주석
now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

INDEX_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Maadi Public Library | Newsletter Archive</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- AUTO-GENERATED by scripts/generate.py on {now} — DO NOT EDIT MANUALLY -->
{GOATCOUNTER_SCRIPT}

<style>
:root{{
  --primary-blue:#0B5FA5;
  --dark-blue:#1F3C6D;
  --light-gray:#F4F6F8;
}}
body{{
  margin:0;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  background:var(--light-gray);
  color:#222;
}}
.container{{
  max-width:1100px;
  margin:0 auto;
  background:#fff;
  padding:30px 20px 60px;
}}
.header-bar{{
  display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;
}}
.header-left,.header-right{{width:180px;display:flex;align-items:center;}}
.header-left{{justify-content:flex-start;}}
.header-right{{justify-content:flex-end;}}
.header-left img,.header-right img{{max-height:60px;}}
.header-center{{flex:1;text-align:center;}}
.header-center h1{{margin:0;font-size:32px;color:var(--dark-blue);}}
.archive-bar{{
  background:var(--primary-blue);color:#fff;text-align:center;
  font-size:22px;font-weight:600;padding:14px 10px;
  border-radius:8px;margin:20px 0 6px;
}}
.library-photo{{width:100%;max-height:420px;overflow:hidden;border-radius:8px;margin:0 0 25px;}}
.library-photo img{{width:100%;height:auto;display:block;}}
.year-section{{margin-top:30px;}}
.year-title{{
  font-size:24px;font-weight:700;color:var(--dark-blue);
  border-bottom:3px solid var(--primary-blue);padding-bottom:6px;margin-bottom:18px;
}}
.news-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;}}
.news-card{{
  display:flex;align-items:center;gap:12px;padding:14px 16px;
  border-radius:10px;background:#f9fafc;
  box-shadow:0 4px 14px rgba(0,0,0,.05);transition:.2s ease;
}}
.news-card:hover{{transform:translateY(-3px);box-shadow:0 8px 22px rgba(0,0,0,.08);}}
.news-cover{{
  width:100px;flex-shrink:0;aspect-ratio:3/4;border-radius:6px;
  overflow:hidden;background:#fff;display:flex;align-items:center;justify-content:center;
}}
.news-cover img{{width:100%;height:100%;object-fit:contain;}}
.news-content{{flex:1;display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px;}}
.month{{font-size:18px;font-weight:700;color:var(--dark-blue);}}
.month-ar{{font-size:14px;font-weight:650;color:#555;}}
.button-group{{display:flex;flex-direction:column;gap:6px;align-items:center;}}
.stat-badge{{font-size:14px;font-weight:700;color:var(--dark-blue);
             background:#e7f0fb;border:1px solid #cfe0f3;border-radius:14px;
             padding:5px 14px;display:inline-block;letter-spacing:.2px;}}
.button{{
  font-size:13px;padding:7px 18px;border-radius:6px;
  background:var(--primary-blue);color:#fff !important;
  text-decoration:none;font-weight:600;transition:.2s ease;
  min-width:110px;text-align:center;display:inline-block;
}}
.button:hover{{background:#083d6b;}}
.btn-disabled{{
  font-size:13px;padding:7px 18px;border-radius:6px;
  background:#bbb;color:#fff;font-weight:600;
  min-width:110px;text-align:center;display:inline-block;cursor:not-allowed;
}}
footer{{margin-top:60px;padding-top:20px;border-top:1px solid #eee;text-align:center;}}
.footer-credit{{font-size:13px;color:#555;}}
.footer-credit img{{height:13px;vertical-align:middle;margin-left:6px;}}
@media(max-width:1000px){{.news-grid{{grid-template-columns:repeat(2,1fr);}}}}
@media(max-width:768px){{
  .header-bar{{flex-direction:column;gap:15px;}}
  .header-left,.header-right{{width:auto;justify-content:center;}}
  .news-grid{{grid-template-columns:1fr;}}
  .news-card{{flex-direction:column;}}
  .library-photo{{height:190px;}}
}}
</style>
</head>
<body>
<div class="container">

<div class="header-bar">
  <div class="header-left"><img src="assets/logos/ESCD_logo.png" alt="ESCD"></div>
  <div class="header-center">
    <h1>Maadi Public Library (مكتبة المعادي العامة)</h1>
  </div>
  <div class="header-right"><img src="assets/logos/Maadi_Public_Library_logo.png" alt="Library"></div>
</div>

<div class="archive-bar">Monthly Newsletter Archive (أرشيف النشرة الشهرية)</div>
<div style="text-align:center;margin:6px 0 20px;">
  <span class="stat-badge" data-gc-path="TOTAL" data-gc-offset="{FACEBOOK_TOTAL_VISITOR_OFFSET}"
        data-gc-label="👥 site visits">👥 {FACEBOOK_TOTAL_VISITOR_OFFSET}</span>
</div>

<div class="library-photo">
  <img src="assets/images/library_wide.jpg" alt="Maadi Public Library">
</div>

<div id="all-news">
{cards_html}
</div>

<footer>
<p class="footer-credit">
This publication is produced in collaboration with
<a href="https://www.koica.go.kr/sites/koica_en/index.do" target="_blank">
<img src="assets/logos/KOICA_logo_s.png" alt="KOICA">
</a>
</p>
</footer>

</div>

<script>
/* 연도별 섹션 자동 그룹화 */
const container=document.getElementById("all-news");
const cards=Array.from(container.querySelectorAll(".news-card"));
cards.sort((a,b)=>b.dataset.date.localeCompare(a.dataset.date));
const grouped={{}};
cards.forEach(card=>{{
  const year=card.dataset.date.split("-")[0];
  if(!grouped[year])grouped[year]=[];
  grouped[year].push(card);
}});
container.innerHTML="";
Object.keys(grouped).sort((a,b)=>b-a).forEach(year=>{{
  const section=document.createElement("div");
  section.className="year-section";
  const title=document.createElement("div");
  title.className="year-title";
  title.textContent=year;
  const grid=document.createElement("div");
  grid.className="news-grid";
  grouped[year].forEach(card=>grid.appendChild(card));
  section.appendChild(title);
  section.appendChild(grid);
  container.appendChild(section);
}});

/* 통계: GoatCounter 실측치 + 페이스북 기존 집계 오프셋 합산 표시 */
(function(){{
  const badges = document.querySelectorAll(".stat-badge[data-gc-path]");
  badges.forEach(badge => {{
    const path = badge.dataset.gcPath;
    const offset = parseInt(badge.dataset.gcOffset, 10) || 0;
    const label = badge.dataset.gcLabel;
    const url = "https://{GOATCOUNTER_CODE}.goatcounter.com/counter/" +
                encodeURIComponent(path) + ".json";
    fetch(url).then(r => r.ok ? r.json() : null).then(data => {{
      const live = data && data.count ? parseInt(String(data.count).replace(/[^0-9]/g,""), 10) : 0;
      badge.textContent = label + " " + (live + offset).toLocaleString();
    }}).catch(() => {{ /* 실패 시 페이스북 오프셋만 유지 */ }});
  }});
}})();
</script>
</body>
</html>
"""

index_path = ROOT / "index.html"
index_path.write_text(INDEX_HTML, encoding="utf-8")
print(f"[generate.py] index.html updated with {len(issues)} issues.")
print("[generate.py] Done ✓")
