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
    # ✅ 禁用 DoctorAgent 的长期记忆功能
    #config["DoctorAgent"]["long_term_memory"] = None
except (ModuleNotFoundError, AttributeError) as e:
    print(f"导入失败: {e}")
    exit(1)

# 设置保存路径
result_path = os.path.join("/Users/wenchienyueh/Desktop/patient_0624/results", experiment_name)
os.makedirs(os.path.join(result_path, "result"), exist_ok=True)

config["PlannerAgent"]["log_path"] = os.path.join(result_path, config["PlannerAgent"]["log_path"])
config["DoctorAgent"]["log_path"] = os.path.join(result_path, config["DoctorAgent"]["log_path"])
config["DataAgent"]["log_path"] = os.path.join(result_path, config["DataAgent"]["log_path"])
# 如果不使用ToolAgent也可以注释掉
# config["ToolAgent"]["log_path"] = os.path.join(result_path, config["ToolAgent"]["log_path"])

# 设置数据路径（本地CSV）
data_path = "/Users/wenchienyueh/Desktop/patient_0624/patient_0624.csv"
try:
    agent_df = pd.read_csv(data_path)  # 如乱码可换成 encoding="gb18030"
except Exception as e:
    print(f"CSV读取失败: {e}")
    exit(1)

# 初始化Agent
AS_agents = PlannerAgent(config)

# 创建结果保存结构
abnormal_list = []
time_consumption = dict()
res_df = pd.DataFrame(columns=["patient_id", "res"])

# 遍历所有样本
for i, row in agent_df.iterrows():
    patient_id = str(row["patient_id"])
    query = f"对于病人{patient_id}，请使用EdemaSystem工具，结合其MRI（路径已知），给出axSpA的诊断。"
    start_time = time.time()

    max_retries = 5
    success = False
    for attempt in range(max_retries):
        try:
            res = AS_agents.generate_response(query)
            res_df.loc[len(res_df)] = [patient_id, res]
            success = True
            break  # 注意：这里是跳出“重试循环”，不是跳出外层的病人循环
        except Exception as e:
            print(f"{patient_id} 第 {attempt + 1} 次推理失败: {e}")
            time.sleep(2)  # 可选：防止频繁请求

    if not success:
        abnormal_list.append(patient_id)
        print(f"{patient_id} 推理最终失败（尝试 {max_retries} 次）")

    consume_time = time.time() - start_time
    time_consumption[patient_id] = consume_time
    AS_agents.clear_llm_cache()
    print(f"第 {i + 1} 个病人，耗时：{consume_time:.2f}s")
    time.sleep(1)


# 保存结果
res_df.to_csv(os.path.join(result_path, "result", "axSpA_res.csv"), index=False)
with open(os.path.join(result_path, "result", "time_consumption.json"), "w") as f:
    json.dump(time_consumption, f)
with open(os.path.join(result_path, "result", "abnormal_list.txt"), "w") as f:
    for item in abnormal_list:
        f.write(f"{item}\n")

print("所有病人推理完毕。结果已保存。")






