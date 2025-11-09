import sys
sys.path.append('..')
import os
import pandas as pd
import json
import time
from datetime import datetime, timedelta
from tqdm import tqdm
import importlib
import argparse
from agent.planner_agent import PlannerAgent


argparse = argparse.ArgumentParser()
argparse.add_argument("--experiment_name", type=str, help="experiment name")


experiment_name = argparse.parse_args().experiment_name

module_path = f"config.config_{experiment_name}"
try:
    module = importlib.import_module(module_path)
    config = getattr(module, "config")  # 获取模块中的 config 对象
    # print(config)  # 可以正常使用 config 了
except (ModuleNotFoundError, AttributeError) as e:
    print(f"导入失败: {e}")


result_path = os.path.join("/data1/lzf/301agent/code_0411/results", experiment_name)

if not os.path.exists(result_path):
    os.makedirs(result_path)

config["PlannerAgent"]["log_path"] = os.path.join(result_path, config["PlannerAgent"]["log_path"])
config["DoctorAgent"]["log_path"] = os.path.join(result_path, config["DoctorAgent"]["log_path"])
config["DataAgent"]["log_path"] = os.path.join(result_path, config["DataAgent"]["log_path"])
config["ToolAgent"]["log_path"] = os.path.join(result_path, config["ToolAgent"]["log_path"])

config["DoctorAgent"]["long_term_memory"]["db_path"] = os.path.join(result_path, config["DoctorAgent"]["long_term_memory"]["db_path"])

with open("/data1/lzf/301agent/code_0411/train_list.txt", "r") as f:
    train_list = f.readlines()
train_list = [x.strip() for x in train_list]
with open("/data1/lzf/301agent/code_0411/test_list.txt", "r") as f:
    test_list = f.readlines()
test_list = [x.strip() for x in test_list]
print("train_list", len(train_list))
print("test_list", len(test_list))

result_save_path = os.path.join(result_path, "result")
if not os.path.exists(result_save_path):
    os.makedirs(result_save_path)

res_df_save_path = os.path.join(result_save_path, "axSpA_res.csv")
abnormal_list_save_path = os.path.join(result_save_path, "abnormal_list.txt")
time_consumption_save_path = os.path.join(result_save_path, "time_consumption.json")


AS_agents = PlannerAgent(config)

abnormal_list = []
time_consumption = dict()
res_df = res_df = pd.DataFrame(columns=["patient_id", "split", "res"])

agent_df = pd.read_csv(config["DataAgent"]["data_df_path"])


index_num = 0
for agent_id in train_list:
    gt = agent_df[agent_df["patient_id"] == agent_id]["diagnosis_result"].values[0]
    diagnosis_text = "诊断为axSpA阳性" if gt == 1 else "诊断为axSpA阴性"
    start_time = time.time()
    # query = "对于病人{}，请给出axSpA的诊断".format(agent_id)
    # res = AS_agents.generate_response_and_learning(query, diagnosis_text)
    # res_df.loc[len(res_df)] = [agent_id, "train", res]
    try:
        query = "对于病人{}，请给出axSpA的诊断".format(agent_id)
        res = AS_agents.generate_response_and_learning(query, diagnosis_text)
        res_df.loc[len(res_df)] = [agent_id, "train", res]
    except:
        abnormal_list.append(agent_id)
    consume_time = time.time() - start_time
    time_consumption[agent_id] = consume_time
    AS_agents.clear_llm_cache()
    index_num += 1
    print("第{}个病人，训练集，耗时：{}".format(index_num, consume_time))
    time.sleep(1)


for agent_id in test_list:
    gt = agent_df[agent_df["patient_id"] == agent_id]["diagnosis_result"].values[0]
    diagnosis_text = "诊断为axSpA阳性" if gt == 1 else "诊断为axSpA阴性"
    start_time = time.time()
    try:
        query = "对于病人{}，请给出axSpA的诊断".format(agent_id)
        res = AS_agents.generate_response_and_learning(query, diagnosis_text)
        res_df.loc[len(res_df)] = [agent_id, "test", res]
    except:
        abnormal_list.append(agent_id)
    consume_time = time.time() - start_time
    time_consumption[agent_id] = consume_time
    AS_agents.clear_llm_cache()
    index_num += 1
    print("第{}个病人，测试集，耗时：{}".format(index_num, consume_time))
    time.sleep(1)


res_df.to_csv(res_df_save_path, index=False)
with open(time_consumption_save_path, "w") as f:
    json.dump(time_consumption, f)
with open(abnormal_list_save_path, "w") as f:
    for item in abnormal_list:
        f.write("%s\n" % item)
print("Finish")
    

