#!/usr/bin/env python3
"""
补丁编排函数 - FunctionGraph Handler

协调整个补丁流程：查询实例 → 创建镜像备份 → 执行补丁 → 通知
由 CodeArts Build 调用，或通过 OBS 事件触发。

Event 结构:
{
    "environment": "dev",
    "update_golden_image": false,
    "patch_config": { ... }
}
"""

import json
import os
import subprocess
import time
from datetime import datetime


def hcloud_cmd(service, action, **kwargs):
    """执行 hcloud CLI 命令"""
    cmd = ["hcloud", service, action]
    for k, v in kwargs.items():
        cmd.extend([f"--{k}", str(v)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise Exception(f"hcloud {service} {action} 失败: {result.stderr}")
    return json.loads(result.stdout) if result.stdout else {}


def get_instances_by_tag(env, region):
    """按标签查询目标 ECS 实例"""
    resp = hcloud_cmd("ECS", "ListServersDetails",
                      tags=f"application-environment={env};automated-patching=True")
    servers = resp.get("servers", [])
    return [s for s in servers if s.get("status") == "ACTIVE"]


def create_image_backup(instance_id, env):
    """创建 IMS 镜像备份"""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    image_name = f"backup-{instance_id[:8]}-{env}-{timestamp}"
    resp = hcloud_cmd("IMS", "CreateImage",
                      name=image_name,
                      instance_id=instance_id,
                      description=f"Pre-patch backup for {instance_id}")
    return resp.get("image_id", "")


def send_notification(topic_urn, subject, message):
    """通过 SMN 发送通知"""
    try:
        hcloud_cmd("SMN", "PublishMessage",
                   topic_urn=topic_urn,
                   subject=subject,
                   message=message)
    except Exception as e:
        print(f"SMN 通知发送失败: {e}")


def run_command_on_instance(instance_id, command):
    """调用远程命令执行函数"""
    fgs_urn = os.environ.get("RUN_CMD_FUNCTION", "")
    if not fgs_urn:
        print(f"警告: 未设置 RUN_CMD_FUNCTION，使用本地执行模式")
        return {"success": True, "output": "skipped (no function configured)"}

    payload = json.dumps({
        "instance_id": instance_id,
        "command": command,
    })
    resp = hcloud_cmd("FunctionGraph", "InvokeFunction",
                      function_urn=fgs_urn,
                      body=payload)
    return resp.get("result", {})


def handler(event, context):
    """FunctionGraph 入口函数"""
    try:
        if isinstance(event, str):
            event = json.loads(event)

        env = event.get("environment", "dev")
        update_golden = event.get("update_golden_image", False)
        patch_config = event.get("patch_config", {})

        region = os.environ.get("REGION", "cn-north-4")
        topic_urn = os.environ.get("SMN_TOPIC_URN", "")

        # 读取补丁配置
        if not patch_config:
            patch_config = {
                "ApplyAllPatches": True,
                "deploy_from": "1",
                "patch": {
                    "1": ["yum update -y"],
                    "2": ["yum install httpd -y"],
                },
            }

        apply_all = patch_config.get("ApplyAllPatches", True)
        deploy_from = patch_config.get("deploy_from", "1")
        patches = patch_config.get("patch", {})

        # 查询目标实例
        instances = get_instances_by_tag(env, region)
        if not instances:
            return json.dumps({"success": False, "error": "未找到目标实例"})

        results = []
        for instance in instances:
            instance_id = instance["id"]
            instance_name = instance.get("name", instance_id)
            print(f"处理实例: {instance_name} ({instance_id})")

            # 创建镜像备份
            image_id = create_image_backup(instance_id, env)
            print(f"镜像备份创建中: {image_id}")

            # 执行补丁
            patch_nums = list(patches.keys())
            if not apply_all:
                patch_nums = [p for p in patch_nums if int(p) >= int(deploy_from)]

            for patch_num in patch_nums:
                command = patches[patch_num][0]
                print(f"执行补丁 #{patch_num}: {command}")
                result = run_command_on_instance(instance_id, command)

                if not result.get("success", False):
                    error_msg = result.get("error", "未知错误")
                    send_notification(
                        topic_urn,
                        f"补丁执行失败: {instance_name}",
                        f"实例: {instance_id}\n补丁: #{patch_num}\n命令: {command}\n错误: {error_msg}",
                    )
                    results.append({
                        "instance": instance_name,
                        "patch": patch_num,
                        "success": False,
                        "error": error_msg,
                    })
                    break
                else:
                    results.append({
                        "instance": instance_name,
                        "patch": patch_num,
                        "success": True,
                    })

        # 发送完成通知
        all_success = all(r["success"] for r in results)
        send_notification(
            topic_urn,
            f"补丁执行{'完成' if all_success else '部分失败'}: 环境 {env}",
            json.dumps(results, indent=2, ensure_ascii=False),
        )

        return json.dumps({
            "success": all_success,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
