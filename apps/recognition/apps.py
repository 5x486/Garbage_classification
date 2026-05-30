import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class RecognitionConfig(AppConfig):
    name = 'apps.recognition'

    def ready(self):
        if hasattr(self, 'inference_engine'):
            return

        from .inference import ModelInference

        checkpoint_path = settings.BASE_DIR / "runs" / "cnn_cls_mobilenet_v3_small_20260525_205457" / "best.pth"
        rule_path = settings.BASE_DIR / "dataset" / "garbage_classify_rule.json"

        if not checkpoint_path.exists():
            logger.warning("模型文件不存在: %s", checkpoint_path)
            self.inference_engine = None
            return

        try:
            self.inference_engine = ModelInference(str(checkpoint_path), str(rule_path))
            logger.info("模型加载完成，设备: %s", self.inference_engine.device)
        except Exception as e:
            logger.error("模型加载失败: %s", e)
            self.inference_engine = None
