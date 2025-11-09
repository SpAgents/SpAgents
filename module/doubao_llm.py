import os

from openai import OpenAI

from config.env import DOUBAO_API_KEY

default_system_prompt = "You are a helpful assistant"
default_api_key = DOUBAO_API_KEY or ""
default_model_name = os.getenv("DOUBAO_MODEL_NAME", "doubao-1-5-pro-32k-250115")
default_base_url = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

class DoubaoLLM(object):
    def __init__(self, system_prompt, api_key, model_name):
        self.system_prompt = system_prompt if system_prompt else default_system_prompt
        self.api_key = api_key if api_key else default_api_key
        self.model_name = model_name if model_name else default_model_name
        self.base_url = default_base_url
        self.hist_messages = []
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.reset_hist()

    def generate_response(self, question):
        self.hist_messages.append({'role': 'user', 'content': question})
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.hist_messages
        )
        response_text = response.choices[0].message.content
        self.hist_messages.append({'role': 'assistant', 'content': response_text})
        return response_text
    
    def reset_hist(self):
        self.hist_messages = [
            {'role': 'system', 'content': self.system_prompt}
        ]
