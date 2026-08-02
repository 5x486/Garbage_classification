# 垃圾分类助手

一个基于 Django + PyTorch 的 Web 应用，使用深度学习（MobileNetV3）识别 40 种垃圾类别，支持图片/视频/摄像头三种识别模式。

> ⚠️ **声明**：本代码仅供学习编程原理，严禁用于任何实际数据抓取或者商业用途。

## 功能

| 功能 | 说明 |
|------|------|
| 📷 **图片识别** | 上传垃圾照片，返回 Top-3 分类结果 + 信心度 + 投放建议 |
| 🎥 **视频识别** | 上传视频，按间隔抽帧识别，统计各类占比 |
| 📹 **摄像头实时识别** | 浏览器调用摄像头，定时抓拍识别，实时显示结果 |
| 📋 **识别历史** | 所有识别记录存入数据库，首页可查看历史 |
| 🔐 **用户系统** | 注册、登录、退出、记住我、密码重置 |
| 🔌 **RESTful API** | 三个 API 端点，可供外部调用 |

## 分类体系

模型识别 **40 种细分类别**，归入 **4 大垃圾类型**：

| 大类 | 垃圾桶颜色 | 包含子类 |
|------|-----------|---------|
| ♻️ 可回收物 | 蓝色 | 塑料瓶、易拉罐、玻璃杯、衣服、充电宝、书本等 24 类 |
| 🍎 厨余垃圾 | 绿色 | 剩菜、水果皮、蛋壳、鱼骨、茶叶渣等 8 类 |
| ☣️ 有害垃圾 | 红色 | 干电池、药膏、过期药品 3 类 |
| 🗑️ 其他垃圾 | 灰色 | 一次性餐盒、烟蒂、污损塑料袋等 5 类 |

每次识别结果都会附带投放建议，指导用户投入正确的垃圾桶。

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | Django 6.0 |
| 深度学习 | PyTorch + torchvision |
| 模型架构 | MobileNetV3-Small（ImageNet 预训练，迁移学习） |
| 图像处理 | Pillow + OpenCV |
| 数据库 | MySQL |
| 前端 | 原生 Django Templates + 原生 JavaScript |
| 摄像头 | HTML5 Canvas API |
| 设计风格 | 深色玻璃渐变主题（Glass & Gradient） |

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 5.7+
- 推荐：NVIDIA GPU + CUDA（CPU 也可运行）

### 安装

```bash
git clone https://github.com/5x486/Garbage_classification.git
cd Garbage_classification

# 创建虚拟环境
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows

# 安装 PyTorch（CUDA 版）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu132

# 安装其他依赖
pip install django opencv-python pillow tqdm mysqlclient

# 验证 GPU 可用
python 1.py
```

### 配置

```bash
# 设置环境变量
export MYSQL_DATABASE="garbage_classify"
export MYSQL_USER="root"
export MYSQL_PASSWORD="your_password"
export MYSQL_HOST="127.0.0.1"
export DJANGO_SECRET_KEY="your-secret-key"

# 创建数据库
mysql -u root -p -e "CREATE DATABASE garbage_classify CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 初始化
python manage.py migrate
python manage.py runserver     # http://127.0.0.1:8000
```

### 训练自己的模型（可选）

```bash
python train.py --data dataset --arch mobilenet_v3_small --epochs 20 --batch 64 --lr 1e-3
```

支持的架构：`resnet18`、`mobilenet_v3_small`、`mobilenet_v3_large`、`efficientnet_b0`

## 项目结构

```
Garbage_classification/
├── garbage_classification/          # Django 项目配置
├── apps/
│   ├── accounts/                    # 用户认证模块
│   │   ├── forms.py                 # 登录/注册表单
│   │   └── views.py                 # 认证视图
│   └── recognition/                 # 垃圾分类核心模块
│       ├── inference.py             # 模型推理（单例模式）
│       ├── views.py                 # 图片/视频/摄像头视图 + API
│       └── models.py                # 识别记录模型
├── templates/
│   ├── base.html                    # 全局布局 + 玻璃风格 CSS
│   ├── accounts/                    # 登录/注册/首页/密码重置页面
│   └── recognition/                 # 图片/视频/摄像头页面
├── dataset/
│   ├── garbage_classify_rule.json   # 40 类标签映射
│   └── train/                       # ~12,800 张训练图片（40 类）
├── runs/
│   └── .../best.pth                 # 已训练模型权重（~6.4MB）
└── train.py                         # 训练脚本（CLI）
```

## 设计亮点

- **三种识别模式**：图片上传（支持拖拽）、视频上传（可调抽帧间隔）、摄像头实时识别
- **40 类细粒度分类**：覆盖中国官方四分类标准，附带垃圾桶颜色投放建议
- **玻璃渐变 UI**：深色主题，`backdrop-filter` 模糊，绿-青渐变，原生 CSS 无框架依赖
- **模型单例加载**：Django 启动时加载一次，避免每次请求重复载入
- **插件化模型架构**：checkpoint 保存完整元数据（架构/类别名/归一化参数），换模型只需换文件
- **完整训练管线**：数据增强、4 种架构可选、AdamW 优化器、自动保存最佳模型
- **RESTful API**：`/api/predict-image/`、`/api/predict-video/`、`/api/predict-frame/` 供外部集成
