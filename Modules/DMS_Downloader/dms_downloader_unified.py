#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMS 통합 다운로더
매출/매입 전표를 전표번호 길이로 자동 인식하여 다운로드
- 8자리: 매출전표 (Billing) - ZSDR0390
- 10자리: 매입전표 (LIV) - ZMMR0820
"""

import sys
import os
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
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
        "color": "#0066CC"  # 파란색
    },
    "LIV": {
        "name": "매입전표",
        "transaction": "zmmr0820",
        "input_field": "wnd[0]/usr/txtS_BELNR-LOW",
        "date_field": "wnd[0]/usr/ctxtS_BUDAT-LOW",
        "folder": "LIV",
        "length": 10,
        "color": "#CC6600"  # 주황색
    }
}

def get_application_path():
    """실행 파일의 실제 경로 반환 (EXE/Python 모두 지원)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_default_download_path():
    """기본 다운로드 경로 반환"""
    app_path = get_application_path()
    return os.path.join(app_path, "DMS_Downloads")

def detect_transaction_type(number):
    """전표번호 길이로 Transaction 타입 자동 감지"""
    clean_number = number.strip()

    if len(clean_number) == 8:
        return "Billing"
    elif len(clean_number) == 10:
        return "LIV"
    else:
        return "UNKNOWN"

class UnifiedDMSDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("DMS 통합 다운로더 - 매출/매입 자동 인식")
        self.root.geometry("750x650")

        # 프로그램 상태
        self.is_downloading = False
        self.stop_flag = None
        self.download_thread = None

        # 설정 변수들
        self.save_path = tk.StringVar(value=get_default_download_path())

        # 전표 통계
        self.doc_stats = {"Billing": 0, "LIV": 0, "UNKNOWN": 0}

        self.setup_ui()
        self.load_saved_settings()

    def setup_ui(self):
        """UI 구성"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 제목
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(pady=(0, 10))

        title_label = ttk.Label(title_frame, text="DMS 통합 다운로더",
                               font=("Arial", 14, "bold"))
        title_label.pack()

        subtitle_label = ttk.Label(title_frame, text="매출/매입 전표 자동 인식 (8자리=매출 | 10자리=매입)",
                                  font=("Arial", 9), foreground="gray")
        subtitle_label.pack()

        # 저장 경로 설정
        self.create_save_path_section(main_frame)

        # 전표번호 입력 섹션
        self.create_doc_input_section(main_frame)

        # 통계 섹션
        self.create_stats_section(main_frame)

        # 실행 버튼 섹션
        self.create_execution_section(main_frame)

        # 진행률 섹션
        self.create_progress_section(main_frame)

        # 로그 섹션
        self.create_log_section(main_frame)

    def create_save_path_section(self, parent):
        """저장 경로 설정 섹션"""
        path_frame = ttk.LabelFrame(parent, text="저장 경로", padding="5")
        path_frame.pack(fill=tk.X, pady=(0, 10))

        path_input_frame = ttk.Frame(path_frame)
        path_input_frame.pack(fill=tk.X)

        ttk.Entry(path_input_frame, textvariable=self.save_path, font=("Arial", 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(path_input_frame, text="폴더 선택", command=self.browse_save_folder).pack(side=tk.RIGHT)

        # 안내 메시지
        info_label = ttk.Label(path_frame,
                              text="💡 하위에 Billing/, LIV/ 폴더가 자동 생성됩니다",
                              font=("Arial", 8), foreground="blue")
        info_label.pack(anchor=tk.W, pady=(3, 0))

    def create_doc_input_section(self, parent):
        """전표번호 입력 섹션"""
        doc_frame = ttk.LabelFrame(parent, text="전표번호 입력", padding="5")
        doc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 설명 라벨
        instruction_text = ("전표번호를 입력하세요 (한 줄에 하나씩):\n"
                          "• 매출: 8자리 (예: 94408946) → ZSDR0390\n"
                          "• 매입: 10자리 (예: 5105824933) → ZMMR0820\n"
                          "• 혼합 입력 가능 (자동 인식)")
        ttk.Label(doc_frame, text=instruction_text, foreground="blue").pack(anchor=tk.W, pady=(0, 5))

        # 전표번호 입력 텍스트 박스
        input_frame = ttk.Frame(doc_frame)
        input_frame.pack(fill=tk.BOTH, expand=True)

        # 텍스트 박스와 타입 표시를 함께 배치
        text_container = ttk.Frame(input_frame)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.doc_text = scrolledtext.ScrolledText(text_container, height=8, font=("Consolas", 10))
        self.doc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 예시 텍스트 추가
        example_text = ("# 예시 (혼합 입력 가능):\n94408946\n5105824933\n94409124\n5105825001\n\n"
                       "# 위 예시를 지우고 실제 전표번호를 입력하세요")
        self.doc_text.insert(tk.END, example_text)

        # 버튼 프레임
        button_frame = ttk.Frame(doc_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(button_frame, text="전체 지우기", command=self.clear_doc_input).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="예시 넣기", command=self.insert_example).pack(side=tk.LEFT, padx=(0, 5))

        # 텍스트 변경 이벤트 바인딩
        self.doc_text.bind('<KeyRelease>', self.update_doc_stats)
        self.doc_text.bind('<Button-1>', self.update_doc_stats)

    def create_stats_section(self, parent):
        """통계 섹션"""
        stats_frame = ttk.LabelFrame(parent, text="전표 통계", padding="5")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.stats_label = ttk.Label(stats_frame,
                                     text="총 0개 | 매출: 0개 | 매입: 0개",
                                     font=("Arial", 10, "bold"))
        self.stats_label.pack()

    def create_execution_section(self, parent):
        """실행 섹션"""
        exec_frame = ttk.Frame(parent)
        exec_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_button = ttk.Button(exec_frame, text="📥 다운로드 시작",
                                     command=self.start_download, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(exec_frame, text="⏹ 중단",
                                    command=self.stop_download, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(exec_frame, text="📁 저장폴더 열기", command=self.open_save_folder).pack(side=tk.RIGHT)

    def create_progress_section(self, parent):
        """진행률 섹션"""
        progress_frame = ttk.LabelFrame(parent, text="진행 상황", padding="5")
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        # 진행률 바
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 5))

        # 상태 정보
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="대기 중...")
        self.status_label.pack(side=tk.LEFT)

        self.current_doc_label = ttk.Label(status_frame, text="")
        self.current_doc_label.pack(side=tk.RIGHT)

    def create_log_section(self, parent):
        """로그 섹션"""
        log_frame = ttk.LabelFrame(parent, text="로그", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 초기 로그 메시지
        self.log("🚀 DMS 통합 다운로더 시작")
        self.log("💡 전표번호를 입력하고 다운로드를 시작하세요")

    def browse_save_folder(self):
        """저장 폴더 선택"""
        folder = filedialog.askdirectory(
            title="다운로드 저장 폴더 선택",
            initialdir=self.save_path.get()
        )
        if folder:
            self.save_path.set(folder)
            self.log(f"📁 저장 폴더 변경: {folder}")
            self.save_settings()

    def clear_doc_input(self):
        """전표번호 입력 전체 지우기"""
        self.doc_text.delete(1.0, tk.END)
        self.update_doc_stats()

    def insert_example(self):
        """예시 전표번호 입력"""
        self.doc_text.delete(1.0, tk.END)
        example_text = "94408946\n5105824933\n94409124\n5105825001\n94409157"
        self.doc_text.insert(tk.END, example_text)
        self.update_doc_stats()

    def get_doc_list(self):
        """입력된 전표번호 리스트 추출"""
        text_content = self.doc_text.get(1.0, tk.END)
        lines = text_content.strip().split('\n')

        doc_list = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                doc_list.append(line)

        return doc_list

    def update_doc_stats(self, event=None):
        """전표번호 통계 업데이트"""
        doc_list = self.get_doc_list()

        # 통계 초기화
        self.doc_stats = {"Billing": 0, "LIV": 0, "UNKNOWN": 0}

        # 각 전표번호 분류
        for doc_number in doc_list:
            doc_type = detect_transaction_type(doc_number)
            self.doc_stats[doc_type] += 1

        # 통계 레이블 업데이트
        total = sum(self.doc_stats.values())
        billing_count = self.doc_stats["Billing"]
        liv_count = self.doc_stats["LIV"]
        unknown_count = self.doc_stats["UNKNOWN"]

        stats_text = f"총 {total}개 | 매출: {billing_count}개 | 매입: {liv_count}개"
        if unknown_count > 0:
            stats_text += f" | ⚠️ 미인식: {unknown_count}개"

        self.stats_label.config(text=stats_text)

    def log(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, current, total, doc_number=""):
        """진행률 업데이트"""
        if total > 0:
            progress_percent = (current / total) * 100
            self.progress['value'] = progress_percent

            status_text = f"진행률: {current}/{total} ({progress_percent:.1f}%)"
            self.status_label.config(text=status_text)

            if doc_number:
                doc_type = detect_transaction_type(doc_number)
                type_name = TRANSACTION_CONFIG.get(doc_type, {}).get("name", "알 수 없음")
                self.current_doc_label.config(text=f"처리 중: {doc_number} [{type_name}]")

        self.root.update_idletasks()

    def start_download(self):
        """다운로드 시작"""
        doc_list = self.get_doc_list()

        if not doc_list:
            messagebox.showwarning("경고", "전표번호를 입력해주세요.")
            return

        # 미인식 전표 확인
        if self.doc_stats["UNKNOWN"] > 0:
            unknown_docs = [doc for doc in doc_list if detect_transaction_type(doc) == "UNKNOWN"]
            msg = f"인식할 수 없는 전표번호가 {len(unknown_docs)}개 있습니다:\n\n"
            msg += "\n".join(unknown_docs[:5])
            if len(unknown_docs) > 5:
                msg += f"\n... 외 {len(unknown_docs)-5}개"
            msg += "\n\n계속 진행하시겠습니까? (미인식 전표는 건너뜁니다)"

            if not messagebox.askyesno("미인식 전표 확인", msg):
                return

        # 저장 폴더 생성
        try:
            os.makedirs(self.save_path.get(), exist_ok=True)
            os.makedirs(os.path.join(self.save_path.get(), "Billing"), exist_ok=True)
            os.makedirs(os.path.join(self.save_path.get(), "LIV"), exist_ok=True)
        except Exception as e:
            messagebox.showerror("오류", f"저장 폴더를 생성할 수 없습니다: {str(e)}")
            return

        # UI 상태 변경
        self.is_downloading = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self.log(f"🚀 다운로드 시작 - 총 {len(doc_list)}개 전표")
        self.log(f"   매출: {self.doc_stats['Billing']}개 | 매입: {self.doc_stats['LIV']}개")
        self.log(f"📁 저장 폴더: {self.save_path.get()}")

        # 별도 스레드에서 다운로드 실행
        self.stop_flag = threading.Event()
        self.download_thread = threading.Thread(
            target=self.download_worker,
            args=(doc_list,)
        )
        self.download_thread.start()

    def download_worker(self, doc_list):
        """다운로드 작업 스레드"""
        # COM 초기화 (별도 스레드에서 필수)
        pythoncom.CoInitialize()

        try:
            log_file = os.path.join(self.save_path.get(),
                                   f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

            # SAP 연결
            SapGuiAuto = None
            application = None
            connection = None

            try:
                self.root.after(0, lambda: self.log("🔌 SAP GUI 연결 시도 중..."))

                # 여러 방법으로 연결 시도
                try:
                    SapGuiAuto = win32com.client.GetObject("SAPGUI")
                except:
                    try:
                        SapGuiAuto = win32com.client.Dispatch("Sapgui.ScriptingCtrl.1")
                    except:
                        SapGuiAuto = win32com.client.GetActiveObject("SAPGUI")

                if SapGuiAuto is None:
                    raise Exception("SAP GUI 객체를 생성할 수 없습니다")

                application = SapGuiAuto.GetScriptingEngine

                if application.Children.Count == 0:
                    raise Exception("SAP GUI가 실행되었지만 연결된 세션이 없습니다. SAP에 로그인해주세요.")

                connection = application.Children(0)
                self.root.after(0, lambda: self.log(f"✓ SAP 연결 성공"))

            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.log(f"❌ SAP 연결 실패: {error_msg}"))
                self.root.after(0, lambda: messagebox.showerror("SAP 연결 오류",
                    f"SAP 연결에 실패했습니다.\n\n{error_msg}\n\n"
                    "확인사항:\n"
                    "1. SAP GUI 실행 및 로그인\n"
                    "2. SAP 스크립팅 활성화"))
                return

            log_lines = []
            total_count = len(doc_list)
            completed_count = 0
            success_count = {"Billing": 0, "LIV": 0}
            fail_count = {"Billing": 0, "LIV": 0}

            for doc_number in doc_list:
                # 정지 요청 체크
                if self.stop_flag.is_set():
                    self.root.after(0, lambda: self.log("⏹ 다운로드 중단됨"))
                    break

                # 진행률 업데이트
                self.root.after(0, lambda c=completed_count, t=total_count, d=doc_number:
                              self.update_progress(c, t, d))

                # 전표 타입 감지
                doc_type = detect_transaction_type(doc_number)

                if doc_type == "UNKNOWN":
                    log_lines.append(f"[{doc_number}] ❌ 미인식 전표 형식 (길이: {len(doc_number)})")
                    self.root.after(0, lambda d=doc_number: self.log(f"⚠️ {d}: 미인식 형식 - 건너뜀"))
                    completed_count += 1
                    continue

                config = TRANSACTION_CONFIG[doc_type]
                type_name = config["name"]

                try:
                    # 새 세션 생성
                    base_session = connection.Children(0)
                    base_session.CreateSession()
                    time.sleep(1)
                    session = connection.Children(connection.Children.Count - 1)

                    session.findById("wnd[0]").maximize()
                    session.findById("wnd[0]/tbar[0]/okcd").text = config["transaction"]
                    session.findById("wnd[0]").sendVKey(0)

                    # 화면 로딩 대기
                    if not self.wait_until_element_exists(session, config["input_field"]):
                        log_lines.append(f"[{doc_number}] ❌ {config['transaction'].upper()} 로딩 실패")
                        fail_count[doc_type] += 1
                        session.findById("wnd[0]").Close()
                        continue

                    # 전표번호 입력 및 실행
                    session.findById(config["input_field"]).text = doc_number
                    session.findById(config["date_field"]).text = ""
                    session.findById("wnd[0]/tbar[1]/btn[8]").press()

                    try:
                        session.findById("wnd[0]/shellcont/shell").clickCurrentCell()
                        time.sleep(0.5)
                    except:
                        log_lines.append(f"[{doc_number}] ⚠ 전표 결과 없음 [{type_name}]")
                        self.root.after(0, lambda d=doc_number, t=type_name:
                                      self.log(f"⚠ {d} [{t}]: 전표 결과 없음"))
                        fail_count[doc_type] += 1
                        session.findById("wnd[0]").Close()
                        continue

                    # 첨부탭 선택 (Billing만 해당)
                    if doc_type == "Billing":
                        try:
                            session.findById("wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN").select()
                            time.sleep(0.5)
                        except:
                            log_lines.append(f"[{doc_number}] ⚠ 첨부탭 접근 실패 [{type_name}]")
                            self.root.after(0, lambda d=doc_number, t=type_name:
                                          self.log(f"⚠ {d} [{t}]: 첨부탭 접근 실패"))
                            fail_count[doc_type] += 1
                            session.findById("wnd[0]").Close()
                            continue

                    # 첨부파일 트리 접근
                    tree_path = "wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN/ssubSCR_MAIN:SAPLCV110:0102/cntlCTL_FILES1/shellcont/shell/shellcont[1]/shell"
                    try:
                        tree = session.findById(tree_path)
                        node_keys = list(tree.GetAllNodeKeys())
                        file_count = len(node_keys)
                        log_lines.append(f"[{doc_number}] 📎 첨부파일 개수: {file_count} [{type_name}]")
                        self.root.after(0, lambda d=doc_number, c=file_count, t=type_name:
                                      self.log(f"📎 {d} [{t}]: {c}개 첨부파일 발견"))
                    except Exception as e:
                        log_lines.append(f"[{doc_number}] ⚠ 트리 접근 실패: {e} [{type_name}]")
                        self.root.after(0, lambda d=doc_number, t=type_name:
                                      self.log(f"⚠ {d} [{t}]: 첨부파일 트리 접근 실패"))
                        fail_count[doc_type] += 1
                        session.findById("wnd[0]").Close()
                        continue

                    if not node_keys:
                        log_lines.append(f"[{doc_number}] ⚠ 첨부파일 없음 [{type_name}]")
                        self.root.after(0, lambda d=doc_number, t=type_name:
                                      self.log(f"⚠ {d} [{t}]: 첨부파일 없음"))
                        fail_count[doc_type] += 1
                        session.findById("wnd[0]").Close()
                        continue

                    # 저장 경로 (타입별 폴더 분리)
                    type_save_dir = os.path.join(self.save_path.get(), config["folder"])
                    os.makedirs(type_save_dir, exist_ok=True)

                    # 첨부파일 다운로드
                    downloaded_files = 0
                    for i, node_id in enumerate(node_keys):
                        if self.stop_flag.is_set():
                            break

                        try:
                            tree.SelectNode(node_id)

                            # Billing: 컨텍스트 메뉴, LIV: F7 키
                            if doc_type == "Billing":
                                tree.NodeContextMenu(node_id)
                                tree.SelectContextMenuItem("CF_EXP_COPY")
                            else:  # LIV
                                session.findById("wnd[0]").sendVKey(19)  # F7

                            time.sleep(0.5)

                            # 저장창에서 파일명 처리
                            saved = False
                            for wnd_num in range(1, 5):
                                try:
                                    path_box = session.findById(f"wnd[{wnd_num}]/usr/ctxtDRAW-FILEP")
                                    full_sap_path = path_box.text.strip()
                                    original_file_name = os.path.basename(full_sap_path)

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
                                    session.findById(f"wnd[{wnd_num}]/tbar[0]/btn[0]").press()
                                    saved = True
                                    break
                                except:
                                    continue

                            if saved:
                                try:
                                    session.findById("wnd[1]/tbar[0]/btn[0]").press()
                                except:
                                    pass
                                log_lines.append(f"[{doc_number}] ✅ 저장 완료: {new_file_name} [{type_name}]")
                                downloaded_files += 1
                            else:
                                log_lines.append(f"[{doc_number}] ❌ 저장 실패 (파일 {i+1}) [{type_name}]")

                        except Exception as e:
                            log_lines.append(f"[{doc_number}] ❌ 오류 (파일 {i+1}): {e} [{type_name}]")

                    # 전표 처리 완료
                    if downloaded_files > 0:
                        self.root.after(0, lambda d=doc_number, c=downloaded_files, t=type_name:
                                      self.log(f"✅ {d} [{t}]: {c}개 파일 다운로드 완료"))
                        success_count[doc_type] += 1
                    else:
                        self.root.after(0, lambda d=doc_number, t=type_name:
                                      self.log(f"❌ {d} [{t}]: 다운로드 실패"))
                        fail_count[doc_type] += 1

                    session.findById("wnd[0]").Close()

                except Exception as e:
                    log_lines.append(f"[{doc_number}] ❌ 전표 처리 실패: {e}")
                    self.root.after(0, lambda d=doc_number, err=str(e):
                                  self.log(f"❌ {d}: 처리 실패 - {err}"))
                    if doc_type != "UNKNOWN":
                        fail_count[doc_type] += 1

                completed_count += 1

            # 로그 저장
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines))

            # 완료 메시지
            if not self.stop_flag.is_set():
                summary = (f"처리 완료!\n\n"
                          f"총 {completed_count}개 처리\n"
                          f"매출 성공: {success_count['Billing']}개 / 실패: {fail_count['Billing']}개\n"
                          f"매입 성공: {success_count['LIV']}개 / 실패: {fail_count['LIV']}개\n\n"
                          f"저장 폴더: {self.save_path.get()}\n"
                          f"로그 파일: {os.path.basename(log_file)}")

                self.root.after(0, lambda: self.log("🎉 모든 다운로드 완료!"))
                self.root.after(0, lambda: self.log(f"📋 로그 파일: {log_file}"))
                self.root.after(0, lambda: messagebox.showinfo("완료", summary))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ 다운로드 오류: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("오류",
                f"다운로드 중 오류가 발생했습니다:\n{str(e)}"))

        finally:
            # COM 정리
            pythoncom.CoUninitialize()
            self.root.after(0, self.reset_ui_state)

    def wait_until_element_exists(self, session, element_id, timeout=10):
        """SAP 화면 요소 로딩 대기"""
        for _ in range(timeout * 2):
            try:
                session.findById(element_id)
                return True
            except:
                time.sleep(0.5)
        return False

    def stop_download(self):
        """다운로드 중단"""
        if self.stop_flag:
            self.stop_flag.set()
            self.log("⏹ 중단 요청됨...")

    def reset_ui_state(self):
        """UI 상태 리셋"""
        self.is_downloading = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress['value'] = 0
        self.status_label.config(text="대기 중...")
        self.current_doc_label.config(text="")

    def open_save_folder(self):
        """저장 폴더 열기"""
        try:
            import subprocess
            if os.path.exists(self.save_path.get()):
                subprocess.Popen(f'explorer "{self.save_path.get()}"')
            else:
                os.makedirs(self.save_path.get(), exist_ok=True)
                subprocess.Popen(f'explorer "{self.save_path.get()}"')
        except Exception as e:
            messagebox.showerror("오류", f"폴더 열기 실패: {str(e)}")

    def save_settings(self):
        """설정 저장"""
        settings_file = os.path.join(get_application_path(), "dms_unified_settings.txt")
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                f.write(f"save_path={self.save_path.get()}\n")
        except:
            pass

    def load_saved_settings(self):
        """저장된 설정 로드"""
        settings_file = os.path.join(get_application_path(), "dms_unified_settings.txt")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("save_path="):
                            path = line.strip().split("=", 1)[1]
                            if os.path.exists(path):
                                self.save_path.set(path)
        except:
            pass

def main():
    """메인 함수"""
    try:
        import win32com.client
    except ImportError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("모듈 오류",
            "pywin32 모듈이 설치되지 않았습니다.\n\n"
            "다음 명령어로 설치하세요:\n"
            "pip install pywin32")
        return

    root = tk.Tk()
    app = UnifiedDMSDownloader(root)

    def on_closing():
        if app.is_downloading:
            if messagebox.askokcancel("종료", "다운로드가 진행 중입니다. 정말 종료하시겠습니까?"):
                if app.stop_flag:
                    app.stop_flag.set()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    try:
        root.iconbitmap(default="")
    except:
        pass

    root.mainloop()

if __name__ == "__main__":
    main()
