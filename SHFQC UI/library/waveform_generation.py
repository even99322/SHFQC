import numpy as np
from scipy.signal.windows import gaussian
from .Formula_Parser import FormulaParser

def generate_waveform(params, error_callback=None):
    """
    根据参数生成波形
    
    参数:
    params (dict): 包含所有波形参数的字典
    formula_parser (FormulaParser): 公式解析器实例
    error_callback (function, optional): 错误回调函数
    
    返回:
    np.ndarray: 生成的波形数据
    """
    formula_parser = FormulaParser()
    wave_type = params['wave_type']
    
    try:
        if wave_type == "高斯脈衝":
            return _generate_gaussian_waveform(params)
                
        elif wave_type == "方波脈衝":
            return _generate_square_waveform(params)
                
        elif wave_type == "指數脈衝":
            return _generate_exponential_waveform(params)
                
        elif wave_type == "自訂波形":
            return _generate_custom_waveform(params, formula_parser, error_callback)
                
        else:
            if error_callback:
                error_callback(f"未知的波形類型: {wave_type}")
            return None
            
    except Exception as e:
        if error_callback:
            error_callback(f"波形生成錯誤: {str(e)}")
        return None

def _generate_gaussian_waveform(params):
    """生成高斯脉冲波形"""
    waveform=np.ones(params['pulse_length'])
    front_len=params['rise_samples']
    end_len=params['fall_samples']
    front_std_devi=params['front_std']
    end_std_devi=params['end_std']

    front = gaussian(2 * front_len, front_std_devi)[:front_len]
    end = gaussian(2 * end_len, end_std_devi)[-end_len:]

    if np.iscomplexobj(waveform):
        front = front.astype(complex)
        end = end.astype(complex)

    waveform = np.concatenate([front, waveform, end])

    return _apply_gain_and_mixing(waveform, params)

def _generate_square_waveform(params):
    """生成方波脉冲波形"""
    
    waveform = np.ones(params['pulse_length'])
    front_len=params['rise_samples']
    end_len=params['fall_samples']

    front = np.zeros(front_len, dtype=waveform.dtype)
    end = np.zeros(end_len, dtype=waveform.dtype)

    waveform = np.concatenate([front, waveform, end])

    return _apply_gain_and_mixing(waveform, params)

def _generate_exponential_waveform(params):
    """生成指数脉冲波形"""
    
    waveform = np.ones(params['pulse_length'])
    front_len=params['rise_samples']
    end_len=params['fall_samples']
    front_tau=params['front_tau']
    end_tau=params['end_tau']
    front_concave_up=params['front_concave']
    end_concave_up=params['end_concave']

    t_front = np.arange(front_len)
    if front_concave_up:
        front = np.exp(-t_front / front_tau)[::-1]
    else:
        front = 1 - np.exp(-t_front / front_tau)

    t_end = np.arange(end_len)
    if end_concave_up:
        end = np.exp(-t_end / end_tau)
    else:
        end = (1 - np.exp(-t_front / front_tau))[::-1]

    # Cast to complex if needed
    if np.iscomplexobj(waveform):
        front = front.astype(complex)
        end = end.astype(complex)

    waveform = np.concatenate([front, waveform, end])

    return _apply_gain_and_mixing(waveform, params)

def _generate_custom_waveform(params, formula_parser, error_callback):
    """生成自定义波形"""
    # 获取自定义参数
    formula = params['custom_formula']
    if not formula:
        if error_callback:
            error_callback("請輸入自訂波型公式")
        return None
        
    # 解析公式
    a=formula_parser.parse(formula=formula)
    if not formula_parser.parse(formula):
        if error_callback:
            error_callback("公式解析失敗")
        return None
    # 获取变量（排除时间变量）
    variables = [v for v in formula_parser.variables if v not in ('t', 'time')]
    
    # 检查参数是否完整
    if not _check_custom_params(variables, params['custom_params'], error_callback):
        return None
        
    # 创建时间数组
    duration = params['custom_duration']
    points = params['custom_points']
    t_array = np.linspace(0, duration, points)
    
    # 计算波形 - 使用向量化计算避免数组转换错误
    waveform = np.vectorize(
        lambda t: formula_parser.evaluate(
            {**params['custom_params'], 't': t}, 
            np.array([t])  # 传入单个时间点
        )[0]
    )(t_array)
    
    # 确保是复数类型
    waveform = waveform.astype(complex)
    
    return _apply_gain_and_mixing(waveform, params)

def _apply_gain_and_mixing(waveform, params):
    """应用增益和数字混频"""
    # 应用增益
    waveform = waveform * params['gain']
    
    # 如果设定了digital_lo，进行数字混频
    if params['digital_lo'] != 0:
        sampling_rate=2e+9
        lo_phase=0
        lo_frequency=params['digital_lo']

        t = np.arange(len(waveform)) * 1/sampling_rate
        carrier = np.exp(1j* 2*np.pi* lo_frequency * t + lo_phase)
        waveform = waveform * carrier

    return waveform

def _check_custom_params(variables, custom_params, error_callback=None):
    """检查自定义参数是否完整"""
    if not variables:
        return True
        
    missing_params = [v for v in variables if v not in custom_params]
    if missing_params:
        if error_callback:
            error_callback(f"參數缺失: 缺少以下參數值: {', '.join(missing_params)}\n請點擊'解析公式'按鈕設置參數")
        return False
    return True