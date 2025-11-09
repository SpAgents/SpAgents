
import requests
import threading
import time
import json
import os
import numpy as np
import uuid
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import argparse

class QuickStressTest:
    
    def __init__(self, base_url="http://152.136.58.167"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        self.lock = threading.Lock()
        
        # 登录
        self.login()
    
    def login(self):
        try:
            login_data = {
                'username': 'admin',
                'password': 'axspa@152136'
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                timeout=30
            )
            
            if response.status_code == 200 and "登录成功" in response.text:
                print("登录成功")
                return True
            else:
                print(f"登录失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"登录异常: {str(e)}")
            return False
    
    def create_test_file(self):
        # 创建小的测试数据 (24, 128, 128) 以减少文件大小
        test_data = np.random.rand(24, 128, 128).astype(np.float32)
        file_id = str(uuid.uuid4())
        file_path = f"temp_{file_id}.npy"
        np.save(file_path, test_data)
        return file_path, file_id
    
    def test_upload(self):
        try:
            file_path, file_id = self.create_test_file()
            
            start_time = time.time()
            
            with open(file_path, 'rb') as f:
                files = {'file': (f"{file_id}.npy", f, 'application/octet-stream')}
                response = self.session.post(
                    f"{self.base_url}/upload",
                    files=files,
                    timeout=30
                )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # 清理临时文件
            os.remove(file_path)
            
            success = response.status_code == 200
            with self.lock:
                self.results.append({
                    'test': 'upload',
                    'success': success,
                    'response_time': response_time,
                    'status_code': response.status_code
                })
            
            if success:
                print(f"上传成功 ({response_time:.2f}s)")
                return response.json().get('file_id')
            else:
                print(f"上传失败 ({response_time:.2f}s)")
                return None
                
        except Exception as e:
            print(f"上传异常: {str(e)}")
            return None
    
    def test_skip_analysis(self):
        try:
            form_data = {
                'age': random.randint(20, 70),
                'sex': random.choice(['男', '女']),
                'reportTime': '2024-01-01',
                'reportFind': 'MRI检查显示...',
                'presentIllness': '患者主诉...',
                'pastIllness': '既往史...',
                'familyHistory': '家族史...',
                'physicalExam': '体格检查...',
                'b27': random.choice(['阳性', '阴性', '未检查']),
                'crp': round(random.uniform(0.1, 10.0), 2),
                'esr': random.randint(5, 50)
            }
            
            params = {
                'formData': json.dumps(form_data, ensure_ascii=False)
            }
            
            start_time = time.time()
            
            response = self.session.get(
                f"{self.base_url}/analyze/skip",
                params=params,
                timeout=30
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            success = response.status_code == 200
            with self.lock:
                self.results.append({
                    'test': 'skip_analysis',
                    'success': success,
                    'response_time': response_time,
                    'status_code': response.status_code
                })
            
            if success:
                print(f"跳过分析成功 ({response_time:.2f}s)")
            else:
                print(f"跳过分析失败 ({response_time:.2f}s)")
            
            return success
            
        except Exception as e:
            print(f"跳过分析异常: {str(e)}")
            return False
    
    def test_analyze(self, file_id):
        try:
            form_data = {
                'age': random.randint(20, 70),
                'sex': random.choice(['男', '女']),
                'reportTime': '2024-01-01',
                'reportFind': 'MRI检查显示...',
                'presentIllness': '患者主诉...',
                'pastIllness': '既往史...',
                'familyHistory': '家族史...',
                'physicalExam': '体格检查...',
                'b27': random.choice(['阳性', '阴性', '未检查']),
                'crp': round(random.uniform(0.1, 10.0), 2),
                'esr': random.randint(5, 50)
            }
            
            params = {
                'formData': json.dumps(form_data, ensure_ascii=False)
            }
            
            start_time = time.time()
            
            # 只等待5秒，不等待完整分析
            response = self.session.get(
                f"{self.base_url}/analyze/{file_id}",
                params=params,
                timeout=5
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            success = response.status_code == 200
            with self.lock:
                self.results.append({
                    'test': 'analyze',
                    'success': success,
                    'response_time': response_time,
                    'status_code': response.status_code
                })
            
            if success:
                print(f"分析请求成功 ({response_time:.2f}s)")
            else:
                print(f"分析请求失败 ({response_time:.2f}s)")
            
            return success
            
        except Exception as e:
            print(f"分析异常: {str(e)}")
            return False
    
    def user_workload(self, user_id):
        print(f"👤 用户 {user_id} 开始测试")
        
        for i in range(5):  # 每个用户执行5轮测试
            try:
                # 测试上传
                file_id = self.test_upload()
                
                # 测试跳过分析
                self.test_skip_analysis()
                
                # 如果有上传成功，测试分析
                if file_id:
                    self.test_analyze(file_id)
                
                # 短暂休息
                time.sleep(0.5)
                
            except Exception as e:
                print(f"用户 {user_id} 测试异常: {str(e)}")
        
        print(f"👤 用户 {user_id} 测试完成")
    
    def run_test(self, concurrent_users=5):
        print(f"开始快速压力测试")
        print(f"并发用户数: {concurrent_users}")
        print(f"目标URL: {self.base_url}")
        print("-" * 50)
        
        start_time = time.time()
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            # 提交用户工作负载
            futures = []
            for i in range(concurrent_users):
                future = executor.submit(self.user_workload, i + 1)
                futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                future.result()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 生成报告
        self.generate_report(total_time)
    
    def generate_report(self, total_time):
        print("\n" + "="*60)
        print("📊 快速压力测试报告")
        print("="*60)
        
        # 按测试类型分组
        test_groups = {}
        for result in self.results:
            test_name = result['test']
            if test_name not in test_groups:
                test_groups[test_name] = []
            test_groups[test_name].append(result)
        
        print(f"总测试时间: {total_time:.2f} 秒")
        print(f"总请求数: {len(self.results)}")
        print(f"平均每秒请求数: {len(self.results) / total_time:.2f}")
        
        print("\n各接口测试结果:")
        print("-" * 40)
        
        for test_name, results in test_groups.items():
            response_times = [r['response_time'] for r in results]
            success_count = sum(1 for r in results if r['success'])
            error_count = len(results) - success_count
            
            print(f"\n🔍 {test_name.upper()}:")
            print(f"  总请求数: {len(results)}")
            print(f"  成功数: {success_count}")
            print(f"  失败数: {error_count}")
            print(f"  成功率: {success_count / len(results) * 100:.1f}%")
            print(f"  平均响应时间: {sum(response_times) / len(response_times):.3f}秒")
            print(f"  最小响应时间: {min(response_times):.3f}秒")
            print(f"  最大响应时间: {max(response_times):.3f}秒")
        
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description='axSpA 系统快速压力测试')
    parser.add_argument('--users', type=int, default=5, help='并发用户数 (默认: 5)')
    parser.add_argument('--url', type=str, default='http://152.136.58.167', help='目标URL')
    
    args = parser.parse_args()
    
    # 创建测试器并运行
    tester = QuickStressTest(args.url)
    tester.run_test(args.users)

if __name__ == "__main__":
    main() 