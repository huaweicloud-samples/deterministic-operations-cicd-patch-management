#!/usr/bin/env python3
"""
远程命令执行函数 - FunctionGraph Handler

接收实例 ID 和命令，通过 SSH 在目标 ECS 实例上执行命令。
通过 SSH 在目标实例上执行远程命令。

Event 结构:
{
    "instance_id": "xxx-xxx-xxx",
    "command": "yum update -y"
}

返回:
{
    "success": true/false,
    "output": "命令输出",
    "error": "错误信息（如有）"
}
"""

import json
import os
import subprocess
import time


def get_instance_info(instance_id, region):
    """通过 hcloud CLI 查询实例信息"""
    cmd = [
        "hcloud", "ECS", "ShowServer",
        "--server_id", instance_id,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        resp = json.loads(result.stdout)
        server = resp.get("server", {})
        return {
            "id": server.get("id", ""),
            "name": server.get("name", ""),
            "private_ip": server.get("addresses", {}).get("vpc", [{}])[0].get("addr", ""),
            "status": server.get("status", ""),
        }
    except Exception:
        return None


def execute_via_ssh(host, command, timeout=120):
    """通过 SSH 执行远程命令"""
    ssh_user = os.environ.get("SSH_USER", "root")
    ssh_key_path = os.environ.get("SSH_KEY_PATH", "/tmp/ssh_key")

    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-i", ssh_key_path,
        f"{ssh_user}@{host}",
        command,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"命令执行超时（{timeout}秒）",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
        }


def handler(event, context):
    """FunctionGraph 入口函数"""
    try:
        if isinstance(event, str):
            event = json.loads(event)

        instance_id = event.get("instance_id", "")
        command = event.get("command", "")
        region = os.environ.get("REGION", "cn-north-4")

        if not instance_id or not command:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": "缺少必要参数: instance_id 或 command",
                }),
            }

        # 查询实例信息
        instance_info = get_instance_info(instance_id, region)
        if not instance_info:
            return {
                "statusCode": 404,
                "body": json.dumps({
                    "success": False,
                    "error": f"未找到实例: {instance_id}",
                }),
            }

        private_ip = instance_info["private_ip"]
        if not private_ip:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": f"实例 {instance_id} 无私有 IP",
                }),
            }

        # 通过 SSH 执行命令
        result = execute_via_ssh(private_ip, command)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": result["success"],
                "output": result["output"],
                "error": result["error"],
                "instance_id": instance_id,
                "instance_name": instance_info["name"],
                "command": command,
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
            }),
        }
