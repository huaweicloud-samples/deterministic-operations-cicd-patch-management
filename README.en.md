# deterministic-operations-cicd-patch-management · Deterministic Operations: CI/CD-Driven Automated Patch Management

![License: MIT-0](https://img.shields.io/badge/License-MIT--0-yellow.svg)
Automate OS patching through a CI/CD pipeline with a staged approval flow that controls progressive patch deployment from the dev environment to the pre-release environment, creating an image backup before every deployment to ensure deterministic and auditable operations.

## 1. Overview

### Overview

This project automates OS patch management through a CI/CD pipeline. The core idea: use staged approval flows to control patch deployment from dev to pre-release environments, with automatic image backups before each deployment to ensure deterministic and auditable operations.

This project implements CI/CD-driven automated patch management on Huawei Cloud CodeArts Pipeline + CodeArts Build + ECS + FunctionGraph.

---

## 2. Table of Contents

- [1. Overview](#1-overview)
- [2. Table of Contents](#2-table-of-contents)
- [3. Architecture Diagram](#3-architecture-diagram)
- [4. Highlights](#4-highlights)
- [5. Cloud Services Used](#5-cloud-services-used)
- [6. Prerequisites](#6-prerequisites)
- [7. Quick Start](#7-quick-start)
- [8. Step-by-Step Deployment](#8-step-by-step-deployment)
- [9. Usage / Verification](#9-usage--verification)
- [10. Cleanup](#10-cleanup)
- [11. Detailed Explanation](#11-detailed-explanation)
- [12. Dependencies](#12-dependencies)
- [13. FAQ / Troubleshooting](#13-faq--troubleshooting)
- [14. Contributing](#14-contributing)
- [15. License](#15-license)
- [16. Contact / Maintainers](#16-contact--maintainers)

### Directory Structure

```
deterministic-operations-cicd-patch-management/
├── infra/                          # Terraform IaC
│   ├── provider.tf                 # Provider config + variables
│   ├── obs.tf                      # OBS bucket
│   ├── iam.tf                      # IAM agency
│   ├── smn.tf                      # SMN notification topic
│   ├── lts.tf                      # LTS log group + stream
│   ├── network.tf                  # VPC + subnet + security group
│   ├── functiongraph.tf            # FunctionGraph functions
│   └── outputs.tf                  # Output variables
├── src/                            # Source code
│   ├── patch_automation.py         # Main patch automation script
│   ├── patch.json                  # Patch configuration
│   ├── buildspec.yml               # CodeArts Build config
│   ├── buildspec_golden_image.yml  # CodeArts Build config
│   ├── run_command/                # Remote command execution function
│   │   └── index.py
│   └── patch_orchestrator/         # Patch orchestration function
│       └── index.py
├── scripts/                        # Scripts
│   └── setup_pipeline.sh           # CodeArts pipeline setup
├── docs/                           # Documentation
│   ├── architecture.md             # Architecture description
│   └── deployment-guide.md         # Deployment guide
├── README.md
├── README.en.md
└── LICENSE
```

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     CodeArts Pipeline                        │
│  Source → Approval(Dev) → Build(Dev) → Build(Golden)        │
│         → Approval(QA) → Build(QA)                          │
│         → Approval(Stg) → Build(Stg)                        │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  CodeArts Build → patch_automation.py → FunctionGraph        │
└─────────────────────────┬───────────────────────────────────┘
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         OBS bucket     SMN topic   LTS logs
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  FunctionGraph (run_command) → SSH → ECS instance cluster    │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
                    IMS image backup
```

See [docs/architecture.md](docs/architecture.md) for the detailed architecture.

---

## 4. Highlights

- **Staged approvals**: patch deployment goes through three approval stages, dev → qa → stg, keeping changes controllable
- **Image backups**: an IMS image backup is created automatically before every patch execution for fast rollback
- **Tag-based filtering**: target instances are selected by ECS tags for flexible patch scope control
- **Golden image**: a golden image is created after patch validation passes, for later deployments
- **Notification alerts**: patch execution results are sent via SMN for timely anomaly awareness
- **Log recording**: full execution logs are recorded in LTS for audit traceability
- **IaC management**: all infrastructure is managed by Terraform, versionable and reproducible

---

## 5. Cloud Services Used

| Component | Service | Description |
|------|------|------|
| Pipeline | CodeArts Pipeline | Orchestrates the patch deployment flow with approval gates |
| Build task | CodeArts Build | Executes the patch automation script |
| Command execution | FunctionGraph | Remote command execution agent, runs commands on ECS over SSH |
| Patch orchestration | FunctionGraph | Coordinates the entire patch flow |
| File storage | OBS | Stores patch configuration files and scripts |
| Notification | SMN | Sends patch execution result notifications |
| Logs | LTS | Records patch execution logs |
| Image | IMS | Creates instance backups and golden images |
| Identity | IAM | FunctionGraph agency authorization |
| Network | VPC | Network for FunctionGraph to access ECS |

---

## 6. Prerequisites

1. Huawei Cloud account with the following services enabled: OBS, FunctionGraph, SMN, LTS, CodeArts, IMS, ECS, VPC, IAM
2. Terraform >= 1.5 installed
3. hcloud CLI installed with AK/SK configured
4. Target ECS instances configured for SSH access

---

## 7. Quick Start

```bash
# 1. Configure credentials
export HW_ACCESS_KEY="your-access-key"
export HW_SECRET_KEY="your-secret-key"

# 2. Deploy infrastructure
cd infra
terraform init && terraform apply

# 3. Upload function code and configuration
# (see docs/deployment-guide.md)

# 4. Set up the CodeArts pipeline
cd ../scripts && bash setup_pipeline.sh
```

---

## 8. Step-by-Step Deployment

Detailed steps are in [docs/deployment-guide.md](docs/deployment-guide.md).

### Patch configuration (src/patch.json)

```json
{
  "ApplyAllPatches": true,
  "deploy_from": "1",
  "patch": {
    "1": ["yum update -y"],
    "2": ["yum install httpd -y"]
  }
}
```

| Field | Description |
|------|------|
| ApplyAllPatches | Whether to apply all patches (true) or start from a given number (false) |
| deploy_from | Starting patch number (effective when ApplyAllPatches=false) |
| patch | Patch command dictionary, keyed by number, with a list of commands as value |

### Terraform variables (infra/provider.tf)

| Variable | Default | Description |
|------|--------|------|
| region | cn-north-4 | Huawei Cloud region |
| project_name | patch-mgmt | Resource naming prefix |
| build_environment | dev | Build environment identifier |
| obs_patch_bucket_name | patch-mgmt-patch-files | Patch file bucket name |
| obs_script_bucket_name | patch-mgmt-scripts | Script bucket name |
| fgs_timeout | 300 | Function timeout (seconds) |
| fgs_memory | 512 | Function memory (MB) |

---

## 9. Usage / Verification

### Usage

This practice triggers the CodeArts pipeline by modifying the patch configuration and pushing code, or invokes the FunctionGraph function manually via the hcloud CLI; see Section 11 for detailed verification methods.

### Trigger patch deployment

1. Modify the patch configuration in `src/patch.json`
2. Commit the code change to the repository
3. CodeArts Pipeline triggers automatically
4. After approval is confirmed, patches execute in environment order

### Manual trigger

```bash
hcloud FunctionGraph InvokeFunction \
  --function_urn "patch-orchestrator-urn" \
  --body '{"environment":"dev","update_golden_image":false}'
```

### Tag target instances

```bash
hcloud ECS BatchAddServerTags \
  --server_ids "instance-id-1,instance-id-2" \
  --tags '[{"key":"application-environment","value":"dev"},{"key":"automated-patching","value":"True"}]'
```

After deployment, follow these steps to verify that the business functionality works before considering the delivery complete.

---

## 10. Cleanup

```bash
cd infra
terraform destroy
```

Then delete the project, repository, build tasks, and pipeline in the CodeArts console.

---

## 11. Detailed Explanation

### Verification methods

1. **Infrastructure verification**: `terraform output` to check output values
2. **Function verification**: invoke the FunctionGraph function manually and check the return value
3. **Pipeline verification**: check pipeline status in the CodeArts console
4. **Notification verification**: check whether the SMN topic received notification messages
5. **Log verification**: view execution logs in the LTS console

### Troubleshooting

| Problem | Possible cause | Resolution |
|------|---------|---------|
| Function invocation timeout | ECS instance not responding | Check instance status and network connectivity |
| SMN notification not received | No subscribers on the topic | Add a subscription endpoint in the SMN console |
| Pipeline not triggered | Code repository not linked | Check the CodeArts pipeline source configuration |
| Empty instance query | Tags do not match | Check whether ECS instance tags are correct |

### Extension guide

- **Add a new environment**: add a new build task and approval stage in `scripts/setup_pipeline.sh`
- **Customize patch commands**: modify the patch dictionary in `src/patch.json`
- **Integrate monitoring alerts**: add a CES alarm rule to monitor patch execution metrics
- **Support multiple regions**: add provider aliases in Terraform for multi-region deployment
- **Containerized deployment**: replace ECS with CCE nodes and use kubectl to execute patch commands

---

## 12. Dependencies

- Terraform >= 1.5
- huaweicloud Terraform Provider ~> 1.70
- hcloud CLI
- Python 3.9+ (FunctionGraph runtime)
- SSH client (remote command execution)

### References

- [Architecture](docs/architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Terraform HuaweiCloud Provider](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [FunctionGraph Developer Guide](https://support.huaweicloud.com/functiongraph/)
- [CodeArts Pipeline](https://support.huaweicloud.com/codepipeline/)
- [OBS Object Storage](https://support.huaweicloud.com/obs/)

---

## 13. FAQ / Troubleshooting

### FAQ

### Q: The FunctionGraph function cannot connect to the ECS instance?

Check the following:
1. Is the FunctionGraph function configured with a VPC and subnet
2. Does the security group allow SSH (port 22) access
3. Is the ECS instance's SSH service running normally
4. Are the SSH keys configured correctly

### Q: How to roll back after a patch execution failure?

An IMS image backup is created before every patch execution; restore the instance from the image backup:
1. Find the backup image in the IMS console
2. Create a new instance from the backup image
3. Replace the original instance

### Q: How to add a new patch command?

Edit `src/patch.json` and add a new entry to the `patch` dictionary:
```json
"3": ["yum install nginx -y"]
```

---

## 14. Contributing

Issues and pull requests are welcome. Please ensure:
1. Code passes the existing tests
2. Terraform configuration passes `terraform validate`
3. No new external dependencies are introduced

---

## 15. License

MIT No Attribution - see [LICENSE](LICENSE).

---

## 16. Contact / Maintainers
| Item | Content |
|---|---|
| **Creator** | [dgc-git](https://github.com/dgc-git) |
| **Maintainer** | [dgc-git](https://github.com/dgc-git) |
| **Contact** | GitHub Issues / PR (see [Section 14](#14-contributing)) |
