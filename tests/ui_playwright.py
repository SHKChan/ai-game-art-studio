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
        expect(page.locator(".entry h3", has_text="Motion Studio")).to_be_visible()
        shot(page, "00_home")
        # Pixel Forge: live editor — pick a skill, change variant / speed / colours / outline / glow, save and export
        page.locator(".tabs").get_by_role("button", name="Pixel Forge", exact=True).click()
        fg = page.locator("#tab-forge")
        fg.locator(".fitem", has_text="Heal").click()
        expect(fg.locator(".fstage h3")).to_have_text("Heal")
        expect(fg.locator(".fstage .small.muted").last).to_contain_text("rendered in", timeout=30000)
        expect(fg.locator(".fthumbs img")).to_have_count(8)
        fg.locator(".chip", has_text="gold").click()
        fg.get_by_label("Speed").fill("2")
        fg.get_by_label("Outline", exact=True).fill("1")
        fg.get_by_label("Glow", exact=True).fill("2")
        fg.get_by_label("Hue").fill("40")
        page.wait_for_timeout(1200)
        expect(fg.locator(".fstage .small.muted").last).to_contain_text("~22 fps", timeout=30000)
        expect(fg.locator(".swatch-in")).to_have_count(6)
        shot(page, "01_forge")
        fg.get_by_role("button", name="Save & export").click()
        expect(fg.get_by_role("link", name="⬇ Download ZIP")).to_be_visible(timeout=120000)
        expect(fg.locator(".fsaved")).to_have_count(1)
        # Pixel documents (advanced): run chest_open and inspect the engine document
        page.get_by_role("button", name="More tools ▸").click()
        page.get_by_role("button", name="Pixel documents").click()
        page.locator("#tab-procedural select").first.select_option("chest_open")
        page.get_by_role("button", name="Run with pixel engine").click()
        page.wait_for_selector("#tab-procedural .cels img", timeout=60000)
        shot(page, "01_procedural")
        # Guided flow: Home -> Animate a character
        page.get_by_role("button", name="Home", exact=True).click()
        page.locator(".entry", has_text="Motion Studio").click()
        w = page.locator("#tab-wizard")
        w.get_by_label("Character name").fill("Test Knight")
        w.locator("input[type=file]").set_input_files(str(ROOT / "samples" / "knight" / "idle" / "poster.png"))
        w.get_by_role("button", name="Create & continue →").click()
        expect(w.locator(".step.cur")).to_contain_text("Actions")
        w.locator(".chip", has_text=re.compile(r"^\+ attack$")).first.click()
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
        w.get_by_role("button", name="▶ Run pipeline").click()
        expect(w.locator(".rcard")).to_have_count(2, timeout=120000)
        shot(page, "13_wizard_review")
        w.locator(".rcard").first.get_by_role("button", name="✓ Approve").click()
        expect(w.locator(".rcard").first.locator(".badge.approved")).to_be_visible(timeout=20000)
        w.locator(".rcard").nth(1).locator(".fstrip figure").nth(1).click()   # redo one frame (dialog accepted)
        page.locator("#toast", has_text="Frame regenerated").wait_for(timeout=60000)
        # Sprite editor: inspect one pixel, recolour it, delete another, save as a patch layer
        w.locator(".rcard").first.get_by_role("button", name="✎ Edit pixels").click()
        ed = page.locator(".sed")
        expect(ed).to_be_visible()
        cv = ed.locator("canvas.sed-canvas")
        box = cv.bounding_box()
        page.wait_for_timeout(300)
        # click the middle of the sprite area: find an opaque pixel via the page
        hexv = ed.locator(".sed-cur input.mono").input_value()
        xy = page.evaluate("""(h) => { const c = document.querySelector('canvas.sed-canvas'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
            const r = parseInt(h.slice(1, 3), 16), g = parseInt(h.slice(3, 5), 16), b = parseInt(h.slice(5, 7), 16);
            for (let y = 0; y < c.height; y += 2) for (let x = 0; x < c.width; x += 2) { const k = (y * c.width + x) * 4;
              if (d[k] === r && d[k + 1] === g && d[k + 2] === b) return [x, y]; }
            return null; }""", hexv)
        if xy:
            cv.click(position={"x": xy[0] + 1, "y": xy[1] + 1})
            expect(ed.locator(".sed-inspect .mono.big")).to_have_text(re.compile("#[0-9A-F]{6}"))
            shot(page, "15_sprite_inspector")
            ed.locator(".sed-inspect .sed-pal.mini button").first.click()      # recolour the pixel
            page.keyboard.press("ArrowRight")
            ed.get_by_role("button", name="✕ Delete pixel").click()
            expect(ed.locator(".sed-top")).to_contain_text("1 frame(s) changed")
            page.keyboard.press("Control+z")
            page.keyboard.press("Control+Shift+z")
            ed.locator(".sed-tool", has_text="Pencil").click()
            cv.click(position={"x": 4, "y": 4})
            ed.get_by_role("button", name="Save").click()
            page.locator("#toast", has_text="Saved").wait_for(timeout=20000)
            expect(ed.locator(".sed-top")).to_contain_text("All saved")
            ed.locator(".sed-frame").nth(2).click()
            ed.get_by_role("button", name="◐ Onion skin").click()
            shot(page, "16_sprite_editor")
        page.keyboard.press("Escape"); page.keyboard.press("Escape"); page.keyboard.press("Escape")
        expect(ed).to_have_count(0)
        expect(w.locator(".rcard").first).to_contain_text("hand-edited")
        w.get_by_role("button", name="Export", exact=True).click()
        expect(w.get_by_role("link", name="⬇ Download ZIP")).to_be_visible(timeout=120000)
        shot(page, "14_wizard_export")
        # Start option 2: describe a character -> 4 generated candidates -> pick one
        w.locator(".stepper .step").first.click()
        w.locator(".pick.new").click()
        w.get_by_role("button", name="Describe it — generate a reference").click()
        w.get_by_label("Character name").fill("Desc Mage")
        w.locator("textarea").first.fill("small mage, blue hat, wooden staff")
        w.locator("input[name=refprov][value=mock]").check()
        w.get_by_role("button", name="Generate 4 candidates →").click()
        expect(w.locator(".cand")).to_have_count(4, timeout=60000)
        shot(page, "17_reference_candidates")
        w.locator(".cand").nth(1).get_by_role("button", name="✓ Use this").click()
        expect(w.locator(".cand.sel")).to_have_count(1, timeout=20000)
        w.get_by_role("button", name="Next →").click()
        expect(w.locator(".step.cur")).to_contain_text("Actions")
        w.get_by_role("button", name="★ Core set: walk · attack · hit").click()
        expect(w.locator(".arow")).to_have_count(3)
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
        page.locator(".tabs").get_by_role("button", name="Asset Import", exact=True).click()
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
        # Theme: System / Dark / Light
        page.select_option("#themeSelect", "light")
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        page.locator(".tabs").get_by_role("button", name="Pixel Forge", exact=True).click()
        expect(page.locator("#tab-forge .fstage .small.muted").last).to_contain_text("rendered in", timeout=30000)
        shot(page, "08_light_theme")
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        page.select_option("#themeSelect", "dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        # Chinese UI: switch language (persists and reloads), every workspace must render translated
        page.select_option("#langSelect", "zh-CN")
        page.wait_for_selector("text=动作工作室")
        page.get_by_role("button", name="更多工具 ▸").click()
        for i, (tab, marker) in enumerate([("动作工作室", "你的角色"), ("像素工坊", "技能与特效"), ("素材导入", "导入并处理"),
                                           ("资源库", "素材"), ("导出", "导出记录"), ("动画编辑器", "选择一个动画"),
                                           ("角色详情", "新建角色"), ("生成与工作流", "生成动画关键帧"), ("像素文档", "像素引擎配方")]):
            page.locator(".tabs").get_by_role("button", name=tab, exact=True).click()
            page.locator(f"text={marker} >> visible=true").first.wait_for(timeout=20000)
            shot(page, f"zh_{i:02d}")
        page.locator(".tabs").get_by_role("button", name="动作工作室", exact=True).click()
        page.locator("#tab-wizard .pick", has_text="Test Knight").click()
        page.locator("#tab-wizard .step", has_text="检查与导出").click()
        page.locator("text=点击某一帧即可只重做这一帧。 >> visible=true").first.wait_for(timeout=20000)
        shot(page, "zh_wizard_review")
        page.select_option("#langSelect", "en")
        page.wait_for_selector("text=Motion Studio")
        b.close()
    if errors:
        print("Console errors:", *errors, sep="\n  ")
        sys.exit(1)
    print("UI smoke test passed; screenshots in", OUT)


if __name__ == "__main__":
    main()
