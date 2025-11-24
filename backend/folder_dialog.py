"""
폴더 선택 유틸리티
Windows 탐색기를 열어 폴더를 선택할 수 있도록 지원
"""
import tkinter as tk
from tkinter import filedialog

def select_folder_dialog():
    """Windows 탐색기를 열어 폴더 선택"""
    root = tk.Tk()
    root.withdraw()  # GUI 윈도우 숨기기
    root.attributes('-topmost', True)  # 상단에 표시
    
    folder_path = filedialog.askdirectory(title='증빙 저장 폴더 선택')
    root.destroy()
    
    return folder_path if folder_path else None
