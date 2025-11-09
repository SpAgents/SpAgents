from config.env import (
    DEEPSEEK_API_KEY,
    LONG_TERM_DB_PATH,
    LONG_TERM_MODEL_DIR,
    data_path,
    model_path,
)


config = {
    "ExperimentName": "ex_tool_2", # 可选
    "DoctorAgent" : {
        "system_prompt": "",
        "model_type": "deepseek_llm",
        "api_key": DEEPSEEK_API_KEY,
        "model_name": "deepseek-reasoner",
        "log_path" : "log/diagnosis_agent.log",
        "max_diagnosis_tries": 3,
        # 暂时禁用长期记忆
        "long_term_memory": {
            "db_path": LONG_TERM_DB_PATH,
            "model_name": LONG_TERM_MODEL_DIR,
            "k": 3
        },
        "prompt_name": "diagnosis_axSpA_no_tool", # diagnosis_axSpA_tool, diagnosis_axSpA_tool, diagnosis_axSpA_hla, diagnosis_axSpA_mri
    },
    "DataAgent" : {
        "system_prompt": "",
        "model_type": "deepseek_llm",
        "api_key": DEEPSEEK_API_KEY,
        "model_name": "deepseek-chat",
        "log_path" : "log/data_agent.log",
        "max_data_tries": 3,
        "use_ai_model": True,
        "data_df_path": data_path("51_patients_real_with_mri.csv"),
    },
    "ToolAgent" : {
        "system_prompt": "",
        "model_type": "deepseek_llm",
        "api_key": DEEPSEEK_API_KEY,
        "model_name": "deepseek-chat",
        "log_path" : "log/model_agent.log",
        "max_model_tries": 3,
        "models_name": ["EdemaSystem"],
        "models_config":{
            "EdemaSystem":  {
                "threshold": 2500,
                "seg_type": "two_stage",
                "seg_1_model":{
                    "load_path": model_path("seg", "best_seg_model_seg_two_1_0_epoch_0.pth"),
                    "is_dp": False
                    },
                "seg_2_model":{
                    "load_path": model_path("seg", "best_seg_model_seg_two_2_0_epoch_0.pth"),
                    "is_dp": False
                    },
                "classify_model":{
                    "load_path": model_path("classify", "best_classify_model_resnet18_fold_0_epoch_0.pth"),
                    "is_dp": False
                    },
                "classify_depth_model":{
                    "load_path": model_path("classify_rl", "best_classify_rl_model_resnet18_deep_fold_0_epoch_0.pth"),
                    "is_dp": False
                    },
                "classify_intensity_model":{
                    "load_path": model_path("classify_rl", "best_classify_rl_model_resnet18_inten_fold_0_epoch_0.pth"),
                    "is_dp": False
                },
            },
        }
    },
    "PlannerAgent" : {
        "system_prompt": "",
        "model_type": "deepseek_llm",
        "api_key": DEEPSEEK_API_KEY,
        "model_name": "deepseek-chat",
        "log_path" : "log/planner_agent.log",
        "max_planner_tries": 3,
        "get_info_func": "get_all_info", #get_all_info, get_text, get_text_b27, get_text_crp_esr, get_text_b27_crp_esr, get_all_info
        "use_tool_agent": True, # True, False
    }
}
