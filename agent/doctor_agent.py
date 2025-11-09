import sys
sys.path.append('..')
from module.qwen_llm import QwenLLM
from module.deepseek_llm import DeepseekLLM
from module.doubao_llm import DoubaoLLM
from module.huatuo_llm import HuatuoLLM
from utils.utils import TxtLog, dict_to_text, extract_json_from_text
from utils.prompt import DiagnosisAgentPrompt
from module.long_term_memory import LongTermMemory

# External Variables
log_path = "/data1/lzf/301agent/log/diagnosis_agent.txt"

class DoctorAgent(object):
    def __init__(self, config):
        model_type = config.get("model_type")
        if model_type == "qwen_llm":
            self.diagnosis_llm = QwenLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        elif model_type == "deepseek_llm":
            self.diagnosis_llm = DeepseekLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        elif model_type == "doubao_llm":
            self.diagnosis_llm = DoubaoLLM(
                system_prompt=config.get("system_prompt"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name")
                )
        elif model_type == "huatuo_llm":
            self.diagnosis_llm = HuatuoLLM(
                api_url=config.get("api_url")
                )
        self.max_diagnosis_tries = config.get("max_diagnosis_tries", 3)
        self.logger = TxtLog(config.get("log_path", log_path))
        self.logger.info("DoctorAgent initialized with model: {}".format(config.get("model_name")))
        #删除长期记忆
        # self.long_term_memory = LongTermMemory(
        #     db_path=config.get("long_term_memory").get("db_path"),
        #     model_name=config.get("long_term_memory").get("model_name")
        #     )
        # self.k = config.get("long_term_memory").get("k")
        long_term_memory_config = config.get("long_term_memory")
        if long_term_memory_config:
            self.long_term_memory = LongTermMemory(
                db_path=long_term_memory_config.get("db_path"),
                model_name=long_term_memory_config.get("model_name")
            )
        else:
            self.long_term_memory = None

        self.k = long_term_memory_config.get("k") if long_term_memory_config else 0
        
        self.prompt_name = config.get("prompt_name")
        
    
    def clear_llm_cache(self):
        self.diagnosis_llm.reset_hist()
        self.logger.info("LLM cache of diagnosis agent cleared.")
    
    def diagnosis_axSpA(self, patient_text):
        self.logger.info("Start diagnosing axSpA")
        # patient_text = dict_to_text(patient_text)
        for i in range(self.max_diagnosis_tries):
            #删除长期记忆
            # case_ref_text = self.long_term_memory.get_ref_case(patient_text, k=self.k)
            if self.long_term_memory:
                case_ref_text = self.long_term_memory.get_ref_case(patient_text, k=self.k)
            else:
                case_ref_text = "无参考病例信息。请仅根据提供的患者信息进行判断。"
            query = DiagnosisAgentPrompt[self.prompt_name].format(patient_info_text=patient_text, case_ref_text=case_ref_text)
            if i != 0:
                query = DiagnosisAgentPrompt["retry_diagnosis_axSpA_CHN"] + query
            self.logger.info("Diagnosis query: {}".format(query))
            response = self.diagnosis_llm.generate_response(query)
            self.logger.info("Diagnosis response: {}".format(response))
            
            success, json_data = extract_json_from_text(response)
            if success:
                self.logger.info("Diagnosis succeeded after {} trying.".format(i))
                return True, json_data, response
            else:
                self.logger.error("Diagnosis failed, retrying...")
        self.logger.error("Diagnosis failed after {} tries".format(self.max_diagnosis_tries))
        return False, _, response
    
    def learn_from_feedback(self, feedback):
        if self.long_term_memory:
            self.long_term_memory.add_entry(feedback["medical_record"], feedback["diagnosis"])
            self.logger.info("Learned from feedback: {}".format(feedback))
            return True
        else:
            self.logger.error("长期记忆未启用，忽略反馈学习。")
            return False
    
    

 