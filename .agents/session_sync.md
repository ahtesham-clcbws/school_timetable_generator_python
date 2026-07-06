# Session Sync

- **Goal:** Restrict Yoga/Games from the 1st period and exclude it from the Class Teacher 1st period preference.
- **Status:** COMPLETED.
  * Added hard constraint in engine.py (assign[(cid, lid, first_pid)] == 0) to prevent Yoga/Games (subject_id = 17) from being scheduled in the 1st normal period of any day.
  * Excluded subject_id == 17 from the list of active variables used to calculate Class Teacher 1st period preference rewards and soft-lock violation penalties.
  * Re-generated timetable for school 2 successfully (445 periods assigned).
