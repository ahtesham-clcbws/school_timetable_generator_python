# scheduler/core/conflict.py
from typing import Dict, List, Tuple
from .models import Period

class TeacherAvailabilityTracker:
    """
    Manages teacher availability windows across all classes.
    Treats teachers as individual persons with continuous time constraints.
    """
    def __init__(self):
        # teacher_id -> day -> list of (start_min, end_min, period_id)
        self.busy_windows: Dict[int, Dict[str, List[Tuple[int, int, int]]]] = {}

    def is_available(self, teacher_id: int, day: str, start_min: int, end_min: int) -> bool:
        if teacher_id not in self.busy_windows or day not in self.busy_windows[teacher_id]:
            return True
        
        for b_start, b_end, _ in self.busy_windows[teacher_id][day]:
            # Detect overlap: max(start1, start2) < min(end1, end2)
            if max(start_min, b_start) < min(end_min, b_end):
                return False
        return True

    def mark_busy(self, teacher_id: int, day: str, start_min: int, end_min: int, period_id: int):
        if teacher_id not in self.busy_windows:
            self.busy_windows[teacher_id] = {}
        if day not in self.busy_windows[teacher_id]:
            self.busy_windows[teacher_id][day] = []
        
        self.busy_windows[teacher_id][day].append((start_min, end_min, period_id))

    def mark_free(self, teacher_id: int, day: str, period_id: int):
        if teacher_id in self.busy_windows and day in self.busy_windows[teacher_id]:
            self.busy_windows[teacher_id][day] = [
                w for w in self.busy_windows[teacher_id][day] if w[2] != period_id
            ]

    def get_free_windows(self, teacher_id: int, day: str, day_start: int, day_end: int) -> List[Tuple[int, int]]:
        """Identify available 'holes' in a teacher's schedule."""
        if teacher_id not in self.busy_windows or day not in self.busy_windows[teacher_id]:
            return [(day_start, day_end)]

        busy = sorted(self.busy_windows[teacher_id][day])
        free = []
        current = day_start
        
        for b_start, b_end, _ in busy:
            if b_start > current:
                free.append((current, b_start))
            current = max(current, b_end)
            
        if current < day_end:
            free.append((current, day_end))
            
        return free
