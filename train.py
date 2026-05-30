import time
from pathlib import Path
import argparse
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from tqdm import tqdm

# CODE_DIR = Path(__file__).resolve()
CODE_DIR = Path(__file__).resolve().parent
RUNS_DIR = CODE_DIR / "runs"


def build_model(arch: str, num_classes: int, pretrained: bool) -> nn.Module:
    """构建模型"""
    from torchvision import models
    if arch == "resnet18":
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
        model.fc = nn.Sequential(
            nn.Dropout(p=0.5),
            nn.Linear(model.fc.in_features, num_classes)
        )
    elif arch == "mobilenet_v3_small":
        model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None)
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, num_classes)

    elif arch == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT if pretrained else None)
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, num_classes)
    elif arch == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT if pretrained else None)
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, num_classes)
    else:
        raise ValueError(f"Unsupported arch: {arch}")
    return model


def train_one_epoch(
        model: nn.Module,
        loader: DataLoader,
        criterion: nn.Module,
        optimizer: torch.optim.Optimizer,
        device: torch.device,
):
    model.train()  # 切换到训练模式
    running_loss = 0.0
    correct = 0
    total = 0

    for images, targets in tqdm(loader, desc="train", leave=False):  # 数据转移到设备
        images = images.to(device)
        targets = targets.to(device)

        # 前向传播
        optimizer.zero_grad()  # 清空梯度
        logits = model(images)  # 模型预测
        loss = criterion(logits, targets)  # 计算损失

        # 反向传播
        loss.backward()
        optimizer.step()  # 更新参数

        # 统计信息
        running_loss += loss.item() * targets.size(0)
        _, predicted = logits.max(1)
        correct += predicted.eq(targets).sum().item()
        total += targets.size(0)

    return running_loss / total, correct / total


@torch.inference_mode()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    """评估模型，返回平均损失和准确率"""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, targets in tqdm(loader, desc="eval", leave=False):
        images = images.to(device)
        targets = targets.to(device)
        logits = model(images)
        loss = criterion(logits, targets)

        running_loss += loss.item() * targets.size(0)
        _, predicted = logits.max(1)
        correct += predicted.eq(targets).sum().item()
        total += targets.size(0)

    return running_loss / total, correct / total


def main():
    parser = argparse.ArgumentParser(description="CNN 垃圾分类训练")
    parser.add_argument("--data", default=str(CODE_DIR / "dataset"), help="数据集根目录")
    parser.add_argument("--arch", default="mobilenet_v3_small",
                        choices=["mobilenet_v3_small", "mobilenet_v3_large", "resnet18", "efficientnet_b0"])
    parser.add_argument("--device", default='cuda', help="cpu或cuda")
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--pretrained", default=True)
    args = parser.parse_args()

    # 设置设备：优先使用用户指定的设备
    if args.device == 'cuda' and torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        if gpu_count > 1:
            device = torch.device("cuda:1")  # 使用GPU1
            print(f"使用GPU1: {torch.cuda.get_device_name(1)}")
        else:

            device = torch.device("cuda:0")  # 只有一个GPU
            print(f"只有一个GPU，使用GPU0: {torch.cuda.get_device_name(0)}")
        print(f"GPU总数量: {gpu_count}")
    else:
        device = torch.device("cpu")
        print("使用CPU训练")

    train_dir = Path(args.data) / "train"
    test_dir = Path(args.data) / "test"

    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]

    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(args.imgsz, scale=(0.6, 1.0)),  # 随机裁剪
        transforms.RandomHorizontalFlip(),  # 随机水平翻转
        transforms.RandomRotation(15),  # 随机旋转
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),  # 颜色抖动
        transforms.ToTensor(),  # 转为张量
        transforms.Normalize(mean=mean, std=std),  # 标准化
    ])

    eval_tf = transforms.Compose([
        transforms.Resize(int(args.imgsz * 1.14)),  # 等比放大14%
        transforms.CenterCrop(args.imgsz),  # 中心裁剪
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    train_ds = ImageFolder(str(train_dir), transform=train_tf)
    test_ds = ImageFolder(str(test_dir), transform=eval_tf)
    class_names = train_ds.classes
    num_classes = len(class_names)

    print(f"类别数量: {num_classes}")
    print(f"训练集大小: {len(train_ds)}")
    print(f"测试集大小: {len(test_ds)}")

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=4, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=args.batch, shuffle=False, num_workers=4, pin_memory=True)

    model = build_model(args.arch, num_classes, args.pretrained)
    model = model.to(device)  # 关键修复：必须赋值回model

    criterion = nn.CrossEntropyLoss()

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    run_name = f"cnn_cls_{args.arch}_{time.strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    best_acc = 0.0  # 跟踪最佳准确率
    start_time = time.time()  # 记录开始时间

    print(f"\n开始训练，共 {args.epochs} 个epoch...")
    print("=" * 60)

    for epoch in range(1, args.epochs + 1):
        print(f"\nEpoch {epoch}/{args.epochs}")
        print("-" * 60)

        # 训练
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        print(f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f}")

        # 评估
        test_loss, test_acc = evaluate(model, test_loader, criterion, device)
        print(f"Test Loss: {test_loss:.4f} | Test Acc: {test_acc:.4f}")

        # 保存最佳模型
        if test_acc > best_acc:
            best_acc = test_acc
            torch.save({
                'arch': args.arch,
                'imgsz': args.imgsz,
                'mean': mean,
                'std': std,
                'class_names': class_names,
                'model_state': model.state_dict(),
                'epoch': epoch,
                'test_acc': test_acc,
            }, run_dir / "best.pth")
            print(f"✓ 保存最佳模型 (Test Acc: {best_acc:.4f})")

    elapsed_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"训练完成！")
    print(f"总用时: {elapsed_time:.2f} 秒 ({elapsed_time/60:.2f} 分钟)")
    print(f"最佳测试准确率: {best_acc:.4f}")
    print(f"模型保存路径: {run_dir / 'best.pth'}")


if __name__ == "__main__":
    main()




