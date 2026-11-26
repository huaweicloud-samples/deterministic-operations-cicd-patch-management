# ============================================================================
# LTS 日志组：补丁执行日志
# ============================================================================

resource "huaweicloud_lts_group" "patch_logs" {
  group_name  = "${var.project_name}-logs"
  ttl_in_days = 30

  tags = {
    project    = var.project_name
    env        = var.build_environment
    managed-by = "terraform"
  }
}

resource "huaweicloud_lts_stream" "patch_execution" {
  group_id    = huaweicloud_lts_group.patch_logs.id
  stream_name = "patch-execution"
  ttl_in_days = 30
}

resource "huaweicloud_lts_stream" "command_output" {
  group_id    = huaweicloud_lts_group.patch_logs.id
  stream_name = "command-output"
  ttl_in_days = 30
}
