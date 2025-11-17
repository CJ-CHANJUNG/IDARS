#!/usr/bin/env python3
"""
엑셀 파일을 CSV로 변환하는 스크립트

사용법:
    python scripts/convert_to_csv.py <파일명>

예시:
    python scripts/convert_to_csv.py EXPORT.xlsx
    python scripts/convert_to_csv.py data/raw/EXPORT.xlsx

참고:
    - 보안 암호화된 파일은 먼저 엑셀에서 열어 CSV로 저장하세요
    - CSV 파일도 이 스크립트로 처리 가능합니다
"""

import sys
import os
import shutil
from pathlib import Path
import pandas as pd
from datetime import datetime


class DataConverter:
    def __init__(self):
        self.raw_dir = Path("data/raw")
        self.processed_dir = Path("data/processed")

        # 디렉토리 생성
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def convert_file(self, file_path):
        """파일을 CSV로 변환하고 processed 폴더로 이동"""
        file_path = Path(file_path)

        # 파일 존재 확인
        if not file_path.exists():
            # raw 폴더에서 찾기
            file_path = self.raw_dir / file_path.name
            if not file_path.exists():
                print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
                return False

        print(f"📁 파일 처리 중: {file_path.name}")

        try:
            # 파일 확장자에 따라 처리
            if file_path.suffix.lower() == '.csv':
                print("ℹ️  이미 CSV 파일입니다. 검증 후 이동합니다.")
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                print("🔄 엑셀 파일을 CSV로 변환 중...")
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                except Exception as e:
                    print(f"⚠️  엑셀 파일을 직접 읽을 수 없습니다: {e}")
                    print("💡 해결 방법:")
                    print("   1. 엑셀에서 파일을 여세요")
                    print("   2. '다른 이름으로 저장' → CSV 형식 선택")
                    print(f"   3. data/raw/{file_path.stem}.csv로 저장")
                    print(f"   4. 이 스크립트를 다시 실행: python scripts/convert_to_csv.py {file_path.stem}.csv")
                    return False
            else:
                print(f"❌ 지원하지 않는 파일 형식: {file_path.suffix}")
                return False

            # 데이터 정보 출력
            print(f"\n✅ 데이터 로드 완료!")
            print(f"   행 수: {len(df):,}")
            print(f"   열 수: {len(df.columns)}")
            print(f"\n📊 컬럼 목록:")
            for i, col in enumerate(df.columns, 1):
                print(f"   {i}. {col}")

            # CSV로 저장
            output_name = file_path.stem + '.csv'
            output_path = self.processed_dir / output_name

            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 저장 완료: {output_path}")

            # 미리보기
            print(f"\n👀 데이터 미리보기 (처음 5행):")
            print(df.head().to_string())

            return True

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_files(self):
        """raw 폴더의 파일 목록 표시"""
        files = list(self.raw_dir.glob("*"))
        excel_files = [f for f in files if f.suffix.lower() in ['.xlsx', '.xls', '.csv']]

        if not excel_files:
            print(f"📂 {self.raw_dir} 폴더에 파일이 없습니다.")
            print(f"\n💡 엑셀 파일을 {self.raw_dir} 폴더에 넣어주세요.")
        else:
            print(f"\n📂 발견된 파일 ({len(excel_files)}개):")
            for i, f in enumerate(excel_files, 1):
                size = f.stat().st_size
                size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                print(f"   {i}. {f.name} ({size_str})")


def main():
    converter = DataConverter()

    # 인자가 없으면 파일 목록 표시
    if len(sys.argv) < 2:
        print("=" * 60)
        print("📋 엑셀 → CSV 변환 도구")
        print("=" * 60)
        converter.list_files()
        print("\n사용법:")
        print("   python scripts/convert_to_csv.py <파일명>")
        print("\n예시:")
        print("   python scripts/convert_to_csv.py EXPORT.xlsx")
        print("   python scripts/convert_to_csv.py EXPORT.csv")
        return

    # 파일 변환
    file_path = sys.argv[1]
    success = converter.convert_file(file_path)

    if success:
        print("\n" + "=" * 60)
        print("✅ 변환 완료!")
        print("=" * 60)
        print(f"다음 단계:")
        print(f"   python scripts/process_data.py {Path(file_path).stem}.csv")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
