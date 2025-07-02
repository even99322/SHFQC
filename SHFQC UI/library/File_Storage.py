import os
import csv
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
    QMessageBox, QListWidget
)
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, QSettings
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from library.plot_manager import PlotManager


class DataSaver:
    """數據保存工具類，提供各種測量數據的保存功能"""
    
    @staticmethod
    def create_save_directories(base_path, file_name):
        """創建新的保存目錄結構"""
        # 主保存路徑
        os.makedirs(base_path, exist_ok=True)
        
        # 創建兩個子資料夾
        csv_dir = os.path.join(base_path, "原始數據(CVS)")
        img_dir = os.path.join(base_path, "數據圖片")
        
        os.makedirs(csv_dir, exist_ok=True)
        os.makedirs(img_dir, exist_ok=True)
        
        # 在圖片目錄下創建與文件名一致的子資料夾
        file_img_dir = os.path.join(img_dir, file_name)
        os.makedirs(file_img_dir, exist_ok=True)
        
        return csv_dir, file_img_dir

    # 統一時間軸生成方法
    @staticmethod
    def _generate_time_axis(data_length):
        """生成時間軸 (單位: ns)"""
        return np.arange(data_length) * 0.5e-9 * 1e9
    
    @staticmethod
    def save_time_data(data, save_info, parent=None):
        """保存時域數據為CSV並返回圖片保存路徑"""
        if data is None:
            if parent:
                QMessageBox.warning(parent, "警告", "沒有可用的時域數據")
            return False, None
            
        # 創建目錄結構
        csv_dir, img_dir = DataSaver.create_save_directories(
            save_info['base_path'], save_info['file_name']
        )
        
        file_path = os.path.join(csv_dir, f"{save_info['file_name']}.csv")
        
        try:
            t = DataSaver._generate_time_axis(len(data))
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # 寫入備註
                if save_info['comments']:
                    writer.writerow([f"# {save_info['comments']}"])
                    writer.writerow([])
                
                writer.writerow(["Time (ns)", "Real", "Imag", "Abs"])
                
                for i in range(len(t)):
                    writer.writerow([
                        f"{t[i]:.4f}",
                        f"{np.real(data[i]):.6e}",
                        f"{np.imag(data[i]):.6e}",
                        f"{np.abs(data[i]):.6e}"
                    ])
                    
            if parent:
                QMessageBox.information(parent, "成功", f"時域數據已保存至: {file_path}")
            return True, img_dir
        except Exception as e:
            if parent:
                QMessageBox.critical(parent, "錯誤", f"保存時域數據失敗: {str(e)}")
            return False, None

    @staticmethod
    def save_freq_data(freq_domain_data, save_info, parent=None):
        """保存頻域數據為CSV並返回圖片保存路徑"""
        if freq_domain_data is None:
            if parent:
                QMessageBox.warning(parent, "警告", "沒有可用的頻域數據")
            return False, None
            
        # 創建目錄結構
        csv_dir, img_dir = DataSaver.create_save_directories(
            save_info['base_path'], save_info['file_name']
        )
        
        file_path = os.path.join(csv_dir, f"{save_info['file_name']}.csv")
        
        try:
            freq = freq_domain_data['freq'] / 1e9  # GHz
            data = freq_domain_data['data']
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                if save_info['comments']:
                    writer.writerow([f"# {save_info['comments']}"])
                    writer.writerow([])
                
                # 添加完整複數信息
                writer.writerow(["Frequency (GHz)", "Real", "Imag", "Abs", "Magnitude (dB)", "Phase (rad)"])
                
                for i in range(len(freq)):
                    magnitude = 20 * np.log10(np.abs(data[i])) if np.abs(data[i]) > 0 else -np.inf
                    writer.writerow([
                        f"{freq[i]:.4f}",
                        f"{np.real(data[i]):.6e}",
                        f"{np.imag(data[i]):.6e}",
                        f"{np.abs(data[i]):.6e}",
                        f"{magnitude:.4f}",
                        f"{np.angle(data[i]):.6f}"
                    ])
                    
            if parent:
                QMessageBox.information(parent, "成功", f"頻域數據已保存至: {file_path}")
            return True, img_dir
        except Exception as e:
            if parent:
                QMessageBox.critical(parent, "錯誤", f"保存頻域數據失敗: {str(e)}")
            return False, None

    @staticmethod
    def save_power_data(power_data, power_amplitudes, save_info, parent=None):
        """保存功率依賴數據為CSV並返回圖片保存路徑"""
        if not power_data or not power_amplitudes:
            if parent:
                QMessageBox.warning(parent, "警告", "沒有可用的功率依賴數據")
            return False, None
            
        # 創建目錄結構
        csv_dir, img_dir = DataSaver.create_save_directories(
            save_info['base_path'], save_info['file_name']
        )
        
        file_path = os.path.join(csv_dir, f"{save_info['file_name']}.csv")
        
        try:
            t = DataSaver._generate_time_axis(len(power_data[0]))
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                if save_info['comments']:
                    writer.writerow([f"# {save_info['comments']}"])
                    writer.writerow([])
                
                # 添加單位信息
                writer.writerow(["Time (ns)"] + 
                               [f"{amp:.3f} V" for amp in power_amplitudes for _ in ("Real", "Imag", "Abs")])
                
                # 添加子標題
                writer.writerow([""] + 
                               [col_type for amp in power_amplitudes for col_type in ("Real", "Imag", "Abs")])
                
                # 寫入數據
                for i in range(len(t)):
                    row = [f"{t[i]:.4f}"]
                    for j in range(len(power_amplitudes)):
                        row.extend([
                            f"{np.real(power_data[j][i]):.6e}",
                            f"{np.imag(power_data[j][i]):.6e}",
                            f"{np.abs(power_data[j][i]):.6e}"
                        ])
                    writer.writerow(row)
                    
                # 添加空行分隔不同數據集
                writer.writerow([])
                writer.writerow(["Amplitude Values (V):"] + [f"{amp:.6f}" for amp in power_amplitudes])
                    
            if parent:
                QMessageBox.information(parent, "成功", f"功率依賴數據已保存至: {file_path}")
            return True, img_dir
        except Exception as e:
            if parent:
                QMessageBox.critical(parent, "錯誤", f"保存功率依賴數據失敗: {str(e)}")
            return False, None

    @staticmethod
    def save_freq_dep_data(freq_dep_data, freq_lo_values, save_info, parent=None):
        """保存頻率依賴數據為CSV並返回圖片保存路徑"""
        if not freq_dep_data or not freq_lo_values:
            if parent:
                QMessageBox.warning(parent, "警告", "沒有可用的頻率依賴數據")
            return False, None
            
        # 創建目錄結構
        csv_dir, img_dir = DataSaver.create_save_directories(
            save_info['base_path'], save_info['file_name']
        )
        
        file_path = os.path.join(csv_dir, f"{save_info['file_name']}.csv")
        
        try:
            t = DataSaver._generate_time_axis(len(freq_dep_data[0]))
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                if save_info['comments']:
                    writer.writerow([f"# {save_info['comments']}"])
                    writer.writerow([])
                
                # 添加單位信息
                freq_mhz_values = [freq / 1e6 for freq in freq_lo_values]
                writer.writerow(["Time (ns)"] + 
                               [f"{freq_mhz:.3f} MHz" for freq_mhz in freq_mhz_values for _ in ("Real", "Imag", "Abs")])
                
                # 添加子標題
                writer.writerow([""] + 
                               [col_type for _ in freq_mhz_values for col_type in ("Real", "Imag", "Abs")])
                
                # 寫入數據
                for i in range(len(t)):
                    row = [f"{t[i]:.4f}"]
                    for j in range(len(freq_lo_values)):
                        row.extend([
                            f"{np.real(freq_dep_data[j][i]):.6e}",
                            f"{np.imag(freq_dep_data[j][i]):.6e}",
                            f"{np.abs(freq_dep_data[j][i]):.6e}"
                        ])
                    writer.writerow(row)
                    
                # 添加空行分隔不同數據集
                writer.writerow([])
                writer.writerow(["Frequency Values (MHz):"] + [f"{freq/1e6:.6f}" for freq in freq_lo_values])
                    
            if parent:
                QMessageBox.information(parent, "成功", f"頻率依賴數據已保存至: {file_path}")
            return True, img_dir
        except Exception as e:
            if parent:
                QMessageBox.critical(parent, "錯誤", f"保存頻率依賴數據失敗: {str(e)}")
            return False, None
        
    @staticmethod
    def save_current_freq_data(current_freq_wave_data, current_values, freq_lo_values, save_info, parent=None):
        """保存電流-頻率-wave數據為CSV (優化結構)"""
        if not current_freq_wave_data or not current_values or not freq_lo_values:
            if parent:
                QMessageBox.warning(parent, "警告", "沒有可用的電流-頻率數據")
            return False, None
        
        # 創建目錄結構
        csv_dir, img_dir = DataSaver.create_save_directories(
            save_info['base_path'], save_info['file_name']
        )
        
        file_path = os.path.join(csv_dir, f"{save_info['file_name']}.csv")
        
        try:
            # 檢查數據維度一致性
            k = len(current_values)
            m = len(freq_lo_values)
            if k == 0 or m == 0:
                raise ValueError("電流或頻率值列表為空")
                
            n = len(current_freq_wave_data[0][0])
            if any(len(arr1) != m or any(len(arr2) != n for arr2 in arr1) for arr1 in current_freq_wave_data):
                raise ValueError("電流-頻率數據維度不一致")
            
            t = DataSaver._generate_time_axis(n)
            freq_mhz_values = [freq / 1e6 for freq in freq_lo_values]  # 轉為MHz
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                if save_info['comments']:
                    writer.writerow([f"# {save_info['comments']}"])
                    writer.writerow([])
                
                # 使用分層結構保存數據
                for current_idx, current_val in enumerate(current_values):
                    # 電流值標題
                    writer.writerow([f"Current = {current_val} A"])
                    writer.writerow([])
                    
                    # 頻率表頭
                    header = ["Time (ns)"] + [f"{freq_mhz:.3f} MHz" for freq_mhz in freq_mhz_values]
                    writer.writerow(header)
                    
                    # 添加子標題行 (Real/Imag/Abs)
                    sub_header = [""]
                    for _ in freq_mhz_values:
                        sub_header.extend(["Real", "Imag", "Abs"])
                    writer.writerow(sub_header)
                    
                    # 寫入時間點數據
                    for time_idx, time_val in enumerate(t):
                        row = [f"{time_val:.4f}"]
                        for freq_idx in range(m):
                            wave_data = current_freq_wave_data[current_idx][freq_idx][time_idx]
                            row.extend([
                                f"{np.real(wave_data):.6e}",
                                f"{np.imag(wave_data):.6e}",
                                f"{np.abs(wave_data):.6e}"
                            ])
                        writer.writerow(row)
                    
                    # 添加空行分隔不同電流值
                    writer.writerow([])
                    writer.writerow([])
                
                # 添加參數總結
                writer.writerow(["Parameter Summary:"])
                writer.writerow(["Current Values (A):"] + [f"{val:.6e}" for val in current_values])
                writer.writerow(["Frequency Values (MHz):"] + [f"{freq/1e6:.6e}" for freq in freq_lo_values])
                    
            if parent:
                QMessageBox.information(parent, "成功", f"電流-頻率數據已保存至: {file_path}")
            return True, img_dir
        except Exception as e:
            if parent:
                QMessageBox.critical(parent, "錯誤", f"保存電流-頻率數據失敗: {str(e)}")
            return False, None

class FileLoader(QDialog):
    """文件加載對話框，支援多種數據格式的加載和可視化"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("加載數據")
        self.setMinimumSize(800, 600)
        self.parent = parent
        
        # 加載設置
        self.settings = QSettings("MyCompany", "SHFQC_Control")
        self.load_settings()

        self.plot_manager = PlotManager(self.parent)
        
        self.init_ui()
        
    def load_settings(self):
        """加載對話框設置"""
        self.file_path = self.settings.value("load_dialog/file_path", os.path.expanduser("~"))
        
    def save_settings(self):
        """保存對話框設置"""
        self.settings.setValue("load_dialog/file_path", self.file_path)
        
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 文件選擇組
        file_group = QGroupBox("文件選擇")
        file_layout = QGridLayout(file_group)
        
        # 文件路徑
        file_layout.addWidget(QLabel("文件夾:"), 0, 0)
        self.path_edit = QLineEdit(self.file_path)
        file_layout.addWidget(self.path_edit, 0, 1)
        self.browse_btn = QPushButton("瀏覽...")
        self.browse_btn.clicked.connect(self.browse_path)
        file_layout.addWidget(self.browse_btn, 0, 2)
        
        # 文件列表
        file_layout.addWidget(QLabel("CSV文件:"), 1, 0)
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.load_selected_file)
        file_layout.addWidget(self.file_list, 1, 1, 1, 2)
        
        # 更新文件列表
        self.update_file_list()
        
        main_layout.addWidget(file_group)
        
        # 預覽區域
        preview_group = QGroupBox("數據預覽")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_canvas = FigureCanvas(plt.Figure(figsize=(8, 4)))
        preview_layout.addWidget(self.preview_canvas)
        
        main_layout.addWidget(preview_group)
        
        # 按鈕
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.load_selected_file)
        buttons.rejected.connect(self.reject)
        
        main_layout.addWidget(buttons)
        
    def browse_path(self):
        """選擇文件夾路徑"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "選擇文件夾",
            self.path_edit.text(),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.path_edit.setText(folder)
            self.file_path = folder
            self.save_settings()
            self.update_file_list()
            
    def update_file_list(self):
        """更新文件列表"""
        self.file_list.clear()
        try:
            for file in os.listdir(self.file_path):
                if file.endswith(".csv"):
                    self.file_list.addItem(file)
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"無法讀取文件夾: {str(e)}")
    
    def load_selected_file(self):
        """加載選中的文件"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "請選擇一個文件")
            return
            
        file_name = selected_items[0].text()
        file_path = os.path.join(self.file_path, file_name)

        try:
            # 確定文件類型並加載數據
            data_type, data = self.detect_and_load_file(file_path)
            
            if data_type == "time_domain":
                # 更新時域圖
                self.plot_manager.update_time_plot(data)
                QMessageBox.information(self, "成功", "時域 {單張} 量測數據已加載並顯示")
                
            elif data_type == "freq_domain":
                # 更新頻域圖
                self.plot_manager.update_freq_plot(data)
                QMessageBox.information(self, "成功", "頻域 {單張} 量測數據已加載並顯示")
                
            elif data_type == "power_dependent":
                # 更新功率依賴圖
                self.plot_manager.update_power_plot(data)
                QMessageBox.information(self, "成功", "時域 {振幅} 掃描數據已加載並顯示")
                
            elif data_type == "frequency_dependent":
                # 更新頻率依賴圖
                self.plot_manager.update_freq_dep_plot(data)
                QMessageBox.information(self, "成功", "時域 {頻率} 掃描數據已加載並顯示")
                
            elif data_type == "current_frequency":
                # 更新電流-頻率數據
                self.plot_manager.update_current_freq_plot(data)
                QMessageBox.information(self, "成功", "時域 {電流頻率} 掃描數據已加載並顯示")
                
            else:
                QMessageBox.warning(self, "警告", "無法識別的文件格式")
                
            # 預覽數據
            self.preview_data(data_type, data)
                
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"加載文件失敗: {str(e)}")
            
    def detect_and_load_file(self, file_path):
        """檢測文件類型並加載數據 (適配新版保存格式)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # 讀取前幾行確定文件類型
            header = []
            comments = []
            for i in range(10):  # 多讀幾行確保捕獲表頭
                try:
                    row = next(reader)
                    if not row:
                        continue
                    if row[0].startswith("#"):
                        comments.append(row[0][2:])  # 保存註釋
                        continue
                    header = row
                    break
                except StopIteration:
                    break
            
            # 根據表頭判斷文件類型
            if header and header[0] == "Time (ns)":
                if len(header) == 4:  # 時域數據
                    return self.load_time_data(file_path)
                elif len(header) > 4 and ("V" in header[1] or "MHz" in header[1]):  # 功率/頻率依賴
                    if "V" in header[1]:
                        return self.load_power_data(file_path)
                    elif "MHz" in header[1]:
                        return self.load_freq_dep_data(file_path)
            elif header and header[0] == "Frequency (GHz)":
                return self.load_freq_data(file_path)
            elif header and header[0].startswith("Current = "):  # 電流-頻率數據
                return self.load_current_freq_data(file_path)
                
        # 嘗試其他檢測方法
        return self.try_detect_by_content(file_path)
    
    def try_detect_by_content(self, file_path):
        """通過內容嘗試檢測文件類型"""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # 讀取前100行分析列數
            col_counts = set()
            for i, row in enumerate(reader):
                if i > 100:
                    break
                if not row or row[0].startswith("#"):
                    continue
                col_counts.add(len(row))
                
            if not col_counts:
                raise ValueError("無法檢測文件類型 - 文件可能為空")
                
            col_count = max(col_counts)  # 取最常見的列數
            
            if col_count == 4:
                # 可能是時域數據
                return self.load_time_data(file_path)
                
            elif col_count == 6:
                # 可能是頻域數據
                return self.load_freq_data(file_path)
                
            elif col_count > 4 and col_count % 3 == 1:  # 時間列 + N組(實,虛,幅)
                # 可能是功率或頻率依賴數據
                with open(file_path, 'r', encoding='utf-8') as f2:
                    reader2 = csv.reader(f2)
                    first_row = None
                    for row in reader2:
                        if row and not row[0].startswith("#"):
                            first_row = row
                            break
                    
                    if first_row and ("V" in first_row[1] or "MHz" in first_row[1]):
                        if "V" in first_row[1]:
                            return self.load_power_data(file_path)
                        elif "MHz" in first_row[1]:
                            return self.load_freq_dep_data(file_path)
                    else:
                        # 如果沒有單位標識，嘗試作為功率數據加載
                        return self.load_power_data(file_path)
            
            elif col_count > 4 and col_count % 3 == 1:
                # 可能是電流-頻率數據
                return self.load_current_freq_data(file_path)
                
        raise ValueError("無法檢測文件類型")
    
    def load_time_data(self, file_path):
        """加載時域數據 (適配新版)"""
        time = []
        real = []
        imag = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].startswith("#") or row[0] == "Time (ns)":
                    continue
                    
                try:
                    time.append(float(row[0]))
                    real.append(float(row[1]))
                    imag.append(float(row[2]))
                except (ValueError, IndexError):
                    continue
                    
        data = np.array(real) + 1j * np.array(imag)
        return "time_domain", data
    
    def load_freq_data(self, file_path):
        """加載頻域數據 (適配新版)"""
        freq = []
        real = []
        imag = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].startswith("#") or row[0] == "Frequency (GHz)":
                    continue
                    
                try:
                    freq.append(float(row[0]))
                    real.append(float(row[1]))
                    imag.append(float(row[2]))
                except (ValueError, IndexError):
                    continue
                    
        data = np.array(real) + 1j * np.array(imag)
        return "freq_domain", {
            'freq': np.array(freq) * 1e9,  # 轉為Hz
            'data': data
        }
    
    def load_power_data(self, file_path):
        """加載功率依賴數據 (適配新版)"""
        # 提取振幅值
        amplitudes = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = None
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                if row[0] == "Time (ns)":
                    header = row
                    break
                    
            if not header:
                raise ValueError("未找到表頭")
                
            # 解析振幅值 (格式: "0.100 V" 或舊版只有數字)
            for i in range(1, len(header), 3):
                amp_str = header[i]
                # 移除單位後嘗試轉換為浮點數
                amp_str = amp_str.replace(" V", "").replace("V", "").strip()
                try:
                    amplitudes.append(float(amp_str))
                except ValueError:
                    continue
        
        # 加載數據
        time = []
        power_data = [[] for _ in range(len(amplitudes))]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # 跳過表頭和子標題
            header_skipped = False
            subheader_skipped = False
            
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                    
                if not header_skipped and row[0] == "Time (ns)":
                    header_skipped = True
                    continue
                    
                if header_skipped and not subheader_skipped:
                    # 檢查是否是子標題行
                    if "Real" in row[1] or "Imag" in row[1] or "Abs" in row[1]:
                        subheader_skipped = True
                        continue
                    else:
                        # 如果沒有子標題行，直接開始數據
                        subheader_skipped = True
                        
                if header_skipped and subheader_skipped:
                    try:
                        time.append(float(row[0]))
                        for i in range(len(amplitudes)):
                            real_idx = 1 + i * 3
                            imag_idx = real_idx + 1
                            real_val = float(row[real_idx])
                            imag_val = float(row[imag_idx])
                            power_data[i].append(real_val + 1j * imag_val)
                    except (ValueError, IndexError):
                        continue
                    
        return "power_dependent", {
            'amp': amplitudes,
            'data': [np.array(wave) for wave in power_data]
        }
    
    def load_freq_dep_data(self, file_path):
        """加載頻率依賴數據 (適配新版)"""
        # 提取頻率值
        freq_values = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = None
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                if row[0] == "Time (ns)":
                    header = row
                    break
                    
            if not header:
                raise ValueError("未找到表頭")
                
            # 解析頻率值 (格式: "1000.000 MHz" 或舊版只有數字)
            for i in range(1, len(header), 3):
                freq_str = header[i]
                # 移除單位後嘗試轉換為浮點數
                freq_str = freq_str.replace(" MHz", "").replace("MHz", "").strip()
                try:
                    freq_values.append(float(freq_str) * 1e6)  # MHz -> Hz
                except ValueError:
                    continue
        
        # 加載數據
        time = []
        freq_dep_data = [[] for _ in range(len(freq_values))]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # 跳過表頭和子標題
            header_skipped = False
            subheader_skipped = False
            
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                    
                if not header_skipped and row[0] == "Time (ns)":
                    header_skipped = True
                    continue
                    
                if header_skipped and not subheader_skipped:
                    # 檢查是否是子標題行
                    if "Real" in row[1] or "Imag" in row[1] or "Abs" in row[1]:
                        subheader_skipped = True
                        continue
                    else:
                        # 如果沒有子標題行，直接開始數據
                        subheader_skipped = True
                        
                if header_skipped and subheader_skipped:
                    try:
                        time.append(float(row[0]))
                        for i in range(len(freq_values)):
                            real_idx = 1 + i * 3
                            imag_idx = real_idx + 1
                            real_val = float(row[real_idx])
                            imag_val = float(row[imag_idx])
                            freq_dep_data[i].append(real_val + 1j * imag_val)
                    except (ValueError, IndexError):
                        continue
                    
        return "frequency_dependent", {
            'lo_values': freq_values,
            'data': [np.array(wave) for wave in freq_dep_data]
        }
    
    def load_current_freq_data(self, file_path):
        """加載電流-頻率數據 (適配新版分層結構)"""
        currents = []
        freq_lo_values = []
        wave_data = {}  # {(current, freq): [complex]}
        
        current_val = None
        current_freqs = []  # 當前電流下的頻率列表

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # 狀態變量
            in_section = False
            reading_header = False
            reading_subheader = False
            reading_data = False
            
            for row in reader:
                if not row:
                    continue
                    
                # 電流標題行 (e.g., "Current = 0.000000 A")
                if row[0].startswith("Current = "):
                    try:
                        # 提取電流值
                        current_str = row[0].split("=")[1].split("A")[0].strip()
                        current_val = float(current_str)
                        
                        # 如果是新電流值，添加到列表
                        if current_val not in currents:
                            currents.append(current_val)
                        
                        in_section = True
                        reading_header = True
                        current_freqs = []  # 重置當前頻率列表
                        continue
                    except (IndexError, ValueError):
                        continue
                        
                # 參數總結行 - 結束數據部分
                if "Parameter Summary:" in row[0]:
                    break
                    
                if not in_section:
                    continue
                    
                # 頻率表頭行
                if reading_header and row[0] == "Time (ns)":
                    # 提取頻率值 (e.g., "1000.000 MHz")
                    for cell in row[1:]:
                        # 移除單位後嘗試轉換
                        cell = cell.replace(" MHz", "").replace("MHz", "").strip()
                        try:
                            freq_val = float(cell) * 1e6  # MHz -> Hz
                            
                            # 添加到當前頻率列表和全局頻率列表
                            current_freqs.append(freq_val)
                            if freq_val not in freq_lo_values:
                                freq_lo_values.append(freq_val)
                        except ValueError:
                            continue
                    reading_header = False
                    reading_subheader = True
                    continue
                    
                # 子標題行 - 跳過
                if reading_subheader:
                    reading_subheader = False
                    reading_data = True
                    continue
                    
                # 數據行
                if reading_data and row[0]:
                    try:
                        # 跳過時間列
                        for i in range(len(current_freqs)):
                            # 計算數據列索引
                            real_idx = 1 + i * 3
                            imag_idx = real_idx + 1
                            
                            # 提取實部和虛部
                            real_val = float(row[real_idx])
                            imag_val = float(row[imag_idx])
                            cplx_val = real_val + 1j * imag_val
                            
                            # 獲取當前頻率
                            freq_val = current_freqs[i]
                            
                            # 創建鍵 (電流, 頻率)
                            key = (current_val, freq_val)
                            
                            # 初始化波形數據列表
                            if key not in wave_data:
                                wave_data[key] = []
                            
                            # 添加數據點
                            wave_data[key].append(cplx_val)
                    except (ValueError, IndexError):
                        continue
        
        # 確保電流和頻率有序
        unique_currents = sorted(set(currents))
        unique_freqs = sorted(set(freq_lo_values))
        
        # 確定時間點數 (取第一個波形的長度)
        first_key = next(iter(wave_data.keys()), None)
        time_points = len(wave_data[first_key]) if first_key else 0
        
        # 創建三維數據結構 [current_index][freq_index][time_index]
        current_freq_data = []
        for current in unique_currents:
            freq_data = []
            for freq in unique_freqs:
                key = (current, freq)
                if key in wave_data:
                    # 確保波形長度一致
                    waveform = wave_data[key]
                    if len(waveform) != time_points:
                        # 如果長度不一致，截斷或填充為零
                        if len(waveform) > time_points:
                            waveform = waveform[:time_points]
                        else:
                            waveform.extend([0+0j] * (time_points - len(waveform)))
                    freq_data.append(np.array(waveform))
                else:
                    # 如果缺少數據點，填充為零數組
                    freq_data.append(np.zeros(time_points, dtype=complex))
            current_freq_data.append(freq_data)
        
        # 轉換為NumPy數組
        current_freq_data = np.array(current_freq_data)
        return "current_frequency", {
            'curr': np.array(unique_currents),
            'lo_values': np.array(unique_freqs),
            'data': current_freq_data
        }
    
    def preview_data(self, data_type, data):
        """預覽數據"""
        ax = self.preview_canvas.figure.clear()
        ax = self.preview_canvas.figure.add_subplot(111)
        
        try:
            if data_type == "time_domain":
                t = np.arange(len(data)) * 0.5e-9 * 1e9  # ns
                ax.plot(t, np.abs(data), label='振幅')
                ax.set_xlabel('時間 (ns)')
                ax.set_ylabel('振幅 (V)')
                ax.set_title('時域數據預覽')
                ax.legend()
                
            elif data_type == "freq_domain":
                freq = data['freq'] / 1e9  # GHz
                ax.plot(freq, 20*np.log10(np.abs(data['data'])))
                ax.set_xlabel('頻率 (GHz)')
                ax.set_ylabel('幅度 (dB)')
                ax.set_title('頻域數據預覽')
                
            elif data_type == "power_dependent":
                # 顯示第一個功率點的數據
                if data['data']:
                    waveform = data['data'][0]
                    t = np.arange(len(waveform)) * 0.5e-9 * 1e9  # ns
                    ax.plot(t, np.abs(waveform), label='振幅')
                    ax.plot(t, np.real(waveform), label='實部')
                    ax.plot(t, np.imag(waveform), label='虛部')
                    ax.set_xlabel('時間 (ns)')
                    ax.set_ylabel('振幅 (V)')
                    ax.set_title(f"功率依賴數據預覽 (振幅={data['amp'][0]:.3f})")
                    ax.legend()
                
            elif data_type == "frequency_dependent":
                # 顯示第一個頻率點的數據
                if data['data']:
                    waveform = data['data'][0]
                    t = np.arange(len(waveform)) * 0.5e-9 * 1e9  # ns
                    ax.plot(t, np.abs(waveform), label='振幅')
                    ax.plot(t, np.real(waveform), label='實部')
                    ax.plot(t, np.imag(waveform), label='虛部')
                    ax.set_xlabel('時間 (ns)')
                    ax.set_ylabel('振幅 (V)')
                    ax.set_title(f"頻率依賴數據預覽 (LO頻率={data['lo_values'][0]/1e6:.3f} MHz)")
                    ax.legend()
                    
            elif data_type == "current_frequency":
                # 顯示第一個電流和頻率點的數據
                if 'data' in data and data['data'].size > 0:
                    waveform = data['data'][0][0]
                    t = np.arange(len(waveform)) * 0.5e-9 * 1e9  # ns
                    ax.plot(t, np.abs(waveform), label='振幅')
                    ax.plot(t, np.real(waveform), label='實部')
                    ax.plot(t, np.imag(waveform), label='虛部')
                    ax.set_xlabel('時間 (ns)')
                    ax.set_ylabel('振幅 (V)')
                    ax.set_title(f"電流-頻率數據預覽 (電流={data['curr'][0]:.3f} A, 頻率={data['lo_values'][0]/1e6:.3f} MHz)")
                    ax.legend()
                    
            else:
                ax.text(0.5, 0.5, '無法預覽此數據類型', 
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax.transAxes)
                
            self.preview_canvas.draw()
            
        except Exception as e:
            ax.text(0.5, 0.5, f'預覽錯誤: {str(e)}', 
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes)
            self.preview_canvas.draw()

class SaveSlicesWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, plot_manager, base_dir, file_name):
        super().__init__()
        self.plot_manager = plot_manager
        self.base_dir = base_dir
        self.file_name = file_name
        self._cancelled = False

        self.data_type = plot_manager.current_data_type
        self.power_amplitudes = plot_manager.power_amplitudes
        self.freq_lo_values = plot_manager.freq_lo_values
        self.current_values = plot_manager.current_values
    
    def cancel(self):
        self._cancelled = True

    def create_slice_plot(self, slice_data, title):
        """创建新的切片图表（不依赖 GUI 组件）"""
        fig = Figure(figsize=(8, 8))
        ax = fig.add_subplot(111)
        
        t = np.arange(len(slice_data)) * 0.5e-9 * 1e9
        ax.plot(t, np.abs(slice_data), 'b-', label='振幅')
        
        ax.set_title(title)
        ax.set_xlabel("時間 (ns)")
        ax.set_ylabel("電壓 (V)")
        ax.grid(True)
        ax.legend()
        
        return fig
    
    def run(self):
        try:
            slices_dir = os.path.join(self.base_dir, "切片圖片")
            os.makedirs(slices_dir, exist_ok=True)
            
            total = 0
            if self.plot_manager.current_data_type == '時域 {振幅} 量測':
                total = len(self.power_amplitudes)
            elif self.plot_manager.current_data_type == '時域 {頻率} 量測':
                total = len(self.freq_lo_values)
            elif self.plot_manager.current_data_type == '時域 {電流頻率} 量測':
                total = len(self.current_values) * len(self.freq_lo_values)
            
            if total == 0:
                self.finished.emit()
                return
            
            count = 0
            
            # 保存功率扫描的所有切片
            if self.plot_manager.current_data_type == '時域 {振幅} 量測':
                for i in range(len(self.power_amplitudes)):
                    if self._cancelled:
                        break
                    
                    slice_data = self.plot_manager.power_data[i]
                    amp = self.power_amplitudes[i]
                    slice_path = os.path.join(slices_dir, f"{self.file_name}_振幅_{amp:.3f}.png")
                    
                    fig = self.create_slice_plot(slice_data, f"振幅掃描切片 (振幅比例: {amp:.3f})")
                    fig.savefig(slice_path, dpi=1000, bbox_inches='tight')
                    plt.close(fig)
                    
                    count += 1
                    self.progress.emit(int(count * 100 / total))
            
            # 保存频率扫描的所有切片
            elif self.plot_manager.current_data_type == '時域 {頻率} 量測':
                for i in range(len(self.freq_lo_values)):
                    if self._cancelled:
                        break
                    
                    slice_data = self.plot_manager.freq_dep_data[i]
                    freq_mhz = self.freq_lo_values[i] / 1e6
                    slice_path = os.path.join(slices_dir, f"{self.file_name}_頻率_{freq_mhz:.3f}MHz.png")
                    
                    fig = self.create_slice_plot(slice_data, f"頻率掃描切片 (LO頻率: {freq_mhz:.3f} MHz)")
                    fig.savefig(slice_path, dpi=1000, bbox_inches='tight')
                    plt.close(fig)  # 关闭图表释放内存
                    
                    count += 1
                    self.progress.emit(int(count * 100 / total))
            
            # 保存电流-频率扫描的所有切片
            elif self.plot_manager.current_data_type == '時域 {電流頻率} 量測':
                # 按电流值创建子目录
                for current_idx, current_val in enumerate(self.current_values):
                    if self._cancelled:
                        break
                    
                    current_dir = os.path.join(slices_dir, f"電流_{current_val:.3f}A")
                    os.makedirs(current_dir, exist_ok=True)
                    
                    # 保存该电流下所有频率的切片
                    for freq_idx in range(len(self.freq_lo_values)):
                        if self._cancelled:
                            break
                        
                        slice_data = self.plot_manager.current_freq_data[current_idx][freq_idx]
                        freq_mhz = self.freq_lo_values[freq_idx] / 1e6
                        slice_path = os.path.join(current_dir, f"{self.file_name}_freq_{freq_mhz:.3f}MHz.png")
                        
                        # 创建新图表并保存
                        fig = self.create_slice_plot(
                            slice_data, 
                            f"電流-頻率掃描切片 (電流: {current_val:.3f} A, 頻率: {freq_mhz:.3f} MHz)"
                        )
                        fig.savefig(slice_path, dpi=1000, bbox_inches='tight')
                        plt.close(fig)  # 关闭图表释放内存
                        
                        count += 1
                        self.progress.emit(int(count * 100 / total))
            
            if not self._cancelled:
                self.finished.emit()
        
        except Exception as e:
            self.error.emit(str(e))