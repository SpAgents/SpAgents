#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
axSpA 系统多线程压力测试脚本
测试各个API接口的性能和并发处理能力
"""

import requests
import threading
import time
import json
import os
import numpy as np
import uuid
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import argparse
import logging
from typing import Dict, List, Tuple, Optional
import queue
import statistics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stress_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StressTestConfig:
    """压力测试配置类"""
    def __init__(self):
        self.base_url = "http://152.136.58.167:5500"
        self.admin_username = "admin"
        self.admin_password = "axspa@152136"
        self.session = requests.Session()
        self.test_data_dir = "test_data"
        self.results = []
        self.lock = threading.Lock()
        
        # 测试参数
        self.concurrent_users = 10
        self.test_duration = 60  # 秒
        self.think_time = 1  # 秒
        self.upload_files = True
        self.analyze_files = True
        
        # 创建测试数据目录
        os.makedirs(self.test_data_dir, exist_ok=True)

class TestResult:
    """测试结果类"""
    def __init__(self, test_name: str, start_time: float, end_time: float, 
                 status_code: int, response_time: float, success: bool, 
                 error_msg: str = ""):
        self.test_name = test_name
        self.start_time = start_time
        self.end_time = end_time
        self.status_code = status_code
        self.response_time = response_time
        self.success = success
        self.error_msg = error_msg
        self.thread_id = threading.current_thread().ident

class StressTester:
    """压力测试器"""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.session = config.session
        self.base_url = config.base_url
        self.results_queue = queue.Queue()
        self.stop_event = threading.Event()
        
    def login(self) -> bool:
        """管理员登录"""
        try:
            login_data = {
                'username': self.config.admin_username,
                'password': self.config.admin_password
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                timeout=30
            )
            end_time = time.time()
            
            success = response.status_code == 200 and "登录成功" in response.text
            result = TestResult(
                "login", start_time, end_time, response.status_code,
                end_time - start_time, success
            )
            self.results_queue.put(result)
            
            if success:
                logger.info("✅ 登录成功")
                return True
            else:
                logger.error(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 登录异常: {str(e)}")
            return False
    
    def create_test_npy_file(self, file_id: str) -> str:
        """创建测试用的NPY文件"""
        file_path = os.path.join(self.config.test_data_dir, f"{file_id}.npy")
        
        # 创建模拟的MRI数据 (24, 512, 512)
        # 使用随机数据模拟真实的MRI图像
        mri_data = np.random.rand(24, 512, 512).astype(np.float32)
        
        # 添加一些结构化的数据模式，使其更像真实的MRI
        for z in range(24):
            # 添加一些圆形区域
            center_x, center_y = 256, 256
            radius = 100 + z * 2
            y, x = np.ogrid[:512, :512]
            mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
            mri_data[z][mask] += 0.3
            
            # 添加一些噪声
            noise = np.random.normal(0, 0.1, (512, 512))
            mri_data[z] += noise
        
        # 确保数据在合理范围内
        mri_data = np.clip(mri_data, 0, 1)
        
        np.save(file_path, mri_data)
        return file_path
    
    def test_upload(self) -> Optional[str]:
        """测试文件上传接口"""
        try:
            file_id = str(uuid.uuid4())
            file_path = self.create_test_npy_file(file_id)
            
            start_time = time.time()
            
            with open(file_path, 'rb') as f:
                files = {'file': (f"{file_id}.npy", f, 'application/octet-stream')}
                response = self.session.post(
                    f"{self.base_url}/upload",
                    files=files,
                    timeout=60
                )
            
            end_time = time.time()
            
            success = response.status_code == 200
            result = TestResult(
                "upload", start_time, end_time, response.status_code,
                end_time - start_time, success
            )
            self.results_queue.put(result)
            
            if success:
                response_data = response.json()
                uploaded_file_id = response_data.get('file_id')
                logger.info(f"✅ 文件上传成功: {uploaded_file_id}")
                return uploaded_file_id
            else:
                logger.error(f"❌ 文件上传失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 文件上传异常: {str(e)}")
            return None
    
    def test_analyze(self, file_id: str) -> bool:
        """测试分析接口"""
        try:
            # 模拟表单数据
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
            
            # 使用stream=True来处理SSE响应
            response = self.session.get(
                f"{self.base_url}/analyze/{file_id}",
                params=params,
                stream=True,
                timeout=300  # 5分钟超时
            )
            
            end_time = time.time()
            
            success = response.status_code == 200
            result = TestResult(
                "analyze", start_time, end_time, response.status_code,
                end_time - start_time, success
            )
            self.results_queue.put(result)
            
            if success:
                # 读取流式响应
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data = line_str[6:]  # 移除 'data: ' 前缀
                            if '✅ 推理完成' in data:
                                logger.info(f"✅ 分析完成: {file_id}")
                                break
                            elif 'error' in data.lower():
                                logger.error(f"❌ 分析错误: {data}")
                                break
            else:
                logger.error(f"❌ 分析请求失败: {response.status_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 分析异常: {str(e)}")
            return False
    
    def test_batch_upload(self) -> List[str]:
        """测试批量上传接口"""
        try:
            file_ids = []
            files = []
            
            # 创建多个测试文件
            for i in range(3):
                file_id = str(uuid.uuid4())
                file_path = self.create_test_npy_file(file_id)
                file_ids.append(file_id)
                files.append(('files', (f"{file_id}.npy", open(file_path, 'rb'), 'application/octet-stream')))
            
            start_time = time.time()
            
            response = self.session.post(
                f"{self.base_url}/upload_batch",
                files=files,
                timeout=120
            )
            
            end_time = time.time()
            
            success = response.status_code == 200
            result = TestResult(
                "batch_upload", start_time, end_time, response.status_code,
                end_time - start_time, success
            )
            self.results_queue.put(result)
            
            # 关闭文件
            for _, (_, file_obj, _) in files:
                file_obj.close()
            
            if success:
                logger.info(f"✅ 批量上传成功: {len(file_ids)} 个文件")
                return file_ids
            else:
                logger.error(f"❌ 批量上传失败: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ 批量上传异常: {str(e)}")
            return []
    
    def test_skip_analysis(self) -> bool:
        """测试跳过分析接口"""
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
                timeout=60
            )
            
            end_time = time.time()
            
            success = response.status_code == 200
            result = TestResult(
                "skip_analysis", start_time, end_time, response.status_code,
                end_time - start_time, success
            )
            self.results_queue.put(result)
            
            if success:
                logger.info("✅ 跳过分析成功")
            else:
                logger.error(f"❌ 跳过分析失败: {response.status_code} - {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 跳过分析异常: {str(e)}")
            return False
    
    def user_workload(self, user_id: int):
        """单个用户的完整工作负载"""
        logger.info(f"👤 用户 {user_id} 开始工作负载")
        
        while not self.stop_event.is_set():
            try:
                # 1. 登录
                if not self.login():
                    logger.error(f"用户 {user_id} 登录失败，跳过此轮测试")
                    time.sleep(self.config.think_time)
                    continue
                
                # 2. 测试上传
                if self.config.upload_files:
                    file_id = self.test_upload()
                    if file_id:
                        # 3. 测试分析
                        if self.config.analyze_files:
                            self.test_analyze(file_id)
                
                # 4. 测试批量上传
                if self.config.upload_files:
                    file_ids = self.test_batch_upload()
                    if file_ids:
                        # 5. 测试批量分析
                        if self.config.analyze_files:
                            for fid in file_ids[:2]:  # 只分析前2个文件
                                self.test_analyze(fid)
                
                # 6. 测试跳过分析
                self.test_skip_analysis()
                
                # 思考时间
                time.sleep(self.config.think_time)
                
            except Exception as e:
                logger.error(f"用户 {user_id} 工作负载异常: {str(e)}")
                time.sleep(self.config.think_time)
    
    def run_stress_test(self):
        """运行压力测试"""
        logger.info("🚀 开始压力测试")
        logger.info(f"📊 测试配置:")
        logger.info(f"   - 并发用户数: {self.config.concurrent_users}")
        logger.info(f"   - 测试时长: {self.config.test_duration} 秒")
        logger.info(f"   - 思考时间: {self.config.think_time} 秒")
        logger.info(f"   - 测试上传: {self.config.upload_files}")
        logger.info(f"   - 测试分析: {self.config.analyze_files}")
        
        start_time = time.time()
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=self.config.concurrent_users) as executor:
            # 提交用户工作负载
            futures = []
            for i in range(self.config.concurrent_users):
                future = executor.submit(self.user_workload, i + 1)
                futures.append(future)
            
            # 等待测试完成或超时
            try:
                for future in as_completed(futures, timeout=self.config.test_duration):
                    pass
            except Exception:
                logger.info("⏰ 测试时间到，停止测试")
            
            # 停止所有线程
            self.stop_event.set()
        
        end_time = time.time()
        
        # 收集结果
        results = []
        while not self.results_queue.empty():
            results.append(self.results_queue.get())
        
        # 生成报告
        self.generate_report(results, end_time - start_time)
    
    def generate_report(self, results: List[TestResult], total_time: float):
        """生成测试报告"""
        logger.info("📋 生成测试报告")
        
        # 按测试类型分组
        test_groups = {}
        for result in results:
            if result.test_name not in test_groups:
                test_groups[result.test_name] = []
            test_groups[result.test_name].append(result)
        
        # 计算统计信息
        report = {
            'test_summary': {
                'total_time': total_time,
                'total_requests': len(results),
                'concurrent_users': self.config.concurrent_users,
                'test_duration': self.config.test_duration
            },
            'test_results': {}
        }
        
        for test_name, test_results in test_groups.items():
            response_times = [r.response_time for r in test_results]
            success_count = sum(1 for r in test_results if r.success)
            error_count = len(test_results) - success_count
            
            report['test_results'][test_name] = {
                'total_requests': len(test_results),
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': success_count / len(test_results) * 100,
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': statistics.median(response_times),
                'p95_response_time': np.percentile(response_times, 95),
                'p99_response_time': np.percentile(response_times, 99),
                'requests_per_second': len(test_results) / total_time
            }
        
        # 打印报告
        self.print_report(report)
        
        # 保存报告
        self.save_report(report)
    
    def print_report(self, report: Dict):
        """打印测试报告"""
        print("\n" + "="*80)
        print("📊 axSpA 系统压力测试报告")
        print("="*80)
        
        summary = report['test_summary']
        print(f"总测试时间: {summary['total_time']:.2f} 秒")
        print(f"总请求数: {summary['total_requests']}")
        print(f"并发用户数: {summary['concurrent_users']}")
        print(f"平均每秒请求数: {summary['total_requests'] / summary['total_time']:.2f}")
        
        print("\n" + "-"*80)
        print("各接口测试结果:")
        print("-"*80)
        
        for test_name, result in report['test_results'].items():
            print(f"\n🔍 {test_name.upper()}:")
            print(f"  总请求数: {result['total_requests']}")
            print(f"  成功数: {result['success_count']}")
            print(f"  失败数: {result['error_count']}")
            print(f"  成功率: {result['success_rate']:.2f}%")
            print(f"  平均响应时间: {result['avg_response_time']:.3f}秒")
            print(f"  最小响应时间: {result['min_response_time']:.3f}秒")
            print(f"  最大响应时间: {result['max_response_time']:.3f}秒")
            print(f"  中位数响应时间: {result['median_response_time']:.3f}秒")
            print(f"  P95响应时间: {result['p95_response_time']:.3f}秒")
            print(f"  P99响应时间: {result['p99_response_time']:.3f}秒")
            print(f"  每秒请求数: {result['requests_per_second']:.2f}")
        
        print("\n" + "="*80)
    
    def save_report(self, report: Dict):
        """保存测试报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 测试报告已保存到: {filename}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='axSpA 系统压力测试')
    parser.add_argument('--users', type=int, default=10, help='并发用户数 (默认: 10)')
    parser.add_argument('--duration', type=int, default=60, help='测试时长(秒) (默认: 60)')
    parser.add_argument('--think-time', type=float, default=1.0, help='思考时间(秒) (默认: 1.0)')
    parser.add_argument('--no-upload', action='store_true', help='跳过文件上传测试')
    parser.add_argument('--no-analyze', action='store_true', help='跳过分析测试')
    parser.add_argument('--url', type=str, default='http://152.136.58.167:5500', help='目标URL')
    
    args = parser.parse_args()
    
    # 创建配置
    config = StressTestConfig()
    config.concurrent_users = args.users
    config.test_duration = args.duration
    config.think_time = args.think_time
    config.upload_files = not args.no_upload
    config.analyze_files = not args.no_analyze
    config.base_url = args.url
    
    # 创建测试器并运行
    tester = StressTester(config)
    tester.run_stress_test()

if __name__ == "__main__":
    main() 