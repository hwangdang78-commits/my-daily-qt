import datetime
import json
import os
import re
import sys
import requests
from bs4 import BeautifulSoup

KST = datetime.timezone(datetime.timedelta(hours=9))
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyQTBot/1.0)"}

GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
]

USER_COMMENTARY_PROMPT = """
아래 성경 본문을 바탕으로, 다음 기준을 엄격하게 지켜 한국어 JSON으로 정리해줘.

[기본 규칙]
- 성경 본문은 우리말성경 표현을 우선해서 설명하고, 필요할 때 개역개정 등 다른 번역본과 비교해도 된다. 단, 정확한 성경 구절 인용 시 번역본을 명확히 밝혀라.
- 본문을 단순히 요약하는 데 그치지 말고, 하나님의 뜻과 오늘의 삶에 어떻게 적용할 수 있는지까지 연결하라.
- 본문의 의미를 지나치게 확대해석하거나 근거 없이 단정하지 말고, 서로 다른 해석이 가능한 부분은 "이렇게 해석되기도 한다"고 구분하라.
- 어려운 신학 용어는 쉬운 한국어로 풀어서 설명하고, 따뜻하고 묵상적인 분위기를 유지하라.
- 억지로 모든 본문을 예수님의 직접적인 예표라고 해석하지 말고, 성경 전체의 구속사적 흐름 안에서 자연스럽게 연결하라.
- 소그룹 질문은 정답을 맞히는 질문이 아니라 각자의 경험을 편하게 나눌 수 있는 쉬운 질문으로 작성하라.
- 순장예배 QT 나눔용은 설교식이 아닌 4단계(1. 마음에 와닿은 말씀 1~2절, 2. 말씀을 통해 깨달은 점, 3. 내 삶과 순장 섬김에 대한 적용, 4. 공동체가 함께 기도할 기도제목)로 작성하라.

[반드시 출력할 JSON 스키마]
{
  "coreSummary": "1. 본문의 핵심 주제 — 본문 전체를 1~2문장으로 쉽게 요약",
  "coreMessage": "1. 가장 중요한 영적 메시지 1~2문장",
  "structureRows": [
    {"range": "단락 범위", "theme": "단락 제목", "msg": "내용과 핵심 의미 간단 설명"}
  ],
  "commentaryOverview": "3. 역사적·신학적 배경",
  "commentaryDetails": [
    {"title": "① 소제목 (절 범위)", "bullets": ["중요 절·표현 설명, 앞뒤 문맥, 반전·반복·대조, 다른 해석 구분 등"]}
  ],
  "godAttributes": [
    {"name": "하나님의 성품/사역 이름", "desc": "쉬운 설명과 근거 절"}
  ],
  "christConnection": "6. 신약 및 예수 그리스도와의 자연스러운 구속사적 연결",
  "meditationPoints": [
    {"title": "묵상 포인트 제목", "desc": "설명", "question": "현실적인 적용 질문 1개"}
  ],
  "keyVerses": [
    {"ref": "책 장:절 (번역본 명시)", "text": "정확한 성경 인용구", "why": "이 구절이 중요한 이유"}
  ],
  "oneLiner": "9. 오늘의 묵상 한 문장",
  "shortPrayer": "10. 짧은 기도",
  "smallGroupQuestions": ["소그룹 쉬운 나눔 질문 3~4개"],
  "sermonOutline": {
    "theme": "설교 핵심 제목",
    "flow": "본문의 논리적 흐름",
    "points": ["설교 대지 1", "설교 대지 2", "설교 대지 3"],
    "application": "예화 및 적용 방향"
  },
  "soonjangGuide": {
    "verses": "1) 마음에 와닿은 말씀 1~2절",
    "realized": "2) 말씀을 통해 깨달은 점",
    "application": "3) 내 삶과 순장 섬김에 대한 적용",
    "prayers": ["4) 공동체가 함께 기도할 기도제목 1", "기도제목 2"]
  },
  "words": [
    {"heb": "원어 표기 (발음)", "verse": "장:절", "meaning": "쉬운 뜻", "desc": "문맥 속 의미"}
  ],
  "questions": [
    {"title": "1. 적용 질문 제목", "question": "질문", "action": "오늘의 실천 가이드", "sample": "예시 묵상 답안"}
  ],
  "samplePrayer": "개인 QT 다이어리용 맞춤형 묵상 기도문"
}
""".strip()


def get_target_dates() -> list:
    env_date = os.environ.get("TARGET_DATE", "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", env_date):
        return [env_date]
    today = datetime.datetime.now(KST).date()
    return [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]


def extract_verses_from_soup(soup: BeautifulSoup) -> list:
    verses = []
    # 1) HTML table rows (<tr><th>7</th><td>본문</td></tr> 또는 <td>7</td><td>본문</td>)
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if len(cells) >= 2 and re.match(r"^\d{1,3}$", cells[0]) and len(cells[1]) >= 4:
            verses.append((cells[0], cells[1]))
    if verses:
        return verses

    # 2) Consecutive lines fallback (줄바꿈으로 절 번호와 본문이 분리된 경우)
    lines = [ln.strip() for ln in soup.get_text("\n", strip=True).splitlines() if ln.strip()]
    in_bible = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        if "역본 선택" in ln or "본문 말씀" in ln:
            in_bible = True
            i += 1
            continue
        if in_bible and ("명이 아멘하셨습니다" in ln or "아멘하기" in ln or "Copyright" in ln):
            break
        if in_bible:
            m_same = re.match(r"^(\d{1,3})\s+([가-힣“\"'].{4,})$", ln)
            if m_same:
                verses.append((m_same.group(1), m_same.group(2).strip()))
            elif re.match(r"^\d{1,3}$", ln) and i + 1 < len(lines) and len(lines[i + 1]) >= 4:
                verses.append((ln, lines[i + 1].strip()))
                i += 1
        i += 1
    return verses


def fetch_duranno_krv(date_str: str) -> dict:
    url = f"https://www.duranno.com/qt/view/bible.asp?qtDate={date_str}"
    res = requests.get(url, headers=HEADERS, timeout=20)
    res.encoding = res.apparent_encoding or "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    lines = [ln.strip() for ln in soup.get_text("\n", strip=True).splitlines() if ln.strip()]

    title = f"{date_str} 오늘의 QT"
    passage_ref = f"{date_str} 본문"
    hymn = "🎵 오늘의 찬송은 두란노 생명의 삶을 참고하세요"
    today_prayer = ""
    amen_count = 0

    for idx, ln in enumerate(lines):
        m_ref = re.match(r"^([가-힣]+\s+\d+\s*:\s*\d+\s*[~-]\s*[\d:]+)(.*)$", ln)
        if m_ref and passage_ref.endswith("본문"):
            passage_ref = re.sub(r"\s+", " ", m_ref.group(1)).strip()
            rest = m_ref.group(2).strip()
            if rest:
                title = rest
            elif idx + 1 < len(lines) and lines[idx + 1] not in ("본문 말씀", "글씨 크게"):
                title = lines[idx + 1]
        if ln.startswith("(새 ") or ln.startswith("새찬송가"):
            hymn = f"🎵 오늘의 찬송: {ln}"
        if "명이 아멘하셨습니다" in ln:
            nums = re.findall(r"\d+", ln.replace(",", ""))
            if nums:
                amen_count = int(nums[0])
        if ln == "오늘의 기도" and idx + 1 < len(lines):
            today_prayer = lines[idx + 1]

    verses_krv = extract_verses_from_soup(soup)
    return {
        "date": date_str,
        "passageRef": passage_ref,
        "title": title,
        "hymn": hymn,
        "initialAmen": amen_count,
        "todayPrayer": today_prayer,
        "verses_krv": verses_krv,
    }


def fetch_duranno_urimal(date_str: str) -> list:
    today_str = datetime.datetime.now(KST).strftime("%Y-%m-%d")
    if date_str != today_str:
        return []
    try:
        res = requests.get("https://www.duranno.com/sena/qt.asp", headers=HEADERS, timeout=20)
        res.encoding = res.apparent_encoding or "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        verses = []
        for ln in [l.strip() for l in soup.get_text("\n", strip=True).splitlines() if l.strip()]:
            m_v = re.match(r"^(\d{1,3})\s*([가-힣“\"'].{4,})$", ln)
            if m_v:
                verses.append((m_v.group(1), m_v.group(2).strip()))
        return verses
    except Exception:
        return []


def build_sections(passage_ref: str, verses_krv: list, verses_urimal: list) -> list:
    m_ch = re.search(r"(\d+)\s*:", passage_ref)
    current_ch = int(m_ch.group(1)) if m_ch else 1
    prev_vnum = 0
    combined = []
    urimal_map = {idx: vtxt for idx, (_, vtxt) in enumerate(verses_urimal)}

    for idx, (vnum_str, krv_txt) in enumerate(verses_krv):
        vnum = int(vnum_str)
        if prev_vnum > 0 and vnum < prev_vnum:
            current_ch += 1
        prev_vnum = vnum
        urimal_txt = urimal_map.get(idx, krv_txt)
        combined.append({"ref": f"{current_ch}:{vnum}", "urimal": urimal_txt, "krv": krv_txt})

    if not combined:
        return []
    return [{"subtitleUrimal": f"오늘의 말씀 ({passage_ref})", "subtitleKrv": f"오늘의 말씀 ({passage_ref})", "verses": combined}]


def call_gemini_with_fallback(api_key: str, prompt: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }
    last_err = None
    for model_id in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        resp = requests.post(url, json=payload, timeout=90)
        if resp.status_code == 200:
            print(f"[DailyQT] Gemini model succeeded: {model_id}")
            raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)
        last_err = f"{model_id} -> HTTP {resp.status_code}: {resp.text[:200]}"
        print(f"[DailyQT] Model retry: {last_err}", file=sys.stderr)
    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def generate_commentary_with_gemini(passage_ref: str, title: str, sections: list) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY secret is empty")
    verse_lines = [f"[{v['ref']}] 우리말성경: {v['urimal']} / 개역개정: {v['krv']}" for sec in sections for v in sec.get("verses", [])]
    full_prompt = f"{USER_COMMENTARY_PROMPT}\n\n[본문 정보]\n- 범위: {passage_ref}\n- 제목: {title}\n- 본문:\n" + "\n".join(verse_lines)
    return call_gemini_with_fallback(api_key, full_prompt)


def needs_regeneration(out_file: str) -> bool:
    if not os.path.exists(out_file):
        return True
    try:
        data = json.load(open(out_file, encoding="utf-8"))
        return not data.get("sections") or not data.get("coreSummary")
    except Exception:
        return True


def process_one_date(date_str: str, force: bool = False):
    os.makedirs("qt", exist_ok=True)
    out_file = os.path.join("qt", f"{date_str}.json")
    if not force and not needs_regeneration(out_file):
        print(f"[DailyQT] Already complete: {out_file} (skip)")
        return

    print(f"[DailyQT] Generating {date_str}...")
    krv_info = fetch_duranno_krv(date_str)
    urimal_verses = fetch_duranno_urimal(date_str)
    sections = build_sections(krv_info["passageRef"], krv_info["verses_krv"], urimal_verses)
    verse_count = len(sections[0]["verses"]) if sections else 0
    print(f"[DailyQT] Parsed {verse_count} verses for {date_str} ({krv_info['passageRef']})")

    commentary = generate_commentary_with_gemini(krv_info["passageRef"], krv_info["title"], sections)

    record = {
        "date": date_str,
        "passageRef": krv_info["passageRef"],
        "title": krv_info["title"],
        "hymn": krv_info["hymn"],
        "initialAmen": krv_info["initialAmen"],
        "sourceType": "자동 피드 동기화",
        "todayPrayer": krv_info["todayPrayer"] or commentary.get("shortPrayer", ""),
        "sections": sections,
        "coreSummary": commentary.get("coreSummary", ""),
        "coreMessage": commentary.get("coreMessage", ""),
        "structureRows": commentary.get("structureRows", []),
        "commentaryOverview": commentary.get("commentaryOverview", ""),
        "commentaryDetails": commentary.get("commentaryDetails", []),
        "godAttributes": commentary.get("godAttributes", []),
        "christConnection": commentary.get("christConnection", ""),
        "meditationPoints": commentary.get("meditationPoints", []),
        "keyVerses": commentary.get("keyVerses", []),
        "oneLiner": commentary.get("oneLiner", ""),
        "shortPrayer": commentary.get("shortPrayer", ""),
        "smallGroupQuestions": commentary.get("smallGroupQuestions", []),
        "sermonOutline": commentary.get("sermonOutline", {}),
        "soonjangGuide": commentary.get("soonjangGuide", {}),
        "words": commentary.get("words", []),
        "questions": commentary.get("questions", []),
        "samplePrayer": commentary.get("samplePrayer", commentary.get("shortPrayer", "")),
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print(f"[DailyQT] Saved complete QT to {out_file}")


def main():
    is_manual = bool(os.environ.get("TARGET_DATE", "").strip())
    for date_str in get_target_dates():
        process_one_date(date_str, force=is_manual)

    dates = sorted(f.replace(".json", "") for f in os.listdir("qt") if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", f))
    with open(os.path.join("qt", "index.json"), "w", encoding="utf-8") as f:
        json.dump({"updatedAt": datetime.datetime.now(KST).isoformat(), "dates": dates}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
