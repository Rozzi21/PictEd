import os
import sys
import traceback
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMessageBox, QScrollArea, QFrame,
    QProgressDialog
)
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QWheelEvent
from PySide6.QtCore import Qt, QRect, QPoint, QThread, Signal
from PIL import Image, ImageEnhance, ImageFilter

base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
models_dir = os.path.join(base_dir, 'models')
if os.path.exists(models_dir):
    os.environ['U2NET_HOME'] = models_dir

import onnxruntime as ort
from rembg import new_session, remove

STYLESHEET = """
QMainWindow {
    background-color: #0a0f1e;
}

QWidget {
    font-family: 'Segoe UI', 'Inter', sans-serif;
    color: #dbe4ff;
    font-size: 13px;
}

/* ---------- Sidebar ---------- */

QFrame#sidebar {
    background-color: #101828;
    border-right: 1px solid #1f2a44;
}

QLabel#app_logo {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
}

QLabel#app_subtitle {
    font-size: 11px;
    color: #6b7a9d;
    margin-bottom: 4px;
}

QFrame#divider {
    background-color: #1f2a44;
    max-height: 1px;
    margin: 6px 0px;
}

QLabel#sidebar_header {
    font-size: 10px;
    font-weight: 700;
    color: #5f7199;
    letter-spacing: 2px;
    margin-top: 14px;
    margin-bottom: 2px;
}

/* ---------- Buttons ---------- */

QPushButton {
    background-color: #182338;
    color: #dbe4ff;
    border: 1px solid #26334f;
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}

QPushButton:hover {
    background-color: #22314f;
    border-color: #3d5a99;
}

QPushButton:pressed {
    background-color: #141d31;
    border-color: #26334f;
}

QPushButton:disabled {
    background-color: #131b2c;
    color: #4a5570;
    border-color: #1c2436;
}

QPushButton#btn_primary {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6366f1, stop:1 #4f46e5);
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#btn_primary:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #818cf8, stop:1 #6366f1);
}

QPushButton#btn_primary:pressed {
    background-color: #4338ca;
}

QPushButton#btn_accent {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #22d3ee, stop:1 #0ea5e9);
    color: #03293d;
    border: none;
    font-weight: 600;
}

QPushButton#btn_accent:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #67e8f9, stop:1 #38bdf8);
}

QPushButton#btn_accent:pressed {
    background-color: #0284c7;
    color: #ffffff;
}

QPushButton#btn_danger {
    background-color: rgba(239, 68, 68, 0.12);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.45);
}

QPushButton#btn_danger:hover {
    background-color: rgba(239, 68, 68, 0.28);
    color: #fecaca;
    border-color: #ef4444;
}

QPushButton#btn_danger:pressed {
    background-color: #991b1b;
    color: #ffffff;
}

/* ---------- Canvas area ---------- */

QScrollArea {
    background-color: #070c18;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #070c18;
}

QLabel#canvas {
    color: #3d4a68;
    font-size: 15px;
}

/* ---------- Scrollbars ---------- */

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}

QScrollBar::handle:vertical {
    background: #26334f;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #3b4a6b;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px;
}

QScrollBar::handle:horizontal {
    background: #26334f;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #3b4a6b;
}

QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}

/* ---------- Info & status ---------- */

QLabel#info_label {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 11px;
    color: #8ea2c9;
    background-color: #0c1426;
    border: 1px solid #1f2a44;
    border-radius: 10px;
    padding: 10px;
}

QStatusBar {
    background-color: #101828;
    color: #6b7a9d;
    border-top: 1px solid #1f2a44;
    font-size: 11px;
    padding: 2px 8px;
}

QStatusBar::item {
    border: none;
}

/* ---------- Dialogs & tooltips ---------- */

QToolTip {
    background-color: #182338;
    color: #dbe4ff;
    border: 1px solid #2d3a5c;
    border-radius: 6px;
    padding: 5px 8px;
}

QProgressDialog {
    background-color: #101828;
    color: #dbe4ff;
}

QProgressBar {
    background-color: #0c1426;
    border: 1px solid #1f2a44;
    border-radius: 6px;
    text-align: center;
    color: #dbe4ff;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:1 #22d3ee);
    border-radius: 5px;
}

QMessageBox {
    background-color: #101828;
    color: #dbe4ff;
}

QMessageBox QPushButton {
    min-width: 80px;
    text-align: center;
}

QFileDialog {
    background-color: #101828;
    color: #dbe4ff;
}
"""

class RemoveBgThread(QThread):
    finished_signal = Signal(object)
    error_signal = Signal(str)
    status_signal = Signal(str)

    _session = None

    def __init__(self, pil_image):
        super().__init__()
        self.pil_image = pil_image

    def run(self):
        try:
            if RemoveBgThread._session is None:
                self.status_signal.emit("Loading AI model...")
                session_options = ort.SessionOptions()
                session_options.intra_op_num_threads = min(4, max(1, (os.cpu_count() or 2) - 1))
                session_options.inter_op_num_threads = 1
                session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                RemoveBgThread._session = new_session(
                    "bria-rmbg",
                    sess_opts=session_options,
                    providers=["CPUExecutionProvider"],
                )

            self.status_signal.emit("Removing background...")
            result = remove(self.pil_image, session=RemoveBgThread._session)
            self.finished_signal.emit(result)
        except Exception:
            self.error_signal.emit(traceback.format_exc())

class ImageCanvas(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False
        self.crop_rect = QRect()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap() and not self.pixmap().isNull():
            self.start_point = event.position().toPoint()
            self.end_point = self.start_point
            self.is_selecting = True
            self.crop_rect = QRect()
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.end_point = event.position().toPoint()
            self.is_selecting = False
            self.crop_rect = QRect(self.start_point, self.end_point).normalized()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap() or self.pixmap().isNull():
            return

        painter = QPainter(self)
        if self.is_selecting or not self.crop_rect.isEmpty():
            current_rect = QRect(self.start_point, self.end_point).normalized() if self.is_selecting else self.crop_rect
            pen = QPen(QColor("#c3c0ff"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(current_rect)
            painter.fillRect(current_rect, QColor(195, 192, 255, 40))

    def reset_selection(self):
        self.crop_rect = QRect()
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.update()

class PhotoEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PictEd — Photo Editor")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self.pil_image = None
        self.original_image = None
        self.zoom_factor = 1.0
        self.remove_bg_thread = None
        self.remove_bg_progress = None

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(8)

        app_logo = QLabel("🎨 PictEd")
        app_logo.setObjectName("app_logo")

        app_subtitle = QLabel("Simple AI-powered photo editor")
        app_subtitle.setObjectName("app_subtitle")

        logo_divider = QFrame()
        logo_divider.setObjectName("divider")

        lbl_file = QLabel("FILE")
        lbl_file.setObjectName("sidebar_header")

        btn_open = QPushButton("📂  Open Image")
        btn_open.setObjectName("btn_primary")
        btn_open.setToolTip("Open an image file (PNG, JPG, BMP, WebP)")
        btn_open.clicked.connect(self.open_image)

        btn_save = QPushButton("💾  Save Image")
        btn_save.setObjectName("btn_accent")
        btn_save.setToolTip("Save the edited image")
        btn_save.clicked.connect(self.save_image)

        lbl_tools = QLabel("TOOLS && EDITS")
        lbl_tools.setObjectName("sidebar_header")

        btn_crop = QPushButton("✂️  Crop Selection")
        btn_crop.setToolTip("Click and drag on the image, then crop")
        btn_crop.clicked.connect(self.crop_image)

        btn_flip_h = QPushButton("↔️  Flip Horizontal")
        btn_flip_h.clicked.connect(self.flip_horizontal)

        btn_flip_v = QPushButton("↕️  Flip Vertical")
        btn_flip_v.clicked.connect(self.flip_vertical)

        upscale_btn_layout = QHBoxLayout()
        upscale_btn_layout.setSpacing(8)
        btn_upscale_2x = QPushButton("⬆️ 2x")
        btn_upscale_2x.setToolTip("Upscale image 2x")
        btn_upscale_2x.clicked.connect(self.upscale_2x)
        btn_upscale_4x = QPushButton("⬆️ 4x")
        btn_upscale_4x.setToolTip("Upscale image 4x")
        btn_upscale_4x.clicked.connect(self.upscale_4x)
        upscale_btn_layout.addWidget(btn_upscale_2x)
        upscale_btn_layout.addWidget(btn_upscale_4x)

        btn_enhance = QPushButton("✨  Enhance Quality")
        btn_enhance.setToolTip("Boost sharpness, contrast, and detail")
        btn_enhance.clicked.connect(self.enhance_quality)

        btn_grayscale = QPushButton("🩶  Grayscale")
        btn_grayscale.clicked.connect(self.to_grayscale)

        self.btn_remove_bg = QPushButton("🪄  Remove Background")
        self.btn_remove_bg.setToolTip("AI background removal (bria-rmbg)")
        self.btn_remove_bg.clicked.connect(self.remove_background)

        lbl_view = QLabel("VIEW && VIEWPORT")
        lbl_view.setObjectName("sidebar_header")

        zoom_btn_layout = QHBoxLayout()
        zoom_btn_layout.setSpacing(8)
        btn_zoom_in = QPushButton("🔍 +")
        btn_zoom_in.setToolTip("Zoom in (or scroll up)")
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out = QPushButton("🔍 −")
        btn_zoom_out.setToolTip("Zoom out (or scroll down)")
        btn_zoom_out.clicked.connect(self.zoom_out)
        zoom_btn_layout.addWidget(btn_zoom_in)
        zoom_btn_layout.addWidget(btn_zoom_out)

        btn_zoom_reset = QPushButton("⤢  Reset Zoom (100%)")
        btn_zoom_reset.clicked.connect(self.reset_zoom)

        lbl_history = QLabel("RESET")
        lbl_history.setObjectName("sidebar_header")

        btn_reset = QPushButton("↺  Reset to Original")
        btn_reset.setObjectName("btn_danger")
        btn_reset.setToolTip("Discard all edits")
        btn_reset.clicked.connect(self.reset_image)

        self.info_label = QLabel("Dimension: -\nZoom: 100%")
        self.info_label.setObjectName("info_label")

        sidebar_layout.addWidget(app_logo)
        sidebar_layout.addWidget(app_subtitle)
        sidebar_layout.addWidget(logo_divider)

        sidebar_layout.addWidget(lbl_file)
        sidebar_layout.addWidget(btn_open)
        sidebar_layout.addWidget(btn_save)

        sidebar_layout.addWidget(lbl_tools)
        sidebar_layout.addWidget(btn_crop)
        sidebar_layout.addWidget(btn_flip_h)
        sidebar_layout.addWidget(btn_flip_v)
        sidebar_layout.addLayout(upscale_btn_layout)
        sidebar_layout.addWidget(btn_enhance)
        sidebar_layout.addWidget(btn_grayscale)
        sidebar_layout.addWidget(self.btn_remove_bg)

        sidebar_layout.addWidget(lbl_view)
        sidebar_layout.addLayout(zoom_btn_layout)
        sidebar_layout.addWidget(btn_zoom_reset)

        sidebar_layout.addWidget(lbl_history)
        sidebar_layout.addWidget(btn_reset)

        sidebar_layout.addSpacing(16)
        sidebar_layout.addWidget(self.info_label)

        self.canvas = ImageCanvas()
        self.canvas.setObjectName("canvas")
        self.canvas.setText("🖼️\n\nNo image loaded\n\nOpen an image to start editing\nDrag on the image to select a crop area")
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.canvas)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.scroll_area)

        self.statusBar().showMessage("Ready — no image loaded")

    def wheelEvent(self, event: QWheelEvent):
        if self.pil_image:
            angle = event.angleDelta().y()
            if angle > 0:
                self.zoom_in()
            elif angle < 0:
                self.zoom_out()

    def update_display(self):
        if self.pil_image is None:
            return

        w, h = self.pil_image.size
        zoom_pct = int(self.zoom_factor * 100)
        self.info_label.setText(f"Dimension:\n{w} x {h} px\nZoom: {zoom_pct}%")

        disp_w = int(w * self.zoom_factor)
        disp_h = int(h * self.zoom_factor)

        img = self.pil_image.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, w, h, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)

        scaled_pixmap = pixmap.scaled(
            disp_w, disp_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.canvas.setPixmap(scaled_pixmap)
        self.canvas.setFixedSize(disp_w, disp_h)
        self.canvas.reset_selection()

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            self.original_image = Image.open(file_path).convert("RGB")
            self.pil_image = self.original_image.copy()
            self.zoom_factor = 1.0
            self.update_display()
            self.statusBar().showMessage(f"Opened: {os.path.basename(file_path)}")

    def crop_image(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        rect = self.canvas.crop_rect
        if rect.isEmpty() or rect.width() < 5 or rect.height() < 5:
            QMessageBox.warning(self, "Warning", "Please click and drag to select crop area first!")
            return

        w, h = self.pil_image.size
        pixmap = self.canvas.pixmap()
        if not pixmap:
            return

        scale_x = w / pixmap.width()
        scale_y = h / pixmap.height()

        left = int(rect.left() * scale_x)
        top = int(rect.top() * scale_y)
        right = int(rect.right() * scale_x)
        bottom = int(rect.bottom() * scale_y)

        left = max(0, min(left, w))
        top = max(0, min(top, h))
        right = max(left + 1, min(right, w))
        bottom = max(top + 1, min(bottom, h))

        self.pil_image = self.pil_image.crop((left, top, right, bottom))
        self.update_display()

    def flip_horizontal(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return
        self.pil_image = self.pil_image.transpose(Image.FLIP_LEFT_RIGHT)
        self.update_display()

    def flip_vertical(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return
        self.pil_image = self.pil_image.transpose(Image.FLIP_TOP_BOTTOM)
        self.update_display()

    def upscale_image(self, factor: float):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        w, h = self.pil_image.size
        if w == 0 or h == 0:
            return

        target_width = int(w * factor)
        target_height = int(h * factor)
        self.pil_image = self.pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        self.update_display()
        QMessageBox.information(self, f"Upscale {factor:g}x", f"Resized to {target_width}x{target_height}")

    def upscale_2x(self):
        self.upscale_image(2.0)

    def upscale_4x(self):
        self.upscale_image(4.0)

    def enhance_quality(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        enhancer = ImageEnhance.Sharpness(self.pil_image)
        img_sharp = enhancer.enhance(1.5)

        enhancer = ImageEnhance.Contrast(img_sharp)
        img_contrast = enhancer.enhance(1.15)

        enhancer = ImageEnhance.Color(img_contrast)
        img_enhanced = enhancer.enhance(1.1)

        self.pil_image = img_enhanced.filter(ImageFilter.DETAIL)
        self.update_display()
        QMessageBox.information(self, "Enhance Quality", "Image sharpness, contrast, and detail enhanced!")

    def zoom_in(self):
        if not self.pil_image:
            return
        if self.zoom_factor < 5.0:
            self.zoom_factor = round(self.zoom_factor + 0.15, 2)
            self.update_display()

    def zoom_out(self):
        if not self.pil_image:
            return
        if self.zoom_factor > 0.15:
            self.zoom_factor = round(self.zoom_factor - 0.15, 2)
            self.update_display()

    def reset_zoom(self):
        if not self.pil_image:
            return
        self.zoom_factor = 1.0
        self.update_display()

    def to_grayscale(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        self.pil_image = self.pil_image.convert("L").convert("RGB")
        self.update_display()

    def remove_background(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        if self.remove_bg_thread and self.remove_bg_thread.isRunning():
            return

        self.btn_remove_bg.setEnabled(False)
        self.remove_bg_progress = QProgressDialog(
            "Preparing background removal...", None, 0, 0, self
        )
        self.remove_bg_progress.setWindowTitle("PictEd")
        self.remove_bg_progress.setWindowModality(Qt.NonModal)
        self.remove_bg_progress.setCancelButton(None)
        self.remove_bg_progress.setMinimumDuration(0)
        self.remove_bg_progress.show()
        self.statusBar().showMessage("Removing background…")

        self.remove_bg_thread = RemoveBgThread(self.pil_image.copy())

        def on_finished(result_img):
            self.remove_bg_progress.close()
            self.pil_image = result_img
            self.update_display()
            self.statusBar().showMessage("Background removed ✓")
            QMessageBox.information(self, "Remove Background", "Background removed successfully!")

        def on_error(err_msg):
            self.remove_bg_progress.close()
            self.statusBar().showMessage("Background removal failed")
            QMessageBox.critical(self, "Error", f"Failed to remove background: {err_msg}")

        def on_thread_finished():
            self.btn_remove_bg.setEnabled(True)
            self.remove_bg_thread.deleteLater()
            self.remove_bg_thread = None
            self.remove_bg_progress = None

        self.remove_bg_thread.status_signal.connect(self.remove_bg_progress.setLabelText)
        self.remove_bg_thread.finished_signal.connect(on_finished)
        self.remove_bg_thread.error_signal.connect(on_error)
        self.remove_bg_thread.finished.connect(on_thread_finished)
        self.remove_bg_thread.start()

    def closeEvent(self, event):
        if self.remove_bg_thread and self.remove_bg_thread.isRunning():
            QMessageBox.warning(
                self,
                "Background Removal in Progress",
                "Wait until background removal finishes before closing PictEd.",
            )
            event.ignore()
            return
        event.accept()

    def reset_image(self):
        if not self.original_image:
            return
        self.pil_image = self.original_image.copy()
        self.update_display()

    def save_image(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "output.png", "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        if file_path:
            self.pil_image.save(file_path)
            self.statusBar().showMessage(f"Saved: {file_path}")
            QMessageBox.information(self, "Saved", f"Saved to {file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PictEd")
    app.setStyleSheet(STYLESHEET)
    window = PhotoEditor()
    window.show()
    sys.exit(app.exec())

