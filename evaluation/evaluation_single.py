import sys
sys.path.append('..')
import os
import pandas as pd
import json
import time
import argparse
from agent.planner_agent import PlannerAgent

# 解析参数（可以设置默认值）
parser = argparse.ArgumentParser()
parser.add_argument("--experiment_name", type=str, default="ex_tool_2", help="experiment name")
args = parser.parse_args()
experiment_name = args.experiment_name

# 导入 config 配置
import importlib
module_path = f"config.config_{experiment_name}"
try:
    module = importlib.import_module(module_path)
    config = getattr(module, "config")
except (ModuleNotFoundError, AttributeError) as e:
    print(f"导入失败: {e}")
    exit(1)

# 设置保存路径
result_path = os.path.join("/Users/wenchienyueh/Desktop/patient_0624/results", experiment_name)
os.makedirs(os.path.join(result_path, "result"), exist_ok=True)

config["PlannerAgent"]["log_path"] = os.path.join(result_path, config["PlannerAgent"]["log_path"])
config["DoctorAgent"]["log_path"] = os.path.join(result_path, config["DoctorAgent"]["log_path"])
config["DataAgent"]["log_path"] = os.path.join(result_path, config["DataAgent"]["log_path"])
config["ToolAgent"]["log_path"] = os.path.join(result_path, config["ToolAgent"]["log_path"])

# 初始化Agent
AS_agents = PlannerAgent(config)

# 创建结果保存结构
abnormal_list = []
time_consumption = dict()
res_df = pd.DataFrame(columns=["patient_id", "res"])

# ✅ 只诊断一个指定的病人
patient_id = "PATIENT_ID"
query = f"对于病人{patient_id}，请使用EdemaSystem工具，结合其MRI（路径已知），给出axSpA的诊断。"
start_time = time.time()

max_retries = 5
success = False
for attempt in range(max_retries):
    try:
        res = AS_agents.generate_response(query)
        res_df.loc[len(res_df)] = [patient_id, res]
        success = True
        break
    except Exception as e:
        print(f"{patient_id} 第 {attempt + 1} 次推理失败: {e}")
        time.sleep(2)

if not success:
    abnormal_list.append(patient_id)
    print(f"{patient_id} 推理最终失败（尝试 {max_retries} 次）")

consume_time = time.time() - start_time
time_consumption[patient_id] = consume_time
AS_agents.clear_llm_cache()
print(f"病人 {patient_id} 推理完毕，耗时：{consume_time:.2f}s")

# 保存结果
res_df.to_csv(os.path.join(result_path, "result", "axSpA_res_single.csv"), index=False)
with open(os.path.join(result_path, "result", "time_consumption_single.json"), "w") as f:
    json.dump(time_consumption, f)
with open(os.path.join(result_path, "result", "abnormal_list_single.txt"), "w") as f:
    for item in abnormal_list:
        f.write(f"{item}\n")

print("病人推理完毕。结果已保存。")

