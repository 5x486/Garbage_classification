# 垃圾分类识别系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Django 项目中实现图片上传、视频上传、摄像头实时三种垃圾分类识别方式，使用已训练的 MobileNetV3-Small 模型。

**Architecture:** Django 单体应用。模型在 AppConfig.ready() 中加载并常驻内存。三个独立前端页面（玻璃渐变风格）通过 AJAX 调用后端推理接口，每次识别保存 RecognitionRecord。

**Tech Stack:** Django 6.1, PyTorch, torchvision, OpenCV, 原生 JavaScript (无框架)

---

### Task 1: 推理引擎 (`recognition/inference.py`)

**Files:**
- Create: `apps/recognition/inference.py`

- [ ] **Step 1: 实现 ModelInference 类**

```python
import json
import time
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms


class ModelInference:
    """垃圾分类推理引擎（单例，AppConfig.ready() 时初始化）"""

    def __init__(self, checkpoint_path: str, rule_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 加载检查点
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.imgsz = checkpoint["imgsz"]
        self.mean = checkpoint["mean"]
        self.std = checkpoint["std"]
        class_names = checkpoint["class_names"]

        # 构建模型
        from torchvision import models
        arch = checkpoint["arch"]
        if arch == "mobilenet_v3_small":
            model = models.mobilenet_v3_small(weights=None)
            model.classifier[-1] = torch.nn.Linear(model.classifier[-1].in_features, len(class_names))
        else:
            raise ValueError(f"Unsupported arch: {arch}")

        model.load_state_dict(checkpoint["model_state"])
        model.to(self.device)
        model.eval()
        self.model = model

        # 加载分类规则
        with open(rule_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.id_to_label: dict[int, str] = {}
        self.id_to_category: dict[int, str] = {}
        for k, v in raw.items():
            cat, label = v.split("/", 1)
            self.id_to_label[int(k)] = label
            self.id_to_category[int(k)] = cat

        self.suggestions = {
            "可回收物": "请投入蓝色可回收物垃圾桶",
            "厨余垃圾": "请投入绿色厨余垃圾桶",
            "有害垃圾": "请投入红色有害垃圾桶",
            "其他垃圾": "请投入灰色其他垃圾桶",
        }

        # 预处理管线（与训练时 eval_tf 一致）
        self.transform = transforms.Compose([
            transforms.Resize(int(self.imgsz * 1.14)),
            transforms.CenterCrop(self.imgsz),
            transforms.ToTensor(),
            transforms.Normalize(mean=self.mean, std=self.std),
        ])

    def predict(self, image: Image.Image) -> dict:
        """对 PIL Image 进行推理，返回结构化结果"""
        t0 = time.perf_counter()

        # 确保 RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # 预处理 + batch 维度
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        # 推理
        with torch.inference_mode():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)

        # Top-1
        top1_prob, top1_idx = probs.max(dim=1)
        class_id = top1_idx.item()
        confidence = top1_prob.item()

        # Top-3
        top3_probs, top3_indices = probs.topk(min(3, probs.size(1)), dim=1)
        top3 = [
            {
                "label": self.id_to_label.get(i.item(), str(i.item())),
                "category": self.id_to_category.get(i.item(), "未知"),
                "confidence": round(p.item(), 4),
            }
            for i, p in zip(top3_indices[0], top3_probs[0])
        ]

        elapsed = round((time.perf_counter() - t0) * 1000, 1)

        return {
            "class_id": class_id,
            "label": self.id_to_label.get(class_id, str(class_id)),
            "category": self.id_to_category.get(class_id, "未知"),
            "confidence": round(confidence, 4),
            "top3": top3,
            "process_time_ms": elapsed,
            "suggestion": self.suggestions.get(
                self.id_to_category.get(class_id, ""), "请按规定分类投放"
            ),
        }
```

- [ ] **Step 2: 验证推理引擎可导入**

Run: `python -c "import sys; sys.path.insert(0, '.'); from apps.recognition.inference import ModelInference; print('import OK')"`
Expected: `import OK`

---

### Task 2: AppConfig 启动加载模型

**Files:**
- Modify: `apps/recognition/apps.py`

- [ ] **Step 1: 在 ready() 中初始化推理引擎**

```python
from django.apps import AppConfig


class RecognitionConfig(AppConfig):
    name = 'apps.recognition'

    def ready(self):
        from pathlib import Path
        from .inference import ModelInference

        checkpoint_path = Path(__file__).resolve().parent.parent.parent / "runs" / "cnn_cls_mobilenet_v3_small_20260525_205457" / "best.pth"
        rule_path = Path(__file__).resolve().parent.parent.parent / "dataset" / "garbage_classify_rule.json"

        if not checkpoint_path.exists():
            print(f"[WARN] 模型文件不存在: {checkpoint_path}")
            return

        self.inference_engine = ModelInference(str(checkpoint_path), str(rule_path))
        print(f"[INFO] 模型加载完成，设备: {self.inference_engine.device}")
```

---

### Task 3: URL 路由配置

**Files:**
- Create: `apps/recognition/urls.py`
- Modify: `garbage_classification/urls.py`

- [ ] **Step 1: 创建 recognition/urls.py**

```python
from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('image/', views.image_upload_view, name='image'),
    path('video/', views.video_upload_view, name='video'),
    path('camera/', views.camera_view, name='camera'),
    path('api/predict-image/', views.api_predict_image, name='api_predict_image'),
    path('api/predict-video/', views.api_predict_video, name='api_predict_video'),
    path('api/predict-frame/', views.api_predict_frame, name='api_predict_frame'),
]
```

- [ ] **Step 2: 修改项目 urls.py**

```python
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def root_redirect(request):
    return redirect('accounts:home')


urlpatterns = [
    path('', root_redirect, name='root'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('recognition/', include('apps.recognition.urls')),
]
```

---

### Task 4: 识别视图 (`recognition/views.py`)

**Files:**
- Rewrite: `apps/recognition/views.py`

- [ ] **Step 1: 实现页面视图和 API 端点**

```python
import io
import json
import base64

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from PIL import Image

from .models import RecognitionRecord, RecordType, RecordStatus


def get_inference_engine():
    """获取已加载的推理引擎实例"""
    cfg = apps.get_app_config("recognition")
    return getattr(cfg, "inference_engine", None)


def save_record(user, record_type, result: dict, image=None):
    """保存识别记录到数据库"""
    return RecognitionRecord.objects.create(
        user=user,
        record_type=record_type,
        status=RecordStatus.SUCCESS,
        snapshot=image,
        result_class=str(result.get("class_id", "")),
        result_label=result.get("label", ""),
        result_category=result.get("category", ""),
        confidence=result.get("confidence"),
        topk=result.get("top3"),
        extra={"process_time_ms": result.get("process_time_ms")},
    )


@login_required
def image_upload_view(request):
    """图片识别页面"""
    return render(request, "recognition/image.html")


@login_required
def video_upload_view(request):
    """视频识别页面"""
    return render(request, "recognition/video.html")


@login_required
def camera_view(request):
    """摄像头实时识别页面"""
    return render(request, "recognition/camera.html")


@login_required
def api_predict_image(request):
    """图片识别 API"""
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    engine = get_inference_engine()
    if engine is None:
        return JsonResponse({"error": "模型未加载"}, status=503)

    file = request.FILES.get("image")
    if not file:
        return JsonResponse({"error": "未上传图片"}, status=400)

    try:
        image = Image.open(file).convert("RGB")
        result = engine.predict(image)

        # 保存记录（附带快照）
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile
        snapshot = SimpleUploadedFile("snapshot.jpg", buf.read(), content_type="image/jpeg")
        save_record(request.user, RecordType.UPLOAD, result, image=snapshot)

        return JsonResponse({"success": True, "result": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def api_predict_video(request):
    """视频识别 API — 抽帧推理"""
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    engine = get_inference_engine()
    if engine is None:
        return JsonResponse({"error": "模型未加载"}, status=503)

    file = request.FILES.get("video")
    if not file:
        return JsonResponse({"error": "未上传视频"}, status=400)

    try:
        interval = int(request.POST.get("interval", 30))
    except ValueError:
        interval = 30

    import tempfile
    import os
    import cv2

    # 保存临时文件
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    for chunk in file.chunks():
        tmp.write(chunk)
    tmp.close()

    try:
        cap = cv2.VideoCapture(tmp.name)
        frame_count = 0
        results = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % interval == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                result = engine.predict(pil_image)
                results.append({
                    "frame": frame_count,
                    "label": result["label"],
                    "category": result["category"],
                    "confidence": result["confidence"],
                })
            frame_count += 1

        cap.release()

        # 汇总
        from collections import Counter
        categories = Counter(r["category"] for r in results)
        labels = Counter(r["label"] for r in results)

        summary = {
            "total_frames": frame_count,
            "sampled_frames": len(results),
            "interval": interval,
            "top_categories": categories.most_common(),
            "top_labels": labels.most_common(3),
        }

        # 保存记录
        if results:
            best = max(results, key=lambda r: r["confidence"])
            best_result = {
                "class_id": -1,
                "label": best["label"],
                "category": best["category"],
                "confidence": best["confidence"],
                "top3": [],
                "process_time_ms": 0,
            }
            save_record(request.user, RecordType.UPLOAD, best_result)

        return JsonResponse({"success": True, "summary": summary, "frames": results})
    finally:
        os.unlink(tmp.name)


@login_required
def api_predict_frame(request):
    """摄像头帧识别 API — 接收 base64 帧"""
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    engine = get_inference_engine()
    if engine is None:
        return JsonResponse({"error": "模型未加载"}, status=503)

    try:
        body = json.loads(request.body)
        b64_data = body.get("frame", "")
        if not b64_data:
            return JsonResponse({"error": "未提供帧数据"}, status=400)

        # 解码 base64 → PIL Image
        # 格式: "data:image/jpeg;base64,xxxxx"
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_data)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        result = engine.predict(image)
        save_record(request.user, RecordType.UPLOAD, result)
        return JsonResponse({"success": True, "result": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def recent_records(request):
    """获取最近识别记录"""
    records = RecognitionRecord.objects.filter(user=request.user).order_by("-created_at")[:10]
    data = [
        {
            "id": r.id,
            "label": r.result_label,
            "category": r.result_category,
            "confidence": r.confidence,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for r in records
    ]
    return JsonResponse({"records": data})
```

---

### Task 5: `settings.py` 补充 MEDIA 配置

**Files:**
- Modify: `garbage_classification/settings.py`

- [ ] **Step 1: 在文件末尾添加 MEDIA 配置**

在 `settings.py` 末尾追加：

```python
# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

---

### Task 6: 基础模板 — 玻璃渐变风格

**Files:**
- Rewrite: `templates/base.html`

- [ ] **Step 1: 重写 base.html 为玻璃渐变主题**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}垃圾分类{% endblock %}</title>
    <style>
        :root {
            --glass-bg: rgba(255, 255, 255, 0.04);
            --glass-border: rgba(255, 255, 255, 0.08);
            --glass-hover: rgba(255, 255, 255, 0.06);
            --green: #4ade80;
            --green-cyan: #22d3ee;
            --text: rgba(255, 255, 255, 0.9);
            --text-secondary: rgba(255, 255, 255, 0.5);
            --text-muted: rgba(255, 255, 255, 0.3);
            --danger: #f87171;
            --radius: 16px;
            --radius-sm: 10px;
        }

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: "Microsoft YaHei", "PingFang SC", system-ui, -apple-system, sans-serif;
            font-size: 15px;
            line-height: 1.6;
            color: var(--text);
            background: linear-gradient(135deg, #0a1628 0%, #0f1f0f 50%, #0a1628 100%);
            min-height: 100vh;
        }

        /* 导航 */
        .navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 32px;
            height: 60px;
            background: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid var(--glass-border);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
        }
        .navbar .brand {
            font-size: 18px;
            font-weight: 700;
            background: linear-gradient(90deg, var(--green), var(--green-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .navbar .nav-links {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .navbar .nav-links .user-name {
            font-size: 13px;
            color: var(--text-secondary);
        }
        .navbar .nav-links a,
        .navbar .nav-links button {
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 13px;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            padding: 7px 16px;
            cursor: pointer;
            transition: all 0.25s;
        }
        .navbar .nav-links a:hover,
        .navbar .nav-links button:hover {
            background: var(--glass-hover);
            color: var(--text);
            border-color: rgba(255, 255, 255, 0.15);
        }

        /* 主容器 */
        .main {
            max-width: 960px;
            margin: 0 auto;
            padding: 32px 24px 64px;
        }

        /* 玻璃卡片 */
        .glass-card {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 32px;
        }

        /* 按钮 */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            height: 44px;
            padding: 0 24px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all 0.25s;
            font-family: inherit;
        }
        .btn-primary {
            background: linear-gradient(135deg, #4ade80, #22d3ee);
            color: #0a1628;
        }
        .btn-primary:hover {
            opacity: 0.9;
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(74, 222, 128, 0.3);
        }
        .btn-primary:disabled {
            opacity: 0.4;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .btn-ghost {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            color: var(--text-secondary);
        }
        .btn-ghost:hover {
            background: var(--glass-hover);
            color: var(--text);
        }

        /* 上传区域 */
        .upload-zone {
            border: 2px dashed rgba(255, 255, 255, 0.12);
            border-radius: var(--radius);
            padding: 48px 24px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-zone:hover, .upload-zone.drag-over {
            border-color: var(--green);
            background: rgba(74, 222, 128, 0.04);
        }
        .upload-zone .icon {
            font-size: 40px;
            margin-bottom: 12px;
        }
        .upload-zone .text {
            color: var(--text-secondary);
            font-size: 14px;
        }
        .upload-zone .hint {
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 6px;
        }
        .upload-zone input[type="file"] { display: none; }

        /* 结果区域 */
        .result-section {
            margin-top: 24px;
        }
        .result-main {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 20px;
            background: rgba(74, 222, 128, 0.06);
            border: 1px solid rgba(74, 222, 128, 0.15);
            border-radius: var(--radius-sm);
            margin-bottom: 16px;
        }
        .result-main .label-name {
            font-size: 22px;
            font-weight: 700;
        }
        .result-main .category-tag {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            background: rgba(74, 222, 128, 0.15);
            color: var(--green);
        }
        .result-main .confidence {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(90deg, var(--green), var(--green-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* Top-3 列表 */
        .top3-list { list-style: none; }
        .top3-list li {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 0;
            border-bottom: 1px solid var(--glass-border);
            font-size: 13px;
        }
        .top3-list li:last-child { border-bottom: none; }
        .top3-list .rank { width: 24px; color: var(--text-muted); }
        .top3-list .bar-wrap {
            flex: 1;
            height: 6px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 3px;
            overflow: hidden;
        }
        .top3-list .bar-fill {
            height: 100%;
            border-radius: 3px;
            background: linear-gradient(90deg, var(--green), var(--green-cyan));
            transition: width 0.5s ease;
        }
        .top3-list .pct {
            width: 48px;
            text-align: right;
            font-weight: 600;
            color: var(--text-secondary);
        }

        /* 建议条 */
        .suggestion {
            margin-top: 16px;
            padding: 14px 18px;
            border-radius: var(--radius-sm);
            background: rgba(74, 222, 128, 0.08);
            border-left: 3px solid var(--green);
            font-size: 14px;
            color: var(--text-secondary);
        }

        /* 帧网格 */
        .frames-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 14px;
            margin-top: 16px;
        }
        .frame-card {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-sm);
            padding: 16px;
            text-align: center;
        }
        .frame-card .frame-num {
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        .frame-card .frame-label {
            font-weight: 600;
            font-size: 14px;
        }
        .frame-card .frame-cat {
            font-size: 11px;
            color: var(--green);
            margin-top: 2px;
        }
        .frame-card .frame-conf {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* 摄像头布局 */
        .camera-layout {
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 24px;
        }
        @media (max-width: 768px) {
            .camera-layout { grid-template-columns: 1fr; }
            .frames-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
        }
        .camera-view {
            width: 100%;
            border-radius: var(--radius);
            border: 1px solid var(--glass-border);
            background: #000;
        }
        .result-panel {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 24px;
        }
        .history-list {
            list-style: none;
            max-height: 300px;
            overflow-y: auto;
        }
        .history-list li {
            padding: 10px 0;
            border-bottom: 1px solid var(--glass-border);
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .history-list li:last-child { border-bottom: none; }

        /* 控件行 */
        .controls-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 20px 0;
        }
        .select-custom {
            height: 44px;
            padding: 0 14px;
            border-radius: var(--radius-sm);
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            color: var(--text);
            font-size: 14px;
            font-family: inherit;
            cursor: pointer;
            outline: none;
        }
        .select-custom:focus {
            border-color: var(--green);
        }
        .select-custom option {
            background: #1a2a1a;
            color: var(--text);
        }

        /* 入口卡片 */
        .entry-cards {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 32px;
        }
        @media (max-width: 640px) {
            .entry-cards { grid-template-columns: 1fr; }
        }
        .entry-card {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius);
            padding: 32px 20px;
            text-align: center;
            text-decoration: none;
            color: var(--text);
            transition: all 0.3s;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
        }
        .entry-card:hover {
            background: var(--glass-hover);
            border-color: rgba(255, 255, 255, 0.15);
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .entry-card .entry-icon { font-size: 36px; margin-bottom: 12px; }
        .entry-card .entry-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .entry-card .entry-desc {
            font-size: 12px;
            color: var(--text-muted);
        }

        /* 记录列表 */
        .record-list { list-style: none; }
        .record-list li {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 0;
            border-bottom: 1px solid var(--glass-border);
            font-size: 14px;
        }
        .record-list li:last-child { border-bottom: none; }
        .record-list .rec-time {
            font-size: 12px;
            color: var(--text-muted);
            min-width: 100px;
        }
        .record-list .rec-cat {
            font-size: 11px;
            padding: 2px 10px;
            border-radius: 20px;
            background: rgba(74, 222, 128, 0.1);
            color: var(--green);
            margin-left: auto;
        }

        /* 隐藏 */
        .hidden { display: none !important; }

        /* 预览图 */
        .preview-img {
            max-width: 100%;
            max-height: 300px;
            border-radius: var(--radius-sm);
            margin: 16px auto;
            display: block;
        }

        /* 加载动画 */
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-top-color: var(--green);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* 消息提示 */
        .toast {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            border-radius: var(--radius-sm);
            font-size: 14px;
            z-index: 1000;
            animation: fadeIn 0.3s ease;
        }
        .toast.error { background: rgba(248, 113, 113, 0.2); border: 1px solid var(--danger); color: var(--danger); }
        .toast.success { background: rgba(74, 222, 128, 0.15); border: 1px solid var(--green); color: var(--green); }
        @keyframes fadeIn { from { opacity: 0; transform: translateX(-50%) translateY(-8px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% if user.is_authenticated %}
    <nav class="navbar">
        <a href="{% url 'accounts:home' %}" style="text-decoration:none;"><span class="brand">垃圾分类助手</span></a>
        <div class="nav-links">
            <span class="user-name">{{ user.username }}</span>
            <a href="{% url 'accounts:home' %}">首页</a>
            <form method="post" action="{% url 'accounts:logout' %}" style="display:inline">
                {% csrf_token %}
                <button type="submit">退出</button>
            </form>
        </div>
    </nav>
    {% endif %}

    <div class="main">
        {% block content %}{% endblock %}
    </div>

    <script>
        // 全局 AJAX 封装
        async function apiPost(url, body) {
            const resp = await fetch(url, {
                method: 'POST',
                headers: body instanceof FormData ? {} : {'Content-Type': 'application/json', 'X-CSRFToken': getCSRF()},
                body: body instanceof FormData ? body : JSON.stringify(body),
            });
            return resp.json();
        }
        function getCSRF() {
            const m = document.cookie.match(/csrftoken=([^;]+)/);
            return m ? m[1] : '';
        }
        function showToast(msg, type) {
            const t = document.createElement('div');
            t.className = 'toast ' + type;
            t.textContent = msg;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 3000);
        }
    </script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

---

### Task 7: 首页 — 入口卡片 + 最近记录

**Files:**
- Modify: `templates/accounts/home.html`

- [ ] **Step 1: 重写 home.html**

```html
{% extends 'base.html' %}
{% block title %}首页 - 垃圾分类{% endblock %}

{% block content %}
<h2 style="font-size:28px;font-weight:700;margin-bottom:8px;">
    欢迎回来，<span style="background:linear-gradient(90deg,#4ade80,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">{{ user.username }}</span>
</h2>
<p style="color:rgba(255,255,255,0.4);margin-bottom:32px;font-size:14px;">选择一种方式开始垃圾分类识别</p>

<div class="entry-cards">
    <a href="{% url 'recognition:image' %}" class="entry-card">
        <div class="entry-icon">📷</div>
        <div class="entry-title">图片识别</div>
        <div class="entry-desc">上传图片 · 即刻识别</div>
    </a>
    <a href="{% url 'recognition:video' %}" class="entry-card">
        <div class="entry-icon">🎬</div>
        <div class="entry-title">视频识别</div>
        <div class="entry-desc">上传视频 · 抽帧分析</div>
    </a>
    <a href="{% url 'recognition:camera' %}" class="entry-card">
        <div class="entry-icon">📹</div>
        <div class="entry-title">实时识别</div>
        <div class="entry-desc">打开摄像头 · 实时检测</div>
    </a>
</div>

<div class="glass-card">
    <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">最近识别记录</h3>
    <ul class="record-list" id="recent-records">
        <li style="color:var(--text-muted);">加载中...</li>
    </ul>
</div>
{% endblock %}

{% block extra_js %}
<script>
(async function() {
    try {
        const resp = await fetch('{% url "recognition:api_recent_records" %}');
        const data = await resp.json();
        const el = document.getElementById('recent-records');
        if (!data.records || data.records.length === 0) {
            el.innerHTML = '<li style="color:var(--text-muted);">暂无识别记录</li>';
            return;
        }
        el.innerHTML = data.records.map(r => `
            <li>
                <span class="rec-time">${r.created_at}</span>
                <span>${r.label}</span>
                <span class="rec-cat">${r.category}</span>
                <span style="font-weight:600;font-size:13px;">${(r.confidence * 100).toFixed(1)}%</span>
            </li>
        `).join('');
    } catch(e) {
        document.getElementById('recent-records').innerHTML = '<li style="color:var(--text-muted);">加载失败</li>';
    }
})();
</script>
{% endblock %}
```

---

### Task 8: 图片识别页面

**Files:**
- Create: `templates/recognition/image.html`

- [ ] **Step 1: 创建 image.html**

```html
{% extends 'base.html' %}
{% block title %}图片识别 - 垃圾分类{% endblock %}

{% block content %}
<div style="max-width:640px;margin:0 auto;">
    <a href="{% url 'accounts:home' %}" style="color:var(--text-muted);text-decoration:none;font-size:13px;">← 返回首页</a>
    <h2 style="font-size:24px;font-weight:700;margin-top:12px;margin-bottom:4px;">图片识别</h2>
    <p style="color:var(--text-muted);font-size:13px;margin-bottom:24px;">上传垃圾图片，即刻识别分类</p>

    <div class="glass-card">
        <div class="upload-zone" id="upload-zone">
            <div class="icon">📷</div>
            <div class="text">点击或拖拽上传图片</div>
            <div class="hint">支持 JPG / PNG / WebP</div>
            <input type="file" id="file-input" accept="image/*">
        </div>
        <img id="preview" class="preview-img hidden" alt="预览">

        <div style="text-align:center;margin-top:16px;">
            <button class="btn btn-primary" id="btn-recognize" disabled>开始识别</button>
        </div>
    </div>

    <div id="result-area" class="glass-card result-section hidden">
        <!-- 动态填充 -->
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
const zone = document.getElementById('upload-zone');
const input = document.getElementById('file-input');
const preview = document.getElementById('preview');
const btn = document.getElementById('btn-recognize');
const resultArea = document.getElementById('result-area');
let selectedFile = null;

zone.addEventListener('click', () => input.click());
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
input.addEventListener('change', () => { if (input.files.length) handleFile(input.files[0]); });

function handleFile(file) {
    selectedFile = file;
    const url = URL.createObjectURL(file);
    preview.src = url;
    preview.classList.remove('hidden');
    btn.disabled = false;
    resultArea.classList.add('hidden');
}

btn.addEventListener('click', async () => {
    if (!selectedFile) return;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 识别中...';

    const fd = new FormData();
    fd.append('image', selectedFile);

    try {
        const data = await apiPost('{% url "recognition:api_predict_image" %}', fd);
        if (data.error) { showToast(data.error, 'error'); btn.disabled = false; btn.textContent = '开始识别'; return; }
        renderResult(data.result);
    } catch(e) {
        showToast('网络错误', 'error');
    }
    btn.disabled = false;
    btn.textContent = '开始识别';
});

function renderResult(r) {
    resultArea.classList.remove('hidden');
    resultArea.innerHTML = `
        <div class="result-main">
            <div style="flex:1;">
                <div class="label-name">${r.label}</div>
                <span class="category-tag">${r.category}</span>
            </div>
            <div class="confidence">${(r.confidence * 100).toFixed(1)}%</div>
        </div>
        <h4 style="font-size:13px;color:var(--text-muted);margin-bottom:8px;">Top-3 可能类别</h4>
        <ul class="top3-list">
            ${r.top3.map((t, i) => `
                <li>
                    <span class="rank">#${i + 1}</span>
                    <span style="width:70px;font-size:13px;">${t.label}</span>
                    <div class="bar-wrap"><div class="bar-fill" style="width:${(t.confidence * 100).toFixed(0)}%;"></div></div>
                    <span class="pct">${(t.confidence * 100).toFixed(1)}%</span>
                </li>
            `).join('')}
        </ul>
        <div class="suggestion">💡 ${r.suggestion}</div>
        <p style="font-size:12px;color:var(--text-muted);margin-top:12px;">处理时间：${r.process_time_ms}ms</p>
    `;
}
</script>
{% endblock %}
```

---

### Task 9: 视频识别页面

**Files:**
- Create: `templates/recognition/video.html`

- [ ] **Step 1: 创建 video.html**

```html
{% extends 'base.html' %}
{% block title %}视频识别 - 垃圾分类{% endblock %}

{% block content %}
<div style="max-width:800px;margin:0 auto;">
    <a href="{% url 'accounts:home' %}" style="color:var(--text-muted);text-decoration:none;font-size:13px;">← 返回首页</a>
    <h2 style="font-size:24px;font-weight:700;margin-top:12px;margin-bottom:4px;">视频识别</h2>
    <p style="color:var(--text-muted);font-size:13px;margin-bottom:24px;">上传视频，按间隔抽帧进行垃圾分类识别</p>

    <div class="glass-card">
        <div class="upload-zone" id="upload-zone">
            <div class="icon">🎬</div>
            <div class="text">点击或拖拽上传视频</div>
            <div class="hint">支持 MP4 / AVI / MOV</div>
            <input type="file" id="file-input" accept="video/*">
        </div>
        <div id="video-name" style="text-align:center;margin-top:12px;color:var(--green);font-size:14px;" class="hidden"></div>

        <div class="controls-row" style="justify-content:center;">
            <label style="font-size:13px;color:var(--text-secondary);">采样间隔：</label>
            <select class="select-custom" id="interval-select">
                <option value="10">每 10 帧</option>
                <option value="30" selected>每 30 帧</option>
                <option value="60">每 60 帧</option>
                <option value="90">每 90 帧</option>
                <option value="120">每 120 帧</option>
            </select>
            <button class="btn btn-primary" id="btn-recognize" disabled>开始识别</button>
        </div>
    </div>

    <div id="result-area" class="hidden">
        <div class="glass-card" style="margin-top:24px;" id="summary-card"></div>
        <h3 style="font-size:16px;font-weight:600;margin-top:24px;margin-bottom:12px;">帧识别结果</h3>
        <div class="frames-grid" id="frames-grid"></div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
const zone = document.getElementById('upload-zone');
const input = document.getElementById('file-input');
const btn = document.getElementById('btn-recognize');
const videoName = document.getElementById('video-name');
const resultArea = document.getElementById('result-area');
let selectedFile = null;

zone.addEventListener('click', () => input.click());
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
input.addEventListener('change', () => { if (input.files.length) handleFile(input.files[0]); });

function handleFile(file) {
    selectedFile = file;
    videoName.textContent = '已选择：' + file.name;
    videoName.classList.remove('hidden');
    btn.disabled = false;
    resultArea.classList.add('hidden');
}

btn.addEventListener('click', async () => {
    if (!selectedFile) return;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 识别中...';

    const fd = new FormData();
    fd.append('video', selectedFile);
    fd.append('interval', document.getElementById('interval-select').value);

    try {
        const data = await apiPost('{% url "recognition:api_predict_video" %}', fd);
        if (data.error) { showToast(data.error, 'error'); btn.disabled = false; btn.textContent = '开始识别'; return; }
        renderResult(data);
    } catch(e) {
        showToast('网络错误', 'error');
    }
    btn.disabled = false;
    btn.textContent = '开始识别';
});

function renderResult(data) {
    resultArea.classList.remove('hidden');

    // 汇总
    const s = data.summary;
    document.getElementById('summary-card').innerHTML = `
        <h3 style="font-size:16px;font-weight:600;margin-bottom:12px;">识别汇总</h3>
        <p style="font-size:13px;color:var(--text-secondary);">总帧数：${s.total_frames}，采样 ${s.sampled_frames} 帧（每 ${s.interval} 帧）</p>
        <p style="font-size:13px;color:var(--text-secondary);margin-top:4px;">
            主要类别：
            ${s.top_categories.map(([cat, n]) => `<span style="color:var(--green);">${cat}</span> (${n}次)`).join(' · ')}
        </p>
    `;

    // 帧结果
    document.getElementById('frames-grid').innerHTML = data.frames.map(f => `
        <div class="frame-card">
            <div class="frame-num">帧 #${f.frame}</div>
            <div class="frame-label">${f.label}</div>
            <div class="frame-cat">${f.category}</div>
            <div class="frame-conf">${(f.confidence * 100).toFixed(1)}%</div>
        </div>
    `).join('');
}
</script>
{% endblock %}
```

---

### Task 10: 摄像头实时识别页面

**Files:**
- Create: `templates/recognition/camera.html`

- [ ] **Step 1: 创建 camera.html**

```html
{% extends 'base.html' %}
{% block title %}实时识别 - 垃圾分类{% endblock %}

{% block content %}
<a href="{% url 'accounts:home' %}" style="color:var(--text-muted);text-decoration:none;font-size:13px;">← 返回首页</a>
<h2 style="font-size:24px;font-weight:700;margin-top:12px;margin-bottom:4px;">实时识别</h2>
<p style="color:var(--text-muted);font-size:13px;margin-bottom:24px;">打开摄像头，实时检测镜头前的垃圾物品</p>

<div class="camera-layout">
    <div class="glass-card" style="padding:0;overflow:hidden;">
        <video id="video" class="camera-view" autoplay playsinline muted></video>
        <canvas id="canvas" class="hidden"></canvas>
    </div>

    <div class="result-panel" id="result-panel">
        <div style="text-align:center;padding:20px 0;color:var(--text-muted);" id="result-placeholder">
            等待摄像头开启...
        </div>
        <div id="result-content" class="hidden">
            <div class="label-name" id="res-label" style="font-size:28px;"></div>
            <span class="category-tag" id="res-cat" style="margin-top:8px;"></span>
            <div class="confidence" id="res-conf" style="font-size:36px;margin-top:12px;"></div>
            <div class="suggestion" id="res-sugg" style="margin-top:16px;"></div>
            <p style="font-size:12px;color:var(--text-muted);margin-top:8px;" id="res-time"></p>
        </div>
        <div style="margin-top:20px;">
            <label style="font-size:12px;color:var(--text-muted);">识别间隔：</label>
            <select class="select-custom" id="interval-select" style="width:100%;margin-top:4px;">
                <option value="1">每 1 秒</option>
                <option value="2" selected>每 2 秒</option>
                <option value="3">每 3 秒</option>
                <option value="5">每 5 秒</option>
            </select>
        </div>
        <button class="btn btn-primary" id="btn-toggle" style="width:100%;margin-top:16px;">开启摄像头</button>

        <h4 style="font-size:13px;font-weight:600;margin-top:24px;margin-bottom:8px;">识别历史</h4>
        <ul class="history-list" id="history-list">
            <li style="color:var(--text-muted);">暂无记录</li>
        </ul>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const btn = document.getElementById('btn-toggle');
const intervalSelect = document.getElementById('interval-select');
let stream = null;
let timer = null;
let running = false;

btn.addEventListener('click', async () => {
    if (running) {
        stopCamera();
    } else {
        await startCamera();
    }
});

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        video.srcObject = stream;
        btn.textContent = '关闭摄像头';
        btn.className = 'btn btn-ghost';
        running = true;
        document.getElementById('result-placeholder').classList.add('hidden');
        document.getElementById('result-content').classList.remove('hidden');
        startCapturing();
    } catch(e) {
        showToast('无法访问摄像头：' + e.message, 'error');
    }
}

function stopCamera() {
    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    if (timer) { clearInterval(timer); timer = null; }
    running = false;
    btn.textContent = '开启摄像头';
    btn.className = 'btn btn-primary';
    document.getElementById('result-placeholder').classList.remove('hidden');
    document.getElementById('result-content').classList.add('hidden');
}

function startCapturing() {
    const interval = parseInt(intervalSelect.value) * 1000;
    if (timer) clearInterval(timer);
    timer = setInterval(captureFrame, interval);
}

intervalSelect.addEventListener('change', () => {
    if (running) startCapturing();
});

async function captureFrame() {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const b64 = canvas.toDataURL('image/jpeg', 0.8);

    try {
        const data = await apiPost('{% url "recognition:api_predict_frame" %}', { frame: b64 });
        if (data.error) return;
        updateResult(data.result);
    } catch(e) { /* 静默失败 */ }
}

function updateResult(r) {
    document.getElementById('res-label').textContent = r.label;
    document.getElementById('res-cat').textContent = r.category;
    document.getElementById('res-conf').textContent = (r.confidence * 100).toFixed(1) + '%';
    document.getElementById('res-sugg').textContent = '💡 ' + r.suggestion;
    document.getElementById('res-time').textContent = '处理时间：' + r.process_time_ms + 'ms';

    const hist = document.getElementById('history-list');
    const now = new Date().toLocaleTimeString();
    if (hist.querySelector('li:first-child')?.textContent?.includes('暂无记录')) {
        hist.innerHTML = '';
    }
    hist.insertAdjacentHTML('afterbegin', `
        <li>
            <span>${now} · ${r.label}</span>
            <span style="color:var(--green);">${(r.confidence * 100).toFixed(1)}%</span>
        </li>
    `);
    // 保留最近 20 条
    while (hist.children.length > 20) hist.lastElementChild.remove();
}
</script>
{% endblock %}
```

---

### Task 11: 添加 `/recognition/api/recent-records/` 路由

**Files:**
- Modify: `apps/recognition/urls.py`

- [ ] **Step 1: 补充路由**

在 `urlpatterns` 中追加一行：

```python
    path('api/recent-records/', views.recent_records, name='api_recent_records'),
```

---

### Task 12: 运行与验证

- [ ] **Step 1: 启动 Django 并验证模型加载**

Run: `python manage.py runserver`
Expected: 控制台输出 `[INFO] 模型加载完成，设备: cuda`（或 cpu）

- [ ] **Step 2: 验证三个页面可访问**

- 打开 `http://127.0.0.1:8000/` → 首页，三个入口卡片
- 打开 `http://127.0.0.1:8000/recognition/image/` → 图片识别页
- 打开 `http://127.0.0.1:8000/recognition/video/` → 视频识别页
- 打开 `http://127.0.0.1:8000/recognition/camera/` → 摄像头页

- [ ] **Step 3: 测试图片识别 API**

Run: `curl -X POST -F "image=@dataset/test/0/sample.jpg" http://127.0.0.1:8000/recognition/api/predict-image/ -H "X-CSRFToken: xxx" -b "sessionid=xxx"`
Expected: JSON 结果含 label、category、confidence 等字段

---

### Task 13: 依赖安装确认

- [ ] **Step 1: 确保依赖就绪**

Run: `pip list | grep -E "torch|torchvision|opencv|pillow|django"`
Expected: 以上包均已安装。若缺少 opencv-python：
Run: `pip install opencv-python`
