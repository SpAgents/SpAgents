# axSpA 智能诊断系统 - 在线版本

这是一个基于多智能体系统的中轴型脊柱关节炎（axSpA）在线诊断平台。

## 🚀 快速开始

### 方法一：使用启动脚本（推荐）

```bash
cd evaluation
python run_online_system.py
```

启动脚本会自动：
1. 检查依赖包
2. 创建测试文件
3. 启动Web服务
4. 打开浏览器

### 方法二：手动启动

1. **安装依赖**
```bash
pip install flask flask-cors numpy pandas
```

2. **启动服务**
```bash
cd evaluation
python evaluation_online.py
```

3. **访问Web界面**
打开浏览器访问：http://localhost:5500

## 📋 功能特性

### 🎯 核心功能
- **文件上传**：支持拖拽上传 .npy 格式的MRI影像文件
- **实时诊断**：使用Server-Sent Events (SSE) 实时显示诊断过程
- **智能分析**：基于多智能体系统进行axSpA诊断
- **结果展示**：清晰展示诊断结果、理由和治疗建议

### 🧠 智能体系统
- **DataAgent**：负责获取和管理病人数据
- **ToolAgent**：负责调用医学影像分析模型
- **DoctorAgent**：负责进行axSpA诊断决策
- **PlannerAgent**：负责协调各个智能体

### 📊 诊断标准
基于ASAS分类标准：
- **影像学路径**：骶髂关节影像学检查显示骶髂关节炎 + 至少一个SpA特征
- **HLA-B27路径**：HLA-B27阳性 + 至少两个SpA特征

## 🎨 界面说明

### 主界面
- **文件上传区域**：拖拽或点击选择 .npy 文件
- **进度显示**：实时显示上传和分析进度
- **诊断日志**：显示详细的诊断过程信息
- **结果展示**：最终诊断结果和建议

### 操作流程
1. **上传文件** → 拖拽或选择 .npy 文件
2. **开始分析** → 点击"开始诊断分析"按钮
3. **实时监控** → 查看诊断过程日志
4. **获取结果** → 查看最终诊断结果

## 📁 文件结构

```
evaluation/
├── evaluation_online.py      # 主服务文件
├── run_online_system.py      # 启动脚本
├── create_test_npy.py        # 测试文件生成器
├── static/
│   └── index.html           # Web界面
├── uploads/                 # 上传文件存储目录
└── README_online.md         # 说明文档
```

## 🔧 技术栈

### 后端
- **Flask**：Web框架
- **Flask-CORS**：跨域支持
- **NumPy**：数值计算
- **Pandas**：数据处理

### 前端
- **HTML5**：页面结构
- **CSS3**：样式设计
- **JavaScript**：交互逻辑
- **Server-Sent Events**：实时通信

### AI模型
- **多智能体系统**：协作诊断
- **深度学习模型**：影像分析
- **大语言模型**：诊断决策

## 📝 使用示例

### 1. 启动系统
```bash
python run_online_system.py
```

### 2. 访问界面
浏览器自动打开：http://localhost:5500

### 3. 上传文件
- 拖拽 .npy 文件到上传区域
- 或点击选择文件

### 4. 开始诊断
- 点击"开始诊断分析"
- 观察实时诊断过程
- 查看最终诊断结果

## ⚠️ 注意事项

### 文件要求
- **格式**：仅支持 .npy 格式
- **内容**：MRI影像数据
- **大小**：建议不超过100MB

### 系统要求
- **Python**：3.7+
- **内存**：建议4GB+
- **网络**：本地访问，无需外网

### 故障排除

#### 1. 端口被占用
```bash
# 查看端口占用
lsof -i :5500

# 杀死进程
kill -9 <PID>
```

#### 2. 依赖缺失
```bash
pip install flask flask-cors numpy pandas
```

#### 3. 权限问题
```bash
# 确保有写入权限
chmod +x run_online_system.py
```

## 🔍 调试模式

如需调试，可以修改 `evaluation_online.py`：

```python
# 开启调试模式
app.run(port=5500, debug=True, use_reloader=False)
```

## 📞 技术支持

如遇问题，请检查：
1. Python版本是否兼容
2. 依赖包是否完整安装
3. 端口5500是否被占用
4. 文件权限是否正确

## 🎯 测试数据

系统会自动创建测试文件 `test_mri.npy`，你可以：
1. 使用这个测试文件进行功能测试
2. 准备自己的MRI数据文件
3. 使用项目中的示例数据

---

**注意**：这是一个演示系统，实际医疗诊断请咨询专业医生。 