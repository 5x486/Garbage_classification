from django.db import models

# Create your models here.
# 识别记录
from django.db import models
from django.conf import settings

class RecordStatus(models.TextChoices):
    SUCCESS = "success", "成功"
    PROCESSING = "processing", "处理中"
    FAILED = "failed", "失败"

# 假设 RecordType 也是在别处定义的，根据代码推断补充
class RecordType(models.TextChoices):
    # 根据实际业务添加选项，这里给出示例
    MANUAL = "manual", "手动"
    UPLOAD = "upload", "文件上传"
    API = "api", "API调用"

class RecognitionRecord(models.Model):
    # 识别人/来源/录入文件/输出文件/图片/预测结果/置信度
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    record_type = models.CharField(max_length=16, choices=RecordType.choices, verbose_name="来源")
    status = models.CharField(
        max_length=16,
        choices=RecordStatus.choices,
        default=RecordStatus.SUCCESS,
        verbose_name="状态",
    )

    source_file = models.FileField(upload_to="uploads/%Y/%m/%d/", null=True, blank=True, verbose_name="输入文件")
    output_file = models.FileField(upload_to="outputs/%Y/%m/%d/", null=True, blank=True, verbose_name="输出文件")
    snapshot = models.ImageField(upload_to="snapshots/%Y/%m/%d/", null=True, blank=True, verbose_name="截图")

    result_class = models.CharField(max_length=16, blank=True, verbose_name="预测类别ID")
    result_label = models.CharField(max_length=128, blank=True, verbose_name="预测结果")
    result_category = models.CharField(max_length=64, blank=True, verbose_name="大类")
    confidence = models.FloatField(null=True, blank=True, verbose_name="置信度")

    topk = models.JSONField(null=True, blank=True, verbose_name="TopK")
    extra = models.JSONField(null=True, blank=True, verbose_name="附加信息")
    error_message = models.TextField(blank=True, verbose_name="错误信息")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "识别记录"
        verbose_name_plural = "识别记录"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["record_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["result_category", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_record_type_display()} {self.result_label or self.result_class} ({self.created_at:%Y-%m-%d %H:%M:%S})"









