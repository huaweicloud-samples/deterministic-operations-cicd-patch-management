# ============================================================================
# IAM 委托：让 FunctionGraph 可访问 OBS / SMN / ECS / IMS
# ============================================================================
# delegated_service_name = "op_svc_fgs" 委托给 FunctionGraph 服务
# 这样 FunctionGraph 才能通过此委托访问用户的 OBS/SMN/ECS/IMS 资源
# ============================================================================

resource "huaweicloud_identity_agency" "functiongraph" {
  name                  = "${var.project_name}-fgs-agency"
  description           = "Agency for FunctionGraph to access OBS, SMN, ECS, IMS"
  duration              = "FOREVER"
  delegated_service_name = "op_svc_fgs"

  project_role {
    project = var.region
    roles = [
      "OBS OperateAccess",
      "SMN FullAccess",
      "ECS FullAccess",
      "IMS FullAccess",
    ]
  }
}
