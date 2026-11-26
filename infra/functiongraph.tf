# ============================================================================
# FunctionGraph 函数：远程命令执行代理
# ============================================================================
# 该函数接收实例 ID 和命令列表，通过 SSH 在目标 ECS 实例上执行补丁命令。
# 通过 SSH 在目标实例上执行远程命令，属于自建运维方案。
# 注：VPC 绑定需要 agency，暂不绑定 VPC，后续通过控制台配置
# ============================================================================

resource "huaweicloud_fgs_function" "run_command" {
  name        = "${var.project_name}-run-command"
  app         = "default"
  handler     = "index.handler"
  memory_size = var.fgs_memory
  timeout     = var.fgs_timeout
  runtime     = "Python3.9"

# 由 CodeArts Build 调用，执行补丁编排的核心逻辑
  code_url  = "https://${var.obs_script_bucket_name}.obs.${var.region}.myhuaweicloud.com/function-code/run_command.zip"

  user_data = jsonencode({
    REGION        = var.region
    OBS_BUCKET    = var.obs_script_bucket_name
    LTS_GROUP_ID  = huaweicloud_lts_group.patch_logs.id
    LTS_STREAM_ID = huaweicloud_lts_stream.command_output.id
  })

  tags = {
    project    = var.project_name
    env        = var.build_environment
    purpose    = "command-execution"
    managed-by = "terraform"
  }
}

# ============================================================================
# FunctionGraph 函数：补丁编排主函数
# ============================================================================
# 该函数协调整个补丁流程：查询实例 → 创建镜像备份 → 执行补丁 → 通知
# 由 CodeArts Build 调用，承载补丁编排的核心逻辑
# ============================================================================

resource "huaweicloud_fgs_function" "patch_orchestrator" {
  name        = "${var.project_name}-orchestrator"
  app         = "default"
  handler     = "index.handler"
  memory_size = var.fgs_memory
  timeout     = var.fgs_timeout
  runtime     = "Python3.9"

  code_type = "obs"
  code_url  = "https://${var.obs_script_bucket_name}.obs.${var.region}.myhuaweicloud.com/function-code/patch_orchestrator.zip"

  user_data = jsonencode({
    REGION           = var.region
    OBS_BUCKET       = var.obs_script_bucket_name
    SMN_TOPIC_URN    = huaweicloud_smn_topic.patch_notification.id
    LTS_GROUP_ID     = huaweicloud_lts_group.patch_logs.id
    LTS_STREAM_ID    = huaweicloud_lts_stream.patch_execution.id
    RUN_CMD_FUNCTION = huaweicloud_fgs_function.run_command.urn
  })

  tags = {
    project    = var.project_name
    env        = var.build_environment
    purpose    = "patch-orchestration"
    managed-by = "terraform"
  }
}
