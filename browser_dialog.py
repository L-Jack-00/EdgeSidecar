import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QPushButton
)
from PyQt6.QtGui import QFont, QIcon
from config import BASE_DIR
from browser_detector import scan_all_browsers, set_browser_selection, load_settings

class BrowserSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 사용할 브라우저 엔진 선택")
        self.setFixedSize(490, 380)

        # Apply application icon if available
        for cand in [BASE_DIR / "app.ico", Path(sys.executable).parent / "app.ico", Path(__file__).parent / "app.ico"]:
            if cand.exists():
                self.setWindowIcon(QIcon(str(cand)))
                break

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
                padding: 10px 22px;
                border-radius: 6px;
                font-size: 13px;
                cursor: pointer;
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

        desc = QLabel(
            "내 컴퓨터에 설치된 브라우저 중 사이드카와 연결할 엔진을 선택해 주세요.\n"
            "(나중에 언제든 대시보드의 '⚙️ 브라우저 엔진 & 보안 관리' 탭에서 변경할 수 있습니다)"
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
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

            # Pre-select Edge if installed, otherwise first available installed browser
            if b["installed"]:
                if b["id"] == "edge" or first_installed is None:
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
        selected_id = "edge"
        for bid, rb in self.radios.items():
            if rb.isChecked():
                selected_id = bid
                break
        set_browser_selection(selected_id)
        self.accept()

def prompt_first_run_browser_selection():
    """Checks if the user has configured a browser on first run. If not, shows modal dialog."""
    settings = load_settings()
    if not settings.get("has_configured_browser", False):
        try:
            app = QApplication.instance()
            own_app = False
            if app is None:
                app = QApplication(sys.argv)
                own_app = True

            dlg = BrowserSelectDialog()
            dlg.exec()

            if own_app:
                app.quit()
        except Exception as e:
            print(f"[FirstRun] Browser selection prompt error: {e}")
