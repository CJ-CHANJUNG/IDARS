#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMS 다운로더 - 간단 버전
전표번호를 직접 입력하여 SAP DMS 첨부파일을 다운로드하는 범용 프로그램
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

def get_application_path():
    """실행 파일의 실제 경로 반환 (EXE/Python 모두 지원)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 EXE인 경우
        return os.path.dirname(sys.executable)
    else:
        # 일반 Python 스크립트인 경우
        return os.path.dirname(os.path.abspath(__file__))

def get_default_download_path():
    """기본 다운로드 경로 반환"""
    # 실행 파일이 있는 폴더에 DMS_Downloads 폴더 생성
    app_path = get_application_path()
    return os.path.join(app_path, "DMS_Downloads")

class SimpleDMSDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("DMS 첨부파일 다운로더 - 간단 버전")
        self.root.geometry("700x550")
        
        # 프로그램 상태
        self.is_downloading = False
        self.stop_flag = None
        self.download_thread = None
        
        # 설정 변수들
        self.save_path = tk.StringVar(value=get_default_download_path())
        
        self.setup_ui()
        self.load_saved_settings()
        
    def setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 제목
        title_label = ttk.Label(main_frame, text="SAP DMS 첨부파일 다운로더", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 저장 경로 설정
        self.create_save_path_section(main_frame)
        
        # 전표번호 입력 섹션
        self.create_vbeln_input_section(main_frame)
        
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
        
        ttk.Entry(path_input_frame, textvariable=self.save_path, font=("Arial", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(path_input_frame, text="폴더 선택", command=self.browse_save_folder).pack(side=tk.RIGHT)
        
    def create_vbeln_input_section(self, parent):
        """전표번호 입력 섹션"""
        vbeln_frame = ttk.LabelFrame(parent, text="전표번호 입력", padding="5")
        vbeln_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 설명 라벨
        instruction_text = ("전표번호를 입력하세요 (한 줄에 하나씩):\n"
                          "• 엑셀에서 복사-붙여넣기 가능\n"
                          "• 공백이나 빈 줄은 자동으로 제거됩니다")
        ttk.Label(vbeln_frame, text=instruction_text, foreground="blue").pack(anchor=tk.W, pady=(0, 5))
        
        # 전표번호 입력 텍스트 박스
        input_frame = ttk.Frame(vbeln_frame)
        input_frame.pack(fill=tk.BOTH, expand=True)
        
        self.vbeln_text = scrolledtext.ScrolledText(input_frame, height=8, font=("Consolas", 10))
        self.vbeln_text.pack(fill=tk.BOTH, expand=True)
        
        # 예시 텍스트 추가
        example_text = ("# 예시:\n94408946\n94409124\n94409157\n\n"
                       "# 위 예시를 지우고 실제 전표번호를 입력하세요")
        self.vbeln_text.insert(tk.END, example_text)
        
        # 버튼 프레임
        button_frame = ttk.Frame(vbeln_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="전체 지우기", command=self.clear_vbeln_input).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="예시 넣기", command=self.insert_example).pack(side=tk.LEFT, padx=(0, 5))
        self.count_label = ttk.Label(button_frame, text="전표 개수: 0")
        self.count_label.pack(side=tk.RIGHT)
        
        # 텍스트 변경 이벤트 바인딩
        self.vbeln_text.bind('<KeyRelease>', self.update_vbeln_count)
        self.vbeln_text.bind('<Button-1>', self.update_vbeln_count)
        
    def create_execution_section(self, parent):
        """실행 섹션"""
        exec_frame = ttk.Frame(parent)
        exec_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 실행 버튼들
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
        
        self.current_vbeln_label = ttk.Label(status_frame, text="")
        self.current_vbeln_label.pack(side=tk.RIGHT)
        
    def create_log_section(self, parent):
        """로그 섹션"""
        log_frame = ttk.LabelFrame(parent, text="로그", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 초기 로그 메시지
        self.log("🚀 DMS 다운로더 시작")
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
            
    def clear_vbeln_input(self):
        """전표번호 입력 전체 지우기"""
        self.vbeln_text.delete(1.0, tk.END)
        self.update_vbeln_count()
        
    def insert_example(self):
        """예시 전표번호 입력"""
        self.vbeln_text.delete(1.0, tk.END)
        example_text = "94408946\n94409124\n94409157\n94409185\n94409202"
        self.vbeln_text.insert(tk.END, example_text)
        self.update_vbeln_count()
        
    def get_vbeln_list(self):
        """입력된 전표번호 리스트 추출"""
        text_content = self.vbeln_text.get(1.0, tk.END)
        lines = text_content.strip().split('\n')
        
        # 빈 줄, 주석(#으로 시작), 공백 제거
        vbeln_list = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                vbeln_list.append(line)
                
        return vbeln_list
        
    def update_vbeln_count(self, event=None):
        """전표번호 개수 업데이트"""
        vbeln_list = self.get_vbeln_list()
        self.count_label.config(text=f"전표 개수: {len(vbeln_list)}")
        
    def log(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_progress(self, current, total, vbeln=""):
        """진행률 업데이트"""
        if total > 0:
            progress_percent = (current / total) * 100
            self.progress['value'] = progress_percent
            
            status_text = f"진행률: {current}/{total} ({progress_percent:.1f}%)"
            self.status_label.config(text=status_text)
            
            if vbeln:
                self.current_vbeln_label.config(text=f"처리 중: {vbeln}")
                
        self.root.update_idletasks()
        
    def start_download(self):
        """다운로드 시작"""
        vbeln_list = self.get_vbeln_list()
        
        if not vbeln_list:
            messagebox.showwarning("경고", "전표번호를 입력해주세요.")
            return
            
        # 저장 폴더 생성
        try:
            os.makedirs(self.save_path.get(), exist_ok=True)
        except Exception as e:
            messagebox.showerror("오류", f"저장 폴더를 생성할 수 없습니다: {str(e)}")
            return
            
        # UI 상태 변경
        self.is_downloading = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        self.log(f"🚀 다운로드 시작 - 총 {len(vbeln_list)}개 전표")
        self.log(f"📁 저장 폴더: {self.save_path.get()}")
        
        # 별도 스레드에서 다운로드 실행
        self.stop_flag = threading.Event()
        self.download_thread = threading.Thread(
            target=self.download_worker,
            args=(vbeln_list,)
        )
        self.download_thread.start()
        
    def download_worker(self, vbeln_list):
        """다운로드 작업 스레드"""
        # COM 초기화 (별도 스레드에서 필수)
        pythoncom.CoInitialize()

        try:
            log_file = os.path.join(self.save_path.get(), f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

            # SAP 연결 - 여러 방법 시도
            SapGuiAuto = None
            application = None
            connection = None

            try:
                self.root.after(0, lambda: self.log("🔌 SAP GUI 연결 시도 중..."))

                # 방법 1: GetObject 시도
                try:
                    self.root.after(0, lambda: self.log("  방법1: GetObject('SAPGUI') 시도..."))
                    SapGuiAuto = win32com.client.GetObject("SAPGUI")
                    self.root.after(0, lambda: self.log("  ✓ 방법1 성공"))
                except Exception as e1:
                    self.root.after(0, lambda: self.log(f"  ✗ 방법1 실패: {str(e1)[:50]}"))

                    # 방법 2: Dispatch 시도
                    try:
                        self.root.after(0, lambda: self.log("  방법2: Dispatch('Sapgui.ScriptingCtrl.1') 시도..."))
                        SapGuiAuto = win32com.client.Dispatch("Sapgui.ScriptingCtrl.1")
                        self.root.after(0, lambda: self.log("  ✓ 방법2 성공"))
                    except Exception as e2:
                        self.root.after(0, lambda: self.log(f"  ✗ 방법2 실패: {str(e2)[:50]}"))

                        # 방법 3: GetActiveObject 시도
                        try:
                            self.root.after(0, lambda: self.log("  방법3: GetActiveObject 시도..."))
                            SapGuiAuto = win32com.client.GetActiveObject("SAPGUI")
                            self.root.after(0, lambda: self.log("  ✓ 방법3 성공"))
                        except Exception as e3:
                            self.root.after(0, lambda: self.log(f"  ✗ 방법3 실패: {str(e3)[:50]}"))
                            raise Exception("모든 SAP GUI 연결 방법 실패")

                if SapGuiAuto is None:
                    raise Exception("SAP GUI 객체를 생성할 수 없습니다")

                self.root.after(0, lambda: self.log("✓ SAPGUI 객체 획득 성공"))

                application = SapGuiAuto.GetScriptingEngine
                self.root.after(0, lambda: self.log("✓ 스크립팅 엔진 획득 성공"))

                if application.Children.Count == 0:
                    raise Exception("SAP GUI가 실행되었지만 연결된 세션이 없습니다. SAP에 로그인해주세요.")

                connection = application.Children(0)
                self.root.after(0, lambda: self.log(f"✓ SAP 연결 성공 (세션 수: {application.Children.Count})"))

            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.log(f"❌ SAP 연결 실패: {error_msg}"))

                # 에러 유형별 상세 메시지
                if "(-2147221020" in error_msg or "잘못된 구문" in error_msg:
                    detail_msg = ("SAP GUI COM 객체에 접근할 수 없습니다.\n\n"
                                 "해결 방법:\n"
                                 "1. SAP GUI를 완전히 종료 후 다시 실행하세요\n"
                                 "2. SAP Logon을 관리자 권한으로 실행하세요\n"
                                 "3. SAP GUI 옵션에서 스크립팅을 활성화하세요:\n"
                                 "   - SAP Logon → 옵션 → 접근성&스크립팅 → 스크립팅\n"
                                 "   - '스크립팅 사용' 체크\n"
                                 "4. 이 프로그램을 관리자 권한으로 실행하세요")
                elif "Children" in error_msg or "로그인" in error_msg:
                    detail_msg = ("SAP GUI는 실행되었지만 로그인된 세션이 없습니다.\n\n"
                                 "해결 방법:\n"
                                 "1. SAP GUI를 실행하고 시스템에 로그인하세요\n"
                                 "2. 로그인 후 다시 다운로드를 시도하세요")
                else:
                    detail_msg = (f"SAP 연결 중 오류가 발생했습니다.\n\n"
                                 f"오류 내용: {error_msg}\n\n"
                                 f"확인사항:\n"
                                 f"1. SAP GUI가 실행 중인지 확인\n"
                                 f"2. SAP에 로그인되어 있는지 확인\n"
                                 f"3. SAP 스크립팅이 활성화되어 있는지 확인")

                self.root.after(0, lambda: messagebox.showerror("SAP 연결 오류", detail_msg))
                return
                
            log_lines = []
            total_count = len(vbeln_list)
            completed_count = 0
            
            for vbeln in vbeln_list:
                # 정지 요청 체크
                if self.stop_flag.is_set():
                    self.root.after(0, lambda: self.log("⏹ 다운로드 중단됨"))
                    break
                    
                # 진행률 업데이트
                self.root.after(0, lambda c=completed_count, t=total_count, v=vbeln: 
                              self.update_progress(c, t, v))
                
                try:
                    # 새 세션 생성
                    base_session = connection.Children(0)
                    base_session.CreateSession()
                    time.sleep(1)
                    session = connection.Children(connection.Children.Count - 1)

                    session.findById("wnd[0]").maximize()
                    session.findById("wnd[0]/tbar[0]/okcd").text = "zsdr0390"
                    session.findById("wnd[0]").sendVKey(0)

                    # 화면 로딩 대기
                    if not self.wait_until_element_exists(session, "wnd[0]/usr/ctxtS_VBELN-LOW"):
                        log_lines.append(f"[{vbeln}] ❌ ZSDR0390 로딩 실패")
                        session.findById("wnd[0]").Close()
                        continue

                    # 전표번호 입력 및 실행
                    session.findById("wnd[0]/usr/ctxtS_VBELN-LOW").text = vbeln
                    session.findById("wnd[0]/usr/ctxtS_FKDAT-LOW").text = ""
                    session.findById("wnd[0]/tbar[1]/btn[8]").press()

                    try:
                        session.findById("wnd[0]/shellcont/shell").clickCurrentCell()
                        time.sleep(0.5)
                    except:
                        log_lines.append(f"[{vbeln}] ⚠ 전표 결과 없음")
                        self.root.after(0, lambda v=vbeln: self.log(f"⚠ {v}: 전표 결과 없음"))
                        session.findById("wnd[0]").Close()
                        continue

                    # 첨부탭 선택
                    try:
                        session.findById("wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN").select()
                        time.sleep(0.5)
                    except:
                        log_lines.append(f"[{vbeln}] ⚠ 첨부탭 접근 실패")
                        self.root.after(0, lambda v=vbeln: self.log(f"⚠ {v}: 첨부탭 접근 실패"))
                        session.findById("wnd[0]").Close()
                        continue

                    # 첨부파일 트리 접근
                    tree_path = "wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN/ssubSCR_MAIN:SAPLCV110:0102/cntlCTL_FILES1/shellcont/shell/shellcont[1]/shell"
                    try:
                        tree = session.findById(tree_path)
                        node_keys = list(tree.GetAllNodeKeys())
                        file_count = len(node_keys)
                        log_lines.append(f"[{vbeln}] 📎 첨부파일 개수: {file_count}")
                        self.root.after(0, lambda v=vbeln, c=file_count: self.log(f"📎 {v}: {c}개 첨부파일 발견"))
                    except Exception as e:
                        log_lines.append(f"[{vbeln}] ⚠ 트리 접근 실패: {e}")
                        self.root.after(0, lambda v=vbeln: self.log(f"⚠ {v}: 첨부파일 트리 접근 실패"))
                        session.findById("wnd[0]").Close()
                        continue

                    if not node_keys:
                        log_lines.append(f"[{vbeln}] ⚠ 첨부파일 없음")
                        self.root.after(0, lambda v=vbeln: self.log(f"⚠ {v}: 첨부파일 없음"))
                        session.findById("wnd[0]").Close()
                        continue

                    # 첨부파일 다운로드
                    downloaded_files = 0
                    for i, node_id in enumerate(node_keys):
                        if self.stop_flag.is_set():
                            break
                            
                        try:
                            tree.SelectNode(node_id)
                            tree.NodeContextMenu(node_id)
                            tree.SelectContextMenuItem("CF_EXP_COPY")
                            time.sleep(0.5)

                            # 저장창에서 파일명 처리
                            saved = False
                            for wnd_num in range(1, 5):
                                try:
                                    path_box = session.findById(f"wnd[{wnd_num}]/usr/ctxtDRAW-FILEP")
                                    full_sap_path = path_box.text.strip()
                                    original_file_name = os.path.basename(full_sap_path)

                                    # 최종 저장 파일명: 전표번호_기존파일명
                                    new_file_name = f"{vbeln}_{original_file_name}"
                                    save_path = os.path.join(self.save_path.get(), new_file_name)

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
                                log_lines.append(f"[{vbeln}] ✅ 저장 완료: {new_file_name}")
                                downloaded_files += 1
                            else:
                                log_lines.append(f"[{vbeln}] ❌ 저장 실패 (파일 {i+1})")
                                
                        except Exception as e:
                            log_lines.append(f"[{vbeln}] ❌ 오류 (파일 {i+1}): {e}")

                    # 전표 처리 완료
                    if downloaded_files > 0:
                        self.root.after(0, lambda v=vbeln, c=downloaded_files: 
                                      self.log(f"✅ {v}: {c}개 파일 다운로드 완료"))
                    else:
                        self.root.after(0, lambda v=vbeln: self.log(f"❌ {v}: 다운로드 실패"))

                    session.findById("wnd[0]").Close()

                except Exception as e:
                    log_lines.append(f"[{vbeln}] ❌ 전표 처리 실패: {e}")
                    self.root.after(0, lambda v=vbeln, err=str(e): self.log(f"❌ {v}: 처리 실패 - {err}"))
                
                completed_count += 1
                
            # 로그 저장
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines))
                
            # 완료 메시지
            if not self.stop_flag.is_set():
                self.root.after(0, lambda: self.log("🎉 모든 다운로드 완료!"))
                self.root.after(0, lambda: self.log(f"📋 로그 파일: {log_file}"))
                self.root.after(0, lambda: messagebox.showinfo("완료", 
                    f"다운로드가 완료되었습니다!\n\n"
                    f"처리된 전표: {completed_count}/{total_count}\n"
                    f"저장 폴더: {self.save_path.get()}\n"
                    f"로그 파일: {os.path.basename(log_file)}"))
                    
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ 다운로드 오류: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("오류", f"다운로드 중 오류가 발생했습니다:\n{str(e)}"))

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
        self.current_vbeln_label.config(text="")
        
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
        settings_file = os.path.join(get_application_path(), "dms_simple_settings.txt")
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                f.write(f"save_path={self.save_path.get()}\n")
        except:
            pass  # 설정 저장 실패는 무시

    def load_saved_settings(self):
        """저장된 설정 로드"""
        settings_file = os.path.join(get_application_path(), "dms_simple_settings.txt")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("save_path="):
                            path = line.strip().split("=", 1)[1]
                            if os.path.exists(path):
                                self.save_path.set(path)
        except:
            pass  # 설정 로드 실패는 무시

def main():
    """메인 함수"""
    # 현재 디렉토리에 필요한 모듈이 있는지 확인
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
    app = SimpleDMSDownloader(root)
    
    # 창 닫기 이벤트 처리
    def on_closing():
        if app.is_downloading:
            if messagebox.askokcancel("종료", "다운로드가 진행 중입니다. 정말 종료하시겠습니까?"):
                if app.stop_flag:
                    app.stop_flag.set()
                root.destroy()
        else:
            root.destroy()
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 창 아이콘 설정 (선택사항)
    try:
        root.iconbitmap(default="")  # 기본 아이콘 사용
    except:
        pass
        
    root.mainloop()

if __name__ == "__main__":
    main()