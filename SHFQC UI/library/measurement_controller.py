import numpy as np
import time

from PyQt6.QtCore import QThread, QObject, pyqtSignal, QMutex

from .waveform_generation import generate_waveform
from .Formula_Parser import FormulaParser
from .RealTimeMonitorDialog import RealTimeMonitorDialog

class MeasurementController(QObject):
    #* 回傳信號定義
    #? 量測回傳信號
    time_data_updated = pyqtSignal(np.ndarray)
    freq_data_updated = pyqtSignal(dict)
    power_data_updated = pyqtSignal(dict)
    freq_dep_data_updated = pyqtSignal(dict)
    current_freq_data_updated = pyqtSignal(dict)
    #? 通用信號
    progress_signal = pyqtSignal(float, float)
    measurement_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, gui, shfqc=None):
        super().__init__()
        self.shfqc = shfqc
        self.gui = gui
        self.measurement_thread = None
        
        # 数据存储
        self.time_domain_data = None
        self.freq_domain_data = None
        self.power_data = []
        self.power_amplitudes = []
        self.freq_dep_data = []
        self.freq_lo_values = []
        self.current_freq_data = []
        self.current_values = []
        self.freq_values = []

    def run_measurement(self, mode, params, yokos=None):
        """啟動量測線程"""
        if self.measurement_thread and self.measurement_thread.isRunning():
            return False

        #* 重新生成波型
        current_waveform = generate_waveform(
            params,
            error_callback=self.error_occurred.emit
        )
        if current_waveform is None:
            return False
        params['waveform'] = current_waveform

        #* 創建並啟用線程
        self.measurement_thread = MeasurementThread(self.shfqc, {
            **params,
            'mode': mode,
            'yokos': yokos or [],
            'n_mea': params['n_avg']
        })
        
        #* 創建量測數據動態顯示窗口
        if mode in ['時域 {振幅} 掃描', '時域 {頻率} 掃描', '時域 {電流頻率} 掃描']:
            
            self.realtime_dialog = RealTimeMonitorDialog(mode, self.gui) 
            self.realtime_dialog.show()

        
        #* 連接量測信號
        if mode == '時域 {單張} 量測':
            self.time_domain_data = None
            self.measurement_thread.update_signal.connect(self._handle_time_data)
        elif mode == '頻域 {單張} 量測':
            self.freq_domain_data = None
            self.measurement_thread.update_signal.connect(self._handle_freq_data)
        elif mode == '時域 {振幅} 掃描':
            self.power_data = []
            self.power_amplitudes = []
            self.measurement_thread.update_signal.connect(self._handle_power_data)
            
            #* 連接量測數據動態顯示窗口
            if hasattr(self, 'realtime_dialog'):
                self.measurement_thread.update_signal.connect(self.realtime_dialog.update_plot)
                self.measurement_thread.update_signal.connect(self.realtime_dialog.update_params)
                self.progress_signal.connect(self.realtime_dialog.update_progress)
                
        elif mode == '時域 {頻率} 掃描':
            self.freq_dep_data = []
            self.freq_lo_values = []
            self.measurement_thread.update_signal.connect(self._handle_freq_dep_data)
            
            #* 連接量測數據動態顯示窗口
            if hasattr(self, 'realtime_dialog'):
                self.measurement_thread.update_signal.connect(self.realtime_dialog.update_plot)
                self.measurement_thread.update_signal.connect(self.realtime_dialog.update_params)
                self.progress_signal.connect(self.realtime_dialog.update_progress)
                
        elif mode == '時域 {電流頻率} 掃描':
            self.current_freq_data = []
            self.current_values = []
            self.freq_values = []
            self.cruu_len = params['curr_freq_dep_curr_points']
            self.freq_len = params['curr_freq_dep_freq_point']
            self.measurement_thread.update_signal.connect(self._handle_current_freq_data)
            
            #* 連接量測數據動態顯示窗口
            if hasattr(self, 'realtime_dialog'):
                self.measurement_thread.update_signal.connect(self.realtime_dialog.update_plot)
                self.measurement_thread.update_signal.connect(self.realtime_dialog.update_params)
                self.progress_signal.connect(self.realtime_dialog.update_progress)

        #* 通用信號連接
        self.measurement_thread.finished_signal.connect(self._handle_measurement_finished)
        self.measurement_thread.progress_signal.connect(self.progress_signal.emit)
        self.measurement_thread.error_signal.connect(self.error_occurred.emit)
        self.measurement_thread.start()
        
        return True
    
    # region: 量測數據處理
    def _handle_time_data(self, data):
        """處理時域 {單張} 量測數據"""
        self.time_domain_data = data
        self.time_data_updated.emit(self.time_domain_data)

    def _handle_freq_data(self, data):
        """處理頻域 {單張} 量測數據"""
        self.freq_domain_data = {
            'freq': np.linspace(
                self.measurement_thread.params['lo_start'],
                self.measurement_thread.params['lo_stop'],
                len(data)
            ) + self.measurement_thread.params['center_freq'],
            'data': data
        }
        self.freq_data_updated.emit(self.freq_domain_data)

    def _handle_power_data(self, data):
        """處理時域 {振幅} 掃描數據"""
        if isinstance(data, tuple) and len(data) == 2 and data[0] == 'params':
            #* 更新實時監控的參數
            if hasattr(self, 'realtime_dialog'):
                self.realtime_dialog.update_params(data[1])
        elif isinstance(data, tuple) and len(data) == 3 and data[0] == 'data':
            amp, waveform = data[1], data[2]
            self.power_amplitudes.append(amp)
            self.power_data.append(waveform)
            
            #* 更新實時監控的參數
            if hasattr(self, 'realtime_dialog'):
                self.realtime_dialog.update_plot((amp, waveform))
        elif isinstance(data, tuple) and len(data) == 1:
            self.power_dep_data_back = {
                'amp':self.power_amplitudes,
                'data':self.power_data
            }
            self.power_data_updated.emit(self.power_dep_data_back)

    def _handle_freq_dep_data(self, data):
        """處理時域 {頻率} 掃描數據"""
        #* 处理参数更新
        if isinstance(data, tuple) and len(data) == 2 and data[0] == 'params':
            # 更新实时监控的参数
            if hasattr(self, 'realtime_dialog'):
                self.realtime_dialog.update_params(data[1])
            return
                
        # 处理测量数据
        if isinstance(data, tuple) and len(data) == 3 and data[0] == 'data':
            freq, waveform = data[1], data[2]
            self.freq_lo_values.append(freq)
            self.freq_dep_data.append(waveform)
            
            # 更新实时监控的绘图
            if hasattr(self, 'realtime_dialog'):
                self.realtime_dialog.update_plot((freq, waveform))
                
        # 处理完成信号
        elif isinstance(data, tuple) and len(data) == 1 and data[0] == 'complete':
            self.freq_dep_data_back = {
                'lo_values': self.freq_lo_values,
                'data': self.freq_dep_data
            }
            self.freq_dep_data_updated.emit(self.freq_dep_data_back)

    def _handle_current_freq_data(self, data):
        """處理時域 {電流頻率} 掃描數據"""
        # 处理参数更新
        if isinstance(data, tuple) and len(data) == 2 and data[0] == 'params':
            # 更新实时监控的参数
            if hasattr(self, 'realtime_dialog'):
                self.realtime_dialog.update_params(data[1])
            return
                
        # 处理测量数据
        if isinstance(data, tuple) and len(data) == 4 and data[0] == 'data':
            current, freq, waveform = data[1], data[2], data[3]
            self.current_values.append(current)
            self.freq_values.append(freq)
            self.current_freq_data.append(waveform)
            
            # 更新实时监控的绘图
            if hasattr(self, 'realtime_dialog'):
                self.realtime_dialog.update_plot((current, freq, waveform))
                
        # 处理完成信号
        elif isinstance(data, tuple) and len(data) == 1 and data[0] == 'complete':
            data_3d = []
            for i in range(self.cruu_len):
                row = []
                for j in range(self.freq_len):
                    # 直接使用原始数据，不重新组织
                    row.append(self.current_freq_data[i*self.freq_len + j])
                data_3d.append(row)
                
            self.current_freq_data_back = {
                'curr': self.current_values[:self.cruu_len],  # 只取有效电流值
                'lo_values': self.freq_values[:self.freq_len],  # 只取有效频率值
                'data': data_3d  # 三维数据 [电流点][频率点][时间点]
            }
            self.current_freq_data_updated.emit(self.current_freq_data_back)
    # endregion

    def _handle_measurement_finished(self):
        """处理测量完成"""
        self.measurement_thread = None
        self.shfqc.qa_input(0)
        self.shfqc.qa_output(0)
        
        # 关闭实时监控对话框
        if hasattr(self, 'realtime_dialog') and self.realtime_dialog.isVisible():
            self.realtime_dialog.accept()
            del self.realtime_dialog
            
        self.measurement_finished.emit()

    def abort_measurement(self):
        """终止当前测量工作"""
        if self.measurement_thread and self.measurement_thread.isRunning():
            self.measurement_thread.stop()
        

# region: 量測線程
class MeasurementThread(QThread):
    update_signal = pyqtSignal(object)          #* 更新量測數據
    finished_signal = pyqtSignal()              #* 任務完成信號
    error_signal = pyqtSignal(str)              #* 錯誤信號
    progress_signal = pyqtSignal(float, float)  #* 量測進度信號

    def __init__(self, shfqc, params):
        super().__init__()
        self.shfqc = shfqc
        self.params = params
        self.formula_parser = FormulaParser
        self._is_running = True
        self.mutex = QMutex()

    def run(self):
        try:
            self.shfqc.qa_input(1)
            self.shfqc.qa_output(1)
            if self.params['mode'] == '時域 {單張} 量測':
                self._run_time_domain()
            elif self.params['mode'] == '頻域 {單張} 量測':
                self._run_frequency_sweep()
            elif self.params['mode'] == '時域 {振幅} 掃描':
                self._run_power_dependent()
            elif self.params['mode'] == '時域 {頻率} 掃描':
                self._run_frequency_dependent()
            elif self.params['mode'] == '時域 {電流頻率} 掃描':
                self.run_current_frequency_dependent()
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()

    def _run_time_domain(self):
        """時域 {單張} 量測流程"""
        #* 主參數設置
        self.shfqc.qa_input_range(self.params['input_range'])
        self.shfqc.qa_output_range(self.params['output_range'])
        self.shfqc.qa_center_freq(self.params['center_freq'])
        
        #* 上傳波型
        self.shfqc.qa_assign_single_complex_waveform(self.params['waveform'])
        
        #* 示波器設置
        self.shfqc.qa_set_scope_config(
            window_duration=self.params['window_duration'],
            n_avg=self.params['n_avg'],
            trigger_delay=self.params['trigger_delay']
        )

        #* 執行量測
        data = self.shfqc.qa_measure_signal(
                n_mea=self.params['n_avg'],
                readout_duration=self.params['window_duration']
            )
        
        #* 回傳數據
        self.update_signal.emit(data)

    def _run_frequency_sweep(self):
        """頻域 {單張} 量測流程"""
        #* 參數設置
        spectrum_data = self.shfqc.qa_measure_spectrum(
            center_f=self.params['center_freq'],
            lo_start_f=self.params['lo_start'],
            lo_stop_f=self.params['lo_stop'],
            lo_n_pts=self.params['lo_points'],
            n_avg=self.params['avg_num'],
            input_range=self.params['input_range'],
            output_range=self.params['output_range'],
            int_time=self.params['int_time']*1e-6,
            plot=False
        )

        #* 回傳數據
        self.update_signal.emit(spectrum_data)
        
    def _run_power_dependent(self):
        """時域 {振幅} 掃描"""
        #* 主參數設置
        self.shfqc.qa_input_range(self.params['input_range'])
        self.shfqc.qa_output_range(self.params['output_range'])
        self.shfqc.qa_center_freq(self.params['center_freq'])
        
        #* 主參數設置
        self.shfqc.qa_set_scope_config(
            window_duration=self.params['window_duration'],
            n_avg=self.params['n_avg'],
            trigger_delay=self.params['trigger_delay']
        )
        
        #* 生成振幅待量測數組
        amplitudes = np.linspace(
            self.params['power_dep_start'],
            self.params['power_dep_stop'],
            self.params['power_dep_points']
        )
        
        #* 測量所有振幅數據
        #? 進度回報初始化
        left_time_avg=10
        time_avg=[0]*left_time_avg
        tick=0
        #? 執行量測迴圈
        for i, amp in enumerate(amplitudes):
            if not self._is_running:
                break
            start_time = time.time()
            #* 生成當前振幅的波形
            current_waveform = amp * self.params['waveform']
            
            #* 上傳波形
            time.sleep(1*1e-6)
            self.shfqc.qa_assign_single_complex_waveform(current_waveform)
            
            #* 執行量測
            data = self.shfqc.qa_measure_signal(
                n_mea=self.params['n_avg'],
                readout_duration=self.params['window_duration']
            )
            
            #* 回傳數據
            #? 回傳進度
            end_time = time.time()
            execution_time = end_time - start_time
            time_avg[tick]=execution_time
            tick+=1
            if tick==left_time_avg:
                tick=0
            progress = (i + 1) / len(amplitudes) * 100
            left_time = (len(amplitudes) - i)*np.average(time_avg)

            current_params = {
                '當前振幅': f"{amp:.4f}",
                '進度': f"{i+1}/{len(amplitudes)}",
                '當前平均時間': f"{execution_time:.2f}秒"
            }
            self.update_signal.emit(('params', current_params))
            
            # 发送测量数据
            self.update_signal.emit(('data', amp, data))

            self.progress_signal.emit(progress,left_time)
        
        # 發送完成信號
        self.update_signal.emit(('complete',))
        
    def _run_frequency_dependent(self):
        """頻率依賴量測流程 (新增)"""
        # 配置设备参数
        self.shfqc.qa_input(1)
        self.shfqc.qa_output(1)
        self.shfqc.qa_input_range(self.params['input_range'])
        self.shfqc.qa_output_range(self.params['output_range'])
        self.shfqc.qa_center_freq(self.params['center_freq'])
        
        # 设置示波器
        self.shfqc.qa_set_scope_config(
            window_duration=self.params['window_duration'],
            n_avg=self.params['n_avg'],
            trigger_delay=self.params['trigger_delay']
        )
        
        # 生成頻率數組
        freqs = np.linspace(
            self.params['freq_dep_start'],
            self.params['freq_dep_stop'],
            self.params['freq_dep_points']
        )
        
        # 測量每個頻率點
        left_time_avg=10
        time_avg=[0]*left_time_avg
        tick=0
        for i, freq in enumerate(freqs):
            if not self._is_running:
                break
            start_time = time.time()
            # 更新波型
            self.params['digital_lo']=freq
            current_waveform = generate_waveform(
                self.params
            )
            self.params['waveform'] = current_waveform
            
            # 上傳波形
            time.sleep(1*1e-6)
            self.shfqc.qa_assign_single_complex_waveform(self.params['waveform'])
            
            # 測量
            data = self.shfqc.qa_measure_signal(
                n_mea=self.params['n_avg'],
                readout_duration=self.params['window_duration']
            )
            
            # 發送當前數據點（頻率和整個波形）
            end_time = time.time()
            execution_time = end_time - start_time
            time_avg[tick]=execution_time
            tick+=1
            if tick==left_time_avg:
                tick=0
            progress = (i + 1) / len(freqs) * 100
            left_time = (len(freqs) - i)*np.average(time_avg)
            # 发送当前参数给实时监控
            current_params = {
                '當前頻率': f"{freq/1e6:.4f} MHz",
                '進度': f"{i+1}/{len(freqs)}",
                '當前平均時間]': f"{execution_time:.2f}秒"
            }
            self.update_signal.emit(('params', current_params))
            
            # 发送测量数据
            self.update_signal.emit(('data', freq, data))

            self.progress_signal.emit(progress,left_time)
        
        # 發送完成信號
        self.update_signal.emit(('complete',))
    
    def run_current_frequency_dependent(self):
        """頻率依賴量測流程 (新增)"""
        # yoko 連接檢測
        yokos = self.params['yokos']
        
        # 配置设备参数
        self.shfqc.qa_input(1)
        self.shfqc.qa_output(1)
        self.shfqc.qa_input_range(self.params['input_range'])
        self.shfqc.qa_output_range(self.params['output_range'])
        self.shfqc.qa_center_freq(self.params['center_freq'])
        
        # 设置示波器
        self.shfqc.qa_set_scope_config(
            window_duration=self.params['window_duration'],
            n_avg=self.params['n_avg'],
            trigger_delay=self.params['trigger_delay']
        )


        # 生成電流數組
        currs = np.linspace(
            self.params['curr_freq_dep_curr_start'],
            self.params['curr_freq_dep_curr_stop'],
            self.params['curr_freq_dep_curr_points']
        )*1e-3
        # 生成頻率數組
        freqs = np.linspace(
            self.params['curr_freq_dep_freq_start'],
            self.params['curr_freq_dep_freq_stop'],
            self.params['curr_freq_dep_freq_point']
        )

        left_time_avg=10
        time_avg=[0]*left_time_avg
        tick=0
        for i, curr in enumerate(currs):
            if not self._is_running:
                break
            
            for yoko in yokos:
                yoko.output_value(curr)
            for j, freq in enumerate(freqs):
                if not self._is_running:
                    break
                start_time = time.time()
                # 更新波型
                self.params['digital_lo']=freq
                current_waveform = generate_waveform(
                    self.params,
                )
                self.params['waveform'] = current_waveform
                
                # 上傳波形
                time.sleep(1*1e-6)
                self.shfqc.qa_assign_single_complex_waveform(self.params['waveform'])
                
                # 測量
                data = self.shfqc.qa_measure_signal(
                    n_mea=self.params['n_avg'],
                    readout_duration=self.params['window_duration']
                )
                
                # 發送當前數據點（頻率和整個波形）
                end_time = time.time()
                execution_time = end_time - start_time
                time_avg[tick]=execution_time
                tick+=1
                if tick==left_time_avg:
                    tick=0
                progress = (i*len(freqs) + j + 1) / (len(currs)*len(freqs)) * 100
                left_time = (len(freqs)*len(currs) - i*len(freqs)-j)*np.average(time_avg)
                # 发送当前参数给实时监控
                current_params = {
                    '當前電流': f"{curr*1000:.4f} mA",
                    '當前頻率': f"{freq/1e6:.4f} MHz",
                    '進度': f"{i+1}/{len(currs)} (電流), {j+1}/{len(freqs)} (頻率)",
                    '當前平均時間': f"{execution_time:.2f}秒"
                }
                self.update_signal.emit(('params', current_params))
                
                # 发送测量数据
                self.update_signal.emit(('data', curr, freq, data))

                self.progress_signal.emit(progress,left_time)
            
        # 發送完成信號
        self.update_signal.emit(('complete',))


    def stop(self):
        """安全停止测量"""
        self.mutex.lock()
        self._is_running = False
        self.mutex.unlock()

