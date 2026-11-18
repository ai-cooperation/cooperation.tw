"""專案產生器的階段卡（tiers）測試；純函式，不寫任何網站輸出。"""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "gen_projects", ROOT / "_scripts/gen_projects.py"
)
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)

TIERS = [
    {"label": "看", "title": "甲", "body": "說明甲", "href": "https://a.example/x", "cta": "去甲 →"},
    {"label": "試", "title": "乙", "body": "說明乙", "href": "https://b.example/", "cta": "去乙 →"},
    {"label": "擁有", "title": "丙", "body": "說明丙", "href": "https://c.example/", "cta": "去丙 →"},
]


def test_tiers_render_one_linked_card_each_in_order():
    html = gen.tiers_section_html({"id": "p", "tiers_title": "三階", "tiers": TIERS})

    assert "<h2>三階</h2>" in html
    assert 'class="proof-grid cols-3"' in html
    assert re.findall(r'<a class="proof-card" href="([^"]+)"', html) == [t["href"] for t in TIERS]
    for t in TIERS:
        assert f'<span class="badge badge-cat">{t["label"]}</span>' in html
        assert f"<h3>{t['title']}</h3><p>{t['body']}</p>" in html
        assert t["cta"] in html


def test_project_without_tiers_renders_nothing():
    assert gen.tiers_section_html({"id": "p"}) == ""


@pytest.mark.parametrize("key", gen.TIER_KEYS)
def test_missing_tier_field_stops_the_build(key):
    broken = [dict(TIERS[0])]
    del broken[0][key]

    with pytest.raises(SystemExit, match=key):
        gen.tiers_section_html({"id": "p", "tiers": broken})


def test_real_agent_kb_tiers_are_complete():
    data = gen.load_data()
    project = next(p for p in data["projects"] if p["id"] == "agent-kb")

    html = gen.tiers_section_html(project)

    assert html.count('class="proof-card"') == 3
    assert "https://agent-kb.cooperation.tw/insights/byoc-portable-personal-context/" in html
