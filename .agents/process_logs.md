# Process Logs

- **2026-07-02 (Update 25):** Added Yoga/Games (subject_id = 17) restriction:
  * Implemented hard constraint in `engine.py` preventing Yoga/Games from being scheduled in the 1st normal period of any day.
  * Excluded Yoga/Games from triggering class teacher 1st period preferences or violations in `engine.py`.
  * Re-generated timetable for school ID 2.
