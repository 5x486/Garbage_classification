import io
import json
import base64
import logging
import os
import tempfile
from collections import Counter

import cv2
from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from PIL import Image

logger = logging.getLogger(__name__)

from .models import RecognitionRecord, RecordType, RecordStatus


def get_inference_engine():
    cfg = apps.get_app_config("recognition")
    engine = getattr(cfg, "inference_engine", None)
    if engine is None:
        logger.debug("模型未加载")
    return engine


def save_record(user, record_type, result: dict, image=None):
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
    return render(request, "recognition/image.html")


@login_required
def video_upload_view(request):
    return render(request, "recognition/video.html")


@login_required
def camera_view(request):
    return render(request, "recognition/camera.html")


@login_required
def api_predict_image(request):
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    engine = get_inference_engine()
    if engine is None:
        return JsonResponse({"error": "模型未加载"}, status=503)

    file = request.FILES.get("image")
    if not file:
        return JsonResponse({"error": "未上传图片"}, status=400)

    if file.size > 10 * 1024 * 1024:
        return JsonResponse({"error": "图片大小不能超过 10MB"}, status=400)

    try:
        image = Image.open(file).convert("RGB")
        result = engine.predict(image)

        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        snapshot = SimpleUploadedFile("snapshot.jpg", buf.read(), content_type="image/jpeg")
        save_record(request.user, RecordType.UPLOAD, result, image=snapshot)

        return JsonResponse({"success": True, "result": result})
    except Exception:
        logger.exception("图片识别失败")
        return JsonResponse({"error": "处理请求时发生错误"}, status=500)


@login_required
def api_predict_video(request):
    if request.method != "POST":
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    engine = get_inference_engine()
    if engine is None:
        return JsonResponse({"error": "模型未加载"}, status=503)

    file = request.FILES.get("video")
    if not file:
        return JsonResponse({"error": "未上传视频"}, status=400)

    if file.size > 100 * 1024 * 1024:
        return JsonResponse({"error": "视频大小不能超过 100MB"}, status=400)

    try:
        interval = int(request.POST.get("interval", 30))
    except ValueError:
        interval = 30

    if interval < 1:
        interval = 30
    if interval > 300:
        interval = 300

    tmp = None
    cap = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        for chunk in file.chunks():
            tmp.write(chunk)
        tmp.close()

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
        cap = None

        categories = Counter(r["category"] for r in results)
        labels = Counter(r["label"] for r in results)

        summary = {
            "total_frames": frame_count,
            "sampled_frames": len(results),
            "interval": interval,
            "top_categories": categories.most_common(),
            "top_labels": labels.most_common(3),
        }

        if not results:
            return JsonResponse({
                "success": True,
                "summary": summary,
                "frames": [],
                "message": "未能从视频中采样到有效帧",
            })

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
    except Exception:
        logger.exception("视频识别失败")
        return JsonResponse({"error": "处理请求时发生错误"}, status=500)
    finally:
        if cap is not None:
            cap.release()
        if tmp is not None:
            os.unlink(tmp.name)


@login_required
def api_predict_frame(request):
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

        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_data)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        result = engine.predict(image)
        save_record(request.user, RecordType.UPLOAD, result)
        return JsonResponse({"success": True, "result": result})
    except Exception:
        logger.exception("摄像头帧识别失败")
        return JsonResponse({"error": "处理请求时发生错误"}, status=500)


@login_required
def recent_records(request):
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
