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
        
        # Override Nursery (1) and KG (2) lesson teachers to be their Class Teacher only if not already assigned
        for cid, cdata in self.classes.items():
            if cid in {1, 2}:
                ct_id = cdata.class_teacher_id
                if ct_id:
                    for lesson in cdata.lessons.values():
                        if not lesson.teacher_id:
                            lesson.teacher_id = ct_id
                        
        model = cp_model.CpModel()
        
        # 1. Define Variables
        # assign[(class_id, lesson_id, period_id)] = BoolVar
        assign = {}
        
        for cid, cdata in self.classes.items():
            for lid, lesson in cdata.lessons.items():
                for pid, period in cdata.periods.items():
                    assign[(cid, lid, pid)] = model.NewBoolVar(f'assign_{cid}_{lid}_{pid}')

        # Objective Terms collection
        objective_terms = []

        # Flexible teacher assignments (Yoga/Games: 17, PBL: 15, and GSP: 14)
        use_ct_var = {}
        is_ct_active = {}
        is_orig_active = {}
        
        for cid, cdata in self.classes.items():
            ct_id = cdata.class_teacher_id
            for lid, lesson in cdata.lessons.items():
                is_flexible = lesson.subject_id in {14, 15, 17} and ct_id is not None and lesson.teacher_id != ct_id
                if is_flexible:
                    # Variable: 1 if we assign the class teacher to this lesson, 0 if original teacher
                    use_ct = model.NewBoolVar(f'use_ct_{cid}_{lid}')
                    use_ct_var[(cid, lid)] = use_ct
                    # Prefer assigning class teacher
                    objective_terms.append(150 * use_ct)
                    
                    for pid in cdata.periods.keys():
                        # CT teaches if assign is 1 and use_ct is 1
                        is_ct = model.NewBoolVar(f'is_ct_{cid}_{lid}_{pid}')
                        model.Add(is_ct <= assign[(cid, lid, pid)])
                        model.Add(is_ct <= use_ct)
                        model.Add(is_ct >= assign[(cid, lid, pid)] + use_ct - 1)
                        is_ct_active[(cid, lid, pid)] = is_ct
                        
                        # Orig teacher teaches if assign is 1 and use_ct is 0
                        is_orig = model.NewBoolVar(f'is_orig_{cid}_{lid}_{pid}')
                        model.Add(is_orig <= assign[(cid, lid, pid)])
                        model.Add(is_orig <= use_ct.Not())
                        model.Add(is_orig >= assign[(cid, lid, pid)] + use_ct.Not() - 1)
                        is_orig_active[(cid, lid, pid)] = is_orig

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
            ct_id = cdata.class_teacher_id
            for lid, lesson in cdata.lessons.items():
                is_flexible = lesson.subject_id in {14, 15, 17} and ct_id is not None and lesson.teacher_id != ct_id
                for pid, period in cdata.periods.items():
                    day = period.day
                    if is_flexible:
                        if ct_id:
                            teacher_day_vars[(ct_id, day)].append((period, is_ct_active[(cid, lid, pid)]))
                        if lesson.teacher_id:
                            teacher_day_vars[(lesson.teacher_id, day)].append((period, is_orig_active[(cid, lid, pid)]))
                    else:
                        teacher_id = lesson.teacher_id
                        if teacher_id:
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

        # Constraint D: Weekly Loads (Hard limits based on user-defined min/max limits)
        for cid, cdata in self.classes.items():
            for lid, lesson in cdata.lessons.items():
                actual_load = sum(assign[(cid, lid, pid)] for pid in cdata.periods.keys())
                
                t_min = min(lesson.min_per_week, lesson.max_per_week)
                t_max = lesson.max_per_week
                
                # Hard constraints enforcing user-defined limits
                model.Add(actual_load <= t_max)
                model.Add(actual_load >= t_min)
                
                # Objective: Maximize assigned periods to hit max limits where possible
                objective_terms.append(100 * actual_load)

        # Constraint D2: Yoga/Games (17) should not be in the first period of any day
        for cid, cdata in self.classes.items():
            for day in self.days:
                pids_for_day = cdata.periods_by_day.get(day, [])
                if not pids_for_day:
                    continue
                sorted_pids = sorted(pids_for_day, key=lambda pid: cdata.periods[pid].start_min)
                normal_pids = sorted_pids
                if normal_pids:
                    first_pid = normal_pids[0]
                    for lid, lesson in cdata.lessons.items():
                        if lesson.subject_id == 17:
                            model.Add(assign[(cid, lid, first_pid)] == 0)

        # Constraint E: Class Teacher First-Period Preference (Very Strong Soft Constraint)
        for cid, cdata in self.classes.items():
            class_teacher = cdata.class_teacher_id
            if not class_teacher:
                continue

            # Build list of active variables per period indicating if the class teacher teaches at that period
            ct_active_vars_at_period = {}
            for pid in cdata.periods.keys():
                vars_list = []
                for lid, lesson in cdata.lessons.items():
                    if lesson.subject_id == 17:
                        continue # Do not apply Class Teacher first period constraint to Yoga/Games
                    is_flexible = lesson.subject_id in {14, 15, 17} and class_teacher is not None and lesson.teacher_id != class_teacher
                    if is_flexible:
                        vars_list.append(is_ct_active[(cid, lid, pid)])
                    elif lesson.teacher_id == class_teacher:
                        vars_list.append(assign[(cid, lid, pid)])
                ct_active_vars_at_period[pid] = vars_list
                
            for day in self.days:
                if day.lower() == 'saturday':
                    continue  # Exclude Saturdays from Class Teacher first period constraint
                pids_for_day = cdata.periods_by_day.get(day, [])
                if not pids_for_day:
                    continue
                sorted_pids = sorted(pids_for_day, key=lambda pid: cdata.periods[pid].start_min)
                first_pid = sorted_pids[0]
                
                # is_ct_first is 1 if class teacher lesson is assigned to first period of the day
                is_ct_first = model.NewBoolVar(f'is_ct_first_{cid}_{day}')
                model.Add(is_ct_first <= sum(ct_active_vars_at_period[first_pid]))
                
                # Extremely high reward for first period Class Teacher
                objective_terms.append(50000 * is_ct_first)
                
                # Soft lock implication: penalize if class teacher teaches later periods on 'day' but NOT the first period
                for pid in sorted_pids[1:]:
                    for active_var in ct_active_vars_at_period[pid]:
                        violation = model.NewBoolVar(f'ct_first_viol_{cid}_{day}_{pid}_{active_var.Name()}')
                        model.Add(violation >= active_var - is_ct_first)
                        objective_terms.append(-25000 * violation)

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
                    
                    # Update teacher if flexible and class teacher was chosen
                    ct_id = cdata.class_teacher_id
                    is_flexible = lesson.subject_id in {14, 15, 17} and ct_id is not None and lesson.teacher_id != ct_id
                    if is_flexible and solver.Value(use_ct_var[(cid, lid)]) == 1:
                        lesson.teacher_id = ct_id
                    
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
