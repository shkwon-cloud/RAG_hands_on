import os
import wikipediaapi
import json
import argparse
import time

wiki = wikipediaapi.Wikipedia(
    language='ko',
    user_agent='rag-data-bot/0.1 (for research purposes only;)'
)

REQUEST_DELAY = 0.5   # 요청 간 딜레이 (초)
MAX_RETRIES = 3       # 최대 재시도 횟수

def _safe_get_text(page, retries=MAX_RETRIES):
    """Wikipedia 페이지 텍스트를 안전하게 가져오기 (재시도 포함)"""
    for attempt in range(retries):
        try:
            return page.text
        except Exception as e:
            print(f"  ⚠ '{page.title}' 텍스트 가져오기 실패 (시도 {attempt+1}/{retries}): {e}")
            time.sleep(2 ** attempt)  # 지수 백오프: 1초, 2초, 4초
    print(f"  ❌ '{page.title}' 건너뜀 (재시도 모두 실패)")
    return ""

def get_pages_in_category(cat_title: str, max_depth=2):
    category = wiki.page(cat_title)
    visited_cats = set()
    visited_titles = set()
    results = []

    def recurse(cat, depth):
        if depth > max_depth or cat.title in visited_cats:
            return
        visited_cats.add(cat.title)

        for member in cat.categorymembers.values():
            if member.ns == wikipediaapi.Namespace.CATEGORY:
                recurse(member, depth + 1)
            elif member.ns == wikipediaapi.Namespace.MAIN:
                if member.title not in visited_titles:
                    text = _safe_get_text(member)
                    if len(text) > 500:
                        visited_titles.add(member.title)
                        results.append(member)
                        if len(results) % 10 == 0:
                            print(f"len(results): {len(results)}")
                    time.sleep(REQUEST_DELAY)  # Rate limiting 방지

    recurse(category, 0)
    print(f"final len(results): {len(results)}")
    return results

def save_pages_as_jsonl(pages, output_path="data/wiki.jsonl"):
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "wiki.jsonl")
    elif not output_path.endswith(".jsonl"):
        output_path = f"{output_path}.jsonl"
    
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for page in pages:
            record = {
                "title": page.title,
                "url": page.fullurl,
                "text": page.text.strip(),
                "source_type": "Wikipedia"
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"✅ JSONL 저장 완료: {len(pages)}개 문서 → {output_path}")

def save_single_page_as_jsonl(page, output_path="data/wiki_single.jsonl"):
    if not page.exists():
        print(f"❌ 문서 '{page.title}' 가 존재하지 않습니다.")
        return
    
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "wiki_single.jsonl")
    elif not output_path.endswith(".jsonl"):
        output_path = f"{output_path}.jsonl"
        
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        record = {
            "title": page.title,
            "url": page.fullurl,
            "text": page.text.strip(),
            "source_type": "Wikipedia"
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"✅ 단일 문서 저장 완료: {page.title} → {output_path}")

def main():
    p = argparse.ArgumentParser(description="Collect Wikipedia pages by category or single page")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--category", type=str,
                       help="Category title to collect pages from. ex) '분류:조선_세종'")
    group.add_argument("--page", type=str,
                       help="Single page title to collect. ex) '세종대왕'")
    p.add_argument("--max_depth", type=int, default=3,
                   help="Maximum depth to traverse subcategories (category mode only)")
    p.add_argument("--output", type=str, default="data/wiki.jsonl",
                   help="Output JSONL file path")
    args = p.parse_args()

    if args.page:
        page = wiki.page(args.page)
        save_single_page_as_jsonl(page, args.output)
    else:
        pages = get_pages_in_category(args.category, args.max_depth)
        save_pages_as_jsonl(pages, args.output)

if __name__ == "__main__":
    main()
