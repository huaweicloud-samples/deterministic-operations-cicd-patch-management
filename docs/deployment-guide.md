# 部署指南

## 前提条件

1. 已安装 Terraform >= 1.5
2. 已安装 hcloud CLI 并配置 AK/SK
3. 已开通以下华为云服务：
   - OBS（对象存储）
   - FunctionGraph（函数工作流）
   - SMN（消息通知服务）
   - LTS（云日志服务）
   - CodeArts（软件开发生产线）
   - IMS（镜像服务）
   - ECS（弹性云服务器）

## 部署步骤

### 1. 配置凭证

```bash
export HW_ACCESS_KEY="your-access-key"
export HW_SECRET_KEY="your-secret-key"
export HW_REGION="cn-north-4"
```

### 2. 部署基础设施

```bash
cd infra
terraform init
terraform plan
# 确认无误后执行
terraform apply
```

Terraform 将创建：
- 2 个 OBS 桶（补丁文件 + 补丁脚本）
- 1 个 SMN 主题
- 1 个 LTS 日志组 + 2 个日志流
- 1 个 IAM 委托
- 1 个 VPC + 子网 + 安全组
- 2 个 FunctionGraph 函数

### 3. 上传函数代码

将 FunctionGraph 函数代码打包并上传到 OBS：

```bash
# 打包远程命令执行函数
cd src/run_command
zip -r run_command.zip .
hcloud OBS UploadObject --bucket=patch-mgmt-scripts --key=function-code/run_command.zip --file=run_command.zip

# 打包补丁编排函数
cd ../patch_orchestrator
zip -r patch_orchestrator.zip .
hcloud OBS UploadObject --bucket=patch-mgmt-scripts --key=function-code/patch_orchestrator.zip --file=patch_orchestrator.zip
```

### 4. 上传补丁配置和脚本

```bash
hcloud OBS UploadObject --bucket=patch-mgmt-patch-files --key=patch.json --file=src/patch.json
hcloud OBS UploadObject --bucket=patch-mgmt-scripts --key=patch_automation.py --file=src/patch_automation.py
```

### 5. 设置 CodeArts 流水线

```bash
chmod +x scripts/setup_pipeline.sh
./scripts/setup_pipeline.sh
```

然后在 CodeArts 控制台中：
1. 配置各审批阶段的审批人
2. 配置构建任务的环境变量（引用 Terraform 输出值）
3. 配置 SMN 主题的订阅终端（邮箱/短信）

### 6. 标记目标 ECS 实例

为需要自动补丁的 ECS 实例添加标签：

```bash
hcloud ECS BatchAddServerTags \
  --server_ids "instance-id-1,instance-id-2" \
  --tags "[{\"key\":\"application-environment\",\"value\":\"dev\"},{\"key\":\"automated-patching\",\"value\":\"True\"}]"
```

### 7. 验证

提交代码变更触发流水线，或在 CodeArts 控制台手动触发：
1. 检查流水线是否正常启动
2. 检查审批步骤是否正确设置
3. 检查构建日志是否正常
4. 检查 SMN 是否收到通知
5. 检查 LTS 日志是否记录了执行信息

## 清理

```bash
cd infra
terraform destroy
```
