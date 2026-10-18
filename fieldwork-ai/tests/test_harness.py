"""Plumbing tests for eval/, forensics, try-on and the seller agent. NO network, NO real Gemini: every model call is mocked.
Run: UV_SYSTEM_CERTS=1 uv run python tests/test_harness.py   (or: uv run python -m unittest tests.test_harness)"""

import asyncio
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="fw_harness_"))
os.environ.update(FW_STORE_DIR=str(TMP / "store"), FW_DATA_DIR=str(TMP / "data"), FW_LOG_DIR=str(TMP / "logs"), FW_USE_VERTEX="0")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from fieldwork import config, forensics, gemini, imgedit, stats, tryon  # noqa: E402
from fieldwork.store import store  # noqa: E402

DATA, LOGS = TMP / "data", TMP / "logs"


# ---------- synthetic data ----------
def hf_image(i: int) -> np.ndarray:
    df = pd.read_parquet(ROOT / "data/hf/data/test-00000-of-00001.parquet", columns=["image"])
    img = cv2.imdecode(np.frombuffer(df.iloc[i]["image"]["bytes"], np.uint8), cv2.IMREAD_COLOR)
    s = 640 / max(img.shape[:2])
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def paint_stain(img: np.ndarray, cx: float = 0.45, cy: float = 0.5) -> np.ndarray:
    out = img.copy()
    h, w = out.shape[:2]
    ov = out.copy()
    cv2.circle(ov, (int(w * cx), int(h * cy)), max(8, w // 28), (20, 40, 90), -1)
    return cv2.addWeighted(cv2.GaussianBlur(ov, (0, 0), 1.5), 0.9, out, 0.1, 0)


def write_video(path: Path, base: np.ndarray, stain: bool = False, rot: float = 0.0, seconds: int = 8, fps: int = 10) -> None:
    h, w = base.shape[:2]
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    img = paint_stain(base) if stain else base
    for i in range(seconds * fps):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot + 0.4 * np.sin(i / 7), 1.0 - (0.04 if rot else 0.0))
        M[:, 2] += (2 * np.sin(i / 5), 2 * np.cos(i / 6))
        fr = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        vw.write(np.clip(fr.astype(np.float32) * (0.93 if rot else 1.0), 0, 255).astype(np.uint8))
    vw.release()


def make_garments(root: Path) -> None:
    a, b = hf_image(0), hf_image(1)
    plan = {"garment-01": (a, True, "marker dot on chest"), "garment-02": (a, False, "no change"),
            "garment-03a": (b, False, "No change"), "garment-03b": (a, False, "no change")}
    for name, (img, stain, ch) in plan.items():
        d = root / name
        (d / "unbox").mkdir(parents=True, exist_ok=True)
        write_video(d / "take.mp4", img)
        write_video(d / "unbox" / "take.mp4", img, stain=stain, rot=4.0)
        (d / "notes.txt").write_text("Uniqlo navy jacket M. code K7Q2. Small stain left cuff.", encoding="utf-8")
        (d / "unbox" / "changes.txt").write_text(ch, encoding="utf-8")


# ---------- mocked Gemini ----------
def fake_generate_factory():
    from fieldwork.take import flaws
    from fieldwork.take.pipeline import Translations
    from fieldwork.take.record import Draft, DraftClaim
    from fieldwork.unbox import judge
    from fieldwork.spec import Box, Item, Lane, Severity

    def gen(task, contents, *, schema=None, model=None, **kw):
        usage = SimpleNamespace(prompt_token_count=1000, candidates_token_count=200, thoughts_token_count=50)
        gemini._log(task, model or "gemini-3.8-flash", SimpleNamespace(usage_metadata=usage), 0.01)
        if task == "take_record":
            return Draft(item=Item(type="jacket", brand="Uniqlo", colour="navy"), code_read="K7Q2", listing_text_en="Navy jacket, small stain.",
                         claims=[DraftClaim(lane=Lane.shown, code="stain", region="left_cuff", severity=Severity.minor, note="small stain",
                                            evidence=[Box(frame_id="f1", box_2d=[300, 300, 500, 500])])])
        if task == "translate_listing":
            return Translations(ja="a", ko="a", zh_TW="a", th="a", id="a", vi="a", hi="a")
        if task == "unbox_compare":
            # content-based stand-in for Gemini: a new defect iff crop B has a clearly darker blob that A lacks
            a, b = [cv2.imdecode(np.frombuffer(c.inline_data.data, np.uint8), cv2.IMREAD_GRAYSCALE).astype(np.float32)
                    for c in contents if hasattr(c, "inline_data")]
            b = cv2.resize(b, (a.shape[1], a.shape[0])) * (a.mean() / max(b.mean(), 1.0))
            blob = cv2.erode((cv2.GaussianBlur(a - b, (0, 0), 2) > 35).astype(np.uint8), np.ones((9, 9), np.uint8))
            bad = bool(blob.any())  # thin misalignment edges vanish under erosion; a filled spot survives
            return judge.PairVerdict(comparable=True, new_defect=bad, code="stain", severity="minor" if bad else "none", unsure=False, reason="dark spot")
        if task == "unbox_flaw_check":
            return judge.FlawCheck(comparable=True, still_visible=True, unsure=False, reason="same stain")
        if task == "flaw_inspect_agentic":
            return SimpleNamespace(text='I zoomed in.\n```json\n{"flaws": [{"code": "stain", "region": "left_cuff", "severity": "minor", "box_2d": [1, 2, 3, 4]}]}\n```')
        if task == "flaw_inspect_plain":
            return flaws.FlawList(flaws=[flaws.Flaw(code="pilling", region="front")])
        raise AssertionError(f"unmocked Gemini task {task}")

    return gen


def fake_embed(paths):
    out = []
    for p in paths:
        im = cv2.resize(cv2.imread(str(p)), (8, 8)).astype(np.float32).ravel()
        im -= im.mean()
        out.append(im / (np.linalg.norm(im) + 1e-6))
    return np.array(out)


def fake_dino_map(ref, new):
    return np.zeros(ref.shape[:2], np.float32)


GRADE = {"condition": {"set": [3, 4], "best": 3, "proba": []}, "pilling": {"set": [1], "best": 1, "proba": []}, "stains": 0.1, "holes": 0.1}


def patches():
    return [mock.patch("fieldwork.gemini.generate", side_effect=fake_generate_factory()),
            mock.patch("fieldwork.gemini.upload_video", return_value="uploaded-video"),
            mock.patch("fieldwork.take.grade.grade", return_value=GRADE),
            mock.patch("fieldwork.unbox.pipeline.embed", side_effect=fake_embed),
            mock.patch("fieldwork.unbox.diff._dino_map", side_effect=fake_dino_map),
            mock.patch.object(config, "LOG_DIR", LOGS), mock.patch.object(config, "DATA_DIR", DATA),
            mock.patch.object(store, "root", TMP / "store", create=True)]


def png_response(img: np.ndarray):
    data = cv2.imencode(".png", img)[1].tobytes()
    part = SimpleNamespace(inline_data=SimpleNamespace(data=data))
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))], usage_metadata=None)


class Base(unittest.TestCase):
    def setUp(self):
        LOGS.mkdir(parents=True, exist_ok=True)
        self._ps = patches()
        for p in self._ps:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self._ps])


class TestStats(unittest.TestCase):
    def test_clopper_pearson(self):
        lo, hi = stats.cp_interval(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.3085, places=3)
        lo, hi = stats.cp_interval(5, 10)
        self.assertAlmostEqual(lo, 0.1871, places=3)
        self.assertAlmostEqual(hi, 0.8129, places=3)
        self.assertEqual(stats.cp_interval(0, 0), (0.0, 1.0))


class TestEval(Base):
    def test_parsers(self):
        import run_eval as ev
        self.assertFalse(ev.parse_changes("No change\n")["planted"])
        c = ev.parse_changes("marker dot on chest\nlint on hem")
        self.assertTrue(c["planted"] and c["n_changes"] == 2)
        n = ev.parse_notes("Uniqlo. code K7Q2. Small stain left cuff. No pilling.")
        self.assertEqual((n["code"], n["flaw_codes"]), ("K7Q2", ["stain"]))

    def test_eval_orchestration_and_ablation_with_scripted_inspection(self):
        import run_eval as ev
        g = DATA / "garments"
        make_garments(g)
        # This is an orchestration test. A pixel heuristic pretending to be Gemini
        # misclassifies alignment edges, so it cannot be the oracle for CV accuracy.
        # Real model candidate/judge behaviour is measured separately by component_stress.py.
        from fieldwork.unbox.gate import UnboxResult
        def scripted_inspection(record, video=None, **kwargs):
            if Path(video).parent.name == "unbox":
                assessment = "differs" if Path(video).parent.parent.name == "garment-01" else "consistent"
            else:
                assessment = "cant_tell"  # deliberate look-alike listing take
            return UnboxResult(verdict=assessment, pairs_aligned=1, pairs_total=1)
        with mock.patch("fieldwork.unbox.pipeline.run_unbox", side_effect=scripted_inspection):
            res = ev.main(["--garments", str(g), "--out", str(DATA / "results"), "--arm", "both", "--arm-frames", "2"])
        self.assertTrue((DATA / "results/eval.json").exists())
        md = (DATA / "results/RESULTS.md").read_text(encoding="utf-8")
        self.assertIn("consistent with the listing", md)
        self.assertNotIn("verified", md.lower())
        rows = {r["garment"]: r for r in res["garments"]}
        self.assertFalse([r for r in rows.values() if "error" in r], rows)
        self.assertEqual(rows["garment-03b"]["partner"], "garment-03a")
        m = res["metrics"]
        self.assertEqual(rows["garment-01"]["unbox"]["verdict"], "differs")      # painted stain found
        self.assertEqual(rows["garment-02"]["unbox"]["verdict"], "consistent")   # re-shoot, no change
        self.assertEqual(m["change_detection_recall"]["k"], 1)
        self.assertEqual(m["change_detection_recall"]["n"], 1)   # only garment-01 has a planted change
        self.assertEqual(m["false_consistent_on_lookalikes"]["n"], 1)
        print("verdicts:", {k: r.get("unbox", {}).get("verdict") for k, r in rows.items()}, "lookalike:", rows["garment-03b"].get("lookalike", {}).get("verdict"))
        self.assertIn("take", res["latency_cost"])
        self.assertGreater(res["latency_cost"]["take"]["usd_total"], 0)  # cost read back from logs/cost.jsonl
        arms = res["ablation"]["arms"]
        self.assertEqual(set(arms), {"agentic", "plain"})
        self.assertGreater(arms["agentic"]["found_noted"], 0)       # parsed JSON-at-end from a mocked code-execution reply
        self.assertEqual(arms["plain"]["found_noted"], 0)           # plain mock only says pilling


class TestFlawParsing(unittest.TestCase):
    def test_json_tail(self):
        from fieldwork.take import flaws
        t = 'prose {"not": 1} more\n```json\n{"flaws": [{"code": "STAIN", "box_2d": [-5, 0, 2000, 10]}]}\n```'
        f = flaws.FlawList.model_validate(flaws.parse_json_tail(t)).flaws[0]
        self.assertEqual((f.code, f.box_2d), ("stain", [0, 0, 1000, 10]))
        with self.assertRaises(ValueError):
            flaws.parse_json_tail("no json here")


class TestTestbedAndForger(Base):
    def _fake_edit(self, prompt, images, model=None, task=""):
        src = cv2.imread(str(images[0])) if not isinstance(images[0], np.ndarray) else images[0]
        out = paint_stain(src, 0.5, 0.5)
        out = cv2.add(out, 3)  # the model also nudges the WHOLE image: compositing must discard that outside the box
        return out

    def test_testbed(self):
        import testbed
        f = DATA / "tb_src.jpg"
        f.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(f), hf_image(2))
        labels = testbed.build([f], DATA / "tb", 1, seed=1, edit=self._fake_edit)
        self.assertTrue(labels[0]["outside_identical"] and labels[0]["synthetic"])
        self.assertIn("SYNTHETIC", (DATA / "tb/labels.json").read_text(encoding="utf-8"))
        ev = testbed.evaluate(labels,
                              regions_fn=lambda a, b, top_k=3: [SimpleNamespace(box_2d=labels[0]["box_2d"], score=9.0)],
                              judge_fn=lambda a, b: SimpleNamespace(new_defect=True, severity="minor"))
        self.assertEqual(ev["recall_on_synthetic_plants"]["k"], 1)

    def test_imgedit_parses_response(self):
        with mock.patch("fieldwork.gemini.client") as c:
            c.return_value.models.generate_content.return_value = png_response(hf_image(0))
            img = imgedit.edit_image("x", [hf_image(0)])
        self.assertEqual(img.ndim, 3)

    def test_forensics_runs(self):
        p = DATA / "clean.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), hf_image(0), [cv2.IMWRITE_JPEG_QUALITY, 85])
        r = forensics.check(p)
        self.assertIsInstance(r.flagged, bool)
        self.assertGreaterEqual(r.ela_score, 0)

    def test_forger_ladder(self):
        import forger, run_eval as ev
        g = DATA / "garments"
        if not (g / "garment-01").exists():
            make_garments(g)
        ev.run_garment(g / "garment-01", [])
        with mock.patch("fieldwork.imgedit.edit_image", side_effect=self._fake_edit):
            res = forger.forge(["ev_garment_01"], 1, DATA / "results/forger", seed=0)
        self.assertEqual(set(res["per_rung"]), set(forger.RUNGS))
        self.assertEqual(len(res["trials"]), 4)
        self.assertEqual(res["per_rung"]["raw"]["forger_wins"]["n"], 1)
        forger.write_md(res, DATA / "results/FORGER.md")
        print("forger wins per rung:", {r: v["forger_wins"]["k"] for r, v in res["per_rung"].items()}, "gate verdicts:",
              [t["gate_verdict"] for t in res["trials"]], "forensics flags:", [t["forensics_flag"] for t in res["trials"]])


class TestTryon(Base):
    def setUp(self):
        super().setUp()
        self.g, self.p = DATA / "garment.jpg", DATA / "person.jpg"
        self.g.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(self.g), hf_image(0))
        cv2.imwrite(str(self.p), hf_image(1))

    def _assert_labelled(self, out: Path):
        img = cv2.imread(str(out))
        self.assertLess(img[: img.shape[0] // 20, 2:20].mean(), 60)  # dark banner strip at the top
        self.assertIn("preview", out.name)

    def test_vertex_then_gemini_then_cache(self):
        resp = SimpleNamespace(generated_images=[SimpleNamespace(image=SimpleNamespace(image_bytes=cv2.imencode(".png", hf_image(2))[1].tobytes()))])
        vc = mock.MagicMock()
        vc.models.recontext_image.return_value = resp
        with mock.patch.dict(os.environ, {"FW_USE_VERTEX": "1"}), mock.patch.object(tryon, "_vertex_client", return_value=vc):
            out = tryon.preview(self.g, self.p, DATA / "tryon_out")
        self.assertEqual(vc.models.recontext_image.call_args.kwargs["model"], "virtual-try-on-001")
        self._assert_labelled(out)
        with mock.patch("fieldwork.gemini.client") as c:
            c.return_value.models.generate_content.return_value = png_response(hf_image(2))
            self._assert_labelled(tryon.preview(self.g, self.p, DATA / "tryon_out"))
        cache = DATA / "demo" / "tryon"
        cache.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(cache / "garment_demo.png"), hf_image(3))
        with mock.patch("fieldwork.gemini.client", side_effect=RuntimeError("quota")):
            self._assert_labelled(tryon.preview(self.g, self.p, DATA / "tryon_out"))
        (cache / "garment_demo.png").unlink()
        with mock.patch("fieldwork.gemini.client", side_effect=RuntimeError("quota")), self.assertRaises(RuntimeError):
            tryon.preview(self.g, self.p, DATA / "tryon_out")


class TestSeller(Base):
    def setUp(self):
        super().setUp()
        from fieldwork import market
        market.seed_fixtures()

    def test_price_rule_never_below_floor(self):
        from fieldwork import pricing
        item = "fx_coat_navy_clean"
        storage_listing = {"id":item,"price_source":"seller","asking_price":1500,"negotiation_enabled":True,"currency":"INR"}
        store.put_json("listings",item,storage_listing)
        store.put_json("floors",item,{"floor":1200})
        for offer in (100,1000,1199,1200,1300,1500,9000):
            result=pricing.offer(store,item,offer)
            self.assertGreaterEqual(result["price"],1200)
            self.assertLessEqual(result["price"],1500)

    def test_tools_and_floor_secrecy(self):
        from fieldwork.agents import seller
        item = "fx_coat_navy_clean"
        store.put_json("listings",item,{"id":item,"price_source":"seller","asking_price":1500,"negotiation_enabled":True,"currency":"INR"})
        store.put_json("floors",item,{"floor":1200})
        out=seller.propose_price(item,buyer_offer=1000)
        self.assertEqual(out["price"],1250)
        self.assertNotIn("1200",json.dumps(out))
        self.assertTrue(any(i["id"] == item for i in seller.list_items()))
        with mock.patch("fieldwork.gemini.generate", return_value=SimpleNamespace(answer="No stain shown.", lang="en", state="shown",
                                                                                   claim_ids=[], model_dump=lambda: {"state": "shown"})):
            self.assertIn("state", seller.answer_question(item, "stain?"))

    def test_chat_wiring(self):
        from fieldwork.agents import seller
        r = seller._runner("gemini-3.8-flash")  # builds the real ADK LlmAgent + FunctionTools (no network)
        self.assertEqual([t.name for t in r.agent.tools], ["list_items", "answer_question", "propose_price"])

        async def fake_run(model, sid, msg):
            if model == "bad":
                raise RuntimeError("overloaded")
            return {"text": "ok", "tool_calls": []}

        with mock.patch.object(seller, "_run", side_effect=fake_run), mock.patch.object(seller.config, "MODEL_FALLBACKS", ["good"]), \
                mock.patch.dict(os.environ, {"FW_SELLER_MODEL": "bad"}):
            out = asyncio.run(seller.chat("s1", "hi"))
        self.assertEqual((out["text"], out["model"]), ("ok", "good"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
