"""Browser UI smoke test (Playwright). Starts from a running studio at STUDIO_URL (default
http://127.0.0.1:8870) with an empty workspace, drives every workspace, asserts real results and
saves screenshots to tests/ui_screens/.

  python -m artstudio serve --port 8870   (in another shell, with a fresh ARTSTUDIO_WORKSPACE)
  python tests/ui_playwright.py
"""
import os
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
        page.goto(URL)
        # Library: create project via the inline form
        page.locator("#projectForm input").first.fill("UI Test RPG")
        page.get_by_role("button", name="Create project").click()
        expect(page.locator("#tab-library h3").first).to_have_text("UI Test RPG")
        # Procedural: run chest_open with Atelier
        page.get_by_role("button", name="Procedural Studio").click()
        page.locator("#tab-procedural select").first.select_option("chest_open")
        page.get_by_role("button", name="Run with Atelier").click()
        page.wait_for_selector("#tab-procedural .cels img", timeout=60000)
        shot(page, "01_procedural")
        # Library: import knight sample
        page.get_by_role("button", name="Library").click()
        page.get_by_role("button", name="Import Pixel Atelier knight sample").click()
        page.wait_for_selector("text=Knight light", timeout=60000)
        shot(page, "02_library")
        # Animation studio: open the attack animation, play, onion skin, compare
        page.locator(".asset", has_text="Knight light").first.click()
        page.wait_for_selector("#tab-animation canvas")
        page.get_by_role("button", name="▶ Play").click()
        page.wait_for_timeout(600)
        page.get_by_role("button", name="❚❚ Pause").click()
        page.locator("label", has_text="Onion skin").locator("input").check()
        page.locator(".tframe").nth(4).click()
        page.get_by_role("button", name="Run checks").click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="⇆ Frame comparison").click()
        shot(page, "03_animation")
        # Frame duplicate then delete (edit interfaces)
        n0 = page.locator(".tframe").count()
        page.get_by_role("button", name="Duplicate").click()
        expect(page.locator(".tframe")).to_have_count(n0 + 1, timeout=20000)
        page.get_by_role("button", name="Delete", exact=True).click()
        expect(page.locator(".tframe")).to_have_count(n0, timeout=20000)
        # Hybrid: attach the chest? use procedural effect if present
        # Import & processing: upload a real GIF from Atelier's showcase
        page.get_by_role("button", name="Import & Processing").click()
        gif = ROOT / "upstream" / "atelier" / "showcase" / "gifs" / "opus-5.5-xhigh" / "explosion.gif"
        page.locator("#tab-import input[type=file]").set_input_files(str(gif))
        page.get_by_role("button", name="Import & process", exact=True).click()
        page.wait_for_selector("text=Before / after", timeout=60000)
        shot(page, "04_import")
        # Character studio: create a character
        page.get_by_role("button", name="Character Studio").click()
        page.get_by_role("button", name="Create", exact=True).click()
        page.wait_for_selector("text=Directional masters")
        shot(page, "05_character")
        # Generation: providers + workflows
        page.get_by_role("button", name="Generation", exact=True).click()
        page.wait_for_selector("text=ComfyUI workflow templates")
        shot(page, "06_generation")
        # Export
        page.get_by_role("button", name="Export Studio").click()
        page.get_by_role("button", name="all", exact=True).click()
        page.get_by_role("button", name="Export", exact=True).click()
        page.wait_for_selector("#tab-export img", timeout=120000)
        shot(page, "07_export")
        # Persistence after reload
        page.reload()
        page.wait_for_selector("text=Knight light")
        # Theme toggle
        page.locator("#themeBtn").click()
        shot(page, "08_light_theme")
        b.close()
    if errors:
        print("Console errors:", *errors, sep="\n  ")
        sys.exit(1)
    print("UI smoke test passed; screenshots in", OUT)


if __name__ == "__main__":
    main()
