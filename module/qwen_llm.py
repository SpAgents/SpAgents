import os

import dashscope

from config.env import QWEN_API_KEY

default_system_prompt = os.getenv("QWEN_SYSTEM_PROMPT", "You are a helpful assistant")
default_api_key = QWEN_API_KEY or ""
default_model_name = os.getenv("QWEN_MODEL_NAME", "qwen-plus")

class QwenLLM(object):
    def __init__(self, system_prompt, api_key, model_name):
        # self.system_prompt = system_prompt if system_prompt else default_system_prompt
        # self.api_key = api_key if api_key else default_api_key
        # self.model_name = model_name if model_name else default_model_name
        self.system_prompt = system_prompt if system_prompt else default_system_prompt
        self.api_key = api_key if api_key else default_api_key
        self.model_name = model_name if model_name else default_model_name
        self.reset_hist()
        
    def generate_response(self, question):
        self.hist_messages.append({'role': 'user', 'content': question})
        response = dashscope.Generation.call(
            api_key=self.api_key,
            model=self.model_name,
            messages=self.hist_messages,
            result_format='message'
            )
        response_text = response.output.choices[0].message.content
        self.hist_messages.append({'role': 'assistant', 'content': response_text})
        return response_text
    
    def reset_hist(self):
        self.hist_messages = [
            {'role': 'system', 'content': self.system_prompt}
        ]
    
    def get_hist(self):
        return self.hist_messages
