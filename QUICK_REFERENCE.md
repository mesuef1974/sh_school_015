# Quick Reference Guide - Database Improvements

## 🚀 Quick Start Commands

### Daily Operations

```bash
# Check for data quality issues and fix them automatically
python manage.py check_data_quality --fix

# View detailed quality report
python manage.py check_data_quality --verbose

# Clean and normalize data
python manage.py cleanup_data

# Check cache performance
python manage.py manage_cache --stats
```

### Weekly Maintenance

```bash
# Archive old attendance records (run every Sunday)
python manage.py archive_old_attendance --days 365

# Clear cache to force refresh
python manage.py manage_cache --clear
python manage.py manage_cache --warm
```

### After Deployments

```bash
# Apply database migrations
python manage.py migrate

# Warm up cache
python manage.py manage_cache --warm

# Verify data quality
python manage.py check_data_quality
```

---

## 📊 Performance Monitoring

### Check Cache Hit Rates

```bash
python manage.py manage_cache --stats
```

**What to look for:**
- Hit rate > 75% = Good
- Hit rate > 85% = Excellent
- Hit rate < 60% = Consider adjusting cache timeouts

### Monitor Database Size

```bash
# PostgreSQL command (run in psql)
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

### Archive Old Data

When `attendance_record` table exceeds 100,000 rows:
```bash
python manage.py archive_old_attendance --days 365 --dry-run  # Preview first
python manage.py archive_old_attendance --days 365             # Execute
```

---

## 🔧 Troubleshooting

### Cache Issues

**Problem:** Data not updating in real-time
```bash
# Clear specific cache
python manage.py manage_cache --clear-cache attendance

# Or clear all caches
python manage.py manage_cache --clear
```

**Problem:** Redis connection error
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"

# Check Redis URL in .env
echo $REDIS_URL  # Should be redis://127.0.0.1:6379/0
```

### Data Quality Issues

**Problem:** Students without classes
```bash
python manage.py check_data_quality --verbose
# Review output, then assign classes manually or via admin
```

**Problem:** Incorrect class counts
```bash
python manage.py cleanup_data  # This fixes class counts automatically
```

**Problem:** Invalid phone/ID formats
```bash
python manage.py cleanup_data  # Normalizes format
python manage.py check_data_quality --fix  # Validates and reports
```

### Performance Issues

**Problem:** Slow queries
1. Check if indexes are applied:
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'school_attendancerecord';
   ```

2. Clear and warm cache:
   ```bash
   python manage.py manage_cache --clear
   python manage.py manage_cache --warm
   ```

3. Archive old data:
   ```bash
   python manage.py archive_old_attendance --days 365
   ```

**Problem:** High memory usage
- Check cache size in Redis:
  ```bash
  redis-cli info memory
  ```
- If > 1GB, consider reducing cache timeouts in settings_base.py

---

## 💡 Code Examples

### Using Cache in Views

```python
from school.cache_utils import cache_attendance_data, get_current_term

# Option 1: Use decorator
@cache_attendance_data(timeout=600)
def get_student_attendance(student_id, date):
    return AttendanceRecord.objects.filter(
        student_id=student_id,
        date=date
    ).select_related('subject', 'teacher')

# Option 2: Use pre-built functions
term = get_current_term()  # Cached automatically
```

### Manual Cache Management

```python
from django.core.cache import caches
from school.cache_utils import make_cache_key

# Get cache
cache = caches['attendance']

# Set value
key = make_cache_key('student_attendance', student_id=123, date='2025-10-21')
cache.set(key, data, timeout=600)

# Get value
data = cache.get(key)

# Delete specific key
cache.delete(key)
```

### Using Validators

```python
from school.validators import (
    validate_saudi_national_id,
    validate_phone_number,
    validate_age_for_grade
)

# In a view or serializer
try:
    validate_saudi_national_id(national_id)
    validate_phone_number(phone)
    validate_age_for_grade(age=15, grade=10)
except ValidationError as e:
    return Response({'error': str(e)}, status=400)
```

---

## 📋 Cheat Sheet

### Cache Timeouts

| Cache Name | Timeout | Use Case |
|------------|---------|----------|
| `default` | 5 min | General queries |
| `long_term` | 1 hour | Classes, subjects, terms |
| `attendance` | 10 min | Attendance records |

### Index Names

| Index Name | Fields | Purpose |
|------------|--------|---------|
| `att_date_status_idx` | date, status | Daily reports |
| `att_term_student_idx` | term, student, status | Student history |
| `att_teacher_sched_idx` | teacher, date, period | Teacher schedule |
| `att_class_sched_idx` | classroom, date, period | Class schedule |
| `att_date_locked_idx` | date, locked | Locked records query |
| `att_student_term_idx` | student, term | Student term summary |

### Management Commands

| Command | Purpose | Frequency |
|---------|---------|-----------|
| `check_data_quality` | Validate data | Daily |
| `cleanup_data` | Normalize formats | Weekly |
| `archive_old_attendance` | Archive old records | Monthly |
| `manage_cache --stats` | Monitor performance | Daily |
| `manage_cache --clear` | Reset cache | As needed |
| `manage_cache --warm` | Preload cache | After deploy |

---

## 🔍 Common Queries

### Find Students Without Classes

```sql
SELECT id, sid, full_name
FROM school_student
WHERE class_fk_id IS NULL AND active = TRUE;
```

### Check Cache Hit Rate

```bash
python manage.py manage_cache --stats | grep "Hit rate"
```

### Count Records by Status

```sql
SELECT status, COUNT(*)
FROM school_attendancerecord
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY status;
```

### Find Duplicate Students

```sql
SELECT full_name, COUNT(*) as count
FROM school_student
GROUP BY full_name
HAVING COUNT(*) > 1;
```

---

## 🎯 Best Practices

### DO ✅
- Run `check_data_quality` daily before generating reports
- Archive attendance data annually
- Clear cache after bulk data updates
- Warm cache after deployments
- Use dry-run mode before destructive operations
- Monitor cache hit rates weekly

### DON'T ❌
- Don't delete data directly (use soft delete)
- Don't skip migrations
- Don't clear cache during peak hours
- Don't modify cache settings without testing
- Don't archive data less than 1 year old
- Don't ignore data quality warnings

---

## 📞 Support

### Error Messages

**"Cache connection refused"**
→ Start Redis: `redis-server` or check if running

**"Index name too long"**
→ Already fixed in migration 0034

**"Duplicate key violation"**
→ Run `check_data_quality` to find duplicates

**"Foreign key constraint"**
→ Check if referenced record exists or use soft delete

---

## 📚 Related Files

- **Settings:** `backend/core/settings_base.py` (lines 183-221)
- **Cache Utils:** `backend/school/cache_utils.py`
- **Validators:** `backend/school/validators.py`
- **Models:** `backend/school/models.py`
- **Base Models:** `backend/school/models_base.py`
- **Enhanced Models:** `backend/school/models_enhanced.py`

---

## 🎓 Training Resources

### For Developers
1. Read `DATABASE_IMPROVEMENTS_SUMMARY.md` for complete overview
2. Review `DATABASE_ANALYSIS_REPORT.md` for detailed analysis
3. Study code examples in `cache_utils.py`
4. Test commands in staging environment first

### For System Administrators
1. Set up daily cron job for `check_data_quality --fix`
2. Set up weekly cron job for `archive_old_attendance`
3. Monitor cache hit rates in monitoring dashboard
4. Set up alerts for data quality issues

### For Database Administrators
1. Monitor index usage with pg_stat_user_indexes
2. Analyze slow queries with pg_stat_statements
3. Monitor table sizes and plan archiving schedule
4. Review backup strategy for archived data

---

**Last Updated:** 2025-10-21
**Version:** 1.0
**Maintainer:** Development Team