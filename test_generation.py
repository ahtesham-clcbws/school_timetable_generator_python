# test_generation.py
import json
import logging
from scheduler.api.handlers import TimetableHandler
from scheduler.core.engine import TimetableEngine

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def run_test():
    with open('tgs_payload.json', 'r') as f:
        laravel_data = json.load(f)
    
    classes = TimetableHandler.parse_payload(laravel_data)
    engine = TimetableEngine(classes)
    
    success = engine.schedule_all()
    timetable = TimetableHandler.format_response(engine)
    
    # Calculate stats
    total_requested = 0
    total_assigned = 0
    remaining_by_subject = {}
    
    for cid, cdata in classes.items():
        for lid, lesson in cdata.lessons.items():
            total_requested += lesson.original_taught_per_week
            total_assigned += (lesson.original_taught_per_week - lesson.taught_per_week)
            if lesson.taught_per_week > 0:
                remaining_by_subject[f"Class {cid} - Subj {lesson.subject_id}"] = lesson.taught_per_week
                
    print("\n--- RESULTS BEFORE CODE CHANGES ---")
    print(f"Status: {'SUCCESS' if success else 'PARTIAL'}")
    print(f"Total Requested Lessons: {total_requested}")
    print(f"Total Assigned Lessons: {total_assigned}")
    print(f"Assign %: {total_assigned / total_requested * 100:.2f}%")
    print("\nRemaining / Unassigned Lessons:")
    for key, val in remaining_by_subject.items():
        print(f"  {key}: {val} remaining")

if __name__ == '__main__':
    run_test()
