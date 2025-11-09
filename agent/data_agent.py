import sys
import os
import pandas as pd
import numpy as np
sys.path.append('..')
from module.qwen_llm import QwenLLM
from module.deepseek_llm import DeepseekLLM
from module.doubao_llm import DoubaoLLM
from module.patient_data import PatientData
from utils.prompt import DataAgentPrompt
from utils.utils import TxtLog, extract_json_from_text

col_12 = ["iru", "sru", "ird", "srd", "slu", "ilu", "sld", "ild", "rdeep", "rinten", "ldeep", "linten"]
col_8 = ["iru", "sru", "ird", "srd", "slu", "ilu", "sld", "ild"]
col_4 = ["ru", "rd", "lu", "ld"]


class DataAgent(object):
    def __init__(self, config):
        '''
        Initialize the DataAgent.
        :param config: A dictionary containing the configuration.
        '''
        model_type = config.get("model_type")
        if model_type == "qwen_llm":
            self.data_llm = QwenLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        elif model_type == "deepseek_llm":
            self.data_llm = DeepseekLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        elif model_type == "doubao_llm":
            self.data_llm = DoubaoLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        self.language = config.get("language", "CHN")
        self.use_ai_model = config.get("use_ai_model", False)
        self.max_data_tries = config.get("max_data_tries", 3)
        
        self.logger = TxtLog(config.get("log_path"))
        self.logger.info("DataAgent initialized.")
        
        self.data_df = pd.read_csv(config.get("data_df_path"))
  
    
    def clear_llm_cache(self):
        '''
        Clear the LLM cache.
        '''
        self.data_llm.reset_hist()
        self.logger.info("LLM cache of data agent cleared.")
    
    def perform_task(self, task_info_text):
        self.logger.info("Start generating patient data.")
        query = DataAgentPrompt["get_data_CHN"].format(task_info_text=task_info_text)
        for i in range(self.max_data_tries):
            try:
                if i != 0:
                    query = DataAgentPrompt["retry_get_data_CHN"] + query
                response = self.data_llm.generate_response(query)
                self.logger.info(response)
                
                flag, json_text = extract_json_from_text(response)
                if flag == False:
                    self.logger.error("Json extraction failed.")
                    continue
                patient_data = self.execute_data_query(json_text)
                
                return True, patient_data 
            except Exception as e:
                self.logger.error(f"Exception occured, retrying... {e}")
        self.logger.error("Data generation failed after {} tries.".format(self.max_data_tries))
        return False, None
        
    def execute_data_query(self, func_dict):
        func_name = func_dict["func_name"]
        func_args = func_dict["func_args"]
        print(func_name, func_args)
        # 使用getattr调用函数并传递参数
        func = getattr(self, func_name)
        if isinstance(func_args, list):
            return func(*func_args)  # 如果func_args是列表，展开列表作为多个参数传入
        return func(func_args)  # 如果func_args是单一的参数，直接传递
        
    
    def __repr__(self):
        return (f"This is a DataAgent.")
    
    def get_patient_data_by_name(self, name):
        '''
        Get patient data by name.
        :param name: The name of the patient.
        :return: A PatientData object.
        '''
        sub_df = self.data_df[self.data_df["name"] == name]
        try:
            patient_id = sub_df["patient_id"].values[0]
        except:
            self.logger.error(f"Patient {name} not found.")
            return None
        return self.get_patient_data_by_id(patient_id)
    
    def get_patient_data_by_id(self, patient_id):
        '''
        Get patient data by patient_id.
        If patient_id is not found in self.data_df, try using it as a direct .npy path.
        :param patient_id: patient ID or direct .npy path.
        :return: A PatientData object or None.
        '''
        sub_df = self.data_df[self.data_df["patient_id"] == patient_id]

        if not sub_df.empty:
            try:
                all_info_dict = sub_df.to_dict(orient='records')[0]
                patient_data = PatientData(all_info_dict)

                if not self.use_ai_model:
                    self.update_patient_data_without_ai_model(patient_data, patient_id)

                return patient_data
            except Exception as e:
                self.logger.error(f"Error parsing data for patient {patient_id}: {e}")
                return None

        # 如果没在 CSV 里找到，尝试 patient_id 是不是一个有效 .npy 路径（新的上传方式）
        if os.path.isfile(patient_id) and patient_id.endswith(".npy"):
            self.logger.info(f"Treating '{patient_id}' as direct npy file path.")
            try:
                # 创建基本的PatientData对象
                patient_data = PatientData({
                    "patient_id": "uploaded_npy",
                    "t2_mri_path": patient_id
                })
                return patient_data
            except Exception as e:
                self.logger.error(f"Failed to create PatientData from path {patient_id}: {e}")
                return None

        self.logger.error(f"Patient '{patient_id}' not found in CSV, nor is it a valid npy path.")
        return None
        
    def get_sum_by_df(self, df, col_list=col_12):
        '''
        Get the sum of the dataframe.
        :param df: A dataframe.
        :p
        :return: The sum of the dataframe.
        '''
        sum_value = 0
        for col in col_list:
            sum_value += df[col].sum()
        return int(sum_value)
        