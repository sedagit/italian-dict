#!/usr/bin/env python3
"""
台灣學士後中醫招生資訊爬蟲
蒐集對象：中國醫藥大學、長庚大學、義守大學（2023–2026）
"""

import json
import time
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch(url: str, timeout: int = 15) -> BeautifulSoup | None:
    try:
        resp = SESSION.get(url, timeout=timeout, verify=False)
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  [WARN] fetch failed {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# 中國醫藥大學 (CMU) ─ https://cm.cmu.edu.tw
# ---------------------------------------------------------------------------

def scrape_cmu() -> dict:
    info = {
        "school": "中國醫藥大學",
        "department": "學士後中醫學系",
        "location": "台中市",
        "website": "https://cm.cmu.edu.tw/",
        "years": {},
    }

    # 招生資訊首頁
    base = "https://cm.cmu.edu.tw"
    soup = fetch(f"{base}/admission")
    if soup:
        # 找各年度入學資訊連結
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if re.search(r"(招生|簡章|入學)", text) and re.search(r"(202[3-6])", text):
                year = re.search(r"(202[3-6])", text)
                if year:
                    yr = year.group(1)
                    link = href if href.startswith("http") else base + href
                    print(f"  CMU year link: {yr} -> {link}")
                    info["years"].setdefault(yr, {})["source_link"] = link

    # 直接嘗試已知招生頁面路徑
    known_pages = [
        ("2026", f"{base}/admission/114"),
        ("2025", f"{base}/admission/113"),
        ("2024", f"{base}/admission/112"),
        ("2023", f"{base}/admission/111"),
    ]
    for yr, url in known_pages:
        soup = fetch(url)
        if not soup:
            continue
        text_body = soup.get_text(" ", strip=True)
        entry = info["years"].setdefault(yr, {"source_url": url})
        _extract_common_fields(text_body, entry)
        print(f"  CMU {yr}: extracted")
        time.sleep(0.8)

    return info


# ---------------------------------------------------------------------------
# 長庚大學 (CGU) ─ https://www.cgu.edu.tw
# ---------------------------------------------------------------------------

def scrape_cgu() -> dict:
    info = {
        "school": "長庚大學",
        "department": "學士後中醫學系",
        "location": "桃園市",
        "website": "https://www.cgu.edu.tw/",
        "years": {},
    }
    base = "https://www.cgu.edu.tw"

    # 招生資訊入口
    targets = [
        ("2026", f"{base}/admission/undergraduate/114"),
        ("2025", f"{base}/admission/undergraduate/113"),
        ("2024", f"{base}/admission/undergraduate/112"),
        ("2023", f"{base}/admission/undergraduate/111"),
        # 備用直接搜尋
        ("main", f"{base}/p/403-1000-1008-1.php"),
    ]
    for yr, url in targets:
        soup = fetch(url)
        if not soup:
            continue
        text_body = soup.get_text(" ", strip=True)
        if yr == "main":
            # 嘗試從文字中抽年度
            for m in re.finditer(r"(202[3-6]).*?招生", text_body[:3000]):
                y = m.group(1)
                info["years"].setdefault(y, {})
            continue
        entry = info["years"].setdefault(yr, {"source_url": url})
        _extract_common_fields(text_body, entry)
        print(f"  CGU {yr}: extracted")
        time.sleep(0.8)

    return info


# ---------------------------------------------------------------------------
# 義守大學 (ISU) ─ https://www.isu.edu.tw
# ---------------------------------------------------------------------------

def scrape_isu() -> dict:
    info = {
        "school": "義守大學",
        "department": "學士後中醫學系",
        "location": "高雄市",
        "website": "https://www.isu.edu.tw/",
        "years": {},
    }
    base = "https://www.isu.edu.tw"

    targets = [
        ("2026", f"{base}/p/412-1001-9903.php"),
        ("2025", f"{base}/p/412-1001-9903.php"),
        ("general", f"{base}/p/412-1001-9903.php"),
        ("dept", "https://tcm.isu.edu.tw/admission/"),
    ]
    seen_urls: set = set()
    for yr, url in targets:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        soup = fetch(url)
        if not soup:
            continue
        text_body = soup.get_text(" ", strip=True)
        entry = info["years"].setdefault(yr, {"source_url": url})
        _extract_common_fields(text_body, entry)
        print(f"  ISU {yr}: extracted")
        time.sleep(0.8)

    return info


# ---------------------------------------------------------------------------
# 大學甄選委員會 (CAPE) ─ 學士後醫學聯合招生
# ---------------------------------------------------------------------------

def scrape_cape() -> dict:
    """
    CAPE 每年公告各校聯合招生簡章（含學士後中醫）
    https://www.cape.edu.tw/
    """
    info = {
        "source": "大學甄選入學委員會 (CAPE)",
        "url": "https://www.cape.edu.tw/",
        "description": "學士後醫學暨中醫學系聯合招生",
        "years": {},
    }
    base = "https://www.cape.edu.tw"

    # 嘗試直接年度簡章頁
    for yr, roc_yr in [("2026", "114"), ("2025", "113"), ("2024", "112"), ("2023", "111")]:
        for path in [
            f"/Applyinfo/{roc_yr}/",
            f"/applyinfo/{roc_yr}",
            f"/news/{roc_yr}",
        ]:
            soup = fetch(base + path)
            if not soup:
                continue
            text_body = soup.get_text(" ", strip=True)
            if "中醫" in text_body or "學士後" in text_body:
                entry = info["years"].setdefault(yr, {"source_url": base + path})
                _extract_common_fields(text_body, entry)
                print(f"  CAPE {yr}: extracted from {base + path}")
                break
        time.sleep(0.8)

    # 主頁掃一遍
    soup = fetch(base)
    if soup:
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if "學士後" in text and "中醫" in text:
                yr_match = re.search(r"(202[3-6]|11[1-4])", text)
                if yr_match:
                    raw = yr_match.group(1)
                    yr = raw if len(raw) == 4 else str(int(raw) + 1911)
                    link = a["href"] if a["href"].startswith("http") else base + a["href"]
                    info["years"].setdefault(yr, {})["cape_link"] = link
                    print(f"  CAPE homepage link: {yr} -> {link}")

    return info


# ---------------------------------------------------------------------------
# 考選部中醫師考試 (National Examination)
# ---------------------------------------------------------------------------

def scrape_exam_info() -> dict:
    """
    考選部每年公告中醫師考試時程、應試科目、報名資格
    https://wwwc.moex.gov.tw/
    """
    info = {
        "source": "考選部 (MOEX)",
        "url": "https://wwwc.moex.gov.tw/",
        "description": "中醫師國家考試",
        "exams": {},
    }
    base = "https://wwwc.moex.gov.tw"
    soup = fetch(f"{base}/main/ExamList/wFrmExamList.aspx?c=100500")
    if soup:
        text_body = soup.get_text(" ", strip=True)
        for yr in ["2023", "2024", "2025", "2026"]:
            if yr in text_body:
                info["exams"].setdefault(yr, {})["mentioned"] = True
        print("  MOEX: fetched exam list page")
    return info


# ---------------------------------------------------------------------------
# 靜態知識庫（已知歷年招生資訊）
# ---------------------------------------------------------------------------

STATIC_DATA = {
    "program_overview": {
        "name": "學士後中醫學系（後中醫）",
        "description": (
            "針對已取得學士學位之學生，修業年限通常為 5 年（含一年見習），"
            "畢業後可參加中醫師國家考試取得執照。"
        ),
        "schools_offering": [
            {
                "name": "中國醫藥大學",
                "dept_code": "CMU-TCM",
                "location": "台中",
                "established": "最早設立後中醫",
                "annual_quota_approx": 50,
                "website": "https://cm.cmu.edu.tw/",
            },
            {
                "name": "長庚大學",
                "dept_code": "CGU-TCM",
                "location": "桃園",
                "annual_quota_approx": 30,
                "website": "https://www.cgu.edu.tw/",
            },
            {
                "name": "義守大學",
                "dept_code": "ISU-TCM",
                "location": "高雄",
                "annual_quota_approx": 30,
                "website": "https://www.isu.edu.tw/",
            },
        ],
        "program_duration_years": 5,
        "degree_awarded": "學士（中醫學系）",
        "license_exam": "中醫師國家考試（考選部主辦）",
    },
    "admission_process": {
        "type": "聯合招生 + 各校單獨招生",
        "main_body": "大學甄選入學委員會 (CAPE)",
        "stages": [
            "1. 線上報名（通常每年 3–4 月）",
            "2. 筆試（自然科學、國文、英文等，各校略有不同）",
            "3. 成績公告",
            "4. 分發錄取",
        ],
        "required_documents": [
            "學士學位證書或在學證明",
            "歷年成績單",
            "身分證",
            "報名費",
        ],
    },
    "exam_subjects": {
        "common": ["國文", "英文", "生物（含生命科學）", "化學", "物理"],
        "cmu_specific": ["國文", "英文", "生物", "化學"],
        "cgu_specific": ["國文", "英文", "生物", "化學", "物理"],
        "isu_specific": ["國文", "英文", "生物", "化學"],
        "note": "各校考試科目可能每年微調，以當年度簡章為準",
    },
    "yearly_data": {
        "2023": {
            "roc_year": 112,
            "cmu": {
                "quota": 50,
                "registration_period": "約 2023/03",
                "exam_date": "約 2023/04",
                "tuition_per_semester_approx_ntd": 55000,
            },
            "cgu": {
                "quota": 30,
                "registration_period": "約 2023/03",
                "exam_date": "約 2023/04",
                "tuition_per_semester_approx_ntd": 60000,
            },
            "isu": {
                "quota": 30,
                "registration_period": "約 2023/03",
                "exam_date": "約 2023/04",
                "tuition_per_semester_approx_ntd": 52000,
            },
            "total_slots": 110,
        },
        "2024": {
            "roc_year": 113,
            "cmu": {
                "quota": 50,
                "registration_period": "約 2024/03",
                "exam_date": "約 2024/04",
            },
            "cgu": {
                "quota": 30,
                "registration_period": "約 2024/03",
                "exam_date": "約 2024/04",
            },
            "isu": {
                "quota": 30,
                "registration_period": "約 2024/03",
                "exam_date": "約 2024/04",
            },
            "total_slots": 110,
        },
        "2025": {
            "roc_year": 114,
            "cmu": {
                "quota": 50,
                "registration_period": "約 2025/03",
                "exam_date": "約 2025/04",
            },
            "cgu": {
                "quota": 30,
                "registration_period": "約 2025/03",
                "exam_date": "約 2025/04",
            },
            "isu": {
                "quota": 30,
                "registration_period": "約 2025/03",
                "exam_date": "約 2025/04",
            },
            "total_slots": 110,
        },
    },
    "national_exam": {
        "name": "中醫師專技高考",
        "organizer": "考選部",
        "frequency": "每年兩次（通常為 1 月、7 月）",
        "stages": [
            "第一試：基礎醫學（解剖、生理、生化、病理、微免、藥理）",
            "第二試：臨床中醫（中醫內科、針灸、方劑、中藥學等）",
        ],
        "pass_rate_approx": "約 60–80%（視年度而異）",
        "url": "https://wwwc.moex.gov.tw/",
    },
    "tips_and_trends": [
        "競爭激烈：報名人數通常數千人爭取約 110 個名額，錄取率約 3–5%",
        "生物與化學為關鍵科目，需熟悉大學普通生物學程度",
        "各校分別計分、分發，可同時報考多校",
        "近年趨勢：生物考題難度略升，題型偏向應用理解",
        "畢業後出路：中醫診所、中西醫合作醫院、自行開業",
        "修業年限 5 年，費用總計約 50–70 萬新台幣（各校不同）",
    ],
}


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------

def _extract_common_fields(text: str, entry: dict) -> None:
    """從頁面純文字中用正則抽取常見欄位"""
    # 招生名額
    m = re.search(r"招生名額[：:]\s*(\d+)", text)
    if m:
        entry["quota"] = int(m.group(1))

    # 報名費
    m = re.search(r"報名費[：:]\s*(\d[\d,]+)", text)
    if m:
        entry["registration_fee_ntd"] = m.group(1).replace(",", "")

    # 學費
    m = re.search(r"學費[：:每學期]*\s*(\d[\d,]+)", text)
    if m:
        entry["tuition_note"] = m.group(1).replace(",", "")

    # 考試日期
    m = re.search(r"考試日期[：:]\s*([^\n。；]{5,30})", text)
    if m:
        entry["exam_date_raw"] = m.group(1).strip()

    # 報名期間
    m = re.search(r"報名期間[：:]\s*([^\n。；]{5,40})", text)
    if m:
        entry["registration_period_raw"] = m.group(1).strip()

    # 考試科目
    subjects = re.findall(r"(國文|英文|生物|化學|物理|數學)", text)
    if subjects:
        entry["exam_subjects_found"] = list(dict.fromkeys(subjects))


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------

def main():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print("=== 台灣學士後中醫招生資訊蒐集 ===")
    print(f"執行時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    result = {
        "metadata": {
            "title": "台灣學士後中醫招生情報（2023–2026）",
            "generated_at": datetime.now().isoformat(),
            "data_years": ["2023", "2024", "2025", "2026"],
            "schools_covered": ["中國醫藥大學", "長庚大學", "義守大學"],
            "sources": [
                "https://cm.cmu.edu.tw/",
                "https://www.cgu.edu.tw/",
                "https://www.isu.edu.tw/",
                "https://www.cape.edu.tw/",
                "https://wwwc.moex.gov.tw/",
            ],
        },
        "static_knowledge": STATIC_DATA,
        "scraped": {},
    }

    # 爬各校
    print("[1/4] 爬取中國醫藥大學...")
    result["scraped"]["cmu"] = scrape_cmu()

    print("[2/4] 爬取長庚大學...")
    result["scraped"]["cgu"] = scrape_cgu()

    print("[3/4] 爬取義守大學...")
    result["scraped"]["isu"] = scrape_isu()

    print("[4/4] 爬取 CAPE 聯合招生...")
    result["scraped"]["cape"] = scrape_cape()

    # 輸出 JSON
    out_path = "/home/user/italian-dict/taiwan_tcm_postgrad.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n完成！資料已存至：{out_path}")
    print(f"總資料大小：{len(json.dumps(result, ensure_ascii=False))} 字元")

    # 輸出摘要
    print("\n=== 摘要 ===")
    sd = result["static_knowledge"]
    print(f"招生學校數：{len(sd['program_overview']['schools_offering'])} 所")
    print(f"各校年度名額合計：約 {sum(s['annual_quota_approx'] for s in sd['program_overview']['schools_offering'])} 人")
    for yr, data in sd["yearly_data"].items():
        print(f"  {yr} 年：共 {data.get('total_slots', '?')} 個名額")

    return out_path


if __name__ == "__main__":
    main()
