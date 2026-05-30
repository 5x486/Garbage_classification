import torch

print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 是否可用: {torch.cuda.is_available()}")
print(f"CUDA 版本: {torch.version.cuda}")
print(f"cuDNN 版本: {torch.backends.cudnn.version()}")

if torch.cuda.is_available():
    print(f"GPU 数量: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
else:
    print("未检测到 GPU！")
    print("\n请检查：")
    print("1. 是否安装了 CUDA 版本的 PyTorch")
    print("2. NVIDIA 驱动是否正确安装")
    print("3. CUDA 版本是否与 PyTorch 兼容")
# pip install torch==2.13.0.dev20260524 --index-url https://download.pytorch.org/whl/nightly/cu132
