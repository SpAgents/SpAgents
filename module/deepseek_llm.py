import os

from openai import OpenAI

from config.env import DEEPSEEK_API_KEY

default_system_prompt = "You are a helpful assistant"
default_api_key = DEEPSEEK_API_KEY or ""
default_model_name = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
default_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


class DeepseekLLM(object):
    def __init__(self, system_prompt, api_key, model_name):
        self.system_prompt = system_prompt if system_prompt else default_system_prompt
        self.api_key = api_key if api_key else default_api_key
        self.model_name = model_name if model_name else default_model_name
        self.base_url = default_base_url
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.messages = [{'role': 'system', 'content': self.system_prompt}]
        
        
    def generate_response(self, question):
        self.messages.append({'role': 'user', 'content': question})
        response = self.client.chat.completions.create(
            model = self.model_name,
            messages = self.messages
        )
        response_text = response.choices[0].message.content
        self.messages.append({'role': 'assistant', 'content': response_text})
        
        return response_text
    def reset_hist(self):
        self.messages = [{'role': 'system', 'content': self.system_prompt}]
    
    def get_hist(self):
        return self.messages