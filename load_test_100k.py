#!/usr/bin/env python3
"""Smart OCR服务的10万并发负载测试脚本。

该脚本用于测试服务在极高并发负载下的性能表现，包括：
- 10万个并发OCR请求
- 详细的性能指标统计
- 错误分析和成功率计算
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    """单个请求的测试结果。"""

    request_id: int
    status_code: int
    duration_ms: float
    success: bool
    error: str | None = None


@dataclass
class LoadTestStats:
    """负载测试的统计信息。"""

    total_requests: int
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_seconds: float = 0.0
    min_response_time_ms: float = float("inf")
    max_response_time_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    median_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    qps: float = 0.0
    error_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def calculate_statistics(self, results: List[LoadTestResult]):
        """根据测试结果计算统计指标。

        参数:
            results: 所有请求的结果列表
        """
        self.successful_requests = sum(1 for r in results if r.success)
        self.failed_requests = sum(1 for r in results if not r.success)

        response_times = [r.duration_ms for r in results if r.success]

        if response_times:
            self.min_response_time_ms = min(response_times)
            self.max_response_time_ms = max(response_times)
            self.avg_response_time_ms = sum(response_times) / len(response_times)

            sorted_times = sorted(response_times)
            n = len(sorted_times)
            median_index = n // 2
            percentile_95_index = int(0.95 * (n - 1)) if n > 1 else 0
            percentile_99_index = int(0.99 * (n - 1)) if n > 1 else 0

            self.median_response_time_ms = sorted_times[median_index]
            self.p95_response_time_ms = sorted_times[percentile_95_index]
            self.p99_response_time_ms = sorted_times[percentile_99_index]

        if self.total_duration_seconds > 0:
            self.qps = self.total_requests / self.total_duration_seconds

        for result in results:
            if not result.success and result.error:
                self.error_distribution[result.error] += 1

    def print_summary(self):
        """打印测试结果摘要。"""
        print("\n" + "=" * 80)
        print("10万并发负载测试结果摘要")
        print("=" * 80)
        print(f"\n【总体统计】")
        print(f"  总请求数:        {self.total_requests:,}")
        print(f"  成功请求数:      {self.successful_requests:,}")
        print(f"  失败请求数:      {self.failed_requests:,}")
        print(f"  成功率:          {(self.successful_requests / self.total_requests * 100):.2f}%")
        print(f"  总耗时:          {self.total_duration_seconds:.2f} 秒")
        print(f"  QPS:             {self.qps:.2f} 请求/秒")

        print(f"\n【响应时间统计】")
        print(f"  最小响应时间:    {self.min_response_time_ms:.2f} ms")
        print(f"  最大响应时间:    {self.max_response_time_ms:.2f} ms")
        print(f"  平均响应时间:    {self.avg_response_time_ms:.2f} ms")
        print(f"  中位数响应时间:  {self.median_response_time_ms:.2f} ms")
        print(f"  P95 响应时间:    {self.p95_response_time_ms:.2f} ms")
        print(f"  P99 响应时间:    {self.p99_response_time_ms:.2f} ms")

        if self.error_distribution:
            print(f"\n【错误分布】")
            for error_type, count in sorted(
                self.error_distribution.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                print(f"  {error_type}: {count:,} 次")

        print("\n" + "=" * 80 + "\n")


class LoadTester:
    """10万并发负载测试器。"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        total_requests: int = 100_000,
        concurrency: int = 1_000,
        timeout: float = 60.0,
    ):
        """初始化负载测试器。

        参数:
            base_url: OCR服务的基础URL
            total_requests: 要发送的总请求数
            concurrency: 同时进行的并发请求数
            timeout: 单个请求的超时时间（秒）
        """
        self.base_url = base_url
        self.total_requests = total_requests
        self.concurrency = concurrency
        self.timeout = timeout
        self.test_image_url = "https://images.unsplash.com/photo-1546410531-bb4caa6b424d"

    async def _send_single_request(
        self, client: httpx.AsyncClient, request_id: int
    ) -> LoadTestResult:
        """发送单个OCR请求并记录结果。

        参数:
            client: HTTP客户端实例
            request_id: 请求序号

        返回:
            包含请求结果的LoadTestResult对象
        """
        start_time = time.perf_counter()
        try:
            response = await client.post(
                f"{self.base_url}/v1/ocr",
                json={"image_url": self.test_image_url},
                timeout=self.timeout,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000

            return LoadTestResult(
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=(response.status_code == 200),
                error=None if response.status_code == 200 else f"HTTP {response.status_code}",
            )
        except httpx.TimeoutException:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return LoadTestResult(
                request_id=request_id,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error="Timeout",
            )
        except httpx.ConnectError as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return LoadTestResult(
                request_id=request_id,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error=f"Connection Error: {type(exc).__name__}",
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return LoadTestResult(
                request_id=request_id,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error=f"Exception: {type(exc).__name__}",
            )

    async def _run_batch(
        self, client: httpx.AsyncClient, start_id: int, batch_size: int
    ) -> List[LoadTestResult]:
        """并发执行一批请求。

        参数:
            client: HTTP客户端实例
            start_id: 批次起始请求ID
            batch_size: 批次大小

        返回:
            该批次所有请求的结果列表
        """
        tasks = [
            self._send_single_request(client, start_id + i)
            for i in range(batch_size)
        ]
        return await asyncio.gather(*tasks)

    async def run(self) -> LoadTestStats:
        """执行完整的负载测试。

        返回:
            包含所有性能指标的统计结果
        """
        logger.info(
            f"开始10万并发负载测试 - 总请求数: {self.total_requests:,}, 并发数: {self.concurrency}"
        )

        stats = LoadTestStats(total_requests=self.total_requests)
        all_results: List[LoadTestResult] = []

        test_start_time = time.time()

        async with httpx.AsyncClient() as client:
            num_batches = (self.total_requests + self.concurrency - 1) // self.concurrency
            logger.info(f"将分为 {num_batches} 批次执行")

            for batch_idx in range(num_batches):
                start_id = batch_idx * self.concurrency
                remaining = self.total_requests - start_id
                batch_size = min(self.concurrency, remaining)

                logger.info(
                    f"执行第 {batch_idx + 1}/{num_batches} 批次 "
                    f"(请求 {start_id + 1} - {start_id + batch_size})"
                )

                batch_results = await self._run_batch(client, start_id, batch_size)
                all_results.extend(batch_results)

                success_count = sum(1 for r in batch_results if r.success)
                logger.info(
                    f"批次完成 - 成功: {success_count}/{batch_size}, "
                    f"累计完成: {len(all_results)}/{self.total_requests}"
                )

        test_end_time = time.time()
        stats.total_duration_seconds = test_end_time - test_start_time

        logger.info("所有请求已完成，正在计算统计信息...")
        stats.calculate_statistics(all_results)

        return stats


async def main():
    """主入口函数。"""
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║          Smart OCR 服务 - 10万并发负载测试                    ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    tester = LoadTester(
        base_url="http://localhost:8000",
        total_requests=100_000,
        concurrency=1_000,
        timeout=60.0,
    )

    try:
        stats = await tester.run()
        stats.print_summary()

        if stats.successful_requests / stats.total_requests < 0.95:
            logger.warning("警告: 成功率低于95%，服务可能无法正常处理高并发负载")
        else:
            logger.info("✅ 负载测试成功完成")

    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as exc:
        logger.exception(f"负载测试失败: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
