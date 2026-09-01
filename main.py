import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMessageBox, QScrollArea, QFrame,
    QProgressDialog
)
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QWheelEvent
from PySide6.QtCore import Qt, QRect, QPoint, QThread, Signal
from PIL import Image, ImageEnhance, ImageFilter
from rembg import remove

class RemoveBgThread(QThread):
    finished_signal = Signal(object)
    error_signal = Signal(str)

    def __init__(self, pil_image):
        super().__init__()
        self.pil_image = pil_image

    def run(self):
        try:
            result = remove(self.pil_image)
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))

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
            pen = QPen(QColor(0, 120, 215), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(current_rect)
            painter.fillRect(current_rect, QColor(0, 120, 215, 40))

    def reset_selection(self):
        self.crop_rect = QRect()
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.update()

class PhotoEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Editor - Crop, 4K, Grayscale, Enhance & Zoom")
        self.resize(1100, 750)

        self.pil_image = None
        self.original_image = None
        self.zoom_factor = 1.0

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)

        btn_open = QPushButton("Open Image")
        btn_open.clicked.connect(self.open_image)

        btn_crop = QPushButton("Crop Selection")
        btn_crop.clicked.connect(self.crop_image)

        btn_upscale = QPushButton("Upscale to 4K")
        btn_upscale.clicked.connect(self.upscale_4k)

        btn_enhance = QPushButton("Enhance Quality")
        btn_enhance.clicked.connect(self.enhance_quality)

        btn_grayscale = QPushButton("Grayscale")
        btn_grayscale.clicked.connect(self.to_grayscale)

        btn_remove_bg = QPushButton("Remove Background")
        btn_remove_bg.clicked.connect(self.remove_background)

        zoom_label = QLabel("Zoom:")
        zoom_btn_layout = QHBoxLayout()
        btn_zoom_in = QPushButton("+ Zoom In")
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_out = QPushButton("- Zoom Out")
        btn_zoom_out.clicked.connect(self.zoom_out)
        zoom_btn_layout.addWidget(btn_zoom_in)
        zoom_btn_layout.addWidget(btn_zoom_out)

        btn_zoom_reset = QPushButton("Reset Zoom (100%)")
        btn_zoom_reset.clicked.connect(self.reset_zoom)

        btn_reset = QPushButton("Reset Original")
        btn_reset.clicked.connect(self.reset_image)

        btn_save = QPushButton("Save Image")
        btn_save.clicked.connect(self.save_image)

        self.info_label = QLabel("Dimension: -\nZoom: 100%")

        sidebar_layout.addWidget(btn_open)
        sidebar_layout.addWidget(btn_crop)
        sidebar_layout.addWidget(btn_upscale)
        sidebar_layout.addWidget(btn_enhance)
        sidebar_layout.addWidget(btn_grayscale)
        sidebar_layout.addWidget(btn_remove_bg)
        sidebar_layout.addSpacing(10)
        sidebar_layout.addWidget(zoom_label)
        sidebar_layout.addLayout(zoom_btn_layout)
        sidebar_layout.addWidget(btn_zoom_reset)
        sidebar_layout.addSpacing(10)
        sidebar_layout.addWidget(btn_reset)
        sidebar_layout.addWidget(btn_save)
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(self.info_label)

        self.canvas = ImageCanvas()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.canvas)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.scroll_area)

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

    def upscale_4k(self):
        if not self.pil_image:
            QMessageBox.warning(self, "Warning", "No image loaded!")
            return

        target_width = 3840
        w, h = self.pil_image.size
        if w == 0:
            return

        target_height = int(h * (target_width / w))
        self.pil_image = self.pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        self.update_display()
        QMessageBox.information(self, "Upscale 4K", f"Resized to {target_width}x{target_height}")

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

        progress = QProgressDialog("Removing background...", None, 0, 0, self)
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.show()

        self.thread = RemoveBgThread(self.pil_image)

        def on_finished(result_img):
            progress.close()
            self.pil_image = result_img
            self.update_display()
            QMessageBox.information(self, "Remove Background", "Background removed successfully!")

        def on_error(err_msg):
            progress.close()
            QMessageBox.critical(self, "Error", f"Failed to remove background: {err_msg}")

        self.thread.finished_signal.connect(on_finished)
        self.thread.error_signal.connect(on_error)
        self.thread.start()

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
            QMessageBox.information(self, "Saved", f"Saved to {file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhotoEditor()
    window.show()
    sys.exit(app.exec())

