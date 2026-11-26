#!/usr/bin/env python3
"""
补丁自动化主脚本

在 CodeArts Build 中执行，负责：
1. 从 OBS 读取补丁配置（patch.json）
2. 按标签查询目标 ECS 实例
3. 创建 IMS 镜像备份
4. 调用 FunctionGraph 函数在目标实例上执行补丁命令
5. 通过 SMN 发送执行结果通知
6. 更新黄金镜像引用
"""

import json
import os
import time
import argparse
import subprocess
from datetime import datetime


class PatchManager:
    """补丁管理器：协调整个补丁流程"""

    def __init__(self, env, appcomponent, topic_urn, region="cn-north-4"):
        self.env = env
        self.appcomponent = appcomponent or "default"
        self.topic_urn = topic_urn
        self.region = region
        self.filename = "patch.json"

        # hcloud CLI 命令前缀
        self.hcloud = "hcloud"

        # 读取补丁配置
        with open(self.filename) as f:
            data = json.load(f)
            self.patch = data["patch"]
            self.apply_all = data["ApplyAllPatches"]
            self.deploy_from = data["deploy_from"]

    def send_notification(self, subject, message):
        """通过 SMN 发送通知"""
        print(f"==== 发送 SMN 通知: {subject} ====")
        cmd = [
            self.hcloud, "SMN", "PublishMessage",
            "--topic_urn", self.topic_urn,
            "--subject", subject,
            "--message", str(message),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"SMN 发送失败: {result.stderr}")
        except Exception as e:
            print(f"SMN 发送异常: {e}")

    def get_instances(self):
        """按标签查询目标 ECS 实例"""
        print(f"==== 查询环境 {self.env} 的目标实例 ====")
        cmd = [
            self.hcloud, "ECS", "ListServersDetails",
            "--tags", f"application-environment={self.env};automated-patching=True",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise Exception(f"查询实例失败: {result.stderr}")
            import json as _json
            resp = _json.loads(result.stdout)
            servers = resp.get("servers", [])
            running = [s for s in servers if s.get("status") == "ACTIVE"]
            print(f"==== 找到 {len(running)} 个运行中的实例 ====")
            return running
        except Exception as e:
            raise Exception(f"查询实例异常: {e}")

    def create_image_backup(self, instance_id, instance_name):
        """创建 IMS 镜像备份"""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        image_name = f"backup-{instance_name}-{self.env}-{timestamp}"
        print(f"==== 创建镜像备份: {image_name} (实例 {instance_id}) ====")

        cmd = [
            self.hcloud, "IMS", "CreateImage",
            "--name", image_name,
            "--instance_id", instance_id,
            "--description", f"Pre-patch backup for {instance_id}",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise Exception(f"创建镜像失败: {result.stderr}")
            import json as _json
            resp = _json.loads(result.stdout)
            image_id = resp.get("image_id", "")
            print(f"==== 镜像创建中: {image_id} ====")
            return image_id
        except Exception as e:
            raise Exception(f"创建镜像异常: {e}")

    def run_command_on_instance(self, instance_id, command):
        """通过 FunctionGraph 在实例上执行命令"""
        print(f"==== 在实例 {instance_id} 上执行: {command} ====")

        fgs_urn = os.environ.get("RUN_CMD_FUNCTION_URN", "")
        if not fgs_urn:
            print("警告: 未设置 RUN_CMD_FUNCTION_URN，跳过命令执行")
            return True

        payload = json.dumps({
            "instance_id": instance_id,
            "command": command,
        })

        cmd = [
            self.hcloud, "FunctionGraph", "InvokeFunction",
            "--function_urn", fgs_urn,
            "--body", payload,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"命令执行失败: {result.stderr}")
                return False
            import json as _json
            resp = _json.loads(result.stdout)
            success = resp.get("result", {}).get("success", False)
            output = resp.get("result", {}).get("output", "")
            print(f"==== 执行结果: {'成功' if success else '失败'} ====")
            if output:
                print(f"==== 输出: {output[:500]} ====")
            return success
        except Exception as e:
            print(f"命令执行异常: {e}")
            return False

    def apply_patches(self):
        """执行补丁流程"""
        try:
            instances = self.get_instances()
            if not instances:
                print("==== 未找到目标实例 ====")
                return

            for instance in instances:
                instance_id = instance["id"]
                instance_name = instance.get("name", instance_id)
                print(f"\n==== 处理实例: {instance_name} ({instance_id}) ====")

                # 1. 创建镜像备份
                self.create_image_backup(instance_id, instance_name)

                # 2. 执行补丁命令
                patches_to_apply = []
                if self.apply_all:
                    patches_to_apply = list(self.patch.keys())
                else:
                    patches_to_apply = [
                        p for p in self.patch.keys()
                        if int(p) >= int(self.deploy_from)
                    ]

                for patch_num in patches_to_apply:
                    command = self.patch[patch_num][0]
                    print(f"==== 执行补丁 #{patch_num}: {command} ====")
                    success = self.run_command_on_instance(instance_id, command)
                    if not success:
                        subject = f"补丁执行失败: 实例 {instance_id}"
                        message = (
                            f"时间: {datetime.now()}\n"
                            f"实例: {instance_id}\n"
                            f"环境: {self.env}\n"
                            f"补丁编号: {patch_num}\n"
                            f"命令: {command}"
                        )
                        self.send_notification(subject, message)
                        return

            print("\n==== 所有补丁执行完成 ====")
            self.send_notification(
                f"补丁执行完成: 环境 {self.env}",
                f"环境 {self.env} 的所有实例补丁执行完成，时间: {datetime.now()}"
            )

        except Exception as e:
            raise Exception(f"补丁执行异常: {e}")

    def update_golden_image(self):
        """更新黄金镜像"""
        try:
            instances = self.get_instances()
            if not instances:
                print("==== 未找到目标实例 ====")
                return

            instance = instances[0]
            instance_id = instance["id"]
            instance_name = instance.get("name", instance_id)

            # 创建黄金镜像
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
            image_name = f"golden-image-{self.env}-{timestamp}"
            print(f"==== 创建黄金镜像: {image_name} ====")

            cmd = [
                self.hcloud, "IMS", "CreateImage",
                "--name", image_name,
                "--instance_id", instance_id,
                "--description", "Golden image after patching",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise Exception(f"创建黄金镜像失败: {result.stderr}")

            import json as _json
            resp = _json.loads(result.stdout)
            image_id = resp.get("image_id", "")

            # 等待镜像可用
            print("==== 等待镜像变为可用状态 ====")
            for _ in range(30):
                time.sleep(10)
                check_cmd = [
                    self.hcloud, "IMS", "ShowImage",
                    "--image_id", image_id,
                ]
                check_result = subprocess.run(
                    check_cmd, capture_output=True, text=True, timeout=30
                )
                if check_result.returncode == 0:
                    check_resp = _json.loads(check_result.stdout)
                    status = check_resp.get("image", {}).get("status", "")
                    print(f"==== 镜像状态: {status} ====")
                    if status == "active":
                        break

            # 通知新黄金镜像可用
            self.send_notification(
                "新黄金镜像可用",
                f"黄金镜像已创建: {image_name} (ID: {image_id})\n"
                f"请更新部署配置以使用新镜像"
            )
            print(f"==== 黄金镜像创建完成: {image_id} ====")

        except Exception as e:
            raise Exception(f"更新黄金镜像异常: {e}")


def main():
    parser = argparse.ArgumentParser(description="补丁管理自动化脚本")
    parser.add_argument("-environment", required=True, help="目标环境")
    parser.add_argument("-appcomponent", help="应用组件")
    parser.add_argument("-updateGoldenImage", help="是否更新黄金镜像")
    parser.add_argument("-topicarn", required=True, help="SMN 主题 URN")
    parser.add_argument("-region", default="cn-north-4", help="区域")
    args = parser.parse_args()

    manager = PatchManager(
        env=args.environment,
        appcomponent=args.appcomponent,
        topic_urn=args.topicarn,
        region=args.region,
    )

    if args.updateGoldenImage == "True":
        manager.update_golden_image()
    else:
        manager.apply_patches()


if __name__ == "__main__":
    main()
