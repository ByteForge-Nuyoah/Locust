#!/bin/bash
set -e

echo "=== 开始 CI/CD 配置验证 ==="

# 1. 验证 Dockerfile
if [ -f "Dockerfile" ]; then
    echo "[PASS] Dockerfile 存在"
    if grep -q "PYTHONUNBUFFERED" Dockerfile; then
        echo "[PASS] Dockerfile 包含 PYTHONUNBUFFERED 优化"
    else
        echo "[WARN] Dockerfile 缺少 PYTHONUNBUFFERED 环境变量"
    fi
else
    echo "[FAIL] Dockerfile 不存在"
    exit 1
fi

# 2. 验证 .dockerignore
if [ -f ".dockerignore" ]; then
    echo "[PASS] .dockerignore 存在"
else
    echo "[WARN] .dockerignore 不存在 (建议创建以减小镜像体积)"
fi

# 3. 验证 K8s 配置
K8S_DIR="k8s"
if [ -d "$K8S_DIR" ]; then
    echo "[PASS] k8s 目录存在"
    for file in locust-master.yaml locust-worker.yaml; do
        if [ -f "$K8S_DIR/$file" ]; then
            echo "[PASS] Found $file"
        else
            echo "[FAIL] Missing $file"
        fi
    done
else
    echo "[FAIL] k8s 目录不存在"
fi

# 4. 建议的构建命令
echo ""
echo "=== 建议的构建与部署命令 ==="
echo "1. 构建 Docker 镜像:"
echo "   docker build -t my-locust-image:latest ."
echo ""
echo "2. 推送镜像 (如果使用远程集群):"
echo "   docker tag my-locust-image:latest your-registry/my-locust-image:latest"
echo "   docker push your-registry/my-locust-image:latest"
echo ""
echo "3. 部署到 Kubernetes:"
echo "   kubectl apply -f k8s/configmap.yaml (如果有)"
echo "   kubectl apply -f k8s/locust-master.yaml"
echo "   kubectl apply -f k8s/locust-worker.yaml"
echo ""
echo "=== 验证结束 ==="
