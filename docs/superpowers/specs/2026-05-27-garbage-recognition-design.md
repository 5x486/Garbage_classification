# 垃圾分类识别系统 — 设计文档

**日期:** 2026-05-27  
**状态:** 已确认

---

## 概述

在现有 Django 项目基础上，补全垃圾分类识别的三种前端页面和后端推理逻辑。使用已训练的 MobileNetV3-Small 模型（`runs/cnn_cls_mobilenet_v3_small_20260525_205457/best.pth`）进行 40 类垃圾分类推理。

---

## 架构

Django 单体应用。模型在 `RecognitionConfig.ready()` 中加载一次并常驻内存，所有推理在 Django 视图内同步完成。

```
Django Application
├── accounts/          (已有) 用户认证
├── recognition/
│   ├── inference.py   (新增) 推理引擎单例
│   ├── views.py       (重写) 三个识别视图 + 历史记录
│   └── urls.py        (新增) 识别路由
├── templates/
│   ├── recognition/
│   │   ├── image.html  (新增) 图片识别页
│   │   ├── video.html  (新增) 视频识别页
│   │   └── camera.html (新增) 摄像头实时页
│   ├── accounts/home.html (修改) 入口卡片 + 历史记录
│   └── base.html       (修改) 玻璃渐变风格主题
```

---

## 设计风格

**玻璃渐变（Glass & Gradient）**
- 深色渐变背景（`#0a1628` → `#1a2a1a`）
- 毛玻璃卡片效果（`backdrop-filter: blur`）
- 半透明边框（`rgba(255,255,255,0.08)`）
- 绿色系渐变点缀（`#4ade80` → `#22d3ee`）
- 呼应环保主题，科技感与质感并重

---

## 页面清单

### 1. 首页（修改）
- 路由: `/` → `accounts:home`
- 三个入口卡片：图片识别 / 视频识别 / 实时识别
- 最近识别记录列表（取最近 10 条）

### 2. 图片识别页
- 路由: `/recognition/image/`
- 拖拽或点击上传图片（JPG/PNG/WebP）
- 前端预览缩略图
- 点击"开始识别"→ AJAX 上传 → 后端推理
- 结果区：名称 + 大类 + 置信度 + Top-3 列表 + 处理时间 + 投放建议

### 3. 视频识别页
- 路由: `/recognition/video/`
- 拖拽或点击上传视频（MP4/AVI/MOV）
- 采样间隔选择器（用户自定义每 N 帧采样）
- 点击"开始识别"→ AJAX 上传 → 后端抽帧推理
- 结果区：每帧结果卡片网格 + 汇总统计

### 4. 摄像头实时识别页
- 路由: `/recognition/camera/`
- 浏览器 `getUserMedia` 调用摄像头
- 左侧：实时视频画面
- 右侧：最新识别结果（名称 + 大类 + 置信度 + 投放建议）
- 识别间隔选择器（每 N 秒）
- 底部：识别历史记录列表

---

## 推理引擎 (`recognition/inference.py`)

```python
class ModelInference:
    def __init__(self, checkpoint_path, rule_path):
        ...  # 加载模型、类别映射
    
    def predict(self, image: PIL.Image) -> dict:
        # 返回: {class_id, label, category, confidence, top3, process_time_ms, suggestion}
```

- 输入: PIL Image（RGB）
- 预处理: Resize(224) → ToTensor → Normalize(与训练一致)
- 模型: MobileNetV3-Small, 40 类
- 后处理: 映射类别 ID → 标签（JSON）→ 大类 → 投放建议
- 投放建议映射:
  - 可回收物 → "请投入蓝色可回收物垃圾桶"
  - 厨余垃圾 → "请投入绿色厨余垃圾桶"
  - 有害垃圾 → "请投入红色有害垃圾桶"
  - 其他垃圾 → "请投入灰色其他垃圾桶"

---

## 关键实现细节

- 模型在 `RecognitionConfig.ready()` 中初始化，存为模块级变量
- 图片识别: multipart/form-data 上传，直接 PIL 解码
- 视频识别: 后端用 OpenCV 读取视频，按采样间隔抽帧，逐帧推理
- 摄像头识别: 前端 `<canvas>` 截帧 → base64 → AJAX JSON POST → 后端解码推理
- 每次识别完成后保存 `RecognitionRecord` 到数据库
- 所有页面需登录才能访问（`@login_required`）

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 新增 | `apps/recognition/inference.py` |
| 新增 | `apps/recognition/urls.py` |
| 重写 | `apps/recognition/views.py` |
| 修改 | `apps/recognition/apps.py` |
| 新增 | `templates/recognition/image.html` |
| 新增 | `templates/recognition/video.html` |
| 新增 | `templates/recognition/camera.html` |
| 修改 | `templates/base.html` |
| 修改 | `templates/accounts/home.html` |
| 修改 | `garbage_classification/urls.py` |
