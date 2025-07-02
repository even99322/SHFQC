# 布局方案
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QFormLayout, QGridLayout, 
    QTableWidget, QGroupBox
)

# 組件
from PyQt6.QtWidgets import (
    QLineEdit, QPushButton, QRadioButton, QLabel, QTextEdit,
    QMessageBox, QComboBox, QDoubleSpinBox, QDialogButtonBox,
    QTableWidgetItem, QFileDialog, QHeaderView, QWidget, QSpinBox,
    QCheckBox
)

# 窗口類型
from PyQt6.QtWidgets import QDialog, QProgressDialog
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QThreadPool, QRunnable, QObject

import os
import configparser
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from pyvisa import ResourceManager
import math

from .device_control import YOKOGAWA
from .File_Storage import DataSaver, SaveSlicesWorker


class ScientificDoubleSpinBox(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._unit_map = {
            "k": 1, "M": 2, "G": 3
        }
        self._unit_list = ["k", "M", "G"]
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.coeff_spin = QDoubleSpinBox()
        self.coeff_spin.setRange(-1000, 1000)
        self.coeff_spin.setSingleStep(0.1)
        self.coeff_spin.setDecimals(3)
        self.coeff_spin.valueChanged.connect(self._emit_value_changed)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(self._unit_list)
        self.unit_combo.setCurrentText("")  # 預設 base
        self.unit_combo.currentIndexChanged.connect(self._emit_value_changed)

        unit_label = QLabel("Hz")

        layout.addWidget(self.coeff_spin)
        layout.addWidget(self.unit_combo)
        layout.addWidget(unit_label)
        layout.addStretch()

    def value(self):
        """取得完整數值"""
        coeff = self.coeff_spin.value()
        unit = self.unit_combo.currentText()
        exponent = self._unit_map.get(unit, 0)
        return coeff * (1000 ** exponent)

    def setValue(self, value):
        """設置完整數值"""
        if value == 0:
            self.coeff_spin.setValue(0)
            self.unit_combo.setCurrentText("")
            return

        exponent = math.floor(math.log(abs(value), 1000))
        coeff = value / (1000 ** exponent)

        if abs(coeff) >= 1000:
            coeff /= 1000
            exponent += 1
        elif abs(coeff) < 1:
            coeff *= 1000
            exponent -= 1

        best_unit = min(self._unit_map, key=lambda k: abs(self._unit_map[k] - exponent))
        self.unit_combo.setCurrentText(best_unit)
        self.coeff_spin.setValue(coeff)

    def _emit_value_changed(self):
        self.valueChanged.emit(self.value())


class SaveDataDialog(QDialog):
    """保存數據對話框"""
    def __init__(self, parent=None, time_data=None, freq_data=None, power_data=None, power_amps=None,
                 freq_dep_data=None, freq_lo_values=None, current_freq_data=None, freq_values=None, 
                 current_values=None):
        super().__init__(parent)
        self.setWindowTitle("保存數據")
        self.setMinimumSize(800, 600)

        #* 切片存檔線程
        self.thread_pool = QThreadPool.globalInstance()
        self.worker = None
        
        #* 存儲數據
        self.time_data = time_data
        self.freq_data = freq_data
        self.power_data = power_data
        self.power_amps = power_amps
        self.freq_dep_data = freq_dep_data
        self.freq_lo_values = freq_lo_values
        self.current_freq_data = current_freq_data
        self.freq_values = freq_values
        self.current_values = current_values
        
        #* 加載或初始化設置
        self.settings = QSettings("MyCompany", "SHFQC_Control")
        self.load_settings()
        
        self.init_ui()
        
    def load_settings(self):
        """加載對話框設置"""
        self.file_path = self.settings.value("save_dialog/file_path", os.path.expanduser("~"))
        self.file_name = self.settings.value("save_dialog/file_name", "experiment_data")
        self.comments = self.settings.value("save_dialog/comments", "")
        self.data_type = self.settings.value("save_dialog/data_type", "time_domain")
        
    def save_settings(self):
        """保存對話框設置"""
        self.settings.setValue("save_dialog/file_path", self.file_path)
        self.settings.setValue("save_dialog/file_name", self.file_name)
        self.settings.setValue("save_dialog/comments", self.comments)
        self.settings.setValue("save_dialog/data_type", self.data_type)
        
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        #* 數據類型選擇
        type_group = QGroupBox("數據類型")
        type_layout = QHBoxLayout(type_group)
        
        self.time_radio = QRadioButton("時域 {單張} 數據")
        self.power_radio = QRadioButton("時域 {振幅} 數據")
        self.freq_dep_radio = QRadioButton("時域 {頻率} 數據")
        self.current_freq_radio = QRadioButton("時域 {電流頻率} 數據")
        self.freq_radio = QRadioButton("頻域 {單張} 數據")
        
        #* 設置選中
        if self.data_type == "時域 {單張} 量測":
            self.time_radio.setChecked(True)
        elif self.data_type == "頻域 {單張} 量測":
            self.freq_radio.setChecked(True)
        elif self.data_type == "時域 {振幅} 掃描":
            self.power_radio.setChecked(True)
        elif self.data_type == "時域 {頻率} 掃描":
            self.freq_dep_radio.setChecked(True)
        elif self.data_type == "時域 {電流頻率} 掃描":
            self.current_freq_radio.setChecked(True)
        else:
            self.time_radio.setChecked(True)
            
        #* 連接信號
        self.time_radio.toggled.connect(lambda: self.update_preview("時域 {單張} 量測"))
        self.power_radio.toggled.connect(lambda: self.update_preview("時域 {振幅} 掃描"))
        self.freq_dep_radio.toggled.connect(lambda: self.update_preview("時域 {頻率} 掃描"))
        self.current_freq_radio.toggled.connect(lambda: self.update_preview("時域 {電流頻率} 掃描"))
        self.freq_radio.toggled.connect(lambda: self.update_preview("頻域 {單張} 量測"))
        
        type_layout.addWidget(self.time_radio)
        type_layout.addWidget(self.freq_radio)
        type_layout.addWidget(self.power_radio)
        type_layout.addWidget(self.freq_dep_radio)
        type_layout.addWidget(self.current_freq_radio)
        
        main_layout.addWidget(type_group)
        
        #* 文件信息組
        file_group = QGroupBox("文件設置")
        file_layout = QGridLayout(file_group)
        
        #* 文件路徑
        file_layout.addWidget(QLabel("保存位置:"), 0, 0)
        self.path_edit = QLineEdit(self.file_path)
        file_layout.addWidget(self.path_edit, 0, 1)
        self.browse_btn = QPushButton("瀏覽...")
        self.browse_btn.clicked.connect(self.browse_path)
        file_layout.addWidget(self.browse_btn, 0, 2)
        
        #* 文件名
        file_layout.addWidget(QLabel("文件名:"), 1, 0)
        self.name_edit = QLineEdit(self.file_name)
        file_layout.addWidget(self.name_edit, 1, 1, 1, 2)
        
        #* 備註
        file_layout.addWidget(QLabel("備註:"), 2, 0)
        self.comments_edit = QTextEdit(self.comments)
        self.comments_edit.setMaximumHeight(100)
        file_layout.addWidget(self.comments_edit, 2, 1, 1, 2)
        
        main_layout.addWidget(file_group)
        
        #* 預覽區域
        preview_group = QGroupBox("數據預覽")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_canvas = FigureCanvas(Figure(figsize=(8, 4)))
        preview_layout.addWidget(self.preview_canvas)
        
        main_layout.addWidget(preview_group)
        
        #* 按鈕
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept_and_save)
        buttons.rejected.connect(self.reject)
        
        main_layout.addWidget(buttons)
        
        #* 初始更新預覽
        self.update_preview(self.data_type)
        
    def browse_path(self):
        """選擇保存路徑"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "選擇保存位置",
            self.path_edit.text(),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.path_edit.setText(folder)
            
    def update_preview(self, data_type):
        """更新數據預覽圖"""
        self.data_type = data_type
        ax = self.preview_canvas.figure.clear()
        ax = self.preview_canvas.figure.add_subplot(111)
        
        try:
            if data_type == "時域 {單張} 量測" and self.time_data is not None:
                t = np.arange(len(self.time_data)) * 0.5e-9 * 1e9  # ns
                ax.plot(t, np.abs(self.time_data))
                ax.set_xlabel('時間 (ns)')
                ax.set_ylabel('電壓 (V)')
                ax.set_title('時域 {單張} 量測數據預覽')
                
            elif data_type == "時域 {振幅} 掃描" and self.power_data is not None and self.power_amps is not None:
                waveform = self.power_data[0]
                t = np.arange(len(waveform)) * 0.5e-9 * 1e9  # ns
                ax.plot(t, np.abs(waveform))
                ax.set_xlabel('時間 (ns)')
                ax.set_ylabel('電壓 (V)')
                ax.set_title(f'時域 [振幅] 掃描數據預覽 (振幅比例: {self.power_amps[0]:.3f})')
                
            elif data_type == "時域 {頻率} 掃描" and self.freq_dep_data is not None and self.freq_lo_values is not None:
                # 顯示第一個頻率點的數據作為預覽
                waveform = self.freq_dep_data[0]
                t = np.arange(len(waveform)) * 0.5e-9 * 1e9  # ns
                ax.plot(t, np.abs(waveform))
                ax.set_xlabel('時間 (ns)')
                ax.set_ylabel('電壓 (V)')
                ax.set_title(f'時域 [頻率] 掃描數據預覽 (LO頻率: {self.freq_lo_values[0]/1e6:.3f} MHz)')

            elif data_type == "時域 {電流頻率} 掃描" and self.current_freq_data is not None and self.current_values is not None:
                if self.current_values and self.current_freq_data:
                    current_val = self.current_values[0]
                    freq_val = self.freq_lo_values[0] if self.freq_lo_values else 0
                    wave_data = self.current_freq_data[0][0]
                    
                    t = np.arange(len(wave_data)) * 0.5e-9 * 1e9
                    ax.plot(t, np.abs(wave_data))
                    ax.set_xlabel('時間 (ns)')
                    ax.set_ylabel('電壓 (V)')
                    ax.set_title(f'時域 [電流頻率] 掃描數據預覽 (電流={current_val:.3f} A, 頻率={freq_val/1e6:.3f} MHz)')

                else:
                    ax.text(0.5, 0.5, '無可用電流-頻率數據', 
                            horizontalalignment='center',
                            verticalalignment='center',
                            transform=ax.transAxes)
                    ax.set_title('數據預覽')
            
            elif data_type == "頻域 {單張} 量測" and self.freq_data is not None:
                freq = self.freq_data['freq'] / 1e9  # GHz
                ax.plot(freq, 20*np.log10(np.abs(self.freq_data['data'])))
                ax.set_xlabel('頻率 (GHz)')
                ax.set_ylabel('Magnitude (dB)')
                ax.set_title('頻域 {單張} 量測數據預覽')
                
            else:
                ax.text(0.5, 0.5, '無可用數據', 
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax.transAxes)
                ax.set_title('數據預覽')
                
            self.preview_canvas.draw()
            
        except Exception as e:
            ax.text(0.5, 0.5, f'預覽錯誤: {str(e)}', 
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes)
            self.preview_canvas.draw()
            
    def accept_and_save(self):
        """接受並保存設置"""
        self.file_path = self.path_edit.text()
        self.file_name = self.name_edit.text()
        self.comments = self.comments_edit.toPlainText()
        
        if not os.path.isdir(self.file_path):
            QMessageBox.warning(self, "錯誤", "指定的保存位置無效")
            return
            
        if not self.file_name:
            QMessageBox.warning(self, "錯誤", "文件名不能為空")
            return
            
        # 創建保存信息字典
        save_info = {
            'base_path': self.file_path,
            'file_name': self.file_name,
            'comments': self.comments
        }
        
        success = False
        img_dir = None
        
        try:
            # 根據數據類型保存數據
            if self.data_type == "時域 {單張} 量測" and self.time_data is not None:
                success, img_dir = DataSaver.save_time_data(self.time_data, save_info, self)
            elif self.data_type == "頻域 {單張} 量測" and self.freq_data is not None:
                success, img_dir = DataSaver.save_freq_data(self.freq_data, save_info, self)
            elif self.data_type == "時域 {振幅} 掃描" and self.power_data is not None and self.power_amps is not None:
                success, img_dir = DataSaver.save_power_data(self.power_data, self.power_amps, save_info, self)
            elif self.data_type == "時域 {頻率} 掃描" and self.freq_dep_data is not None and self.freq_lo_values is not None:
                success, img_dir = DataSaver.save_freq_dep_data(self.freq_dep_data, self.freq_lo_values, save_info, self)
            elif self.data_type == "時域 {電流頻率} 掃描" and self.current_freq_data is not None and self.current_values is not None and self.freq_lo_values is not None:
                success, img_dir = DataSaver.save_current_freq_data(
                    self.current_freq_data, self.current_values, self.freq_lo_values, save_info, self
                )
            else:
                QMessageBox.warning(self, "警告", "沒有可用的數據來保存")
                return
                
            # 保存圖片
            if success and img_dir and self.plot_manager:
                os.makedirs(img_dir, exist_ok=True)
                
                self.save_single_plot(img_dir, save_info['file_name'])
                self.save_heatmap(img_dir, save_info['file_name'])
                
                self.progress_dialog = QProgressDialog(
                    "正在保存切片圖片...", 
                    "取消", 
                    0, 
                    100, 
                    self
                )
                self.progress_dialog.setWindowTitle("保存進度")
                self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                self.progress_dialog.setAutoClose(True)
                
                self.worker = SaveSlicesWorker(self.plot_manager, img_dir, save_info['file_name'])
                self.worker_thread = QObject()
                
                self.worker.progress.connect(self.progress_dialog.setValue)
                self.worker.finished.connect(self.on_slice_save_finished)
                self.worker.error.connect(self.on_slice_save_error)
                self.progress_dialog.canceled.connect(self.worker.cancel)
                
                self.thread_pool.start(self.worker.run)
            else:
                self.finalize_saving()
                
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"保存數據時出錯: {str(e)}")
            return
            
        if success:
            self.save_settings()
            self.accept()
    
    def save_single_plot(self, img_dir, file_name):
        """保存指定單張圖片"""
        try:
            fig = Figure(figsize=(8, 8))
            ax = fig.add_subplot(111)
            
            if self.data_type == '時域 {單張} 量測' and self.time_data is not None:
                t = np.arange(len(self.time_data)) * 0.5e-9 * 1e9
                ax.plot(t, np.abs(self.time_data), 'b-', label='振幅')
                ax.set_title("時域 {單張} 量測數據")
                ax.set_xlabel("時間 (ns)")
                ax.set_ylabel("電壓 (V)")
            
            elif self.data_type == '頻域 {單張} 量測' and self.freq_data is not None:
                freq = self.freq_data['freq'] / 1e9  # GHz
                ax.plot(freq, 20*np.log10(np.abs(self.freq_data['data'])))
                ax.set_title("頻域 {單張} 量測數據")
                ax.set_xlabel("頻率 (GHz)")
                ax.set_ylabel("Magnitude (dB)")
            
            ax.grid(True)
            ax.legend()
            fig.savefig(os.path.join(img_dir, f"{file_name}_single.png"), dpi=1000, bbox_inches='tight')
            plt.close(fig)
            return True
        except Exception as e:
            print(f"保存單張失敗: {str(e)}")
            return False
    
    def save_heatmap(self, img_dir, file_name):
        """保存热图图片（1:1比例）"""
        try:
            if self.data_type in ['時域 {振幅} 掃描', '時域 {頻率} 掃描']:
                fig = Figure(figsize=(8, 8))
                ax = fig.add_subplot(111)
                
                if self.data_type == '時域 {振幅} 掃描' and self.power_data is not None:
                    t = np.arange(len(self.power_data[0])) * 0.5e-9 * 1e9
                    amplitudes = self.power_amplitudes
                    
                    max_amp = np.max([np.max(np.abs(data)) for data in self.power_data])
                    
                    # 创建热图数据
                    heatmap_data = np.zeros((len(amplitudes), len(t)))
                    for i, data in enumerate(self.power_data):
                        heatmap_data[i] = np.abs(data)
                    
                    # 绘制热图
                    im = ax.imshow(
                        heatmap_data, 
                        aspect='auto', 
                        extent=[t[0], t[-1], amplitudes[0], amplitudes[-1]],
                        cmap='viridis',
                        vmin=0,
                        vmax=max_amp
                    )
                    ax.set_title("振幅掃描熱圖")
                    ax.set_xlabel("時間 (ns)")
                    ax.set_ylabel("振幅比例")
                    fig.colorbar(im, ax=ax, label='電壓 (V)')

                elif self.data_type == '時域 {頻率} 掃描' and self.freq_dep_data is not None:
                    t = np.arange(len(self.freq_dep_data[0])) * 0.5e-9 * 1e9
                    amplitudes = self.power_amplitudes
                    
                    max_amp = np.max([np.max(np.abs(data)) for data in self.freq_dep_data])
                    
                    heatmap_data = np.zeros((len(amplitudes), len(t)))
                    for i, data in enumerate(self.freq_dep_data):
                        heatmap_data[i] = np.abs(data)
                    
                    im = ax.imshow(
                        heatmap_data, 
                        aspect='auto', 
                        extent=[t[0], t[-1], amplitudes[0], amplitudes[-1]],
                        cmap='viridis',
                        vmin=0,
                        vmax=max_amp
                    )
                    ax.set_title("頻率掃描熱圖")
                    ax.set_xlabel("時間 (ns)")
                    ax.set_ylabel("Lo頻率")
                    fig.colorbar(im, ax=ax, label='電壓 (V)')
                
                fig.savefig(os.path.join(img_dir, f"{file_name}_heatmap.png"), dpi=1000, bbox_inches='tight')
                plt.close(fig)
                return True
            return False
        except Exception as e:
            print(f"保存熱圖失敗: {str(e)}")
            return False
        
    def get_save_info(self):
        """獲取保存信息"""
        return {
            'base_path': self.file_path,
            'file_name': self.file_name,
            'comments': self.comments,
            'data_type': self.data_type
        }

    def on_slice_save_finished(self):
        """切片保存完成"""
        self.progress_dialog.close()
        self.finalize_saving()
    
    def on_slice_save_error(self, error_msg):
        """切片保存出错"""
        self.progress_dialog.close()
        QMessageBox.critical(self, "错误", f"保存切片时出错: {error_msg}")
        self.finalize_saving()
    
    def finalize_saving(self):
        """完成保存操作，关闭对话框"""
        self.save_settings()
        self.accept()
    



class ParameterDialog(QDialog):
    """參數輸入對話框"""
    def __init__(self, variables, parent=None):
        super().__init__(parent)
        self.setWindowTitle("輸入參數值")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 創建表格
        self.table = QTableWidget(len(variables), 2)
        self.table.setHorizontalHeaderLabels(["參數", "值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        
        # 填充表格
        for i, var in enumerate(sorted(variables)):
            self.table.setItem(i, 0, QTableWidgetItem(var))
            item = QTableWidgetItem("1.0")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, item)
        
        layout.addWidget(self.table)
        
        # 添加按鈕
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_parameters(self):
        """獲取參數字典"""
        params = {}
        for i in range(self.table.rowCount()):
            var = self.table.item(i, 0).text()
            value = self.table.item(i, 1).text()
            try:
                # 嘗試解析為複數
                if 'j' in value or 'i' in value:
                    params[var] = complex(value)
                else:
                    params[var] = float(value)
            except ValueError:
                params[var] = 0.0
        return params
    

class YOKOGAWAControlDialog(QDialog):
    """YOKOGAWA儀器控制對話框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YOKOGAWA 儀器控制")
        self.setMinimumSize(600, 500)

        self.config_path = os.path.join(os.path.dirname(__file__), 'DC_config.ini')
        
        self.yokos = []
        self.rm = None
        self.DC_id = {}
        
        self.init_ui()
        self.load_settings()
        self.a=1
        
    def init_ui(self):
        """初始化用戶界面"""
        main_layout = QVBoxLayout(self)
        
        # 儀器連接組
        connection_group = QGroupBox("儀器連接")
        connection_layout = QFormLayout(connection_group)
        
        self.btn_scan = QPushButton("掃描儀器")
        self.btn_scan.clicked.connect(self.scan_devices)
        connection_layout.addRow(self.btn_scan)
        
        self.link_yoko_devices_group = QGroupBox("選擇YOKOGAWA設備")
        self.link_yoko_layout = QVBoxLayout(self.link_yoko_devices_group)
        connection_layout.addRow(self.link_yoko_devices_group)
        
        self.btn_connect = QPushButton("連接儀器")
        self.btn_connect.clicked.connect(self.connect_device)
        connection_layout.addRow(self.btn_connect)
        
        self.connection_status = QLabel("未連接")
        self.connection_status.setStyleSheet("color: gray;")
        connection_layout.addRow("狀態:", self.connection_status)
        
        main_layout.addWidget(connection_group)
        
        # 儀器控制組
        control_group = QGroupBox("儀器控制")
        control_layout = QFormLayout(control_group)
        
        # 功能選擇
        self.func_combo = QComboBox()
        self.func_combo.addItems(["電流調控", "其餘功能未建立"])
        control_layout.addRow("功能:", self.func_combo)
        
        # 範圍選擇
        self.range_combo = QComboBox()
        self.range_combo.addItems(["200", "100", "10", "1"])
        control_layout.addRow("範圍(mA):", self.range_combo)
        
        # 輸出值
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-200, 200)
        self.value_spin.setSingleStep(0.001)
        self.value_spin.setDecimals(3)

        self.value_step_spin = QComboBox()
        self.value_step_spin.addItems(["1", "0.1", "0.01", "0.001"])
        self.value_step_spin.currentIndexChanged.connect(self.update_value_step)

        control_layout.addRow("輸出值(mA):", self.value_spin)
        control_layout.addRow("調整步距(mA):", self.value_step_spin)
        
        # 輸出開關
        self.output_combo = QComboBox()
        self.output_combo.addItems(["ON", "OFF"])
        control_layout.addRow("輸出:", self.output_combo)
        
        # 操作按鈕
        btn_layout = QHBoxLayout()
        
        self.btn_set_func = QPushButton("設定功能")
        self.btn_set_func.clicked.connect(self.set_function)
        btn_layout.addWidget(self.btn_set_func)
        
        self.btn_set_value = QPushButton("設定輸出值")
        self.btn_set_value.clicked.connect(self.set_value)
        btn_layout.addWidget(self.btn_set_value)
        
        self.btn_set_output = QPushButton("設定輸出")
        self.btn_set_output.clicked.connect(self.set_output)
        btn_layout.addWidget(self.btn_set_output)
        
        control_layout.addRow(btn_layout)
        
        main_layout.addWidget(control_group)
        
        # 消磁控制組
        demag_group = QGroupBox("消磁控制")
        demag_layout = QVBoxLayout(demag_group)
        
        self.demag_path_edit = QLineEdit("0.15, -0.12, 0.09, -0.06, 0.02, -0.01, 0.005, -0.001, 0.0")
        demag_layout.addWidget(QLabel("消磁路徑 (逗號分隔):"))
        demag_layout.addWidget(self.demag_path_edit)
        
        self.btn_demag = QPushButton("執行消磁")
        self.btn_demag.clicked.connect(self.run_demag)
        demag_layout.addWidget(self.btn_demag)
        
        main_layout.addWidget(demag_group)
        
        # 狀態信息
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        main_layout.addWidget(self.status_text)
        
        # 按鈕
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.clicked.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
    
    def update_value_step(self):
        setp = float(self.value_step_spin.currentText())
        self.value_spin.setSingleStep(setp)

    def load_settings(self):
        """加載配置文件"""
        config = configparser.ConfigParser()
        
        # 默認建立文件
        if not os.path.exists(self.config_path):
            self.save_settings()
            return
            
        config.read(self.config_path)
        # 設備設置
        if config.has_section('DC_supply'):
            self.value_spin.setValue(float(config['DC_supply'].get('curr_value', 100)))

    def save_settings(self):
        """保存配置文件"""
        config = configparser.ConfigParser()
        
        # Device 配置
        config['DC_supply'] = {
            'curr_value': str(self.value_spin.value())
        }
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)
    
    def closeEvent(self, event):
        """關閉視窗後複寫配置文件"""
        self.save_settings()
        event.accept()
    
    def scan_devices(self):
        """掃描可用的YOKOGAWA設備"""
        while self.link_yoko_layout.count():
            item = self.link_yoko_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        try:
            self.rm = ResourceManager()
            devices = self.rm.list_resources()
            self.DC_id={}
            for device in devices:
                if "USB" in device:  # 只顯示USB設備
                    if "90ZC38697"in device:
                        self.dc1_check = QCheckBox("DC1")
                        self.link_yoko_layout.addWidget(self.dc1_check)
                        self.dc1_check.stateChanged.connect(self.connect_device)
                        self.DC_id["DC1"]=device

                    elif "90ZC38696"in device:
                        self.dc2_check = QCheckBox("DC2")
                        self.link_yoko_layout.addWidget(self.dc2_check)
                        self.dc2_check.stateChanged.connect(self.connect_device)
                        self.DC_id["DC2"]=device

                    elif "9017D5818"in device:
                        self.dc3_check = QCheckBox("DC3")
                        self.link_yoko_layout.addWidget(self.dc3_check)
                        self.dc3_check.stateChanged.connect(self.connect_device)
                        self.DC_id["DC3"]=device

                    elif "9017D5816"in device:
                        self.dc4_check = QCheckBox("DC4")
                        self.link_yoko_layout.addWidget(self.dc4_check)
                        self.dc4_check.stateChanged.connect(self.connect_device)
                        self.DC_id["DC4"]=device

        except Exception as e:
            self.status_text.append(f"掃描錯誤: {str(e)}")
    
    def connect_device(self):
        """連接選定的設備"""
        self.yokos = []
        try:
            if self.dc1_check.isChecked(): # DC1
                device_id = self.DC_id["DC1"]
                visa_resource = self.rm.open_resource(device_id)
                yoko = YOKOGAWA(device_id, visa_resource)
                self.yokos.append(yoko)

            if self.dc2_check.isChecked(): # DC2
                device_id = self.DC_id["DC2"]
                visa_resource = self.rm.open_resource(device_id)
                yoko = YOKOGAWA(device_id, visa_resource)
                self.yokos.append(yoko)

            if self.dc3_check.isChecked(): # DC3
                device_id = self.DC_id["DC3"]
                visa_resource = self.rm.open_resource(device_id)
                yoko = YOKOGAWA(device_id, visa_resource)
                self.yokos.append(yoko)

            if self.dc4_check.isChecked(): # DC4
                device_id = self.DC_id["DC4"]
                visa_resource = self.rm.open_resource(device_id)
                yoko = YOKOGAWA(device_id, visa_resource)
                self.yokos.append(yoko)
            for yoko in self.yokos:
                try:
                    yoko.operation_setting('CURR', 200e-3)
                except Exception as e:
                    self.status_text.append(f"{yoko.id} 設定錯誤: {str(e)}")
        except Exception as e:
            self.status_text.append(f"連接錯誤: {str(e)}")
    
    def set_function(self):
        """設定儀器功能"""
        func = self.func_combo.currentText()
        range_val = float(self.range_combo.currentText())*1e-3
        
        for yoko in self.yokos:
            try:
                yoko.operation_setting(func, range_val)
                self.status_text.append(f"{yoko.id}: 設定功能 {func} 範圍 {range_val}")
            except Exception as e:
                self.status_text.append(f"{yoko.id} 設定錯誤: {str(e)}")
    
    def set_value(self):
        """設定輸出值"""
        value = round(self.value_spin.value()*1e-3,6)
        
        for yoko in self.yokos:
            try:
                yoko.output_value(value)
                self.status_text.append(f"{yoko.id}: 設定輸出值 {value}")
            except Exception as e:
                self.status_text.append(f"{yoko.id} 設定錯誤: {str(e)}")
    
    def set_output(self):
        """設定輸出開關"""
        output = self.output_combo.currentText()
        
        for yoko in self.yokos:
            try:
                yoko.output(output)
                self.status_text.append(f"{yoko.id}: 設定輸出 {output}")
            except Exception as e:
                self.status_text.append(f"{yoko.id} 設定錯誤: {str(e)}")
    
    def run_demag(self):
        """執行消磁程序"""
        path_str = self.demag_path_edit.text()
        try:
            path = [float(x.strip()) for x in path_str.split(',')]
        except ValueError:
            self.status_text.append("消磁路徑格式錯誤")
            return
            
        if not self.yokos:
            self.status_text.append("沒有已連接的儀器")
            return
            
        self.status_text.append("開始執行消磁...")
        
        # 開啟所有輸出
        for yoko in self.yokos:
            yoko.output('ON')
        
        # 執行消磁
        try:
            YOKOGAWA.demag(self.yokos, path)
            self.status_text.append("消磁完成")
        except Exception as e:
            self.status_text.append(f"消磁錯誤: {str(e)}")
        
        # 關閉所有輸出
        for yoko in self.yokos:
            yoko.output('OFF')