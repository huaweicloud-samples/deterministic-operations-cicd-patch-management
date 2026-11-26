# ============================================================================
# 网络基础设施：FunctionGraph 函数访问 ECS 实例的网络
# 使用现有 VPC（myvpc）
# ============================================================================

data "huaweicloud_vpc" "patch_vpc" {
  name = "myvpc"
}

resource "huaweicloud_vpc_subnet" "patch_subnet" {
  name       = "${var.project_name}-subnet"
  vpc_id     = data.huaweicloud_vpc.patch_vpc.id
  cidr       = "10.0.5.0/24"
  gateway_ip = "10.0.5.1"

  tags = {
    project    = var.project_name
    managed-by = "terraform"
  }
}

resource "huaweicloud_networking_secgroup" "patch_sg" {
  name        = "${var.project_name}-sg"
  description = "Security group for patch management"

  tags = {
    project    = var.project_name
    managed-by = "terraform"
  }
}

# 允许 SSH 访问（FunctionGraph 执行远程命令需要）
resource "huaweicloud_networking_secgroup_rule" "allow_ssh" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = "10.0.0.0/16"
  security_group_id = huaweicloud_networking_secgroup.patch_sg.id
}
