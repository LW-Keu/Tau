"""arXiv 免费数据源接入 (Atom API, cs.AI/cs.CL/cs.LG).

用法:
    python memory/utils/arxiv_fetch.py --date 2026-07-07 --out temp/arxiv_raw_20260707.json

数据源:
    - http://export.arxiv.org/api/query  (Atom API, 无需鉴权)
    - 实际 RSS (http://export.arxiv.org/rss/cs.AI) 周末/节假日常为空,故采用 Atom API 作为稳定来源

输出 schema 与 daily_report_fetch.py 的 _norm() 对齐.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

BJT = timezone(timedelta(hours=8))
USER_AGENT = "Mozilla/5.0 (compatible; tau-daily-report/1.0)"
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]


def _now_bjt():
    return datetime.now(BJT)


def _arxiv_id(entry_id: str) -> str:
    """从 http://arxiv.org/abs/2607.02514v1 提取 2607.02514"""
    tail = entry_id.rsplit("/", 1)[-1]
    return re.sub(r"v\d+$", "", tail)


def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _truncate_summary(text: str, limit: int = 360) -> str:
    t = _clean_text(text)
    if len(t) <= limit:
        return t
    return t[: limit - 1] + "…"


def fetch_arxiv(scraped_at: datetime = None, window_days: int = 7,
                per_cat: int = 10, categories: list = None) -> list:
    """返回 daily_report_fetch.py _norm 风格的记录列表."""
    scraped_at = scraped_at or _now_bjt()
    if scraped_at.tzinfo is None:
        scraped_at = scraped_at.replace(tzinfo=BJT)
    cutoff = scraped_at - timedelta(days=window_days)
    categories = categories or CATEGORIES

    # 单请求拉取全部分类,避免多次访问 arXiv 服务器
    cat_query = "+OR+".join(f"cat:{c}" for c in categories)
    max_results = max(per_cat * len(categories), 20)
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query={cat_query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml_bytes = resp.read()

    root = ET.fromstring(xml_bytes)
    ns = {"a": ATOM_NS, "arxiv": ARXIV_NS}

    records = []
    seen_ids = set()
    for entry in root.findall("a:entry", ns):
        title = _clean_text(entry.find("a:title", ns).text)
        entry_id = entry.find("a:id", ns).text.strip()
        updated = entry.find("a:updated", ns).text.strip()
        summary = entry.find("a:summary", ns).text or ""

        primary = entry.find("arxiv:primary_category", ns)
        cat = primary.get("term") if primary is not None else "cs.AI"

        abs_url = entry_id
        pdf_url = None
        for link in entry.findall("a:link", ns):
            rel = link.get("rel") or "alternate"
            if rel == "alternate":
                abs_url = link.get("href") or abs_url
            elif link.get("title") == "pdf":
                pdf_url = link.get("href")

        try:
            pub_dt = datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(BJT)
        except Exception:
            continue
        if pub_dt < cutoff:
            continue

        arxiv_id = _arxiv_id(entry_id)
        if arxiv_id in seen_ids:
            continue
        seen_ids.add(arxiv_id)

        records.append({
            "title": title,
            "url": abs_url,
            "source": f"arXiv-{cat}",
            "pub_date_abs": pub_dt.isoformat(),
            "pub_date": pub_dt.date().isoformat(),
            "rel_time": updated,
            "snippet": _truncate_summary(summary),
            "category": "前沿技术",
            "tier": "research",
            "channel": "urllib",
            "arxiv_id": arxiv_id,
            "arxiv_pdf_url": pdf_url,
        })

    return sorted(records, key=lambda x: x["pub_date"], reverse=True)


def run(date: str = None, out: str = None, window_days: int = 7,
        per_cat: int = 10, categories: list = None):
    scraped_at = _now_bjt()
    if date:
        scraped_at = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=BJT, hour=18)
    out = out or os.path.join("temp", f"arxiv_raw_{scraped_at:%Y%m%d}.json")

    records = fetch_arxiv(scraped_at, window_days=window_days,
                          per_cat=per_cat, categories=categories)

    by_cat = {}
    for r in records:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1

    payload = {
        "_meta": {
            "scraped_at": scraped_at.isoformat(),
            "channels": ["urllib"],
            "total": len(records),
            "by_category": by_cat,
            "window_days": window_days,
            "categories": categories or CATEGORIES,
        },
        "records": records,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out)) if os.path.dirname(out) else ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[arxiv] {len(records)} records -> {out}", file=sys.stderr)
    return payload


def main():
    ap = argparse.ArgumentParser(description="arXiv cs.AI/CL/LG 数据源采集")
    ap.add_argument("--date", help="报告日期 YYYY-MM-DD (默认: 北京时间今天)")
    ap.add_argument("--out", help="输出 JSON 路径")
    ap.add_argument("--window-days", type=int, default=7, help="回溯天数")
    ap.add_argument("--per-cat", type=int, default=10, help="每分类最大命中")
    ap.add_argument("--categories", help="逗号分隔的分类,默认 cs.AI,cs.CL,cs.LG")
    args = ap.parse_args()
    cats = args.categories.split(",") if args.categories else None
    run(date=args.date, out=args.out, window_days=args.window_days,
        per_cat=args.per_cat, categories=cats)


if __name__ == "__main__":
    main()
