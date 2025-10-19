Teacher Attendance: fixed heights for top boxes

This page now fixes the heights of the two top boxes:
- glass-header ("معلومات اليوم" container)
- chips-card (the KPIs chips container)

How to adjust heights
- Open TeacherAttendance.vue
- In the first <style scoped> block, variables are defined on .page-grid:
  .page-grid { --top-card-h: 88px; --chips-card-h: 88px; }

Change the pixel values to suit desired design.

Notes
- Content inside these boxes is vertically centered and overflow is hidden to preserve the exact height.
- The change is scoped to this component only and does not affect other pages.
- No global page scroll is introduced; header/footer remain fixed.