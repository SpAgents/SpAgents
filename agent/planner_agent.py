import sys
import logging
import json

sys.path.append('..')
from module.qwen_llm import QwenLLM
from module.deepseek_llm import DeepseekLLM
from module.doubao_llm import DoubaoLLM
from agent.data_agent import DataAgent
from agent.tool_agent import ToolAgent
from agent.doctor_agent import DoctorAgent
from utils.prompt import PlannerAgentPrompt
from utils.utils import TxtLog, extract_list_from_text, extract_json_from_text, dict_to_text
# External Variables
log_path = "/data1/lzf/301agent/log/planner_agent.log"

class PlannerAgent:
    def __init__(self, config):
        
        config_planner = config.get("PlannerAgent")
        model_type = config_planner.get("model_type")
        if model_type == "qwen_llm":
            self.planner_llm = QwenLLM(
                system_prompt=config_planner.get("system_prompt"),
                api_key=config_planner.get("api_key"),
                model_name=config_planner.get("model_name")
            )
        elif model_type == "deepseek_llm":
            self.planner_llm = DeepseekLLM(
                system_prompt=config_planner.get("system_prompt"),
                api_key=config_planner.get("api_key"),
                model_name=config_planner.get("model_name")
            )
        elif model_type == "doubao_llm":
            self.planner_llm = DoubaoLLM(
                system_prompt=config_planner.get("system_prompt"),
                api_key=config_planner.get("api_key"),
                model_name=config_planner.get("model_name")
            )
        self.max_planner_tries = config_planner.get("max_planner_tries", 3)
        self.logger = TxtLog(config_planner.get("log_path", log_path))
        
        self.init_agent(config)
        
        self.get_info_func = config_planner.get("get_info_func", "get_all_info")
        self.use_tool_agent = config_planner.get("use_tool_agent", True)
        
    
    def init_agent(self, config):
        self.data_agent = DataAgent(config["DataAgent"])
        self.logger.info("DataAgent initialized.")
        self.tool_agent = ToolAgent(config["ToolAgent"])
        self.logger.info("ToolAgent initialized.")
        self.doctor_agent = DoctorAgent(config["DoctorAgent"])
        self.logger.info("DoctorAgent initialized.")
    
    def clear_llm_cache(self):
        self.planner_llm.reset_hist()
        self.logger.info("LLM cache of planner agent cleared.")
        self.data_agent.clear_llm_cache()
        self.tool_agent.clear_llm_cache()
        self.doctor_agent.clear_llm_cache()
    
    def generate_response_and_learning(self, ori_query, label):
        self.logger.info("Start generating response.")
        for i in range(self.max_planner_tries):
            self.logger.info(f"Try {i+1}")
            
            query = PlannerAgentPrompt["Planner_Task_CHN"].format(query_text=ori_query)
            if i != 0:
                query = query + PlannerAgentPrompt["retry_perform_task_CHN"]
                
            response = self.planner_llm.generate_response(query)
            self.logger.info(response)
            agent_list = extract_list_from_text(response)
            
            self.logger.info(f"Agent list: {agent_list}")
            
            if (len(agent_list) == 0) or (agent_list is None):
                response_prompt = PlannerAgentPrompt["PlannerResponse_CHN"].format(query_text=ori_query)
                response = self.planner_llm.generate_response(response_prompt)
                return response
                
            
            if len(agent_list) == 1:
                agent_name = agent_list[0]
                if agent_name == "DataAgent":
                    task_info_prompt = PlannerAgentPrompt["CallDataAgent"]
                    task_info_planner = task_info_prompt.format(query_text=ori_query)
                    # self.logger.info(task_info_planner)
                    task_info_response = self.planner_llm.generate_response(task_info_planner)
                    self.logger.info(task_info_response)
                    json_flag, task_info_json = extract_json_from_text(task_info_response)
                    if json_flag == False:
                        self.logger.error("Json extraction failed.")
                        continue
                        
                    flag, patient_data = self.data_agent.perform_task(task_info_json["task_info"])
                    if flag == False:
                        self.logger.error("Data generation failed.")
                        continue
                    return_text = self.analysis_data_agent_res(patient_data, task_info_json)
                    return return_text
                
                elif agent_name == "ToolAgent":
                    #TODO:
                    return "暂未设计只调用ToolAgent的情况"
                elif agent_name == "DoctorAgent":
                    flag, json_result, response = self.doctor_agent.diagnosis_axSpA(ori_query)
                    if flag == False:
                        self.logger.error("Diagnosis failed.")
                        continue
                    return_text = self.analysis_doctor_agent_res(json_result)
                    return return_text
                else:
                    self.logger.error("Invalid agent name.")
                    continue
        
            if len(agent_list) == 2:
                agent_name1 = agent_list[0]
                agent_name2 = agent_list[1]
                if agent_name1 == "DataAgent" and agent_name2 == "ToolAgent":
                    flag, patient_data = self.data_agent.perform_task(ori_query)
                    if flag == False:
                        self.logger.error("Data generation failed.")
                        continue
                    tool_task_prompt = PlannerAgentPrompt["CallToolAgent"]
                    tool_task_planner = tool_task_prompt.format(query_text=ori_query)
                    tool_task_info_response = self.planner_llm.generate_response(tool_task_planner)
                    self.logger.info(tool_task_info_response)
                    json_flag, tool_task_json = extract_json_from_text(tool_task_info_response)
                    if json_flag == False:
                        self.logger.error("Json extraction failed.")
                        continue
                    tool_paras = {k: patient_data.get_attribute(k) for k in tool_task_json["tool_paras"]} 
                    tool_task_info = tool_task_json["task_info"] + "\n 病人信息如下：" + json.dumps(tool_paras, ensure_ascii=False)
                    tool_response = self.tool_agent.perform_task(tool_task_info)
                    
                    return tool_response
                
                elif agent_name1 == "DataAgent" and agent_name2 == "DoctorAgent":
                    flag, patient_data = self.data_agent.perform_task(ori_query)
                    if flag == False:
                        self.logger.error("Data generation failed.")
                        continue
                    flag, json_result, response = self.doctor_agent.diagnosis_axSpA(dict_to_text(patient_data.get_examination_info()))
                    if flag == False:
                        self.logger.error("Diagnosis failed.")
                        continue
                    return_text = self.analysis_doctor_agent_res(json_result)
                    return return_text
                    
            if len(agent_list) == 3:
                flag, patient_data = self.data_agent.perform_task(ori_query)
                if flag == False:
                    self.logger.error("Data generation failed.")
                    continue
                
                # 决定是否使用ToolAgent
                if self.use_tool_agent == True:
                    t2_mri_path = patient_data.get_attribute("t2_mri_path")
                    tool_task_info = "对病人"+patient_data.get_attribute("patient_id")+"进行水肿判断，MRI影像路径为" + t2_mri_path
                    tool_response = self.tool_agent.perform_task(tool_task_info)
                    self.logger.info("tool_response:" + tool_response)
                elif self.use_tool_agent == False:
                    tool_response = ""
                
                # 决定使用哪些信息
                method = getattr(patient_data, self.get_info_func)
                doctor_task_info = tool_response + "\n" + dict_to_text(method())
                
                self.logger.info("doctor_task_info:"+doctor_task_info)
                
                flag, json_result, response = self.doctor_agent.diagnosis_axSpA(doctor_task_info)
                if flag == False:
                    self.logger.error("Diagnosis failed.")
                    continue
                return_text = self.analysis_doctor_agent_res(json_result)
                # 更新长期记忆
                self.doctor_agent.learn_from_feedback({"medical_record": doctor_task_info, "diagnosis": label})
                return return_text

    def generate_response(self, ori_query):
        self.logger.info("Start generating response.")
        
        # 检查是否为Web环境（包含文件路径的查询）
        is_web_environment = ".npy" in ori_query or "uploads/" in ori_query or "文件路径" in ori_query
        
        for i in range(self.max_planner_tries):
            self.logger.info(f"Try {i+1}")
            
            # 根据运行环境选择不同的处理策略
            if is_web_environment:
                # Web环境：直接进行完整的三智能体流程
                self.logger.info("检测到Web环境，直接执行完整诊断流程")
                return self._execute_web_diagnosis(ori_query)
            else:
                # 本地环境：使用原有的LLM规划逻辑
                query = PlannerAgentPrompt["Planner_Task_CHN"].format(query_text=ori_query)
                if i != 0:
                    query = query + PlannerAgentPrompt["retry_perform_task_CHN"]
                    
                response = self.planner_llm.generate_response(query)
                self.logger.info(response)
                agent_list = extract_list_from_text(response)
                
                self.logger.info(f"Agent list: {agent_list}")
                
                if (len(agent_list) == 0) or (agent_list is None):
                    response_prompt = PlannerAgentPrompt["PlannerResponse_CHN"].format(query_text=ori_query)
                    response = self.planner_llm.generate_response(response_prompt)
                    return response
                
            
            if len(agent_list) == 1:
                agent_name = agent_list[0]
                if agent_name == "DataAgent":
                    task_info_prompt = PlannerAgentPrompt["CallDataAgent"]
                    task_info_planner = task_info_prompt.format(query_text=ori_query)
                    # self.logger.info(task_info_planner)
                    task_info_response = self.planner_llm.generate_response(task_info_planner)
                    self.logger.info(task_info_response)
                    json_flag, task_info_json = extract_json_from_text(task_info_response)
                    if json_flag == False:
                        self.logger.error("Json extraction failed.")
                        continue
                        
                    flag, patient_data = self.data_agent.perform_task(task_info_json["task_info"])
                    if flag == False:
                        self.logger.error("Data generation failed.")
                        continue
                    return_text = self.analysis_data_agent_res(patient_data, task_info_json)
                    return return_text
                
                elif agent_name == "ToolAgent":
                    #TODO:
                    return "暂未设计只调用ToolAgent的情况"
                elif agent_name == "DoctorAgent":
                    flag, json_result, response = self.doctor_agent.diagnosis_axSpA(ori_query)
                    if flag == False:
                        self.logger.error("Diagnosis failed.")
                        continue
                    return_text = self.analysis_doctor_agent_res(json_result)
                    return return_text
                else:
                    self.logger.error("Invalid agent name.")
                    continue
        
            if len(agent_list) == 2:
                agent_name1 = agent_list[0]
                agent_name2 = agent_list[1]
                if agent_name1 == "DataAgent" and agent_name2 == "ToolAgent":
                    flag, patient_data = self.data_agent.perform_task(ori_query)
                    if flag == False:
                        self.logger.error("Data generation failed.")
                        continue
                    tool_task_prompt = PlannerAgentPrompt["CallToolAgent"]
                    tool_task_planner = tool_task_prompt.format(query_text=ori_query)
                    tool_task_info_response = self.planner_llm.generate_response(tool_task_planner)
                    self.logger.info(tool_task_info_response)
                    json_flag, tool_task_json = extract_json_from_text(tool_task_info_response)
                    if json_flag == False:
                        self.logger.error("Json extraction failed.")
                        continue
                    tool_paras = {k: patient_data.get_attribute(k) for k in tool_task_json["tool_paras"]} 
                    tool_task_info = tool_task_json["task_info"] + "\n 病人信息如下：" + json.dumps(tool_paras, ensure_ascii=False)
                    tool_response = self.tool_agent.perform_task(tool_task_info)
                    
                    return tool_response
                
                elif agent_name1 == "DataAgent" and agent_name2 == "DoctorAgent":
                    flag, patient_data = self.data_agent.perform_task(ori_query)
                    if flag == False:
                        self.logger.error("Data generation failed.")
                        continue
                    flag, json_result, response = self.doctor_agent.diagnosis_axSpA(dict_to_text(patient_data.get_examination_info()))
                    if flag == False:
                        self.logger.error("Diagnosis failed.")
                        continue
                    return_text = self.analysis_doctor_agent_res(json_result)
                    return return_text
                    
            if len(agent_list) == 3:
                flag, patient_data = self.data_agent.perform_task(ori_query)
                if flag == False:
                    self.logger.error("Data generation failed.")
                    continue
                
                # 决定是否使用ToolAgent
                if self.use_tool_agent == True:
                    t2_mri_path = patient_data.get_attribute("t2_mri_path")
                    tool_task_info = "对病人"+patient_data.get_attribute("patient_id")+"进行水肿判断，MRI影像路径为" + t2_mri_path
                    tool_response = self.tool_agent.perform_task(tool_task_info)
                    self.logger.info("tool_response:" + tool_response)
                elif self.use_tool_agent == False:
                    tool_response = ""
                
                # 决定使用哪些信息
                method = getattr(patient_data, self.get_info_func)
                doctor_task_info = tool_response + "\n" + dict_to_text(method())
                
                self.logger.info("doctor_task_info:"+doctor_task_info)
                
                flag, json_result, response = self.doctor_agent.diagnosis_axSpA(doctor_task_info)
                if flag == False:
                    self.logger.error("Diagnosis failed.")
                    continue
                return_text = self.analysis_doctor_agent_res(json_result)
                # 更新长期记忆
                # self.doctor_agent.learn_from_feedback({"medical_record": doctor_task_info, "diagnosis": label})
                return return_text
    
    def _execute_web_diagnosis(self, ori_query):
        """
        Web环境下的诊断流程：直接执行DataAgent -> ToolAgent -> DoctorAgent
        """
        self.logger.info("开始Web环境诊断流程")
        
        try:
            # 1. 调用DataAgent获取病人数据
            self.logger.info("调用DataAgent...")
            
            # 从查询中提取文件路径和病历信息
            import re
            file_path_match = re.search(r'文件路径：(.+?)(?:\n|$)', ori_query)
            if file_path_match:
                file_path = file_path_match.group(1).strip()
                self.logger.info(f"提取到文件路径: {file_path}")
                
                # 提取病历信息
                medical_info = {}
                medical_patterns = {
                    'age': r'年龄：(.+?)(?:\n|$)',
                    'sex': r'性别：(.+?)(?:\n|$)',
                    'report_time': r'影像报告时间：(.+?)(?:\n|$)',
                    'report_find': r'影像报告所见：(.+?)(?:\n|$)',
                    'history_present_illness': r'现病史：(.+?)(?:\n|$)',
                    'history_past_illness': r'既往史：(.+?)(?:\n|$)',
                    'family_medical_history': r'家族史：(.+?)(?:\n|$)',
                    'physical_examination': r'体格检查：(.+?)(?:\n|$)',
                    'B27': r'HLA-B27检查结果：(.+?)(?:\n|$)',
                    'CRP': r'C反应蛋白\(CRP\)：(.+?)(?:\n|$)',
                    'ESR': r'红细胞沉降率\(ESR\)：(.+?)(?:\n|$)'
                }
                
                for key, pattern in medical_patterns.items():
                    match = re.search(pattern, ori_query)
                    if match:
                        value = match.group(1).strip()
                        if value != '未提供':
                            medical_info[key] = value
                
                self.logger.info(f"提取到病历信息: {medical_info}")
                
                # 直接调用DataAgent的get_patient_data_by_id方法
                patient_data = self.data_agent.get_patient_data_by_id(file_path)
                if patient_data is None:
                    self.logger.error("DataAgent执行失败")
                    return "数据获取失败，请检查文件路径是否正确"
                
                # 更新PatientData对象，添加病历信息
                if medical_info:
                    self.logger.info("更新PatientData对象，添加病历信息")
                    for key, value in medical_info.items():
                        try:
                            # 处理数值类型转换
                            if key in ['age', 'B27', 'CRP', 'ESR']:
                                try:
                                    if key == 'B27':
                                        value = int(value)
                                    else:
                                        value = float(value)
                                except:
                                    self.logger.error(f"无法转换数值 {key}: {value}")
                            setattr(patient_data, key, value)
                            self.logger.info(f"成功设置属性 {key}: {value}")
                        except Exception as e:
                            self.logger.error(f"无法设置属性 {key}: {e}")
            else:
                self.logger.error("无法从查询中提取文件路径")
                return "查询格式错误，无法提取文件路径"
            
            # 2. 调用ToolAgent进行影像分析
            self.logger.info("调用ToolAgent...")
            if self.use_tool_agent:
                t2_mri_path = patient_data.get_attribute("t2_mri_path")
                if t2_mri_path:
                    tool_task_info = f"对病人{patient_data.get_attribute('patient_id')}进行水肿判断，MRI影像路径为{t2_mri_path}"
                    tool_response = self.tool_agent.perform_task(tool_task_info)
                    self.logger.info(f"ToolAgent响应: {tool_response}")
                else:
                    tool_response = "未找到MRI影像路径"
                    self.logger.error("未找到MRI影像路径")
            else:
                tool_response = ""
            
            # 3. 调用DoctorAgent进行诊断
            self.logger.info("调用DoctorAgent...")
            method = getattr(patient_data, self.get_info_func)
            doctor_task_info = tool_response + "\n" + dict_to_text(method())
            
            self.logger.info(f"DoctorAgent任务信息: {doctor_task_info}")
            
            flag, json_result, response = self.doctor_agent.diagnosis_axSpA(doctor_task_info)
            if not flag:
                self.logger.error("DoctorAgent执行失败")
                return "诊断失败，请检查数据完整性"
            
            # 4. 返回诊断结果
            return_text = self.analysis_doctor_agent_res(json_result)
            self.logger.info("Web环境诊断流程完成")
            return return_text
            
        except Exception as e:
            self.logger.error(f"Web环境诊断流程异常: {e}")
            return f"诊断过程中出现错误: {str(e)}"
        

    def analysis_data_agent_res(self, patient_data, task_info_json):
        if len(task_info_json["target_data_name"]) == 0:
            return_dict = patient_data.get_examination_info()
            # 把字典直接转化为字符串格式
            return_text = json.dumps(return_dict, ensure_ascii=False)
        else:
            return_dict = {k: patient_data.get_attribute(k) for k in task_info_json["target_data_name"]}
            return_text = json.dumps(return_dict, ensure_ascii=False)
        return return_text
        
    def analysis_doctor_agent_res(self, json_result):
        text = "诊断结果："
        if json_result["diagnosis_result"] == 0:
            text += "未诊断为axSpA\n"
        elif json_result["diagnosis_result"] == 1:
            text += "可以诊断为axSpA\n"
        elif json_result["diagnosis_result"] == -1:
            text += "信息不足，无法进行诊断\n"
        text += "诊断理由：" + json_result["reason"] + "\n"
        text += "治疗建议：" if json_result["diagnosis_result"] == 1 else "检查建议："
        text += json_result["suggestion"] + "\n"
        return text