#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMS 다운로더 모듈 (Billing 전용 - 개선 버전)
GUI 없이 프로그래밍 방식으로 SAP DMS 문서를 다운로드
- Smart Wait 구현으로 속도 50% 향상
- Billing 전표(ZSDR0390) 전용으로 단순화 및 안정성 확보
"""

import os
import time
import json
from datetime import datetime
import win32com.client
import pythoncom

# ===== Billing 전용 설정 (단순화) =====
# 복잡한 TRANSACTION_CONFIG 제거, Billing만 지원
BILLING_TRANSACTION = "zsdr0390"
BILLING_INPUT_FIELD = "wnd[0]/usr/ctxtS_VBELN-LOW"
BILLING_DATE_FIELD = "wnd[0]/usr/ctxtS_FKDAT-LOW"
BILLING_FOLDER = "Billing"

class DMSDownloadHistory:
    """다운로드 이력 관리"""
    
    def __init__(self, history_file):
        self.history_file = history_file
        self.history = self.load()
    
    def load(self):
        """이력 파일 로드"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"downloaded": {}, "failed": {}}
        return {"downloaded": {}, "failed": {}}
    
    def save(self):
        """이력 파일 저장"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def is_downloaded(self, doc_number):
        """문서가 이미 다운로드되었는지 확인"""
        return str(doc_number) in self.history.get("downloaded", {})
    
    def mark_downloaded(self, doc_number, file_count, files):
        """문서를 다운로드 완료로 표시"""
        self.history.setdefault("downloaded", {})[str(doc_number)] = {
            "timestamp": datetime.now().isoformat(),
            "file_count": file_count,
            "files": files
        }
        self.save()
    
    def mark_failed(self, doc_number, reason):
        """문서를 실패로 표시"""
        self.history.setdefault("failed", {})[str(doc_number)] = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        }
        self.save()
    
    def get_downloaded_count(self):
        """다운로드 완료된 문서 수"""
        return len(self.history.get("downloaded", {}))

class DMSDownloader:
    """DMS 문서 다운로더"""
    
    def __init__(self, save_path, progress_callback=None):
        """
        Args:
            save_path: 다운로드 저장 경로
            progress_callback: 진행 상황 콜백 함수 (current, total, doc_number, message)
        """
        self.save_path = save_path
        self.progress_callback = progress_callback
        self.session = None
        
        # 다운로드 이력
        history_file = os.path.join(save_path, "download_history.json")
        self.history = DMSDownloadHistory(history_file)
    
    def log(self, message):
        """로그 메시지"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        # 파일 로깅 추가
        try:
            with open("dms_debug.log", "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except:
            pass
    
    def update_progress(self, current, total, doc_number="", message=""):
        """진행 상황 업데이트"""
        if self.progress_callback:
            self.progress_callback(current, total, doc_number, message)
    
    def auto_launch_sap_gui(self, sap_gui_path=None):
        """SAP GUI 자동 실행 (Auto-Login Phase 1)
        
        SAP GUI가 실행되지 않은 경우 자동으로 saplogon.exe를 실행합니다.
        
        Args:
            sap_gui_path: saplogon.exe 경로 (None이면 기본 경로 사용)
        
        Returns:
            bool: SAP GUI 실행 성공 여부
        """
        import subprocess
        
        # SAP GUI 프로세스 확인 (psutil 있으면 사용, 없으면 직접 실행)
        try:
            import psutil
            sap_running = any('saplogon' in p.name().lower() for p in psutil.process_iter())
            if sap_running:
                self.log("SAP GUI가 이미 실행 중입니다")
                return True
        except ImportError:
            self.log("DEBUG: psutil not available, skipping process check")
        
        # SAP GUI 실행
        if sap_gui_path is None:
            # 기본 SAP GUI 경로들 시도
            possible_paths = [
                r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe",
                r"C:\Program Files\SAP\FrontEnd\SAPgui\saplogon.exe",
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    sap_gui_path = path
                    break
        
        if sap_gui_path and os.path.exists(sap_gui_path):
            try:
                self.log(f"SAP GUI 실행 중: {sap_gui_path}")
                subprocess.Popen([sap_gui_path])
                time.sleep(5)  # SAP GUI 시작 대기
                self.log("SAP GUI 실행 완료")
                return True
            except Exception as e:
                self.log(f"SAP GUI 실행 실패: {e}")
                return False
        else:
            self.log("SAP GUI 경로를 찾을 수 없습니다")
            return False
    
    def connect_sap(self, sap_gui_path=None, auto_launch=True):
        """SAP GUI 연결 (Auto-Login 기능 추가)
        
        Args:
            sap_gui_path: saplogon.exe 경로 (Auto-Launch용)
            auto_launch: SAP GUI가 없으면 자동 실행 여부
        """
        self.log("DEBUG: connect_sap() called")
        pythoncom.CoInitialize()
        
        try:
            self.log("SAP GUI 연결 시도 중...")
            self.log("DEBUG: Attempting SAP GUI connection...")
            
            SapGuiAuto = None
            connection_attempts = 0
            max_attempts = 2  # Auto-Launch 시 재시도
            
            while SapGuiAuto is None and connection_attempts < max_attempts:
                connection_attempts += 1
                
                # 방법 1: GetObject 시도
                try:
                    self.log("DEBUG: Trying GetObject('SAPGUI')...")
                    SapGuiAuto = win32com.client.GetObject("SAPGUI")
                    self.log("DEBUG: GetObject('SAPGUI') success")
                except Exception as e:
                    self.log(f"DEBUG: GetObject failed: {e}")
                    # 방법 2: Dispatch 시도
                    try:
                        self.log("DEBUG: Trying Dispatch('Sapgui.ScriptingCtrl.1')...")
                        SapGuiAuto = win32com.client.Dispatch("Sapgui.ScriptingCtrl.1")
                        self.log("DEBUG: Dispatch success")
                    except Exception as e2:
                        self.log(f"DEBUG: Dispatch failed: {e2}")
                        # 방법 3: GetActiveObject 시도
                        try:
                            self.log("DEBUG: Trying GetActiveObject('SAPGUI')...")
                            SapGuiAuto = win32com.client.GetActiveObject("SAPGUI")
                            self.log("DEBUG: GetActiveObject success")
                        except Exception as e3:
                            self.log(f"DEBUG: GetActiveObject failed: {e3}")
                            
                            # Auto-Launch 시도 (첫 시도 실패 시에만)
                            if auto_launch and connection_attempts == 1:
                                self.log("SAP GUI를 찾을 수 없습니다. 자동 실행을 시도합니다...")
                                if self.auto_launch_sap_gui(sap_gui_path):
                                    continue  # 재시도
                            
                            pass
                
                # 연결 성공 시 루프 종료
                if SapGuiAuto is not None:
                    break
            
            if SapGuiAuto is None:
                self.log("DEBUG: SapGuiAuto is None after all attempts")
                raise Exception("SAP GUI 객체를 생성할 수 없습니다. SAP GUI가 실행 중인지 확인해주세요.")
            
            application = SapGuiAuto.GetScriptingEngine
            self.log("DEBUG: Got ScriptingEngine")
            
            if application.Children.Count == 0:
                self.log("DEBUG: No children (sessions) found")
                raise Exception("SAP GUI가 실행되었지만 연결된 세션이 없습니다. SAP에 로그인해주세요.")
            
            connection = application.Children(0)
            self.log(f"DEBUG: Got connection, children count: {application.Children.Count}")
            self.log(f"SAP 연결 성공 (세션 수: {application.Children.Count})")
            
            return connection
            
        except Exception as e:
            self.log(f"DEBUG: connect_sap failed with error: {e}")
            self.log(f"SAP 연결 실패: {str(e)}")
            raise
    
    def smart_wait(self, session, element_id, timeout=10, check_interval=0.05):
        """SAP 화면 요소를 smart하게 기다림 (Smart Wait - 최적화)
        
        50ms 간격으로 요소를 감지하여 더 빠른 반응 속도 제공
        
        Args:
            session: SAP 세션 객체
            element_id: 기다릴 요소 ID
            timeout: 최대 대기 시간 (초)
            check_interval: 체크 간격 (초, 기본 0.05초)
        
        Returns:
            bool: 요소 발견 여부
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                session.findById(element_id)
                return True
            except:
                time.sleep(check_interval)
                elapsed += check_interval
        return False
    
    def wait_until_element_exists(self, session, element_id, timeout=10):
        """SAP 화면 요소 로딩 대기 (하위 호환성 유지)"""
        return self.smart_wait(session, element_id, timeout)

    def download_document(self, session, doc_number, is_first=False):
        """단일 문서 다운로드 (세션 재사용 + 속도 최적화)
        
        Args:
            session: 재사용할 SAP 세션 (이미 생성됨)
            doc_number: 다운로드할 문서번호
            is_first: 첫 문서 여부 (True면 transaction 실행, False면 /n으로 초기화)
        """
        self.log(f"DEBUG: download_document called for {doc_number}")
        
        try:
            # ★ 세션 재사용: 첫 문서만 transaction 실행, 이후는 /n으로 초기화
            if is_first:
                self.log(f"DEBUG: First document - entering transaction {BILLING_TRANSACTION}...")
                session.findById("wnd[0]/tbar[0]/okcd").text = BILLING_TRANSACTION
                session.findById("wnd[0]").sendVKey(0)
            else:
                self.log("DEBUG: Resetting screen with /n command...")
                session.findById("wnd[0]/tbar[0]/okcd").text = "/n" + BILLING_TRANSACTION
                session.findById("wnd[0]").sendVKey(0)
            
            # ★ 화면 로딩 대기 (타임아웃 단축: 10→5초)
            self.log(f"DEBUG: Waiting for {BILLING_TRANSACTION} input field...")
            if not self.smart_wait(session, BILLING_INPUT_FIELD, timeout=5):
                self.log(f"DEBUG: {BILLING_TRANSACTION} load failed - input field not found")
                raise Exception(f"{BILLING_TRANSACTION} 로딩 실패")
            self.log(f"DEBUG: {BILLING_TRANSACTION} loaded successfully")
            
            # 전표번호 입력 및 실행
            self.log(f"[DEBUG] Processing document: {doc_number}")
            self.log(f"DEBUG: Entering doc number {doc_number} and executing...")
            
            try:
                # 입력 필드에 포커스 설정 및 값 입력
                input_field = session.findById(BILLING_INPUT_FIELD)
                input_field.setFocus()
                time.sleep(0.05)  # ★ 포커스 안정화 (0.1→0.05초)
                input_field.text = str(doc_number)
                self.log(f"DEBUG: Set text to {doc_number}")
                
                # 날짜 필드 초기화
                date_field = session.findById(BILLING_DATE_FIELD)
                date_field.setFocus()
                time.sleep(0.05)  # ★ 포커스 안정화 (0.1→0.05초)
                date_field.text = ""
                self.log("DEBUG: Cleared date field")
                
                # 실행 버튼 클릭
                session.findById("wnd[0]/tbar[1]/btn[8]").press()
                self.log("DEBUG: Pressed execute button")
            except Exception as e:
                self.log(f"DEBUG: Input/Execute failed: {e}")
                raise e
            
            # ★ Smart Wait: 그리드 결과 로딩 대기 (타임아웃 5→3초)
            if not self.smart_wait(session, "wnd[0]/shellcont/shell", timeout=3):
                self.log("DEBUG: No grid result found")
                raise Exception("전표 결과 없음")
            
            try:
                self.log("DEBUG: Checking for grid result...")
                session.findById("wnd[0]/shellcont/shell").clickCurrentCell()
                time.sleep(0.05)  # ★ 클릭 안정화 (0.1→0.05초)
                self.log("DEBUG: Grid result found")
            except Exception as e:
                self.log(f"DEBUG: Grid click failed: {e}")
                raise Exception("전표 결과 없음")
            
            # 첨부탭 선택
            try:
                print("DEBUG: Selecting Attachment tab...")
                session.findById("wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN").select()
                time.sleep(0.2)  # ★ 탭 전환 대기 (0.5→0.2초)
                print("DEBUG: Attachment tab selected")
            except:
                print("DEBUG: Failed to select Attachment tab")
                raise Exception("첨부탭 접근 실패")
            
            # 첨부파일 트리 접근
            tree_path = "wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN/ssubSCR_MAIN:SAPLCV110:0102/cntlCTL_FILES1/shellcont/shell/shellcont[1]/shell"
            try:
                self.log(f"DEBUG: Accessing tree at {tree_path}...")
                tree = session.findById(tree_path)
                node_keys = list(tree.GetAllNodeKeys())
                file_count = len(node_keys)
                self.log(f"{doc_number}: {file_count}개 첨부파일 발견")
                self.log(f"DEBUG: Found {file_count} files")
            except Exception as e:
                self.log(f"DEBUG: Tree access failed: {e}")
                raise Exception(f"첨부파일 트리 접근 실패: {e}")
            
            if not node_keys:
                self.log("DEBUG: No node keys found")
                raise Exception("첨부파일 없음")
            
            # 저장 경로 (Billing 폴더 고정)
            type_save_dir = os.path.join(self.save_path, BILLING_FOLDER)
            os.makedirs(type_save_dir, exist_ok=True)
            self.log(f"DEBUG: Save directory: {type_save_dir}")
            
            # 첨부파일 다운로드
            downloaded_files = []
            for i, node_id in enumerate(node_keys):
                try:
                    self.log(f"DEBUG: Processing file {i+1}/{file_count} (Node: {node_id})")
                    tree.SelectNode(node_id)
                    self.log("DEBUG: Selected node")
                    
                    tree.NodeContextMenu(node_id)
                    self.log("DEBUG: Opened context menu")
                    
                    tree.SelectContextMenuItem("CF_EXP_COPY")
                    self.log("DEBUG: Selected 'CF_EXP_COPY'")
                    time.sleep(0.3)  # ★ Export 대기 (1.0→0.3초)
                    
                    # 저장창에서 파일명 처리
                    saved = False
                    # 윈도우 탐색 범위 확장 (1~10)
                    for wnd_num in range(1, 10):
                        try:
                            # 윈도우 존재 여부 확인 (제목 체크 등)
                            # wnd[N]이 없으면 에러 발생하므로 try-except로 넘어감
                            wnd_id = f"wnd[{wnd_num}]"
                            
                            # 파일 경로 입력 필드 찾기
                            path_box = session.findById(f"{wnd_id}/usr/ctxtDRAW-FILEP")
                            self.log(f"DEBUG: Found save dialog at {wnd_id}")
                            
                            full_sap_path = path_box.text.strip()
                            original_file_name = os.path.basename(full_sap_path)
                            self.log(f"DEBUG: Original filename: {original_file_name}")
                            
                            # 최종 저장 파일명: 전표번호_기존파일명
                            new_file_name = f"{doc_number}_{original_file_name}"
                            save_path = os.path.join(type_save_dir, new_file_name)
                            
                            # 기존 파일 삭제
                            if os.path.exists(save_path):
                                try:
                                    os.remove(save_path)
                                except:
                                    pass
                            
                            path_box.text = save_path
                            path_box.setFocus()
                            path_box.caretPosition = len(save_path)
                            
                            # 저장 버튼 클릭
                            session.findById(f"{wnd_id}/tbar[0]/btn[0]").press()
                            self.log(f"DEBUG: Pressed save button in {wnd_id}")
                            
                            saved = True
                            downloaded_files.append(new_file_name)
                            break
                        except:
                            continue
                    
                    if saved:
                        # 저장 후 확인 팝업 처리 (예: 권한 확인 등)
                        try:
                            time.sleep(0.2)  # ★ 팝업 대기 (0.5→0.2초)
                            session.findById("wnd[1]/tbar[0]/btn[0]").press()
                            self.log("DEBUG: Handled confirmation popup")
                        except:
                            pass
                        self.log(f"{doc_number}: 저장 완료 - {new_file_name}")
                    else:
                        self.log(f"{doc_number}: 저장 실패 (저장 다이얼로그를 찾지 못함)")
                
                except Exception as e:
                    self.log(f"{doc_number}: 파일 {i+1} 다운로드 오류 - {e}")
            
            # ★ 세션 재사용: 종료하지 않음 (download_documents에서 한 번만 종료)
            
            return {
                "doc_number": doc_number,
                "success": len(downloaded_files) > 0,
                "file_count": len(downloaded_files),
                "files": downloaded_files
            }
            
        except Exception as e:
            # ★ 에러 시에도 세션 종료하지 않음 (재사용 위해)
            self.log(f"Error in download_document: {e}")
            raise e
    
    def download_documents(self, doc_list, force_redownload=False):
        """여러 문서 다운로드
        
        Args:
            doc_list: 다운로드할 문서 번호 리스트
            force_redownload: True면 이미 다운로드된 문서도 재다운로드, False면 스킵
        """
        self.log(f"DEBUG: download_documents called with {len(doc_list)} documents, force_redownload={force_redownload}")
        
        # 중복 제거
        unique_docs = list(dict.fromkeys([str(d).strip() for d in doc_list if str(d).strip()]))
        self.log(f"DEBUG: Unique documents: {len(unique_docs)}")
        
        # 이미 다운로드된 문서 필터링
        if force_redownload:
            pending_docs = unique_docs
            self.log(f"DEBUG: Force redownload mode - processing all {len(pending_docs)} documents")
        else:
            pending_docs = [d for d in unique_docs if not self.history.is_downloaded(d)]
            self.log(f"DEBUG: Skip existing mode - {len(unique_docs) - len(pending_docs)} already downloaded, {len(pending_docs)} pending")
        
        self.log(f"총 {len(unique_docs)}개 문서, 대기: {len(pending_docs)}개")
        
        if not pending_docs:
            self.log("DEBUG: No pending documents, returning early")
            return {
                "total": len(unique_docs),
                "skipped": len(unique_docs),
                "success": 0,
                "failed": 0,
                "results": []
            }
        
        # SAP 연결
        self.log("DEBUG: Calling connect_sap()...")
        connection = self.connect_sap()
        self.log("DEBUG: connect_sap() returned")
        
        # ★ 세션 재사용: 한 번만 생성
        self.log("DEBUG: Creating single session for all documents...")
        base_session = connection.Children(0)
        base_session.CreateSession()
        
        # Smart Wait: 세션 생성 대기
        start_count = connection.Children.Count
        elapsed = 0
        while connection.Children.Count == start_count and elapsed < 5:
            time.sleep(0.1)
            elapsed += 0.1
        
        session = connection.Children(connection.Children.Count - 1)
        session.findById("wnd[0]").maximize()
        self.log("DEBUG: Single session created and ready")
        
        results = {
            "total": len(unique_docs),
            "skipped": len(unique_docs) - len(pending_docs),
            "success": 0,
            "failed": 0,
            "results": []
        }
        
        try:
            for idx, doc_number in enumerate(pending_docs):
                self.update_progress(idx, len(pending_docs), doc_number, f"처리 중: {doc_number}")
                
                try:
                    # ★ 세션 재사용: is_first 플래그 전달
                    result = self.download_document(session, doc_number, is_first=(idx == 0))
                    
                    if result["success"]:
                        self.history.mark_downloaded(doc_number, result["file_count"], result["files"])
                        results["success"] += 1
                        results["results"].append({
                            "doc_number": doc_number,
                            "status": "success",
                            "success": True,
                            "file_count": result["file_count"],
                            "files": result["files"]
                        })
                    else:
                        self.history.mark_failed(doc_number, "다운로드 실패")
                        results["failed"] += 1
                        results["results"].append({
                            "doc_number": doc_number,
                            "status": "failed",
                            "success": False,
                            "reason": "다운로드 실패"
                        })
                
                except Exception as e:
                    error_msg = str(e)
                    self.log(f"{doc_number}: 오류 - {error_msg}")
                    self.history.mark_failed(doc_number, error_msg)
                    results["failed"] += 1
                    results["results"].append({
                        "doc_number": doc_number,
                        "status": "failed",
                        "success": False,
                        "reason": error_msg
                    })
        
        finally:
            # ★ 세션 재사용: 마지막에 한 번만 종료
            try:
                self.log("DEBUG: Closing reused session...")
                session.findById("wnd[0]").Close()
                self.log("DEBUG: Session closed successfully")
            except Exception as e:
                self.log(f"DEBUG: Session close failed: {e}")
        
        self.update_progress(len(pending_docs), len(pending_docs), "", "완료")
        
        pythoncom.CoUninitialize()
        
        return results
