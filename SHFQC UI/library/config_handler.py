import configparser
import os

class ConfigHandler:
    def __init__(self, config_path):
        self.config_path = config_path 
        
    def load(self, gui):
        """加載配置文件"""
        config = configparser.ConfigParser()
        
        #* 無文件則建立預設配置文件
        if not os.path.exists(self.config_path):
            self.save(gui)
            return
            
        try:
            config.read(self.config_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            try:
                config.read(self.config_path, encoding='utf-8-sig')
            except Exception as e:
                print(f"讀取配置文件失敗: {e}")
                self.save(gui)
                return

        #* 主要參數設置
        if config.has_section('主要參數'):
            #* 參數設置
            input_val = float(config['主要參數'].get('輸入功率', -10))
            output_val = float(config['主要參數'].get('輸出功率', -15))
            gui.center_freq_spin.setValue(float(config['主要參數'].get('中心頻率', 5e9)))
            gui.digital_lo_spin.setValue(float(config['主要參數'].get('混頻頻率', 1e6)))
            gui.gain_spin.setValue(float(config['主要參數'].get('波型增益', 1.0)))

            #* range數值查找及設置
            input_idx = self._find_combo_index(gui.input_range_combo, input_val)
            output_idx = self._find_combo_index(gui.output_range_combo, output_val)
            gui.input_range_combo.setCurrentIndex(input_idx)
            gui.output_range_combo.setCurrentIndex(output_idx)

        #* 波型參數設置
        if config.has_section('波型參數'):
            #? 通用波型設置
            gui.pulse_length_spin.setValue(int(config['波型參數'].get('通用波型_中段波長', 800)))
            gui.rise_samples_spin.setValue(int(config['波型參數'].get('通用波型_前段波長', 40)))
            gui.fall_samples_spin.setValue(int(config['波型參數'].get('通用波型_後段波長', 25)))
            #? 高斯波型設置
            gui.front_std_spin.setValue(int(config['波型參數'].get('高斯波型_前段標準差', 12)))
            gui.end_std_spin.setValue(int(config['波型參數'].get('高斯波型_後段標準差', 5)))
            #? 指數波型設置
            gui.front_tau_spin.setValue(float(config['波型參數'].get('指數波型_前段時間常數', 5.0)))
            gui.end_tau_spin.setValue(float(config['波型參數'].get('指數波型_後段時間常數', 10.0)))
            gui.front_concave_check.setChecked(config['波型參數'].get('指數波型_前段凹面方向', 'False') == 'True')
            gui.end_concave_check.setChecked(config['波型參數'].get('指數波型_後段凹面方向', 'True') == 'True')
            #? 自訂義波型設置
            gui.custom_formula_edit.setText(config['波型參數'].get('自訂波型_自訂波型公式', 'sin(2*pi*f*t)'))
            gui.custom_points_spin.setValue(int(config['波型參數'].get('自訂波型_自訂波型點數', 1000)))
            gui.custom_duration_spin.setValue(float(config['波型參數'].get('自訂波型_自訂波型長度', 1e-6)))
            #? 自訂義波型參數
            custom_params = config['波型參數'].get('自訂波型_自訂波型參數', '')
            if custom_params:
                try:
                    if custom_params.startswith("{") and custom_params.endswith("}"):
                        gui.custom_params = eval(custom_params)
                        param_text = ", ".join([f"{k}={v}" for k, v in gui.custom_params.items()])
                        gui.custom_params_label.setText(f"參數: {param_text}")
                    else:
                        raise ValueError("Invalid dictionary format")
                except:
                    gui.custom_params = {}
                    gui.custom_params_label.setText("參數: 無")
        #* 量測參數設置
        if config.has_section('量測參數'):
            #? 時域 {單張} 量測參數設置
            gui.window_dur_spin_time.setValue(int(config['量測參數'].get('時域單張_量測時長', 2000)))
            gui.trigger_delay_spin_time.setValue(int(config['量測參數'].get('時域單張_觸發延遲', 100)))
            gui.num_avg_spin_time.setValue(int(config['量測參數'].get('時域單張_平均次數', 20)))

            #? 時域 {振幅} 量測參數設置
            gui.window_dur_spin_power.setValue(int(config['量測參數'].get('時域振幅_量測時長', 2000)))
            gui.trigger_delay_spin_power.setValue(int(config['量測參數'].get('時域振幅_觸發延遲', 100)))
            gui.num_avg_spin_power.setValue(int(config['量測參數'].get('時域振幅_平均次數', 20)))

            gui.power_start_spin.setValue(float(config['量測參數'].get('時域振幅_起始振幅', 0.1)))
            gui.power_stop_spin.setValue(float(config['量測參數'].get('時域振幅_終止振幅', 1.0)))
            gui.power_points_spin.setValue(int(config['量測參數'].get('時域振幅_量測點數', 10)))
            #? 時域 {頻率} 量測參數設置
            gui.window_dur_spin_freq.setValue(int(config['量測參數'].get('時域頻率_量測時長', 2000)))
            gui.trigger_delay_spin_freq.setValue(int(config['量測參數'].get('時域頻率_觸發延遲', 100)))
            gui.num_avg_spin_freq.setValue(int(config['量測參數'].get('時域頻率_平均次數', 20)))

            gui.freq_dep_start_spin.setValue(float(config['量測參數'].get('時域頻率_起始頻率', 1e6)))
            gui.freq_dep_stop_spin.setValue(float(config['量測參數'].get('時域頻率_終止頻率', 10e6)))
            gui.freq_dep_points_spin.setValue(int(config['量測參數'].get('時域頻率_量測點數', 10)))
            #? 時域 {電流頻率} 量測參數設置
            gui.window_dur_spin_current_freq.setValue(int(config['量測參數'].get('時域電流頻率_量測時長', 2000)))
            gui.trigger_delay_spin_current_freq.setValue(int(config['量測參數'].get('時域電流頻率_觸發延遲', 100)))
            gui.num_avg_spin_current_freq.setValue(int(config['量測參數'].get('時域電流頻率_平均次數', 20)))

            gui.current_start_spin.setValue(float(config['量測參數'].get('時域電流頻率_起始電流', 0)))
            gui.current_stop_spin.setValue(float(config['量測參數'].get('時域電流頻率_終止電流', 0)))
            gui.current_points_spin.setValue(int(config['量測參數'].get('時域電流頻率_電流量測點數', 101)))

            gui.freq_start_current_freq.setValue(float(config['量測參數'].get('時域電流頻率_起始頻率', 0)))
            gui.freq_stop_current_freq.setValue(float(config['量測參數'].get('時域電流頻率_終止頻率', 0)))
            gui.freq_points_current_freq.setValue(int(config['量測參數'].get('時域電流頻率_頻率量測點數', 10)))

            #? 頻域 {單張} 量測參數設置
            gui.lo_start_spin.setValue(float(config['量測參數'].get('頻域單張_起始頻率', -80e6)))
            gui.lo_stop_spin.setValue(float(config['量測參數'].get('頻域單張_中止頻率', -60e6)))
            gui.lo_points_spin.setValue(int(config['量測參數'].get('頻域單張_量測點數', 401)))
            gui.avg_num_spin.setValue(int(config['量測參數'].get('頻域單張_平均次數', 10)))
            gui.int_time_spin.setValue(int(config['量測參數'].get('頻域單張_積分時間', 200)))

    def save(self, gui):
        """保存配置文件"""
        config = configparser.ConfigParser()

        def to_str(value):
            return str(value) if not isinstance(value, str) else value

        config['主要參數'] = {
            '輸入功率': to_str(gui.input_range_combo.currentData()),
            '輸出功率': to_str(gui.output_range_combo.currentData()),
            '中心頻率': to_str(gui.center_freq_spin.value()),
            '混頻頻率': to_str(gui.digital_lo_spin.value()),
            '波型增益': to_str(gui.gain_spin.value())
        }

        custom_params = getattr(gui, 'custom_params', {})
        custom_params_str = str(custom_params) if custom_params else "{}"

        config['波型參數'] = {
            '通用波型_中段波長': to_str(gui.pulse_length_spin.value()),
            '通用波型_前段波長': to_str(gui.rise_samples_spin.value()),
            '通用波型_後段波長': to_str(gui.fall_samples_spin.value()),

            '高斯波型_前段標準差': to_str(gui.front_std_spin.value()),
            '高斯波型_後段標準差': to_str(gui.end_std_spin.value()),

            '指數波型_前段時間常數': to_str(gui.front_tau_spin.value()),
            '指數波型_後段時間常數': to_str(gui.end_tau_spin.value()),
            '指數波型_前段凹面方向': to_str(gui.front_concave_check.isChecked()),
            '指數波型_後段凹面方向': to_str(gui.end_concave_check.isChecked()),

            '自訂波型_自訂波型公式': to_str(gui.custom_formula_edit.text()),
            '自訂波型_自訂波型點數': to_str(gui.custom_points_spin.value()),
            '自訂波型_自訂波型長度': to_str(gui.custom_duration_spin.value()),
            '自訂波型_自訂波型參數': custom_params_str
        }

        config['量測參數'] = {
            '時域單張_量測時長': to_str(gui.window_dur_spin_time.value()),
            '時域單張_觸發延遲': to_str(gui.trigger_delay_spin_time.value()),
            '時域單張_平均次數': to_str(gui.num_avg_spin_time.value()),

            '時域振幅_量測時長': to_str(gui.window_dur_spin_power.value()),
            '時域振幅_觸發延遲': to_str(gui.trigger_delay_spin_power.value()),
            '時域振幅_平均次數': to_str(gui.num_avg_spin_power.value()),
            '時域振幅_起始振幅': to_str(gui.power_start_spin.value()),
            '時域振幅_終止振幅': to_str(gui.power_stop_spin.value()),
            '時域振幅_量測點數': to_str(gui.power_points_spin.value()),

            '時域頻率_量測時長': to_str(gui.window_dur_spin_freq.value()),
            '時域頻率_觸發延遲': to_str(gui.trigger_delay_spin_freq.value()),
            '時域頻率_平均次數': to_str(gui.num_avg_spin_freq.value()),
            '時域頻率_起始頻率': to_str(gui.freq_dep_start_spin.value()),
            '時域頻率_終止頻率': to_str(gui.freq_dep_stop_spin.value()),
            '時域頻率_量測點數': to_str(gui.freq_dep_points_spin.value()),

            '時域電流頻率_量測時長': to_str(gui.window_dur_spin_current_freq.value() if hasattr(gui, 'window_dur_spin_current_freq') else 2000),
            '時域電流頻率_觸發延遲': to_str(gui.trigger_delay_spin_current_freq.value() if hasattr(gui, 'trigger_delay_spin_current_freq') else 100),
            '時域電流頻率_平均次數': to_str(gui.num_avg_spin_current_freq.value() if hasattr(gui, 'num_avg_spin_current_freq') else 20),
            '時域電流頻率_起始電流': to_str(gui.current_start_spin.value()),
            '時域電流頻率_終止電流': to_str(gui.current_stop_spin.value()),
            '時域電流頻率_電流量測點數': to_str(gui.current_points_spin.value()),
            '時域電流頻率_起始頻率': to_str(gui.freq_start_current_freq.value()),
            '時域電流頻率_終止頻率': to_str(gui.freq_stop_current_freq.value()),
            '時域電流頻率_頻率量測點數': to_str(gui.freq_points_current_freq.value()),
            
            '頻域單張_起始頻率': to_str(gui.lo_start_spin.value()),
            '頻域單張_中止頻率': to_str(gui.lo_stop_spin.value()),
            '頻域單張_量測點數': to_str(gui.lo_points_spin.value()),
            '頻域單張_平均次數': to_str(gui.avg_num_spin.value()),
            '頻域單張_積分時間': to_str(gui.int_time_spin.value())
        }
        
        with open(self.config_path, 'w', encoding='utf-8-sig') as configfile:
            config.write(configfile)

    def _find_combo_index(self, combo, value):
        """在combo中尋找最接近的數值索引"""
        closest_idx = 0
        min_diff = float('inf')
        for idx in range(combo.count()):
            item_val = combo.itemData(idx)
            if item_val is None:
                continue
            try:
                diff = abs(float(item_val) - float(value))
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = idx
            except (TypeError, ValueError):
                continue
        return closest_idx