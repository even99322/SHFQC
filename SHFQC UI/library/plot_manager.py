import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

class PlotManager:
    def __init__(self, gui):
        self.gui = gui
        self.power_amplitudes = None
        self.freq_lo_values = None
        self.current_values = None
        self.power_data = None
        self.freq_dep_data = None
        self.current_freq_data = None
    # region: 時域 {單張} 量測繪製
    #* 時域 {單張} 量測繪製
    def update_time_plot(self, data):
        """更新時域 {單張} 繪圖"""
        self.gui.time_plot.figure.clear()
        ax = self.gui.time_plot.figure.add_subplot(111)
        t = np.arange(len(data)) * 0.5e-9
        ax.plot(t*1e9, np.abs(data), label='電壓')
        ax.set_xlabel('時間 (ns)')
        ax.set_ylabel('電壓 (V)')
        ax.legend()
        ax.grid(True)
        self.gui.time_plot.draw()
    # endregion

    # region: 頻域 {單張} 量測繪製
    #* 頻域 {單張} 量測繪製
    def update_freq_plot(self, data):
        """更新頻域 {單張} 繪圖"""
        self.gui.freq_plot.figure.clear()
        ax = self.gui.freq_plot.figure.add_subplot(111)
        freq = data['freq']
        data = data['data']
        data_power = (np.abs(data)**2)*10
        data_dBm = 10*np.log10(data_power)
        ax.plot(freq/1e9, data_dBm)
        ax.set_xlabel('頻率 (GHz)')
        ax.set_ylabel('幅度 (dB)')
        ax.grid(True)
        self.gui.freq_plot.draw()
    # endregion

    # region: 時域 {振幅} 掃描繪製
    #* 時域 {振幅} 量測繪製
    def update_power_plot(self, data):
        """更新時域 {振幅} 繪圖"""
        self.power_amplitudes = data['amp']
        self.gui.power_amplitudes = data['amp']
        self.power_data = data['data']
        self.gui.power_data = data['data']
        #* 滑條設置
        self.gui.power_slider.setEnabled(True)
        self.gui.power_slider.setRange(0, len(self.gui.power_amplitudes) - 1)
        self.gui.power_slider.setValue(0)

        self._plot_power_overview()
        self.update_power_slice(0)
    
    def _plot_power_overview(self):
        """繪製時域 {振幅} 2D熱圖"""
        if not self.gui.power_data or not self.gui.power_amplitudes:
            return

        amplitudes = np.array(self.gui.power_amplitudes)
        waveforms = np.array(self.gui.power_data)
        time_axis = np.arange(waveforms.shape[1]) * 0.5e-9
        self.gui.power_time_axis = time_axis

        self.gui.power_overview.figure.clear()
        ax = self.gui.power_overview.figure.add_subplot(111)
        im = ax.imshow(np.abs(waveforms), cmap='coolwarm', aspect='auto',
                    extent=[time_axis[0] * 1e9, time_axis[-1] * 1e9,
                            amplitudes[0], amplitudes[-1]], origin='lower')
        
        #* 添加振幅標記線
        current_amp = amplitudes[self.gui.power_slider.value()]
        self.gui.power_line = ax.axhline(y=current_amp, color='yellow', linestyle='--', linewidth=2)
        
        self.gui.power_overview.figure.colorbar(im, ax=ax).set_label("|single| (V)")
        ax.set_xlabel("時間 (ns)")
        ax.set_ylabel("振幅")
        ax.set_title("時域 {振幅} 量測 2D熱圖")
        self.gui.power_overview.draw()

    def update_power_slice(self, index):
        """更新時域 {振幅} 指定振幅切片圖"""
        if not self.gui.power_data or index >= len(self.gui.power_data):
            return

        amplitude = self.gui.power_amplitudes[index]
        waveform = self.gui.power_data[index]
        time_axis = self.gui.power_time_axis * 1e9

        self.gui.power_label.setText(f"選定振幅: {amplitude:.3f}")

        #* 更新熱圖上的標記線
        if hasattr(self.gui, 'power_line'):
            self.gui.power_line.set_ydata([amplitude, amplitude])
            self.gui.power_overview.draw()

        fig = self.gui.power_slice.figure
        fig.clear()
        ax = fig.add_subplot(111)

        ax.plot(time_axis, np.abs(waveform), 'b-', label='振幅')
        #ax.plot(time_axis, np.real(waveform), 'r--', label='實部', alpha=0.3)
        #ax.plot(time_axis, np.imag(waveform), 'g-.', label='虛部', alpha=0.3)
        ax.set_xlabel("時間 (ns)")
        ax.set_ylabel("電壓 (V)")
        ax.set_title(f"振幅比例為 {amplitude:.3f} 的切片")
        ax.legend()
        ax.grid(True)

        self.gui.power_slice.draw()
    # endregion

    # region: 時域 {頻率} 掃描繪製
    #* 時域 {頻率} 量測繪製
    def update_freq_dep_plot(self, data):
        """更新時域 {頻率} 繪圖"""
        self.freq_lo_values = data['lo_values']
        self.freq_dep_data = data['data']
        self.gui.freq_lo_values = data['lo_values']
        self.gui.freq_dep_data = data['data']

        #* 滑條設置
        self.gui.freq_dep_slider.setEnabled(True)
        self.gui.freq_dep_slider.setRange(0, len(self.gui.freq_lo_values) - 1)
        self.gui.freq_dep_slider.setValue(0)

        self._plot_freq_dep_overview()
        self.update_freq_dep_slice(0)

    def _plot_freq_dep_overview(self):
        """繪製時域 {頻率} 2D熱圖"""
        if not self.gui.freq_dep_data or not self.gui.freq_lo_values:
            return

        freqs = np.array(self.gui.freq_lo_values)
        waveforms = np.array(self.gui.freq_dep_data)
        time_axis = np.arange(waveforms.shape[1]) * 0.5e-9 
        self.gui.freq_dep_time_axis = time_axis

        self.gui.freq_dep_overview.figure.clear()
        ax = self.gui.freq_dep_overview.figure.add_subplot(111)
        im = ax.imshow(np.abs(waveforms), cmap='coolwarm', aspect='auto',
                       extent=[time_axis[0] * 1e9, time_axis[-1] * 1e9,
                               freqs[0]/1e6, freqs[-1]/1e6], origin='lower')
        
        #* 添加頻率標記線
        current_freq = freqs[self.gui.freq_dep_slider.value()] / 1e6
        self.gui.freq_dep_line = ax.axhline(y=current_freq, color='yellow', linestyle='--', linewidth=2)
        
        self.gui.freq_dep_overview.figure.colorbar(im, ax=ax).set_label("|single| (V)")
        ax.set_xlabel("時間 (ns)")
        ax.set_ylabel("混頻頻率 (MHz)")
        ax.set_title("時域 {頻率} 量測 2D熱圖")
        self.gui.freq_dep_overview.draw()

    def update_freq_dep_slice(self, index):
        """更新時域 {頻率} 指定振幅切片圖"""
        if not self.gui.freq_dep_data or index >= len(self.gui.freq_dep_data):
            return

        freq = self.gui.freq_lo_values[index]
        waveform = self.gui.freq_dep_data[index]
        time_axis = self.gui.freq_dep_time_axis * 1e9

        self.gui.freq_dep_label.setText(f"選定頻率: {freq/1e6:.3f} MHz")

        #* 更新熱圖上的標記線
        if hasattr(self.gui, 'freq_dep_line'):
            self.gui.freq_dep_line.set_ydata([freq/1e6, freq/1e6])
            self.gui.freq_dep_overview.draw()

        fig = self.gui.freq_dep_slice.figure
        fig.clear()
        ax = fig.add_subplot(111)

        ax.plot(time_axis, np.abs(waveform), 'b-', label='振幅')
        #ax.plot(time_axis, np.real(waveform), 'r--', label='實部', alpha=0.3)
        #ax.plot(time_axis, np.imag(waveform), 'g-.', label='虛部', alpha=0.3)
        ax.set_xlabel("時間 (ns)")
        ax.set_ylabel("電流 (V)")
        ax.set_title(f"混頻頻率為 {freq/1e6:.3f} MHz 的切片")
        ax.legend()
        ax.grid(True)

        self.gui.freq_dep_slice.draw()

    # endregion

    # region: 時域 {電流頻率} 掃描繪製
    #* 時域 {電流頻率} 量測繪製
    def update_current_freq_plot(self, data):
        """更新時域 {電流頻率} 繪圖"""
        self.current_values = data['curr']
        self.freq_lo_values = data['lo_values']
        self.current_freq_data = data['data']
        self.gui.current_values = data['curr'] 
        self.gui.freq_values = data['lo_values']
        self.gui.current_freq_data = data['data'] # 三維資料 [電流點][頻率點][時間點]
        
        #* 滑條設置
        self.gui.current_slider.setEnabled(True)
        self.gui.freq_slider_current_freq.setEnabled(True)
        self.gui.current_slider.setRange(0, len(self.gui.current_values) - 1)
        self.gui.freq_slider_current_freq.setRange(0, len(self.gui.freq_values) - 1)
        self.gui.current_slider.setValue(0)
        self.gui.freq_slider_current_freq.setValue(0)
        
        #* 繪製初始的熱圖和切片
        self._plot_current_freq_overview(0)
        self.update_current_freq_slice(0, 0)

    def _plot_current_freq_overview(self, current_index):
        """繪製時域 {電流頻率} 2D熱圖"""
        #* 獲取指定電流值
        current = self.gui.current_values[current_index] * 1e3
        freq_len = len(self.gui.freq_values)

        #* 獲取當前電流值對應的頻率2D數據
        freq_data = self.gui.current_freq_data[current_index]
        waveforms = np.array(freq_data)
        time_points = waveforms.shape[1]
        time_axis = np.arange(time_points) * 0.5e-9
        
        self.gui.current_freq_overview.figure.clear()
        ax = self.gui.current_freq_overview.figure.add_subplot(111)
        
        im = ax.imshow(np.abs(waveforms), cmap='coolwarm', aspect='auto',
                    extent=[time_axis[0] * 1e9, time_axis[-1] * 1e9,
                            self.gui.freq_values[0]/1e6, self.gui.freq_values[-1]/1e6], 
                    origin='lower')
        
        #* 添加頻率標記線
        current_freq = self.gui.freq_values[self.gui.freq_slider_current_freq.value()] / 1e6
        self.gui.freq_line = ax.axhline(y=current_freq, color='yellow', linestyle='--', linewidth=2)
        
        self.gui.current_freq_overview.figure.colorbar(im, ax=ax).set_label("|single| (V)")
        ax.set_xlabel("時間 (ns)")
        ax.set_ylabel("頻率 (MHz)")
        ax.set_title(f"電流為 {current:.3f} mA 的時域 [電流頻率] 量測 2D熱圖")
        self.gui.current_freq_overview.draw()

    def update_current_freq_slice(self, current_index, freq_index):
        """更新時域 {電流頻率} 指定電流頻率切片圖"""        
        if (current_index >= len(self.gui.current_values) or 
            freq_index >= len(self.gui.freq_values) or
            current_index >= len(self.gui.current_freq_data) or
            freq_index >= len(self.gui.current_freq_data[current_index])):
            return
        
        #* 獲取數據
        current = self.gui.current_values[current_index] * 1e3
        freq = self.gui.freq_values[freq_index]
        waveform = self.gui.current_freq_data[current_index][freq_index]
        
        #* 更新標籤
        self.gui.current_label.setText(f"{current:.3f} mA")
        self.gui.freq_label_current_freq.setText(f"{freq/1e6:.3f} MHz")
        
        #* 更新熱圖上的標記線
        self._plot_current_freq_overview(current_index)
        if hasattr(self.gui, 'freq_line'):
            self.gui.freq_line.set_ydata([freq/1e6, freq/1e6])
            self.gui.current_freq_overview.draw()

        fig = self.gui.current_freq_slice.figure
        fig.clear()
        ax = fig.add_subplot(111)
        
        t = np.arange(len(waveform)) * 0.5e-9 * 1e9
        ax.plot(t, np.abs(waveform), 'b-', label='振幅')
        #ax.plot(t, np.real(waveform), 'r--', label='實部', alpha=0.3)
        #ax.plot(t, np.imag(waveform), 'g-.', label='虛部', alpha=0.3)
        ax.set_xlabel("時間 (ns)")
        ax.set_ylabel("電壓 (V)")
        ax.set_title(f"電流: {current:.3f} mA, 頻率: {freq/1e6:.3f} MHz 的切片")
        ax.legend()
        ax.grid(True)
        
        self.gui.current_freq_slice.draw()
    # endregion