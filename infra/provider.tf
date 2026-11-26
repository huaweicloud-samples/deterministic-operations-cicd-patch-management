terraform {
  required_version = ">= 1.5"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = "~> 1.70"
    }
  }

  backend "local" {}
}

provider "huaweicloud" {
  region = var.region
  # 在华为云「我的凭证」页面获取 Access Key 并填入环境变量
  # export HW_ACCESS_KEY="your-access-key"
  # export HW_SECRET_KEY="your-secret-key"
}

# ============================================================================
# 变量定义
# ============================================================================

variable "region" {
  description = "华为云区域"
  type        = string
  default     = "cn-north-4"
}

variable "project_name" {
  description = "项目名称，用于资源命名前缀"
  type        = string
  default     = "patch-mgmt"
}

variable "build_environment" {
  description = "构建环境标识"
  type        = string
  default     = "dev"
}

variable "domain_name" {
  description = "华为云账号域名（IAM 委托归属域）"
  type        = string
  default     = "your-huaweicloud-domain"
}

variable "obs_patch_bucket_name" {
  description = "补丁文件 OBS 桶名（全局唯一）"
  type        = string
  default     = "patch-mgmt-patch-files"
}

variable "obs_script_bucket_name" {
  description = "补丁脚本 OBS 桶名（全局唯一）"
  type        = string
  default     = "patch-mgmt-scripts"
}

variable "fgs_timeout" {
  description = "FunctionGraph 函数超时时间（秒）"
  type        = number
  default     = 300
}

variable "fgs_memory" {
  description = "FunctionGraph 函数内存大小（MB）"
  type        = number
  default     = 512
}
