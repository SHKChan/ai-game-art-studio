"""Motion Studio action plans: reference -> actions -> prompts (Codex / template) -> one strip per action.

Codex is replaced by tests/fake_codex.py (a test double for `codex exec` and `codex app-server`);
ComfyUI by mock_comfyui. Neither produces real art; these tests check the pipeline, not image quality."""
import json
import os
import sys
import unittest
from pathlib import Path

from helpers import KNIGHT, ROOT, cleanup, mock_comfy, studio, temp_workspace

from PIL import Image

from artstudio import actions as plans
from artstudio.codex_cli import CodexError, extract_json, resolve
from artstudio.jobs import Budget, BudgetExceeded
from artstudio.providers.base import GenerationError
from artstudio.util import StudioError

FAKE = f"{sys.executable} {ROOT / 'tests' / 'fake_codex.py'}"
REF = KNIGHT / "idle" / "poster.png"


class ActionPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        cls.s.cfg.codex_bin = FAKE
        cls.s.registry.get("codex").codex_bin = FAKE
        cls.pid = cls.s.ws.create_project("A")["id"]

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.tmp)

    def setUp(self):
        os.environ.pop("FAKE_CODEX_MODE", None)

    def char(self, name="Knight", view="side"):
        return self.s.create_character_from_reference(self.pid, name, REF, view=view)

    def plan(self, cid, actions):
        return plans.save_plan(self.s.ws, self.pid, cid, {"actions": actions})

    # ---- plan model
    def test_reference_becomes_locked_master(self):
        c = self.char()
        self.assertEqual(c["direction_mode"], "side2")
        self.assertTrue(c["masters"]["right"]["locked"])
        top = self.char("Top", view="top_down")
        self.assertIn("south", top["masters"])
        c2 = self.s.set_character_reference(self.pid, c["id"], KNIGHT / "run" / "poster.png" if (KNIGHT / "run" / "poster.png").exists() else REF)
        self.assertTrue(any(h["event"] == "master_replaced" for h in c2["history"]))

    def test_plan_clean_and_ids(self):
        cid = self.char()["id"]
        p = self.plan(cid, [{"preset": "attack"}, {"name": "Spin slash", "frames": 5}, {"name": "旋风斩"}, {"name": "旋风斩"}])
        self.assertEqual([a["id"] for a in p["actions"]], ["attack", "spin_slash", "action", "action_2"])
        self.assertEqual(p["actions"][0]["frames"], 8)
        self.assertEqual(len(p["actions"][0]["poses"]), 8)
        self.assertEqual(len(p["actions"][1]["poses"]), 5)
        with self.assertRaises(StudioError):
            self.plan(cid, [{"name": "x", "frames": 40}])
        with self.assertRaises(StudioError):
            self.plan(cid, [{"preset": "moonwalk"}])

    def test_template_prompts_en_zh(self):
        cid = self.char()["id"]
        self.plan(cid, [{"preset": "run"}, {"name": "Spin", "description": "spins once", "frames": 5, "loop": True}])
        p = self.s.write_action_prompts(self.pid, cid, "template")
        self.assertIn("4 columns x 2 rows", p["actions"][0]["prompt"])
        self.assertIn("3 columns x 2 rows", p["actions"][1]["prompt"])
        self.assertIn("Leave the last 1 cell(s) empty", p["actions"][1]["prompt"])
        self.assertIn("spins once", p["actions"][1]["prompt"])
        self.assertIn("last frame flows back", p["actions"][1]["prompt"])
        self.assertNotIn("Style: ;", p["actions"][1]["prompt"])
        p = self.s.write_action_prompts(self.pid, cid, "template", language="zh-CN")
        self.assertIn("固定 4 列 × 2 行", p["actions"][0]["prompt"])
        self.assertEqual(p["actions"][0]["prompt_source"], "template")

    # ---- Codex prompt writing
    def test_codex_writes_prompts_from_reference(self):
        cid = self.char()["id"]
        self.plan(cid, [{"preset": "attack"}, {"name": "Spin", "description": "spins once", "frames": 5}])
        p = self.s.write_action_prompts(self.pid, cid, "codex")
        self.assertEqual(p["identity_source"], "codex")
        self.assertIn("fake codex", p["identity"])
        for a in p["actions"]:
            self.assertEqual(a["prompt_source"], "codex")
            self.assertIn("reference seen: True", a["prompt"])
            self.assertEqual(len(a["poses"]), a["frames"])
        p = self.s.write_action_prompts(self.pid, cid, "codex", language="zh-CN")
        self.assertIn("金发", p["identity"])

    def test_codex_failure_is_reported(self):
        cid = self.char()["id"]
        self.plan(cid, [{"preset": "idle"}])
        os.environ["FAKE_CODEX_MODE"] = "fail"
        with self.assertRaises(StudioError) as cm:
            self.s.write_action_prompts(self.pid, cid, "codex")
        self.assertEqual(cm.exception.code, "codex_failed")

    def test_extract_json_and_resolve(self):
        self.assertEqual(extract_json('x ```json\n{"a": "b}"}\n```')["a"], "b}")
        self.assertEqual(extract_json('pre {"a": {"b": "q\\"}"}} post')["a"]["b"], 'q"}')
        with self.assertRaises(CodexError):
            extract_json("no json here")
        self.assertIsNone(resolve("definitely-not-a-codex-binary-xyz"))
        self.assertEqual(resolve(FAKE)[-1], str(ROOT / "tests" / "fake_codex.py"))

    # ---- generation
    def test_codex_generates_one_strip_per_action(self):
        cid = self.char()["id"]
        self.plan(cid, [{"name": "Spin", "description": "spins once", "frames": 5}])
        self.s.write_action_prompts(self.pid, cid, "template")
        a = self.s.generate_action(self.pid, cid, "spin", "codex")
        self.assertEqual(len(a["animation"]["frames"]), 5)
        self.assertEqual(a["action"]["action_id"], "spin")
        self.assertEqual(a["action"]["layout"], "grid 3x2")
        self.assertEqual(a["action"]["sheet_qa"]["status"], "pass")
        self.assertEqual(len(a["action"]["attempts"]), 1)
        self.assertEqual(a["animation"]["anchor"]["kind"], "ground")
        self.assertFalse(a["provider"]["is_test_fixture"])
        self.assertIn("action:spin", a["tags"])
        p = plans.load_plan(self.s.ws, self.pid, cid)
        self.assertEqual(p["actions"][0]["asset_id"], a["id"])
        self.assertEqual(p["actions"][0]["status"], "generated")
        # selective regeneration of one frame uses the action's frame prompt
        r = self.s.regenerate_frame(self.pid, a["id"], 2, "codex", note="tighter grip")
        self.assertIn("frame 3/5", r["animation"]["frames"][2]["generation"]["prompt"])
        self.assertIn("tighter grip", r["animation"]["frames"][2]["generation"]["prompt"])

    def test_codex_generation_failure_marks_action(self):
        cid = self.char()["id"]
        self.plan(cid, [{"preset": "hit"}])
        os.environ["FAKE_CODEX_MODE"] = "fail"
        with self.assertRaises(GenerationError):
            self.s.generate_action(self.pid, cid, "hit", "codex")
        self.assertEqual(plans.load_plan(self.s.ws, self.pid, cid)["actions"][0]["status"], "failed")

    def test_mock_is_labelled_fixture_and_batch_budget(self):
        cid = self.char()["id"]
        self.plan(cid, [{"preset": "run"}, {"preset": "idle"}])
        a = self.s.generate_action(self.pid, cid, "run", "mock")
        self.assertTrue(a["provider"]["is_test_fixture"])
        self.assertIn("test-fixture", a["tags"])
        with self.assertRaises(BudgetExceeded):  # codex counts toward the budget: 2 actions, budget 1
            self.s._job_batch_actions({"character_id": cid, "action_ids": ["run", "idle"], "provider_id": "codex"},
                                      __import__("artstudio.providers.base", fromlist=["JobContext"]).JobContext(), Budget(1), {"project_id": self.pid})

    def test_bad_sheet_is_regenerated(self):
        cid = self.char()["id"]
        self.plan(cid, [{"preset": "hit"}])
        self.s.write_action_prompts(self.pid, cid, "template")
        os.environ["FAKE_CODEX_MODE"] = "bad_once"
        os.environ["FAKE_CODEX_STATE"] = str(self.tmp / "bad_once.flag")
        try:
            a = self.s.generate_action(self.pid, cid, "hit", "codex")
        finally:
            os.environ.pop("FAKE_CODEX_STATE", None)
        self.assertEqual([x["status"] for x in a["action"]["attempts"]], ["retry", "pass"])
        self.assertEqual(a["action"]["attempts"][0]["issues"][0]["code"], "empty_cell")
        self.assertEqual(len(a["animation"]["frames"]), 4)
        self.assertEqual(a["action"]["grid"], [2, 2])

    def test_retries_are_capped(self):
        cid = self.char()["id"]
        self.plan(cid, [{"preset": "hit"}])
        plan = plans.load_plan(self.s.ws, self.pid, cid)
        plan["settings"] = {"max_retries": 0}
        plans.save_plan(self.s.ws, self.pid, cid, plan)
        os.environ["FAKE_CODEX_MODE"] = "bad_once"
        os.environ["FAKE_CODEX_STATE"] = str(self.tmp / "bad_once_cap.flag")
        try:
            with self.assertRaises(GenerationError):
                self.s.generate_action(self.pid, cid, "hit", "codex")
        finally:
            os.environ.pop("FAKE_CODEX_STATE", None)
        self.assertEqual(plans.load_plan(self.s.ws, self.pid, cid)["actions"][0]["status"], "failed")

    def test_core_presets_and_grid(self):
        from artstudio.processing.sheet import grid_for
        pr = plans.presets()
        self.assertEqual(list(pr)[:3], ["walk", "attack", "hit"])
        self.assertEqual((pr["walk"]["cols"], pr["walk"]["rows"]), (4, 2))
        self.assertEqual((pr["hit"]["cols"], pr["hit"]["rows"]), (2, 2))
        self.assertEqual([grid_for(n) for n in (1, 3, 4, 5, 8, 12)], [(1, 1), (3, 1), (2, 2), (3, 2), (4, 2), (4, 3)])
        self.assertEqual(plans.new_action("hit", lang="zh-CN")["name"], "受击")

    def test_strip_reference(self):
        p = self.s.strip_reference(REF, 4, self.tmp / "sr", "pixel")
        with Image.open(p) as im:
            self.assertEqual(im.size, (2048, 512))
            self.assertEqual(im.mode, "RGB")


class ActionComfyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = mock_comfy()
        cls.tmp = temp_workspace()
        os.environ["COMFYUI_URL"] = cls.url
        cls.s = studio(cls.tmp, job_timeout_s=20)
        cls.pid = cls.s.ws.create_project("CA")["id"]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        os.environ.pop("COMFYUI_URL", None)
        cleanup(cls.tmp)

    def test_comfyui_strip_via_job(self):
        c = self.s.create_character_from_reference(self.pid, "Hero", REF)
        plans.save_plan(self.s.ws, self.pid, c["id"], {"actions": [{"preset": "walk"}]})
        job = self.s.jobs.submit("batch_actions", {"character_id": c["id"], "action_ids": ["walk"], "provider_id": "comfyui",
                                                   "params": {"checkpoint": "mock-sd15-fixture.safetensors", "steps": 4, "cell": 128}},
                                 project_id=self.pid, budget=1)
        j = self.s.jobs.wait(job["id"], 60)
        self.assertEqual(j["status"], "succeeded", j)
        a = self.s.ws.get_asset(self.pid, j["result"]["asset_id"])
        self.assertTrue(a["provider"]["is_test_fixture"])  # mock server output is a labelled fixture
        self.assertEqual(a["animation"]["frames"][0]["generation"]["workflow_id"], self.s.default_strip_workflow())
        ups = self.srv.state.uploads()
        self.assertTrue(ups)
        with Image.open(self.srv.state.dir / "input" / ups[-1]) as im:
            self.assertEqual(im.size, (128 * 4, 128 * 2))  # reference repeated in a 4x2 grid


class ActionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        from artstudio.server.app import make_server
        cls.srv = make_server(cls.s, "127.0.0.1", 0)
        cls.port = cls.srv.server_address[1]
        cls.srv.RequestHandlerClass.allowed_hosts = {f"127.0.0.1:{cls.port}"}
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cleanup(cls.tmp)

    def req(self, method, path, body=None):
        import http.client
        from artstudio.server.app import TOKEN
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        c.request(method, path, json.dumps(body) if body is not None else None,
                  {"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "Cookie": f"artstudio={TOKEN}"})
        r = c.getresponse()
        return r.status, json.loads(r.read() or b"null")

    def test_guided_flow_api(self):
        import base64
        st, p = self.req("POST", "/api/projects", {"name": "W"})
        pid = p["id"]
        data = "data:image/png;base64," + base64.b64encode(REF.read_bytes()).decode()
        st, c = self.req("POST", f"/api/projects/{pid}/characters/from-reference", {"name": "Hero", "filename": "hero.png", "data": data})
        self.assertEqual(st, 200, c)
        cid = c["id"]
        st, pr = self.req("GET", "/api/action-presets")
        self.assertIn("attack", pr)
        st, plan = self.req("POST", f"/api/projects/{pid}/characters/{cid}/plan", {"actions": [{"preset": "idle"}, {"name": "Wave", "frames": 4}]})
        self.assertEqual([a["id"] for a in plan["actions"]], ["idle", "wave"])
        st, r = self.req("POST", f"/api/projects/{pid}/characters/{cid}/plan/prompts", {"method": "template"})
        self.assertTrue(all(a["prompt"] for a in r["plan"]["actions"]))
        st, job = self.req("POST", f"/api/projects/{pid}/characters/{cid}/plan/generate", {"provider_id": "mock"})
        self.assertEqual(job["budget"], 2)
        j = self.s.jobs.wait(job["id"], 60)
        self.assertEqual(j["status"], "succeeded", j)
        self.assertEqual(len(j["result"]["asset_ids"]), 2)
        st, err = self.req("POST", f"/api/projects/{pid}/characters/{cid}/plan/generate", {"provider_id": "nope"})
        self.assertEqual(st, 200)  # queued; the job itself fails with bad_request
        self.assertEqual(self.s.jobs.wait(err["id"], 30)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
