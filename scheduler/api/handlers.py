# scheduler/api/handlers.py
from typing import List, Dict, Any
from ..core.models import ClassData, Period, Lesson
from ..core.engine import TimetableEngine
import logging

logger = logging.getLogger('TimetableAPI')

class TimetableHandler:
    @staticmethod
    def parse_payload(laravel_data: List[Dict[str, Any]]) -> Dict[int, ClassData]:
        classes = {}
        for c_data in laravel_data:
            cid = c_data['class_id']
            c_obj = ClassData(id=cid, name=c_data.get('class_name', f'Class {cid}'))
            
            # Periods
            for i, p_data in enumerate(c_data.get('periods', [])):
                pid = cid * 1000 + i + 1
                period = Period(
                    id=pid,
                    class_id=cid,
                    day=p_data['period_day'],
                    start_time=p_data['start_time'],
                    end_time=p_data['end_time']
                )
                c_obj.periods[pid] = period
                day = period.day
                if day not in c_obj.periods_by_day:
                    c_obj.periods_by_day[day] = []
                c_obj.periods_by_day[day].append(pid)
            
            c_obj.sort_periods()

            # Lessons
            for i, l_data in enumerate(c_data.get('lessons', [])):
                lid = cid * 1000 + i + 1
                lesson = Lesson(
                    id=lid,
                    class_id=cid,
                    subject_id=l_data['subject_id'],
                    teacher_id=l_data['teacher_id'],
                    taught_per_week=l_data['taught_per_week'],
                    is_back_to_back=l_data['is_back_to_back']
                )
                c_obj.lessons[lid] = lesson
            
            classes[cid] = c_obj
        return classes

    @staticmethod
    def format_response(engine: TimetableEngine) -> Dict[str, Any]:
        timetable = {'days': {}, 'classes': {}}
        
        # Day-wise
        for day in engine.days:
            day_schedule = {}
            for cid, cdata in engine.classes.items():
                day_periods = []
                for pid in cdata.periods_by_day.get(day, []):
                    period = cdata.periods[pid]
                    assigned = None
                    if period.assigned_lesson_id:
                        lesson = cdata.lessons[period.assigned_lesson_id]
                        assigned = {
                            'lesson_id': lesson.id,
                            'subject_id': lesson.subject_id,
                            'teacher_id': lesson.teacher_id,
                            'class_id': cid
                        }
                    
                    day_periods.append({
                        'period_id': pid,
                        'start_time': period.start_time,
                        'end_time': period.end_time,
                        'assigned_lesson': assigned
                    })
                day_schedule[cid] = day_periods
            timetable['days'][day] = day_schedule

        # Class-wise stats
        for cid, cdata in engine.classes.items():
            class_info = {
                'total_periods': len(cdata.periods),
                'assigned_periods': sum(1 for p in cdata.periods.values() if p.assigned_lesson_id),
                'lessons': {}
            }
            for lid, lesson in cdata.lessons.items():
                class_info['lessons'][lid] = {
                    'subject_id': lesson.subject_id,
                    'teacher_id': lesson.teacher_id,
                    'sessions_assigned': lesson.original_taught_per_week - lesson.taught_per_week,
                    'sessions_remaining': lesson.taught_per_week
                }
            timetable['classes'][cid] = class_info

        return timetable
