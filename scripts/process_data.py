#!/usr/bin/env python3
"""
전표 데이터 처리 스크립트

사용법:
    python scripts/process_data.py <파일명> [옵션]

예시:
    python scripts/process_data.py EXPORT.csv
    python scripts/process_data.py EXPORT.csv --summary
    python scripts/process_data.py EXPORT.csv --filter "금액 > 1000000"
    python scripts/process_data.py EXPORT.csv --export result.xlsx
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime


class InvoiceDataProcessor:
    """전표 데이터 처리 클래스"""

    def __init__(self, file_path):
        self.processed_dir = Path("data/processed")
        self.output_dir = Path("data/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 파일 로드
        file_path = Path(file_path)
        if not file_path.exists():
            file_path = self.processed_dir / file_path.name

        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        print(f"📂 파일 로드 중: {file_path.name}")
        self.df = pd.read_csv(file_path, encoding='utf-8-sig')
        self.original_rows = len(self.df)
        print(f"✅ {self.original_rows:,}행 로드 완료\n")

    def show_info(self):
        """데이터 기본 정보 표시"""
        print("=" * 80)
        print("📊 데이터 정보")
        print("=" * 80)
        print(f"행 수: {len(self.df):,}")
        print(f"열 수: {len(self.df.columns)}")
        print(f"\n컬럼 목록:")

        for i, col in enumerate(self.df.columns, 1):
            dtype = self.df[col].dtype
            null_count = self.df[col].isnull().sum()
            null_pct = (null_count / len(self.df)) * 100

            print(f"  {i:2d}. {col:30s} | {str(dtype):10s} | 결측: {null_count:5d} ({null_pct:5.1f}%)")

        print("\n" + "=" * 80)

    def show_summary(self):
        """데이터 요약 통계"""
        print("\n📈 요약 통계")
        print("=" * 80)

        # 숫자형 컬럼 통계
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            print("\n[숫자형 컬럼]")
            summary = self.df[numeric_cols].describe()
            print(summary.to_string())

        # 날짜형 컬럼 찾기 (컬럼명에 '일자', 'date' 포함)
        date_like_cols = [col for col in self.df.columns
                          if '일자' in col or 'date' in col.lower() or '날짜' in col]

        if date_like_cols:
            print(f"\n[날짜형 컬럼]")
            for col in date_like_cols:
                print(f"  {col}:")
                print(f"    최소: {self.df[col].min()}")
                print(f"    최대: {self.df[col].max()}")

        # 범주형 컬럼 (고유값이 적은 컬럼)
        print(f"\n[범주형 컬럼 (고유값 20개 이하)]")
        for col in self.df.columns:
            unique_count = self.df[col].nunique()
            if unique_count <= 20 and unique_count > 1:
                print(f"  {col}: {unique_count}개")
                value_counts = self.df[col].value_counts()
                for val, count in value_counts.head(10).items():
                    print(f"    - {val}: {count:,}개")

        print("=" * 80)

    def filter_data(self, condition):
        """데이터 필터링"""
        print(f"\n🔍 필터 적용: {condition}")

        try:
            # 간단한 조건 파싱 (예: "금액 > 1000000")
            # 실제로는 더 복잡한 파싱이 필요할 수 있음
            filtered_df = self.df.query(condition)
            print(f"✅ {len(filtered_df):,}행이 조건을 만족합니다 (전체의 {len(filtered_df)/len(self.df)*100:.1f}%)")

            self.df = filtered_df
            return True
        except Exception as e:
            print(f"❌ 필터 적용 실패: {e}")
            print("💡 팁: 컬럼명에 공백이 있으면 백틱(`)으로 감싸주세요")
            print("   예: `전표 금액` > 1000000")
            return False

    def group_by(self, columns, agg_func='sum'):
        """그룹화 및 집계"""
        if isinstance(columns, str):
            columns = [columns]

        print(f"\n📊 그룹화: {', '.join(columns)}")

        try:
            # 숫자형 컬럼만 집계
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()

            if not numeric_cols:
                print("❌ 집계할 숫자형 컬럼이 없습니다")
                return None

            if agg_func == 'sum':
                result = self.df.groupby(columns)[numeric_cols].sum()
            elif agg_func == 'mean':
                result = self.df.groupby(columns)[numeric_cols].mean()
            elif agg_func == 'count':
                result = self.df.groupby(columns)[numeric_cols].count()
            else:
                result = self.df.groupby(columns)[numeric_cols].agg(agg_func)

            print(f"✅ 그룹 수: {len(result)}")
            print("\n결과 미리보기:")
            print(result.head(10).to_string())

            return result

        except Exception as e:
            print(f"❌ 그룹화 실패: {e}")
            return None

    def export(self, output_name, format='csv'):
        """결과 내보내기"""
        output_path = self.output_dir / output_name

        print(f"\n💾 내보내기 중: {output_path}")

        try:
            if format == 'csv' or output_name.endswith('.csv'):
                self.df.to_csv(output_path, index=False, encoding='utf-8-sig')
            elif format == 'excel' or output_name.endswith(('.xlsx', '.xls')):
                self.df.to_excel(output_path, index=False, engine='openpyxl')
            else:
                print(f"❌ 지원하지 않는 형식: {format}")
                return False

            file_size = output_path.stat().st_size
            print(f"✅ 저장 완료! ({file_size:,} bytes)")
            print(f"   위치: {output_path}")

            return True

        except Exception as e:
            print(f"❌ 내보내기 실패: {e}")
            return False

    def preview(self, n=10):
        """데이터 미리보기"""
        print(f"\n👀 데이터 미리보기 (처음 {n}행)")
        print("=" * 80)
        print(self.df.head(n).to_string())
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='전표 데이터 처리 도구')
    parser.add_argument('file', help='처리할 CSV 파일')
    parser.add_argument('--info', action='store_true', help='데이터 정보 표시')
    parser.add_argument('--summary', action='store_true', help='요약 통계 표시')
    parser.add_argument('--preview', type=int, default=10, help='미리보기 행 수 (기본: 10)')
    parser.add_argument('--filter', type=str, help='필터 조건 (예: "금액 > 1000000")')
    parser.add_argument('--groupby', type=str, help='그룹화 컬럼 (쉼표로 구분)')
    parser.add_argument('--agg', type=str, default='sum', help='집계 함수 (sum, mean, count)')
    parser.add_argument('--export', type=str, help='결과를 파일로 내보내기')

    args = parser.parse_args()

    try:
        # 데이터 로드
        processor = InvoiceDataProcessor(args.file)

        # 기본 정보
        if args.info or (not any([args.summary, args.filter, args.groupby, args.export])):
            processor.show_info()

        # 미리보기
        if not args.summary:
            processor.preview(args.preview)

        # 요약 통계
        if args.summary:
            processor.show_summary()

        # 필터링
        if args.filter:
            processor.filter_data(args.filter)
            processor.preview(args.preview)

        # 그룹화
        if args.groupby:
            columns = [col.strip() for col in args.groupby.split(',')]
            result = processor.group_by(columns, args.agg)
            if result is not None and args.export:
                # 그룹화 결과를 DataFrame으로 변환
                processor.df = result.reset_index()

        # 내보내기
        if args.export:
            processor.export(args.export)

        print("\n✅ 처리 완료!")

    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
