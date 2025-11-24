#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
정확도 측정 도구
파싱 결과와 정답을 비교하여 정확도를 측정합니다.
"""

# ═══════════════════════════════════════════════════════════════════════
# 🔧 사용자 설정 (여기만 수정하세요!)
# ═══════════════════════════════════════════════════════════════════════

# [필수] 정답 데이터 파일 경로 (test_data.json)
GROUND_TRUTH_FILE = r"D:\CJ\Project Manager\IDARS\Data\test_data.json"

# [선택] PDF 파일들이 있는 폴더 (비워두면 정답 파일과 같은 폴더 사용)
PDF_FOLDER = ""

# ═══════════════════════════════════════════════════════════════════════
# ✅ 설정 완료 - 아래 코드는 수정하지 마세요!
# ═══════════════════════════════════════════════════════════════════════

import json
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
import sys

try:
    from posco_parser import DocumentParser
except ImportError:
    print("❌ Error: posco_parser.py를 찾을 수 없습니다.")
    print("   이 파일을 posco_parser.py와 같은 폴더에 두세요.")
    sys.exit(1)


class AccuracyChecker:
    """
    정확도 측정 및 분석
    """
    
    def __init__(self, ground_truth_path: str):
        """
        Args:
            ground_truth_path: 정답 데이터 JSON 파일 경로
        """
        self.ground_truth_path = Path(ground_truth_path)
        self.ground_truth = self.load_ground_truth()
        self.results = []
        
    def load_ground_truth(self) -> Dict:
        """
        정답 데이터 로드
        
        Returns:
            정답 데이터 딕셔너리
        """
        if not self.ground_truth_path.exists():
            print(f"⚠️  정답 파일이 없습니다: {self.ground_truth_path}")
            print("\n📝 정답 파일 생성 방법:")
            print(self.get_sample_ground_truth())
            sys.exit(1)
        
        with open(self.ground_truth_path, encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def get_sample_ground_truth() -> str:
        """
        샘플 정답 데이터 형식 반환
        """
        return """
{
  "file1.pdf": {
    "invoice": {
      "invoice_number": "1234567",
      "invoice_date": "2025-06-30",
      "currency": "EUR",
      "total_amount": 54656.40,
      "shipper": "POSCO INTERNATIONAL CORPORATION"
    },
    "bl": {
      "bl_number": "PLIHQ4G81934",
      "vessel_name": "CMA CGM PLATINUM",
      "port_of_loading": "BUSAN, KOREA"
    }
  },
  "file2.pdf": {
    "invoice": {
      "invoice_number": "7654321",
      ...
    }
  }
}
"""
    
    def normalize_value(self, value: Any) -> str:
        """
        값 정규화 (비교 용이하게)
        
        Args:
            value: 원본 값
            
        Returns:
            정규화된 문자열
        """
        if value is None:
            return ""
        
        # 공백 제거, 소문자 변환
        s = str(value).strip().lower()
        
        # 쉼표 제거 (금액 비교용)
        s = s.replace(',', '')
        
        return s
    
    def compare_values(self, pred: Any, truth: Any) -> bool:
        """
        두 값이 같은지 비교
        
        Args:
            pred: 예측값
            truth: 정답값
            
        Returns:
            일치 여부
        """
        pred_norm = self.normalize_value(pred)
        truth_norm = self.normalize_value(truth)
        
        # 완전 일치
        if pred_norm == truth_norm:
            return True
        
        # 숫자인 경우 float 비교
        try:
            pred_float = float(pred_norm)
            truth_float = float(truth_norm)
            
            # 0.01 오차 허용
            if abs(pred_float - truth_float) < 0.01:
                return True
        except (ValueError, TypeError):
            pass
        
        # 부분 일치 (문자열 포함)
        if truth_norm and truth_norm in pred_norm:
            return True
        
        return False
    
    def calculate_field_accuracy(self, 
                                 predictions: Dict, 
                                 ground_truth: Dict) -> Dict:
        """
        필드별 정확도 계산
        
        Args:
            predictions: 예측 결과
            ground_truth: 정답
            
        Returns:
            필드별 정확도 딕셔너리
        """
        results = {}
        
        for field, true_value in ground_truth.items():
            pred_value = predictions.get(field)
            is_correct = self.compare_values(pred_value, true_value)
            
            results[field] = {
                'predicted': pred_value,
                'expected': true_value,
                'correct': is_correct
            }
        
        return results
    
    def run_test(self, pdf_dir: str = None) -> Dict:
        """
        전체 테스트 실행
        
        Args:
            pdf_dir: PDF 파일 디렉토리 (기본값: ground_truth와 같은 위치)
            
        Returns:
            테스트 결과
        """
        if pdf_dir is None:
            pdf_dir = self.ground_truth_path.parent
        
        pdf_path = Path(pdf_dir)
        
        print("\n" + "="*80)
        print("📊 정확도 테스트 시작")
        print("="*80)
        
        # 통계
        total_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        error_cases = []
        
        # 각 파일 테스트
        for pdf_file, expected in self.ground_truth.items():
            pdf_full_path = pdf_path / pdf_file
            
            if not pdf_full_path.exists():
                print(f"⚠️  파일 없음: {pdf_file}")
                continue
            
            print(f"\n📄 Testing: {pdf_file}")
            
            # 파싱 실행
            try:
                with DocumentParser(str(pdf_full_path)) as parser:
                    results = parser.parse_all()
            except Exception as e:
                print(f"❌ 파싱 실패: {e}")
                continue
            
            # 각 문서 유형별로 비교
            for doc_type, expected_fields in expected.items():
                if doc_type not in results['documents']:
                    print(f"  ⚠️  {doc_type} 문서를 찾지 못했습니다")
                    continue
                
                predictions = results['documents'][doc_type]
                field_results = self.calculate_field_accuracy(
                    predictions, 
                    expected_fields
                )
                
                # 통계 업데이트
                for field, result in field_results.items():
                    key = f"{doc_type}.{field}"
                    total_stats[key]['total'] += 1
                    
                    if result['correct']:
                        total_stats[key]['correct'] += 1
                        print(f"  ✓ {key}")
                    else:
                        print(f"  ✗ {key}")
                        print(f"      예측: {result['predicted']}")
                        print(f"      정답: {result['expected']}")
                        
                        # 에러 케이스 저장
                        error_cases.append({
                            'file': pdf_file,
                            'field': key,
                            'predicted': result['predicted'],
                            'expected': result['expected'],
                        })
        
        return self.generate_report(total_stats, error_cases)
    
    def generate_report(self, 
                       stats: Dict, 
                       error_cases: List[Dict]) -> Dict:
        """
        리포트 생성 및 출력
        
        Args:
            stats: 통계 딕셔너리
            error_cases: 에러 케이스 리스트
            
        Returns:
            리포트 딕셔너리
        """
        print("\n" + "="*80)
        print("📊 정확도 리포트")
        print("="*80)
        
        # 필드별 정확도
        field_accuracies = {}
        
        for field, stat in sorted(stats.items()):
            if stat['total'] > 0:
                acc = stat['correct'] / stat['total'] * 100
                field_accuracies[field] = acc
                print(f"{field:40s}: {acc:6.2f}% ({stat['correct']}/{stat['total']})")
        
        # 전체 정확도
        total_correct = sum(s['correct'] for s in stats.values())
        total_count = sum(s['total'] for s in stats.values())
        
        if total_count > 0:
            overall_acc = total_correct / total_count * 100
        else:
            overall_acc = 0.0
        
        print("="*80)
        print(f"{'전체 정확도':40s}: {overall_acc:6.2f}% ({total_correct}/{total_count})")
        
        # 가장 틀리는 필드 TOP 5
        print("\n" + "="*80)
        print("❌ 가장 많이 틀리는 필드 TOP 5")
        print("="*80)
        
        error_counts = defaultdict(int)
        for error in error_cases:
            error_counts[error['field']] += 1
        
        top_errors = sorted(error_counts.items(), 
                          key=lambda x: x[1], 
                          reverse=True)[:5]
        
        for field, count in top_errors:
            print(f"  {field:40s}: {count}개 틀림")
        
        # 성능 요약
        print("\n" + "="*80)
        print("📈 성능 요약")
        print("="*80)
        
        if overall_acc >= 95:
            print("🎉 훌륭합니다! 프로덕션 준비 완료!")
        elif overall_acc >= 85:
            print("👍 좋은 성능입니다. 조금만 더 개선하면 완벽!")
        elif overall_acc >= 70:
            print("⚠️  개선이 필요합니다. 위 TOP 5 필드를 집중 개선하세요.")
        else:
            print("❌ 많은 개선이 필요합니다. 패턴 점검이 시급합니다.")
        
        # 다음 액션 제안
        print("\n💡 다음 액션:")
        if top_errors:
            field_name = top_errors[0][0]
            print(f"  1. {field_name} 필드 패턴 개선")
            print(f"  2. 틀린 케이스 분석 (아래 에러 케이스 참고)")
            print(f"  3. posco_patterns.py 또는 posco_patterns_v2.py 수정")
            print(f"  4. 다시 테스트")
        
        # 에러 케이스 상세
        if error_cases:
            print("\n" + "="*80)
            print("📝 에러 케이스 상세 (처음 10개)")
            print("="*80)
            
            for i, error in enumerate(error_cases[:10], 1):
                print(f"\n{i}. {error['file']} - {error['field']}")
                print(f"   예측: {error['predicted']}")
                print(f"   정답: {error['expected']}")
        
        return {
            'overall_accuracy': overall_acc,
            'field_accuracies': field_accuracies,
            'total_correct': total_correct,
            'total_count': total_count,
            'error_cases': error_cases,
            'top_errors': top_errors,
        }


def main():
    """
    메인 실행 함수
    """
    # 명령줄에서 실행하는 경우 (고급 사용자용)
    if len(sys.argv) >= 2:
        ground_truth_path = sys.argv[1]
        pdf_dir = sys.argv[2] if len(sys.argv) > 2 else None
    # 파일 상단에 설정한 값 사용 (초보자용)
    else:
        ground_truth_path = GROUND_TRUTH_FILE
        pdf_dir = PDF_FOLDER if PDF_FOLDER else None
        
        # 설정값 확인
        if not ground_truth_path or ground_truth_path == r"D:\CJ\Project Manager\IDARS\Data\test_data.json":
            print("\n" + "="*80)
            print("⚠️  주의: 파일 상단의 GROUND_TRUTH_FILE을 실제 경로로 수정하세요!")
            print("="*80)
            print(f"\n현재 설정: {ground_truth_path}")
            print("\n수정 방법:")
            print("  1. 이 파일(accuracy_checker.py)을 메모장이나 VSCode로 여세요")
            print("  2. 맨 위 '사용자 설정' 부분을 찾으세요")
            print("  3. GROUND_TRUTH_FILE = r\"실제경로\"로 수정하세요")
            print("  4. 저장 후 다시 실행하세요")
            print("\n예시:")
            print('  GROUND_TRUTH_FILE = r"D:\\My Documents\\test_data.json"')
            print("\n또는 명령줄에서:")
            print('  python accuracy_checker.py "정답파일경로" "PDF폴더(선택)"')
            print("\n정답 파일 형식:")
            print(AccuracyChecker.get_sample_ground_truth())
            print("="*80)
            sys.exit(1)
    
    checker = AccuracyChecker(ground_truth_path)
    results = checker.run_test(pdf_dir)
    
    # 결과 저장
    output_path = Path(ground_truth_path).parent / "accuracy_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 리포트 저장: {output_path}")


if __name__ == "__main__":
    main()
