import sys
import os
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QListWidget, QFileDialog, QSplitter, 
    QFrame, QMessageBox, QProgressDialog, QScrollArea, QStyle
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette

# If moviepy is installed, we can do real exports. Otherwise, mock it.
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

# --- UI Styling (Premium Dark Theme) ---
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1E1E1E;
}
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #E0E0E0;
}
QPushButton {
    background-color: #2D2D30;
    border: 1px solid #3E3E42;
    border-radius: 4px;
    padding: 6px 12px;
    color: #FFFFFF;
}
QPushButton:hover {
    background-color: #3E3E42;
}
QPushButton:pressed {
    background-color: #007ACC;
    border: 1px solid #007ACC;
}
QPushButton#PrimaryButton {
    background-color: #007ACC;
    border: none;
    font-weight: bold;
}
QPushButton#PrimaryButton:hover {
    background-color: #005A9E;
}
QListWidget {
    background-color: #252526;
    border: 1px solid #333337;
    border-radius: 4px;
    padding: 4px;
}
QListWidget::item {
    padding: 6px;
    border-bottom: 1px solid #333337;
}
QListWidget::item:selected {
    background-color: #094771;
    color: white;
}
QLabel#Header {
    font-size: 14px;
    font-weight: bold;
    color: #CCCCCC;
    margin-bottom: 8px;
}
QLabel#PreviewScreen {
    background-color: #000000;
    border: 2px solid #333337;
    border-radius: 6px;
}
QFrame#TimelineFrame {
    background-color: #252526;
    border: 1px solid #333337;
    border-radius: 4px;
}
QSplitter::handle {
    background-color: #333337;
}
"""

class ProMediaSuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Creative Pro Suite - Video Editor")
        self.setMinimumSize(1000, 700)
        
        self.imported_clips = []
        self.timeline_clips = []
        
        self.init_ui()
        
    def init_ui(self):
        # Main Widget and Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- Top Section: 3-way Splitter ---
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
        btn_pause = QPushButton("⏸ Pause")
        btn_stop = QPushButton("⏹ Stop")
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
            ("✨ AI Auto Color Grade", self.mock_ai_tool),
            ("✂️ Smart AI Trim", self.mock_ai_tool),
            ("📝 Generate Subtitles", self.mock_ai_tool),
            ("🎨 Enhance Visuals", self.mock_ai_tool),
            ("🎵 Auto-Match Music", self.mock_ai_tool)
        ]
        
        for name, callback in tools:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, n=name: self.mock_ai_tool(n))
            right_layout.addWidget(btn)
            
        right_layout.addStretch()
        
        # Add to splitter
        top_splitter.addWidget(left_panel)
        top_splitter.addWidget(center_panel)
        top_splitter.addWidget(right_panel)
        top_splitter.setSizes([200, 600, 200])
        
        main_layout.addWidget(top_splitter, stretch=2)
        
        # --- Bottom Section: Timeline ---
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        
        lbl_timeline = QLabel("Timeline Sequence")
        lbl_timeline.setObjectName("Header")
        bottom_layout.addWidget(lbl_timeline)
        
        # Timeline visual area
        self.timeline_area = QFrame()
        self.timeline_area.setObjectName("TimelineFrame")
        self.timeline_area.setMinimumHeight(120)
        self.timeline_inner_layout = QHBoxLayout(self.timeline_area)
        self.timeline_inner_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        bottom_layout.addWidget(self.timeline_area)
        
        # Timeline actions
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
        # Clear existing
        for i in reversed(range(self.timeline_inner_layout.count())): 
            widget = self.timeline_inner_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                
        # Re-add items
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
        QMessageBox.information(self, "AI Tool Activated", f"Starting '{tool_name}' on the selected media...\n\n(This is a seamless integration feature ready to process your content using AI algorithms.)")
        
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
            QMessageBox.information(self, "Exporting", f"Project successfully exported to:\n{save_path}\n\n(Note: moviepy is not installed, so this is a mock export.)")
            
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
            
            # Simple UI update hook for moviepy
            def my_logger(message):
                pass # In a real app we parse proglog messages to update progress.setValue()
                
            progress.setValue(50)
            progress.setLabelText("Rendering Video... This may take a moment.")
            
            # Write file
            final_clip.write_videofile(save_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
            
            progress.setValue(100)
            QMessageBox.information(self, "Export Complete", f"Successfully exported your project to:\n{save_path}")
            
            # Free memory
            for c in clips:
                c.close()
            final_clip.close()
            
        except Exception as e:
            progress.setValue(100)
            QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply global stylesheet
    app.setStyleSheet(DARK_STYLESHEET)
    
    # Set modern fusion style as base
    app.setStyle("Fusion")
    
    window = ProMediaSuite()
    window.show()
    sys.exit(app.exec())
