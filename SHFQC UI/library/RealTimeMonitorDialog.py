import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QLabel, 
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QWidget
)
from PyQt6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class RealTimeMonitorDialog(QDialog):
    def __init__(self, measurement_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"實時監控 - {measurement_type}")
        self.setMinimumSize(800, 600)
        
        #* 切換顯示模式
        self.measurement_type = measurement_type
        self._init_ui()
        
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        #* 左側面板 - 信息顯示
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        #* 進度顯示
        progress_group = QGroupBox("進度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_label = QLabel("等待開始...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.time_label = QLabel("剩餘時間: --:--:--")
        self.abort_button = QPushButton("中止量測")
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.abort_button)
        
        #* 當前參數
        self.params_group = QGroupBox("當前參數")
        self.params_layout = QVBoxLayout(self.params_group)
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(["參數", "值"])
        self.params_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.params_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.params_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.params_layout.addWidget(self.params_table)
        
        left_layout.addWidget(progress_group)
        left_layout.addWidget(self.params_group)
        
        #* 右側面板 - 繪圖
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        #* 創建特定量測繪圖方案
        self.plot_group = QGroupBox("實時數據")
        plot_layout = QVBoxLayout(self.plot_group)
        
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        plot_layout.addWidget(self.canvas)
        
        right_layout.addWidget(self.plot_group)
        
        #* 添加分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])
        
        main_layout.addWidget(splitter)
        
        #* 連接信號
        self.abort_button.clicked.connect(self.reject)
    
    def update_progress(self, progress, left_time):
        """更新進度資訊"""
        self.progress_bar.setValue(int(progress))
        
        #* 計算剩餘時間
        if left_time > 0:
            remaining_time_h = left_time // 3600
            left_time -= remaining_time_h * 3600
            remaining_time_m = left_time // 60
            remaining_time_s = left_time - remaining_time_m * 60
            self.time_label.setText(f"剩餘時間: {int(remaining_time_h):02}:{int(remaining_time_m):02}:{int(remaining_time_s):02}(h/m/s)")
        
    def update_params(self, params):
        """更新參數表格"""
        if not isinstance(params, tuple) or len(params) < 2 or params[0] != 'params':
            return
        
        param_dict = params[1]
        
        if not isinstance(param_dict, dict):
            return
        
        # 設置表格行數
        self.params_table.setRowCount(len(param_dict))
        
        # 填充表格
        for i, (key, value) in enumerate(param_dict.items()):
            self.params_table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.params_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        # 自動調整列寬
        self.params_table.resizeColumnsToContents()
    
    def update_plot(self, data):
        """根據測量類型更新繪圖"""
        if not isinstance(data, tuple) or len(data) < 2 or data[0] != 'data':
            return
        
        # 提取數據
        plot_data = data[1:]
        
        # 切換繪圖類型
        if self.measurement_type == "時域 {振幅} 掃描":
            self._update_power_plot(plot_data)
        elif self.measurement_type == "時域 {頻率} 掃描":
            self._update_freq_dep_plot(plot_data)
        elif self.measurement_type == "時域 {電流頻率} 掃描":
            self._update_current_freq_plot(plot_data)
        
        self.canvas.draw()
    
    def _update_power_plot(self, data):
        """更新時域 {振幅} 掃描"""
        if len(data) < 2:
            return
        self.ax.cla()

        #* 數據格式: (amp, waveform)
        amp, waveform = data
        time_axis = np.arange(len(waveform)) * 0.5e-9 * 1e9
        
        self.ax.plot(time_axis, np.abs(waveform), 'b-', label='振幅')
        self.ax.set_xlabel("時間 (ns)")
        self.ax.set_ylabel("電壓 (V)")
        self.ax.set_title(f"振幅比例: {amp:.3f}")
        self.ax.legend()
        self.ax.grid(True)
    
    def _update_freq_dep_plot(self, data):
        """更新時域 {頻率} 掃描"""
        if len(data) < 2:
            return
        self.ax.cla()

        #* 數據格式: (freq, waveform)
        freq, waveform = data
        time_axis = np.arange(len(waveform)) * 0.5e-9 * 1e9 
        
        self.ax.plot(time_axis, np.abs(waveform), 'b-', label='振幅')
        self.ax.set_xlabel("時間 (ns)")
        self.ax.set_ylabel("電壓 (V)")
        self.ax.set_title(f"頻率: {freq/1e6:.3f} MHz")
        self.ax.legend()
        self.ax.grid(True)
    
    def _update_current_freq_plot(self, data):
        """更新時域 {電流頻率} 掃描"""
        if len(data) < 3:
            return
        self.ax.cla()

        # 數據格式: (current, freq, waveform)
        current, freq, waveform = data
        time_axis = np.arange(len(waveform)) * 0.5e-9 * 1e9
        
        self.ax.plot(time_axis, np.abs(waveform), 'b-', label='振幅')
        self.ax.set_xlabel("時間 (ns)")
        self.ax.set_ylabel("電壓 (V)")
        self.ax.set_title(f"電流: {current*1000:.3f} mA, 頻率: {freq/1e6:.3f} MHz")
        self.ax.legend()
        self.ax.grid(True)
    
    def reject(self):
        """使用者點擊中止按鈕"""
        super().reject()
        
        try:
            if hasattr(self.parent(), 'measurement_controller'):
                self.parent().measurement_controller.abort_measurement()
        except AttributeError:
            print("無法中止測量：未找到測量控制器")