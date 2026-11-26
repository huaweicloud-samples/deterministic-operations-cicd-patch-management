# deterministic-operations-cicd-patch-management · 确定性运维：CI/CD 驱动的自动化补丁管理

![License: MIT-0](https://img.shields.io/badge/License-MIT--0-yellow.svg)
通过 CI/CD 流水线驱动操作系统补丁的自动化管理，以分阶段审批流程控制补丁从开发环境到预发布环境的逐步部署，每次部署前自动创建镜像备份，确保运维操作的确定性和可回溯性。

## 1. 简介 / Overview

### 简介


本项目通过 CI/CD 流水线驱动操作系统补丁的自动化管理。核心思路：以分阶段审批流程控制补丁从开发环境到预发布环境的逐步部署，每次部署前自动创建镜像备份，确保运维操作的确定性和可回溯性。

本项目在华为云 CodeArts Pipeline + CodeArts Build + ECS + FunctionGraph 上实现 CI/CD 驱动的自动化补丁管理。

---

## 2. 目录

- [1. 简介 / Overview](#1-简介--overview)
- [2. 目录](#2-目录)
- [3. 架构图](#3-架构图)
- [4. 方案亮点](#4-方案亮点)
- [5. 涉及云服务](#5-涉及云服务)
- [6. 前置条件](#6-前置条件)
- [7. 快速开始](#7-快速开始)
- [8. 分步部署](#8-分步部署)
- [9. 使用方法 / 验证](#9-使用方法--验证)
- [10. 清理资源](#10-清理资源)
- [11. 详细说明](#11-详细说明)
- [12. 依赖](#12-依赖)
- [13. FAQ / 故障排除](#13-faq--故障排除)
- [14. 贡献指南](#14-贡献指南)
- [15. 许可证](#15-许可证)
- [16. 联系方式 / 维护者](#16-联系方式--维护者)

### 目录结构


```
deterministic-operations-cicd-patch-management/
├── infra/                          # Terraform IaC
│   ├── provider.tf                 # Provider 配置 + 变量定义
│   ├── obs.tf                      # OBS 桶
│   ├── iam.tf                      # IAM 委托
│   ├── smn.tf                      # SMN 通知主题
│   ├── lts.tf                      # LTS 日志组 + 流
│   ├── network.tf                  # VPC + 子网 + 安全组
│   ├── functiongraph.tf            # FunctionGraph 函数
│   └── outputs.tf                  # 输出变量
├── src/                            # 源代码
│   ├── patch_automation.py         # 补丁自动化主脚本
│   ├── patch.json                  # 补丁配置
│   ├── buildspec.yml               # CodeArts Build 配置
│   ├── buildspec_golden_image.yml  # CodeArts Build 配置
│   ├── run_command/                # 远程命令执行函数
│   │   └── index.py
│   └── patch_orchestrator/         # 补丁编排函数
│       └── index.py
├── scripts/                        # 脚本
│   └── setup_pipeline.sh           # CodeArts 流水线设置
├── docs/                           # 文档
│   ├── architecture.md             # 架构说明
│   └── deployment-guide.md         # 部署指南
├── README.md
├── README.en.md
└── LICENSE
```

---

## 3. 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     CodeArts Pipeline                        │
│  Source → Approval(Dev) → Build(Dev) → Build(Golden)        │
│         → Approval(QA) → Build(QA)                          │
│         → Approval(Stg) → Build(Stg)                        │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  CodeArts Build → patch_automation.py → FunctionGraph        │
└─────────────────────────┬───────────────────────────────────┘
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         OBS 桶      SMN 主题     LTS 日志
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  FunctionGraph (run_command) → SSH → ECS 实例集群            │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
                    IMS 镜像备份
```

详细架构说明请参考 [docs/architecture.md](docs/architecture.md)。

---

## 4. 方案亮点

- **分阶段审批**：补丁部署经过 dev → qa → stg 三阶段审批，确保变更可控
- **镜像备份**：每次补丁执行前自动创建 IMS 镜像备份，支持快速回滚
- **标签筛选**：通过 ECS 标签筛选目标实例，灵活控制补丁范围
- **黄金镜像**：补丁验证通过后创建黄金镜像，供后续部署使用
- **通知告警**：通过 SMN 发送补丁执行结果，及时感知异常
- **日志记录**：通过 LTS 记录完整执行日志，支持审计追溯
- **IaC 管理**：全部基础设施通过 Terraform 管理，可版本化、可复现

---

## 5. 涉及云服务

| 组件 | 服务 | 说明 |
|------|------|------|
| 流水线 | CodeArts Pipeline | 编排补丁部署流程，包含审批门禁 |
| 构建任务 | CodeArts Build | 执行补丁自动化脚本 |
| 命令执行 | FunctionGraph | 远程命令执行代理，通过 SSH 在 ECS 上执行命令 |
| 补丁编排 | FunctionGraph | 协调整个补丁流程 |
| 文件存储 | OBS | 存储补丁配置文件和脚本 |
| 通知 | SMN | 发送补丁执行结果通知 |
| 日志 | LTS | 记录补丁执行日志 |
| 镜像 | IMS | 创建实例备份和黄金镜像 |
| 身份 | IAM | FunctionGraph 委托授权 |
| 网络 | VPC | FunctionGraph 访问 ECS 的网络 |

---

## 6. 前置条件

1. 华为云账号，已开通以下服务：OBS、FunctionGraph、SMN、LTS、CodeArts、IMS、ECS、VPC、IAM
2. 已安装 Terraform >= 1.5
3. 已安装 hcloud CLI 并配置 AK/SK
4. 目标 ECS 实例已配置 SSH 访问

---

## 7. 快速开始

```bash
# 1. 配置凭证
export HW_ACCESS_KEY="your-access-key"
export HW_SECRET_KEY="your-secret-key"

# 2. 部署基础设施
cd infra
terraform init && terraform apply

# 3. 上传函数代码和配置
# （详见 docs/deployment-guide.md）

# 4. 设置 CodeArts 流水线
cd ../scripts && bash setup_pipeline.sh
```

---

## 8. 分步部署

详细步骤请参考 [docs/deployment-guide.md](docs/deployment-guide.md)。

### 补丁配置 (src/patch.json)

```json
{
  "ApplyAllPatches": true,
  "deploy_from": "1",
  "patch": {
    "1": ["yum update -y"],
    "2": ["yum install httpd -y"]
  }
}
```

| 字段 | 说明 |
|------|------|
| ApplyAllPatches | 是否应用所有补丁（true）或从指定编号开始（false） |
| deploy_from | 起始补丁编号（ApplyAllPatches=false 时生效） |
| patch | 补丁命令字典，键为编号，值为命令列表 |

### Terraform 变量 (infra/provider.tf)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| region | cn-north-4 | 华为云区域 |
| project_name | patch-mgmt | 资源命名前缀 |
| build_environment | dev | 构建环境标识 |
| obs_patch_bucket_name | patch-mgmt-patch-files | 补丁文件桶名 |
| obs_script_bucket_name | patch-mgmt-scripts | 脚本桶名 |
| fgs_timeout | 300 | 函数超时（秒） |
| fgs_memory | 512 | 函数内存（MB） |

---

## 9. 使用方法 / 验证

### 使用方法

本实践通过修改补丁配置并推送代码触发 CodeArts 流水线，也可通过 hcloud CLI 手动调用 FunctionGraph 函数；详细验证方法见第 11 节。

### 触发补丁部署

1. 修改 `src/patch.json` 中的补丁配置
2. 提交代码变更到仓库
3. CodeArts Pipeline 自动触发
4. 在审批阶段确认后，补丁将按环境顺序执行

### 手动触发

```bash
hcloud FunctionGraph InvokeFunction \
  --function_urn "patch-orchestrator-urn" \
  --body '{"environment":"dev","update_golden_image":false}'
```

### 标记目标实例

```bash
hcloud ECS BatchAddServerTags \
  --server_ids "instance-id-1,instance-id-2" \
  --tags '[{"key":"application-environment","value":"dev"},{"key":"automated-patching","value":"True"}]'
```

部署完成后请按本节步骤自行验证，确认业务功能可用，方可视为交付完成。

---

## 10. 清理资源

```bash
cd infra
terraform destroy
```

然后在 CodeArts 控制台删除项目、仓库、构建任务和流水线。

---

## 11. 详细说明

### 验证方法

1. **基础设施验证**：`terraform output` 检查输出值
2. **函数验证**：手动调用 FunctionGraph 函数检查返回值
3. **流水线验证**：在 CodeArts 控制台检查流水线状态
4. **通知验证**：检查 SMN 主题是否收到通知消息
5. **日志验证**：在 LTS 控制台查看执行日志

### 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 函数调用超时 | ECS 实例无响应 | 检查实例状态和网络连通性 |
| SMN 通知未收到 | 主题无订阅 | 在 SMN 控制台添加订阅终端 |
| 流水线未触发 | 代码仓库未关联 | 检查 CodeArts 流水线源配置 |
| 实例查询为空 | 标签不匹配 | 检查 ECS 实例标签是否正确 |

### 扩展指南

- **添加新环境**：在 `scripts/setup_pipeline.sh` 中添加新的构建任务和审批阶段
- **自定义补丁命令**：修改 `src/patch.json` 中的 patch 字典
- **集成监控告警**：添加 CES 告警规则监控补丁执行指标
- **支持多区域**：在 Terraform 中添加 provider alias 实现多区域部署
- **容器化部署**：将 ECS 替换为 CCE 节点，使用 kubectl 执行补丁命令

---

## 12. 依赖

- Terraform >= 1.5
- huaweicloud Terraform Provider ~> 1.70
- hcloud CLI
- Python 3.9+（FunctionGraph 运行时）
- SSH 客户端（远程命令执行）

### 参考文档

- [架构说明](docs/architecture.md)
- [部署指南](docs/deployment-guide.md)
- [Terraform HuaweiCloud Provider](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [FunctionGraph 开发指南](https://support.huaweicloud.com/functiongraph/)
- [CodeArts 流水线](https://support.huaweicloud.com/codepipeline/)
- [OBS 对象存储](https://support.huaweicloud.com/obs/)

---

## 13. FAQ / 故障排除

### FAQ

### Q: FunctionGraph 函数无法连接 ECS 实例？

检查以下项：
1. FunctionGraph 函数是否配置了 VPC 和子网
2. 安全组是否允许 SSH（端口 22）访问
3. ECS 实例的 SSH 服务是否正常运行
4. SSH 密钥是否正确配置

### Q: 补丁执行失败如何回滚？

每次补丁执行前会创建 IMS 镜像备份，可通过镜像备份恢复实例：
1. 在 IMS 控制台找到备份镜像
2. 使用备份镜像创建新实例
3. 替换原实例

### Q: 如何添加新的补丁命令？

编辑 `src/patch.json`，在 `patch` 字典中添加新条目：
```json
"3": ["yum install nginx -y"]
```

---

## 14. 贡献指南

欢迎提交 Issue 和 Pull Request。请确保：
1. 代码通过现有测试
2. Terraform 配置可通过 `terraform validate`
3. 不引入新的外部依赖

---

## 15. 许可证

MIT No Attribution - 详见 [LICENSE](LICENSE)

---

## 16. 联系方式 / 维护者
| 项 | 内容 |
|---|---|
| **创建者** | [dgc-git](https://github.com/dgc-git) |
| **维护者** | [dgc-git](https://github.com/dgc-git) |
| **联系方式** | GitHub Issues / PR（见[第 14 节](#14-贡献指南)） |
