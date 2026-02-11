# Locust 性能测试框架 (Advanced Edition)

基于 **Locust + InfluxDB + Grafana** 的多项目、工程化性能测试体系。支持 cURL 自动转脚本、分级颜色日志、分布式监控、以及多渠道（钉钉/企业微信/邮件）自动化报告通知。

## 🚀 核心特性

-   **多项目隔离**：支持 `projects/` 目录下多项目独立管理配置、数据与场景。
-   **一键运行 (Quick Start)**：通过 `run.py` 自动完成“测试执行 -> 报告生成 -> 自动打开报告 -> 结果通知”的全流程。
-   **分级颜色日志**：控制台输出根据日志级别（DEBUG/INFO/WARN/ERROR）显示不同颜色，极大提升调试体验。
-   **全自动化监控面板**：集成 Grafana Provisioning，启动容器即自动加载 InfluxDB 数据源与预设的性能监控面板。
-   **增强型配置管理**：支持环境变量替换 (`${VAR:-default}`)、点号嵌套访问 (`notification.enabled`) 以及项目级配置覆盖。
-   **多格式数据驱动**：内置 `DataLoaderFactory`，支持 CSV、JSON、YAML 格式的测试数据循环读取。
-   **cURL 自动转换**：一键将浏览器 cURL 命令转换为可执行的 Locust 性能测试脚本。
-   **性能分析报告**：压测结束自动发送详细报告，包含：
    -   核心指标：Requests, RPS, Failure Rate, Avg/P95/P99 RT。
    -   **Top 5 慢接口统计**：直观定位性能瓶颈。
    -   **报告自动压缩**：自动打包 HTML 与 CSV 数据为 ZIP 附件发送。

---

## 📂 项目结构

```text
Locust/
├── projects/                # [核心] 各项目资源目录
│   └── crm/                 # 项目示例：包含数据、环境配置、场景脚本
├── src/                     # 公共核心源码
│   ├── common/              # 数据加载、通知器、InfluxDB 监听器、颜色日志工具
│   └── config/              # 配置管理器 (支持嵌套访问与环境变量)
├── deploy/                  # 部署与基础设施
│   ├── grafana/             # Grafana 面板与数据源自动配置 (Provisioning)
│   └── k8s/                 # Kubernetes 部署清单
├── tests/                   # 单元测试 (Config, Notifier, DataLoader)
├── tools/                   # 辅助工具集 (cURL 转换、定时任务、CI 运行器)
├── logs/                    # 运行日志目录
├── reports/                 # 压测报告存档 (HTML, ZIP, CSV)
├── run.py                   # 【推荐】交互式一键运行入口
├── run_config.yaml          # 运行参数全局配置文件
├── locustfile.py            # Locust 启动入口 (支持动态加载项目)
├── docker-compose.yml       # 基础设施编排 (InfluxDB, Chronograf, Grafana)
└── requirements.txt         # 核心依赖列表
```

---

## 🛠️ 快速开始

### 1. 环境准备
```bash
# 安装核心依赖
pip install -r requirements.txt

# 启动监控基础设施 (InfluxDB + Chronograf + Grafana)
docker-compose up -d
```
-   **Grafana**: [http://localhost:3000](http://localhost:3000) (admin/admin) —— 性能监控面板。
-   **Chronograf**: [http://localhost:8888](http://localhost:8888) —— InfluxDB 可视化管理后台。

### 2. 运行压测 (Quick Start)
这是最推荐的运行方式，它会根据 `run_config.yaml` 自动执行：
```bash
# 运行默认项目
python3 run.py

# 指定项目与并发数
python3 run.py crm dev 50 5m
```
*注：在 macOS 上，测试结束后会自动在浏览器打开 HTML 报告，并根据配置的时间自动关闭标签页。*

### 3. CI/CD 自动化运行
适用于 Jenkins 或 GitHub Actions：
```bash
python3 tools/run_test.py -p crm -e dev -u 20 -r 5 -t 2m
```

### 4. 启动定时任务
```bash
# 读取 base.yaml 中的 schedule 配置自动运行
python3 tools/scheduler.py -p crm
```

---

## 💡 高级功能说明

### 🌈 颜色日志
项目内置了颜色日志工具，无需额外配置即可在控制台看到彩色的运行状态。如需在自定义脚本中使用：
```python
from src.common.logger_utils import setup_logger
logger = setup_logger(__name__)
logger.info("这是一条绿色日志")
logger.error("这是一条红色错误日志")
```

### ⚙️ 嵌套配置访问
您可以使用点号访问深层配置，并支持环境变量默认值：
```python
from src.config.manager import config
token = config.get("notification.dingtalk.token")
db_host = config.get("influxdb.host", "${INFLUX_HOST:-localhost}")
```

### 📊 自动监控面板
通过 `deploy/grafana/provisioning`，Grafana 会在启动时自动加载 `locust_dashboard.json`。您无需手动导入 JSON 即可直接查看实时性能图表。

---

## 🧪 单元测试
为了保证核心组件的稳定性，建议在修改代码后运行测试：
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 -m unittest discover tests
```

---
