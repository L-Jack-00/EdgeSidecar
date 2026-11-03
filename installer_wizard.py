import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QProgressBar, QMessageBox, QFileDialog
)

def create_installer_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0ea5e9"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(6, 6, 52, 52, 14, 14)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", 26, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "E")
    painter.end()
    return QIcon(pixmap)

def create_windows_shortcut(target_exe: Path, shortcut_path: Path, working_dir: Path):
    """Creates a Windows .lnk shortcut using WScript.Shell."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = str(target_exe)
        shortcut.WorkingDirectory = str(working_dir)
        shortcut.Description = "Edge Sidecar Browser"
        shortcut.IconLocation = f"{target_exe},0"
        shortcut.Save()
        return True
    except Exception as e:
        print(f"[Installer] Failed to create shortcut: {e}")
        return False

class InstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: Path, make_desktop: bool, make_start: bool):
        super().__init__()
        self.target_dir = target_dir
        self.make_desktop = make_desktop
        self.make_start = make_start

    def run(self):
        try:
            self.progress_changed.emit(10, "설치 디렉토리 준비 중...")
            self.target_dir.mkdir(parents=True, exist_ok=True)

            # Determine source directory (frozen vs script)
            if getattr(sys, "frozen", False):
                src_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "payload"
                if not src_dir.exists():
                    src_dir = Path(sys.executable).parent
            else:
                src_dir = Path(__file__).parent / "dist" / "EdgeSidecar"
                if not src_dir.exists():
                    src_dir = Path(__file__).parent

            self.progress_changed.emit(30, "프로그램 핵심 파일 복사 중...")
            time.sleep(0.3)

            # Copy files to target_dir
            if (src_dir / "EdgeSidecar.exe").exists():
                shutil.copy2(src_dir / "EdgeSidecar.exe", self.target_dir / "EdgeSidecar.exe")
            if (src_dir / "_internal").exists():
                dest_internal = self.target_dir / "_internal"
                if dest_internal.exists():
                    shutil.rmtree(dest_internal, ignore_errors=True)
                shutil.copytree(src_dir / "_internal", dest_internal)

            # Ensure essential assets
            for extra in ["dashboard.html", "rules.json", "README.md"]:
                if (src_dir / extra).exists():
                    shutil.copy2(src_dir / extra, self.target_dir / extra)

            # Ensure bin directory exists for portable chromium
            (self.target_dir / "bin").mkdir(exist_ok=True)

            self.progress_changed.emit(70, "바로가기 생성 중...")
            exe_path = self.target_dir / "EdgeSidecar.exe"

            # Desktop Shortcut
            if self.make_desktop and exe_path.exists():
                desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
                if desktop.exists():
                    create_windows_shortcut(exe_path, desktop / "Edge Sidecar.lnk", self.target_dir)

            # Start Menu Shortcut
            if self.make_start and exe_path.exists():
                start_menu = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"))
                if start_menu.exists():
                    create_windows_shortcut(exe_path, start_menu / "Edge Sidecar.lnk", self.target_dir)

            # Create clean uninstaller script
            uninstaller_bat = self.target_dir / "uninstall.bat"
            with open(uninstaller_bat, "w", encoding="utf-8") as f:
                f.write(
                    '@echo off\n'
                    'echo Edge Sidecar Browser 제거 중...\n'
                    'timeout /t 2 /nobreak > nul\n'
                    f'del /f /q "%USERPROFILE%\\Desktop\\Edge Sidecar.lnk" 2>nul\n'
                    f'del /f /q "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Edge Sidecar.lnk" 2>nul\n'
                    f'cd ..\n'
                    f'rmdir /s /q "{self.target_dir}" 2>nul\n'
                    'echo 제거가 완료되었습니다.\n'
                    'pause\n'
                )

            self.progress_changed.emit(100, "설치 완료!")
            self.finished.emit(True, str(exe_path))
        except Exception as e:
            self.finished.emit(False, str(e))

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge Sidecar Browser 설치 마법사 (v1.2.0)")
        self.setFixedSize(540, 420)
        self.setWindowIcon(create_installer_icon())
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLabel { font-size: 13px; }
            QLineEdit {
                background: #1e293b;
                border: 1px solid #334155;
                padding: 8px 12px;
                border-radius: 6px;
                color: #f8fafc;
            }
            QPushButton {
                background: #0ea5e9;
                color: #000;
                font-weight: bold;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background: #38bdf8; }
            QPushButton#btn-browse {
                background: #334155;
                color: #f8fafc;
                padding: 8px 14px;
            }
            QCheckBox { font-size: 13px; spacing: 8px; }
            QProgressBar {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #fff;
                height: 20px;
            }
            QProgressBar::chunk { background: #0ea5e9; border-radius: 5px; }
        """)

        self.default_install_path = Path(os.path.expandvars(r"%LOCALAPPDATA%\EdgeSidecar"))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(16)

        # Header Title
        title = QLabel("🛡️ Edge Sidecar Browser 설치 마법사")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        desc = QLabel("파이썬 없이도 바로 실행되는 포터블 크로뮴 기반 커스텀 브라우저를 설치합니다.")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(desc)

        # Path selection
        layout.addWidget(QLabel("설치 경로:"))
        path_box = QHBoxLayout()
        self.txt_path = QLineEdit(str(self.default_install_path))
        path_box.addWidget(self.txt_path)
        btn_browse = QPushButton("찾아보기...")
        btn_browse.setObjectName("btn-browse")
        btn_browse.clicked.connect(self.browse_folder)
        path_box.addWidget(btn_browse)
        layout.addLayout(path_box)

        # Options
        self.chk_desktop = QCheckBox("바탕화면에 바로가기 생성")
        self.chk_desktop.setChecked(True)
        layout.addWidget(self.chk_desktop)

        self.chk_start = QCheckBox("시작 메뉴에 등록")
        self.chk_start.setChecked(True)
        layout.addWidget(self.chk_start)

        # Progress bar
        self.lbl_status = QLabel("준비됨")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_install = QPushButton("설치 시작 ➔")
        self.btn_install.clicked.connect(self.start_install)
        btn_box.addWidget(self.btn_install)
        layout.addLayout(btn_box)

        self.setLayout(layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "설치할 폴더 선택", self.txt_path.text())
        if folder:
            self.txt_path.setText(str(Path(folder) / "EdgeSidecar"))

    def start_install(self):
        target_dir = Path(self.txt_path.text().strip())
        self.btn_install.setEnabled(False)
        self.txt_path.setEnabled(False)

        self.worker = InstallWorker(
            target_dir=target_dir,
            make_desktop=self.chk_desktop.isChecked(),
            make_start=self.chk_start.isChecked()
        )
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, val, msg):
        self.progress.setValue(val)
        self.lbl_status.setText(msg)

    def on_finished(self, success, result):
        if success:
            reply = QMessageBox.question(
                self, "설치 완료",
                "Edge Sidecar Browser 설치가 성공적으로 완료되었습니다!\n\n지금 프로그램을 실행하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes and os.path.exists(result):
                os.startfile(result)
            self.close()
        else:
            QMessageBox.critical(self, "설치 오류", f"설치 중 오류가 발생했습니다:\n{result}")
            self.btn_install.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())
