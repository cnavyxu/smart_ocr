from __future__ import annotations

"""任务进度跟踪器模块，负责管理OCR任务的执行状态与统计信息。"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from smart_ocr.models import TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """单个任务的运行时信息。"""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    total_pages: int = 1
    processed_pages: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """将任务信息转换为字典格式。

        Returns:
            Dict[str, Any]: 包含任务详细信息的字典表示
        """
        elapsed = (self.end_time or time.time()) - self.start_time
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": round(self.progress, 2),
            "total_pages": self.total_pages,
            "processed_pages": self.processed_pages,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": elapsed,
            "result": self.result,
            "error": self.error,
        }


class TaskTracker:
    """OCR任务的运行状态跟踪器。"""

    def __init__(self, max_history: int = 10_000):
        """初始化任务跟踪器。

        Args:
            max_history: 需要保留的历史任务数量上限
        """
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = asyncio.Lock()
        self._max_history = max_history
        logger.info("任务跟踪器已初始化，最大历史记录数: %s", max_history)

    def create_task(self, total_pages: int = 1) -> str:
        """创建一个新的任务并返回任务ID。

        Args:
            total_pages: 任务预计需要处理的页数

        Returns:
            str: 新创建任务的唯一标识符
        """
        task_id = str(uuid.uuid4())
        sanitized_pages = max(total_pages, 1)
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            total_pages=sanitized_pages,
        )
        self._tasks[task_id] = task_info
        logger.debug("创建新任务 %s，总页数 %s", task_id, sanitized_pages)
        return task_id

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        processed_pages: Optional[int] = None,
        total_pages: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """更新指定任务的运行状态。

        Args:
            task_id: 目标任务的唯一标识符
            status: 更新后的任务状态
            processed_pages: 当前已处理的页数
            total_pages: 任务总页数，若提供将覆盖原值
            result: 任务完成后的结果数据
            error: 任务失败时的错误信息
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                logger.warning("尝试更新不存在的任务: %s", task_id)
                return

            task.status = status

            if total_pages is not None:
                task.total_pages = max(total_pages, 1)

            if processed_pages is not None:
                task.processed_pages = max(min(processed_pages, task.total_pages), 0)

            progress_base = max(task.total_pages, 1)
            task.progress = min(
                100.0, (task.processed_pages / progress_base) * 100
            )

            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.end_time = time.time()

            if result is not None:
                task.result = result

            if error is not None:
                task.error = error

            logger.debug(
                "任务 %s 状态已更新为 %s，进度 %.2f%%",
                task_id,
                status.value,
                task.progress,
            )

            if len(self._tasks) > self._max_history:
                await self._cleanup_old_tasks()

    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询指定任务的详情。

        Args:
            task_id: 任务唯一标识符

        Returns:
            Optional[Dict[str, Any]]: 若任务存在返回任务详情字典，否则返回None
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return task.to_dict()

    async def get_all_tasks(
        self,
        status_filter: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """返回任务列表。

        Args:
            status_filter: 状态过滤器，只返回指定状态的任务
            limit: 返回的最大任务数量

        Returns:
            List[Dict[str, Any]]: 任务信息字典列表
        """
        async with self._lock:
            tasks = list(self._tasks.values())

            if status_filter is not None:
                tasks = [task for task in tasks if task.status == status_filter]

            tasks.sort(key=lambda item: item.start_time, reverse=True)
            sliced = tasks[: max(limit, 0)]
            return [task.to_dict() for task in sliced]

    async def get_statistics(self) -> Dict[str, Any]:
        """获取任务执行的统计信息。

        Returns:
            Dict[str, Any]: 包含任务数量与成功率等指标的统计数据
        """
        async with self._lock:
            total = len(self._tasks)
            pending = sum(1 for task in self._tasks.values() if task.status == TaskStatus.PENDING)
            processing = sum(
                1 for task in self._tasks.values() if task.status == TaskStatus.PROCESSING
            )
            completed = sum(
                1 for task in self._tasks.values() if task.status == TaskStatus.COMPLETED
            )
            failed = sum(1 for task in self._tasks.values() if task.status == TaskStatus.FAILED)

            success_rate = (completed / total * 100) if total > 0 else 0.0

            return {
                "total_tasks": total,
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "success_rate": round(success_rate, 2),
            }

    async def _cleanup_old_tasks(self) -> None:
        """清理过期的历史任务，避免占用过多内存。"""
        completed_tasks = [
            (task_id, task)
            for task_id, task in self._tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]

        if len(completed_tasks) <= self._max_history // 2:
            return

        completed_tasks.sort(key=lambda item: item[1].end_time or 0)
        removable = len(completed_tasks) - (self._max_history // 2)
        for task_id, _ in completed_tasks[:removable]:
            self._tasks.pop(task_id, None)
            logger.debug("清理过期任务: %s", task_id)


_tracker_instance: Optional[TaskTracker] = None


def get_task_tracker() -> TaskTracker:
    """获取任务跟踪器的全局单例。

    Returns:
        TaskTracker: 任务跟踪器实例
    """
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = TaskTracker()
    return _tracker_instance
