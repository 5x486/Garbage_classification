import json
import time

import torch
from PIL import Image
from torchvision import models, transforms


class ModelInference:
    """垃圾分类推理引擎（单例，AppConfig.ready() 时初始化）"""

    def __init__(self, checkpoint_path: str, rule_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 加载检查点
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)

        # 校验检查点必需键
        required_keys = {"arch", "imgsz", "mean", "std", "class_names", "model_state"}
        missing = required_keys - checkpoint.keys()
        if missing:
            raise RuntimeError(
                f"Checkpoint missing required keys: {', '.join(sorted(missing))}"
            )

        self.imgsz = checkpoint["imgsz"]
        self.mean = checkpoint["mean"]
        self.std = checkpoint["std"]
        class_names = checkpoint["class_names"]

        # 构建模型
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
