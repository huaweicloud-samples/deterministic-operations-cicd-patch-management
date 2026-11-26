# ============================================================================
# SMN 主题：审批通知 + 补丁执行失败告警
# ============================================================================

resource "huaweicloud_smn_topic" "patch_notification" {
  name         = "${var.project_name}-notification"
  display_name = "Patch Management Notification"

  tags = {
    project    = var.project_name
    env        = var.build_environment
    managed-by = "terraform"
  }
}
