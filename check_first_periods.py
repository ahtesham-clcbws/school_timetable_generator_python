# check_first_periods.py
import json
from scheduler.api.handlers import TimetableHandler
from scheduler.core.engine import TimetableEngine

class_names = {
    1: "Nur", 2: "KG", 3: "Class I", 4: "Class II", 5: "Class III",
    6: "Class IV", 7: "Class V", 8: "Class VI", 9: "Class VII",
    10: "Class VIII", 11: "Class IX", 12: "Class X"
}

def run_test():
    with open('school2_payload.json', 'r') as f:
        laravel_data = json.load(f)
    
    classes = TimetableHandler.parse_payload(laravel_data)
    engine = TimetableEngine(classes)
    
    success = engine.schedule_all()
    
    print("\nFirst Period Class Teacher Assignment Check (M-F):")
    print("-" * 65)
    print(f"{'Class Name':<12} | {'Day':<10} | {'First Period Subject':<22} | {'CT Assigned?':<10}")
    print("-" * 65)
    
    for cid, cdata in sorted(classes.items()):
        ct_id = cdata.class_teacher_id
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            pids = cdata.periods_by_day.get(day, [])
            if not pids:
                continue
            sorted_pids = sorted(pids, key=lambda pid: cdata.periods[pid].start_min)
            first_pid = sorted_pids[0]
            period = cdata.periods[first_pid]
            
            assigned_lid = period.assigned_lesson_id
            if assigned_lid is not None:
                lesson = cdata.lessons[assigned_lid]
                # Check if lesson's teacher matches the class teacher
                is_ct = (lesson.teacher_id == ct_id)
                subj_name = f"Subj {lesson.subject_id}"
                print(f"{class_names.get(cid, f'Class {cid}'):<12} | {day:<10} | {subj_name:<22} | {str(is_ct):<10}")
            else:
                print(f"{class_names.get(cid, f'Class {cid}'):<12} | {day:<10} | {'Empty':<22} | False")

if __name__ == '__main__':
    run_test()
