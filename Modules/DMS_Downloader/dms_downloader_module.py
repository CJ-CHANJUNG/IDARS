#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMS 다운로더 모듈
GUI 없이 프로그래밍 방식으로 SAP DMS 문서를 다운로드
다운로드 이력 추적 기능 포함
"""

import os
import time
import json
from datetime import datetime
import win32com.client
import pythoncom

# Transaction 설정
TRANSACTION_CONFIG = {
    "Billing": {
        "name": "매출전표",
        "transaction": "zsdr0390",
        "input_field": "wnd[0]/usr/ctxtS_VBELN-LOW",
        "date_field": "wnd[0]/usr/ctxtS_FKDAT-LOW",
        "folder": "Billing",
        "length": 8,
    },
    "LIV": {
        "name": "매입전표",
        "transaction": "zmmr0820",
        "input_field": "wnd[0]/usr/txtS_BELNR-LOW",
        "date_field": "wnd[0]/usr/ctxtS_BUDAT-LOW",
        "folder": "LIV",
        "length": 10,
    }
}

def detect_transaction_type(number):
    """전표번호 길이로 Transaction 타입 자동 감지"""
    clean_number = str(number).strip()
    
    if len(clean_number) == 8:
        return "Billing"
    elif len(clean_number) == 10:
        return "LIV"
    else:
        return "UNKNOWN"

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
    
    def connect_sap(self):
        """SAP GUI 연결 (Billing Downloader 로직 적용)"""
        self.log("DEBUG: connect_sap() called")
        pythoncom.CoInitialize()
        
        try:
            self.log("SAP GUI 연결 시도 중...")
            self.log("DEBUG: Attempting SAP GUI connection...")
            
            SapGuiAuto = None
            
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
                        pass
            
            if SapGuiAuto is None:
                self.log("DEBUG: SapGuiAuto is None")
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

            raise
    
    def wait_until_element_exists(self, session, element_id, timeout=10):
        """SAP 화면 요소 로딩 대기"""
        for _ in range(timeout * 2):
            try:
                session.findById(element_id)
                return True
            except:
                time.sleep(0.5)
        return False

    def download_document(self, connection, doc_number):
        """단일 문서 다운로드 (Billing Downloader 로직 적용)"""
        self.log(f"DEBUG: download_document called for {doc_number}")
        
        try:
            # 새 세션 생성
            self.log("DEBUG: Creating new session...")
            base_session = connection.Children(0)
            base_session.CreateSession()
            time.sleep(1)
            session = connection.Children(connection.Children.Count - 1)
            self.log("DEBUG: New session created")
            
            session.findById("wnd[0]").maximize()
            self.log("DEBUG: Entering transaction ZSDR0390...")
            session.findById("wnd[0]/tbar[0]/okcd").text = "zsdr0390"
            session.findById("wnd[0]").sendVKey(0)
            
            # 화면 로딩 대기
            self.log("DEBUG: Waiting for ZSDR0390 input field...")
            if not self.wait_until_element_exists(session, "wnd[0]/usr/ctxtS_VBELN-LOW"):
                self.log("DEBUG: ZSDR0390 load failed - input field not found")
                raise Exception("ZSDR0390 로딩 실패")
            self.log("DEBUG: ZSDR0390 loaded successfully")
            
            # 안정성을 위한 대기
            time.sleep(1.0)
            
            # 전표번호 입력 및 실행
            self.log(f"[DEBUG] Processing document: {doc_number}")
            self.log(f"DEBUG: Entering doc number {doc_number} and executing...")
            
            try:
                # 입력 필드에 포커스 설정 및 값 입력
                input_field = session.findById("wnd[0]/usr/ctxtS_VBELN-LOW")
                input_field.setFocus()
                time.sleep(0.5)
                input_field.text = str(doc_number)
                self.log(f"DEBUG: Set text to {doc_number}")
                
                # 날짜 필드 초기화
                date_field = session.findById("wnd[0]/usr/ctxtS_FKDAT-LOW")
                date_field.setFocus()
                time.sleep(0.2)
                date_field.text = ""
                self.log("DEBUG: Cleared date field")
                
                # 실행 버튼 클릭
                session.findById("wnd[0]/tbar[1]/btn[8]").press()
                self.log("DEBUG: Pressed execute button")
            except Exception as e:
                self.log(f"DEBUG: Input/Execute failed: {e}")
                raise e
            
            try:
                self.log("DEBUG: Checking for grid result...")
                session.findById("wnd[0]/shellcont/shell").clickCurrentCell()
                time.sleep(0.5)
                self.log("DEBUG: Grid result found")
            except:
                self.log("DEBUG: No grid result found")
                raise Exception("전표 결과 없음")
            
            # 첨부탭 선택
            try:
                print("DEBUG: Selecting Attachment tab...")
                session.findById("wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN").select()
                time.sleep(0.5)
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
            type_save_dir = os.path.join(self.save_path, "Billing")
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
                    time.sleep(1.0)
                    
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
                            time.sleep(0.5)
                            session.findById("wnd[1]/tbar[0]/btn[0]").press()
                            self.log("DEBUG: Handled confirmation popup")
                        except:
                            pass
                        self.log(f"{doc_number}: 저장 완료 - {new_file_name}")
                    else:
                        self.log(f"{doc_number}: 저장 실패 (저장 다이얼로그를 찾지 못함)")
                
                except Exception as e:
                    self.log(f"{doc_number}: 파일 {i+1} 다운로드 오류 - {e}")
            
            # 세션 종료
            try:
                session.findById("wnd[0]").Close()
                self.log("DEBUG: Session closed")
            except:
                pass
            
            return {
                "doc_number": doc_number,
                "success": len(downloaded_files) > 0,
                "file_count": len(downloaded_files),
                "files": downloaded_files
            }
            
        except Exception as e:
            # 세션 종료 시도
            try:
                session.findById("wnd[0]").Close()
            except:
                pass
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
        
        results = {
            "total": len(unique_docs),
            "skipped": len(unique_docs) - len(pending_docs),
            "success": 0,
            "failed": 0,
            "results": []
        }
        
        for idx, doc_number in enumerate(pending_docs):
            self.update_progress(idx, len(pending_docs), doc_number, f"처리 중: {doc_number}")
            
            try:
                result = self.download_document(connection, doc_number)
                
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
        
        self.update_progress(len(pending_docs), len(pending_docs), "", "완료")
        
        pythoncom.CoUninitialize()
        
        return results
