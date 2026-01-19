# scheduler/core/engine.py
import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict
from .models import ClassData, Lesson, Period
from .conflict import TeacherAvailabilityTracker

logger = logging.getLogger('TimetableEngine')

class TimetableEngine:
    def __init__(self, classes: Dict[int, ClassData]):
        self.classes = classes
        self.lessons: Dict[int, Lesson] = {}
        for c in self.classes.values():
            self.lessons.update(c.lessons)
            
        self.teacher_tracker = TeacherAvailabilityTracker()
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        self.assignment_count = 0
        self.backtrack_count = 0

    def schedule_all(self) -> bool:
        """Main entry point for scheduling."""
        success = True
        for day in self.days:
            if not self.schedule_day(day):
                logger.warning(f"Failed to fully schedule {day}")
                success = False
        return success

    def schedule_day(self, day: str) -> bool:
        """Schedule all classes for a specific day."""
        # MRV: Sort classes by complexity (sessions / periods)
        sorted_classes = self._get_sorted_classes_for_day(day)
        
        day_success = True
        for class_id in sorted_classes:
            if not self.schedule_class_day(class_id, day):
                day_success = False
        return day_success

    def _get_sorted_classes_for_day(self, day: str) -> List[int]:
        class_complexity = []
        for cid, cdata in self.classes.items():
            avail_p = len([pid for pid in cdata.periods_by_day.get(day, []) 
                          if cdata.periods[pid].assigned_lesson_id is None])
            req_s = sum(min(2, l.taught_per_week) for l in cdata.lessons.values() if l.taught_per_week > 0)
            
            score = req_s / avail_p if avail_p > 0 else 999
            class_complexity.append((score, cid))
            
        class_complexity.sort(reverse=True)
        return [cid for _, cid in class_complexity]

    def schedule_class_day(self, class_id: int, day: str, depth: int = 0) -> bool:
        if depth > 100: return False
        
        cdata = self.classes[class_id]
        avail_periods = [pid for pid in cdata.periods_by_day.get(day, []) 
                        if cdata.periods[pid].assigned_lesson_id is None]
        
        if not avail_periods: return True

        for pid in avail_periods:
            period = cdata.periods[pid]
            # MRV: Get lessons for this class sorted by priority
            lessons = self._get_available_lessons_for_day(class_id, day)
            
            for lesson in lessons:
                if self._is_valid(lesson, period):
                    self._assign(lesson, period)
                    if self.schedule_class_day(class_id, day, depth + 1):
                        return True
                    self._unassign(lesson, period)
        
        return False

    def _is_valid(self, lesson: Lesson, period: Period) -> bool:
        # 1. Teacher busy? (Interval-based check)
        if not self.teacher_tracker.is_available(lesson.teacher_id, period.day, period.start_min, period.end_min):
            return False
            
        # 2. Back-to-back?
        if lesson.is_back_to_back:
            if lesson.daily_count[period.day] >= 2:
                return False
                
        return True

    def _assign(self, lesson: Lesson, period: Period):
        period.assigned_lesson_id = lesson.id
        lesson.taught_per_week -= 1
        lesson.daily_count[period.day] += 1
        lesson.assigned_period_ids.append(period.id)
        
        self.teacher_tracker.mark_busy(lesson.teacher_id, period.day, period.start_min, period.end_min, period.id)
        self.assignment_count += 1

    def _unassign(self, lesson: Lesson, period: Period):
        period.assigned_lesson_id = None
        lesson.taught_per_week += 1
        lesson.daily_count[period.day] -= 1
        if period.id in lesson.assigned_period_ids:
            lesson.assigned_period_ids.remove(period.id)
            
        self.teacher_tracker.mark_free(lesson.teacher_id, period.day, period.id)
        self.backtrack_count += 1

    def _get_available_lessons_for_day(self, class_id: int, day: str) -> List[Lesson]:
        cdata = self.classes[class_id]
        available = []
        for l in cdata.lessons.values():
            if l.taught_per_week > 0:
                # Basic availability check
                if l.is_back_to_back and l.daily_count[day] >= 2:
                    continue
                available.append(l)
        
        # Priority: Most sessions remaining, then back-to-back
        available.sort(key=lambda l: (-l.taught_per_week, l.is_back_to_back))
        return available
