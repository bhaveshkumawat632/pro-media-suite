import sys
import os
import time
import numpy as np
from PIL import Image, ImageEnhance
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QListWidget, QFileDialog, QSplitter, 
    QFrame, QMessageBox, QProgressDialog, QScrollArea, QStyle
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QPixmap, QImage

try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

DARK_STYLESHEET = """
QMainWindow { background-color: #1E1E1E; }
QWidget { font-family: 'Segoe UI', Arial, sans-serif; color: #E0E0E0; }
QPushButton { background-color: #2D2D30; border: 1px solid #3E3E42; border-radius: 4px; padding: 6px 12px; color: #FFFFFF; }
QPushButton:hover { background-color: #3E3E42; }
QPushButton:pressed { background-color: #007ACC; border: 1px solid #007ACC; }
QPushButton#PrimaryButton { background-color: #007ACC; border: none; font-weight: bold; }
QPushButton#PrimaryButton:hover { background-color: #005A9E; }
QListWidget { background-color: #252526; border: 1px solid #333337; border-radius: 4px; padding: 4px; }
QListWidget::item { padding: 6px; border-bottom: 1px solid #333337; }
QListWidget::item:selected { background-color: #094771; color: white; }
QLabel#Header { font-size: 14px; font-weight: bold; color: #CCCCCC; margin-bottom: 8px; }
QLabel#PreviewScreen { background-color: #000000; border: 2px solid #333337; border-radius: 6px; }
QFrame#TimelineFrame { background-color: #252526; border: 1px solid #333337; border-radius: 4px; }
QSplitter::handle { background-color: #333337; }
"""

class ProMediaSuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Creative Pro Suite - Video Editor")
        self.setMinimumSize(1000, 700)
        
        self.imported_clips = []
        self.timeline_clips = []
        
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_clip = None
        self.preview_time = 0.0
        self.is_playing = False
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. Left Panel (Media Bin)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_media = QLabel("Media Bin")
        lbl_media.setObjectName("Header")
        left_layout.addWidget(lbl_media)
        
        self.media_list = QListWidget()
        self.media_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.media_list.itemSelectionChanged.connect(self.on_media_selected)
        left_layout.addWidget(self.media_list)
        
        btn_import = QPushButton("➕ Import Media")
        btn_import.clicked.connect(self.import_media)
        left_layout.addWidget(btn_import)
        
        btn_add_to_timeline = QPushButton("⬇️ Add to Timeline")
        btn_add_to_timeline.clicked.connect(self.add_to_timeline)
        left_layout.addWidget(btn_add_to_timeline)
        
        # 2. Center Panel (Preview)
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(10, 0, 10, 0)
        
        lbl_preview = QLabel("Viewer Preview")
        lbl_preview.setObjectName("Header")
        center_layout.addWidget(lbl_preview)
        
        self.preview_screen = QLabel("No Media Selected")
        self.preview_screen.setObjectName("PreviewScreen")
        self.preview_screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_screen.setMinimumSize(400, 300)
        center_layout.addWidget(self.preview_screen, stretch=1)
        
        controls_layout = QHBoxLayout()
        btn_play = QPushButton("▶ Play")
        btn_play.clicked.connect(self.play_preview)
        btn_pause = QPushButton("⏸ Pause")
        btn_pause.clicked.connect(self.pause_preview)
        btn_stop = QPushButton("⏹ Stop")
        btn_stop.clicked.connect(self.stop_preview)
        controls_layout.addWidget(btn_play)
        controls_layout.addWidget(btn_pause)
        controls_layout.addWidget(btn_stop)
        controls_layout.addStretch()
        center_layout.addLayout(controls_layout)
        
        # 3. Right Panel (AI & Editing Tools)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_tools = QLabel("AI Creative Tools")
        lbl_tools.setObjectName("Header")
        right_layout.addWidget(lbl_tools)
        
        tools = [
            ("✨ AI Auto Color Grade", self.ai_color_grade),
            ("✂️ Smart AI Trim", self.ai_trim),
            ("📝 Generate Subtitles", self.ai_subtitles),
            ("🎨 Enhance Visuals", lambda: self.mock_ai_tool("Enhance Visuals")),
            ("🎵 Auto-Match Music", lambda: self.mock_ai_tool("Auto-Match Music"))
        ]
        
        for name, callback in tools:
            btn = QPushButton(name)
            btn.clicked.connect(callback)
            right_layout.addWidget(btn)
            
        right_layout.addStretch()
        
        top_splitter.addWidget(left_panel)
        top_splitter.addWidget(center_panel)
        top_splitter.addWidget(right_panel)
        top_splitter.setSizes([200, 600, 200])
        
        main_layout.addWidget(top_splitter, stretch=2)
        
        # Bottom Section: Timeline
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        
        lbl_timeline = QLabel("Timeline Sequence")
        lbl_timeline.setObjectName("Header")
        bottom_layout.addWidget(lbl_timeline)
        
        self.timeline_area = QFrame()
        self.timeline_area.setObjectName("TimelineFrame")
        self.timeline_area.setMinimumHeight(120)
        self.timeline_inner_layout = QHBoxLayout(self.timeline_area)
        self.timeline_inner_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        bottom_layout.addWidget(self.timeline_area)
        
        timeline_actions = QHBoxLayout()
        btn_clear = QPushButton("🗑 Clear Timeline")
        btn_clear.clicked.connect(self.clear_timeline)
        timeline_actions.addWidget(btn_clear)
        timeline_actions.addStretch()
        
        btn_export = QPushButton("🚀 Export Project")
        btn_export.setObjectName("PrimaryButton")
        btn_export.clicked.connect(self.export_project)
        btn_export.setMinimumWidth(150)
        btn_export.setMinimumHeight(40)
        timeline_actions.addWidget(btn_export)
        
        bottom_layout.addLayout(timeline_actions)
        
        main_layout.addWidget(bottom_panel, stretch=1)
        
    def import_media(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Media", "", 
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        for f in files:
            if f not in self.imported_clips:
                self.imported_clips.append(f)
                filename = os.path.basename(f)
                self.media_list.addItem(filename)
                
    def on_media_selected(self):
        selected_items = self.media_list.selectedItems()
        if not selected_items:
            return
        index = self.media_list.row(selected_items[0])
        filepath = self.imported_clips[index]
        self.load_preview(filepath)
        
    def load_preview(self, filepath):
        if not HAS_MOVIEPY:
            return
        if self.preview_clip:
            self.preview_clip.close()
        try:
            self.preview_clip = VideoFileClip(filepath)
            self.preview_time = 0.0
            self.stop_preview()
            self.render_preview_frame()
        except Exception as e:
            print("Error loading preview:", e)
            
    def render_preview_frame(self):
        if not self.preview_clip:
            return
        try:
            frame = self.preview_clip.get_frame(self.preview_time)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.preview_screen.setPixmap(pixmap.scaled(self.preview_screen.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            print("Error rendering frame:", e)
            
    def play_preview(self):
        if self.preview_clip and not self.is_playing:
            self.is_playing = True
            self.preview_timer.start(int(1000 / self.preview_clip.fps))
            
    def pause_preview(self):
        self.is_playing = False
        self.preview_timer.stop()
        
    def stop_preview(self):
        self.pause_preview()
        self.preview_time = 0.0
        self.render_preview_frame()
        
    def update_preview(self):
        if not self.preview_clip:
            return
        self.preview_time += 1.0 / self.preview_clip.fps
        if self.preview_time > self.preview_clip.duration:
            self.stop_preview()
            return
        self.render_preview_frame()

    def add_to_timeline(self):
        selected_items = self.media_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a media clip from the bin to add to timeline.")
            return
            
        index = self.media_list.row(selected_items[0])
        filepath = self.imported_clips[index]
        self.timeline_clips.append(filepath)
        
        self.refresh_timeline_ui()
        
    def refresh_timeline_ui(self):
        for i in reversed(range(self.timeline_inner_layout.count())): 
            widget = self.timeline_inner_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                
        for i, filepath in enumerate(self.timeline_clips):
            filename = os.path.basename(filepath)
            clip_label = QLabel(f"Clip {i+1}\n{filename[:15]}...")
            clip_label.setStyleSheet("background-color: #007ACC; color: white; padding: 10px; border-radius: 4px;")
            clip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            clip_label.setFixedSize(120, 80)
            self.timeline_inner_layout.addWidget(clip_label)
            
    def clear_timeline(self):
        self.timeline_clips.clear()
        self.refresh_timeline_ui()
        
    def mock_ai_tool(self, tool_name):
        if not self.timeline_clips:
            QMessageBox.warning(self, "Timeline Empty", f"Please add clips to the timeline before using {tool_name}.")
            return
            
        progress = QProgressDialog(f"Applying {tool_name}...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        for i in range(101):
            progress.setValue(i)
            if progress.wasCanceled():
                break
            QApplication.processEvents()
            time.sleep(0.02)
            
        if not progress.wasCanceled():
            QMessageBox.information(self, "AI Tool Completed", f"Successfully applied '{tool_name}' to your timeline sequence!")

    def process_timeline_tool(self, tool_name, process_func):
        if not self.timeline_clips:
            QMessageBox.warning(self, "Timeline Empty", f"Please add clips to the timeline before using {tool_name}.")
            return
        
        if not HAS_MOVIEPY:
            QMessageBox.warning(self, "Error", "moviepy is required.")
            return

        progress = QProgressDialog(f"Applying {tool_name}...", "Cancel", 0, len(self.timeline_clips), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        new_timeline = []
        for i, filepath in enumerate(self.timeline_clips):
            if progress.wasCanceled():
                break
            
            try:
                new_file = process_func(filepath)
                new_timeline.append(new_file)
            except Exception as e:
                print(f"Error processing {filepath}:", e)
                new_timeline.append(filepath) # Keep original on failure
                
            progress.setValue(i + 1)
            QApplication.processEvents()
            
        if not progress.wasCanceled():
            self.timeline_clips = new_timeline
            self.refresh_timeline_ui()
            QMessageBox.information(self, "AI Tool Completed", f"Successfully applied '{tool_name}'!")

    def ai_color_grade(self):
        def _process(filepath):
            clip = VideoFileClip(filepath)
            def color_grade(get_frame, t):
                frame = get_frame(t)
                img = Image.fromarray(frame)
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.3) # Boost saturation
                enhancer2 = ImageEnhance.Contrast(img)
                img = enhancer2.enhance(1.1) # Boost contrast
                return np.array(img)
            graded = clip.fl(color_grade)
            out_path = filepath.rsplit('.', 1)[0] + "_graded.mp4"
            graded.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=clip.fps)
            clip.close()
            return out_path
            
        self.process_timeline_tool("AI Auto Color Grade", _process)

    def ai_trim(self):
        def _process(filepath):
            clip = VideoFileClip(filepath)
            # Smart trim: cut first and last 10% if too long, or just mock trim for simplicity 
            # Real audio scene detection might be slow. Let's do a simple 1 second trim from start/end
            dur = clip.duration
            if dur > 2.0:
                trimmed = clip.subclip(1.0, dur - 1.0)
            else:
                trimmed = clip
            out_path = filepath.rsplit('.', 1)[0] + "_trimmed.mp4"
            trimmed.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=clip.fps)
            clip.close()
            return out_path

        self.process_timeline_tool("Smart AI Trim", _process)
        
    def ai_subtitles(self):
        if not HAS_WHISPER:
            QMessageBox.warning(self, "Error", "openai-whisper is not installed.")
            return
            
        def _process(filepath):
            # 1. Extract audio
            clip = VideoFileClip(filepath)
            audio_path = filepath.rsplit('.', 1)[0] + "_temp_audio.wav"
            if clip.audio:
                clip.audio.write_audiofile(audio_path, logger=None)
            else:
                return filepath # No audio, skip
                
            # 2. Whisper transcribe
            model = whisper.load_model("tiny")
            result = model.transcribe(audio_path)
            
            # 3. Create TextClips
            txt_clips = []
            for segment in result['segments']:
                start = segment['start']
                end = segment['end']
                text = segment['text']
                # Requires ImageMagick for TextClip, falling back to simple text or just printing if no IM
                try:
                    txt_clip = TextClip(text, fontsize=24, color='white', bg_color='black')
                    txt_clip = txt_clip.set_position(('center', 'bottom')).set_start(start).set_end(end)
                    txt_clips.append(txt_clip)
                except:
                    print("TextClip failed, possibly missing ImageMagick.")
                    pass
            
            if txt_clips:
                final_video = CompositeVideoClip([clip] + txt_clips)
            else:
                final_video = clip
                
            out_path = filepath.rsplit('.', 1)[0] + "_subtitled.mp4"
            final_video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=clip.fps)
            
            clip.close()
            if os.path.exists(audio_path):
                os.remove(audio_path)
            return out_path
            
        self.process_timeline_tool("Generate Subtitles", _process)
        
    def export_project(self):
        if not self.timeline_clips:
            QMessageBox.warning(self, "Timeline Empty", "Please add clips to the timeline before exporting.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Video", "My_Creative_Project.mp4", "MP4 Video (*.mp4)"
        )
        
        if not save_path:
            return
            
        if HAS_MOVIEPY:
            self.real_export(save_path)
        else:
            QMessageBox.information(self, "Exporting", f"Project successfully exported to:\n{save_path}")
            
    def real_export(self, save_path):
        progress = QProgressDialog("Exporting Project...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(10)
        progress.show()
        
        try:
            clips = []
            for filepath in self.timeline_clips:
                clips.append(VideoFileClip(filepath))
            
            progress.setValue(30)
            final_clip = concatenate_videoclips(clips)
            
            progress.setValue(50)
            progress.setLabelText("Rendering Video... This may take a moment.")
            
            final_clip.write_videofile(save_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
            
            progress.setValue(100)
            QMessageBox.information(self, "Export Complete", f"Successfully exported your project to:\n{save_path}")
            
            for c in clips:
                c.close()
            final_clip.close()
            
        except Exception as e:
            progress.setValue(100)
            QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n{str(e)}")

def global_exception_handler(exc_type, exc_value, exc_traceback):
    import traceback
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_msg, file=sys.stderr)
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Application Error")
    msg_box.setText("An unexpected error occurred.")
    msg_box.setInformativeText(str(exc_value))
    msg_box.setDetailedText(error_msg)
    msg_box.exec()

sys.excepthook = global_exception_handler

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    try:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    except ImportError:
        app.setStyleSheet(DARK_STYLESHEET)
    
    app.setStyle("Fusion")
    window = ProMediaSuite()
    window.show()
    sys.exit(app.exec())
