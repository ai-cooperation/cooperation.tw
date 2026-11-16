"""課程產生器的隔離驗收測試，不改動網站輸出。"""
import copy
import importlib.util
import json
import re
from html import escape
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "gen_courses", ROOT / "_scripts/gen_courses.py"
)
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)
SOURCE = yaml.safe_load((ROOT / "data/courses.yml").read_text())
FIELDS = (
    "id name category status wave tagline audience story skills deliverables "
    "abilities future_roles assets limits faq seo_title seo_description image"
).split()


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    source = tmp_path / "courses.yml"
    source.write_text(yaml.safe_dump(SOURCE, allow_unicode=True))
    out = tmp_path / "courses"
    monkeypatch.setattr(gen, "DATA", source)
    monkeypatch.setattr(gen, "OUT_DIR", out)
    return source, out


def save(source, data):
    source.write_text(yaml.safe_dump(data, allow_unicode=True))


def frontmatter(text):
    return yaml.safe_load(text.split("---", 2)[1])


def test_generation_contract_and_repeatability(isolated, capsys):
    _, out = isolated
    out.mkdir()
    (out / "obsolete.qmd").write_text("舊課程")
    (out / "keep.txt").write_text("保留")
    gen.main()
    assert set(path.name for path in out.glob("*.qmd")) == {
        "index.qmd", *(f'{p["id"]}.qmd' for p in SOURCE["courses"])
    }
    assert (out / "keep.txt").read_text() == "保留"
    listing = (out / "index.qmd").read_text()
    assert frontmatter(listing) == {
        "pagetitle": "從你的問題找課程｜情境式 AI 實作課程",
        "description": "不必先懂工具。從生活與家庭、工作與產業、教育與研究的真實情境進來，練四個關鍵能力，做出帶得走的 AI 作品。",
        "page-layout": "custom",
        "toc": False,
    }
    assert "從你在意的問題開始" in listing
    assert "情境式課程練的是四個關鍵能力" in listing
    assert "情境式課程</h2>" in listing
    # 不寫課程數量（入口卡一律「系列課程」）
    assert "門課 →" not in listing
    assert listing.count("系列課程 →") == 3
    assert 'href="/method/#axis-a"' in listing
    assert listing.count('<div class="cgrid">') == 3
    assert (listing.count('class="ccard reveal-fx"')
            == len(SOURCE["courses"]))
    categories = SOURCE["categories"]
    positions = [listing.index(
        f'<h3 class="cgroup-label reveal-fx" id="cat-{c}">')
                 for c in ("life", "work", "learn")]
    assert positions == sorted(positions)
    for cat in categories.values():
        assert cat["hook"] in listing
    for p in SOURCE["courses"]:
        assert f'href="/courses/{p["id"]}.html"' in listing
        assert f'<p class="ccard-pain">{p["tagline"]}</p>' in listing
        take = p.get("take", p["deliverables"][0])
        assert f'<p class="ccard-take">帶走：{take}</p>' in listing
        assert f'<p class="ccard-meta">適合：{p["audience"]}</p>' in listing
        assert (f'<img src="/assets/images/{p["image"]}" '
                f'alt="{p["name"]}" loading="lazy">') in listing
        text = (out / f'{p["id"]}.qmd').read_text()
        assert frontmatter(text) == {
            "pagetitle": p["seo_title"], "description": p["seo_description"],
            "page-layout": "custom", "toc": False,
        }
        assert text.count("```{=html}") == 1
        assert '<article class="detail">' in text
        assert '<header class="detail-head reveal-fx">' in text
        assert (f'badge-cat">{categories[p["category"]]["name"]}</span>'
                in text)
        assert f'<h1>{p["name"]}</h1>' in text
        assert f'<p class="detail-audience">適合：{p["audience"]}</p>' in text
        assert (f'<img class="detail-hero reveal-fx" '
                f'src="/assets/images/{p["image"]}" alt="{p["name"]}">'
                in text)
        titles = [
            "這門課的情境", "你會做出什麼（可帶走的作品）", "會用到的 AI 技巧",
            "你會帶走的能力", "之後可以往哪走", "這門課背後的真實系統",
            "誠實界線", "常見問題",
        ]
        positions = [text.index(f"<h2>{title}</h2>") for title in titles]
        assert positions == sorted(positions)
        for key in ("story", "abilities", "future_roles", "assets", "limits"):
            assert p[key] in text
        for item in p["deliverables"] + p["skills"]:
            assert f"<li>{item}</li>" in text
        assert "進階角色屬於後續路徑" not in text  # 制式免責句已移除（agy 審查 #7）
        if p["status"] == "pilot":
            assert '<span class="badge badge-pilot">預約試上</span>' in text
        else:
            assert "badge-pilot" not in text
        if p.get("projects"):
            for pid in p["projects"]:
                assert f'<a class="proof-card" href="/projects/{pid}.html">' in text
        else:
            assert '<a href="/projects/">看全部運行中的專案 →</a>' in text
        assert '<section class="detail-block detail-limits reveal-fx">' in text
        assert '<div class="faq-list">' in text
        for faq in p["faq"]:
            assert (f'<div class="faq-item"><h3>{faq["q"]}</h3>'
                    f'<p>{faq["a"]}</p></div>') in text
        if p["status"] == "pilot":
            label, subject, css = "預約試上", "試上申請", "btn-primary"
            explanation = ("小班體驗場陸續安排，時間、時數與費用會在"
                           "通知信中說明，登記後依序通知。")
        else:
            label, subject, css = "開課時通知我", "開課通知", "btn-ghost-dark"
            explanation = ("這門課尚未排定場次；想上的人多的課會先開，"
                           "確定開課會第一時間通知您。")
        button = f'<a class="{css}" href="/apply/?course={p["id"]}">{label}</a>'
        assert text.count(button) == 2
        assert ("不方便填表單？直接寫信到 ai@cooperation.tw，標題註明「"
                f'{subject}：{p["name"]}」。') in text
        assert explanation in text
        assert not re.search(r"<a\b[^>]*>[^<]*(報名|購買)", text)
        assert ('<p class="detail-back"><a href="/courses/">'
                '← 回課程探索</a></p>') in text
        payload = json.loads(re.search(
            r'<script type="application/ld\+json">(.*?)</script>', text
        ).group(1))
        assert payload["@context"] == "https://schema.org"
        course, breadcrumbs, faq = payload["@graph"]
        url = f'https://cooperation.tw/courses/{p["id"]}.html'
        expected_course = {
            "@type": "Course", "name": p["name"],
            "description": p["seo_description"], "url": url,
            "provider": {"@type": "Organization", "name": "AI Cooperation",
                         "url": "https://cooperation.tw"},
        }
        if p["status"] == "pilot":
            expected_course["hasCourseInstance"] = {
                "@type": "CourseInstance", "courseMode": "onsite"}
        assert course == expected_course
        assert breadcrumbs["@type"] == "BreadcrumbList"
        assert [(x["name"], x["item"]) for x in
                breadcrumbs["itemListElement"]] == [
            ("首頁", "https://cooperation.tw/"),
            ("課程", "https://cooperation.tw/courses/"), (p["name"], url),
        ]
        assert faq == {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": x["q"], "acceptedAnswer": {
                "@type": "Answer", "text": x["a"]}} for x in p["faq"]
        ]}
        assert not re.search(r'"(?:offers|price|priceCurrency)"', text)
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    gen.main()
    assert before == {p.name: p.read_bytes() for p in out.iterdir()}
    assert str(len(SOURCE["courses"])) in capsys.readouterr().out


@pytest.mark.parametrize("key", ["categories", "courses"])
def test_missing_root_keys_preserve_output(isolated, key):
    source, out = isolated
    data = copy.deepcopy(SOURCE)
    del data[key]
    save(source, data)
    out.mkdir()
    old = out / "keep.qmd"
    old.write_text("原有頁面")
    with pytest.raises(SystemExit, match=key):
        gen.main()
    assert old.read_text() == "原有頁面"


@pytest.mark.parametrize("key", FIELDS)
def test_missing_course_keys(isolated, key):
    source, _ = isolated
    data = copy.deepcopy(SOURCE)
    del data["courses"][0][key]
    save(source, data)
    with pytest.raises(SystemExit, match=key):
        gen.load_data()


@pytest.mark.parametrize("key", ["life", "work", "learn", "name", "hook"])
def test_missing_category_keys(isolated, key):
    source, _ = isolated
    data = copy.deepcopy(SOURCE)
    target = (data["categories"]["life"] if key in ("name", "hook")
              else data["categories"])
    del target[key]
    save(source, data)
    with pytest.raises(SystemExit, match=key):
        gen.load_data()


@pytest.mark.parametrize("key", ["q", "a"])
def test_missing_faq_keys(isolated, key):
    source, _ = isolated
    data = copy.deepcopy(SOURCE)
    del data["courses"][0]["faq"][0][key]
    save(source, data)
    with pytest.raises(SystemExit, match=key):
        gen.load_data()


@pytest.mark.parametrize(("key", "value"), [
    ("status", "live"), ("category", "unknown"), ("id", "../escape"),
    ("id", "index"), ("name", ""), ("name", 4), ("wave", 0), ("wave", True),
    ("skills", []), ("skills", "文字"), ("skills", [None]),
    ("deliverables", []), ("faq", []), ("faq", "文字"), ("faq", [None]),
    ("faq", [{"q": "", "a": "回答"}]),
])
def test_invalid_course_values(isolated, key, value):
    source, _ = isolated
    data = copy.deepcopy(SOURCE)
    data["courses"][0][key] = value
    save(source, data)
    with pytest.raises(SystemExit):
        gen.load_data()


@pytest.mark.parametrize("data", [
    None, [], {"categories": [], "courses": []},
    {**SOURCE, "courses": None}, {**SOURCE, "courses": []},
    {**SOURCE, "courses": [None]},
    {**SOURCE, "categories": {**SOURCE["categories"], "life": None}},
    {**SOURCE, "categories": {**SOURCE["categories"], "life": {
        "name": "", "hook": "情境"}}},
    {**SOURCE, "courses": [SOURCE["courses"][0], SOURCE["courses"][0]]},
])
def test_invalid_structure(isolated, data):
    source, _ = isolated
    save(source, data)
    with pytest.raises(SystemExit):
        gen.load_data()


def test_read_errors(isolated, monkeypatch):
    source, _ = isolated
    source.write_text("courses: [")
    with pytest.raises(SystemExit):
        gen.load_data()
    monkeypatch.setattr(gen, "DATA", source.parent / "missing.yml")
    with pytest.raises(SystemExit):
        gen.load_data()


def test_html_yaml_json_escaping_and_category_order(isolated):
    source, out = isolated
    data = copy.deepcopy(SOURCE)
    data["categories"] = dict(reversed(list(data["categories"].items())))
    p = data["courses"][0]
    for key in ("name", "seo_title", "seo_description", "story"):
        p[key] = '課程 "引號" & <測試> </script>'
    p["faq"][0]["a"] = "內容 </script><script>測試</script>"
    save(source, data)
    gen.main()
    page = (out / f'{p["id"]}.qmd').read_text()
    assert frontmatter(page)["pagetitle"] == p["seo_title"]
    assert f'<h1>{escape(p["name"])}</h1>' in page
    body = page.split("```{=html}", 1)[1]
    assert body.count("</script>") == 1
    payload = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', page
    ).group(1)
    assert "<\\/script>" in payload
    assert json.loads(payload)["@graph"][0]["name"] == p["name"]
    listing = (out / "index.qmd").read_text()
    assert listing.index('id="cat-life"') < listing.index('id="cat-work"')
    assert listing.index('id="cat-work"') < listing.index('id="cat-learn"')
