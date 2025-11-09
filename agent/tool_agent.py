import sys
sys.path.append('..')
from module.qwen_llm import QwenLLM
from module.deepseek_llm import DeepseekLLM
from module.doubao_llm import DoubaoLLM
from module.edema_system import EdemaSystem
from utils.prompt import ToolAgentPrompt
from utils.utils import TxtLog, extract_python_code_from_text, extract_list_from_text, extract_python_from_doubao

# External Variables
log_path = "/data1/lzf/301agent/log/tool_agent.txt"

class ToolAgent(object):
    def __init__(self, config):
        model_type = config.get("model_type")
        if model_type == "qwen_llm":
            self.model_llm = QwenLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        elif model_type == "deepseek_llm":
            self.model_llm = DeepseekLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        elif model_type == "doubao_llm":
            self.model_llm = DoubaoLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        self.max_data_tries = config.get("max_model_tries", 3)
        self.model_name = model_type
        self.logger = TxtLog(config.get("log_path", log_path))
        self.tool_name_list = []
        self.tool_description = ""
        self.init_models(config)
    
    def clear_llm_cache(self):
        self.model_llm.reset_hist()
        self.logger.info("LLM cache of tool agent cleared.")
        for tool_name in self.tool_name_list:
            if tool_name == "EdemaSystem":
                self.edema_system.clear_data_cache()
    
    def init_models(self, config):
        self.logger.info("Start initializing models.")
        if "EdemaSystem" in config["models_name"]:
            # TODO:加入异常处理
            self.edema_system = EdemaSystem(config["models_config"]["EdemaSystem"])
            self.logger.info("EdemaSystem initialized.")
            self.tool_name_list.append("EdemaSystem")
            self.tool_description += "## 工具" + str(len(self.tool_name_list)) + "：\n" + ToolAgentPrompt["Tool_EdemaSystem_CHN"]
        self.logger.info("Models initialized.")

    
    def perform_task(self, task_info_text):
        self.logger.info("Start performing task.")
        for i in range(self.max_data_tries):
            self.logger.info(f"Try {i+1}")
            try:
                query = ToolAgentPrompt["PerformTask_CHN"].format(task_info_text=task_info_text, tool_description=self.tool_description)
                if i != 0:
                    query = ToolAgentPrompt["retry_perform_task_CHN"] + query

                response = self.model_llm.generate_response(query)
                    
                self.logger.info(response)
                if self.model_name == "qwen_llm":
                    code_text = extract_python_code_from_text(response)
                elif self.model_name == "doubao_llm":
                    code_text = extract_python_from_doubao(response)
                else:
                    code_text = extract_python_code_from_text(response)
                self.logger.info(f"Generated code: {code_text}")
                
                result = eval(code_text)
                self.logger.info(f"Task performed.")
            except Exception as e:
                self.logger.error(f"Error: {e}")
                continue
            return result
        

    def tool_run_sparcc_score(self, npy_img_path=None, patient_id=None, dicom_path=None):
        if npy_img_path is None and patient_id is not None:
            # 自动拼接 npy 路径
            npy_img_path = f"/Users/wenchienyueh/Desktop/doctor_data/converted_npy/{patient_id}.npy"

        if npy_img_path is not None:
            result = self.edema_system.run_sparcc_score(npy_img_path, patient_id)
            self.edema_system.clear_data_cache()
            result = self.convert_sparcc_df_to_text(result)
            self.logger.info(f"SPARCC score: {result}")
            return result
        elif dicom_path is not None:
            result = self.edema_system.run(dicom_path)
            self.edema_system.clear_data_cache()
            self.logger.info(f"Edema report: {result}")
            return result
        else:
            return "缺少图像路径，无法执行分析"
        
        
    def convert_sparcc_df_to_text(self, sparcc_df):
        df_text =  sparcc_df.to_string()
        df_text = "SPARCC评分表格如下：\n" + df_text
        # 计算数字列的总和:
        col = ["iru", "sru", "ird", "srd", "slu", "ilu", "sld", "ild", "rdeep", "rinten", "ldeep", "linten"]
        df_sum = sparcc_df[col].sum()
        df_sum = df_sum.sum()
        
        df_sum_text = "SPARCC评分总和如下：\n" + str(df_sum)
        return df_text + "\n" + df_sum_text
        
    
        
        
        
        
        