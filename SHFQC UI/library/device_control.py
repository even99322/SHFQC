import threading
import numpy as np
import time
from typing import Tuple,List

from zhinst.toolkit import SHFQAChannelMode, Waveforms

class SHFQC:
    """
        Now, please use digital method to generate carrier within 200MHz,
        and use center frequency to tune rest of it, it has resolution of 200MHz.
        The demod should be done manually, might add weight into SHFQC in the future.
        
        And use output_range to set maxima output, the waveform is normalized of it,
        e,g, for output_range = 0dbm, waveform array of 0.5 will be 0dbm * 0.5.
    """
    def __init__(self, device, session):
        self.session = session
        self.device = device
        self.QA_CHANNEL_INDEX = 0
        self.QA_SCOPE_CHANNEL = 0

        # default_setting
        self.device.qachannels[self.QA_CHANNEL_INDEX].input.on(0)
        self.device.qachannels[self.QA_CHANNEL_INDEX].output.on(0)
        self.device.qachannels[self.QA_CHANNEL_INDEX].configure_channel(
            center_frequency=5e9,
            input_range=-10, # dB
            output_range=-15, # dB
            mode=SHFQAChannelMode.READOUT,
        )
    
    def qa_input(self, onoff_in_01):
        """Input on or off. 0 for off and 1 for on."""
        self.device.qachannels[self.QA_CHANNEL_INDEX].input.on(onoff_in_01)

    def qa_output(self, onoff_in_01):
        """Output on or off. 0 for off and 1 for on."""
        self.device.qachannels[self.QA_CHANNEL_INDEX].output.on(onoff_in_01)

    def qa_input_range(self, range_in_dbm):
        """Maxima input power, the measured data is normalized of it.
        
        for example, for input_range is 0dbm, 0.5 means 0dbm * 0.5.
        """
        self.device.qachannels[self.QA_CHANNEL_INDEX].input.range(range_in_dbm)

    def qa_output_range(self, range_in_dbm):
        """Maxima output power, the output is normalized of it.
        
        for example. for output_power is 0dbm, 0.5 means 0dbm * 0.5.
        """
        self.device.qachannels[self.QA_CHANNEL_INDEX].output.range(range_in_dbm)

    def qa_center_freq(self, freq_in_Hz):
        """frequecnt for up/down conversion analog LO, has resolution of 0.2GHz."""
        freq_in_MHz = freq_in_Hz / 1e+6
        if freq_in_MHz % 200 != 0:
            raise Exception(f'resolution of center frequency is 200 MHz, input value {freq_in_Hz} is not allowed.')
        self.device.qachannels[self.QA_CHANNEL_INDEX].centerfreq(freq_in_Hz)

    def qa_assign_single_complex_waveform(self, complex_waveform, markers=None, slot: int=0):
        """Assign one waveform to a specific slot, default is first slot, with index 0.

        It will store the waveform in first slot, with index 0, by default.

        Example usage:
        >>> shfqc.qa_assign_single_complex_waveform(
        >>>     complex_waveform=np.array([
        >>>         0+0.1j, 0.2+0.4j, 0.4+0j, 0.2+0.4j, 0.1+0.2j
        >>>     ])
        >>> )
        """
        readout_pulses = Waveforms()
        readout_pulses.assign_waveform(
            slot=slot,
            wave1=complex_waveform,
            markers=markers
        )
        print(readout_pulses)
        self.device.qachannels[self.QA_CHANNEL_INDEX].generator.write_to_waveform_memory(readout_pulses)
        return readout_pulses

    def qa_assign_single_iq_waveform(self, I_waveform, Q_waveform, markers=None, slot: int=0):
        """Assign one waveform to a specific slot, default is first slot, with index 0.
        
        It will store the waveform in first slot, with index 0, by default.

        Example usage:
        >>> shfqc.qa_assign_single_iq_waveform(
        >>>     I_waveform=np.array([  0, 0.2, 0.4, 0.2, 0.1]),
        >>>     Q_waveform=np.array([0.1, 0.4,   0, 0.4, 0.2]),
        >>> )
        """
        readout_pulses = Waveforms()
        readout_pulses.assign_waveform(
            slot=slot,
            wave1=I_waveform,
            wave2=Q_waveform,
            markers=markers
        )
        self.device.qachannels[self.QA_CHANNEL_INDEX].generator.write_to_waveform_memory(readout_pulses)
        return readout_pulses

    def qa_set_scope_config(
            self, window_duration: float, n_avg: int, 
            trigger_delay=200e-9
        ):
        """set config of scope, it will influence time domain measurement since we take data from it.

        Args:
            window_duration(float): the display time of scope.
            trigger_delay(float): the delay time after recive trigger, for start of measurement.

        Example usage:       
        >>> shfqc.qa_set_scope_config(
        >>>     window_duration=700e-9,
        >>>     n_avg=20,
        >>>     trigger_delay=100e-9
        >>> )
        """
        SHFQA_SAMPLING_FREQUENCY = 2e+9
        self.device.scopes[self.QA_SCOPE_CHANNEL].configure(
        input_select={self.QA_SCOPE_CHANNEL: f"channel{self.QA_CHANNEL_INDEX}_signal_input"},
        num_samples=int(window_duration * SHFQA_SAMPLING_FREQUENCY),
        trigger_input=f"channel{self.QA_CHANNEL_INDEX}_sequencer_monitor0",
        num_segments=1,
        num_averages=n_avg,
        trigger_delay=trigger_delay,
    )

    def qa_measure_signal(self, n_mea, readout_duration):
        """Perform measurement and return the result.
        
        Example usage:
        >>> # measured time domain signal
        >>> data = shfqc.qa_measure_signal(
        >>>     n_mea=20, # should be the same as n_avg in the scope
        >>>     readout_duration=700e-9 # should be the same as window_duration in the scope
        >>> )
        >>> # plot the result, user can scale x and y, by your knowlege
        >>> t = np.arange(len(data)) * 1/SAMPLING_RATE
        >>> plt.plot(t*1e+9, np.real(data), label='Re')
        >>> plt.plot(t*1e+9, np.imag(data), label='Im')
        >>> plt.plot(t*1e+9, np.abs(data), label='Abs')
        >>> plt.xlabel('time / ns')
        >>> plt.ylabel('signal / qa_input_range')
        >>> plt.legend()
        >>> plt.show()
        """

        self.device.qachannels[self.QA_CHANNEL_INDEX].generator.configure_sequencer_triggering(
            aux_trigger="software_trigger0",
            play_pulse_delay=0
        )

        # upload sequencer program
        seqc_program = f"""
            repeat({n_mea}) {{
                waitDigTrigger(1);
                startQA(QA_GEN_{0}, 0x0, true,  0, 0x0);
            }}
        """
        self.device.qachannels[self.QA_CHANNEL_INDEX].generator.load_sequencer_program(seqc_program)

        # Start a measurement
        self.device.scopes[self.QA_SCOPE_CHANNEL].run(single=True)
        self.device.qachannels[self.QA_CHANNEL_INDEX].generator.enable_sequencer(single=True)
        self.device.start_continuous_sw_trigger(
            num_triggers=n_mea, wait_time=readout_duration
        )

        # get results to calculate weights and plot data
        scope_data, *_ = self.device.scopes[0].read()
        return scope_data[0]


    def qa_measure_spectrum(
            self, center_f, lo_start_f, lo_stop_f, 
            lo_n_pts, n_avg, 
            input_range=-10, output_range=-15, gain=0.8,
            int_time=100e-6, plot=True
        ):
        """measure spectrum using sweeper.

        Args:
            center_f(float): the upconversion LO frequency, equals center frequecny of specturm.\
                It has resolution of 200MHz, so only 4, 4.2, 4.4 GHz etc... can be used.
            lo_start_f(float): start freq for ditigal LO to be sweep, -500~500MHz is allowed.
            lo_stop_f(float): stop freq for ditigal LO to be sweep, -500~500MHz is allowed.
            input_range(int): input maxima power in dbm, data is normalized of it.
            output_range(int): output power in dbm.
            gain (float): lo gain factor.

        Explanation:
            The sweep is measure by tuning digital LO, set by lo_start/stop_f.
            The LO output signal is up conversion by center_f. center_f has 
            resolution of 0.2GHz, ditigal LO has range of -500MHz~500MHz.
        
        Example usage:
        >>> spectrum_data = shfqc.qa_measure_spectrum(
        >>>     center_f=4e+9, lo_start_f=-200e+6, lo_stop_f=+200e+6, 
        >>>     lo_n_pts=401, n_avg=20, 
        >>>     gain=0.7, input_range=-10, output_range=-15,
        >>>     plot=True
        >>> )
        """
        # check frequency is allowed or not
        center_f_in_MHz = center_f / 1e+6
        if center_f_in_MHz % 200 != 0:
            raise Exception(f'resolution of center frequency is 200 MHz, input value {center_f} is not allowed.')
        for f in (lo_start_f, lo_stop_f):
            if f > 500e+6 or f < -500e+6:
                raise Exception(f'Range for digital LO is -500MHz ~ +500MHz, {f} is out of range.')

        sweeper = self.session.modules.shfqa_sweeper
        sweeper.device(self.device)

        sweeper.sweep.start_freq(lo_start_f)
        sweeper.sweep.stop_freq(lo_stop_f)
        sweeper.sweep.num_points(lo_n_pts)
        sweeper.sweep.oscillator_gain(gain)
        # The sequencer is used by default but can be disabled manually
        # sweeper.sweep.mode("host-driven")
        sweeper.sweep.mode("sequencer-based")

        sweeper.average.integration_time(int_time)
        sweeper.average.num_averages(n_avg)
        sweeper.average.mode("sequential")


        sweeper.rf.channel(self.QA_CHANNEL_INDEX)
        sweeper.rf.input_range(input_range)
        sweeper.rf.output_range(output_range)
        sweeper.rf.center_freq(center_f)

        result = sweeper.run()
        if plot: sweeper.plot()
        return result['vector']
    

class YOKOGAWA:
    """高階YOKOGAWA控制物件"""
    
    def __init__(self, id: str, visa_resource):
        self.id = id
        self.visa_resource = visa_resource

    def visa_write(self, command):
        """寫入SCPI命令到YOKOGAWA"""
        self.visa_resource.write(command)
        
    def clear_error_flag(self):
        """清除錯誤LED指示燈"""
        self.visa_write('*CLS')
        
    def operation_setting(self, func: str, range: float):
        """設定功能和範圍"""
        self.visa_write(f":SOUR:FUNC {func}; RANG {range}")
        
    def output(self, on_or_off: str):
        """設定輸出開啟或關閉"""
        self.visa_write(f":OUTP {on_or_off}")
        
    def output_value(self, value: float):
        """設定輸出源電平值"""
        self.visa_write(f":SOUR:LEV {value}")
        
    def sweep(self, goal_value, delta_time, delta_value) -> threading.Thread:
        """執行掃描到目標值"""
        def inner(goal_value, delta_time, delta_value):
            curr_value = self.get_output_value()
            if goal_value < curr_value:
                delta_value = -delta_value
            source_levels = np.arange(curr_value, goal_value, delta_value)
            for level in source_levels:
                self.output_value(level)
                time.sleep(delta_time)
            time.sleep(delta_time)
            self.output_value(goal_value)
        
        thread = threading.Thread(
            target=inner, args=(goal_value, delta_time, delta_value) 
        )
        thread.start()
        return thread

    def visa_query(self, command):
        """查詢SCPI命令並返回響應"""
        return self.visa_resource.query(command)
        
    def get_operation_setting(self) -> Tuple[str, float]:
        """獲取當前操作設定"""
        func = self.visa_query(':SOUR:FUNC?')[:-1]
        range = float(self.visa_query(':SOUR:RANG?'))
        return func, range
        
    def get_output_status(self) -> str:
        """獲取輸出狀態"""
        states_str = self.visa_query(':OUTP?')
        if states_str == '1\n': return 'ON'
        elif states_str == '0\n': return 'OFF'
        
    def get_output_value(self) -> float:
        """獲取輸出源電平值"""
        return float(self.visa_query(':SOUR:LEV?'))

    @staticmethod
    def wait_for_sweeping(*threads: List[threading.Thread]):
        """等待所有掃描執行緒完成"""
        for thread in threads:
            thread.join()
            
    @staticmethod
    def demag_single(yoko, path: list, sweep_delta_time=0.05, sweep_delta_current=2e-3):
        """執行單個YOKOGAWA消磁腳本"""
        for point in path:
            yoko.sweep(point, sweep_delta_time, sweep_delta_current).join()
            
    @staticmethod
    def demag(yokos: list, path: list, sweep_delta_time=0.05, sweep_delta_current=2e-3):
        """執行多個YOKOGAWA消磁腳本"""
        threads = []
        for yoko in yokos:
            threads.append(threading.Thread( 
                target=YOKOGAWA.demag_single, args=(yoko, path, sweep_delta_time, sweep_delta_current) 
            ))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()