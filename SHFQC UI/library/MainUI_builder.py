# library/ui_builder.py
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QStackedWidget, QWidget, QLabel, QScrollArea, QTabWidget,
    QSlider, QSplitter, QFrame, QTextEdit, QProgressBar
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)

class UIBuilder:
    # region: 主布局建立
    @staticmethod
    def create_main_ui(gui):
        """建構主視窗布局"""
        main_widget = QWidget()
        gui.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        #* 左側控制面板布局定義
        control_panel = UIBuilder.create_control_panel(gui)
        main_layout.addWidget(control_panel, stretch=2)
        
        #* 右側繪圖面板布局定義
        viz_panel = UIBuilder.create_viz_panel(gui)
        main_layout.addWidget(viz_panel, stretch=3)
        
        return main_widget

    @staticmethod
    def create_control_panel(gui):
        """建構左側控制面板布局"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        #* 設置實驗參數設置選項卡
        tab_widget = QTabWidget()
        tab_widget.addTab(UIBuilder.create_config_tab(gui), "實驗設置")
        tab_widget.addTab(UIBuilder.create_measure_tab(gui), "量測控制")
        
        layout.addWidget(tab_widget)
        scroll_area.setWidget(content_widget)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(scroll_area)
        return container

    @staticmethod
    def create_viz_panel(gui):
        """建構右側繪圖面板布局"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        #* 繪圖選項卡
        tab_widget = QTabWidget()
        tab_widget.addTab(UIBuilder.create_plot_tab(gui.time_plot), "時域 {單張} 量測")
        tab_widget.addTab(UIBuilder.create_power_plot_tab(gui), "時域 {振幅} 掃描")
        tab_widget.addTab(UIBuilder.create_freq_dep_plot_tab(gui), "時域 {頻率} 掃描")
        tab_widget.addTab(UIBuilder.create_current_freq_plot_tab(gui), "時域 {電流頻率} 掃描")
        tab_widget.addTab(UIBuilder.create_plot_tab(gui.freq_plot), "頻域 {單張} 量測")
        
        layout.addWidget(tab_widget)
        
        #* 數據保存組
        layout.addWidget(UIBuilder.create_save_group(gui))
        
        return panel
    # endregion
    
    # region: 實驗設置選項卡建立
    @staticmethod
    def create_config_tab(gui):
        """實驗設置選項卡布局"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        #* 設備配置組
        layout.addWidget(UIBuilder.create_device_group(gui))
        #* 主要參數组
        layout.addWidget(UIBuilder.create_signal_group(gui))
        #* 波形生成組
        layout.addWidget(UIBuilder.create_waveform_group(gui))
        #* 波形預覽組
        layout.addWidget(UIBuilder.create_wave_preview_group(gui))
        
        return tab
    
    @staticmethod
    def create_device_group(gui):
        """設備配置組件群組"""
        group = QGroupBox("儀器連線")
        layout = QFormLayout(group)

        #* 連線按鈕及狀態標籤布局
        row = QWidget()
        hbox = QHBoxLayout(row)
        hbox.addWidget(gui.btn_connect)
        hbox.addWidget(QLabel("狀態:"))
        hbox.addWidget(gui.lbl_connect_status)
        hbox.addStretch()
        layout.addRow(row)

        return group

    @staticmethod
    def create_signal_group(gui):
        """主要參數組件群組"""
        group = QGroupBox("主要參數設置")
        layout = QFormLayout(group)

        layout.addRow("輸入功率:", gui.input_range_combo)
        layout.addRow("輸出功率:", gui.output_range_combo)
        layout.addRow("中心頻率:", gui.center_freq_spin)
        layout.addRow("混頻頻率:", gui.digital_lo_spin)
        layout.addRow("波型增益:", gui.gain_spin)

        return group
    
    @staticmethod
    def create_waveform_group(gui):
        """波形生成組件群組"""
        group = QGroupBox("波形生成")
        layout = QFormLayout(group)
        
        #* 波形类型
        gui.wave_type_combo.addItems(["方波脈衝", "高斯脈衝", "指數脈衝", "自訂波形"])
        layout.addRow("波形類型:", gui.wave_type_combo)
        
        #* 基本参数
        layout.addRow("中段波型長度 (點數):", gui.pulse_length_spin)
        layout.addRow("前段波型長度 (點數):", gui.rise_samples_spin)
        layout.addRow("後段波型長度 (點數):", gui.fall_samples_spin)
        
        #* 波形特定参数堆叠
        
        gui.wave_param_stack = QStackedWidget()
        UIBuilder.create_wave_param_stack(gui)
        layout.addRow(gui.wave_param_stack)

        return group
    
    @staticmethod
    def create_wave_param_stack(gui):
        """創建波形生成組件堆棧"""
        #* 方波
        square_params_widget = QWidget()
        square_layout = QVBoxLayout(square_params_widget)
        square_layout.addWidget(QLabel("無額外參數"))
        gui.wave_param_stack.addWidget(square_params_widget)
        #* 高斯波
        gauss_params_widget = QWidget()
        gauss_layout = QFormLayout(gauss_params_widget)
        gauss_layout.addRow("前端標準差:", gui.front_std_spin)
        gauss_layout.addRow("末端標準差:", gui.end_std_spin)
        gui.wave_param_stack.addWidget(gauss_params_widget)
        #* 指數波
        exp_params_widget = QWidget()
        exp_layout = QFormLayout(exp_params_widget)
        exp_layout.addRow("前端時間常數:", gui.front_tau_spin)
        exp_layout.addRow("末端時間常數:", gui.end_tau_spin)
        exp_layout.addRow(gui.front_concave_check)
        exp_layout.addRow(gui.end_concave_check)
        gui.wave_param_stack.addWidget(exp_params_widget)
        #* 自訂義波型
        custom_params_widget = QWidget()
        custom_layout = QFormLayout(custom_params_widget)
        custom_layout.addRow("公式:", gui.custom_formula_edit)
        custom_layout.addRow(gui.parse_formula_btn)
        custom_layout.addRow("波型長度:", gui.custom_duration_spin)
        custom_layout.addRow("採樣點數:", gui.custom_points_spin)
        custom_layout.addRow(gui.custom_params_btn)
        custom_layout.addRow(gui.custom_params_label)
        gui.wave_param_stack.addWidget(custom_params_widget)
    
    @staticmethod
    def create_wave_preview_group(gui):
        """波型預覽組件群組"""
        group = QGroupBox("波形預覽")
        layout = QVBoxLayout(group)
        layout.addWidget(gui.wave_preview)
        return group
    # endregion
    
    # region: 實驗控制選項卡建立
    @staticmethod
    def create_measure_tab(gui):
        """量測控制選項卡布局"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        #* 實驗方案選擇
        scheme_group = QGroupBox("實驗方案選擇")
        scheme_layout = QHBoxLayout(scheme_group)
        scheme_layout.addWidget(QLabel("選擇實驗方案:"))
        scheme_layout.addWidget(gui.scheme_combo)
        scheme_layout.addStretch()
        layout.addWidget(scheme_group)
        
        #* 方案堆棧
        gui.scheme_stack = UIBuilder.create_scheme_stack(gui)
        layout.addWidget(gui.scheme_stack)
        
        #* YOKOGAWA控制组
        layout.addWidget(UIBuilder.create_yokogawa_group(gui))
        
        #* 量測控制按鈕組
        layout.addWidget(UIBuilder.create_ctrl_buttons(gui))
        
        #* 量測進度顯示
        layout.addWidget(gui.time_label)
        layout.addWidget(gui.progress_bar)
        
        return tab

    @staticmethod
    def create_scheme_stack(gui):
        """創建並初始化實驗方案堆棧"""
        scheme_stack = QStackedWidget()
        
        #* 方案1: 時域 {單張} 量測
        time_domain_widget = QWidget()
        time_layout = QVBoxLayout(time_domain_widget)
        time_layout.addWidget(UIBuilder.create_time_measure_group(gui))
        time_layout.addStretch()
        scheme_stack.addWidget(time_domain_widget)
        
        #* 方案2: 時域 {振幅} 量測
        power_widget = QWidget()
        power_layout = QVBoxLayout(power_widget)
        power_layout.addWidget(UIBuilder.create_power_dependent_time_group(gui))
        power_layout.addWidget(UIBuilder.create_power_dependent_power_group(gui))
        power_layout.addStretch()
        scheme_stack.addWidget(power_widget)
        
        #* 方案3: 時域 {頻率} 量測
        freq_scan_widget = QWidget()
        freq_scan_layout = QVBoxLayout(freq_scan_widget)
        freq_scan_layout.addWidget(UIBuilder.create_frequency_dependent_time_group(gui))
        freq_scan_layout.addWidget(UIBuilder.create_frequency_dependent_frequency_group(gui))
        freq_scan_layout.addStretch()
        scheme_stack.addWidget(freq_scan_widget)

        #* 方案4: 時域 {電流頻率} 掃描
        current_freq_widget = QWidget()
        current_freq_layout = QVBoxLayout(current_freq_widget)
        current_freq_layout.addWidget(UIBuilder.create_current_freq_time_group(gui))
        current_freq_layout.addWidget(UIBuilder.create_current_freq_frequency_group(gui))
        current_freq_layout.addWidget(UIBuilder.create_current_freq_current_group(gui))
        scheme_stack.addWidget(current_freq_widget)

        #* 方案5: 頻域 {單張} 量測
        freq_domain_widget = QWidget()
        freq_layout = QVBoxLayout(freq_domain_widget)
        freq_layout.addWidget(UIBuilder.create_freq_measure_group(gui))
        freq_layout.addStretch()
        scheme_stack.addWidget(freq_domain_widget)
        
        return scheme_stack

    @staticmethod
    def create_time_measure_group(gui):
        """時域 {單張} 量測組件群"""
        group = QGroupBox("時域 {單張} 設置")
        layout = QFormLayout(group)
        layout.addRow("量測時長:", gui.window_dur_spin_time)
        layout.addRow("觸發延遲:", gui.trigger_delay_spin_time)
        layout.addRow("平均次數:", gui.num_avg_spin_time)
        return group

    #* 時域 {振幅} 量測群組
    @staticmethod
    def create_power_dependent_time_group(gui):
        """時域 {振幅} 量測 (基礎) 組件群"""
        group = QGroupBox("時域基礎設置")
        layout = QFormLayout(group)
        layout.addRow("量測時長:", gui.window_dur_spin_power)
        layout.addRow("觸發延遲:", gui.trigger_delay_spin_power)
        layout.addRow("平均次數:", gui.num_avg_spin_power)
        return group

    @staticmethod
    def create_power_dependent_power_group(gui):
        """時域 {振幅} 量測 (振幅) 組件群"""
        group = QGroupBox("振幅掃描設置")
        layout = QFormLayout(group)
        layout.addRow("起始振幅:", gui.power_start_spin)
        layout.addRow("終止振幅:", gui.power_stop_spin)
        layout.addRow("量測點數:", gui.power_points_spin)
        return group

    #* 時域 {頻率} 量測
    @staticmethod
    def create_frequency_dependent_time_group(gui):
        """時域 {頻率} 量測 (基礎) 組件群"""
        group = QGroupBox("時域基礎設置")
        layout = QFormLayout(group)
        layout.addRow("量測時長:", gui.window_dur_spin_freq)
        layout.addRow("觸發延遲:", gui.trigger_delay_spin_freq)
        layout.addRow("平均次數:", gui.num_avg_spin_freq)
        return group
    
    @staticmethod
    def create_frequency_dependent_frequency_group(gui):
        """時域 {頻率} 量測 (頻率) 組件群"""
        group = QGroupBox("頻率掃描設置")
        layout = QFormLayout(group)
        layout.addRow("起始頻率:", gui.freq_dep_start_spin)
        layout.addRow("終止頻率:", gui.freq_dep_stop_spin)
        layout.addRow("量測點數:", gui.freq_dep_points_spin)
        return group

    #* 時域 {電流頻率} 掃描
    @staticmethod
    def create_current_freq_time_group(gui):
        """時域 {電流頻率} 量測 (基礎) 組件群"""
        group = QGroupBox("時域基礎設置")
        layout = QFormLayout(group)
        layout.addRow("量測時長:", gui.window_dur_spin_current_freq)
        layout.addRow("觸發延遲:", gui.trigger_delay_spin_current_freq)
        layout.addRow("平均次數:", gui.num_avg_spin_current_freq)
        return group
    
    @staticmethod
    def create_current_freq_frequency_group(gui):
        """時域 {電流頻率} 量測 (電流) 組件群"""
        group = QGroupBox("頻率掃描設置")
        layout = QFormLayout(group)
        layout.addRow("起始頻率:", gui.freq_start_current_freq)
        layout.addRow("終止頻率:", gui.freq_stop_current_freq)
        layout.addRow("量測點數:", gui.freq_points_current_freq)
        return group

    @staticmethod
    def create_current_freq_current_group(gui):
        """時域 {電流頻率} 量測 (電流) 組件群"""
        group = QGroupBox("電流掃描設置")
        layout = QFormLayout(group)
        
        #* 電流範圍設置
        layout.addRow("起始電流(mA):", gui.current_start_spin)
        layout.addRow("終止電流(mA):", gui.current_stop_spin)
        layout.addRow("量測點數:", gui.current_points_spin)
        
        #* YOKOGAWA設備選擇
        yoko_devices_group = QGroupBox("偵測DC設備")
        yoko_layout = QVBoxLayout(yoko_devices_group)
        yoko_layout.addWidget(gui.yoko_devices_contect)
        yoko_layout.addWidget(gui.yoko_status)
        layout.addRow(yoko_devices_group)
        
        #* YOKOGAWA設備連接
        layout.addRow(gui.link_yoko_devices_group)
        
        return group

    #* 頻域 {單張} 量測
    @staticmethod
    def create_freq_measure_group(gui):
        """頻域 {單張} 量測組件群"""
        group = QGroupBox("頻域 {單張} 設置")
        layout = QFormLayout(group)
        layout.addRow("起始頻率:", gui.lo_start_spin)
        layout.addRow("中止頻率:", gui.lo_stop_spin)
        layout.addRow("量測點數:", gui.lo_points_spin)
        layout.addRow("平均次數:", gui.avg_num_spin)
        layout.addRow("積分時間(us):", gui.int_time_spin)
        return group

    @staticmethod
    def create_yokogawa_group(gui):
        """YOKOGAWA控制组件群"""
        group = QGroupBox("其他儀器控制")
        layout = QVBoxLayout(group)
        layout.addWidget(gui.btn_control_yoko)
        layout.addStretch()
        return group
    
    @staticmethod
    def create_ctrl_buttons(gui):
        """控制按鈕群組"""
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.addWidget(gui.run_measure_btn)
        layout.addWidget(gui.run_power_btn)
        layout.addWidget(gui.run_freq_dep_btn)
        layout.addWidget(gui.run_current_freq_btn)
        layout.addWidget(gui.run_sweep_btn)
        layout.addWidget(gui.abort_btn)
        return group
    # endregion

    # region: 實驗控制選項卡建立
    @staticmethod
    def create_plot_tab(canvas):
        """創建時域、頻域 {單張} 量測繪圖卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = NavigationToolbar(canvas, tab)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        return tab
    
    @staticmethod
    def create_power_plot_tab(gui):
        """創建時域 {振幅} 量測繪圖卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        #* 使用分割器分割熱圖及切片
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        #* 上部分：熱圖及滑塊
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        overview_toolbar = NavigationToolbar(gui.power_overview, top_widget)
        top_layout.addWidget(overview_toolbar)
        top_layout.addWidget(gui.power_overview)
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("選定振幅數據:"))
        slider_layout.addWidget(gui.power_slider)
        slider_layout.addWidget(gui.power_label)
        top_layout.addLayout(slider_layout)
        
        #* 下部分：切片
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        slice_toolbar = NavigationToolbar(gui.power_slice, bottom_widget)
        bottom_layout.addWidget(slice_toolbar)
        bottom_layout.addWidget(gui.power_slice)
        
        #* 分割器布局設置
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([300, 600]) #1:2
        layout.addWidget(splitter)
        return tab
    
    @staticmethod
    def create_freq_dep_plot_tab(gui):
        """創建時域 {頻率} 量測繪圖卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        #* 使用分割器分割熱圖及切片
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        #* 上部分：熱圖及滑塊
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        overview_toolbar = NavigationToolbar(gui.freq_dep_overview, top_widget)
        top_layout.addWidget(overview_toolbar)
        top_layout.addWidget(gui.freq_dep_overview)
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("選定頻率數據:"))
        slider_layout.addWidget(gui.freq_dep_slider)
        slider_layout.addWidget(gui.freq_dep_label)
        top_layout.addLayout(slider_layout)
        
        #* 下部分：切片
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        slice_toolbar = NavigationToolbar(gui.freq_dep_slice, bottom_widget)
        bottom_layout.addWidget(slice_toolbar)
        bottom_layout.addWidget(gui.freq_dep_slice)
        
        #* 分割器布局設置
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([300, 600]) #1:2
        layout.addWidget(splitter)
        return tab

    @staticmethod
    def create_current_freq_plot_tab(gui):
        """創建時域 {電流頻率} 量測繪圖卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        #* 使用分割器分割熱圖及切片
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        #* 上部分：熱圖
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        overview_toolbar = NavigationToolbar(gui.current_freq_overview, top_widget)
        top_layout.addWidget(overview_toolbar)
        top_layout.addWidget(gui.current_freq_overview)
        
        #* 上部分：電流滑塊
        current_slider_layout = QHBoxLayout()
        current_slider_layout.addWidget(QLabel("選定電流:"))
        current_slider_layout.addWidget(gui.current_slider)
        current_slider_layout.addWidget(gui.current_label)
        top_layout.addLayout(current_slider_layout)
        
        #* 上部分：頻率滑塊
        freq_slider_layout = QHBoxLayout()
        freq_slider_layout.addWidget(QLabel("選定頻率:"))
        freq_slider_layout.addWidget(gui.freq_slider_current_freq)
        freq_slider_layout.addWidget(gui.freq_label_current_freq)
        top_layout.addLayout(freq_slider_layout)
        
        #* 下部分：切片
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        slice_toolbar = NavigationToolbar(gui.current_freq_slice, bottom_widget)
        bottom_layout.addWidget(slice_toolbar)
        bottom_layout.addWidget(gui.current_freq_slice)
        
        #* 分割器布局設置
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)
        return tab

    # endregion
    @staticmethod
    def create_save_group(gui):
        """數據保存控件組"""
        group = QGroupBox("數據保存區")
        layout = QHBoxLayout(group)
        layout.addWidget(gui.save_data_btn)
        layout.addWidget(gui.load_data_btn)
        layout.addWidget(gui.save_config_btn)
        return group