# ============================================================================
# OBS 桶：补丁文件存储 + 补丁脚本存储
# ============================================================================

resource "huaweicloud_obs_bucket" "patch_files" {
  bucket        = var.obs_patch_bucket_name
  acl           = "private"
  force_destroy = true
  versioning    = true
  encryption    = true

  tags = {
    project    = var.project_name
    env        = var.build_environment
    purpose    = "patch-files"
    managed-by = "terraform"
  }
}

resource "huaweicloud_obs_bucket" "patch_scripts" {
  bucket        = var.obs_script_bucket_name
  acl           = "private"
  force_destroy = true
  versioning    = true
  encryption    = true

  tags = {
    project    = var.project_name
    env        = var.build_environment
    purpose    = "patch-scripts"
    managed-by = "terraform"
  }
}
