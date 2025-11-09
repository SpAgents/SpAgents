import requests

from config.env import HUATUO_API_URL

# 定义一个函数，提取## Final Response后边的文本
def extract_final_response(text):
    start = text.find("## Final Response") + len("## Final Response")
    return text[start:].strip()

class HuatuoLLM:
    def __init__(self, api_url=None):
        self.api_url = api_url if api_url else HUATUO_API_URL
        self.history = []  # 存储历史对话

    def generate_response(self, input_text):
        """
        生成响应并更新历史对话。包括历史对话和当前用户输入。
        """
        # 将用户的输入添加到历史对话
        self.history.append({"role": "user", "content": input_text})

        # 将历史对话合并成字符串，作为模型的输入
        # 生成的输入应该包括用户的所有输入和模型的所有回答
        context = ""
        for message in self.history:
            context += f"{message['role']}: {message['content']}\n"

        # 创建请求体
        data = {"input_text": context}

        # 发送POST请求到API
        response = requests.post(self.api_url, json=data)

        if response.status_code == 200:
            result = response.json()
            response_text = result['response']
            response_text = extract_final_response(response_text)
            # 将模型的响应添加到历史对话
            self.history.append({"role": "assistant", "content": response_text})

            return response_text
        else:
            return f"请求失败，状态码: {response.status_code}"

    def reset_hist(self):
        """
        重置历史对话。
        """
        self.history = []

    def get_hist(self):
        """
        获取历史对话。
        """
        return self.history
