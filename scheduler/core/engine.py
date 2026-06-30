# scheduler/core/engine.py
import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict
from ortools.sat.python import cp_model
from .models import ClassData, Lesson, Period

logger = logging.getLogger('TimetableEngine')

class TimetableEngine:
    def __init__(self, classes: Dict[int, ClassData]):
        self.classes = classes
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        self.assignment_count = 0
        self.backtrack_count = 0  # Kept for compatibility with response stats

    def schedule_all(self) -> bool:
        """Main entry point for scheduling using Google OR-Tools CP-SAT."""
        logger.info("Initializing Google OR-Tools CP-SAT scheduler with advanced preferences")
        model = cp_model.CpModel()
        
        # 1. Define Variables
        # assign[(class_id, lesson_id, period_id)] = BoolVar
        assign = {}
        
        for cid, cdata in self.classes.items():
            for lid, lesson in cdata.lessons.items():
                for pid, period in cdata.periods.items():
                    assign[(cid, lid, pid)] = model.NewBoolVar(f'assign_{cid}_{lid}_{pid}')

        # 2. Add Constraints

        # Constraint A: At most one lesson per period slot for each class
        for cid, cdata in self.classes.items():
            for pid, period in cdata.periods.items():
                model.Add(
                    sum(assign[(cid, lid, pid)] for lid in cdata.lessons.keys()) <= 1
                )

        # Constraint B: No teacher clash (overlapping times for the same teacher on the same day)
        teacher_day_vars = defaultdict(list)
        for cid, cdata in self.classes.items():
            for lid, lesson in cdata.lessons.items():
                teacher_id = lesson.teacher_id
                if not teacher_id:
                    continue
                for pid, period in cdata.periods.items():
                    day = period.day
                    teacher_day_vars[(teacher_id, day)].append((period, assign[(cid, lid, pid)]))

        # Add pairwise conflict constraints for overlapping times
        for (teacher_id, day), vars_list in teacher_day_vars.items():
            n = len(vars_list)
            for i in range(n):
                p1, var1 = vars_list[i]
                for j in range(i + 1, n):
                    p2, var2 = vars_list[j]
                    # Overlap detection: max(start_min1, start_min2) < min(end_min1, end_min2)
                    if max(p1.start_min, p2.start_min) < min(p1.end_min, p2.end_min):
                        model.Add(var1 + var2 <= 1)

        # Objective Terms collection
        objective_terms = []

        # Constraint D: Weekly Loads (Soft Constraints & Deviations)
        # Core Subject IDs: 1 (English), 2 (Math), 3 (EVS/Science), 4 (Hindi), 5 (Urdu), 6 (Arabic), 18 (SST)
        # Minor Subject IDs: 11 (Computer), 12 (Art & Craft), 14 (GSP), 16 (Playtime), 17 (Yoga/Games)
        core_subjects = {1, 2, 3, 4, 5, 6, 18}
        minor_subjects = {11, 12, 14, 16, 17}

        for cid, cdata in self.classes.items():
            for lid, lesson in cdata.lessons.items():
                target = lesson.taught_per_week
                actual_load = sum(assign[(cid, lid, pid)] for pid in cdata.periods.keys())
                
                if lesson.subject_id in core_subjects:
                    if target == 8:
                        t_min, t_max = 6, 8
                    elif target == 4:
                        t_min, t_max = 4, 6
                    elif target == 6:
                        t_min, t_max = 4, 7
                    elif target == 5:
                        t_min, t_max = 4, 7
                    elif target == 7:
                        t_min, t_max = 5, 8
                    else:
                        t_min = max(0, target - 1)
                        t_max = target + 1
                    
                    model.Add(actual_load <= t_max)

                    # Absolute deviation: dev = |actual_load - target|
                    # If actual_load is in [t_min, t_max], we want to minimize distance to target
                    dev = model.NewIntVar(0, target, f'dev_{cid}_{lid}')
                    model.Add(dev >= actual_load - target)
                    model.Add(dev >= target - actual_load)
                    
                    objective_terms.append(100 * actual_load)
                    objective_terms.append(-10 * dev)
                    
                elif lesson.subject_id in minor_subjects:
                    # Allowed: [1, target] if target > 0. Lowering allowed, but not below 1.
                    model.Add(actual_load <= target)
                    if target > 0:
                        minor_viol = model.NewBoolVar(f'minor_viol_{cid}_{lid}')
                        model.Add(actual_load >= 1 - minor_viol)
                        objective_terms.append(-50 * minor_viol)
                    else:
                        model.Add(actual_load == 0)
                    
                    objective_terms.append(100 * actual_load)
                    
                else:
                    # Other subjects (soft equality constraint: max target, but don't crash if less)
                    model.Add(actual_load <= target)
                    dev = model.NewIntVar(0, target, f'dev_other_{cid}_{lid}')
                    model.Add(dev >= target - actual_load)
                    objective_terms.append(100 * actual_load)
                    objective_terms.append(-10 * dev)

        # Constraint E: Class Teacher First-Period Preference (70% Target / Soft Constraint)
        for cid, cdata in self.classes.items():
            class_teacher = cdata.class_teacher_id
            if not class_teacher:
                continue
                
            ct_lessons = [lid for lid, l in cdata.lessons.items() if l.teacher_id == class_teacher]
            if not ct_lessons:
                continue
                
            for day in self.days:
                pids_for_day = cdata.periods_by_day.get(day, [])
                if not pids_for_day:
                    continue
                sorted_pids = sorted(pids_for_day, key=lambda pid: cdata.periods[pid].start_min)
                first_pid = sorted_pids[0]
                
                # is_ct_first is 1 if class teacher lesson is assigned to first period of the day
                is_ct_first = model.NewBoolVar(f'is_ct_first_{cid}_{day}')
                model.Add(is_ct_first <= sum(assign[(cid, lid, first_pid)] for lid in ct_lessons))
                
                # Soft lock implication: penalize if class teacher teaches later periods on 'day' but NOT the first period
                for pid in sorted_pids[1:]:
                    for lid in ct_lessons:
                        violation = model.NewBoolVar(f'ct_first_viol_{cid}_{day}_{pid}_{lid}')
                        # violation is 1 if class teacher teaches pid but is_ct_first is 0
                        model.Add(violation >= assign[(cid, lid, pid)] - is_ct_first)
                        objective_terms.append(-80 * violation)
                
                objective_terms.append(300 * is_ct_first)

        # Constraint F: Daily count limits (soft constraints, allows breaking is_back_to_back)
        for cid, cdata in self.classes.items():
            for lid, lesson in cdata.lessons.items():
                periods_by_day = defaultdict(list)
                for pid, period in cdata.periods.items():
                    periods_by_day[period.day].append(pid)
                
                for day, pids in periods_by_day.items():
                    daily_sum = sum(assign[(cid, lid, pid)] for pid in pids)
                    limit = 2 if lesson.is_back_to_back else 1
                    
                    # soft limit penalty: violation = max(0, daily_sum - limit)
                    violation = model.NewIntVar(0, len(pids), f'violation_{cid}_{lid}_{day}')
                    model.Add(violation >= daily_sum - limit)
                    
                    objective_terms.append(-20 * violation)

        # Set Objective Function: Maximize scheduled lessons & teacher placement, minimize deviations
        model.Maximize(sum(objective_terms))

        # 3. Solve the Model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 20.0  # Set safety timeout
        
        status = solver.Solve(model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # 4. Map the solution back to the engine structures
            self.assignment_count = 0
            for (cid, lid, pid), var in assign.items():
                if solver.Value(var) == 1:
                    cdata = self.classes[cid]
                    period = cdata.periods[pid]
                    lesson = cdata.lessons[lid]
                    
                    period.assigned_lesson_id = lid
                    lesson.taught_per_week -= 1
                    lesson.daily_count[period.day] += 1
                    lesson.assigned_period_ids.append(pid)
                    self.assignment_count += 1
            
            # Check if we fully satisfied target lesson loads
            total_target = sum(l.taught_per_week for c in self.classes.values() for l in c.lessons.values())
            success = (total_target == 0)
            
            logger.info(f"Timetable solved successfully. Status: {solver.StatusName(status)}, Success: {success}")
            return success
        else:
            logger.warning(f"Solver failed to find a feasible solution. Status: {solver.StatusName(status)}")
            return False
