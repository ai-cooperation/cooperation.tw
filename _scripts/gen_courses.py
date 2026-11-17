#!/usr/bin/env python3
"""從 data/courses.yml 生成課程探索總頁與各課程獨立頁。

用法：python3 _scripts/gen_courses.py
產出：courses/index.qmd + courses/<id>.qmd
唯一資料源是 data/courses.yml，不要手改產出檔。
"""
import json
import re
import sys
from html import escape
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "courses.yml"
PROJECTS_DATA = ROOT / "data" / "projects.yml"
OUT_DIR = ROOT / "courses"
APPLY_DIR = ROOT / "apply"
SITE = "https://cooperation.tw"
# GAS 表單後端（_gas/；deployment 固定此 URL，改版用 clasp redeploy 同 ID）
APPLY_ENDPOINT = ("https://script.google.com/macros/s/"
                  "AKfycbwk6xMhzIgrxgONZatAkEDmdzWMYFWYJ31W6Inrlh5bf9PJrJ6"
                  "qrFiUAxRjfi-Vx6w2/exec")


def load_projects() -> dict[str, dict[str, Any]]:
    """讀 projects.yml，回傳 id → project（供課程頁連回作品）。"""
    try:
        with open(PROJECTS_DATA, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        sys.exit(f"無法讀取 projects.yml：{exc}")
    return {p["id"]: p for p in data.get("projects", [])}


def jsonld(p: dict[str, Any]) -> str:
    """每頁一段 @graph：Course + BreadcrumbList + FAQPage。"""
    page_url = f"{SITE}/courses/{p['id']}.html"
    main = {
        "@type": "Course",
        "name": p["name"],
        "description": p["seo_description"],
        "url": page_url,
        "provider": {
            "@type": "Organization", "name": "AI Cooperation", "url": SITE,
        },
    }
    # 規劃中課程尚無任何場次，不得宣告 CourseInstance。
    if p["status"] == "pilot":
        main["hasCourseInstance"] = {
            "@type": "CourseInstance", "courseMode": "onsite",
        }
    graph = [main, {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首頁",
             "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "課程",
             "item": f"{SITE}/courses/"},
            {"@type": "ListItem", "position": 3, "name": p["name"],
             "item": page_url},
        ],
    }]
    graph.append({"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": x["q"],
         "acceptedAnswer": {"@type": "Answer", "text": x["a"]}}
        for x in p["faq"]
    ]})
    payload = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


STATUS_LABEL = {"pilot": "預約試上", "planned": ""}
CATEGORY_ORDER = ("life", "work", "learn")
COURSE_FIELDS = (
    "id", "name", "category", "status", "wave", "tagline", "audience",
    "story", "skills", "deliverables", "abilities", "future_roles",
    "assets", "limits", "faq", "seo_title", "seo_description", "image",
)


def require_keys(value: Any, keys: tuple[str, ...], context: str) -> None:
    """檢查資料物件與必要欄位，錯誤須指出資料位置。"""
    if not isinstance(value, dict):
        sys.exit(f"courses.yml {context} 必須是物件")
    for key in keys:
        if key not in value:
            sys.exit(f"courses.yml {context} 缺少 {key}")


def load_data() -> dict[str, Any]:
    try:
        with open(DATA, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        sys.exit(f"無法讀取 courses.yml：{exc}")
    require_keys(data, ("categories", "courses"), "根節點")
    require_keys(data["categories"], CATEGORY_ORDER, "categories")
    for cid in CATEGORY_ORDER:
        cat = data["categories"][cid]
        context = f"categories.{cid}"
        require_keys(cat, ("name", "hook"), context)
        for key in ("name", "hook"):
            if not isinstance(cat[key], str) or not cat[key].strip():
                sys.exit(f"courses.yml {context}.{key} 必須是非空文字")
    if not isinstance(data["courses"], list) or not data["courses"]:
        sys.exit("courses.yml courses 必須是非空清單")
    seen = set()
    for index, p in enumerate(data["courses"], start=1):
        context = f"courses 第 {index} 筆"
        require_keys(p, COURSE_FIELDS, context)
        for key in COURSE_FIELDS:
            if key in ("wave", "skills", "deliverables", "faq"):
                continue
            if not isinstance(p[key], str) or not p[key].strip():
                sys.exit(f"courses.yml {context}.{key} 必須是非空文字")
        if (not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", p["id"])
                or p["id"] == "index" or p["id"] in seen):
            sys.exit(f"courses.yml {context}.id 無效或重複：{p['id']}")
        seen.add(p["id"])
        if p["category"] not in CATEGORY_ORDER:
            sys.exit(f"courses.yml {context}.category 無效：{p['category']}")
        if p["status"] not in STATUS_LABEL:
            sys.exit(f"courses.yml {context}.status 無效：{p['status']}")
        if type(p["wave"]) is not int or p["wave"] < 1:
            sys.exit(f"courses.yml {context}.wave 必須是正整數")
        for key in ("skills", "deliverables"):
            values = p[key]
            if (not isinstance(values, list) or not values
                    or any(not isinstance(x, str) or not x.strip()
                           for x in values)):
                sys.exit(f"courses.yml {context}.{key} 必須是非空文字清單")
        if not isinstance(p["faq"], list) or not p["faq"]:
            sys.exit(f"courses.yml {context}.faq 必須是非空清單")
        for number, item in enumerate(p["faq"], start=1):
            faq_context = f"{context}.faq 第 {number} 筆"
            require_keys(item, ("q", "a"), faq_context)
            for key in ("q", "a"):
                if not isinstance(item[key], str) or not item[key].strip():
                    sys.exit(f"courses.yml {faq_context}.{key} 必須是非空文字")
    return data


PROJECTS: dict[str, dict[str, Any]] = {}


def axes_html(p: dict[str, Any]) -> str:
    """課程頁的能力軸 tags，連到學習地圖對應區塊。"""
    ids = p.get("axes", [])
    if not ids:
        return ""
    chips = []
    for aid in ids:
        if aid not in AXES:
            sys.exit(f"courses.yml {p['id']}.axes 無效：{aid}")
        chips.append(
            f'<a class="axis-chip axis-chip-sm" href="/method/#axis-{aid.lower()}">'
            f'{aid} {AXES[aid]}</a>')
    return ('<p class="detail-axes">這門課練的能力：'
            f'{"".join(chips)}</p>')


def related_html(p: dict[str, Any]) -> str:
    """課程頁的對應作品卡；沒有已上站的對應系統時退回總覽連結。"""
    ids = p.get("projects", [])
    if not ids:
        return '<a href="/projects/">看全部運行中的專案 →</a>'
    cards = []
    for pid in ids:
        proj = PROJECTS.get(pid)
        if proj is None or proj.get("status") == "coming":
            sys.exit(f"courses.yml {p['id']}.projects 含無效或未上站的專案：{pid}")
        cards.append(
            f'<a class="proof-card" href="/projects/{pid}.html">'
            f'<h3>{escape(proj["name"])}</h3>'
            f'<p>{escape(proj["tagline"])}</p>'
            '<span class="pcard-cta">看這個系統 →</span></a>'
        )
    return (f'<div class="proof-grid cols-{min(len(cards), 3)}">'
            f'{"".join(cards)}</div>')


def status_badge(p: dict[str, Any]) -> str:
    """僅開放試上課程顯示「預約試上」徽章；未開課課程不掛標籤。"""
    if p["status"] != "pilot":
        return ""
    return f'<span class="badge badge-pilot">{STATUS_LABEL["pilot"]}</span>'


def card_html(p: dict[str, Any]) -> str:
    # 課名優先於痛點句：第一眼先看到課名（agy 審查 #10）。
    inner = (
        f'<img src="/assets/images/{escape(p["image"])}"'
        f' alt="{escape(p["name"])}" loading="lazy">'
        '<div class="ccard-body">'
        f'<div class="ccard-head"><h3>{escape(p["name"])}</h3>'
        f'{status_badge(p)}</div>'
        f'<p class="ccard-pain">{escape(p["tagline"])}</p>'
        f'<p class="ccard-meta">適合：{escape(p["audience"])}</p>'
        f'<p class="ccard-take">帶走：{escape(p.get("take", p["deliverables"][0]))}</p>'
        '</div>'
    )
    return (
        f'<a class="ccard reveal-fx" href="/courses/{p["id"]}.html">'
        f'{inner}</a>'
    )


AXES = {
    "A": "看懂文件與影像",
    "B": "把資料變成系統",
    "C": "建自己的知識庫",
    "D": "讓 AI 自動運轉",
}

FUNNEL_HERO = """<section class="hero hero-lite hero-lines">
<div class="hero-inner">
<span class="hero-kicker reveal-fx">情境式 AI 實作課程</span>
<h1 class="reveal-fx" style="--rd:.05s">從你在意的問題開始<br>做出<em>自己的第一個 AI 應用</em></h1>
<p class="hero-sub reveal-fx" style="--rd:.15s">不必先懂工具 <br class="br-m">從真實的生活與工作情境進來<br>完成一個帶得走的作品 <br class="br-m">再看見背後的技術與路徑</p>
</div>
</section>"""

# 三入口卡的補充描述與配圖
ENTR_META = {
    "life": {"image": "cat-life.png",
             "desc": "照顧家人、毛孩與自己的家，AI 可以多幫一點——"
                     "智慧門鈴、遠距照護、寵物健康、裝修模擬。"},
    "work": {"image": "cat-work.png",
             "desc": "重複的流程、看不完的資料，做一個自己的小系統——"
                     "訂單系統、用電分析、會議追蹤、產業情報。"},
    "learn": {"image": "cat-learn.png",
              "desc": "讓學習真的發生、讓研究想法變成可執行的計畫——"
                      "學習教練、研究方法。"},
}


def entrances_html(data: dict[str, Any]) -> str:
    cards = []
    for i, cid in enumerate(CATEGORY_ORDER):
        meta = ENTR_META[cid]
        delay = f' style="--rd:.{i * 8:02d}s"' if i else ""
        cards.append(
            f'<a class="entr-card reveal-fx"{delay} href="#cat-{cid}">'
            f'<img src="/assets/images/{meta["image"]}" alt="" loading="lazy">'
            f'<h3>{escape(data["categories"][cid]["name"])}</h3>'
            f'<p>{escape(meta["desc"])}</p>'
            '<span class="entr-cta">系列課程 →</span></a>')
    return (
        '<section class="home-section" id="find">\n'
        '<h2 class="reveal-fx">你最近在意哪一種問題</h2>\n'
        '<p class="section-lead reveal-fx">選一個入口 '
        '<br class="br-m">找到從你的情境出發的課程</p>\n'
        f'<div class="entr-grid">\n{chr(10).join(cards)}\n</div>\n</section>')


ABILITY_STRIP = """<section class="home-section">
<h2 class="reveal-fx">情境式課程練的是四個關鍵能力</h2>
<p class="section-lead reveal-fx">情境是入口，能力才是你帶走的東西。每門課標示它練哪幾個。</p>
<div class="axis-strip reveal-fx">
<a class="axis-chip" href="/method/#axis-a">A 看懂文件與影像</a>
<a class="axis-chip" href="/method/#axis-b">B 把資料變成系統</a>
<a class="axis-chip" href="/method/#axis-c">C 建自己的知識庫</a>
<a class="axis-chip" href="/method/#axis-d">D 讓 AI 自動運轉</a>
<a class="axis-more" href="/method/">看完整學習地圖 →</a>
</div>
</section>"""

STEPS_BAND = """<section class="home-section">
<h2 class="reveal-fx">課怎麼上</h2>
<p class="section-lead reveal-fx">每門課都用同一套方法：場景任務進、作品驗收出。</p>
<div class="steps-grid">
<div class="step-item reveal-fx"><h3>扮演一個真實角色</h3><p>你是情境裡的需求提出者——老闆、照顧者、老師、分析師，課程從你的任務開始。</p></div>
<div class="step-item reveal-fx" style="--rd:.08s"><h3>三級深度自己選</h3><p>Level 1 用現成示範完成作品；Level 2 修改規則與資料；Level 3 設計跨工具整合。不會寫程式可以從 Level 1 走到 3。</p></div>
<div class="step-item reveal-fx" style="--rd:.16s"><h3>作品驗收才算學會</h3><p>每門課結束時，你帶走一件自己驗收過、隔天就拿得出來用的作品。</p></div>
</div>
</section>"""

PROOF_BAND = """<div class="proof-band">
<div class="proof-inner">
<h2 class="reveal-fx">課程背後是真實運轉的系統</h2>
<p class="section-lead reveal-fx">我們不用假案例教學。課堂上的教材，來自這些每天真實運轉、在站上公開的系統。</p>
<div class="proof-grid">
<a class="proof-card reveal-fx" href="/projects/insurance-kb.html"><span class="proof-num">每日</span><h3>保險業知識庫</h3><p>覆蓋台日韓港與東南亞，每天自動累積的市場情報</p></a>
<a class="proof-card reveal-fx" style="--rd:.06s" href="/projects/ifrs-s2.html"><span class="proof-num">188 份</span><h3>IFRS S2 合規知識庫</h3><p>永續揭露差距分析，逐條對照原文出處</p></a>
<a class="proof-card reveal-fx" style="--rd:.12s" href="/projects/agent-kb.html"><span class="proof-num">12 模組</span><h3>Agent KB 教學知識庫</h3><p>學員上課用的同一套系統</p></a>
<a class="proof-card reveal-fx" style="--rd:.18s" href="/projects/paperlab.html"><span class="proof-num">運行中</span><h3>PaperLab</h3><p>從研究想法到論文初稿的生產系統</p></a>
</div>
<p class="proof-more reveal-fx"><a href="/projects/">看全部運行中的專案 →</a></p>
</div>
</div>"""

ENT_BAND = """<section class="ent-band" id="enterprise">
<div class="ent-inner reveal-fx">
<div>
<h2>企業內訓</h2>
<p class="ent-lead">培育能帶領部門完成工作改善的種子人才</p>
<p>六小時從入門到自動化的四階段實作，用你們自己的工作流程當教材，學員結業時直接交付部門可以用的改善方案。</p>
<p class="ent-specs">小班實作｜六小時四階段｜學員無須程式背景</p>
</div>
<a class="btn-primary" href="/apply/enterprise.html">洽詢內訓方案</a>
</div>
</section>"""


def gen_listing(data: dict[str, Any]) -> None:
    # 課程區首頁＝完整情境漏斗：切入 → 能力 → 九課 → 證據 → 內訓。
    # page-layout custom + home-section 容器，與首頁同寬（66rem）。
    parts = [
        "---",
        'pagetitle: "從你的問題找課程｜情境式 AI 實作課程"',
        'description: "不必先懂工具。從生活與家庭、工作與產業、教育與研究的真實情境進來，練四個關鍵能力，做出帶得走的 AI 作品。"',
        "page-layout: custom",
        "toc: false",
        "---",
        "",
        "```{=html}",
        FUNNEL_HERO,
        entrances_html(data),
        '<section class="home-section"><h2 class="reveal-fx">'
        '情境式課程</h2>'
        '<p class="section-lead reveal-fx">每門課從一個真實的痛點開始，'
        '結束時你會帶走一件自己驗收過的作品。</p></section>',
    ]
    for cid in CATEGORY_ORDER:
        cat = data["categories"][cid]
        items = [p for p in data["courses"] if p["category"] == cid]
        parts.append('<section class="home-section home-section-tight">')
        parts.append(
            f'<h3 class="cgroup-label reveal-fx" id="cat-{cid}">'
            f'{escape(cat["name"])}</h3>')
        parts.append(
            f'<p class="section-lead reveal-fx">{escape(cat["hook"])}</p>')
        parts.append('<div class="cgrid">')
        parts.extend(card_html(p) for p in items)
        parts.append("</div>")
        parts.append("</section>")
    parts += [ABILITY_STRIP, STEPS_BAND, PROOF_BAND, ENT_BAND, "```", ""]
    (OUT_DIR / "index.qmd").write_text("\n".join(parts), encoding="utf-8")


def gen_detail(p: dict[str, Any], cat: dict[str, str]) -> None:
    # 未開課只收開課興趣；兩種狀態均不得產生報名或購買入口。
    if p["status"] == "pilot":
        label, subject, css = "預約試上", "試上申請", "btn-primary"
        explanation = ("小班體驗場陸續安排，時間、時數與費用會在"
                       "通知信中說明，登記後依序通知。")
    else:
        label, subject, css = "開課時通知我", "開課通知", "btn-ghost-dark"
        explanation = ("這門課尚未排定場次；想上的人多的課會先開，"
                       "確定開課會第一時間通知您。")
    href = f'/apply/?course={p["id"]}'
    entry_btn = f'<a class="{css}" href="{href}">{label}</a>'
    # 表單是主通道；mailto 當退路。
    mail_fallback = ('<p class="detail-cta-note">不方便填表單？直接寫信到 '
                     'ai@cooperation.tw，標題註明「'
                     f'{subject}：{escape(p["name"])}」。</p>')
    gains_html = "".join(f"<li>{escape(g)}</li>" for g in p["deliverables"])
    skills_html = "".join(f"<li>{escape(t)}</li>" for t in p["skills"])
    lines = [
        "---",
        f'pagetitle: {json.dumps(p["seo_title"], ensure_ascii=False)}',
        f'description: {json.dumps(p["seo_description"], ensure_ascii=False)}',
        "page-layout: custom",
        "toc: false",
        "---",
        "",
        "```{=html}",
        '<article class="detail">',
        '<header class="detail-head reveal-fx">',
        f'{status_badge(p)}'
        f' <span class="badge badge-cat">{escape(cat["name"])}</span>',
        f'<h1>{escape(p["name"])}</h1>',
        f'<p class="detail-tagline">{escape(p["tagline"])}</p>',
        f'<p class="detail-audience">適合：{escape(p["audience"])}</p>',
        axes_html(p),
        entry_btn,
        "</header>",
        '<img class="detail-hero reveal-fx"'
        f' src="/assets/images/{escape(p["image"])}"'
        f' alt="{escape(p["name"])}">',
        '<section class="detail-block reveal-fx">',
        "<h2>這門課的情境</h2>",
        f'<p>{escape(p["story"])}</p>',
        "</section>",
        '<section class="detail-block reveal-fx">',
        "<h2>你會做出什麼（可帶走的作品）</h2>",
        f'<ul class="detail-gains">{gains_html}</ul>',
        "</section>",
        '<section class="detail-block reveal-fx">',
        "<h2>會用到的 AI 技巧</h2>",
        f'<ul class="detail-gains">{skills_html}</ul>',
        "</section>",
        '<section class="detail-block reveal-fx">',
        "<h2>你會帶走的能力</h2>",
        f'<p>{escape(p["abilities"])}</p>',
        "</section>",
        '<section class="detail-block reveal-fx">',
        "<h2>之後可以往哪走</h2>",
        f'<p>{escape(p["future_roles"])}。</p>',
        "</section>",
        '<section class="detail-block reveal-fx">',
        "<h2>這門課背後的真實系統</h2>",
        f'<p>{escape(p["assets"])}</p>',
        related_html(p),
        "</section>",
        '<section class="detail-block detail-limits reveal-fx">',
        "<h2>誠實界線</h2>",
        f'<p>{escape(p["limits"])}</p>',
        "</section>",
    ]
    faq_html = "".join(
        f'<div class="faq-item"><h3>{escape(x["q"])}</h3>'
        f'<p>{escape(x["a"])}</p></div>' for x in p["faq"]
    )
    lines += [
        '<section class="detail-block reveal-fx">',
        "<h2>常見問題</h2>",
        f'<div class="faq-list">{faq_html}</div>',
        "</section>",
        '<section class="detail-block reveal-fx">',
        entry_btn,
        f"<p>{explanation}</p>",
        mail_fallback,
        "</section>",
        f'<script type="application/ld+json">{jsonld(p)}</script>',
        '<p class="detail-back"><a href="/courses/">← 回課程探索</a></p>',
        "</article>",
        "```",
        "",
    ]
    (OUT_DIR / f'{p["id"]}.qmd').write_text("\n".join(lines), encoding="utf-8")


def apply_page_js(payload_js: str, lead_type: str) -> str:
    """表單送出共用 JS：寫入 payload、no-cors 送 GAS、GA4 轉換事件、切換成功畫面。"""
    return f"""<script>
(function() {{
  var form = document.getElementById('apply-form');
  if (!form) return;
  form.addEventListener('submit', function(ev) {{
    ev.preventDefault();
    var btn = form.querySelector('button[type="submit"]');
    var data = {payload_js};
    btn.disabled = true;
    btn.textContent = '送出中…';
    fetch('{APPLY_ENDPOINT}', {{
      method: 'POST', mode: 'no-cors',
      headers: {{ 'Content-Type': 'text/plain;charset=utf-8' }},
      body: JSON.stringify(data)
    }}).then(function() {{
      if (typeof gtag === 'function') {{
        gtag('event', 'generate_lead', {{
          lead_type: '{lead_type}',
          course_id: data.course_id || '',
          transport_type: 'beacon'
        }});
      }}
      form.hidden = true;
      document.getElementById('apply-ok').hidden = false;
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}).catch(function() {{
      btn.disabled = false;
      btn.textContent = '重新送出';
      document.getElementById('apply-err').hidden = false;
    }});
  }});
}})();
</script>"""


def gen_apply(data: dict[str, Any]) -> None:
    """預約試上表單頁：單一表單收全部課程，?course=<id> 預選。"""
    options = "".join(
        f'<option value="{p["id"]}">{escape(p["name"])}</option>'
        for p in data["courses"])
    payload = ("""{
      type: 'trial',
      course_id: form.course.value,
      course: form.course.options[form.course.selectedIndex].text,
      name: form.name_field.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      situation: form.situation.value.trim(),
      source: form.source.value
    }""")
    parts = [
        "---",
        'pagetitle: "預約試上｜AI Cooperation"',
        'description: "登記課程試上：小班體驗場陸續安排，場次確定後第一時間通知您。"',
        "page-layout: custom",
        "toc: false",
        "---",
        "",
        "```{=html}",
        '<article class="detail form-page">',
        '<header class="detail-head reveal-fx">',
        '<h1>預約試上</h1>',
        '<p class="detail-tagline">留下你的情境，小班體驗場確定後第一時間通知你</p>',
        "</header>",
        '<div id="apply-ok" class="form-ok" hidden>',
        "<h2>已收到你的登記</h2>",
        "<p>確認信已寄到你的信箱。場次確定後，時間、時數與費用會在通知信中說明，依登記順序通知。</p>",
        '<p><a href="/courses/">← 回課程探索</a></p>',
        "</div>",
        '<form id="apply-form" class="apply-form reveal-fx">',
        '<label>想試上的課程',
        f'<select name="course" required>{options}</select></label>',
        '<label>稱呼 <span class="req">必填</span>',
        '<input type="text" name="name_field" required autocomplete="name" '
        'placeholder="怎麼稱呼你，暱稱就可以"></label>',
        '<label>Email <span class="req">必填</span>',
        '<input type="email" name="email" required autocomplete="email" '
        'placeholder="場次通知會寄到這"></label>',
        '<label>電話',
        '<input type="tel" name="phone" autocomplete="tel" '
        'placeholder="可不填，開課前提醒用"></label>',
        '<label>你的情境：想解決什麼問題',
        '<textarea name="situation" rows="4" placeholder="例如：每天手動整理訂單表、家人獨居想多一層安心……"></textarea></label>',
        '<label>怎麼知道這門課',
        '<select name="source"><option value="">（可不選）</option>'
        '<option>朋友推薦</option><option>搜尋找到</option>'
        '<option>社群看到</option><option>上過其他課</option>'
        '<option>其他</option></select></label>',
        '<button type="submit" class="btn-primary">送出登記</button>',
        '<p id="apply-err" class="form-err" hidden>送出失敗，請再試一次，'
        '或直接寫信到 ai@cooperation.tw。</p>',
        '<p class="detail-cta-note">不方便填表單？直接寫信到 '
        'ai@cooperation.tw，註明想試上的課程即可。</p>',
        "</form>",
        "</article>",
        # ?course=<id> 預選課程
        '<script>(function(){var c=new URLSearchParams(location.search)'
        ".get('course');if(!c)return;"
        "var s=document.querySelector('#apply-form select[name=course]');"
        "if(!s)return;for(var i=0;i<s.options.length;i++){"
        "if(s.options[i].value===c){s.selectedIndex=i;break;}}})();</script>",
        apply_page_js(payload, "course_trial"),
        "```",
        "",
    ]
    APPLY_DIR.mkdir(exist_ok=True)
    (APPLY_DIR / "index.qmd").write_text("\n".join(parts), encoding="utf-8")


def gen_apply_enterprise() -> None:
    """企業內訓諮詢表單頁。"""
    payload = ("""{
      type: 'enterprise',
      company: form.company.value.trim(),
      name: form.name_field.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      workflow: form.workflow.value.trim(),
      headcount: form.headcount.value,
      schedule: form.schedule.value.trim()
    }""")
    parts = [
        "---",
        'pagetitle: "企業內訓諮詢｜AI Cooperation"',
        'description: "企業內訓諮詢：六小時四階段實作，用你們自己的工作流程當教材，一個工作天內回覆。"',
        "page-layout: custom",
        "toc: false",
        "---",
        "",
        "```{=html}",
        '<article class="detail form-page">',
        '<header class="detail-head reveal-fx">',
        '<h1>企業內訓諮詢</h1>',
        '<p class="detail-tagline">留下部門的情況，一個工作天內與你聯絡</p>',
        '<p class="detail-audience">流程：30 分鐘課前訪談 → 課程規劃與報價 → 排期開課</p>',
        "</header>",
        '<div id="apply-ok" class="form-ok" hidden>',
        "<h2>已收到諮詢</h2>",
        "<p>確認信已寄到你的信箱，我會在一個工作天內與你聯絡，"
        "先約一次 30 分鐘的課前流程訪談。</p>",
        '<p><a href="/">← 回首頁</a></p>',
        "</div>",
        '<form id="apply-form" class="apply-form reveal-fx">',
        '<label>公司與部門 <span class="req">必填</span>',
        '<input type="text" name="company" required autocomplete="organization" '
        'placeholder="例如：某某科技 製造部"></label>',
        '<label>稱呼 <span class="req">必填</span>',
        '<input type="text" name="name_field" required autocomplete="name" '
        'placeholder="怎麼稱呼你"></label>',
        '<label>Email <span class="req">必填</span>',
        '<input type="email" name="email" required autocomplete="email" '
        'placeholder="課程規劃與報價會寄到這"></label>',
        '<label>電話',
        '<input type="tel" name="phone" autocomplete="tel" '
        'placeholder="可不填，方便電話訪談再留"></label>',
        '<label>想改善的工作流程 <span class="req">必填</span>',
        '<textarea name="workflow" rows="4" required placeholder="例如：客服信件分類回覆、每月報表彙整、現場巡檢紀錄……"></textarea></label>',
        '<label>預計人數',
        '<select name="headcount"><option value="">未定</option>'
        '<option>10 人以內</option><option>10-20 人</option>'
        '<option>20 人以上</option></select></label>',
        '<label>期望時段',
        '<input type="text" name="schedule" placeholder="例如：12 月平日下午、明年 Q1"></label>',
        '<button type="submit" class="btn-primary">送出諮詢</button>',
        '<p id="apply-err" class="form-err" hidden>送出失敗，請再試一次，'
        '或直接寫信到 ai@cooperation.tw。</p>',
        '<p class="detail-cta-note">不方便填表單？直接寫信到 '
        'ai@cooperation.tw，註明「企業內訓洽詢」即可。</p>',
        "</form>",
        "</article>",
        apply_page_js(payload, "enterprise"),
        "```",
        "",
    ]
    APPLY_DIR.mkdir(exist_ok=True)
    (APPLY_DIR / "enterprise.qmd").write_text(
        "\n".join(parts), encoding="utf-8")


def main() -> None:
    # 完整驗證資料後才清除舊頁，避免輸入錯誤破壞既有輸出。
    data = load_data()
    PROJECTS.update(load_projects())
    OUT_DIR.mkdir(exist_ok=True)
    for old in OUT_DIR.glob("*.qmd"):
        old.unlink()
    gen_listing(data)
    for p in data["courses"]:
        gen_detail(p, data["categories"][p["category"]])
    gen_apply(data)
    gen_apply_enterprise()
    print(f"完成：課程探索總頁 + {len(data['courses'])} 個課程獨立頁"
          " + 預約試上/企業諮詢表單頁")


if __name__ == "__main__":
    main()
