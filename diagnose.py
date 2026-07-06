# diagnose.py
import json
import logging
from scheduler.api.handlers import TimetableHandler
from scheduler.core.engine import TimetableEngine
from ortools.sat.python import cp_model

logging.basicConfig(level=logging.INFO)

def run_test():
    with open('tgs_payload.json', 'r') as f:
        laravel_data = json.load(f)
    
    classes = TimetableHandler.parse_payload(laravel_data)
    
    model = cp_model.CpModel()
    assign = {}
    for cid, cdata in classes.items():
        for lid, lesson in cdata.lessons.items():
            for pid, period in cdata.periods.items():
                assign[(cid, lid, pid)] = model.NewBoolVar(f'assign_{cid}_{lid}_{pid}')

    # Constraint A: At most one lesson per period slot for each class
    for cid, cdata in classes.items():
        for pid, period in cdata.periods.items():
            model.Add(
                sum(assign[(cid, lid, pid)] for lid in cdata.lessons.keys()) <= 1
            )

    # Constraint B: No teacher clash
    from collections import defaultdict
    teacher_day_vars = defaultdict(list)
    for cid, cdata in classes.items():
        for lid, lesson in cdata.lessons.items():
            teacher_id = lesson.teacher_id
            if not teacher_id:
                continue
            for pid, period in cdata.periods.items():
                day = period.day
                teacher_day_vars[(teacher_id, day)].append((period, assign[(cid, lid, pid)]))

    for (teacher_id, day), vars_list in teacher_day_vars.items():
        n = len(vars_list)
        for i in range(n):
            p1, var1 = vars_list[i]
            for j in range(i + 1, n):
                p2, var2 = vars_list[j]
                if max(p1.start_min, p2.start_min) < min(p1.end_min, p2.end_min):
                    model.Add(var1 + var2 <= 1)

    # Let's check if the hard constraints themselves are infeasible!
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)
    print(f"Basic constraints only: status is {solver.StatusName(status)}")
    print(solver.ResponseStats())

if __name__ == '__main__':
    run_test()
