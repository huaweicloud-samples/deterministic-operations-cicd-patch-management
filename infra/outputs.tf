# ============================================================================
# 输出
# ============================================================================

output "obs_patch_bucket" {
  description = "补丁文件 OBS 桶名"
  value       = huaweicloud_obs_bucket.patch_files.bucket
}

output "obs_script_bucket" {
  description = "补丁脚本 OBS 桶名"
  value       = huaweicloud_obs_bucket.patch_scripts.bucket
}

output "smn_topic_urn" {
  description = "SMN 主题 URN"
  value       = huaweicloud_smn_topic.patch_notification.id
}

output "run_command_function_urn" {
  description = "远程命令执行函数 URN"
  value       = huaweicloud_fgs_function.run_command.urn
}

output "patch_orchestrator_function_urn" {
  description = "补丁编排函数 URN"
  value       = huaweicloud_fgs_function.patch_orchestrator.urn
}

output "lts_group_id" {
  description = "LTS 日志组 ID"
  value       = huaweicloud_lts_group.patch_logs.id
}

output "vpc_id" {
  description = "VPC ID"
  value       = data.huaweicloud_vpc.patch_vpc.id
}

output "subnet_id" {
  description = "子网 ID"
  value       = huaweicloud_vpc_subnet.patch_subnet.id
}

output "security_group_id" {
  description = "安全组 ID"
  value       = huaweicloud_networking_secgroup.patch_sg.id
}
