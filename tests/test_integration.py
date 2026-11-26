"""Integration tests: pixel engine + builders, sample/pipeline helpers, mock ComfyUI, job queue, HTTP server, CLI."""
import http.client
import io
import json
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from helpers import KNIGHT, ROOT, cleanup, mock_comfy, studio, temp_workspace

from PIL import Image

from artstudio import adapters
from artstudio.animation import load_frames
from artstudio.comfy.workflows import derive_template, is_api_format
from artstudio.jobs import Budget, BudgetExceeded
from artstudio.util import StudioError



class PixelForgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        cls.p = cls.s.ws.create_project("A")

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.tmp)

    def test_builders_produce_editable_documents(self):
        expected = {"potion": (1, 64), "chest": (1, 64), "chest_open": (8, 64), "fireball": (8, 64), "sword_slash": (8, 64), "ice_spear": (1, 32), "hero_shrine": (4, 96),
                    "heal": (8, 64), "buff_aura": (8, 64), "lightning_strike": (8, 64), "shield_barrier": (8, 64),
                    "frost_nova": (8, 64), "poison_cloud": (8, 64)}
        for b, (n, size) in expected.items():
            a = self.s.procedural(self.p["id"], b)
            self.assertEqual(len(a["animation"]["frames"]), n, b)
            self.assertEqual(a["animation"]["canvas"], [size, size])
            self.assertEqual(a["qa"]["deterministic"]["status"], "passed", (b, a["qa"]["deterministic"]["issues"]))
            doc = self.s.ws.engine_home(self.p["id"]) / "documents" / a["procedural"]["doc_id"]
            self.assertTrue((doc / "doc.json").is_file() and (doc / "doc.recipe").is_file())
            layers = json.loads((doc / "doc.json").read_text(encoding="utf-8"))["layers"]
            self.assertGreaterEqual(len(layers), 2, "procedural art must be layered")

    def test_recipe_replay_reproduces_pixels(self):
        a = self.s.procedural(self.p["id"], "sword_slash")
        rec = self.s.ws.asset_dir(self.p["id"], a["id"]) / a["procedural"]["recipe"]
        b = self.s.replay_recipe(self.p["id"], rec, "replayed")
        fa = [im.tobytes() for _, im in load_frames(self.s.ws, a)]
        fb = [im.tobytes() for _, im in load_frames(self.s.ws, b)]
        self.assertEqual(fa, fb)

    def test_spritepipe_verifies_procedural_animation(self):
        a = self.s.procedural(self.p["id"], "chest_open")
        pairs = load_frames(self.s.ws, a)
        r = adapters.spritepipe_verify([im for _, im in pairs], [f["duration_ms"] for f, _ in pairs], a["animation"]["pivot"],
                                       self.tmp / "sp-chest", "chest")
        self.assertEqual(r["status"], "TECHNICAL_VERIFIED", r)


class SamplePipelineTests(unittest.TestCase):
    def test_sheet_steps_and_prompt(self):
        steps = adapters.sheet_steps()
        self.assertEqual(list(steps)[:2], ["idle", "run"])
        p = adapters.sheet_prompt_zh("骑士", "light", "金发", "巨剑")
        self.assertIn("骑士", p)

    def test_knight_frames_exact(self):
        frames, durs, meta = adapters.knight_frames("idle")
        self.assertEqual(len(frames), meta["count"])
        self.assertEqual(frames[0].size, tuple(meta["frame_size"]))


class ComfyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = mock_comfy()
        cls.tmp = temp_workspace()
        import os
        os.environ["COMFYUI_URL"] = cls.url
        cls.s = studio(cls.tmp, job_timeout_s=20)
        cls.p = cls.s.ws.create_project("C")
        cls.c = cls.s.ws.create_character(cls.p["id"], "Hero", "four", "pixel", description="red hood adventurer")
        cls.prov = cls.s.registry.get("comfyui")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cleanup(cls.tmp)

    def setUp(self):
        self.srv.state.scenario = "ok"
        self.s.cfg.comfyui.job_timeout_s = 20

    def gen(self, **kw):
        base = dict(provider_id="comfyui", workflow_id="sd-image-to-image", character_id=self.c["id"], template="walk", direction="east",
                    reference=str(KNIGHT / "idle" / "poster.png"), params={"checkpoint": "mock-sd15-fixture.safetensors", "steps": 6})
        base.update(kw)
        job = self.s.jobs.submit("generate", base, project_id=self.p["id"])
        return self.s.jobs.wait(job["id"], 60)

    def test_status_and_mock_detection(self):
        st = self.prov.status()
        self.assertTrue(st.available)
        self.assertTrue(st.details["is_mock"])

    def test_success_is_labelled_fixture(self):
        j = self.gen()
        self.assertEqual(j["status"], "succeeded", j)
        a = self.s.ws.get_asset(self.p["id"], j["result"]["asset_id"])
        self.assertTrue(a["provider"]["is_test_fixture"])
        self.assertIn("test-fixture", a["tags"])
        self.assertGreater(len(a["animation"]["frames"]), 1)
        self.assertTrue(all(f["origin"] == "fixture" for f in a["animation"]["frames"]))

    def test_missing_model(self):
        j = self.gen(params={"checkpoint": "not-installed.safetensors"})
        self.assertEqual((j["status"], j["error_code"]), ("failed", "missing_models"))

    def test_missing_nodes(self):
        j = self.gen(workflow_id="svd-image-to-video", params={"video_checkpoint": "x"})
        self.assertEqual(j["error_code"], "missing_nodes")
        self.assertIn("SVD_img2vid_Conditioning", j["error_details"]["missing_nodes"])

    def test_invalid_workflow_rejected_by_server(self):
        tpl = self.s.registry.workflows.get("sd-text-to-image")
        bad = json.loads(json.dumps(tpl["workflow"]))
        bad["3"]["inputs"]["sampler_name"] = "not_a_sampler"
        t = self.s.registry.workflows.import_workflow(bad, name="bad", category="text_to_image", wid="bad-wf")
        self.assertEqual(t["verification"], "unverified")
        j = self.gen(workflow_id="bad-wf", params={"model_ckpt_name_4": "mock-sd15-fixture.safetensors"})
        self.assertEqual(j["error_code"], "invalid_values")

    def test_execution_failure(self):
        self.srv.state.scenario = "fail"
        j = self.gen()
        self.assertEqual(j["error_code"], "execution_error")

    def test_timeout_and_remote_interrupt(self):
        self.srv.state.scenario = "timeout"
        self.s.cfg.comfyui.job_timeout_s = 1.5
        j = self.gen()
        self.assertEqual(j["error_code"], "timeout")

    def test_websocket_disconnect_falls_back_to_polling(self):
        self.srv.state.scenario = "disconnect"
        j = self.gen(params={"checkpoint": "mock-sd15-fixture.safetensors", "steps": 10})
        self.assertEqual(j["status"], "succeeded", j)

    def test_cancel(self):
        self.srv.state.scenario = "timeout"
        job = self.s.jobs.submit("generate", dict(provider_id="comfyui", workflow_id="sd-text-to-image", character_id=self.c["id"],
                                                  params={"checkpoint": "mock-sd15-fixture.safetensors"}), project_id=self.p["id"])
        import time
        time.sleep(0.8)
        self.s.jobs.cancel(job["id"])
        j = self.s.jobs.wait(job["id"], 30)
        self.assertEqual(j["status"], "cancelled")

    def test_service_disconnected(self):
        from artstudio.config import ComfyConfig
        from artstudio.providers.comfyui import ComfyUIProvider
        p = ComfyUIProvider(ComfyConfig(url="http://127.0.0.1:1", connect_timeout_s=0.5), self.s.registry.workflows)
        st = p.status()
        self.assertFalse(st.available)
        self.assertIn("unreachable", st.reason)

    def test_master_candidate_and_regeneration(self):
        job = self.s.jobs.submit("generate", dict(provider_id="comfyui", kind="master_candidate", workflow_id="sd-text-to-image", character_id=self.c["id"],
                                                  direction="south", params={"checkpoint": "mock-sd15-fixture.safetensors", "steps": 3}), project_id=self.p["id"])
        j = self.s.jobs.wait(job["id"], 60)
        self.assertEqual(j["status"], "succeeded", j)
        c = self.s.ws.get_character(self.p["id"], self.c["id"])
        self.assertTrue(c["candidates"][-1]["is_test_fixture"])
        a = self.s.ws.get_asset(self.p["id"], self.gen()["result"]["asset_id"])
        r = self.s.regenerate_frame(self.p["id"], a["id"], 1, "comfyui", "sd-pose-keyframe",
                                    {"checkpoint": "mock-sd15-fixture.safetensors", "controlnet": "mock-openpose-fixture.safetensors", "steps": 3,
                                     "pose_image": str(KNIGHT / "run" / "poster.png")})
        self.assertEqual(r["animation"]["frames"][1]["origin"], "fixture")

    def test_workflow_import_derivation(self):
        tpl = self.s.registry.workflows.get("sd-pose-keyframe")
        self.assertTrue(is_api_format(tpl["workflow"]))
        self.assertFalse(is_api_format({"nodes": [], "links": []}))
        d = derive_template(tpl["workflow"], wid="x", name="x", category="pose_keyframe")
        self.assertEqual(d["mappings"]["prompt"], [{"node": "6", "input": "text"}])
        self.assertEqual(d["mappings"]["negative_prompt"], [{"node": "7", "input": "text"}])
        self.assertIn("seed", d["mappings"])
        self.assertEqual({m["input"] for m in d["required_models"]}, {"ckpt_name", "control_net_name"})
        with self.assertRaises(StudioError):
            derive_template({"nodes": [], "links": []}, wid="y", name="y", category="text_to_image")


class JobTests(unittest.TestCase):
    def test_budget(self):
        b = Budget(2)
        b.spend(); b.spend()
        with self.assertRaises(BudgetExceeded):
            b.spend()

    def test_batch_requires_budget_and_stops(self):
        tmp = temp_workspace()
        try:
            s = studio(tmp)
            p = s.ws.create_project("B")
            with self.assertRaises(StudioError):
                s.jobs.submit("batch_generate", {"items": []}, project_id=p["id"])
            srv, url = mock_comfy()
            s.registry.get("comfyui").http.base = url
            c = s.ws.create_character(p["id"], "H", "four")
            item = dict(provider_id="comfyui", workflow_id="sd-image-to-image", character_id=c["id"], template="idle",
                        reference=str(KNIGHT / "idle" / "poster.png"), params={"checkpoint": "mock-sd15-fixture.safetensors", "steps": 2})
            job = s.jobs.submit("batch_generate", {"items": [dict(item, direction=d) for d in ("south", "east", "north")]}, project_id=p["id"], budget=2)
            j = s.jobs.wait(job["id"], 120)
            self.assertEqual((j["status"], j["error_code"], j["budget_used"]), ("failed", "budget_exceeded", 2))
            srv.shutdown()
        finally:
            cleanup(tmp)


class ServerAndCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = temp_workspace()
        cls.s = studio(cls.tmp)
        from artstudio.server.app import make_server
        cls.srv = make_server(cls.s, "127.0.0.1", 0)
        cls.port = cls.srv.server_address[1]
        from artstudio.server import app
        cls.srv.RequestHandlerClass.allowed_hosts = {f"127.0.0.1:{cls.port}"}
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cleanup(cls.tmp)

    def req(self, method, path, body=None, cookie=True, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {"Host": host or f"127.0.0.1:{self.port}", "Content-Type": "application/json"}
        if cookie:
            from artstudio.server.app import TOKEN
            h["Cookie"] = f"artstudio={TOKEN}"
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        return r.status, r.read()

    def test_security(self):
        self.assertEqual(self.req("GET", "/api/projects", cookie=False)[0], 401)
        self.assertEqual(self.req("GET", "/api/projects", host="evil.example:80")[0], 403)
        self.assertEqual(self.req("GET", "/files/x/assets/../../studio.json")[0], 404)

    def test_api_project_flow(self):
        st, body = self.req("POST", "/api/projects", {"name": "API"})
        self.assertEqual(st, 200)
        pid = json.loads(body)["id"]
        st, body = self.req("POST", f"/api/projects/{pid}/knight-sample", {"actions": ["idle"]})
        self.assertEqual(st, 200, body)
        aid = json.loads(body)["assets"][0]
        st, body = self.req("GET", f"/api/projects/{pid}/assets/{aid}/contact-sheet.png")
        self.assertEqual(st, 200)
        self.assertEqual(Image.open(io.BytesIO(body)).format, "PNG")
        st, body = self.req("POST", f"/api/projects/{pid}/assets/{aid}/frames", {"op": "duration", "index": 0, "duration_ms": 300})
        self.assertEqual(json.loads(body)["animation"]["frames"][0]["duration_ms"], 300)

    def test_cli(self):
        from artstudio.cli import main
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--workspace", str(self.tmp), "project", "create", "CLI", "--id", "cli-proj"])
        self.assertEqual(json.loads(buf.getvalue())["id"], "cli-proj")
        buf = io.StringIO()
        gif = ROOT / "tests" / "fixtures" / "showcase" / "torch.gif"
        with redirect_stdout(buf):
            main(["--workspace", str(self.tmp), "import", str(gif), "--project", "cli-proj", "--opts", '{"name":"torch"}'])
        out = json.loads(buf.getvalue())
        self.assertGreater(out["animation"]["frames"], 1)


if __name__ == "__main__":
    unittest.main()
