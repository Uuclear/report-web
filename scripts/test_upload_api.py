#!/usr/bin/env python3
"""手动回归：上传单文件并轮询状态（需先启动后端 http://localhost:8080）"""
from pathlib import Path

import requests
import time

ROOT = Path(__file__).resolve().parent.parent


def test_upload():
    test_file = ROOT / "files_limis" / "IMG_20260403_174854.jpg"
    upload_url = "http://localhost:8080/api/upload/single"

    print("=" * 50)
    print("开始上传测试...")
    print(f"测试文件: {test_file}")
    print("=" * 50)

    with open(test_file, "rb") as f:
        response = requests.post(
            upload_url,
            files={"file": f},
            data={"source_type": "auto"},
            timeout=120,
        )

    print(f"上传响应状态码: {response.status_code}")
    print(f"上传响应内容: {response.text}")

    if response.status_code != 200:
        print("上传失败!")
        return

    result = response.json()
    file_id = result["file_id"]
    print(f"文件ID: {file_id}")

    print("\n开始轮询状态...")
    status_url = f"http://localhost:8080/api/upload/status/{file_id}"

    for i in range(30):
        time.sleep(1)
        status_response = requests.get(status_url, timeout=30)
        print(f"第{i + 1}次查询: 状态码={status_response.status_code}")

        if status_response.status_code == 200:
            status = status_response.json()
            print(f"  status={status['status']}")
            print(f"  message={status['message']}")

            if status["status"] in ("completed", "failed"):
                print("\n处理完成!")
                print("=" * 50)
                if status.get("data"):
                    print("识别结果:")
                    print(f"  报告编号: {status['data'].get('report_no')}")
                    print(f"  来源: {status['data'].get('source')}")
                    print(f"  信息: {status['data'].get('info', {})}")
                print("=" * 50)
                print("（若已配置 data.db，可在「结果查询」页或数据库中核对是否已落库）")
                break
        else:
            print(f"  错误: {status_response.text}")

    print("\n测试完成!")


if __name__ == "__main__":
    test_upload()
