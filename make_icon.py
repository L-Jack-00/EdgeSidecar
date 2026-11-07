import os
import struct
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPainterPath
from PyQt6.QtCore import Qt, QByteArray, QBuffer

app = QApplication(sys.argv)

sizes = [16, 24, 32, 48, 64, 128, 256]
png_data_list = []

for s in sizes:
    img = QImage(s, s, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = max(1.0, s * 0.06)
    w = s - 2 * margin
    h = s - 2 * margin

    # Gradient background
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0.0, QColor("#38bdf8"))  # Cyan / Light Sky Blue
    grad.setColorAt(0.5, QColor("#0ea5e9"))  # Sky Blue
    grad.setColorAt(1.0, QColor("#1d4ed8"))  # Deep Blue

    # Shield geometry
    path = QPainterPath()
    path.moveTo(s / 2, margin)
    path.lineTo(s - margin, margin + h * 0.22)
    path.quadTo(s - margin, margin + h * 0.72, s / 2, s - margin)
    path.quadTo(margin, margin + h * 0.72, margin, margin + h * 0.22)
    path.closeSubpath()

    p.fillPath(path, QBrush(grad))

    # Clean Shield Inner Border
    border_pen = QPen(QColor(255, 255, 255, 230), max(1.0, s * 0.05))
    p.strokePath(path, border_pen)

    # Stylized "E" in the center
    p.setPen(QColor("#ffffff"))
    font_size = int(s * 0.46)
    font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, "E")
    p.end()

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    png_data_list.append((s, bytes(ba)))

# Compose standard Windows ICO format
header = struct.pack("<HHH", 0, 1, len(sizes))
offset = 6 + 16 * len(sizes)
entries = b""
images = b""

for s, data in png_data_list:
    w = 0 if s == 256 else s
    h = 0 if s == 256 else s
    size = len(data)
    entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, size, offset)
    entries += entry
    images += data
    offset += size

out_path = "app.ico"
with open(out_path, "wb") as f:
    f.write(header + entries + images)

print(f"app.ico generated successfully at {out_path} ({os.path.getsize(out_path)} bytes)")
