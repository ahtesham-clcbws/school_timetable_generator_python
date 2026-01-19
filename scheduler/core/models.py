# scheduler/core/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

class TimeUtils:
    @staticmethod
    def to_minutes(time_str: str) -> int:
        """Convert 'HH:MM' or 'HH:MM:SS' to minutes from midnight."""
        parts = list(map(int, time_str.split(':')))
        return parts[0] * 60 + parts[1]

@dataclass
class Period:
    id: int
    class_id: int
    day: str
    start_time: str
    end_time: str
    start_min: int = 0
    end_min: int = 0
    assigned_lesson_id: Optional[int] = None

    def __post_init__(self):
        self.start_min = TimeUtils.to_minutes(self.start_time)
        self.end_min = TimeUtils.to_minutes(self.end_time)

@dataclass
class Lesson:
    id: int
    class_id: int
    subject_id: int
    teacher_id: int
    taught_per_week: int
    is_back_to_back: bool
    original_taught_per_week: int = 0
    assigned_period_ids: List[int] = field(default_factory=list)
    daily_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def __post_init__(self):
        self.original_taught_per_week = self.taught_per_week
        from collections import defaultdict
        self.daily_count = defaultdict(int)

@dataclass
class ClassData:
    id: int
    name: str
    periods: Dict[int, Period] = field(default_factory=dict)
    lessons: Dict[int, Lesson] = field(default_factory=dict)
    periods_by_day: Dict[str, List[int]] = field(default_factory=dict)

    def sort_periods(self):
        for day in self.periods_by_day:
            self.periods_by_day[day].sort(key=lambda pid: self.periods[pid].start_min)
