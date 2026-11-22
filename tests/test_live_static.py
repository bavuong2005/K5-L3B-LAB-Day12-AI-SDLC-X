"""chonoi.live phục vụ file tĩnh trong chonoi/web/ (pixi.min.js) và chặn đọc ra ngoài thư mục web."""
import unittest
import urllib.error
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer


def _status(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read(64)
    except urllib.error.HTTPError as e:
        return e.code, "", b""


class LiveStaticTest(unittest.TestCase):
    def test_pixi_served_and_traversal_blocked(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, ctype, head = _status(base + "/pixi.min.js")
            self.assertEqual(code, 200)
            self.assertIn("javascript", ctype)
            self.assertGreater(len(head), 0)
            self.assertEqual(_status(base + "/khong-co.js")[0], 404)
            self.assertEqual(_status(base + "/../live.py")[0], 404)
            self.assertEqual(_status(base + "/%2e%2e/live.py")[0], 404)
        finally:
            server.stop()

    def test_art_subfolder_served_and_fallback_wired(self):
        import os
        from chonoi.live import WEB_DIR
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            for name in ("characters.js", "environment.js"):
                if os.path.isfile(os.path.join(WEB_DIR, "art", name)):
                    code, ctype, head = _status(base + "/art/" + name)
                    self.assertEqual(code, 200)
                    self.assertIn("javascript", ctype)
            self.assertEqual(_status(base + "/art/../../live.py")[0], 404)
            self.assertEqual(_status(base + "/art/%2e%2e/%2e%2e/live.py")[0], 404)
            self.assertEqual(_status(base + "/art/khong-co.js")[0], 404)
        finally:
            server.stop()
        html = open(os.path.join(WEB_DIR, "index.html"), encoding="utf-8").read()
        self.assertIn('src="art/characters.js"', html)
        self.assertIn('src="art/environment.js"', html)
        # dự phòng: không có module art thì ART.ok=false và vẽ canvas 2D cũ
        self.assertIn("artMods()", html)
        self.assertIn("drawAnimatedFish(", html)


class LiveTutorialStoryAudioWiringTest(unittest.TestCase):
    """Phase 4: hướng dẫn / cốt truyện / nhạc nối vào index.html và rơi về êm khi thiếu module."""

    @classmethod
    def setUpClass(cls):
        import os
        from chonoi.live import WEB_DIR
        cls.web = WEB_DIR
        cls.html = open(os.path.join(WEB_DIR, "index.html"), encoding="utf-8").read()

    def test_script_tags_optional(self):
        self.assertIn('<script src="story.js" onerror="void 0"></script>', self.html)
        self.assertIn('<script src="audio.js" onerror="void 0"></script>', self.html)

    def test_story_and_audio_served_when_present(self):
        import os
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            for name in ("story.js", "audio.js"):
                if os.path.isfile(os.path.join(self.web, name)):
                    code, ctype, _ = _status(base + "/" + name)
                    self.assertEqual(code, 200)
                    self.assertIn("javascript", ctype)
        finally:
            server.stop()

    def test_fallbacks_for_missing_modules(self):
        for needle in ("window.ChoNoiStory", "window.ChoNoiAudio", "function audCall(", "catch (e)",
                       "if (!st || !Array.isArray(lines)"):
            self.assertIn(needle, self.html)

    def test_tutorial_hooks(self):
        for needle in ("TUT_STEPS", "dive: [", "quan: [", "chonoi_tut_", 'id === "tutorial"', 'id === "help"',
                       'k === "?"', "tutNext", "tutSkip", "function quanHint(", "function wantHold(",
                       "Hướng dẫn", "Cốt truyện", "volDown", "volUp", 'setMuted'):
            self.assertIn(needle, self.html)

    def test_hold_while_modal(self):
        self.assertIn("storyActive() || tutHolding()", self.html)

    def test_story_stages_and_audio_scenes(self):
        for needle in ('storyDay("pre")', 'storyDay("post")', "pickEnding", "st.intro",
                       '"dive"', '"quan"', '"shop"', '"result"', '"story"', "setDepth", "setIntensity"):
            self.assertIn(needle, self.html)

    def test_character_renamed(self):
        self.assertNotIn("Út Sen", self.html)
        self.assertNotIn("Má Tư", self.html)  # cả game gọi là Bà Tư

    def test_demo_buttons_only_with_demo_param(self):
        """Menu thật không hiện nút Demo; chỉ khi mở với ?demo."""
        self.assertIn('const DEMO_MENU = params.has("demo");', self.html)
        i = self.html.index("if (DEMO_MENU) {")
        j = self.html.index('btn("demoDay"')
        self.assertLess(i, j)
        before = self.html[:j]
        self.assertNotIn('btn("demoDay"', before)
        self.assertNotIn("Khởi động nhanh các Demo", self.html[:i])

    def test_no_favicon_404_and_audio_resume_guarded(self):
        self.assertIn('rel="icon"', self.html)
        self.assertIn("rp.catch", self.html)
        audio = open(self.web + "/audio.js", encoding="utf-8").read()
        self.assertIn("rp.catch", audio)

    def test_first_run_story_and_tutorial_only_in_day_mode(self):
        """Bench (mode gather, startFromMenu) không được kẹt vì hội thoại/thẻ hướng dẫn."""
        self.assertIn("if (isDayMode() && !NO_GUIDE && !STORY.skipIntro", self.html)
        self.assertIn('params.get("guide") === "0"', self.html)
        self.assertIn("if (DEMO || NO_GUIDE || !isDayMode() ||", self.html)


if __name__ == "__main__":
    unittest.main()
