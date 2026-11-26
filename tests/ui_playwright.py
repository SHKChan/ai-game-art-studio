"""Browser UI smoke test (Playwright). Starts from a running studio at STUDIO_URL (default
http://127.0.0.1:8870) with an empty workspace, drives every workspace, asserts real results and
saves screenshots to tests/ui_screens/.

  ARTSTUDIO_CODEX="python tests/fake_codex.py" python -m artstudio serve --port 8870
      (in another shell, with a fresh ARTSTUDIO_WORKSPACE; the Codex test double makes the Codex path testable offline)
  python tests/ui_playwright.py
"""
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = os.environ.get("STUDIO_URL", "http://127.0.0.1:8870/")
OUT = Path(__file__).resolve().parent / "ui_screens"
ROOT = Path(__file__).resolve().parents[1]
OUT.mkdir(exist_ok=True)
errors = []


def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1500, "height": 950})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept("keep the sword in both hands"))
        page.goto(URL)
        # Home: create a project via the inline form, then the three entry points appear
        page.locator("#projectForm input").first.fill("UI Test RPG")
        page.get_by_role("button", name="Create project").click()
        expect(page.locator(".entry h3", has_text="Animate a character")).to_be_visible()
        shot(page, "00_home")
        # Pixel assets: run chest_open with the pixel engine
        page.get_by_role("button", name="Pixel assets").click()
        page.locator("#tab-procedural select").first.select_option("chest_open")
        page.get_by_role("button", name="Run with pixel engine").click()
        page.wait_for_selector("#tab-procedural .cels img", timeout=60000)
        shot(page, "01_procedural")
        # Guided flow: Home -> Animate a character
        page.get_by_role("button", name="Home", exact=True).click()
        page.locator(".entry", has_text="Animate a character").click()
        w = page.locator("#tab-wizard")
        w.get_by_label("Character name").fill("Test Knight")
        w.locator("input[type=file]").set_input_files(str(ROOT / "samples" / "knight" / "idle" / "poster.png"))
        w.get_by_role("button", name="Create & continue →").click()
        expect(w.locator(".step.cur")).to_contain_text("Actions")
        w.locator(".chip", has_text="attack").first.click()
        expect(w.locator(".arow")).to_have_count(1)
        w.get_by_role("button", name="+ Custom action").click()
        expect(w.locator(".arow")).to_have_count(2)
        row = w.locator(".arow").nth(1)
        row.get_by_label("Action name").fill("Spin slash")
        row.locator("input.grow").fill("spins once with the sword held out")
        row.locator("input.grow").press("Tab")
        shot(page, "10_wizard_actions")
        w.get_by_role("button", name="Next →").click()
        expect(w.locator(".step.cur")).to_contain_text("Prompts")
        w.get_by_role("button", name="✨ Write with Codex (reads the reference image)").click()
        expect(w.locator("textarea[aria-label=Prompt]").first).to_have_value(re.compile("FAKE-CODEX"), timeout=60000)
        shot(page, "11_wizard_prompts")
        w.get_by_role("button", name="Next →").click()
        expect(w.locator(".step.cur")).to_contain_text("Generate")
        expect(w.locator(".prov.sel")).to_contain_text("Codex CLI")
        shot(page, "12_wizard_generate")
        w.get_by_role("button", name="▶ Generate").click()
        expect(w.locator(".rcard")).to_have_count(2, timeout=120000)
        shot(page, "13_wizard_review")
        w.locator(".rcard").first.get_by_role("button", name="✓ Approve").click()
        expect(w.locator(".rcard").first.locator(".badge.approved")).to_be_visible(timeout=20000)
        w.locator(".rcard").nth(1).locator(".fstrip figure").nth(1).click()   # redo one frame (dialog accepted)
        page.locator("#toast", has_text="Frame regenerated").wait_for(timeout=60000)
        w.get_by_role("button", name="Export", exact=True).click()
        expect(w.get_by_role("link", name="⬇ Download ZIP")).to_be_visible(timeout=120000)
        shot(page, "14_wizard_export")
        # Library: import knight sample
        page.get_by_role("button", name="Library").click()
        page.get_by_role("button", name="Import knight sample").click()
        page.wait_for_selector("text=Knight light", timeout=60000)
        shot(page, "02_library")
        # Animation editor (advanced): open the attack animation, play, onion skin, compare
        page.locator(".asset", has_text="Knight light").first.click()
        page.wait_for_selector("#tab-animation canvas")
        expect(page.get_by_role("button", name="Animation editor")).to_be_visible()
        page.get_by_role("button", name="▶ Play").click()
        page.wait_for_timeout(600)
        page.get_by_role("button", name="❚❚ Pause").click()
        page.locator("label", has_text="Onion skin").locator("input").check()
        page.locator(".tframe").nth(4).click()
        page.get_by_role("button", name="Run checks").click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="⇆ Frame comparison").click()
        shot(page, "03_animation")
        n0 = page.locator(".tframe").count()
        page.get_by_role("button", name="Duplicate").click()
        expect(page.locator(".tframe")).to_have_count(n0 + 1, timeout=20000)
        page.get_by_role("button", name="Delete", exact=True).click()
        expect(page.locator(".tframe")).to_have_count(n0, timeout=20000)
        # Import: upload a real GIF (showcase fixture)
        page.get_by_role("button", name="Import", exact=True).click()
        gif = ROOT / "tests" / "fixtures" / "showcase" / "explosion.gif"
        page.locator("#tab-import input[type=file]").set_input_files(str(gif))
        page.get_by_role("button", name="Import & process", exact=True).click()
        page.wait_for_selector("text=Before / after", timeout=60000)
        shot(page, "04_import")
        # Character details (advanced)
        page.get_by_role("button", name="Character details").click()
        page.get_by_role("button", name="Create", exact=True).click()
        page.wait_for_selector("text=Directional masters")
        shot(page, "05_character")
        # Generation & workflows (advanced)
        page.get_by_role("button", name="Generation & workflows").click()
        page.wait_for_selector("text=ComfyUI workflow templates")
        shot(page, "06_generation")
        # Export
        page.locator(".tabs").get_by_role("button", name="Export", exact=True).click()
        page.locator("#tab-export").get_by_role("button", name="all", exact=True).click()
        page.locator("#tab-export").get_by_role("button", name="Export", exact=True).click()
        page.wait_for_selector("#tab-export img", timeout=120000)
        shot(page, "07_export")
        # Persistence after reload
        page.reload()
        page.wait_for_selector("text=Continue")
        expect(page.locator("#tab-home .pick", has_text="Test Knight")).to_be_visible()
        # Theme toggle
        page.locator("#themeBtn").click()
        shot(page, "08_light_theme")
        page.locator("#themeBtn").click()
        # Chinese UI: switch language (persists and reloads), every workspace must render translated
        page.select_option("#langSelect", "zh-CN")
        page.wait_for_selector("text=制作角色动画")
        page.get_by_role("button", name="更多工具 ▸").click()
        for i, (tab, marker) in enumerate([("角色动画", "你的角色"), ("像素素材", "像素引擎配方"), ("导入", "导入并处理"),
                                           ("资源库", "素材"), ("导出", "导出记录"), ("动画编辑器", "选择一个动画"),
                                           ("角色详情", "新建角色"), ("生成与工作流", "生成动画关键帧")]):
            page.locator(".tabs").get_by_role("button", name=tab, exact=True).click()
            page.locator(f"text={marker} >> visible=true").first.wait_for(timeout=20000)
            shot(page, f"zh_{i:02d}")
        page.locator(".tabs").get_by_role("button", name="角色动画", exact=True).click()
        page.locator("#tab-wizard .pick", has_text="Test Knight").click()
        page.locator("#tab-wizard .step", has_text="检查与导出").click()
        page.locator("text=点击某一帧即可只重做这一帧。 >> visible=true").first.wait_for(timeout=20000)
        shot(page, "zh_wizard_review")
        page.select_option("#langSelect", "en")
        page.wait_for_selector("text=Animate a character")
        b.close()
    if errors:
        print("Console errors:", *errors, sep="\n  ")
        sys.exit(1)
    print("UI smoke test passed; screenshots in", OUT)


if __name__ == "__main__":
    main()
