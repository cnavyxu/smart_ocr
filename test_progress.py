#!/usr/bin/env python3
"""测试任务进度跟踪功能的示例脚本。

该脚本演示如何使用任务进度跟踪API：
- 提交OCR任务并获取任务ID
- 轮询查询任务执行进度
- 获取任务统计信息
"""
import asyncio
import time

import httpx


async def test_task_progress():
    """测试任务进度跟踪功能。"""
    print("=" * 60)
    print("任务进度跟踪功能测试")
    print("=" * 60)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n1. 提交OCR任务...")
        response = await client.post(
            f"{base_url}/v1/ocr",
            json={"image_url": "https://images.unsplash.com/photo-1546410531-bb4caa6b424d"},
            params={"track_progress": True},
        )

        if response.status_code != 200:
            print(f"❌ 任务提交失败: {response.status_code}")
            print(response.text)
            return

        result = response.json()
        task_id = result.get("task_id")

        if not task_id:
            print("❌ 响应中没有task_id")
            return

        print(f"✅ 任务已提交，任务ID: {task_id}")
        print(f"   识别到 {result['text_count']} 个文本区域")
        print(f"   处理时间: {result['processing_time']:.3f} 秒")

        print(f"\n2. 查询任务进度...")
        progress_response = await client.get(f"{base_url}/v1/tasks/{task_id}")

        if progress_response.status_code == 200:
            progress = progress_response.json()
            print(f"✅ 任务状态: {progress['status']}")
            print(f"   进度: {progress['progress']:.1f}%")
            print(f"   已处理页数: {progress['processed_pages']}/{progress['total_pages']}")
            print(f"   运行时间: {progress['elapsed_time']:.3f} 秒")
        else:
            print(f"❌ 查询任务进度失败: {progress_response.status_code}")

        print(f"\n3. 获取任务统计信息...")
        stats_response = await client.get(f"{base_url}/v1/tasks/statistics")

        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"✅ 任务统计:")
            print(f"   总任务数: {stats['total_tasks']}")
            print(f"   待处理: {stats['pending']}")
            print(f"   处理中: {stats['processing']}")
            print(f"   已完成: {stats['completed']}")
            print(f"   失败: {stats['failed']}")
            print(f"   成功率: {stats['success_rate']:.2f}%")
        else:
            print(f"❌ 获取统计信息失败: {stats_response.status_code}")

        print(f"\n4. 获取所有任务列表（最近10个）...")
        tasks_response = await client.get(
            f"{base_url}/v1/tasks",
            params={"limit": 10},
        )

        if tasks_response.status_code == 200:
            tasks_data = tasks_response.json()
            print(f"✅ 找到 {tasks_data['count']} 个任务:")
            for idx, task in enumerate(tasks_data["tasks"][:5], 1):
                print(
                    f"   {idx}. ID: {task['task_id'][:8]}... "
                    f"状态: {task['status']} "
                    f"进度: {task['progress']:.1f}%"
                )
        else:
            print(f"❌ 获取任务列表失败: {tasks_response.status_code}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60 + "\n")


async def test_concurrent_with_progress():
    """测试多个并发任务的进度跟踪。"""
    print("\n" + "=" * 60)
    print("并发任务进度跟踪测试")
    print("=" * 60)

    base_url = "http://localhost:8000"
    num_tasks = 10

    print(f"\n提交 {num_tasks} 个并发OCR任务...")

    async def submit_task(client: httpx.AsyncClient, task_num: int) -> str | None:
        """提交单个任务并返回任务ID。"""
        try:
            response = await client.post(
                f"{base_url}/v1/ocr",
                json={"image_url": "https://images.unsplash.com/photo-1546410531-bb4caa6b424d"},
                params={"track_progress": True},
            )
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("task_id")
                print(f"✅ 任务 {task_num} 已提交，ID: {task_id[:8] if task_id else 'N/A'}...")
                return task_id
        except Exception as exc:
            print(f"❌ 任务 {task_num} 提交失败: {exc}")
        return None

    async with httpx.AsyncClient(timeout=60.0) as client:
        tasks = [submit_task(client, i + 1) for i in range(num_tasks)]
        task_ids = await asyncio.gather(*tasks)
        task_ids = [tid for tid in task_ids if tid]

        print(f"\n成功提交 {len(task_ids)} 个任务")

        if not task_ids:
            print("没有成功的任务，测试终止")
            return

        print("\n等待2秒后查询所有任务状态...")
        await asyncio.sleep(2)

        stats_response = await client.get(f"{base_url}/v1/tasks/statistics")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"\n当前系统统计:")
            print(f"  总任务数: {stats['total_tasks']}")
            print(f"  已完成: {stats['completed']}")
            print(f"  成功率: {stats['success_rate']:.2f}%")

    print("\n" + "=" * 60)
    print("并发测试完成！")
    print("=" * 60 + "\n")


async def main():
    """主入口函数。"""
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║          Smart OCR 服务 - 进度跟踪功能测试                    ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    await test_task_progress()
    await test_concurrent_with_progress()


if __name__ == "__main__":
    asyncio.run(main())
