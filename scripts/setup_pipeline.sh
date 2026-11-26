#!/bin/bash
# ============================================================================
# CodeArts 流水线设置脚本
# ============================================================================
# 用途：通过 hcloud CLI 创建 CodeArts 项目、代码仓库、构建任务和流水线
# 前提：已安装 hcloud CLI 并配置好 AK/SK
# ============================================================================

set -euo pipefail

PROJECT_NAME="patch-mgmt"
REGION="${REGION:-cn-north-4}"
REPO_NAME="deterministic-operations-cicd-patch-management"

echo "==== 1. 创建 CodeArts 项目 ===="
hcloud CodeArts CreateProject \
  --name "${PROJECT_NAME}" \
  --description "CI/CD 驱动的自动化补丁管理系统" \
  --region "${REGION}"

echo "==== 2. 创建代码仓库 ===="
hcloud CodeArts CreateRepository \
  --project_name "${PROJECT_NAME}" \
  --repo_name "${REPO_NAME}" \
  --description "确定性运维：CI/CD 补丁管理"

echo "==== 3. 创建构建任务 - dev 环境 ===="
hcloud CodeArts CreateBuildJob \
  --project_name "${PROJECT_NAME}" \
  --job_name "patch-dev" \
  --buildspec_file "src/buildspec.yml" \
  --parameters "ENVIRONMENT=dev,REGION=${REGION}"

echo "==== 4. 创建构建任务 - qa 环境 ===="
hcloud CodeArts CreateBuildJob \
  --project_name "${PROJECT_NAME}" \
  --job_name "patch-qa" \
  --buildspec_file "src/buildspec.yml" \
  --parameters "ENVIRONMENT=qa,REGION=${REGION}"

echo "==== 5. 创建构建任务 - stg 环境 ===="
hcloud CodeArts CreateBuildJob \
  --project_name "${PROJECT_NAME}" \
  --job_name "patch-stg" \
  --buildspec_file "src/buildspec.yml" \
  --parameters "ENVIRONMENT=stg,REGION=${REGION}"

echo "==== 6. 创建构建任务 - 黄金镜像 ===="
hcloud CodeArts CreateBuildJob \
  --project_name "${PROJECT_NAME}" \
  --job_name "golden-image" \
  --buildspec_file "src/buildspec_golden_image.yml" \
  --parameters "ENVIRONMENT=dev,REGION=${REGION}"

echo "==== 7. 创建流水线 ===="
hcloud CodeArts CreatePipeline \
  --project_name "${PROJECT_NAME}" \
  --pipeline_name "patch-management-pipeline" \
  --stages '[
    {
      "name": "Source",
      "type": "source",
      "config": {"repo": "'"${REPO_NAME}"'", "branch": "main"}
    },
    {
      "name": "Approval-Dev",
      "type": "approval",
      "config": {"approvers": [], "description": "审批 dev 环境补丁执行"}
    },
    {
      "name": "Build-Dev",
      "type": "build",
      "config": {"job": "patch-dev"}
    },
    {
      "name": "Build-Golden-Image",
      "type": "build",
      "config": {"job": "golden-image"}
    },
    {
      "name": "Approval-QA",
      "type": "approval",
      "config": {"approvers": [], "description": "审批 qa 环境补丁执行"}
    },
    {
      "name": "Build-QA",
      "type": "build",
      "config": {"job": "patch-qa"}
    },
    {
      "name": "Approval-Stg",
      "type": "approval",
      "config": {"approvers": [], "description": "审批 stg 环境补丁执行"}
    },
    {
      "name": "Build-Stg",
      "type": "build",
      "config": {"job": "patch-stg"}
    }
  ]'

echo "==== CodeArts 流水线设置完成 ===="
echo "请在 CodeArts 控制台配置审批人信息"
