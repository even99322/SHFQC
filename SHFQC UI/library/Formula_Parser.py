import cmath
import numpy as np
import ast

class FormulaParser:
    """分析數學公式並返回參數字典"""
    
    # 自訂義數學函式白名單
    MATH_FUNCTIONS = {
        'sin': cmath.sin, 'cos': cmath.cos, 'tan': cmath.tan,
        'exp': cmath.exp, 'log': cmath.log, 'sqrt': cmath.sqrt,
        'abs': abs, 'phase': cmath.phase, 'real': lambda z: z.real,
        'imag': lambda z: z.imag, 'conj': np.conjugate,
        'pi': cmath.pi, 'e': cmath.e, 'j': 1j, 'i': 1j,
        'sinc': lambda x: np.sinc(x/np.pi) if isinstance(x, np.ndarray) else (np.sinc(x/np.pi) if x != 0 else 1)
    }
    
    def __init__(self):
        self.variables = set() # 參數名稱儲存
        self.parameters = {} #參數數值儲存
        self.tree = None
        
    def parse(self, formula: str):
        """解析公式并返回AST"""
        self.variables.clear()
        try:
            # 確保公式以表達式形式處理
            if not formula.strip().startswith('('):
                formula = f"({formula})"
                
            self.tree = ast.parse(formula, mode='eval')
            self._collect_variables(self.tree.body)
            return True
        except SyntaxError as e:
            raise ValueError(f"公式語法錯誤: {e.msg} (位置 {e.lineno}:{e.offset})")
            
    def _collect_variables(self, node: ast.AST):
        """變量名蒐集"""
        if isinstance(node, ast.Name):
            if node.id not in self.MATH_FUNCTIONS:
                self.variables.add(node.id)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.MATH_FUNCTIONS:
                for arg in node.args:
                    self._collect_variables(arg)
        elif isinstance(node, (ast.BinOp, ast.UnaryOp)):
            self._collect_variables(node.left) if hasattr(node, 'left') else None
            self._collect_variables(node.operand) if hasattr(node, 'operand') else None
            self._collect_variables(node.right) if hasattr(node, 'right') else None
        elif isinstance(node, ast.Compare):
            self._collect_variables(node.left)
            for comp in node.comparators:
                self._collect_variables(comp)
        else:
            for child in ast.iter_child_nodes(node):
                self._collect_variables(child)

    def evaluate(self, parameters: dict, t_array: np.ndarray = None):
        """計算公式值"""
        if self.tree is None:
            raise ValueError("需先解析公式")
        
        # 添加時間數組如果存在
        if t_array is not None:
            parameters['t'] = t_array
            parameters['time'] = t_array
        
        missing = self.variables - parameters.keys()
        if missing:
            raise ValueError(f"缺少參數: {missing}")
        
        env = {**self.MATH_FUNCTIONS, **parameters}
        
        try:
            code = compile(self.tree, '<string>', 'eval')
            value = eval(code, {'__builtins__': None}, env)
            
            # 確保返回的是數組
            if isinstance(value, (int, float, complex)):
                return np.full_like(t_array, value)
            return value
        except Exception as e:
            raise ValueError(f"計算錯誤: {str(e)}")