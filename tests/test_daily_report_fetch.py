"""Tests for memory/daily_report_fetch.py pure functions + run() orchestration.

Migrated from scripts/smoke_daily_report_fetch.py. Network channels
(_fetch_bing_dispatch / fetch_rss) are mocked; gnews is skipped via run()'s
no_google_news flag, so the suite stays offline and side-effect-free.
"""
import base64
import json
import os
import tempfile
import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone
from unittest import mock

import memory.daily_report_fetch as f

_AT = datetime(2026, 6, 20, 18, 0, tzinfo=timezone(timedelta(hours=8)))


def _ck(real_url):
    b = base64.urlsafe_b64encode(real_url.encode()).decode().rstrip("=")
    return "https://www.bing.com/ck/a?" + urllib.parse.urlencode({"u": "a1" + b, "p": "x"})


class TestDailyReportFetch(unittest.TestCase):

    def test_unwrap_bing_url(self):
        self.assertEqual(f.unwrap_bing_url(_ck("https://reuters.com/article/x")),
                         "https://reuters.com/article/x")
        direct = "https://apnews.com/y"
        self.assertEqual(f.unwrap_bing_url(direct), direct)            # 非跳转链原样
        # 坏 base64 回退到原始 bing 链
        self.assertTrue(f.unwrap_bing_url("https://www.bing.com/ck/a?u=a1@@bad")
                        .startswith("https://www.bing.com"))
        self.assertEqual(f.unwrap_bing_url(""), "")

    def test_rel_to_abs(self):
        self.assertEqual(f.rel_to_abs("3 hours ago", _AT), "2026-06-20")
        self.assertEqual(f.rel_to_abs("1 day ago", _AT), "2026-06-19")
        self.assertEqual(f.rel_to_abs("2 days ago", _AT), "2026-06-18")
        self.assertEqual(f.rel_to_abs("1 week ago", _AT), "2026-06-13")
        self.assertEqual(f.rel_to_abs("Jun 19, 2026", _AT), "2026-06-19")
        # Bing 短形式 (aria-label fallback): "7h" "3d" "2w"
        self.assertEqual(f.rel_to_abs("7h", _AT), "2026-06-20")
        self.assertEqual(f.rel_to_abs("3d", _AT), "2026-06-17")
        self.assertEqual(f.rel_to_abs("2w", _AT), "2026-06-06")
        self.assertIsNone(f.rel_to_abs("", _AT))
        self.assertIsNone(f.rel_to_abs("昨天", _AT))                   # 不可解析返回 None

    def test_dedup_records(self):
        recs = [{"url": "https://a.com/1"}, {"url": "https://a.com/1/"},
                {"url": "https://b.com"}, {"url": ""}]
        out = f.dedup_records(recs)
        self.assertEqual(len(out), 2)                                 # 尾斜杠等价合并 + 空 URL 丢弃

    def test_build_bing_url_and_queries(self):
        url = f.build_bing_url(["rare earth", "critical minerals"],
                               ["usgs.gov", "iea.org", "a.org", "b.org", "c.org"])
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["q"][0]
        self.assertIn('"rare earth" OR "critical minerals"', q)       # 多关键词 → OR
        self.assertIn("site:usgs.gov", q)
        self.assertNotIn("site:c.org", q)                             # 仅取前 SITES_PER_QUERY=4
        self.assertIn("setmkt=en-US", url)
        self.assertIn("interval", url)
        # 单关键词 → 直接使用, 无引号
        url2 = f.build_bing_url(["oil gas OPEC"], [])
        q2 = urllib.parse.parse_qs(urllib.parse.urlparse(url2).query)["q"][0]
        self.assertEqual(q2, "oil gas OPEC")
        qs = f.category_queries({"keywords": ["x"], "bing_sites": ["s1.gov"]})
        self.assertEqual(len(qs), 2)                                  # 受限 + 不限域兜底
        qs2 = f.category_queries({"keywords": ["x"], "bing_sites": []})
        self.assertEqual(len(qs2), 1)                                 # 无域仅兜底

    def test_parse_rss(self):
        rss = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
               b'<item><title>A</title><link>https://x.com/a</link>'
               b'<pubDate>Fri, 19 Jun 2026 10:00:00 GMT</pubDate></item>'
               b'<item><title>B</title><link>https://x.com/b</link></item>'
               b'</channel></rss>')
        items = f.parse_rss(rss)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["url"], "https://x.com/a")
        atom = (b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
                b'<entry><title>C</title><link href="https://y.com/c"/>'
                b'<updated>2026-06-18T08:00:00Z</updated></entry></feed>')
        aitems = f.parse_rss(atom)
        self.assertEqual(aitems[0]["url"], "https://y.com/c")
        self.assertEqual(f.parse_rss(b"not xml"), [])                 # 坏 XML 容错

    def test_run_orchestration(self):
        # mock bing 调度边界 + rss, 跳过 gnews; 验证去重 / _meta / 落盘 schema
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(f, "_fetch_bing_dispatch") as m_bing, \
                mock.patch.object(f, "fetch_rss") as m_rss:
            m_bing.return_value = (
                [{"url": "https://a.com/1", "category": "energy", "tier": "news", "channel": "bing"},
                 {"url": "https://a.com/1", "category": "energy", "tier": "news", "channel": "bing"}],
                ["tmwebdriver"],
            )
            m_rss.side_effect = lambda feeds, cat, tier, at, **k: (
                [{"url": "https://b.com", "category": cat, "tier": tier, "channel": "rss"}]
                if feeds else [])
            src = os.path.join(d, "src.json")
            with open(src, "w") as fh:
                json.dump({"daily_news": {"energy": {"keywords": ["oil"], "bing_sites": [],
                                                     "rss": ["http://feed"]}},
                           "analysis": {"think_tanks_rss": []}}, fh)
            out = os.path.join(d, "raw.json")
            payload = f.run(date="2026-06-20", out=out, min_records=1,
                            sources_path=src, no_google_news=True)
            self.assertEqual(payload["_meta"]["total"], 2, payload["_meta"])  # a.com 去重后 + b.com
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as fh:
                disk = json.load(fh)
            self.assertTrue(disk["_meta"]["scraped_at"].startswith("2026-06-20"), disk["_meta"])
            self.assertEqual(disk["_meta"]["by_category"]["energy"], 2, disk["_meta"])

    def test_run_thin_data_exits(self):
        # 数据稀薄 -> sys.exit(3)
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(f, "_fetch_bing_dispatch") as m_bing, \
                mock.patch.object(f, "fetch_rss") as m_rss:
            m_bing.return_value = ([], [])
            m_rss.return_value = []
            src = os.path.join(d, "src.json")
            with open(src, "w") as fh:
                json.dump({"daily_news": {}, "analysis": {"think_tanks_rss": []}}, fh)
            with self.assertRaises(SystemExit) as ctx:
                f.run(date="2026-06-20", out=os.path.join(d, "o.json"),
                      min_records=5, sources_path=src, no_google_news=True)
            self.assertEqual(ctx.exception.code, 3)


if __name__ == "__main__":
    unittest.main()
