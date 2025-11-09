# -*- coding: utf-8 -*-
"""
axSpA 智能诊断系统 - 在线Web服务
"""

from flask import Flask, request, Response, stream_with_context, send_from_directory, redirect, url_for, session, render_template_string, jsonify
from flask_cors import CORS
import numpy as np
import sys
import os
import time
import uuid
import importlib
import io
import traceback
import json
import re
import shutil
import tempfile
import SimpleITK as sitk
import numpy as np
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

def ImageResample(sitk_img, new_size=[512, 512, None], is_label=False):
    size = np.array(sitk_img.GetSize())
    spacing = np.array(sitk_img.GetSpacing())
    if new_size[2] is None:
        new_size = [new_size[0], new_size[1], int(size[2])]
    new_spacing_refine = size * spacing / new_size
    new_spacing_refine = [float(s) for s in new_spacing_refine]
    new_size = [int(s) for s in new_size]
    resample = sitk.ResampleImageFilter()
    resample.SetOutputDirection(sitk_img.GetDirection())
    resample.SetOutputOrigin(sitk_img.GetOrigin())
    resample.SetSize(new_size)
    resample.SetOutputSpacing(new_spacing_refine)
    if is_label:
        resample.SetInterpolator(sitk.sitkNearestNeighbor)
    else:
        resample.SetInterpolator(sitk.sitkBSpline)
    return resample.Execute(sitk_img)

def resizeImageWithCropOrPad(image: np.ndarray, img_size=(24, 512, 512), **kwargs) -> np.ndarray:
    assert image.ndim == 3 and len(img_size) == 3
    from_indices = [[0, s] for s in image.shape]
    to_padding   = [[0, 0]  for _ in range(3)]
    slicer       = [slice(None)] * 3
    for dim in range(3):
        diff = image.shape[dim] - img_size[dim]
        if diff >= 0:                       # 裁剪
            start = diff // 2
            from_indices[dim] = [start, start + img_size[dim]]
        else:                              # 填充
            pad_total  = -diff
            pad_before = pad_total // 2
            pad_after  = pad_total - pad_before
            to_padding[dim] = (pad_before, pad_after)
        slicer[dim] = slice(from_indices[dim][0], from_indices[dim][1])
    cropped = image[slicer[0], slicer[1], slicer[2]]
    return np.pad(cropped, pad_width=to_padding, mode="constant", **kwargs)

def linear_scale_image(image: np.ndarray, up_quantile=99, low_quantile=1) -> np.ndarray:
    max_val = np.percentile(image, up_quantile)
    min_val = np.percentile(image, low_quantile)
    scaled  = (image - min_val) / (max_val - min_val)
    return np.clip(scaled, 0, 1)

def preprocess_npy_like_official(npy_array, tgt_shape=(24,512,512)):
    # Step1 形状处理
    if npy_array.shape != tgt_shape:
        npy_array = resizeImageWithCropOrPad(npy_array, img_size=tgt_shape)
    # Step2 线性拉伸
    npy_array = linear_scale_image(npy_array).astype(np.float32)
    return npy_array

def preprocess_image_v3(dicom_dir, out_z=24, out_hw=512):
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
    reader.SetFileNames(dicom_names)
    sitk_img = reader.Execute()
    z = sitk_img.GetSize()[2]
    sitk_img = ImageResample(sitk_img, new_size=[out_hw, out_hw, z])
    img = sitk.GetArrayFromImage(sitk_img)  # (z, 512, 512)
    img = resizeImageWithCropOrPad(img, img_size=(out_z, out_hw, out_hw))
    img = linear_scale_image(img)
    return img

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.planner_agent import PlannerAgent

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'your_secret_key_here'  # 用于session
# 设置文件上传大小限制为500MB
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_conn():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# 系统维护模式配置
MAINTENANCE_MODE = True  # 设置为True时，只允许管理员登录
ADMIN_USERNAME = 'admin'  # 管理员用户名

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 维护模式检查：只允许管理员登录
        if MAINTENANCE_MODE and username != ADMIN_USERNAME:
            return render_template_string(open('static/login.html').read(), 
                                        error='系统维护中，暂时只允许管理员登录')
        
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE username=%s', (username,))
                user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['username'] = username
                session['is_admin'] = user.get('is_admin', False)
                return redirect('/')
            else:
                return render_template_string(open('static/login.html').read(), error='账号或密码错误')
        finally:
            conn.close()
    return render_template_string(open('static/login.html').read(), error=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # 维护模式检查：禁止注册
    if MAINTENANCE_MODE:
        return render_template_string(open('static/register.html').read(), 
                                    error='系统维护中，暂时禁止新用户注册')
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password:
            return render_template_string(open('static/register.html').read(), error='账号和密码不能为空')
        
        if password != confirm_password:
            return render_template_string(open('static/register.html').read(), error='两次输入的密码不一致')
        
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE username=%s', (username,))
                if cursor.fetchone():
                    return render_template_string(open('static/register.html').read(), error='账号已存在')
                password_hash = generate_password_hash(password)
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s)', (username, password_hash))
                conn.commit()
            return redirect('/login')
        finally:
            conn.close()
    return render_template_string(open('static/register.html').read(), error=None)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    if request.method == 'POST':
        return jsonify({'success': True})
    return redirect('/login')



# ====== 加载 config 和 agent ======
# 根据环境自动选择配置文件
import os
if os.path.exists("/var/www/axspa-system"):  # 服务器环境
    experiment_name = "ex_tool_2_server"
else:  # 本地环境
    experiment_name = "ex_tool_2"

module_path = f"config.config_{experiment_name}"
config = getattr(importlib.import_module(module_path), "config")
# 设置日志路径为控制台输出
config["PlannerAgent"]["log_path"] = "log/planner_agent.log"
config["DoctorAgent"]["log_path"] = "log/diagnosis_agent.log"
config["DataAgent"]["log_path"] = "log/data_agent.log"
config["ToolAgent"]["log_path"] = "log/model_agent.log"
AS_agents = PlannerAgent(config)

# ====== 1. 上传文件 ======
@app.route('/upload', methods=['POST'])
def upload():
    try:
        print(f"[UPLOAD] 开始处理上传请求")
        print(f"[UPLOAD] Content-Type: {request.content_type}")
        print(f"[UPLOAD] Content-Length: {request.content_length}")
        
        files = request.files.getlist('files')
        print(f"[UPLOAD] 检测到 {len(files)} 个文件")
        
        if files and len(files) > 0:
            file_id = str(uuid.uuid4())
            dicom_dir = os.path.join(UPLOAD_FOLDER, file_id)
            os.makedirs(dicom_dir, exist_ok=True)
            
            print(f"[UPLOAD] 创建临时目录: {dicom_dir}")
            
            # 验证文件类型
            for f in files:
                if not (f.filename.endswith('.dcm') or '.' not in f.filename):
                    print(f"[UPLOAD] 不支持的文件类型: {f.filename}")
                    shutil.rmtree(dicom_dir)
                    return {"error": "仅支持DICOM(.dcm)文件"}, 400
                save_path = os.path.join(dicom_dir, f.filename)
                f.save(save_path)
                print(f"[UPLOAD] 保存文件: {f.filename}")
            
            try:
                print(f"[UPLOAD] 开始DICOM转NPY处理")
                # Step1: DICOM转原始NPY（不做插值/归一化）
                reader = sitk.ImageSeriesReader()
                dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
                print(f"[UPLOAD] 找到 {len(dicom_names)} 个DICOM文件")
                reader.SetFileNames(dicom_names)
                image = reader.Execute()
                image_array = sitk.GetArrayFromImage(image)  # shape: [z, h, w]
                print(f"[UPLOAD] 图像形状: {image_array.shape}")
                
                # Step2: 标准化处理
                npy_img = preprocess_npy_like_official(image_array)
                npy_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.npy")
                np.save(npy_path, npy_img)
                print(f"[UPLOAD] NPY文件保存成功: {npy_path}")
                
                shutil.rmtree(dicom_dir)
                print(f"[UPLOAD] 清理临时目录")
                
                return {"file_id": file_id}
            except Exception as e:
                print(f"[UPLOAD] DICOM转NPY失败: {str(e)}")
                print(f"[UPLOAD] 错误详情: {traceback.format_exc()}")
                shutil.rmtree(dicom_dir)
                return {"error": f"DICOM转NPY失败: {str(e)}"}, 500
        else:
            if 'file' not in request.files:
                print(f"[UPLOAD] 未提供文件")
                return {"error": "未提供文件"}, 400
            file = request.files['file']
            if not file.filename.endswith(".npy"):
                print(f"[UPLOAD] 不支持的文件类型: {file.filename}")
                return {"error": "只支持 .npy 或 DICOM 文件"}, 400
            file_id = str(uuid.uuid4())
            file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.npy")
            try:
                file.save(file_path)
                print(f"[UPLOAD] NPY文件保存成功: {file_path}")
                return {"file_id": file_id}
            except Exception as e:
                print(f"[UPLOAD] 保存NPY文件失败: {str(e)}")
                return {"error": f"保存文件失败: {str(e)}"}, 500
    except Exception as e:
        print(f"[UPLOAD] 上传处理异常: {str(e)}")
        print(f"[UPLOAD] 错误详情: {traceback.format_exc()}")
        return {"error": f"上传失败: {str(e)}"}, 500

# ====== 1.1. 分批上传文件 ======
@app.route('/upload_batch', methods=['POST'])
def upload_batch():
    try:
        print(f"[UPLOAD_BATCH] 开始处理分批上传请求")
        print(f"[UPLOAD_BATCH] Content-Type: {request.content_type}")
        print(f"[UPLOAD_BATCH] Content-Length: {request.content_length}")
        
        files = request.files.getlist('files')
        print(f"[UPLOAD_BATCH] 检测到 {len(files)} 个文件")
        
        if not files or len(files) == 0:
            return {"error": "未提供文件"}, 400
        
        # 为每个文件创建单独的目录
        file_ids = []
        for f in files:
            if not (f.filename.endswith('.dcm') or '.' not in f.filename):
                print(f"[UPLOAD_BATCH] 不支持的文件类型: {f.filename}")
                return {"error": "仅支持DICOM(.dcm)文件"}, 400
            
            file_id = str(uuid.uuid4())
            dicom_dir = os.path.join(UPLOAD_FOLDER, file_id)
            os.makedirs(dicom_dir, exist_ok=True)
            
            save_path = os.path.join(dicom_dir, f.filename)
            f.save(save_path)
            print(f"[UPLOAD_BATCH] 保存文件: {f.filename} -> {file_id}")
            
            file_ids.append(file_id)
        
        return {"file_ids": file_ids, "count": len(file_ids)}
        
    except Exception as e:
        print(f"[UPLOAD_BATCH] 分批上传处理异常: {str(e)}")
        print(f"[UPLOAD_BATCH] 错误详情: {traceback.format_exc()}")
        return {"error": f"分批上传失败: {str(e)}"}, 500

# ====== 1.3. 压缩包上传 ======
@app.route('/upload_zip', methods=['POST'])
def upload_zip():
    try:
        print(f"[UPLOAD_ZIP] 开始处理压缩包上传")
        print(f"[UPLOAD_ZIP] Content-Type: {request.content_type}")
        print(f"[UPLOAD_ZIP] Content-Length: {request.content_length}")
        
        if 'zip_file' not in request.files:
            print(f"[UPLOAD_ZIP] 未提供压缩包文件")
            return {"error": "未提供压缩包文件"}, 400
        
        zip_file = request.files['zip_file']
        if not zip_file.filename.endswith('.zip'):
            print(f"[UPLOAD_ZIP] 不支持的文件类型: {zip_file.filename}")
            return {"error": "只支持ZIP压缩包"}, 400
        
        # 创建临时目录
        file_id = str(uuid.uuid4())
        temp_dir = os.path.join(UPLOAD_FOLDER, file_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        print(f"[UPLOAD_ZIP] 创建临时目录: {temp_dir}")
        
        # 保存压缩包
        zip_path = os.path.join(temp_dir, 'dicom_files.zip')
        zip_file.save(zip_path)
        print(f"[UPLOAD_ZIP] 压缩包保存成功: {zip_path}")
        
        try:
            # 解压文件
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            print(f"[UPLOAD_ZIP] 解压完成，开始DICOM处理")
            
            # 处理DICOM文件
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(temp_dir)
            print(f"[UPLOAD_ZIP] 找到 {len(dicom_names)} 个DICOM文件")
            
            if len(dicom_names) == 0:
                raise Exception("未找到DICOM文件")
            
            reader.SetFileNames(dicom_names)
            image = reader.Execute()
            image_array = sitk.GetArrayFromImage(image)
            print(f"[UPLOAD_ZIP] 图像形状: {image_array.shape}")
            
            # 标准化处理
            npy_img = preprocess_npy_like_official(image_array)
            npy_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.npy")
            np.save(npy_path, npy_img)
            print(f"[UPLOAD_ZIP] NPY文件保存成功: {npy_path}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            print(f"[UPLOAD_ZIP] 清理完成")
            
            return {"file_id": file_id}
            
        except Exception as e:
            print(f"[UPLOAD_ZIP] 处理失败: {str(e)}")
            print(f"[UPLOAD_ZIP] 错误详情: {traceback.format_exc()}")
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return {"error": f"压缩包处理失败: {str(e)}"}, 500
            
    except Exception as e:
        print(f"[UPLOAD_ZIP] 上传处理异常: {str(e)}")
        print(f"[UPLOAD_ZIP] 错误详情: {traceback.format_exc()}")
        return {"error": f"压缩包上传失败: {str(e)}"}, 500

# ====== 2. 分析文件，实时返回推理日志 ======
@app.route('/analyze/<file_id>', methods=['GET'])
def analyze(file_id):
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.npy")
    if not os.path.exists(file_path):
        return Response("event: error\ndata: 文件未找到\n\n", mimetype="text/event-stream")

    # 获取表单数据
    form_data_str = request.args.get('formData', '{}')
    try:
        form_data = json.loads(form_data_str)
    except:
        form_data = {}

    # 构建包含病历信息的查询
    medical_info = ""
    if form_data:
        medical_info = f"""
病历信息：
- 年龄：{form_data.get('age', '未提供')}
- 性别：{form_data.get('sex', '未提供')}
- 影像报告时间：{form_data.get('reportTime', '未提供')}
- 影像报告所见：{form_data.get('reportFind', '未提供')}
- 现病史：{form_data.get('presentIllness', '未提供')}
- 既往史：{form_data.get('pastIllness', '未提供')}
- 家族史：{form_data.get('familyHistory', '未提供')}
- 体格检查：{form_data.get('physicalExam', '未提供')}
- HLA-B27检查结果：{form_data.get('b27', '未提供')}
- C反应蛋白(CRP)：{form_data.get('crp', '未提供')} mg/dl
- 红细胞沉降率(ESR)：{form_data.get('esr', '未提供')} mm/h
"""

    query = f"请对以下MRI图像进行完整的axSpA诊断：\n文件路径：{file_path}\n{medical_info}\n这是一个直接上传的npy文件，请调用DataAgent获取文件数据，然后调用ToolAgent进行影像分析，最后调用DoctorAgent给出诊断结果。"

    def generate():
        stream = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stream

        try:
            yield f"data: 🧠 正在分析文件：{file_path}\n\n"
            yield f"data: [INFO] 🚀 开始调用 generate_response()\n\n"
            yield f"data: [INFO] 📝 查询内容：{query}\n\n"

            start = time.time()
            result = AS_agents.generate_response(query)
            elapsed = round(time.time() - start, 2)

            yield f"data: [INFO] ✅ 推理完成，耗时 {elapsed} 秒\n\n"
            yield f"data: [INFO] 📋 诊断摘要：{str(result)[:100]}\n\n"

            sys.stdout.flush()
            stream.seek(0)
            for line in stream.readlines():
                if line.strip():
                    yield f"data: {line.strip()}\n\n"

            yield f"data: ✅ 推理完成，总耗时 {elapsed} 秒\n\n"
            
            # 尝试从结果中提取诊断JSON
            print("[DEBUG] generate: 开始调用extract_diagnosis_json函数")
            diagnosis_json = extract_diagnosis_json(str(result))
            if diagnosis_json:
                print(f"[DEBUG] generate: 成功提取诊断JSON: {diagnosis_json}")
                try:
                    parsed = json.loads(diagnosis_json)
                    diagnosis_result = int(parsed.get("diagnosis_result", -1))
                    reason = parsed.get("reason", "")
                    suggestion = parsed.get("suggestion", "")

                    if diagnosis_result == 1:
                        diag_text = "✅ 可以诊断为axSpA"
                    elif diagnosis_result == 0:
                        diag_text = "❌ 未诊断为axSpA"
                    elif diagnosis_result == -1:
                        diag_text = "❓ 无法确定诊断"
                    else:
                        diag_text = f"❓ 诊断结果: {diagnosis_result}"

                    # 构建最终诊断文字输出
                    final_result_text = f"""🧾 最终诊断结果：\n            诊断结果：{diag_text}\n            {f"诊断理由：{reason}" if reason else ""}\n            {f"治疗建议：{suggestion}" if suggestion else ""}\n            """
                    print(f"[DEBUG] generate: 推送final_result_text到前端:\n{final_result_text}")
                    yield f"data: {final_result_text}\n\n"

                    # 同时发结构化 JSON，供前端调用 displayDiagnosisResult()
                    print(f"[DEBUG] generate: 推送diagnosis_json到前端: {parsed}")
                    yield f"data: 🎯 诊断结果JSON: {json.dumps(parsed, ensure_ascii=False)}\n\n"

                except Exception as e:
                    print("[DEBUG] generate: JSON解析失败:", e)
                    yield f"data: ⛔ JSON解析失败: {e}\n\n"

            else:
                print("[DEBUG] generate: 未能提取到诊断JSON")
                print(f"[DEBUG] generate: 完整结果: {str(result)}")
                
                # 尝试从文本解析
                print("[DEBUG] generate: 尝试从文本结果中解析诊断信息")
                diagnosis_result = parse_diagnosis_from_text(str(result))
                if diagnosis_result:
                    print(f"[DEBUG] generate: 从文本解析的诊断结果: {diagnosis_result}")
                    # 重复上面的结构化输出逻辑
                    diagnosis = diagnosis_result.get("diagnosis_result", -1)
                    reason = diagnosis_result.get("reason", "")
                    suggestion = diagnosis_result.get("suggestion", "")

                    if diagnosis == 1:
                        diag_text = "✅ 可以诊断为axSpA"
                    elif diagnosis == 0:
                        diag_text = "❌ 未诊断为axSpA"
                    elif diagnosis == -1:
                        diag_text = "❓ 无法确定诊断"
                    else:
                        diag_text = f"❓ 诊断结果: {diagnosis}"

                    final_result_text = f"""🧾 最终诊断结果：\n            诊断结果：{diag_text}\n            {f"诊断理由：{reason}" if reason else ""}\n            {f"治疗建议：{suggestion}" if suggestion else ""}\n            """
                    print(f"[DEBUG] generate: 推送final_result_text到前端(文本解析):\n{final_result_text}")
                    yield f"data: {final_result_text}\n\n"
                    print(f"[DEBUG] generate: 推送diagnosis_result到前端(文本解析): {diagnosis_result}")
                    yield f"data: 🎯 诊断结果JSON: {json.dumps(diagnosis_result, ensure_ascii=False)}\n\n"
                else:
                    print("[DEBUG] generate: 无法从文本中解析诊断信息")
                    yield f"data: ⛔ 无法提取诊断JSON，也无法从文本中解析诊断结论。\n\n"
            
            yield f"event: done\ndata: done\n\n"

        except Exception as e:
            tb = traceback.format_exc()
            yield f"event: error\ndata: 推理失败: {str(e)}\n\n"
            yield f"data: ⛔ 详细错误:\n{tb}\n\n"
        finally:
            sys.stdout = old_stdout
            AS_agents.clear_llm_cache()

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route('/analyze/skip', methods=['GET'])
def analyze_skip():
    # 获取表单数据
    form_data_str = request.args.get('formData', '{}')
    try:
        form_data = json.loads(form_data_str)
    except:
        form_data = {}

    # 构建包含病历信息的查询
    medical_info = ""
    if form_data:
        medical_info = f"""
病历信息：
- 年龄：{form_data.get('age', '未提供')}
- 性别：{form_data.get('sex', '未提供')}
- 影像报告时间：{form_data.get('reportTime', '未提供')}
- 影像报告所见：{form_data.get('reportFind', '未提供')}
- 现病史：{form_data.get('presentIllness', '未提供')}
- 既往史：{form_data.get('pastIllness', '未提供')}
- 家族史：{form_data.get('familyHistory', '未提供')}
- 体格检查：{form_data.get('physicalExam', '未提供')}
- HLA-B27检查结果：{form_data.get('b27', '未提供')}
- C反应蛋白(CRP)：{form_data.get('crp', '未提供')} mg/dl
- 红细胞沉降率(ESR)：{form_data.get('esr', '未提供')} mm/h
"""

    query = f"请根据以下病历信息进行axSpA诊断：\n{medical_info}\n注意：本次无影像文件上传，请仅基于病历信息和实验室检查等进行推理。"

    def generate():
        stream = io.StringIO()
        old_stdout = sys.stdout
        #sys.stdout = stream
        try:
            yield f"data: 🧠 正在分析无影像文件的病例...\n\n"
            yield f"data: [INFO] 🚀 开始调用 generate_response()\n\n"
            yield f"data: [INFO] 📝 查询内容：{query}\n\n"
            start = time.time()
            result = AS_agents.generate_response(query)
            elapsed = round(time.time() - start, 2)
            yield f"data: [INFO] ✅ 推理完成，耗时 {elapsed} 秒\n\n"
            yield f"data: [INFO] 📋 诊断摘要：{str(result)[:100]}\n\n"
            sys.stdout.flush()
            stream.seek(0)
            for line in stream.readlines():
                if line.strip():
                    yield f"data: {line.strip()}\n\n"
            yield f"data: ✅ 推理完成，总耗时 {elapsed} 秒\n\n"
            # 尝试结构化输出
            diagnosis_json = extract_diagnosis_json(str(result))
            if diagnosis_json:
                try:
                    parsed = json.loads(diagnosis_json)
                    diagnosis_result = parsed.get("diagnosis_result", -1)
                    reason = parsed.get("reason", "")
                    suggestion = parsed.get("suggestion", "")
                    if diagnosis_result == 1:
                        diag_text = "✅ 可以诊断为axSpA"
                    elif diagnosis_result == 0:
                        diag_text = "❌ 未诊断为axSpA"
                    elif diagnosis_result == -1:
                        diag_text = "❓ 无法确定诊断"
                    else:
                        diag_text = f"❓ 诊断结果: {diagnosis_result}"
                    final_result_text = f"""🧾 最终诊断结果：\n            诊断结果：{diag_text}\n            {f"诊断理由：{reason}" if reason else ""}\n            {f"治疗建议：{suggestion}" if suggestion else ""}\n            """
                    yield f"data: {final_result_text}\n\n"
                    yield f"data: 🎯 诊断结果JSON: {json.dumps(parsed, ensure_ascii=False)}\n\n"
                except Exception as e:
                    yield f"data: ⛔ JSON解析失败: {e}\n\n"
            else:
                # 新增：尝试用 parse_diagnosis_from_text
                diagnosis_result = parse_diagnosis_from_text(str(result))
                if diagnosis_result:
                    # 推送降级JSON
                    yield f"data: 🎯 诊断结果JSON: {json.dumps(diagnosis_result, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: ⛔ 无法提取诊断JSON。\n\n"
            yield f"event: done\ndata: done\n\n"
        except Exception as e:
            tb = traceback.format_exc()
            yield f"event: error\ndata: 推理失败: {str(e)}\n\n"
            yield f"data: ⛔ 详细错误:\n{tb}\n\n"
        finally:
            sys.stdout = old_stdout
            AS_agents.clear_llm_cache()
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

def parse_diagnosis_from_text(result_str):
    """从文本结果中解析诊断信息，优先取否定、再取肯定、最后不确定。"""
    print(f"\n==================== 开始解析文本诊断结果 ====================\n长度: {len(result_str)}")
    print(f"文本前500字符: {result_str[:500]}")
    try:
        # 优先否定
        if "未诊断为axSpA" in result_str or "axSpA阴性" in result_str:
            diagnosis_result = 0
        # 肯定
        elif "可以诊断为axSpA" in result_str or "诊断为axSpA" in result_str or "axSpA阳性" in result_str or "axSpA诊断成立" in result_str:
            diagnosis_result = 1
        # 不确定
        elif "无法确定诊断" in result_str or "诊断不明确" in result_str:
            diagnosis_result = -1
        else:
            diagnosis_result = -1
        reason = ""
        suggestion = ""
        # 提取诊断理由
        if "诊断理由" in result_str:
            reason_start = result_str.find("诊断理由")
            reason_end = result_str.find("\n", reason_start)
            if reason_end == -1:
                reason_end = len(result_str)
            reason = result_str[reason_start:reason_end].replace("诊断理由", "").strip()
            reason = reason.lstrip('：:').strip()  # 新增：去掉开头的冒号和空格
        # 提取治疗建议
        if "治疗建议" in result_str:
            suggestion_start = result_str.find("治疗建议")
            suggestion_end = result_str.find("\n", suggestion_start)
            if suggestion_end == -1:
                suggestion_end = len(result_str)
            suggestion = result_str[suggestion_start:suggestion_end].replace("治疗建议", "").strip()
            suggestion = suggestion.lstrip('：:').strip()  # 新增：去掉开头的冒号和空格
        print(f"[DEBUG] parse_diagnosis_from_text: diagnosis_result={diagnosis_result}, reason={reason}, suggestion={suggestion}")
        return {
            "diagnosis_result": diagnosis_result,
            "reason": reason,
            "suggestion": suggestion
        }
    except Exception as e:
        print(f"解析文本诊断结果时出错: {e}")
        return None

def extract_diagnosis_json(result_str):
    print("\n==================== LLM原始输出 ====================\n", result_str, "\n====================================================\n")
    # 方法1: 匹配markdown代码块
    json_pattern = r'```json\s*([\s\S]*?)\s*```'
    matches = re.findall(json_pattern, result_str)
    all_jsons = []
    if matches:
        print(f"[DEBUG] extract_diagnosis_json: 匹配到 {len(matches)} 个 ```json``` 块")
        for json_str in matches[::-1]:
            try:
                parsed = json.loads(json_str)
                print(f"[DEBUG] extract_diagnosis_json: 解析JSON成功: {parsed}")
                all_jsons.append((parsed, json_str))
            except Exception as e:
                print(f"[DEBUG] extract_diagnosis_json: 解析JSON失败: {e}, 内容: {json_str}")
                continue
    # 方法2: diagnosis_result
    if not all_jsons:
        diagnosis_pattern = r'\{[^{}]*"diagnosis_result"[^{}]*\}'
        matches = re.findall(diagnosis_pattern, result_str)
        print(f"[DEBUG] extract_diagnosis_json: 方法2匹配到 {len(matches)} 个 diagnosis_result 块")
        for json_str in matches[::-1]:
            try:
                parsed = json.loads(json_str)
                print(f"[DEBUG] extract_diagnosis_json: 解析JSON成功: {parsed}")
                all_jsons.append((parsed, json_str))
            except Exception as e:
                print(f"[DEBUG] extract_diagnosis_json: 解析JSON失败: {e}, 内容: {json_str}")
                continue
    # 方法3: diagnosis_result+reason+suggestion
    if not all_jsons:
        json_pattern2 = r'\{[^{}]*"diagnosis_result"[^{}]*"reason"[^{}]*"suggestion"[^{}]*\}'
        matches = re.findall(json_pattern2, result_str)
        print(f"[DEBUG] extract_diagnosis_json: 方法3匹配到 {len(matches)} 个 diagnosis_result+reason+suggestion 块")
        for json_str in matches[::-1]:
            try:
                parsed = json.loads(json_str)
                print(f"[DEBUG] extract_diagnosis_json: 解析JSON成功: {parsed}")
                all_jsons.append((parsed, json_str))
            except Exception as e:
                print(f"[DEBUG] extract_diagnosis_json: 解析JSON失败: {e}, 内容: {json_str}")
                continue

    print(f"[DEBUG] extract_diagnosis_json: all_jsons = {all_jsons}")
    # 优先使用 diagnosis_result 字段
    for parsed, json_str in all_jsons:
        if "diagnosis_result" in parsed:
            print(f"[DEBUG] extract_diagnosis_json: 命中diagnosis_result: {parsed}")
            return json.dumps(parsed, ensure_ascii=False)
    if all_jsons:
        print(f"[DEBUG] extract_diagnosis_json: 返回第一个JSON: {all_jsons[0][0]}")
        return json.dumps(all_jsons[0][0], ensure_ascii=False)

    # 兜底：用正则提取所有 {...}，逐个尝试解析
    brace_pattern = r'\{[\s\S]*?\}'
    matches = re.findall(brace_pattern, result_str)
    for json_str in matches:
        try:
            parsed = json.loads(json_str)
            if all(k in parsed for k in ["diagnosis_result", "reason", "suggestion"]):
                print(f"[DEBUG] extract_diagnosis_json: 兜底多JSON解析成功: {parsed}")
                return json.dumps(parsed, ensure_ascii=False)
        except Exception as e:
            continue

    print("所有方法都未找到有效的诊断JSON")
    return None

# ====== 3. 提供Web界面 ======
# 修改主页路由，未登录跳转到登录页
@app.route('/')
def index():
    if 'username' not in session:
        return redirect('/login')
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    print("🚀 启动 axSpA 智能诊断系统...")
    print("📱 Web界面地址: http://0.0.0.0:5500")
    print("📁 支持上传 .npy 格式的MRI影像文件")
    app.run(host='0.0.0.0', port=5500, debug=False, use_reloader=False, threaded=True)