# test_alternative.py
import json
import logging
from scheduler.api.handlers import TimetableHandler
from scheduler.core.engine import TimetableEngine

logging.basicConfig(level=logging.INFO)
logging.getLogger('TimetableEngine').setLevel(logging.WARNING)

class_names = {
    1: "Nur", 2: "KG", 3: "Class I", 4: "Class II", 5: "Class III",
    6: "Class IV", 7: "Class V", 8: "Class VI", 9: "Class VII",
    10: "Class VIII", 11: "Class IX", 12: "Class X"
}

def run_test():
    with open('school2_payload.json', 'r') as f:
        laravel_data = json.load(f)
    
    # Alternative 1: Assign Teacher 85 to Arabic (Subject 6) for Nursery (1) and KG (2)
    for c in laravel_data:
        if c['class_id'] in {1, 2}:
            for l in c['lessons']:
                if l['subject_id'] == 6:
                    l['teacher_id'] = 85
                    
    classes = TimetableHandler.parse_payload(laravel_data)
    engine = TimetableEngine(classes)
    
    success = engine.schedule_all()
    
    print("\n========================================================================")
    print("           REPORT WITH ARABIC IN NUR/KG ASSIGNED TO TEACHER 85           ")
    print("========================================================================")
    print(f"{'Class Name':<15} | {'Available Slots':<15} | {'Requested Lessons':<18} | {'Assigned Lessons':<18} | {'Allocation %':<12}")
    print("-" * 88)
    
    total_slots = 0
    total_requested = 0
    total_assigned = 0
    
    for cid, cdata in sorted(classes.items()):
        name = class_names.get(cid, f"Class {cid}")
        slots = len(cdata.periods)
        requested = sum(l.original_taught_per_week for l in cdata.lessons.values())
        assigned = sum(1 for p in cdata.periods.values() if p.assigned_lesson_id is not None)
        
        pct = (assigned / slots * 100) if slots > 0 else 0.0
        print(f"{name:<15} | {slots:<15} | {requested:<18} | {assigned:<18} | {pct:>11.2f}%")
        
        total_slots += slots
        total_requested += requested
        total_assigned += assigned
        
    print("-" * 88)
    total_pct = (total_assigned / total_slots * 100) if total_slots > 0 else 0.0
    print(f"{'TOTAL':<15} | {total_slots:<15} | {total_requested:<18} | {total_assigned:<18} | {total_pct:>11.2f}%")
    print("========================================================================\n")
    
    print("Remaining / Unassigned Lessons:")
    for cid, cdata in sorted(classes.items()):
        name = class_names.get(cid, f"Class {cid}")
        for lid, lesson in cdata.lessons.items():
            if lesson.taught_per_week > 0:
                print(f"  {name}: Subject {lesson.subject_id} has {lesson.taught_per_week} remaining (Requested: {lesson.original_taught_per_week})")

if __name__ == '__main__':
    run_test()
