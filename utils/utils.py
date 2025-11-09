import logging
import math
import os
import re
import json
from datetime import datetime

def dict_to_text(data_dict):
    """
    Convert a dictionary to a text string, removing items with NaN values.
    
    Args:
        data_dict (dict): The input dictionary to be converted.
    
    Returns:
        str: The resulting text with key-value pairs, excluding NaN values.
    """
    # Filter out keys with NaN values
    cleaned_dict = {k: v for k, v in data_dict.items() if v is not None and not (isinstance(v, float) and math.isnan(v))}
    
    # Convert cleaned dictionary to a text format
    text = '\n'.join([f"{key}: {value}" for key, value in cleaned_dict.items()])
    text = text.replace("patient_id", "患者ID")
    text = text.replace("name", "姓名")
    text = text.replace("sex", "性别")
    text = text.replace("age", "年龄")
    text = text.replace("report_time", "影像报告报告时间")
    text = text.replace("report_find", "影像报告所见")
    text = text.replace("history_present_illness", "现病史")
    text = text.replace("history_past_illness", "既往史")
    text = text.replace("family_medical_history", "家族史")
    text = text.replace("physical_examination", "体格检查")
    text = text.replace("B27", "HLA-B27检查结果")
    text = text.replace("CRP", "C反应蛋白(CRP)")
    text = text.replace("ESR", "红细胞沉降率(ESR)")
    return text

import re
import json

def extract_json_from_text(text):
    """
    尝试从 LLM 输出文本中提取 JSON 内容，兼容 markdown 包裹、多行格式等。

    Args:
        text (str): LLM 的返回文本，可能包含 markdown 样式或多行 JSON。

    Returns:
        (bool, dict): 是否成功解析 + JSON 数据（失败返回 None）
    """
    text = text.strip()

    # 尝试先去除 markdown 包裹
    text = re.sub(r"```[jJ][sS][oO][nN]([\u4e00-\u9fa5：:]*)", "", text)  # 移除 ```json 等
    text = text.replace("```", "").strip()

    try:
        # 第一种尝试：直接解析整个文本
        return True, json.loads(text)
    except Exception:
        pass

    try:
        # 第二种尝试：匹配 {...} 内容
        match = re.search(r"{[\s\S]*}", text)
        if match:
            json_text = match.group()
            return True, json.loads(json_text)
    except Exception:
        pass

    print("未找到或无法解析 JSON 数据")
    return False, None

    
        
def setup_logger(log_path):
    """
    Set up the logger for the DiagnosisAgent.
    """
    if not os.path.exists(os.path.dirname(log_path)):
        os.makedirs(os.path.dirname(log_path))
        
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create file handler and set level to debug
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the file handler to logger
    logger.addHandler(file_handler)

    return logger

class TxtLog(object):
    def __init__(self, log_file_path):
        '''
        Initialize the TxtLog.
        :param log_file_path: 日志文件路径。若为 None，则禁用日志功能。
        '''
        if log_file_path is None:
            self.log_file_path = None
            self.disabled = True
            return
        self.disabled = False
        self.log_file_path = log_file_path
        if not os.path.exists(log_file_path):
            log_file_dir = os.path.dirname(log_file_path)
            if not os.path.exists(log_file_dir):
                os.makedirs(log_file_dir)
            with open(log_file_path, 'w') as file:
                file.write("")

    def info(self, message):
        '''
        Log a message to the log file.
        :param message: The message to log.
        '''
        if self.disabled:
            return
        log_type = "INFO"
        if isinstance(message, dict):
            message = json.dumps(message, ensure_ascii=False)
        elif not isinstance(message, str):
            message = str(message)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{log_type}] {message}\n"
        with open(self.log_file_path, 'a') as file:
            file.write(log_entry)
        print(log_entry)

    def error(self, message):
        '''
        Log an error message to the log file.
        :param message: The error message to log.
        '''
        if self.disabled:
            return
        log_type = "ERROR"
        if isinstance(message, dict):
            message = json.dumps(message, ensure_ascii=False)
        elif not isinstance(message, str):
            message = str(message)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{log_type}] {message}\n"
        with open(self.log_file_path, 'a') as file:
            file.write(log_entry)
        print(log_entry)

    def show_logs(self):
        '''
        Display the contents of the log file.
        '''
        if self.disabled or not os.path.exists(self.log_file_path):
            print("日志功能已禁用或文件不存在。")
            return
        with open(self.log_file_path, 'r') as file:
            logs = file.read()
        print(logs)
            
def extract_python_code_from_text(text):
    '''
    Extract Python code blocks from a text.
    :param text: The input text.
    :return: A Python code block.
    '''
    # 可能是python，也可能是Python，还可能是PYTHON
    
    match1 = re.search(r'```python(.*?)```', text, re.DOTALL)
    match2 = re.search(r'```Python(.*?)```', text, re.DOTALL)
    match3 = re.search(r'```PYTHON(.*?)```', text, re.DOTALL)
    if match1:
        code_block = match1.group(1)
    elif match2:
        code_block = match2.group(1)
    elif match3:
        code_block = match3.group(1)
    else:
        code_block = None
        print("未找到Python代码")
    return code_block

def extract_python_from_doubao(text):
    '''
    Extract Python code blocks from a text.
    :param text: The input text.
    :return: A Python code block.
    '''
    # 可能是python，也可能是Python，还可能是PYTHON
    
    match1 = re.search(r'```python：(.*?)```', text, re.DOTALL)
    match2 = re.search(r'```Python：(.*?)```', text, re.DOTALL)
    match3 = re.search(r'```PYTHON：(.*?)```', text, re.DOTALL)
    if match1:
        code_block = match1.group(1)
    elif match2:
        code_block = match2.group(1)
    elif match3:
        code_block = match3.group(1)
    else:
        code_block = None
        print("未找到Python代码")
    return code_block


def extract_list_from_text(text):
    '''
    Extract a list from a text.
    :param text: The input text.
    :return: A list extracted from the text.
    '''
    match = re.search(r'\[(.*?)\]', text)
    if match:
        list_str = match.group(0)
        list_items = eval(list_str)

        
        return list_items
    else:
        return None