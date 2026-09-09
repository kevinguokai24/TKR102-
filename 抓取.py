# -*- coding: utf-8 -*-
"""
楊桃美食網 (ytower.com.tw) 食譜爬蟲

輸出欄位（CSV 與 JSON 完全對應）：
  seq, title, url, image_url, ingredients_text, steps_text, tags, publish_date

已由實際頁面核對確認：
  - 5 大分類參數：主菜種類=MAINFOOD 國家別=COUNTRY 菜式類別=KIND
                  葷素別=VEGETARIA 烘焙專區=RETYPE
  - COUNTRY 查詢值需補「料理」（中式 -> 中式料理），其餘 4 種維度用選項原文。
  - 食譜內頁網址格式："iframe-recipe.asp?seq=A03-1295"
  - 分頁靠跟隨頁面上「next page?」連結（實際指向 pager.asp）。
  - 材料 <li> 用 <a href=".../material-search.asp?...">材料名</a> 份量 包住，
    分組標題（如「材料」「調味料」）是不含連結的純文字 <li>，照原文抄錄。
  - tags 欄位來自頁面下方「所屬分類」那一列，固定是
    KIND . MAINFOOD . COUNTRY . VEGETARIA . book 這 5 個連結依序用 "." 相連，
    重組成 "主菜 / 豬肉 / 中式料理 / 葷食 / xxx" 這種格式。
  - publish_date 來自頁面上的「上稿日期:M/D/YYYY」文字。

用法：
  pip install -r requirements.txt
  python ytower_scraper.py --calibrate
  python ytower_scraper.py --dimensions 國家別 --max-pages 1 --limit-recipes 5
  python ytower_scraper.py --resume
"""
from __future__ import annotations
import argparse, json, logging, random, re, time, urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

BASE_URL = "https://www.ytower.com.tw"
SEARCH_PATH = "/recipe/recipe-search.asp"
TIMEOUT, MAX_RETRIES, DELAY_RANGE, MAX_PAGES = 15, 3, (1.0, 3.0), 300

DIMENSIONS = {
    "主菜種類": ("MAINFOOD", "", [
        "蛋", "牛肉", "豬肉", "雞肉", "羊肉", "鴨肉", "鵝肉", "魚肉", "貝類",
        "魷魚/花枝", "蝦/蟹", "豆腐", "蒟蒻", "根莖類", "葉菜類", "瓜果類",
        "水果類", "海菜/菇蕈", "種子/核果", "中式點心", "西式點心",
        "米飯/米食", "豆干/腐皮", "麵食/麵粉",
    ]),
    "國家別": ("COUNTRY", "料理", ["中式", "韓式", "西式", "南洋", "日式", "其他"]),
    "菜式類別": ("KIND", "", ["主菜", "前菜", "湯", "冰品", "點心", "飯食", "粥品", "麵食", "飲料"]),
    "葷素別": ("VEGETARIA", "", ["葷食", "素食"]),
    "烘焙專區": ("RETYPE", "", ["蛋糕", "西點", "麵包", "餅乾"]),
}

RECIPE_LINK_RE = re.compile(r"iframe-recipe(?:-p)?\.asp\?seq=([A-Za-z]\d{2}-\d+)", re.I)
NEXT_PAGE_WORDS = ["next page", "下一頁", "下頁", ">>"]
TIPS_WORDS = ["小叮嚀", "貼心小叮嚀", "秘訣", "小秘訣", "tips"]
TIPS_HEADING_RE = re.compile("|".join(TIPS_WORDS), re.I)
PUBLISH_DATE_RE = re.compile(r"上稿日期[:：]?\s*([\d/]+)")

# 頁面最下方「所屬分類」那一列固定順序：KIND . MAINFOOD . COUNTRY . VEGETARIA . book
TAG_CHAIN_RE = re.compile(
    r'<a[^>]+href="[^"]*?\bKIND=[^"]*?"[^>]*>([^<]*)</a>\s*\.\s*'
    r'<a[^>]+href="[^"]*?\bMAINFOOD=[^"]*?"[^>]*>([^<]*)</a>\s*\.\s*'
    r'<a[^>]+href="[^"]*?\bCOUNTRY=[^"]*?"[^>]*>([^<]*)</a>\s*\.\s*'
    r'<a[^>]+href="[^"]*?\bVEGETARIA=[^"]*?"[^>]*>([^<]*)</a>\s*\.\s*'
    r'<a[^>]+href="[^"]*?\bbook=[^"]*?"[^>]*>([^<]*)</a>',
    re.S,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("ytower")


@dataclass
class Recipe:
    seq: str
    title: str = ""
    url: str = ""
    image_url: str = ""
    ingredients_text: str = ""
    steps_text: str = ""
    tags: str = ""
    publish_date: str = ""


def big5_q(text: str) -> str:
    """中文轉 Big5 URL 編碼（該站的搜尋參數採 Big5）。"""
    try:
        raw = text.encode("big5")
    except UnicodeEncodeError:
        raw = text.encode("cp950", errors="ignore")
    return urllib.parse.quote(raw)


def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Referer": BASE_URL + "/recipe/",
    })
    retry = Retry(total=MAX_RETRIES, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def get(session: requests.Session, url: str) -> tuple[Optional[BeautifulSoup], str]:
    """回傳 (soup, 原始html文字)；html 用來做 tags 的原文規則比對。"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "cp950"
            time.sleep(random.uniform(*DELAY_RANGE))
            return BeautifulSoup(r.text, "html.parser"), r.text
        except requests.RequestException as e:
            log.warning(f"重試 {attempt}/{MAX_RETRIES}：{url} -> {e}")
            time.sleep(2.0 * attempt)
    log.error(f"放棄請求：{url}")
    return None, ""


def extract_recipe_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        m = RECIPE_LINK_RE.search(a["href"])
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append((m.group(1), urllib.parse.urljoin(BASE_URL, a["href"])))
    return out


def next_page_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    for a in soup.find_all("a", href=True):
        if any(w in a.get_text(strip=True).lower() for w in NEXT_PAGE_WORDS):
            return urllib.parse.urljoin(current_url, a["href"])
    return None


def crawl_category(session, dim: str, opt: str, param: str, suffix: str, max_pages=None) -> list[tuple[str, str]]:
    url = f"{BASE_URL}{SEARCH_PATH}?{param}={big5_q(opt + suffix)}"
    links, page = [], 1
    while page <= (max_pages or MAX_PAGES):
        log.info(f"[列表] {dim}={opt} 第 {page} 頁 -> {url}")
        soup, _ = get(session, url)
        if soup is None:
            break
        found = extract_recipe_links(soup)
        if not found:
            log.info(f"{dim}={opt} 第 {page} 頁沒有食譜連結，結束此分類。")
            break
        links.extend(found)
        nxt = next_page_url(soup, url)
        if not nxt or nxt == url:
            break
        url, page = nxt, page + 1
    log.info(f"[完成] {dim}={opt} 共 {len(links)} 筆")
    return links


# ---------------- 內頁解析 ----------------

def _normalize_heading(s: str) -> str:
    """去除常見裝飾符號（【】、全形/半形空白、項目符號），
    這樣不管原始標題是「材料」還是「【材　料】」都能比對到。"""
    return re.sub(r"[【】\s\u3000\-•・]", "", s)


def _find_heading(soup: BeautifulSoup, keywords: list[str]):
    """尋找一個「去除裝飾符號後」完全等於 keywords 其中之一的文字節點。"""
    targets = set(keywords)
    return soup.find(string=lambda s: bool(s) and _normalize_heading(s) in targets)


def parse_ingredients_text(soup: BeautifulSoup) -> str:
    """從「材料」標題往後走訪 <li>，直到「作法」標題為止。
    有 material-search.asp 連結的是材料項(name:amount)，
    沒有連結的短項目是分組標題（如材料/調味料），原文照抄，
    最後用「、」串成一整段。"""
    heading = _find_heading(soup, ["材料", "食材"])
    if heading is None:
        return ""
    parts = [heading.strip()]
    for li in heading.find_all_next("li"):
        text = li.get_text(strip=True)
        if _normalize_heading(text) in ("作法", "做法", "步驟"):
            break
        link = li.find("a", href=re.compile(r"material-search\.asp"))
        if link:
            name = link.get_text(strip=True)
            amount = li.get_text(" ", strip=True).replace(name, "", 1).strip(" :：")
            parts.append(f"{name}:{amount}" if amount else name)
        elif text:
            parts.append(text)
    return "、".join(parts)


def parse_steps_text(soup: BeautifulSoup) -> str:
    heading = _find_heading(soup, ["作法", "做法", "步驟"])
    if heading is None:
        return ""
    lines = []
    for tag in heading.find_all_next(["li", "p"]):
        text = tag.get_text(strip=True)
        if not text:
            continue
        if TIPS_HEADING_RE.search(text) and not re.match(r"^\d+[\.\、]", text):
            break
        if re.match(r"^\d+[\.\、]", text):
            lines.append(text)
        elif lines:
            break  # 已離開作法區塊
    return "\n".join(f"{i}. {t}" for i, t in enumerate(lines, 1))


def parse_tags(html: str) -> str:
    m = TAG_CHAIN_RE.search(html)
    return " / ".join(g.strip() for g in m.groups()) if m else ""


def parse_detail(soup: BeautifulSoup, html: str, seq: str, url: str) -> Recipe:
    rec = Recipe(seq=seq, url=url)
    rec.title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    og_img = soup.find("meta", attrs={"property": "og:image"})
    rec.image_url = og_img["content"].strip() if og_img and og_img.get("content") else ""
    rec.ingredients_text = parse_ingredients_text(soup)
    rec.steps_text = parse_steps_text(soup)
    rec.tags = parse_tags(html)
    m = PUBLISH_DATE_RE.search(soup.get_text())
    rec.publish_date = m.group(1) if m else ""
    return rec


# ---------------- 輸出（JSON + CSV 一律同時寫出） ----------------

def save_all(records: dict[str, Recipe], outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = outdir / "ytower_recipes.json", outdir / "ytower_recipes.csv"
    rows = [asdict(r) for r in records.values()]
    with open(json_path, "w", encoding="utf-8-sig") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    log.info(f"已寫入 {json_path.name} 與 {csv_path.name}（共 {len(records)} 筆）")


def load_existing(json_path: Path) -> dict[str, Recipe]:
    if not json_path.exists():
        return {}
    data = json.loads(json_path.read_text(encoding="utf-8-sig"))
    return {d["seq"]: Recipe(**d) for d in data}


def calibrate(session):
    debug = Path("debug"); debug.mkdir(exist_ok=True)
    for dim, (param, suffix, opts) in DIMENSIONS.items():
        opt = opts[0]
        url = f"{BASE_URL}{SEARCH_PATH}?{param}={big5_q(opt + suffix)}"
        soup, html = get(session, url)
        (debug / f"sample_{dim}.html").write_text(html, encoding="utf-8")
        links = extract_recipe_links(soup) if soup else []
        log.info(f"{dim}={opt}（查詢值：{opt + suffix}）-> 抓到 {len(links)} 筆連結"
                  + ("" if links else "　⚠️ 0 筆，請開 debug/ 內對應檔案檢查原因"))


def load_progress(path: Path) -> set:
    if not path.exists():
        return set()
    return {tuple(x) for x in json.loads(path.read_text(encoding="utf-8"))}


def save_progress(done: set, path: Path):
    path.write_text(json.dumps(sorted(done), ensure_ascii=False), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--dimensions", nargs="*", default=None)
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--limit-recipes", type=int, default=None, help="本次最多新抓幾篇內頁（測試用）")
    ap.add_argument("--target", type=int, default=None, help="累計抓到這個總筆數就停止（含之前已存的）")
    ap.add_argument("--fresh", action="store_true", help="不續跑，清空重新開始（預設一律自動續跑）")
    ap.add_argument("--output-dir", default="output")
    args = ap.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 額外把 log 同時寫進檔案，重開程式也能查到之前跑到哪裡
    file_handler = logging.FileHandler(outdir / "scraper.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(file_handler)

    session = build_session()
    log.info("建立瀏覽階段...")
    get(session, BASE_URL + "/")

    if args.calibrate:
        calibrate(session)
        return

    json_path = outdir / "ytower_recipes.json"
    progress_path = outdir / "progress.json"

    # 預設一律自動續跑：讀取既有結果 + 已完成的分類清單，不會每次重頭爬。
    # 只有明確加 --fresh 才會清空重來。
    records = {} if args.fresh else load_existing(json_path)
    done_categories = set() if args.fresh else load_progress(progress_path)
    log.info(f"已載入既有紀錄 {len(records)} 筆；已完成分類 {len(done_categories)} 組"
              + ("（--fresh，將清空重新開始）" if args.fresh else ""))

    new_count = 0

    def target_reached() -> bool:
        return args.target is not None and len(records) >= args.target

    def target_remaining() -> Optional[int]:
        return None if args.target is None else max(0, args.target - len(records))

    try:
        for dim in (args.dimensions or DIMENSIONS.keys()):
            if target_reached():
                break
            param, suffix, opts = DIMENSIONS[dim]
            for opt in opts:
                if target_reached():
                    break
                if (dim, opt) in done_categories:
                    log.info(f"[略過已完成分類] {dim}={opt}")
                    continue

                links = crawl_category(session, dim, opt, param, suffix, args.max_pages)
                todo = [(seq, url) for seq, url in links
                        if seq not in records or not records[seq].steps_text]

                remaining = target_remaining()
                if remaining is not None:
                    todo = todo[:remaining]
                if args.limit_recipes is not None:
                    todo = todo[: max(0, args.limit_recipes - new_count)]

                for i, (seq, url) in enumerate(todo, 1):
                    log.info(f"[內頁 {dim}={opt} {i}/{len(todo)}] 累計 {len(records)+1} 筆 -> {url}")
                    soup, html = get(session, url)
                    if soup is None:
                        continue
                    records[seq] = parse_detail(soup, html, seq, url)
                    new_count += 1
                    if new_count % 20 == 0:
                        save_all(records, outdir)  # 中繼存檔：JSON+CSV 一起寫

                    if target_reached() or (args.limit_recipes is not None and new_count >= args.limit_recipes):
                        break

                # 這個分類的連結若已經完整跑過（沒被 target/limit 提前中斷），才算完成，
                # 下次可以直接跳過，不用重新爬列表頁。
                if not target_reached() and (args.limit_recipes is None or new_count < args.limit_recipes):
                    done_categories.add((dim, opt))
                    save_progress(done_categories, progress_path)
    finally:
        save_all(records, outdir)  # 不論正常結束、達到 target 或中途出錯，都保證存檔
        save_progress(done_categories, progress_path)

    if target_reached():
        log.info(f"已達到目標筆數 {args.target}，停止。")
    log.info(f"本次新抓 {new_count} 筆，累計 {len(records)} 筆。")


if __name__ == "__main__":
    main()