import os
import time
from datetime import datetime
try:
    import win32com.client
except ImportError:
    win32com = None

def wait_for_sap_gui(max_wait=30):
    """SAP GUI가 준비될 때까지 대기"""
    for i in range(max_wait):
        try:
            SapGuiAuto = win32com.client.GetObject("SAPGUI")
            application = SapGuiAuto.GetScriptingEngine
            if application.Children.Count > 0:
                return True
        except:
            pass
        time.sleep(1)
    return False

def get_sap_session():
    """SAP 세션을 안전하게 가져오기"""
    try:
        # SAP GUI 연결 확인
        if not wait_for_sap_gui():
            raise Exception("SAP GUI가 실행되지 않았거나 연결할 수 없습니다.")
        
        SapGuiAuto = win32com.client.GetObject("SAPGUI")
        application = SapGuiAuto.GetScriptingEngine
        
        # 연결 확인
        if application.Children.Count == 0:
            raise Exception("SAP 연결이 없습니다. SAP GUI에서 시스템에 로그인해주세요.")
        
        connection = application.Children(0)
        
        # 세션 확인
        if connection.Children.Count == 0:
            raise Exception("SAP 세션이 없습니다.")
        
        session = connection.Children(0)
        return session, connection
        
    except Exception as e:
        raise Exception(f"SAP GUI 연결 실패: {e}")

def safe_find_by_id(session, control_id, max_retries=3):
    """안전하게 컨트롤을 찾기"""
    for i in range(max_retries):
        try:
            control = session.findById(control_id)
            if control:
                return control
        except Exception as e:
            if i == max_retries - 1:
                raise Exception(f"컨트롤을 찾을 수 없습니다: {control_id}, 오류: {e}")
            time.sleep(1)
    raise Exception(f"컨트롤을 찾을 수 없습니다: {control_id}")

def run_zsdr0580_and_download(start_date, end_date, download_path):
    try:
        print("🔄 SAP GUI 연결 중...")
        session, connection = get_sap_session()
        
        print("🔄 새 세션 생성 중...")
        session.CreateSession()
        new_session = connection.Children(connection.Children.Count - 1)
        
        # 세션이 준비될 때까지 대기
        time.sleep(3)
        
        print("🔄 창 최대화 중...")
        try:
            safe_find_by_id(new_session, "wnd[0]").maximize()
        except Exception as e:
            print(f"⚠️ 창 최대화 실패: {e}")

        print("🔄 ZSDR0580 트랜잭션 실행 중...")
        try:
            safe_find_by_id(new_session, "wnd[0]/tbar[0]/okcd").text = "ZSDR0580"
            safe_find_by_id(new_session, "wnd[0]").sendVKey(0)
        except Exception as e:
            print(f"❌ ZSDR0580 트랜잭션 실행 실패: {e}")
            return

        # 화면 로딩 대기
        time.sleep(2)

        print("🔄 검색 조건 입력 중...")
        try:
            # 시작일 입력 (S_FKDAT-LOW)
            safe_find_by_id(new_session, "wnd[0]/usr/ctxtS_FKDAT-LOW").text = start_date
            time.sleep(0.5)
            
            # 종료일 입력 (S_FKDAT-HIGH)
            safe_find_by_id(new_session, "wnd[0]/usr/ctxtS_FKDAT-HIGH").text = end_date
            time.sleep(0.5)
            
            # 종료일 필드에 포커스 설정 (VBS 참고)
            safe_find_by_id(new_session, "wnd[0]/usr/ctxtS_FKDAT-HIGH").setFocus()
            time.sleep(0.5)
            safe_find_by_id(new_session, "wnd[0]/usr/ctxtS_FKDAT-HIGH").caretPosition = 10
            time.sleep(0.5)
            
            # 실행 버튼 클릭
            safe_find_by_id(new_session, "wnd[0]/tbar[1]/btn[8]").press()
        except Exception as e:
            print(f"❌ 검색 조건 입력 실패: {e}")
            return

        # ALV Grid 로딩 대기
        print("🔄 결과 로딩 중...")
        grid_id = "wnd[0]/usr/cntlGO_CONT/shellcont/shell"
        max_wait = 20
        grid = None
        
        for i in range(max_wait):
            try:
                grid = safe_find_by_id(new_session, grid_id)
                if grid:
                    break
            except:
                time.sleep(1)
                if i == max_wait - 1:
                    print(f"⚠️ ALV Grid 로딩 실패 - 최대 대기 시간 초과")
                    try:
                        safe_find_by_id(new_session, "wnd[0]").close()
                    except:
                        pass
                    return

        if grid is None:
            print("⚠️ ALV Grid를 찾을 수 없습니다.")
            try:
                safe_find_by_id(new_session, "wnd[0]").close()
            except:
                pass
            return

        print("🔄 엑셀 다운로드 준비 중...")
        try:
            # VBS 참고: pressToolbarContextButton과 selectContextMenuItem 사용
            grid.pressToolbarContextButton("&MB_EXPORT")
            time.sleep(1)
            grid.selectContextMenuItem("&XXL")
            time.sleep(1)
            
            # 확인 버튼 클릭
            safe_find_by_id(new_session, "wnd[1]/tbar[0]/btn[0]").press()
        except Exception as e:
            print(f"❌ 엑셀 다운로드 준비 실패: {e}")
            return

        # 파일명 생성 (VBS 참고)
        start_short = start_date[2:4] + start_date[5:7] + start_date[8:10]
        end_short = end_date[2:4] + end_date[5:7] + end_date[8:10]
        file_name = f"Billing List_{start_short}~{end_short}.XLSX"
        full_path = os.path.join(download_path, file_name)

        # 기존 파일 삭제
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                print(f"[기존 파일 삭제] {full_path}")
            except Exception as e:
                print(f"[경고] 기존 파일 삭제 실패: {e}")

        print("🔄 파일 저장 중...")
        try:
            # 저장 경로 입력
            safe_find_by_id(new_session, "wnd[1]/usr/ctxtDY_PATH").text = download_path
            time.sleep(0.5)
            
            # 파일명 입력
            safe_find_by_id(new_session, "wnd[1]/usr/ctxtDY_FILENAME").text = file_name
            time.sleep(0.5)
            
            # 커서 위치 설정 (VBS 참고)
            safe_find_by_id(new_session, "wnd[1]/usr/ctxtDY_FILENAME").caretPosition = len(file_name)
            time.sleep(0.5)
            
            # 저장 버튼 클릭
            safe_find_by_id(new_session, "wnd[1]/tbar[0]/btn[0]").press()
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")
            return

        print(f"✅ 저장 완료: {file_name}")
        time.sleep(2)
        
        # 세션 종료
        try:
            safe_find_by_id(new_session, "wnd[0]").close()
        except:
            pass

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        # 오류 발생 시 세션 정리
        try:
            if 'new_session' in locals():
                safe_find_by_id(new_session, "wnd[0]").close()
        except:
            pass

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='SAP ZSDR0580 Downloader')
    parser.add_argument('--start_date', required=True, help='Start Date (YYYY.MM.DD)')
    parser.add_argument('--end_date', required=True, help='End Date (YYYY.MM.DD)')
    parser.add_argument('--output_dir', required=True, help='Output Directory')

    args = parser.parse_args()

    # Force UTF-8 for stdout/stderr to avoid encoding errors on Windows
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir, exist_ok=True)

    # Check if SAP is available (Mock check for dev environment without SAP)
    try:
        if win32com is None:
            raise Exception("win32com not installed")
        SapGuiAuto = win32com.client.GetObject("SAPGUI")
    except:
        print("[WARN] SAP GUI not found. Running in MOCK mode for testing.")
        # Create a mock file for testing
        start_short = args.start_date[2:4] + args.start_date[5:7] + args.start_date[8:10]
        end_short = args.end_date[2:4] + args.end_date[5:7] + args.end_date[8:10]
        # Use CSV for mock to avoid openpyxl dependency
        file_name = f"Billing List_{start_short}~{end_short}.csv"
        full_path = os.path.join(args.output_dir, file_name)
        
        import pandas as pd
        # Create dummy data
        df = pd.DataFrame({
            'Billing Document': ['90000001', '90000002'],
            'Billing Date': [args.start_date, args.end_date],
            'Amount': [10000, 20000],
            'Customer Name': ['Mock Customer A', 'Mock Customer B']
        })
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"[MOCK] Saved mock file: {full_path}")
        sys.exit(0)

    run_zsdr0580_and_download(args.start_date, args.end_date, args.output_dir) 