#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D조건 도착 증빙 다운로더 모듈
SAP T-code ZTDR0210을 사용하여 D조건 전표의 도착 증빙을 다운로드
- 이메일, 이미지, PDF 등 다양한 형식의 증빙 지원
- VBS 스크립트 기반 SAP GUI 자동화
"""

import os
import time
import json
from datetime import datetime
import win32com.client
import pythoncom

# ===== D조건 전용 설정 =====
DTERM_TRANSACTION = "ztdr0210"
DTERM_INPUT_FIELD = "wnd[0]/usr/ctxtS_VBELN-LOW"
DTERM_DATE_FIELD = "wnd[0]/usr/ctxtS_BUDAT-LOW"

class DtermDownloadHistory:
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

class DtermDownloader:
    """D조건 증빙 다운로더"""

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
        history_file = os.path.join(save_path, "dterm_download_history.json")
        self.history = DtermDownloadHistory(history_file)

    def log(self, message):
        """로그 메시지"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)

        # 파일 로깅
        try:
            with open("dterm_debug.log", "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except:
            pass

    def update_progress(self, current, total, doc_number=None, message=""):
        """진행 상황 업데이트"""
        if self.progress_callback:
            self.progress_callback(current, total, doc_number, message)

    def connect_sap(self):
        """SAP GUI 연결"""
        self.log("SAP GUI 연결 시도 중...")
        pythoncom.CoInitialize()

        try:
            SapGuiAuto = win32com.client.GetObject("SAPGUI")
            application = SapGuiAuto.GetScriptingEngine

            if application.Children.Count == 0:
                raise Exception("SAP GUI가 실행되었지만 연결된 세션이 없습니다. SAP에 로그인해주세요.")

            connection = application.Children(0)
            self.log(f"SAP 연결 성공")
            return connection

        except Exception as e:
            self.log(f"SAP 연결 실패: {str(e)}")
            raise

    def download_documents(self, doc_numbers, force_redownload=False):
        """
        문서 리스트 다운로드

        Args:
            doc_numbers: 다운로드할 전표번호 리스트
            force_redownload: 이미 다운로드된 문서도 재다운로드 여부

        Returns:
            {"total": int, "success": int, "failed": int, "skipped": int, "results": []}
        """
        self.log(f"=== D조건 증빙 다운로드 시작 ===")
        self.log(f"Total documents: {len(doc_numbers)}")
        self.log(f"Force redownload: {force_redownload}")
        self.log(f"Save path: {self.save_path}")

        # 저장 디렉토리 확인
        os.makedirs(self.save_path, exist_ok=True)

        # 중복 제거 및 필터링
        unique_docs = list(dict.fromkeys([str(d).strip() for d in doc_numbers if str(d).strip()]))
        self.log(f"Unique documents: {len(unique_docs)}")

        # 이미 다운로드된 문서 필터링
        if force_redownload:
            pending_docs = unique_docs
            self.log(f"Force redownload mode - processing all {len(pending_docs)} documents")
        else:
            pending_docs = [d for d in unique_docs if not self.history.is_downloaded(d)]
            skipped = len(unique_docs) - len(pending_docs)
            self.log(f"Skip existing mode - {skipped} already downloaded, {len(pending_docs)} pending")

        if not pending_docs:
            self.log("No pending documents to download")
            return {
                "total": len(unique_docs),
                "skipped": len(unique_docs),
                "success": 0,
                "failed": 0,
                "results": []
            }

        # SAP 연결
        try:
            connection = self.connect_sap()
        except Exception as e:
            error_msg = f"SAP 연결 실패: {str(e)}"
            self.log(f"ERROR: {error_msg}")
            return {
                "total": len(unique_docs),
                "success": 0,
                "failed": len(pending_docs),
                "skipped": len(unique_docs) - len(pending_docs),
                "error": error_msg,
                "results": []
            }

        # ★ 세션 생성 및 최대화 (DMS 패턴 적용)
        self.log("Creating new session for D-term download...")
        base_session = connection.Children(0)
        base_session.CreateSession()

        # 세션 생성 대기
        start_count = connection.Children.Count
        elapsed = 0
        while connection.Children.Count == start_count and elapsed < 5:
            time.sleep(0.1)
            elapsed += 0.1

        self.session = connection.Children(connection.Children.Count - 1)
        self.session.findById("wnd[0]").maximize()
        self.log("Session created and maximized")

        results = {
            "total": len(unique_docs),
            "skipped": len(unique_docs) - len(pending_docs),
            "success": 0,
            "failed": 0,
            "results": []
        }

        try:
            for idx, doc_number in enumerate(pending_docs):
                self.log(f"[{idx+1}/{len(pending_docs)}] {doc_number}: Starting download...")
                self.update_progress(idx + 1, len(pending_docs), doc_number, "Downloading...")

                try:
                    # ★ 세션 재사용: is_first 플래그 전달
                    file_count, files = self.download_single_document(doc_number, is_first=(idx == 0))

                    if file_count > 0:
                        self.log(f"[{idx+1}/{len(pending_docs)}] {doc_number}: SUCCESS ({file_count} files)")
                        self.history.mark_downloaded(doc_number, file_count, files)
                        results["success"] += 1
                        results["results"].append({
                            "doc_number": doc_number,
                            "status": "success",
                            "success": True,
                            "file_count": file_count,
                            "files": files
                        })
                    else:
                        self.log(f"[{idx+1}/{len(pending_docs)}] {doc_number}: No files downloaded")
                        self.history.mark_failed(doc_number, "no_files")
                        results["failed"] += 1
                        results["results"].append({
                            "doc_number": doc_number,
                            "status": "failed",
                            "success": False,
                            "reason": "no_files"
                        })

                except Exception as e:
                    error_msg = str(e)
                    self.log(f"[{idx+1}/{len(pending_docs)}] {doc_number}: FAILED - {error_msg}")
                    self.history.mark_failed(doc_number, error_msg)
                    results["failed"] += 1
                    results["results"].append({
                        "doc_number": doc_number,
                        "status": "failed",
                        "success": False,
                        "reason": error_msg
                    })

        finally:
            # ★ 세션 정리 (DMS 패턴)
            try:
                self.log("Closing D-term session...")
                self.session.findById("wnd[0]").Close()
                self.log("Session closed successfully")
            except Exception as e:
                self.log(f"Session close failed: {e}")

            pythoncom.CoUninitialize()

        self.log(f"=== D조건 증빙 다운로드 완료 ===")
        self.log(f"Success: {results['success']}, Failed: {results['failed']}, Skipped: {results['skipped']}")

        return results

    def download_single_document(self, billing_doc, is_first=False):
        """
        단일 문서 다운로드 (Python win32com 사용)

        Args:
            billing_doc: 전표번호
            is_first: 첫 문서 여부 (True면 transaction 실행, False면 /n으로 초기화)

        Returns:
            (file_count, [files]) - 다운로드된 파일 수와 파일 리스트
        """
        try:
            # ★ 세션 재사용: 첫 문서만 transaction 실행, 이후는 /n으로 초기화
            if is_first:
                self.log(f"First document - Executing T-code ZTDR0210 for {billing_doc}...")
                self.session.findById("wnd[0]/tbar[0]/okcd").text = DTERM_TRANSACTION
                self.session.findById("wnd[0]").sendVKey(0)
            else:
                self.log(f"Resetting screen for {billing_doc}...")
                self.session.findById("wnd[0]/tbar[0]/okcd").text = "/n" + DTERM_TRANSACTION
                self.session.findById("wnd[0]").sendVKey(0)

            time.sleep(1.0)  # 화면 로딩 대기

            # Date 필드 클리어 (중요!)
            try:
                self.session.findById(DTERM_DATE_FIELD).text = ""
            except:
                pass  # 필드가 없을 수 있음

            # Billing Document 입력
            self.session.findById(DTERM_INPUT_FIELD).text = billing_doc
            self.session.findById(DTERM_INPUT_FIELD).SetFocus()
            time.sleep(0.1)

            # F8 실행 버튼 클릭 (중요!)
            self.log(f"Pressing F8 (Execute) button...")
            self.session.findById("wnd[0]/tbar[1]/btn[8]").press()

            # 결과 로딩 대기
            self.log(f"Waiting for results to load...")
            time.sleep(3)

            # 현재 화면 정보 출력
            try:
                window_title = self.session.findById("wnd[0]").text
                self.log(f"Current window title: {window_title}")
            except:
                pass

            # DMS 전구 버튼 클릭 (증빙 화면 진입)
            self.log(f"Clicking DMS status column to access evidence...")
            try:
                # DMS_STATUS 컬럼 선택 후 클릭 (전구 버튼)
                grid = self.session.findById("wnd[0]/shellcont/shell")
                grid.currentCellColumn = "DMS_STATUS"
                grid.clickCurrentCell()
                time.sleep(2)
                self.log(f"✓ DMS status cell clicked")
            except Exception as e:
                self.log(f"ERROR: Could not click DMS status: {str(e)[:100]}")
                return 0, []

            # 다운로드 전 파일 목록
            before_files = set()
            if os.path.exists(self.save_path):
                before_files = set(os.listdir(self.save_path))

            # 트리 컨트롤 접근 (레코딩된 경로 사용)
            tree_path = "wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN/ssubSCR_MAIN:SAPLCV110:0102/cntlCTL_FILES1/shellcont/shell/shellcont[1]/shell"

            self.log(f"Accessing tree control at: {tree_path}")
            try:
                tree = self.session.findById(tree_path)
                self.log(f"✓ Tree found successfully")
            except Exception as e:
                self.log(f"ERROR: Tree control not found: {str(e)[:100]}")
                return 0, []

            # 모든 노드 가져오기
            self.log(f"Getting all node keys from tree...")
            try:
                node_keys = list(tree.GetAllNodeKeys())
                file_count = len(node_keys)
                self.log(f"Found {file_count} nodes in tree")

                # 각 노드의 정보 출력 (디버깅)
                for i, nk in enumerate(node_keys):
                    try:
                        node_text = tree.GetNodeTextByKey(nk)
                        self.log(f"  Node {i+1}: [{nk}] Text: {node_text}")
                    except:
                        self.log(f"  Node {i+1}: [{nk}]")

            except Exception as e:
                self.log(f"ERROR: Could not get node keys: {str(e)[:100]}")
                return 0, []

            if not node_keys:
                self.log(f"No nodes found for {billing_doc}")
                return 0, []

            # 첫 번째 노드가 폴더일 수 있으므로 확장 시도
            if len(node_keys) > 0:
                try:
                    first_node = node_keys[0]
                    self.log(f"Attempting to expand first node: [{first_node}]")
                    tree.ExpandNode(first_node)
                    time.sleep(0.5)

                    # 확장 후 다시 노드 가져오기
                    node_keys = list(tree.GetAllNodeKeys())
                    self.log(f"After expansion: {len(node_keys)} nodes")
                    for i, nk in enumerate(node_keys):
                        try:
                            node_text = tree.GetNodeTextByKey(nk)
                            self.log(f"  Node {i+1}: [{nk}] Text: {node_text}")
                        except:
                            self.log(f"  Node {i+1}: [{nk}]")
                except Exception as e:
                    self.log(f"Could not expand first node: {str(e)[:100]}")

            # 각 노드(파일) 다운로드 - 첫 번째 노드는 폴더일 수 있으므로 스킵 가능성 고려
            downloaded_count = 0
            # 노드가 1개면 그것이 파일, 2개 이상이면 첫 번째는 폴더일 가능성
            start_idx = 1 if len(node_keys) > 1 else 0
            self.log(f"Starting download from node index {start_idx}")

            for i in range(start_idx, len(node_keys)):
                node_id = node_keys[i]
                try:
                    self.log(f"Processing file {i+1}/{len(node_keys)} (Node: {node_id})")

                    # 노드 선택
                    try:
                        self.log(f"  → Selecting node...")
                        tree.SelectNode(node_id)
                        self.log(f"  ✓ Node selected")
                        time.sleep(0.1)
                    except Exception as e:
                        self.log(f"  ✗ Failed to select node: {str(e)[:100]}")
                        continue

                    # 컨텍스트 메뉴 열기
                    try:
                        self.log(f"  → Opening context menu...")
                        tree.NodeContextMenu(node_id)
                        self.log(f"  ✓ Context menu opened")
                        time.sleep(0.2)
                    except Exception as e:
                        self.log(f"  ✗ Failed to open context menu: {str(e)[:100]}")
                        continue

                    # Export/Copy 선택
                    try:
                        self.log(f"  → Selecting CF_EXP_COPY...")
                        tree.SelectContextMenuItem("CF_EXP_COPY")
                        self.log(f"  ✓ CF_EXP_COPY selected")
                        time.sleep(0.5)
                    except Exception as e:
                        self.log(f"  ✗ Failed to select CF_EXP_COPY: {str(e)[:100]}")
                        continue

                    # 다운로드 다이얼로그에서 파일명 설정
                    try:
                        # 파일 경로 필드 확인
                        self.log(f"  → Finding file path field...")
                        file_field = self.session.findById("wnd[1]/usr/ctxtDRAW-FILEP")
                        self.log(f"  ✓ File path field found")
                        original_filename = file_field.text
                        self.log(f"  → Original filename: {original_filename}")

                        # 원본 파일명 추출 (경로에서 파일명만)
                        if original_filename:
                            import os as path_os
                            orig_name = path_os.path.basename(original_filename)
                            save_filename = f"{billing_doc}_{orig_name}"
                            save_fullpath = path_os.path.join(self.save_path, save_filename)
                            self.log(f"  → Save path: {save_fullpath}")

                            # 새 경로 설정
                            file_field.text = save_fullpath
                            file_field.setFocus()
                            self.log(f"  → File path set, clicking save button...")

                            # 저장 버튼 클릭
                            self.session.findById("wnd[1]/tbar[0]/btn[0]").press()
                            time.sleep(0.5)

                            downloaded_count += 1
                            self.log(f"  ✓ Downloaded: {save_filename}")

                            # 확인 메시지 처리
                            try:
                                self.log(f"  → Checking for confirmation popup...")
                                self.session.findById("wnd[2]/usr/btnSPOP-OPTION1").press()
                                self.log(f"  ✓ Confirmation popup handled")
                                time.sleep(0.2)
                            except:
                                self.log(f"  → No confirmation popup")
                                pass

                        else:
                            self.log(f"  ✗ No filename in dialog")

                    except Exception as e:
                        self.log(f"  ✗ Download dialog error: {str(e)[:100]}")

                except Exception as e:
                    self.log(f"  ✗ Error processing node {node_id}: {str(e)[:100]}")
                    continue

            # 다운로드 후 파일 목록
            after_files = set()
            if os.path.exists(self.save_path):
                after_files = set(os.listdir(self.save_path))

            # 새로 생성된 파일 확인
            new_files = after_files - before_files
            downloaded_files = [f for f in new_files if f.startswith(billing_doc)]

            return len(downloaded_files), downloaded_files

        except Exception as e:
            self.log(f"ERROR downloading {billing_doc}: {str(e)}")
            return 0, []

if __name__ == "__main__":
    # 테스트용
    print("D-term Downloader Module")
    print("Usage: import this module and use DtermDownloader class")
