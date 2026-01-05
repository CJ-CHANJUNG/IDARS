# -*- coding: utf-8 -*-
"""
기존 프로젝트의 final_results.json에서 final_status 제거
사용자가 직접 최종판단한 것만 남기기 위함
"""

import json
from pathlib import Path

def clear_final_status(project_path):
    """
    프로젝트의 final_results.json에서 final_status 키 제거
    """
    final_file = Path(project_path) / 'step3_data_extraction' / 'final_results.json'

    if not final_file.exists():
        print(f"❌ 파일 없음: {final_file}")
        return

    # 파일 로드
    with open(final_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # final_status 제거
    removed_count = 0
    for doc_id, doc_data in data.items():
        if 'final_status' in doc_data:
            del doc_data['final_status']
            removed_count += 1

    # 파일 저장
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 완료: {removed_count}개 전표의 final_status 제거")
    print(f"   파일: {final_file}")

if __name__ == '__main__':
    # 프로젝트 경로 지정
    project_path = r"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\샘플2_20251231_072311"

    print(f"프로젝트: {project_path}")
    clear_final_status(project_path)
    print("\n✨ 이제 프론트엔드를 새로고침하면 모든 전표가 '판단 대기' 상태가 됩니다.")
