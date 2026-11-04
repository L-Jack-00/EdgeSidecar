import asyncio
import os
import sys
import threading
import webbrowser
from pathlib import Path

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QActionGroup
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout,
    QHBoxLayout, QLabel, QRadioButton, QPushButton, QMessageBox
)

from config import PROXY_PORT, BASE_DIR
from harness_core import supervisor, HarnessState
from browser_detector import scan_all_browsers, set_browser_selection, load_settings, resolve_selected_browser
import sidecar_app

def create_shield_icon() -> QIcon:
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

class BrowserSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 기본 브라우저 엔진 선택")
        self.setFixedSize(480, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLabel { color: #f8fafc; font-size: 13px; }
            QRadioButton {
                color: #f8fafc;
                font-size: 13px;
                padding: 6px;
                spacing: 8px;
            }
            QRadioButton::indicator { width: 16px; height: 16px; }
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
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(14)

        title = QLabel("🌐 사용할 브라우저 엔진 선택")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        desc = QLabel("내 컴퓨터에 설치된 브라우저 중 사이드카와 연결할 엔진을 선택해 주세요.\n(나중에 언제든 대시보드나 트레이 메뉴에서 변경할 수 있습니다)")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(desc)

        self.radios = {}
        browsers = scan_all_browsers()
        first_installed = None

        for b in browsers:
            status_text = " (설치됨)" if b["installed"] else " [미설치]"
            label = f"{b['name']}{status_text}"
            rb = QRadioButton(label)
            rb.setEnabled(b["installed"])
            if not b["installed"]:
                rb.setStyleSheet("color: #64748b;")

            if b["installed"] and first_installed is None:
                first_installed = b["id"]
                rb.setChecked(True)

            self.radios[b["id"]] = rb
            layout.addWidget(rb)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_ok = QPushButton("선택 완료 및 시작 ➔")
        btn_ok.clicked.connect(self.on_confirm)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)

        self.setLayout(layout)

    def on_confirm(self):
        selected_id = "auto"
        for bid, rb in self.radios.items():
            if rb.isChecked():
                selected_id = bid
                break
        set_browser_selection(selected_id)
        self.accept()

class SystemTrayApp(QObject):
    quit_signal = pyqtSignal()

    def __init__(self, profile_name: str = "default"):
        super().__init__()
        self.profile_name = profile_name
        self.app = QApplication(sys.argv)
        self.quit_signal.connect(self.exit_app)

        # Check first launch browser configuration
        settings = load_settings()
        if not settings.get("has_configured_browser", False):
            dlg = BrowserSelectDialog()
            dlg.exec()

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(create_shield_icon())
        self.update_tray_tooltip()

        self.create_menu()
        self.tray.activated.connect(self.on_tray_activated)

        # Start Sidecar Async Engine in background daemon thread
        self.engine_thread = threading.Thread(target=self.run_engine, daemon=True)
        self.engine_thread.start()

    def update_tray_tooltip(self):
        try:
            _, bname = resolve_selected_browser()
        except Exception:
            bname = "Chromium"
        self.tray.setToolTip(f"Edge Sidecar Browser ({bname})")

    def create_menu(self):
        menu = QMenu()

        act_dashboard = QAction("🛡️ 대시보드 콘솔 열기", menu)
        act_dashboard.triggered.connect(self.open_dashboard)
        menu.addAction(act_dashboard)

        act_store = QAction("🧩 크롬 웹스토어 열기", menu)
        act_store.triggered.connect(self.open_store)
        menu.addAction(act_store)

        menu.addSeparator()

        # Submenu: Change Browser Engine
        engine_menu = QMenu("🌐 브라우저 엔진 변경", menu)
        group = QActionGroup(engine_menu)
        group.setExclusive(True)

        settings = load_settings()
        current_sel = settings.get("selected_browser", "auto")
        browsers = scan_all_browsers()

        for b in browsers:
            status_suffix = " (사용 가능)" if b["installed"] else " [미설치]"
            action = QAction(f"{b['name']}{status_suffix}", engine_menu, checkable=True)
            action.setEnabled(b["installed"])
            if b["id"] == current_sel or (current_sel == "auto" and b["installed"] and not any(a.isChecked() for a in group.actions())):
                action.setChecked(True)
            action.triggered.connect(lambda checked, bid=b["id"]: self.change_engine(bid))
            group.addAction(action)
            engine_menu.addAction(action)

        menu.addMenu(engine_menu)

        act_swap = QAction("🚀 최신 포터블 크로뮴 확인 및 교체", menu)
        act_swap.triggered.connect(self.open_dashboard)
        menu.addAction(act_swap)

        menu.addSeparator()

        self.act_pause = QAction("⏸️ 패킷 통제 일시정지", menu)
        self.act_pause.triggered.connect(self.toggle_pause)
        menu.addAction(self.act_pause)

        act_folder = QAction("📁 프로필 데이터 폴더 열기", menu)
        act_folder.triggered.connect(self.open_folder)
        menu.addAction(act_folder)

        menu.addSeparator()

        act_exit = QAction("❌ 브라우저 및 사이드카 종료", menu)
        act_exit.triggered.connect(self.exit_app)
        menu.addAction(act_exit)

        self.tray.setContextMenu(menu)

    def change_engine(self, browser_id: str):
        set_browser_selection(browser_id)
        self.update_tray_tooltip()
        QMessageBox.information(
            None,
            "엔진 변경 완료",
            "브라우저 엔진 설정이 변경되었습니다.\n\n다음에 브라우저를 다시 실행할 때 선택하신 엔진으로 구동됩니다."
        )

    def run_engine(self):
        try:
            asyncio.run(sidecar_app.main(self.profile_name))
        except Exception as e:
            print(f"[TrayApp] Engine thread exited: {e}")
        finally:
            # Emit signal to main GUI thread for clean complete shutdown
            self.quit_signal.emit()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_dashboard()

    def open_dashboard(self):
        webbrowser.open(f"http://127.0.0.1:{PROXY_PORT}/dashboard")

    def open_store(self):
        webbrowser.open("https://chromewebstore.google.com")

    def toggle_pause(self):
        if supervisor.state == HarnessState.PAUSED:
            supervisor.resume()
            self.act_pause.setText("⏸️ 패킷 통제 일시정지")
        else:
            supervisor.pause()
            self.act_pause.setText("▶️ 패킷 통제 재개")

    def open_folder(self):
        os.startfile(str(BASE_DIR))

    def exit_app(self):
        supervisor.emergency_stop()
        if hasattr(self, "tray") and self.tray is not None:
            self.tray.hide()
            self.tray.deleteLater()
        self.app.quit()
        # Safety net: ensure completely killed after 0.5s if any thread hangs
        threading.Timer(0.5, lambda: os._exit(0)).start()

    def run(self):
        self.tray.show()
        return self.app.exec()

if __name__ == "__main__":
    profile = "default"
    for arg in sys.argv[1:]:
        if arg in ("default", "developer", "isolated"):
            profile = arg
    app = SystemTrayApp(profile_name=profile)
    sys.exit(app.run())
