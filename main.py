import os
import sys
import shutil
import subprocess
import tempfile
import traceback
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMessageBox, QScrollArea, QFrame,
    QProgressDialog, QInputDialog, QColorDialog, QSlider, QButtonGroup,
    QToolButton, QSizePolicy
)
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QWheelEvent, QAction
)
from PySide6.QtCore import Qt, QRect, QPoint, QThread, Signal
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
models_dir = os.path.join(base_dir, 'models')
if os.path.exists(models_dir):
    os.environ['U2NET_HOME'] = models_dir

import onnxruntime as ort
from rembg import new_session, remove

STYLESHEET = """
QMainWindow {
    background-color: #111315;
}

QWidget {
    font-family: 'Segoe UI', sans-serif;
    color: #e6e8e7;
    font-size: 13px;
}

/* ---------- Sidebar ---------- */

QFrame#sidebar {
    background-color: #191c1e;
    border-left: 1px solid #303537;
}

QLabel#app_logo {
    font-size: 22px;
    font-weight: 800;
    color: #f2f4f3;
    letter-spacing: 1px;
}

QLabel#app_subtitle {
    font-size: 11px;
    color: #87918f;
    margin-bottom: 2px;
    letter-spacing: 0.5px;
}

QFrame#divider {
    background-color: #303537;
    max-height: 1px;
    margin: 8px 0px;
}

QLabel#sidebar_header {
    font-size: 10px;
    font-weight: 700;
    color: #8b9694;
    letter-spacing: 2.5px;
    margin-top: 16px;
    margin-bottom: 4px;
}

/* ---------- Buttons ---------- */

QPushButton {
    background-color: #252a2c;
    color: #dfe4e2;
    border: 1px solid #3b4244;
    border-radius: 6px;
    padding: 8px 11px;
    font-size: 12px;
    font-weight: 500;
    text-align: left;
}

QPushButton:hover {
    background-color: #303739;
    border-color: #697573;
}

QPushButton:pressed {
    background-color: #1c2021;
    border-color: #53605d;
}

QPushButton:checked {
    background-color: #2c7774;
    color: #ffffff;
    border-color: #55aaa0;
}

QPushButton:disabled {
    background-color: #131b2c;
    color: #4a5570;
    border-color: #1c2436;
}

QPushButton#btn_primary {
    background-color: #2d7773;
    color: #ffffff;
    border: 1px solid #4da69d;
    border-radius: 6px;
    font-weight: 600;
    padding: 10px 12px;
    text-align: center;
}

QPushButton#btn_primary:hover {
    background-color: #378e88;
}

QPushButton#btn_primary:pressed {
    background-color: #215d5a;
}

QPushButton#btn_accent {
    background-color: #d7a34f;
    color: #21190d;
    border: 1px solid #efc16e;
    border-radius: 6px;
    font-weight: 600;
    padding: 10px 12px;
    text-align: center;
}

QPushButton#btn_accent:hover {
    background-color: #e5b563;
}

QPushButton#btn_accent:pressed {
    background-color: #a6762d;
    color: #ffffff;
}

QPushButton#btn_danger {
    background-color: rgba(239, 68, 68, 0.12);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.45);
    border-radius: 8px;
    padding: 9px 12px;
    text-align: center;
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

/* ---------- Menu bar ---------- */

QMenuBar {
    background-color: #191c1e;
    color: #dfe4e2;
    border-bottom: 1px solid #303537;
    font-size: 12px;
    padding: 3px 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 13px;
    border-radius: 6px;
}

QMenuBar::item:selected {
    background-color: #24365a;
}

QMenuBar::item:pressed {
    background-color: #16233a;
}

QMenu {
    background-color: #202426;
    color: #dbe4ff;
    border: 1px solid #3b4244;
    border-radius: 8px;
    padding: 5px;
}

QMenu::item {
    padding: 6px 24px 6px 16px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #24365a;
}

QMenu::item:disabled {
    color: #4a5570;
}

QMenu::separator {
    height: 1px;
    background: #1e2a45;
    margin: 4px 8px;
}

/* ---------- Toolbar (CorelDRAW-like tool column) ---------- */

QFrame#toolbar {
    background-color: #17191a;
    border-right: 1px solid #303537;
}

QFrame#toolbar QPushButton {
    background-color: #222728;
    color: #dbe4ff;
    border: 1px solid #363d3e;
    border-radius: 7px;
    padding: 0px;
    font-size: 11px;
    font-weight: 600;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    text-align: center;
    margin-bottom: 6px;
}

QFrame#toolbar QPushButton:hover {
    background-color: #24365a;
    border-color: #4260a3;
}

QFrame#toolbar QPushButton:checked {
    background-color: #2d7773;
    color: #ffffff;
    border-color: #55aaa0;
}

QFrame#toolbar QPushButton#btn_danger {
    background-color: rgba(239, 68, 68, 0.12);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.45);
}

QFrame#toolbar QPushButton#btn_danger:hover {
    background-color: rgba(239, 68, 68, 0.28);
    color: #fecaca;
    border-color: #ef4444;
}

QFrame#toolbar QPushButton#tool_text {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QFrame#toolbar QScrollArea {
    background: transparent;
    border: none;
}

QFrame#toolbar QScrollArea > QWidget > QWidget {
    background: transparent;
}

QFrame#tool_divider {
    background-color: #303537;
    min-height: 1px;
    max-height: 1px;
    margin: 6px 4px;
}

QFrame#context_bar {
    background-color: #191c1e;
    border-bottom: 1px solid #303537;
}

QLabel#workspace_label {
    color: #b8c2bf;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}

QLabel#context_hint {
    color: #727d7a;
    font-size: 11px;
}


/* ---------- Canvas area ---------- */

QScrollArea {
    background-color: #0d0f10;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #0d0f10;
}

QLabel#canvas {
    color: #7b8583;
    font-size: 15px;
}

/* ---------- Scrollbars ---------- */

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}

QScrollBar::handle:vertical {
    background: #2a3a5c;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #4260a3;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px;
}

QScrollBar::handle:horizontal {
    background: #2a3a5c;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #4260a3;
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
    color: #9da9a5;
    background-color: #141718;
    border: 1px solid #303637;
    border-radius: 10px;
    padding: 12px;
}

QStatusBar {
    background-color: #191c1e;
    color: #87918f;
    border-top: 1px solid #303537;
    font-size: 11px;
    padding: 3px 10px;
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

QSlider::groove:horizontal {
    height: 6px;
    background: #0c1426;
    border: 1px solid #1f2a44;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:1 #22d3ee);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #dbe4ff;
    border: 2px solid #6366f1;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #ffffff;
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
    draw_started = Signal(QPoint)
    draw_moved = Signal(QPoint, QPoint)
    draw_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False
        self.crop_rect = QRect()
        self.tool = "select"
        self.is_drawing = False
        self.last_draw_point = QPoint()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self.pixmap() or self.pixmap().isNull():
            return

        if self.tool in ("brush", "eraser"):
            self.is_drawing = True
            self.last_draw_point = event.position().toPoint()
            self.draw_started.emit(self.last_draw_point)
            return

        self.start_point = event.position().toPoint()
        self.end_point = self.start_point
        self.is_selecting = True
        self.crop_rect = QRect()
        self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            current = event.position().toPoint()
            self.draw_moved.emit(self.last_draw_point, current)
            self.last_draw_point = current
            return

        if self.is_selecting:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            self.draw_finished.emit()
            return

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
    SAVE_OPTIONS = {
        "PNG": {"optimize": True},
        "JPEG": {"quality": 95, "optimize": True},
        "WEBP": {"quality": 92, "method": 6},
        "AVIF": {"quality": 75},
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PictEd — Photo Editor")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self.pil_image = None
        self.original_image = None
        self.current_path = None
        self.last_dir = None
        self.zoom_factor = 1.0
        self.tool = "select"
        self.brush_color = QColor("#ff3b30")
        self.brush_size = 20
        self.remove_bg_thread = None
        self.remove_bg_progress = None

        self.init_ui()

    def _make_tool_button(self, text, tooltip, callback=None, checkable=False, object_name=None):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        if object_name:
            btn.setObjectName(object_name)
        if callback:
            btn.clicked.connect(callback)
        return btn

    def _tool_divider(self):
        d = QFrame()
        d.setObjectName("tool_divider")
        return d

    def init_ui(self):
        self._create_menu_bar()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- Icon tool column (left) ----
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedWidth(56)
        toolbar_outer = QVBoxLayout(toolbar)
        toolbar_outer.setContentsMargins(0, 0, 0, 0)
        toolbar_outer.setSpacing(0)

        tool_scroll = QScrollArea()
        tool_scroll.setWidgetResizable(True)
        tool_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tool_scroll.setFrameShape(QFrame.NoFrame)

        tool_inner = QWidget()
        toolbar_layout = QVBoxLayout(tool_inner)
        toolbar_layout.setAlignment(Qt.AlignTop)
        toolbar_layout.setContentsMargins(8, 10, 8, 10)
        toolbar_layout.setSpacing(0)
        tool_scroll.setWidget(tool_inner)
        toolbar_outer.addWidget(tool_scroll)

        # Selection / paint tools (exclusive group)
        self.btn_select_tool = self._make_tool_button(
            "↖", "Select / Crop — drag on the image to select an area",
            lambda: self.set_tool("select"), checkable=True)
        self.btn_select_tool.setChecked(True)
        self.btn_brush = self._make_tool_button(
            "✎", "Brush — paint with the selected color and size",
            lambda: self.set_tool("brush"), checkable=True)
        self.btn_eraser = self._make_tool_button(
            "⌫", "Eraser — erase parts of the image (becomes transparent)",
            lambda: self.set_tool("eraser"), checkable=True)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        for tool_btn in (self.btn_select_tool, self.btn_brush, self.btn_eraser):
            self.tool_group.addButton(tool_btn)
            toolbar_layout.addWidget(tool_btn)

        toolbar_layout.addWidget(self._tool_divider())

        # Transform / edit tools
        btn_crop = self._make_tool_button("◲", "Crop the selected area", self.crop_image)
        btn_flip_h = self._make_tool_button("↔", "Flip Horizontal", self.flip_horizontal)
        btn_flip_v = self._make_tool_button("↕", "Flip Vertical", self.flip_vertical)
        btn_upscale_2x = self._make_tool_button("2×", "Upscale image 2x", self.upscale_2x)
        btn_upscale_4x = self._make_tool_button("4×", "Upscale image 4x", self.upscale_4x)
        btn_enhance = self._make_tool_button("✦", "Enhance sharpness, contrast, and detail", self.enhance_quality)
        btn_grayscale = self._make_tool_button("◐", "Grayscale", self.to_grayscale)
        self.btn_remove_bg = self._make_tool_button("✂", "AI background removal (bria-rmbg)", self.remove_background)
        for b in (btn_crop, btn_flip_h, btn_flip_v, btn_upscale_2x,
                  btn_upscale_4x, btn_enhance, btn_grayscale, self.btn_remove_bg):
            toolbar_layout.addWidget(b)

        toolbar_layout.addWidget(self._tool_divider())

        # Convert format tools
        btn_convert_png = self._make_tool_button("PNG", "Export as PNG (lossless, keeps alpha)",
                                                 lambda: self.convert_format("PNG"), object_name="tool_text")
        btn_convert_webp = self._make_tool_button("WEBP", "Export as WebP (quality 92, keeps alpha)",
                                                  lambda: self.convert_format("WEBP"), object_name="tool_text")
        btn_convert_avif = self._make_tool_button("AVIF", "Export as AVIF (quality 75, keeps alpha)",
                                                  lambda: self.convert_format("AVIF"), object_name="tool_text")
        btn_convert_webm = self._make_tool_button("WEBM", "Render as short VP9 WebM video (requires ffmpeg)",
                                                  self.convert_to_webm, object_name="tool_text")
        for b in (btn_convert_png, btn_convert_webp, btn_convert_avif, btn_convert_webm):
            toolbar_layout.addWidget(b)

        toolbar_layout.addWidget(self._tool_divider())

        # View tools
        btn_zoom_in = self._make_tool_button("＋", "Zoom in (or scroll up)", self.zoom_in)
        btn_zoom_out = self._make_tool_button("－", "Zoom out (or scroll down)", self.zoom_out)
        btn_zoom_reset = self._make_tool_button("⊙", "Reset zoom to 100%", self.reset_zoom)
        for b in (btn_zoom_in, btn_zoom_out, btn_zoom_reset):
            toolbar_layout.addWidget(b)

        toolbar_layout.addWidget(self._tool_divider())

        # Reset
        btn_reset = self._make_tool_button("↺", "Reset to original — discard all edits",
                                           self.reset_image, object_name="btn_danger")
        toolbar_layout.addWidget(btn_reset)

        # ---- Properties sidebar (right): file + pen only ----
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(252)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)
        sidebar_layout.setContentsMargins(16, 14, 16, 14)
        sidebar_layout.setSpacing(7)

        app_logo = QLabel("PictEd")
        app_logo.setObjectName("app_logo")

        app_subtitle = QLabel("Properties")
        app_subtitle.setObjectName("app_subtitle")

        logo_divider = QFrame()
        logo_divider.setObjectName("divider")

        lbl_file = QLabel("FILE")
        lbl_file.setObjectName("sidebar_header")

        btn_open = QPushButton("Open Image")
        btn_open.setObjectName("btn_primary")
        btn_open.setToolTip("Open an image file (PNG, JPG, BMP, WebP, AVIF)")
        btn_open.clicked.connect(self.open_image)

        btn_save = QPushButton("Save Image")
        btn_save.setObjectName("btn_accent")
        btn_save.setToolTip("Save the edited image")
        btn_save.clicked.connect(self.save_image)

        lbl_paint = QLabel("PEN PROPERTIES")
        lbl_paint.setObjectName("sidebar_header")

        self.btn_brush_color = QPushButton()
        self.btn_brush_color.setToolTip("Pick the brush color")
        self.btn_brush_color.clicked.connect(self.set_brush_color)

        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(1, 200)
        self.brush_size_slider.setValue(self.brush_size)
        self.brush_size_slider.setToolTip("Brush / eraser size in image pixels")
        self.brush_size_slider.valueChanged.connect(self.set_brush_size)

        self.size_label = QLabel(f"Brush size: {self.brush_size} px")
        self.size_label.setObjectName("info_label")

        self.info_label = QLabel("Dimension: -\nZoom: 100%")
        self.info_label.setObjectName("info_label")

        sidebar_layout.addWidget(app_logo)
        sidebar_layout.addWidget(app_subtitle)
        sidebar_layout.addWidget(logo_divider)

        sidebar_layout.addWidget(lbl_file)
        sidebar_layout.addWidget(btn_open)
        sidebar_layout.addWidget(btn_save)

        sidebar_layout.addWidget(lbl_paint)
        sidebar_layout.addWidget(self.btn_brush_color)
        sidebar_layout.addWidget(self.brush_size_slider)
        sidebar_layout.addWidget(self.size_label)

        sidebar_layout.addSpacing(12)
        sidebar_layout.addWidget(self.info_label)

        self.canvas = ImageCanvas()
        self.canvas.setObjectName("canvas")
        self.canvas.setText("DROP IMAGE TO START\n\nOpen Image  ·  Ctrl+O\nDrag canvas to select crop area")
        self.canvas.draw_started.connect(self.on_draw_started)
        self.canvas.draw_moved.connect(self.on_draw_moved)
        self.canvas.draw_finished.connect(self.on_draw_finished)
        self._refresh_brush_color_button()
        self.btn_brush_color.setFixedHeight(30)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.canvas)

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        context_bar = QFrame()
        context_bar.setObjectName("context_bar")
        context_layout = QHBoxLayout(context_bar)
        context_layout.setContentsMargins(16, 9, 16, 9)
        context_layout.setSpacing(10)
        workspace_label = QLabel("WORKSPACE")
        workspace_label.setObjectName("workspace_label")
        context_layout.addWidget(workspace_label)
        context_layout.addStretch()
        hint = QLabel("Scroll to zoom  ·  Space + drag to pan")
        hint.setObjectName("context_hint")
        context_layout.addWidget(hint)
        workspace_layout.addWidget(context_bar)
        workspace_layout.addWidget(self.scroll_area)

        main_layout.addWidget(toolbar)
        main_layout.addWidget(workspace)
        main_layout.addWidget(sidebar)

        self.statusBar().showMessage("Ready — no image loaded")

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        act_open = QAction("Open Image...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.open_image)
        act_save = QAction("Save Image...", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.save_image)
        file_menu.addAction(act_open)
        file_menu.addAction(act_save)
        file_menu.addSeparator()

        convert_menu = file_menu.addMenu("Convert To")
        for label, fmt in (("PNG", "PNG"), ("WebP", "WEBP"), ("AVIF", "AVIF")):
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, f=fmt: self.convert_format(f))
            convert_menu.addAction(act)
        act_webm = QAction("WebM (video)", self)
        act_webm.triggered.connect(self.convert_to_webm)
        convert_menu.addAction(act_webm)

        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        edit_menu = menu_bar.addMenu("Edit")
        act_crop = QAction("Crop Selection", self)
        act_crop.triggered.connect(self.crop_image)
        act_flip_h = QAction("Flip Horizontal", self)
        act_flip_h.triggered.connect(self.flip_horizontal)
        act_flip_v = QAction("Flip Vertical", self)
        act_flip_v.triggered.connect(self.flip_vertical)
        act_gray = QAction("Grayscale", self)
        act_gray.triggered.connect(self.to_grayscale)
        act_enhance = QAction("Enhance Quality", self)
        act_enhance.triggered.connect(self.enhance_quality)
        act_rembg = QAction("Remove Background", self)
        act_rembg.triggered.connect(self.remove_background)
        for act in (act_crop, act_flip_h, act_flip_v):
            edit_menu.addAction(act)
        edit_menu.addSeparator()
        edit_menu.addAction(act_enhance)
        edit_menu.addAction(act_gray)
        edit_menu.addAction(act_rembg)
        edit_menu.addSeparator()
        act_up2 = QAction("Upscale 2x", self)
        act_up2.triggered.connect(self.upscale_2x)
        act_up4 = QAction("Upscale 4x", self)
        act_up4.triggered.connect(self.upscale_4x)
        edit_menu.addAction(act_up2)
        edit_menu.addAction(act_up4)
        edit_menu.addSeparator()
        act_reset = QAction("Reset to Original", self)
        act_reset.triggered.connect(self.reset_image)
        edit_menu.addAction(act_reset)

        view_menu = menu_bar.addMenu("View")
        act_zin = QAction("Zoom In", self)
        act_zin.setShortcut("Ctrl++")
        act_zin.triggered.connect(self.zoom_in)
        act_zout = QAction("Zoom Out", self)
        act_zout.setShortcut("Ctrl+-")
        act_zout.triggered.connect(self.zoom_out)
        act_zreset = QAction("Reset Zoom (100%)", self)
        act_zreset.setShortcut("Ctrl+0")
        act_zreset.triggered.connect(self.reset_zoom)
        view_menu.addAction(act_zin)
        view_menu.addAction(act_zout)
        view_menu.addAction(act_zreset)

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

    def _default_save_path(self, ext: str) -> str:
        """Default save location: same directory the image was opened from."""
        stem = os.path.splitext(os.path.basename(self.current_path))[0] if self.current_path else "output"
        directory = self.last_dir or os.getcwd()
        return os.path.join(directory, f"{stem}.{ext}")

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", self.last_dir or "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.avif)"
        )
        if file_path:
            try:
                self.original_image = Image.open(file_path).convert("RGB")
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to open image:\n{exc}")
                return
            self.current_path = file_path
            self.last_dir = os.path.dirname(os.path.abspath(file_path))
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

    def set_tool(self, tool: str):
        self.tool = tool
        self.canvas.tool = tool
        if tool == "select":
            self.canvas.setCursor(Qt.ArrowCursor)
            self.statusBar().showMessage("Tool: select / crop")
        else:
            self.canvas.setCursor(Qt.CrossCursor)
            self.statusBar().showMessage(f"Tool: {tool} — {self.brush_size} px — drag on the image")

    def _refresh_brush_color_button(self):
        text_color = "#06121f" if self.brush_color.lightness() > 128 else "#ffffff"
        self.btn_brush_color.setStyleSheet(
            f"QPushButton {{ background-color: {self.brush_color.name()}; "
            f"color: {text_color}; border: 1px solid #3d5a99; }}"
        )
        self.btn_brush_color.setText(f"Color {self.brush_color.name().upper()}")

    def set_brush_color(self):
        color = QColorDialog.getColor(self.brush_color, self, "Brush Color")
        if not color.isValid():
            return
        self.brush_color = color
        self._refresh_brush_color_button()

    def set_brush_size(self, value):
        self.brush_size = int(value)
        self.size_label.setText(f"Brush size: {self.brush_size} px")

    def _handle_draw(self, start: QPoint, end: QPoint):
        pixmap = self.canvas.pixmap()
        if not pixmap or pixmap.isNull():
            return

        scale = self.pil_image.width / pixmap.width()
        p1 = (int(start.x() * scale), int(start.y() * scale))
        p2 = (int(end.x() * scale), int(end.y() * scale))
        width = max(1, int(self.brush_size))

        if self.tool == "eraser":
            if self.pil_image.mode != "RGBA":
                self.pil_image = self.pil_image.convert("RGBA")
            color = (0, 0, 0, 0)
        else:
            color = (*self.brush_color.getRgb()[:3], 255)

        draw = ImageDraw.Draw(self.pil_image)
        if p1 == p2:
            r = width / 2
            draw.ellipse((p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r), fill=color)
        else:
            draw.line((p1, p2), fill=color, width=width, joint="curve")

        self._paint_canvas_preview(start, end)

    def _paint_canvas_preview(self, start: QPoint, end: QPoint):
        pixmap = self.canvas.pixmap()
        if not pixmap or pixmap.isNull():
            return

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        width = max(1, int(round(self.brush_size * self.zoom_factor)))
        pen = QPen(self.brush_color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        if self.tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen.setColor(QColor(0, 0, 0, 0))
        painter.setPen(pen)
        if start == end:
            painter.drawPoint(start)
        else:
            painter.drawLine(start, end)
        painter.end()
        self.canvas.setPixmap(pixmap)

    def on_draw_started(self, point: QPoint):
        if not self.pil_image:
            return
        self._handle_draw(point, point)

    def on_draw_moved(self, start: QPoint, end: QPoint):
        if not self.pil_image:
            return
        self._handle_draw(start, end)

    def on_draw_finished(self):
        if not self.pil_image:
            return
        self.update_display()
        if self.tool == "eraser":
            self.statusBar().showMessage(f"Erased ({self.brush_size} px) — area is now transparent")
        else:
            self.statusBar().showMessage(f"Painted with brush ({self.brush_size} px)")

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

    def _prepare_for_save(self, fmt: str) -> Image.Image:
        """Return an image with a mode suitable for the target format."""
        img = self.pil_image
        has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
        if fmt in ("PNG", "WEBP", "AVIF"):
            return img.convert("RGBA") if has_alpha else img.convert("RGB")
        if has_alpha:
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[-1])
            return background
        return img.convert("RGB")

    @staticmethod
    def _resolve_save_format(file_path: str, selected_filter: str = ""):
        """Pick a Pillow format from the file extension, or the dialog filter."""
        mapping = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP", ".avif": "AVIF"}
        fmt = mapping.get(os.path.splitext(file_path)[1].lower())
        if fmt is None:
            fmt = "JPEG" if "JPEG" in selected_filter.upper() else "PNG"
            file_path += ".jpg" if fmt == "JPEG" else ".png"
        return fmt, file_path

    def convert_format(self, fmt: str):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        fmt = fmt.upper()
        ext = {"PNG": "png", "WEBP": "webp", "AVIF": "avif"}.get(fmt, fmt.lower())

        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Convert to {fmt}", self._default_save_path(ext), f"{fmt} (*.{ext})"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(f".{ext}"):
            file_path = f"{file_path}.{ext}"

        try:
            img = self._prepare_for_save(fmt)
            img.save(file_path, format=fmt, **self.SAVE_OPTIONS.get(fmt, {}))
        except Exception as exc:
            QMessageBox.critical(self, "Conversion Failed", f"Cannot convert to {fmt}:\n{exc}")
            self.statusBar().showMessage(f"{fmt} conversion failed")
            return

        size_kb = os.path.getsize(file_path) / 1024
        self.statusBar().showMessage(f"Converted to {fmt}: {file_path}")
        QMessageBox.information(self, "Converted", f"Saved {fmt} ({size_kb:.1f} KB)\n{file_path}")

    def convert_to_webm(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            QMessageBox.critical(
                self, "ffmpeg Not Found",
                "ffmpeg is required to create WebM videos.\n"
                "Install it (e.g. sudo apt install ffmpeg) and try again."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Convert to WebM", self._default_save_path("webm"), "WebM video (*.webm)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".webm"):
            file_path = f"{file_path}.webm"

        duration, ok = QInputDialog.getInt(
            self, "WebM Duration", "Video length (seconds):", 5, 1, 60, 1
        )
        if not ok:
            return

        frame = self.pil_image.convert("RGB")
        w, h = frame.size
        even_w, even_h = w - (w % 2), h - (h % 2)
        if even_w != w or even_h != h:
            # yuv420p requires even dimensions
            frame = frame.crop((0, 0, even_w, even_h))

        tmp_dir = tempfile.mkdtemp(prefix="picted_webm_")
        frame_path = os.path.join(tmp_dir, "frame.png")
        error_msg = None

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage("Rendering WebM video…")
        try:
            frame.save(frame_path, format="PNG")
            cmd = [
                ffmpeg_path, "-y", "-loop", "1", "-i", frame_path,
                "-t", str(duration), "-r", "30",
                "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
                "-b:v", "0", "-crf", "32", "-an", file_path,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                stderr_lines = (proc.stderr or "").strip().splitlines()
                error_msg = stderr_lines[-1] if stderr_lines else "ffmpeg failed"
        except Exception as exc:
            error_msg = str(exc)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            QApplication.restoreOverrideCursor()

        if error_msg or not os.path.exists(file_path):
            QMessageBox.critical(
                self, "Conversion Failed",
                f"Cannot create WebM:\n{error_msg or 'unknown ffmpeg error'}"
            )
            self.statusBar().showMessage("WebM conversion failed")
            return

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        self.statusBar().showMessage(f"Converted to WebM: {file_path}")
        QMessageBox.information(
            self, "Converted",
            f"Saved WebM video ({duration}s, {size_mb:.2f} MB)\n{file_path}"
        )

    def save_image(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Image", self._default_save_path("png"),
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp);;AVIF (*.avif)"
        )
        if not file_path:
            return

        try:
            fmt, file_path = self._resolve_save_format(file_path, selected_filter)
            img = self._prepare_for_save(fmt)
            img.save(file_path, format=fmt, **self.SAVE_OPTIONS.get(fmt, {}))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save image:\n{exc}")
            self.statusBar().showMessage("Save failed")
            return

        self.statusBar().showMessage(f"Saved: {file_path}")
        QMessageBox.information(self, "Saved", f"Saved to {file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PictEd")
    app.setStyleSheet(STYLESHEET)
    window = PhotoEditor()
    window.show()
    sys.exit(app.exec())

