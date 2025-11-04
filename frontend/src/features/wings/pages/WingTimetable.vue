<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
      <template #actions>
        <span class="d-inline-flex align-items-center gap-2 flex-wrap align-items-center">
          <span class="small text-muted" aria-live="polite">
            <template v-if="isToday">اليوم: {{ formattedDate }} • {{ liveTime }}</template>
            <template v-else>التاريخ: {{ formattedDate }}</template>
          </span>
        </span>
      </template>
    </WingPageHeader>

    <div class="auto-card p-3 d-flex align-items-center gap-2 flex-wrap toolbar-card">
      <span class="vr mx-2 d-none d-sm-block"></span>

      <div class="d-flex align-items-center gap-2 flex-wrap ms-auto toolbar-controls">
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:home-2-bold-duotone" />
          <label class="visually-hidden" for="wingSelect">اختر الجناح</label>
          <select
            id="wingSelect"
            aria-label="اختيار الجناح"
            class="form-select form-select-sm"
            v-model.number="wingId"
            @change="loadData"
          >
            <option :value="null" disabled>اختر الجناح</option>
            <option v-for="(name, id) in wingOptions" :key="id" :value="Number(id)">
              {{ name }}
            </option>
          </select>
        </div>
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:calendar-bold-duotone" />
          <label class="visually-hidden" for="tt-date-2">التاريخ</label>
          <DatePickerDMY
            :id="'tt-date-2'"
            :aria-label="'اختيار التاريخ'"
            inputClass="form-control form-control-sm"
            wrapperClass="m-0"
            v-model="dateStr"
            @change="loadData"
          />
        </div>
        <div class="btn-group btn-group-sm" role="group" aria-label="وضع العرض" style="display:none">
          <button type="button" class="btn" :class="mode === 'daily' ? 'btn-primary' : 'btn-outline-secondary'" @click="setMode('daily')">اليوم</button>
          <button type="button" class="btn" :class="mode === 'weekly' ? 'btn-primary' : 'btn-outline-secondary'" @click="setMode('weekly')">أسبوع</button>
        </div>
        <DsButton size="sm" variant="outline" icon="solar:printer-bold-duotone" @click="printPage" aria-label="طباعة الجدول">طباعة</DsButton>
        <DsButton size="sm" variant="outline" icon="solar:refresh-bold-duotone" :loading="loading" @click="loadData" aria-label="تحديث البيانات">تحديث</DsButton>
        <DsButton size="sm" variant="outline" :icon="paused ? 'solar:play-bold-duotone' : 'solar:pause-bold-duotone'" @click="toggleLive" :label="paused ? 'استئناف التحديث الحي' : 'إيقاف التحديث الحي'">{{ paused ? 'استئناف' : 'إيقاف' }}</DsButton>
        <span class="small text-muted" aria-live="polite">آخر تحديث: {{ lastUpdated || '—' }}</span>
        <div class="vr d-none d-sm-block"></div>
      </div>
    </div>

    <!-- Print-only header -->
    <div class="auto-card p-2 print-header" aria-hidden="true">
      <div class="d-flex align-items-center gap-2">
        <Icon icon="solar:printer-bold-duotone" />
        <div class="fw-bold">
          {{
            mode === "daily"
              ? "الجدول اليومي — " + formattedDate + " — " + dayNameAr(dateStr)
              : "الجدول الأسبوعي"
          }}
          <span v-if="wingLabel"> — {{ wingLabel }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="auto-card p-4 text-center">
      <Icon icon="solar:refresh-bold-duotone" class="animate-spin text-4xl" />
      <div class="text-muted mt-2 small">جاري تحميل الجدول...</div>
    </div>

    <div v-else-if="error" class="alert alert-danger">حدث خطأ أثناء التحميل: {{ error }}</div>

    <!-- Empty state -->
    <div v-else-if="isEmpty" class="auto-card p-4 text-center">
      <Icon icon="solar:inbox-line-bold-duotone" class="text-5xl mb-2" style="opacity: 0.4" />
      <div class="h6 mb-1">لا توجد بيانات للعرض</div>
      <div class="text-muted small" v-if="meta.reason === 'no_wing'">
        لا يوجد جناح مخصص لحسابك. عيّن نفسك كمشرف لجناح في لوحة الإدارة (Wing.supervisor).
      </div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_term'">
        لا يوجد فصل دراسي حالي (is_current=True). أنشئ فصلًا وحدده كحالي.
      </div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_classes'">
        لا توجد صفوف مرتبطة بهذا الجناح. اربط بعض الصفوف بالجناح.
      </div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_entries_today'">
        لا توجد حصص مجدولة لهذا اليوم ضمن الجناح/الفصل الدراسي الحالي.
      </div>
      <div class="text-muted small" v-else>تحقق من اختيار الجناح والتاريخ</div>
    </div>

    <!-- Daily view (Wing 3 Thursday grouped) -->
    <div v-else-if="mode === 'daily' && isWing3ThuGrouped" class="d-flex flex-column gap-4">
      <!-- Group: Secondary (10-1, 10-2) -->
      <div class="auto-card p-0 overflow-auto">
        <div class="p-3 d-flex align-items-center gap-2 border-bottom">
          <Icon icon="solar:calendar-date-bold-duotone" />
          <div class="fw-bold">الخميس — ثانوي (10-1 / 10-2)</div>
          <span class="ms-auto small text-muted">{{ classListSecondary.length }} فصل</span>
        </div>
        <div class="in-card-98">
          <div class="tt-daily-scroller">
            <table class="tt-daily-table" dir="rtl" aria-label="جدول يومي (ثانوي)">
              <colgroup>
                <col style="min-width: 120px" />
                <col v-for="tok in dailyHeaderTokensSecondary" :key="'cg-sec-'+String(tok)" style="min-width: 120px" />
              </colgroup>
              <thead>
                <tr>
                  <th class="th-sticky">الفصل</th>
                  <th v-for="tok in dailyHeaderTokensSecondary" :key="'ph-sec-'+String(tok)" class="resizable-th" :class="dailyHeaderClass(String(tok))">
                    <template v-if="isPeriodToken(String(tok))">حصة {{ periodNumFromToken(String(tok)) }}</template>
                    <template v-else>{{ headerLabel(String(tok)) }}</template>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cls in classListSecondary" :key="'sec-'+cls.id">
                  <th class="th-sticky">
                    <div class="hdr-line"><span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span></div>
                  </th>
                  <td v-for="tok in dailyHeaderTokensSecondary" :key="'sec-cell-'+cls.id+'-'+String(tok)" :class="dailyCellClass(String(tok))">
                    <template v-if="!isPeriodToken(String(tok))">
                      <div class="slot-cell">
                        <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                        <div class="slot-time" v-if="slotTimeForGroup('secondary', String(tok))">{{ fmtTime(slotTimeForGroup('secondary', String(tok))![0]) }} – {{ fmtTime(slotTimeForGroup('secondary', String(tok))![1]) }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <template v-if="dailyItemFor(cls.id, periodNumFromToken(String(tok)))">
                        <div class="period-cell" :style="{ backgroundColor: dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.color || '#f5f7fb' }">
                          <div class="cell-subject one-line">
                            <Icon v-if="subjectIcon(dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                            <span class="subject-name truncate-1">{{ dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                          </div>
                          <div class="cell-teacher one-line truncate-1">{{ dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.teacher_name || '—' }}</div>
                          <div class="cell-time small text-muted" v-if="timeRangeForGroup('secondary', periodNumFromToken(String(tok)))">
                            <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                            {{ timeRangeForGroup('secondary', periodNumFromToken(String(tok))) }}
                          </div>
                        </div>
                      </template>
                      <span v-else class="text-muted">—</span>
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Group: Grade 9 (2-4) -->
      <div class="auto-card p-0 overflow-auto">
        <div class="p-3 d-flex align-items-center gap-2 border-bottom">
          <Icon icon="solar:calendar-date-bold-duotone" />
          <div class="fw-bold">الخميس — تاسع (2 / 3 / 4)</div>
          <span class="ms-auto small text-muted">{{ classListG9.length }} فصل</span>
        </div>
        <div class="in-card-98">
          <div class="tt-daily-scroller">
            <table class="tt-daily-table" dir="rtl" aria-label="جدول يومي (تاسع 2-3-4)">
              <colgroup>
                <col style="min-width: 120px" />
                <col v-for="tok in dailyHeaderTokensG9" :key="'cg-g9-'+String(tok)" style="min-width: 120px" />
              </colgroup>
              <thead>
                <tr>
                  <th class="th-sticky">الفصل</th>
                  <th v-for="tok in dailyHeaderTokensG9" :key="'ph-g9-'+String(tok)" class="resizable-th" :class="dailyHeaderClass(String(tok))">
                    <template v-if="isPeriodToken(String(tok))">حصة {{ periodNumFromToken(String(tok)) }}</template>
                    <template v-else>{{ headerLabel(String(tok)) }}</template>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cls in classListG9" :key="'g9-'+cls.id">
                  <th class="th-sticky">
                    <div class="hdr-line"><span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span></div>
                  </th>
                  <td v-for="tok in dailyHeaderTokensG9" :key="'g9-cell-'+cls.id+'-'+String(tok)" :class="dailyCellClass(String(tok))">
                    <template v-if="!isPeriodToken(String(tok))">
                      <div class="slot-cell">
                        <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                        <div class="slot-time" v-if="slotTimeForGroup('grade9_2_4', String(tok))">{{ fmtTime(slotTimeForGroup('grade9_2_4', String(tok))![0]) }} – {{ fmtTime(slotTimeForGroup('grade9_2_4', String(tok))![1]) }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <template v-if="dailyItemFor(cls.id, periodNumFromToken(String(tok)))">
                        <div class="period-cell" :style="{ backgroundColor: dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.color || '#f5f7fb' }">
                          <div class="cell-subject one-line">
                            <Icon v-if="subjectIcon(dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                            <span class="subject-name truncate-1">{{ dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                          </div>
                          <div class="cell-teacher one-line truncate-1">{{ dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.teacher_name || '—' }}</div>
                          <div class="cell-time small text-muted" v-if="timeRangeForGroup('grade9_2_4', periodNumFromToken(String(tok)))">
                            <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                            {{ timeRangeForGroup('grade9_2_4', periodNumFromToken(String(tok))) }}
                          </div>
                        </div>
                      </template>
                      <span v-else class="text-muted">—</span>
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Daily view (updated): الصفوف = الفصول، الأعمدة = الحصص مع ترويسة مدمجة -->
    <div v-else-if="mode === 'daily' && !isWing3ThuGrouped" class="auto-card p-0 overflow-auto">
      <div class="p-3 d-flex align-items-center gap-2 border-bottom">
        <Icon icon="solar:calendar-date-bold-duotone" />
        <div class="fw-bold">جدول اليوم — {{ formattedDate }} — {{ dayNameAr(dateStr) }}</div>
        <span class="ms-auto small text-muted">{{ groupedDaily.total }} عنصر</span>
      </div>
      <div class="in-card-98">
        <div class="tt-daily-scroller">
          <table class="tt-daily-table" dir="rtl" aria-label="جدول يومي: الفصول صفوف والحصص أعمدة">
            <colgroup>
              <col style="min-width: 120px" />
              <col v-for="tok in dailyHeaderTokensSafe" :key="'cg-p-'+String(tok)" style="min-width: 120px" />
            </colgroup>
            <thead>
              <tr>
                <th class="tt-daily-th tt-daily-th-sticky">الفصل</th>
                <th
                  v-for="tok in dailyHeaderTokensSafe"
                  :key="'hd-'+String(tok)"
                  class="tt-daily-th"
                  :class="dailyHeaderClass(String(tok))"
                >
                  <template v-if="isPeriodToken(String(tok))">
                    <div class="fw-bold">حصة {{ periodNumFromToken(String(tok)) }}</div>
                  </template>
                  <template v-else>
                    <div class="fw-bold">{{ headerLabel(String(tok)) }}</div>
                  </template>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(cls, idx) in dailyClassList" :key="'row-cls-'+cls.id">
                <th scope="row" class="tt-daily-th tt-daily-th-sticky">
                  <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name || ('صف #'+cls.id) }}</span>
                </th>
                <td
                  v-for="tok in dailyHeaderTokensSafe"
                  :key="'cell-'+cls.id+'-'+String(tok)"
                  class="tt-daily-td"
                  :class="dailyCellClass(String(tok))"
                >
                  <!-- Non-lesson cell -->
                  <template v-if="!isPeriodToken(String(tok))">
                    <div class="slot-cell">
                      <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                      <div class="slot-time" v-if="slotTimeDailyForClass(cls.id, String(tok))">
                        {{ fmtTime(slotTimeDailyForClass(cls.id, String(tok))![0]) }} – {{ fmtTime(slotTimeDailyForClass(cls.id, String(tok))![1]) }}
                      </div>
                    </div>
                  </template>
                  <!-- Lesson cell -->
                  <template v-else>
                    <template v-if="dailyItemFor(cls.id, periodNumFromToken(String(tok)))">
                      <div
                        class="period-cell"
                        :style="{ backgroundColor: dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.color || '#f5f7fb' }"
                        :title="
                          (dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name || 'مادة') +
                          ' — ' + (dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.teacher_name || '—') +
                          (timeRange(periodNumFromToken(String(tok))) ? (' — ' + timeRange(periodNumFromToken(String(tok)))) : '')
                        "
                      >
                        <div class="cell-subject one-line">
                          <Icon v-if="subjectIcon(dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                          <span class="subject-name truncate-1">{{ dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                        </div>
                        <div class="cell-teacher one-line truncate-1">{{ dailyItemFor(cls.id, periodNumFromToken(String(tok)))?.teacher_name || '—' }}</div>
                        <div class="cell-time small text-muted" v-if="timeRange(periodNumFromToken(String(tok)))">
                          <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                          {{ timeRange(periodNumFromToken(String(tok))) }}
                        </div>
                      </div>
                    </template>
                    <span v-else class="text-muted">—</span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Weekly view: الأيام صفوف والحصص أعمدة (Wing 3 Thursday grouped) -->
    <div v-else-if="mode === 'weekly' && isWing3ThuGrouped" class="d-flex flex-column gap-4">
      <!-- Secondary table -->
      <div v-if="classListWeeklySecondary.length" class="auto-card p-0 overflow-hidden">
        <div class="p-3 d-flex align-items-center gap-2 border-bottom">
          <Icon icon="solar:calendar-bold-duotone" />
          <div class="fw-bold">الجدول الأسبوعي — ثانوي (10-1 / 10-2)</div>
          <span class="ms-auto small text-muted">{{ classListWeeklySecondary.length }} فصل</span>
        </div>
        <div class="in-card-98">
          <div class="tt7-wrapper">
            <div class="tt7-scroller">
              <table class="tt7-table" dir="rtl" aria-label="جدول أسبوعي (ثانوي)">
                <colgroup>
                  <col :style="{ minWidth: weeklyColPx(0) }" />
                  <col :style="{ minWidth: weeklyColPx(1) }" />
                  <col v-for="(tok, i) in weeklyHeaderTokensSecondaryGroup" :key="'cg-sec-' + String(tok)" :style="{ minWidth: weeklyColPx(i + 2) }" />
                </colgroup>
                <thead>
                  <tr>
                    <th class="tt7-th tt7-th-sticky tt7-th-period resizable-th">الفصل</th>
                    <th class="tt7-th resizable-th">اليوم</th>
                    <th v-for="tok in weeklyHeaderTokensSecondaryGroup" :key="'ph-sec-' + String(tok)" class="tt7-th resizable-th" :class="weeklyHeaderClass(String(tok))">
                      <template v-if="isPeriodToken(String(tok))">حصة {{ periodNumFromToken(String(tok)) }}</template>
                      <template v-else>{{ headerLabel(String(tok)) }}</template>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="(cls, ci) in classListWeeklySecondary" :key="'sec-' + cls.id">
                    <tr v-for="(d, idx) in DAYS5" :key="'row-sec-' + cls.id + '-d-' + d[0]" :class="{ 'class-separator': ci > 0 && idx === 0 }">
                      <th v-if="idx === 0" class="tt7-th tt7-th-period tt7-th-sticky" :rowspan="DAYS5.length">
                        <div class="hdr-line">
                          <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span>
                        </div>
                      </th>
                      <th class="tt7-th">{{ d[1] }}</th>
                      <td v-for="tok in weeklyHeaderTokensSecondaryGroup" :key="'cell-sec-' + cls.id + '-' + d[0] + '-' + String(tok)" class="tt7-td" :class="weeklyCellClass(String(tok))">
                        <div class="tt7-cell">
                          <template v-if="!isPeriodToken(String(tok))">
                            <div class="slot-cell">
                              <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                              <div class="slot-time" v-if="weeklySlotTimeForGroup(d[0], String(tok), 'secondary')">
                                {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'secondary')![0]) }} – {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'secondary')![1]) }}
                              </div>
                            </div>
                          </template>
                          <template v-else>
                            <template v-if="classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))">
                              <div class="mini-cell" :style="{ backgroundColor: classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.color || '#f5f7fb' }">
                                <div class="mini-subj one-line">
                                  <Icon v-if="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                                  <span class="subject-name truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                                </div>
                                <div class="mini-teacher one-line truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.teacher_name || '—' }}</div>
                                <div class="mini-time small text-muted" v-if="weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'secondary')">
                                  <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                                  {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'secondary')![0]) }} – {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'secondary')![1]) }}
                                </div>
                              </div>
                            </template>
                            <span v-else class="text-muted">—</span>
                          </template>
                        </div>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Grade 9 (2-4) per-class tables: Sun–Wed per class -->
      <template v-for="cls in classListWeeklyG9" :key="'g9pc-' + cls.id">
        <div class="auto-card p-0 overflow-hidden">
          <div class="p-3 d-flex align-items-center gap-2 border-bottom">
            <Icon icon="solar:calendar-bold-duotone" />
            <div class="fw-bold">الجدول الأسبوعي — تاسع ({{ cls.name }}) — الأحد إلى الأربعاء</div>
            <span class="ms-auto small text-muted">فصل واحد</span>
          </div>
          <div class="in-card-98">
            <div class="tt7-wrapper">
              <div class="tt7-scroller">
                <table class="tt7-table" dir="rtl" aria-label="جدول أسبوعي (تاسع — أحد إلى أربعاء)">
                  <colgroup>
                    <col :style="{ minWidth: weeklyColPx(0) }" />
                    <col :style="{ minWidth: weeklyColPx(1) }" />
                    <col v-for="(tok, i) in weeklyHeaderTokensG9_SW" :key="'cg-g9-' + String(tok)" :style="{ minWidth: weeklyColPx(i + 2) }" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th class="tt7-th tt7-th-sticky tt7-th-period resizable-th">الفصل</th>
                      <th class="tt7-th resizable-th">اليوم</th>
                      <th v-for="tok in weeklyHeaderTokensG9_SW" :key="'ph-g9-' + String(tok)" class="tt7-th resizable-th" :class="weeklyHeaderClass(String(tok))">
                        <template v-if="isPeriodToken(String(tok))">حصة {{ periodNumFromToken(String(tok)) }}</template>
                        <template v-else>{{ headerLabel(String(tok)) }}</template>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(d, idx) in DAYS_SW" :key="'row-g9-' + cls.id + '-d-' + d[0]">
                      <th v-if="idx === 0" class="tt7-th tt7-th-period tt7-th-sticky" :rowspan="DAYS_SW.length">
                        <div class="hdr-line">
                          <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span>
                        </div>
                      </th>
                      <th class="tt7-th">{{ d[1] }}</th>
                      <td v-for="tok in weeklyHeaderTokensG9_SW" :key="'cell-g9-' + cls.id + '-' + d[0] + '-' + String(tok)" class="tt7-td" :class="weeklyCellClass(String(tok))">
                        <div class="tt7-cell">
                          <template v-if="!isPeriodToken(String(tok))">
                            <div class="slot-cell">
                              <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                              <div class="slot-time" v-if="weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')">
                                {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')![0]) }} – {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')![1]) }}
                              </div>
                            </div>
                          </template>
                          <template v-else>
                            <template v-if="classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))">
                              <div class="mini-cell" :style="{ backgroundColor: classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.color || '#f5f7fb' }">
                                <div class="mini-subj one-line">
                                  <Icon v-if="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                                  <span class="subject-name truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                                </div>
                                <div class="mini-teacher one-line truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.teacher_name || '—' }}</div>
                                <div class="mini-time small text-muted" v-if="weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')">
                                  <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                                  {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')![0]) }} – {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')![1]) }}
                                </div>
                              </div>
                            </template>
                            <span v-else class="text-muted">—</span>
                          </template>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Grade 9 (2-4) — Thursday only for this class (no table header) -->
        <div class="auto-card p-0 overflow-hidden mt-3">
          <div class="in-card-98">
            <div class="tt7-wrapper">
              <div class="tt7-scroller">
                <table class="tt7-table" dir="rtl" aria-label="جدول أسبوعي (الخميس فقط) — تاسع ({{ cls.name }})">
                  <colgroup>
                    <col :style="{ minWidth: weeklyColPx(0) }" />
                    <col :style="{ minWidth: weeklyColPx(1) }" />
                    <col v-for="(tok, i) in weeklyHeaderTokensG9_Thu" :key="'cg-g9-thu-' + String(tok)" :style="{ minWidth: weeklyColPx(i + 2) }" />
                  </colgroup>
                  <tbody>
                    <tr v-for="(d, idx) in DAYS_THU" :key="'row-g9-thu-' + cls.id + '-d-' + d[0]">
                      <th v-if="idx === 0" class="tt7-th tt7-th-period tt7-th-sticky" :rowspan="DAYS_THU.length">
                        <div class="hdr-line">
                          <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span>
                        </div>
                      </th>
                      <th class="tt7-th">{{ d[1] }}</th>
                      <td v-for="tok in weeklyHeaderTokensG9_Thu" :key="'cell-g9-thu-' + cls.id + '-' + d[0] + '-' + String(tok)" class="tt7-td" :class="weeklyCellClass(String(tok))">
                        <div class="tt7-cell">
                          <template v-if="!isPeriodToken(String(tok))">
                            <div class="slot-cell">
                              <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                              <div class="slot-time" v-if="weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')">
                                {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')![0]) }} – {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')![1]) }}
                              </div>
                            </div>
                          </template>
                          <template v-else>
                            <template v-if="classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))">
                              <div class="mini-cell" :style="{ backgroundColor: classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.color || '#f5f7fb' }">
                                <div class="mini-subj one-line">
                                  <Icon v-if="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                                  <span class="subject-name truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                                </div>
                                <div class="mini-teacher one-line truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.teacher_name || '—' }}</div>
                                <div class="mini-time small text-muted" v-if="weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')">
                                  <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                                  {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')![0]) }} – {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')![1]) }}
                                </div>
                              </div>
                            </template>
                            <span v-else class="text-muted">—</span>
                          </template>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

      <!-- Grade 9 (2-4) — Thursday only (no table header) -->
      <div v-if="false" class="auto-card p-0 overflow-hidden">
        <div class="p-3 d-flex align-items-center gap-2 border-bottom">
          <Icon icon="solar:calendar-bold-duotone" />
          <div class="fw-bold">الخميس — تاسع (2 / 3 / 4)</div>
          <span class="ms-auto small text-muted">{{ classListWeeklyG9.length }} فصل</span>
        </div>
        <div class="in-card-98">
          <div class="tt7-wrapper">
            <div class="tt7-scroller">
              <table class="tt7-table" dir="rtl" aria-label="جدول أسبوعي (الخميس فقط) — تاسع 2-3-4">
                <colgroup>
                  <col :style="{ minWidth: weeklyColPx(0) }" />
                  <col :style="{ minWidth: weeklyColPx(1) }" />
                  <col v-for="(tok, i) in weeklyHeaderTokensG9_Thu" :key="'cg-g9-thu-' + String(tok)" :style="{ minWidth: weeklyColPx(i + 2) }" />
                </colgroup>
                <tbody>
                  <template v-for="(cls, ci) in classListWeeklyG9" :key="'g9-thu-' + cls.id">
                    <tr v-for="(d, idx) in DAYS_THU" :key="'row-g9-thu-' + cls.id + '-d-' + d[0]" :class="{ 'class-separator': ci > 0 && idx === 0 }">
                      <th v-if="idx === 0" class="tt7-th tt7-th-period tt7-th-sticky" :rowspan="DAYS_THU.length">
                        <div class="hdr-line">
                          <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span>
                        </div>
                      </th>
                      <th class="tt7-th">{{ d[1] }}</th>
                      <td v-for="tok in weeklyHeaderTokensG9_Thu" :key="'cell-g9-thu-' + cls.id + '-' + d[0] + '-' + String(tok)" class="tt7-td" :class="weeklyCellClass(String(tok))">
                        <div class="tt7-cell">
                          <template v-if="!isPeriodToken(String(tok))">
                            <div class="slot-cell">
                              <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                              <div class="slot-time" v-if="weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')">
                                {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')![0]) }} – {{ fmtTime(weeklySlotTimeForGroup(d[0], String(tok), 'grade9_2_4')![1]) }}
                              </div>
                            </div>
                          </template>
                          <template v-else>
                            <template v-if="classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))">
                              <div class="mini-cell" :style="{ backgroundColor: classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.color || '#f5f7fb' }">
                                <div class="mini-subj one-line">
                                  <Icon v-if="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                                  <span class="subject-name truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                                </div>
                                <div class="mini-teacher one-line truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.teacher_name || '—' }}</div>
                                <div class="mini-time small text-muted" v-if="weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')">
                                  <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                                  {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')![0]) }} – {{ fmtTime(weeklyPeriodTimeForGroup(d[0], periodNumFromToken(String(tok)), 'grade9_2_4')![1]) }}
                                </div>
                              </div>
                            </template>
                            <span v-else class="text-muted">—</span>
                          </template>
                        </div>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

    <!-- Weekly view: الأيام صفوف والحصص أعمدة (default) -->
    <div v-else-if="mode === 'weekly' && !isWing3ThuGrouped" class="auto-card p-0 overflow-hidden">
      <div class="p-3 d-flex align-items-center gap-2 border-bottom">
        <Icon icon="solar:calendar-bold-duotone" />
        <div class="fw-bold">الجدول الأسبوعي للفصل</div>
        <span class="ms-auto small text-muted">فصول × أيام (الأحد → الخميس)</span>
      </div>
      <div class="in-card-98">
        <div class="tt7-wrapper">
          <div class="tt7-scroller">
            <table class="tt7-table" dir="rtl" aria-label="جدول أسبوعي: الأيام صفوف والحصص أعمدة">
              <colgroup>
                <col :style="{ minWidth: weeklyColPx(0) }" />
                <col :style="{ minWidth: weeklyColPx(1) }" />
                <col v-for="(tok, i) in weeklyHeaderTokens" :key="'cg-p-' + String(tok)" :style="{ minWidth: weeklyColPx(i + 2) }" />
              </colgroup>
              <thead>
                <tr>
                  <th class="tt7-th tt7-th-sticky tt7-th-period resizable-th">الفصل</th>
                  <th class="tt7-th resizable-th">اليوم</th>
                  <th v-for="tok in weeklyHeaderTokens" :key="'ph-' + String(tok)" class="tt7-th resizable-th" :class="weeklyHeaderClass(String(tok))">
                    <template v-if="isPeriodToken(String(tok))">حصة {{ periodNumFromToken(String(tok)) }}</template>
                    <template v-else>{{ headerLabel(String(tok)) }}</template>
                  </th>
                </tr>
              </thead>
              <tbody>
                <template v-for="(cls, ci) in classList" :key="'grp-' + cls.id">
                  <tr v-for="(d, idx) in DAYS5" :key="'row-c-' + cls.id + '-d-' + d[0]" :class="{ 'class-separator': ci > 0 && idx === 0 }">
                    <th v-if="idx === 0" class="tt7-th tt7-th-period tt7-th-sticky" :rowspan="DAYS5.length">
                      <div class="hdr-line">
                        <span class="badge text-bg-secondary no-wrap class-name-badge">{{ cls.name }}</span>
                      </div>
                    </th>
                    <th class="tt7-th">{{ d[1] }}</th>
                    <td v-for="tok in weeklyHeaderTokens" :key="'cell-' + cls.id + '-' + d[0] + '-' + String(tok)" class="tt7-td" :class="weeklyCellClass(String(tok))">
                      <div class="tt7-cell">
                        <!-- Non-lesson: show label + time -->
                        <template v-if="!isPeriodToken(String(tok))">
                          <div class="slot-cell">
                            <div class="slot-label">{{ headerLabel(String(tok)) }}</div>
                            <div class="slot-time" v-if="weeklySlotTime(d[0], String(tok))">
                              {{ fmtTime(weeklySlotTime(d[0], String(tok))![0]) }} – {{ fmtTime(weeklySlotTime(d[0], String(tok))![1]) }}
                            </div>
                          </div>
                        </template>
                        <!-- Lesson cell: show mini with times if available -->
                        <template v-else>
                          <template v-if="classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))">
                            <div
                              class="mini-cell"
                              :style="{ backgroundColor: classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.color || '#f5f7fb' }"
                              :title="
                                (classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name || 'مادة') +
                                ' — ' +
                                (classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.teacher_name || '—')
                              "
                            >
                              <div class="mini-subj one-line">
                                <Icon v-if="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" :icon="subjectIcon(classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name)" class="subject-icon" />
                                <span class="subject-name truncate-1">{{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.subject_name || 'مادة' }}</span>
                              </div>
                              <div class="mini-teacher one-line truncate-1">
                                {{ classDayPeriodItem(cls.id, d[0], periodNumFromToken(String(tok)))?.teacher_name || '—' }}
                              </div>
                              <div class="mini-time small text-muted" v-if="weeklyPeriodTime(d[0], periodNumFromToken(String(tok)))">
                                <Icon icon="solar:clock-circle-bold-duotone" class="me-1" />
                                {{ fmtTime(weeklyPeriodTime(d[0], periodNumFromToken(String(tok)))![0]) }} – {{ fmtTime(weeklyPeriodTime(d[0], periodNumFromToken(String(tok)))![1]) }}
                              </div>
                            </div>
                          </template>
                          <span v-else class="text-muted">—</span>
                        </template>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive, watch, nextTick } from 'vue';
import { tiles } from '../../../home/icon-tiles.config';
import { useRoute, useRouter } from 'vue-router';
const route = useRoute();
const router = useRouter();
const tileMeta = computed(() => {
  const name = route.name as string | undefined;
  if (name === 'wing-timetable-weekly') {
    return tiles.find(t => t.to === '/wing/timetable/weekly') || { title: 'الجدول الأسبوعي', icon: 'solar:calendar-bold-duotone', color: '#5dade2' };
  }
  return tiles.find(t => t.to === '/wing/timetable/daily') || { title: 'جدول اليوم', icon: 'solar:clock-circle-bold-duotone', color: '#5dade2' };
});
import { onBeforeUnmount } from "vue";
import DsButton from "../../../components/ui/DsButton.vue";
import { getWingMe, getWingTimetable } from "../../../shared/api/client";
import { formatDateDMY, parseDMYtoISO, toIsoDate } from "../../../shared/utils/date";
import DatePickerDMY from "../../../components/ui/DatePickerDMY.vue";
// Wing context: ensure dynamic subtitle like other Wing pages
import { useWingContext } from '../../../shared/composables/useWingContext';
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
const { ensureLoaded, wingLabelFull, setSelectedWing } = useWingContext();
onMounted(() => { try { ensureLoaded(); } catch {} });

const today = new Date();
const iso = (d: Date) => d.toISOString().slice(0, 10);
const dateStr = ref<string>(iso(today));
const mode = ref<"daily" | "weekly">("daily");
// Lock mode based on route (two separate pages)
if ((route.name as string | undefined) === 'wing-timetable-weekly') {
  mode.value = 'weekly';
} else {
  mode.value = 'daily';
}
watch(
  () => route.name,
  (nv) => {
    if (nv === 'wing-timetable-weekly') mode.value = 'weekly';
    else mode.value = 'daily';
  }
);
const loading = ref(false);
const error = ref<string | null>(null);
const wingId = ref<number | null>(null);
const wingOptions = ref<Record<number, string>>({});

const DAYS = [
  [1, "الأحد"],
  [2, "الاثنين"],
  [3, "الثلاثاء"],
  [4, "الأربعاء"],
  [5, "الخميس"],
] as const;
// أيام الدراسة: الأحد إلى الخميس فقط (إزالة الجمعة والسبت لطلبك)
const DAYS5 = [
  [1, "الأحد"],
  [2, "الاثنين"],
  [3, "الثلاثاء"],
  [4, "الأربعاء"],
  [5, "الخميس"],
] as const;
// Weekly grouping subsets
const DAYS_SW = [
  [1, "الأحد"],
  [2, "الاثنين"],
  [3, "الثلاثاء"],
  [4, "الأربعاء"],
] as const;
const DAYS_THU = [
  [5, "الخميس"],
] as const;
const PERIODS = [1, 2, 3, 4, 5, 6, 7];
const activeDay = ref<number>(1);
const activeDayStr = computed(() => String(activeDay.value));

const weekly = ref<Record<string, any[]>>({});
const dailyItems = ref<any[]>([]);
const meta = ref<Record<string, any>>({});
const periodTimes = ref<Record<number, { start: string; end: string }>>({});
// Weekly per-day period times map (from API meta.period_times_by_day)
const weeklyPeriodTimesByDay = ref<Record<string, Record<number, [string, string]>>>({});

// Token-based columns support
const dailyHeaderTokens = ref<string[]>([]);
// Safe fallback: if backend didn't send columns for daily view, default to P1..P7
const dailyHeaderTokensSafe = computed<string[]>(() => {
  return (dailyHeaderTokens.value && dailyHeaderTokens.value.length)
    ? dailyHeaderTokens.value
    : PERIODS.map((n) => `P${n}`);
});
const dailySlotMeta = ref<Record<string, { kind: string; label?: string; start_time?: string; end_time?: string }>>({});
// Per-class non-lesson times for the selected day (e.g., different break/prayer per class)
const dailyNonLessonTimesByClass = ref<Record<number, Record<string, [string, string]>>>({} as any);
const weeklyColumnsByDay = ref<Record<string, string[]>>({});
const weeklySlotMetaByDay = ref<Record<string, Record<string, { kind: string; label?: string; start_time?: string; end_time?: string }>>>({});

// Weekly column resize state (period + 7 days)
const enableResize = ref(false);
const WEEKLY_COLS = 9; // 0 = الفصل (sticky), 1 = اليوم، 2..8 = الحصص 1..7
const weeklyWidths = ref<number[]>([]);
const defaultWeeklyWidths = () => {
  // Reduce class/day to half width and distribute extra space to periods equally
  const arr = new Array(WEEKLY_COLS).fill(140);
  // Halved sticky columns to free space for periods
  arr[0] = 50; // الفصل (sticky)
  arr[1] = 48; // اليوم
  // Make all period columns equal and wider to avoid inner horizontal scrollbars
  for (let i = 2; i < WEEKLY_COLS; i++) arr[i] = 240;
  return arr;
};
const LS_KEY = "wing_tt_weekly_col_widths";
const hasCustomWidths = computed(() => {
  const def = defaultWeeklyWidths();
  if (weeklyWidths.value.length !== WEEKLY_COLS) return false;
  return weeklyWidths.value.some((v, i) => v !== def[i]);
});
function weeklyColPx(i: number): string {
  const w = weeklyWidths.value[i];
  return typeof w === "number" && !isNaN(w) ? `${w}px` : "";
}
function loadWeeklyWidths() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) {
      weeklyWidths.value = defaultWeeklyWidths();
      return;
    }
    const arr = JSON.parse(raw);
    if (Array.isArray(arr) && arr.length === WEEKLY_COLS) {
      weeklyWidths.value = arr.map((n: any, idx: number) =>
        Number.isFinite(n)
          ? Math.max(idx === 0 ? 50 : 45, Math.min(Number(n), 600))
          : defaultWeeklyWidths()[idx]
      );
    } else {
      weeklyWidths.value = defaultWeeklyWidths();
    }
  } catch {
    weeklyWidths.value = defaultWeeklyWidths();
  }
}
function saveWeeklyWidths() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(weeklyWidths.value));
  } catch {}
}
function resetWeeklyWidths() {
  weeklyWidths.value = defaultWeeklyWidths();
  saveWeeklyWidths();
}
// Drag-to-resize logic
let dragState: null | { col: number; startX: number; startW: number } = null;
function onResizeStart(colIndex: number, e: MouseEvent) {
  // In RTL, moving mouse left increases width visually; but since we use clientX delta, we invert sign
  dragState = { col: colIndex, startX: e.clientX, startW: weeklyWidths.value[colIndex] || 140 };
  document.addEventListener("mousemove", onResizeMove);
  document.addEventListener("mouseup", onResizeEnd, { once: true });
  // prevent text selection
  document.body.classList.add("resizing");
}
function onResizeMove(e: MouseEvent) {
  if (!dragState) return;
  const idx = dragState.col;
  const delta =
    document.dir === "rtl" || document.documentElement.getAttribute("dir") === "rtl"
      ? dragState.startX - e.clientX
      : e.clientX - dragState.startX;
  // Allow narrower sticky class/day columns to maximize period widths
  const minW = idx === 0 ? 100 : 90;
  const maxW = 600;
  const next = Math.max(minW, Math.min(dragState.startW + delta, maxW));
  // apply
  const arr = weeklyWidths.value.slice();
  arr[idx] = next;
  weeklyWidths.value = arr;
}
function onResizeEnd() {
  document.removeEventListener("mousemove", onResizeMove);
  document.body.classList.remove("resizing");
  dragState = null;
  saveWeeklyWidths();
}

const isEmpty = computed(() =>
  mode.value === "daily"
    ? dailyItems.value.length === 0
    : Object.values(weekly.value).every((a) => (a as any[]).length === 0)
);
const formattedDate = computed(() => formatDateDMY(dateStr.value));
// Unified date/time header badge support
const dateISO = computed(() => parseDMYtoISO(dateStr.value) || toIsoDate(new Date()));
const isToday = computed(() => dateISO.value === toIsoDate(new Date()));
const liveTime = ref<string>("");
function updateLiveTime() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  liveTime.value = `${hh}:${mm}`;
}
let liveClockTimer: any = null;
function startLiveClock() { stopLiveClock(); updateLiveTime(); liveClockTimer = setInterval(updateLiveTime, 60_000); }
function stopLiveClock() { if (liveClockTimer) { clearInterval(liveClockTimer); liveClockTimer = null; } }

// Professional live refresh controls
const paused = ref<boolean>(String(route.query.paused || '') === '1');
const lastUpdated = ref<string>('');
function timeAscii(d: Date): string { const hh = String(d.getHours()).padStart(2,'0'); const mm = String(d.getMinutes()).padStart(2,'0'); return `${hh}:${mm}`; }
function syncPausedToUrl() {
  const q = { ...route.query } as any;
  if (paused.value) q.paused = '1'; else delete q.paused;
  router.replace({ query: q }).catch(() => {});
}
function toggleLive() { paused.value = !paused.value; syncPausedToUrl(); if (!paused.value) { loadData(); } }
const AUTO_REFRESH_MS = 30000;
let refreshTimer: any = null;
function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(() => {
    if (!document.hidden && isToday.value && !paused.value) {
      loadData();
    }
  }, AUTO_REFRESH_MS);
}
function stopAutoRefresh() { if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; } }
function handleVisibility() { if (!document.hidden && !paused.value) { loadData(); } }

const groupedDaily = computed(() => {
  const groups: Record<number, any[]> = {};
  for (const p of PERIODS) groups[p] = [];
  for (const it of dailyItems.value) {
    if (groups[it.period_number]) groups[it.period_number].push(it);
  }
  return { groups, total: dailyItems.value.length };
});

// ===== Wing 3 Thursday grouping support =====
const currentDow = ref<number>(1);
const isWing3ThuGrouped = computed(() => {
  const gby = (meta.value as any)?.grouped_by;
  return Number(wingId.value) === 3 && gby === 'wing3_thursday' && ((mode.value === 'weekly') || (mode.value === 'daily' && Number((resDow.value || currentDow.value)) === 5));
});
// Store dow from API
const resDow = ref<number | null>(null);

function parseGradeSectionFromName(name?: string | null): { grade: number; section: number | null } {
  const s = String(name || '').trim();
  const m = /^(\d+)[\-\/.](\d+)/.exec(s);
  if (m) return { grade: Number(m[1]), section: Number(m[2]) };
  const m2 = /(\d+)/.exec(s);
  return { grade: m2 ? Number(m2[1]) : 0, section: null };
}
function isSecondaryName(name?: string | null) {
  const { grade } = parseGradeSectionFromName(name);
  return grade >= 10;
}
function isGrade9_2_4Name(name?: string | null) {
  const { grade, section } = parseGradeSectionFromName(name);
  return grade === 9 && section !== null && section >= 2 && section <= 4;
}

const classListSecondary = computed<{ id: number; name: string }[]>(() => {
  // build from dailyItems unique classes
  const seen = new Map<number, string>();
  for (const it of dailyItems.value) {
    const cid = Number(it.class_id);
    const cname = String(it.class_name || '');
    if (isSecondaryName(cname) && !seen.has(cid)) seen.set(cid, cname);
  }
  return Array.from(seen.entries()).map(([id, name]) => ({ id, name })).sort((a,b)=> String(a.name).localeCompare(String(b.name), 'ar'));
});
const classListG9 = computed<{ id: number; name: string }[]>(() => {
  const seen = new Map<number, string>();
  for (const it of dailyItems.value) {
    const cid = Number(it.class_id);
    const cname = String(it.class_name || '');
    if (isGrade9_2_4Name(cname) && !seen.has(cid)) seen.set(cid, cname);
  }
  return Array.from(seen.entries()).map(([id, name]) => ({ id, name })).sort((a,b)=> String(a.name).localeCompare(String(b.name), 'ar'));
});

// Group-specific headers/times (daily)
const dailyHeaderTokensSecondary = computed<string[]>(() => {
  const gcols = (meta.value as any)?.group_columns_by_day?.secondary?.['5'];
  if (Array.isArray(gcols) && gcols.length) return gcols.map(String);
  return dailyHeaderTokensSafe.value;
});
const dailyHeaderTokensG9 = computed<string[]>(() => {
  const gcols = (meta.value as any)?.group_columns_by_day?.grade9_2_4?.['5'];
  if (Array.isArray(gcols) && gcols.length) return gcols.map(String);
  return dailyHeaderTokensSafe.value;
});
function slotTimeForGroup(group: 'secondary' | 'grade9_2_4', tok: string): [string, string] | null {
  const metaMap = (meta.value as any)?.group_slot_meta_by_day?.[group]?.['5']?.[tok];
  if (metaMap && metaMap.start_time && metaMap.end_time) return [String(metaMap.start_time), String(metaMap.end_time)];
  return null;
}
function timeRangeForGroup(group: 'secondary' | 'grade9_2_4', p: number): string {
  const mp = (meta.value as any)?.group_period_times_by_day?.[group]?.['5'] || {};
  const rec = mp[p as any];
  if (Array.isArray(rec) && rec.length >= 2) {
    const s = timeToHM(String(rec[0]));
    const e = timeToHM(String(rec[1]));
    return s && e ? `${s} — ${e}` : s || e || '';
  } else if (rec && typeof rec === 'object') {
    const s = timeToHM((rec as any).start || (rec as any).start_time);
    const e = timeToHM((rec as any).end || (rec as any).end_time);
    return s && e ? `${s} — ${e}` : s || e || '';
  }
  return '';
}

// Weekly grouped helpers
const classListWeeklySecondary = computed(() => classList.value.filter((c) => isSecondaryName(c.name)));
const classListWeeklyG9 = computed(() => classList.value.filter((c) => isGrade9_2_4Name(c.name)));
// Group-specific weekly header tokens (prefer DB-provided Thursday group columns when available)
const weeklyHeaderTokensSecondaryGroup = computed<string[]>(() => {
  const gcols = (meta.value as any)?.group_columns_by_day?.secondary?.['5'];
  if (Array.isArray(gcols) && gcols.length) return gcols.map(String);
  return (weeklyHeaderTokens as any).value || [];
});
// Weekly headers for Grade 9 (2-4): use Sun–Wed per-day columns from DB so RECESS appears after P4.
const weeklyHeaderTokensG9_SW = computed<string[]>(() => {
  // Prefer columns for Sunday (assumed same structure Sun–Wed for upper floor)
  const cols1 = (weeklyColumnsByDay.value || {})['1'];
  if (Array.isArray(cols1) && cols1.length) return cols1.map(String);
  // Fallback to Monday if Sunday missing
  const cols2 = (weeklyColumnsByDay.value || {})['2'];
  if (Array.isArray(cols2) && cols2.length) return cols2.map(String);
  // Last resort: generic weekly header tokens
  return (weeklyHeaderTokens as any).value || [];
});
// Weekly headers for Thursday (Grade 9 group): keep using group Thursday columns from backend meta
const weeklyHeaderTokensG9_Thu = computed<string[]>(() => {
  const gcols = (meta.value as any)?.group_columns_by_day?.grade9_2_4?.['5'];
  if (Array.isArray(gcols) && gcols.length) return gcols.map(String);
  return (weeklyHeaderTokens as any).value || [];
});
function weeklySlotTimeForGroup(day: number, tok: string, group: 'secondary' | 'grade9_2_4') {
  if (Number(day) === 5) {
    const metaMap = (meta.value as any)?.group_slot_meta_by_day?.[group]?.['5']?.[tok];
    if (metaMap && metaMap.start_time && metaMap.end_time) return [String(metaMap.start_time), String(metaMap.end_time)];
  }
  return weeklySlotTime(day, tok);
}
function weeklyPeriodTimeForGroup(day: number, p: number, group: 'secondary' | 'grade9_2_4') {
  if (Number(day) === 5) {
    const mp = (meta.value as any)?.group_period_times_by_day?.[group]?.['5'] || {};
    const rec = mp[p as any];
    if (Array.isArray(rec) && rec.length >= 2) return [String(rec[0]), String(rec[1])];
    if (rec && typeof rec === 'object') {
      const s = (rec as any).start || (rec as any).start_time;
      const e = (rec as any).end || (rec as any).end_time;
      if (s || e) return [String(s || ''), String(e || '')];
    }
  }
  return weeklyPeriodTime(day, p);
}

// Build class list for daily header row (unique classes appearing today)
const dailyClassList = computed(() => {
  const map = new Map<number, { id: number; name?: string | null }>();
  for (const it of dailyItems.value) {
    const id = Number(it.class_id);
    if (Number.isFinite(id) && !map.has(id)) {
      map.set(id, { id, name: it.class_name || null });
    }
  }
  return Array.from(map.values()).sort((a, b) => (a.name || '').localeCompare(b.name || '') || a.id - b.id);
});

// Derive current wing label for print header and context
const wingLabel = computed(() => {
  const id = wingId.value as number | null;
  if (!id) return "";
  const name = (wingOptions.value as any)[id];
  return name || `جناح #${id}`;
});

function printPage() {
  try {
    window.print();
  } catch {}
}

function dayNameAr(d: string): string {
  const N = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(d));
  let dt: Date = m ? new Date(parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3])) : new Date(d);
  if (isNaN(dt.getTime())) return "—";
  return N[dt.getDay()] || "—";
}

import { subjectIcon } from "../../../shared/icons/subjectIcons";

function setMode(m: "daily" | "weekly") {
  if (mode.value !== m) {
    mode.value = m;
    loadData();
    if (m === "daily") {
      nextTick().then(() => updateUnifiedCellWidth());
    }
  }
}

function timeToHM(t: string | undefined | null): string {
  if (!t) return "";
  // Expecting 'HH:MM[:SS]' — keep HH:MM
  const m = /^(\d{2}:\d{2})/.exec(String(t));
  return m ? m[1] : String(t);
}
function timeRange(p: number): string {
  const rec = periodTimes.value[p as keyof typeof periodTimes.value] as any;
  if (!rec) return "";
  const s = timeToHM(rec.start);
  const e = timeToHM(rec.end);
  return s && e ? `${s} — ${e}` : s || e || "";
}

// ===== Token helpers (daily/weekly) =====
function isPeriodToken(tok: string): boolean {
  return typeof tok === 'string' && /^P\d+$/.test(tok);
}
function periodNumFromToken(tok: string): number {
  const m = /^P(\d+)$/.exec(String(tok));
  return m ? Number(m[1]) : 0;
}
function headerLabel(tok: string): string {
  if (isPeriodToken(tok)) return `حصة ${periodNumFromToken(tok)}`;
  const kind = String(tok).split('-')[0].toLowerCase();
  if (kind === 'recess' || kind === 'break') return 'استراحة';
  if (kind === 'prayer') return 'الصلاة';
  return tok;
}
function fmtTime(t?: string) {
  if (!t) return '';
  const m = /^(\d{2}:\d{2})/.exec(String(t));
  return m ? m[1] : String(t);
}
// Daily slot time from meta
function slotTimeDaily(tok: string): [string, string] | null {
  const m = dailySlotMeta.value?.[tok];
  if (m && m.start_time && m.end_time) return [String(m.start_time), String(m.end_time)];
  return null;
}
// Resolve non-lesson kind from token (e.g., 'RECESS-1' -> 'recess')
function kindFromToken(tok: string): string | null {
  if (isPeriodToken(tok)) return null;
  const k = String(tok).split('-')[0].toLowerCase();
  return k === 'break' ? 'recess' : k;
}
// Class-specific non-lesson time if available; else fallback to global slot meta
function slotTimeDailyForClass(classId: number, tok: string): [string, string] | null {
  const kind = kindFromToken(tok);
  if (kind) {
    const clsMap = dailyNonLessonTimesByClass.value?.[classId];
    if (clsMap) {
      const v = clsMap[kind];
      if (Array.isArray(v) && v.length >= 2) return [String(v[0]), String(v[1])];
    }
  }
  return slotTimeDaily(tok);
}
function dailyHeaderClass(tok: string) {
  if (isPeriodToken(tok)) return {} as any;
  const kind = String(tok).split('-')[0].toLowerCase();
  return {
    'slot-header': true,
    'slot-kind-recess': kind === 'recess' || kind === 'break',
    'slot-kind-prayer': kind === 'prayer',
  } as any;
}
function dailyCellClass(tok: string) {
  if (isPeriodToken(tok)) return {} as any;
  const kind = String(tok).split('-')[0].toLowerCase();
  return [
    'slot-cell-outer',
    kind === 'recess' || kind === 'break' ? 'slot-kind-recess' : '',
    kind === 'prayer' ? 'slot-kind-prayer' : '',
  ];
}

// Weekly tokens: prefer first day with tokens, fallback to fixed P1..P7
const weeklyHeaderTokens = computed<string[]>(() => {
  const days = [1,2,3,4,5];
  for (const d of days) {
    const arr = weeklyColumnsByDay.value[String(d)] || [];
    if (arr && arr.length) return arr;
  }
  return [1,2,3,4,5,6,7].map((n) => `P${n}`);
});
function weeklyHeaderClass(tok: string) {
  if (isPeriodToken(tok)) return {} as any;
  const kind = String(tok).split('-')[0].toLowerCase();
  return {
    'slot-header': true,
    'slot-kind-recess': kind === 'recess' || kind === 'break',
    'slot-kind-prayer': kind === 'prayer',
  } as any;
}
function weeklyCellClass(tok: string) {
  if (isPeriodToken(tok)) return {} as any;
  const kind = String(tok).split('-')[0].toLowerCase();
  return [
    'slot-cell-outer',
    kind === 'recess' || kind === 'break' ? 'slot-kind-recess' : '',
    kind === 'prayer' ? 'slot-kind-prayer' : '',
  ];
}
function weeklySlotTime(day: number, tok: string): [string, string] | null {
  const meta = weeklySlotMetaByDay.value?.[String(day)]?.[tok];
  if (meta && meta.start_time && meta.end_time) return [String(meta.start_time), String(meta.end_time)];
  // fallback: search any day
  for (const k of Object.keys(weeklySlotMetaByDay.value || {})) {
    const m = weeklySlotMetaByDay.value[k]?.[tok];
    if (m && m.start_time && m.end_time) return [String(m.start_time), String(m.end_time)];
  }
  return null;
}
function weeklyPeriodTime(day: number, p: number): [string, string] | null {
  const dmap = weeklyPeriodTimesByDay.value?.[String(day)] || {};
  const rec = dmap[p as keyof typeof dmap] as any;
  if (rec && Array.isArray(rec) && rec.length >= 2) return [String(rec[0]), String(rec[1])];
  const fallback = periodTimes.value[p as keyof typeof periodTimes.value] as any;
  if (fallback && (fallback.start || fallback.end)) {
    return [String(fallback.start || ''), String(fallback.end || '')];
  }
  return null;
}

// إرجاع عناصر الخلية لليوم d (1..7) والحصة p (1..7)
function cellItems(d: number, p: number) {
  const arr = weekly.value[String(d)] || [];
  return arr.filter((i: any) => Number(i.period_number) === p);
}

// New: Build list of classes (unique across the week) for the weekly class×day grid
const classList = computed<{ id: number; name: string }[]>(() => {
  const seen = new Map<number, string>();
  const days = [1, 2, 3, 4, 5];
  for (const d of days) {
    const arr = (weekly.value[String(d)] || []) as any[];
    for (const it of arr) {
      const cid = Number(it.class_id);
      if (!Number.isFinite(cid)) continue;
      if (!seen.has(cid)) seen.set(cid, it.class_name || `صف #${cid}`);
    }
  }
  // Return sorted by name (locale-aware Arabic if available)
  return Array.from(seen.entries())
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => String(a.name).localeCompare(String(b.name), "ar"));
});

// New: items for a given class and day (all periods), sorted by period_number
function classDayItems(classId: number, d: number) {
  const arr = weekly.value[String(d)] || [];
  return (arr as any[])
    .filter((it) => Number(it.class_id) === Number(classId))
    .sort((a, b) => Number(a.period_number) - Number(b.period_number));
}

// Helper: find the daily item for a given class and period (used by daily integrated table)
function dailyItemFor(classId: number, p: number) {
  const g = groupedDaily.value.groups?.[p] as any[] | undefined;
  if (!Array.isArray(g)) return null;
  return g.find((it) => Number(it.class_id) === Number(classId)) || null;
}

// Helper: weekly single item for class + day + period
function classDayPeriodItem(classId: number, d: number, p: number) {
  const arr = weekly.value[String(d)] || [];
  return (arr as any[]).find(
    (it) => Number(it.class_id) === Number(classId) && Number(it.period_number) === Number(p)
  ) || null;
}

function ensureWeeklyShape() {
  // ضَمَن وجود مفاتيح 1..7 حتى إن لم يرجعها الـ API
  for (let d = 1; d <= 7; d++) {
    if (!weekly.value[String(d)]) weekly.value[String(d)] = [];
  }
}

// ==== Countdown logic ====
const countdownMap = ref<Record<number, string>>({});
let timerHandle: number | null = null;

function parseDateTime(dIso: string, hm: string | undefined): Date | null {
  if (!dIso || !hm) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dIso));
  const t = /^(\d{2}):(\d{2})(?::(\d{2}))?/.exec(String(hm));
  if (!m || !t) return null;
  const y = parseInt(m[1], 10);
  const mo = parseInt(m[2], 10) - 1;
  const dd = parseInt(m[3], 10);
  const hh = parseInt(t[1], 10);
  const mi = parseInt(t[2], 10);
  const ss = t[3] ? parseInt(t[3], 10) : 0;
  return new Date(y, mo, dd, hh, mi, ss);
}

function fmtHMS(totalSeconds: number): string {
  if (totalSeconds < 0) totalSeconds = 0;
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

function updateCountdowns() {
  const map: Record<number, string> = {};
  const now = new Date();
  for (const p of PERIODS) {
    const rec = periodTimes.value[p as keyof typeof periodTimes.value] as any;
    if (!rec) {
      map[p] = "";
      continue;
    }
    const start = parseDateTime(dateStr.value, rec.start);
    const end = parseDateTime(dateStr.value, rec.end);
    if (!start || !end) {
      map[p] = "";
      continue;
    }
    if (now >= start && now <= end) {
      const remain = Math.floor((end.getTime() - now.getTime()) / 1000);
      map[p] = fmtHMS(remain);
    } else {
      map[p] = "";
    }
  }
  countdownMap.value = map;
}

function startTimer() {
  stopTimer();
  updateCountdowns();
  timerHandle = window.setInterval(updateCountdowns, 1000);
}
function stopTimer() {
  if (timerHandle != null) {
    window.clearInterval(timerHandle);
    timerHandle = null;
  }
}

async function loadMe() {
  try {
    const me = await getWingMe();
    const map: Record<number, string> = {};
    (me.wings?.ids || []).forEach((id: number, idx: number) => {
      map[id] = me.wings?.names?.[idx] || "جناح #" + id;
    });
    wingOptions.value = map;
    if (!wingId.value) {
      const keys = Object.keys(map);
      if (keys.length) wingId.value = Number(keys[0]);
    }
    // Reflect current selection in shared Wing context for header subtitle
    if (wingId.value) {
      const name = (wingOptions.value as any)[wingId.value] as string | undefined;
      try { setSelectedWing(wingId.value, name || null); } catch {}
    }
  } catch {
    wingOptions.value = {} as any;
  }
}

async function loadData() {
  if (!wingId.value) {
    await loadMe();
    if (!wingId.value) return;
  }
  loading.value = true;
  error.value = null;
  try {
    const res = await getWingTimetable({
      wing_id: wingId.value || undefined,
      date: dateStr.value,
      mode: mode.value,
    });
    // Extract period_times (prefer per-day if available)
    const metaRes = (res as any).meta || {};
    meta.value = metaRes as any;
    // Store API-reported dow for daily mode to drive grouped rendering condition
    if ((res as any).mode === 'daily' && typeof (res as any).dow === 'number') {
      resDow.value = Number((res as any).dow);
    } else {
      resDow.value = null;
    }
    // Update currentDow from selected date string
    try {
      const d = new Date(dateISO.value);
      // JS: Sunday=0..Saturday=6 → convert to school: Sun=1..Sat=7
      const js = d.getDay();
      currentDow.value = js === 0 ? 7 : js;
    } catch { currentDow.value = 1; }
    const byDay = (metaRes as any).period_times_by_day || null;
    const generic = (metaRes as any).period_times || {};
    // Save weekly per-day times as [start,end] tuples for quick lookup
    if (byDay && typeof byDay === 'object') {
      const map: Record<string, Record<number, [string, string]>> = {};
      Object.keys(byDay).forEach((d) => {
        const inner = (byDay as any)[d] || {};
        const rec: Record<number, [string, string]> = {} as any;
        Object.keys(inner).forEach((p) => {
          const v = inner[p as any];
          if (Array.isArray(v) && v.length >= 2) rec[Number(p)] = [String(v[0]), String(v[1])];
          else if (v && typeof v === 'object') {
            const s = (v as any).start || (v as any).start_time;
            const e = (v as any).end || (v as any).end_time;
            if (s && e) rec[Number(p)] = [String(s), String(e)];
          }
        });
        map[String(d)] = rec;
      });
      weeklyPeriodTimesByDay.value = map;
    } else {
      weeklyPeriodTimesByDay.value = {} as any;
    }
    const pt: Record<number, { start: string; end: string }> = {};
    let rawMap: any = generic;
    if ((res as any).mode === "daily" && byDay && typeof (res as any).dow === "number") {
      rawMap = byDay[String((res as any).dow)] || generic;
    }
    Object.keys(rawMap || {}).forEach((k) => {
      const v = (rawMap as any)[k];
      if (Array.isArray(v) && v.length >= 2) {
        pt[Number(k)] = { start: String(v[0]), end: String(v[1]) };
      } else if (v && typeof v === "object") {
        const s = (v as any).start || (v as any).start_time;
        const e = (v as any).end || (v as any).end_time;
        if (s || e) pt[Number(k)] = { start: String(s || ""), end: String(e || "") } as any;
      }
    });
    periodTimes.value = pt;

    // Parse tokenized columns/meta for daily and weekly
    if ((metaRes as any).columns && Array.isArray((metaRes as any).columns)) {
      dailyHeaderTokens.value = ((metaRes as any).columns as any[]).map(String);
    } else {
      dailyHeaderTokens.value = [];
    }
    if ((metaRes as any).slot_meta && typeof (metaRes as any).slot_meta === 'object') {
      dailySlotMeta.value = metaRes.slot_meta as any;
    } else {
      dailySlotMeta.value = {} as any;
    }
    if ((metaRes as any).columns_by_day && typeof (metaRes as any).columns_by_day === 'object') {
      weeklyColumnsByDay.value = metaRes.columns_by_day as any;
    } else {
      weeklyColumnsByDay.value = {} as any;
    }
    if ((metaRes as any).slot_meta_by_day && typeof (metaRes as any).slot_meta_by_day === 'object') {
      weeklySlotMetaByDay.value = metaRes.slot_meta_by_day as any;
    } else {
      weeklySlotMetaByDay.value = {} as any;
    }
    // Parse optional class-specific non-lesson times for the selected day
    if ((metaRes as any).non_lesson_times_by_class && typeof (metaRes as any).non_lesson_times_by_class === 'object') {
      const raw = metaRes.non_lesson_times_by_class as Record<string, Record<string, [string, string]>>;
      const mapped: Record<number, Record<string, [string, string]>> = {};
      Object.keys(raw).forEach((cid) => {
        const inner = raw[cid] || {} as any;
        const out: Record<string, [string, string]> = {} as any;
        Object.keys(inner).forEach((k) => {
          const v = inner[k] as any;
          if (Array.isArray(v) && v.length >= 2) {
            out[String(k).toLowerCase()] = [String(v[0]), String(v[1])];
          } else if (v && typeof v === 'object') {
            const s = (v as any).start || (v as any).start_time;
            const e = (v as any).end || (v as any).end_time;
            if (s && e) out[String(k).toLowerCase()] = [String(s), String(e)];
          }
        });
        mapped[Number(cid)] = out;
      });
      dailyNonLessonTimesByClass.value = mapped;
    } else {
      dailyNonLessonTimesByClass.value = {} as any;
    }

    if ((res as any).mode === "weekly") {
      weekly.value = (res as any).days || {};
      ensureWeeklyShape();
      if (!weekly.value[activeDayStr.value]) activeDay.value = 1;
    } else {
      dailyItems.value = (res as any).items || [];
    }
    // After data load, (re)start countdown timer for daily mode
    if (mode.value === "daily") startTimer();
    else stopTimer();
    // Measure and unify cell widths for daily view after DOM updates
    await nextTick();
    if (mode.value === "daily") {
      updateUnifiedCellWidth();
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || String(e);
  } finally {
    try { lastUpdated.value = timeAscii(new Date()); } catch {}
    loading.value = false;
  }
}

watch(wingId, (nv) => {
  try {
    const name = (wingOptions.value as any)[nv as any] as string | undefined;
    setSelectedWing(nv ?? null, name || null);
  } catch {}
});

onMounted(async () => {
  loadWeeklyWidths();
  await loadMe();
  await loadData();
  startTimer();
  setupResizeObserver();
});

onBeforeUnmount(() => {
  stopTimer();
  teardownResizeObserver();
});

// === Equalize daily cell width across items (based on longest content) ===
let _resizeHandler: any = null;

// Measure intrinsic width of a given element's text by cloning its computed text styles (safe with Vue scoped CSS)
function _measureElementText(el: HTMLElement | null): number {
  if (!el) return 0;
  const cs = window.getComputedStyle(el);
  const ruler = document.createElement("div");
  ruler.style.position = "absolute";
  ruler.style.visibility = "hidden";
  ruler.style.whiteSpace = "nowrap";
  ruler.style.pointerEvents = "none";
  ruler.style.zIndex = "-1";
  // Copy key text styles so measurement matches the real rendering even under scoped CSS
  ruler.style.font = cs.font; // shorthand includes weight/size/family when available
  ruler.style.fontSize = cs.fontSize;
  ruler.style.fontFamily = cs.fontFamily;
  ruler.style.fontWeight = cs.fontWeight as any;
  ruler.style.letterSpacing = cs.letterSpacing;
  ruler.style.textTransform = cs.textTransform as any;
  ruler.style.lineHeight = cs.lineHeight;
  ruler.textContent = el.textContent || "";
  document.body.appendChild(ruler);
  const rect = ruler.getBoundingClientRect();
  const w = Math.ceil(rect.width);
  ruler.remove();
  return w;
}

function updateUnifiedCellWidth() {
  if (mode.value !== "daily") {
    document.documentElement.style.removeProperty("--wing-cell-w");
    return;
  }
  try {
    const nodes = Array.from(document.querySelectorAll(".period-cell")) as HTMLElement[];
    if (!nodes.length) {
      document.documentElement.style.setProperty("--wing-cell-w", "160px");
      return;
    }
    let max = 0;
    for (const el of nodes) {
      const subjTextEl = el.querySelector(".cell-subject .subject-name") as HTMLElement | null;
      const teacherEl = el.querySelector(".cell-teacher") as HTMLElement | null;
      const iconWidth = 18; // approx icon + gap
      const gap = 8; // subject/teacher internal gap
      const subjW = (subjTextEl ? _measureElementText(subjTextEl) : 0) + iconWidth + gap;
      const teachW = teacherEl ? _measureElementText(teacherEl) : 0;
      const inner = Math.max(subjW, teachW);
      const paddings = 16; // .period-cell has 0.5rem left + 0.5rem right ≈ 16px total
      max = Math.max(max, inner + paddings);
    }
    // Double the measured width and clamp
    const increased = max * 2.0;
    const clamped = Math.max(160, Math.min(increased, 900));
    document.documentElement.style.setProperty("--wing-cell-w", clamped + "px");
  } catch {}
}
function setupResizeObserver() {
  if (_resizeHandler) return;
  _resizeHandler = () => {
    if (mode.value === "daily") {
      updateUnifiedCellWidth();
    }
  };
  window.addEventListener("resize", _resizeHandler);
}
function teardownResizeObserver() {
  if (_resizeHandler) {
    window.removeEventListener("resize", _resizeHandler);
    _resizeHandler = null;
  }
}
</script>

<style scoped>
.toolbar-controls .btn {
  white-space: nowrap;
}

/* Ensure inner content is centered at 95% of the card width (same pattern as TeacherTimetable) */
.in-card-95 {
  width: 95%;
  max-width: 100%;
  margin-inline: auto;
  display: block;
}

.slot-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.slot-card .icon-wrap {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  color: #8a1538;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
}
.tiny {
  font-size: 0.8rem;
}

.days-tabs {
  background: linear-gradient(135deg, #f8f9fa 0%, #edf1f5 100%);
  border-bottom: 1px solid #e9ecef;
}
.no-wrap {
  white-space: nowrap;
}
.one-line {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Multi-line truncation helpers */
.truncate-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
.truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Prevent content from forcing wrap: allow text to shrink within flex container */
.slot-card .flex-fill {
  min-width: 0;
}
.slot-card .icon-wrap,
.slot-card .badge {
  flex-shrink: 0;
}
/* Strong single-line header utility for period headers */
.hdr-line {
  display: flex;
  align-items: center;
  justify-content: center; /* center horizontally in weekly class header cell */
  gap: 0.5rem;
  white-space: nowrap;
  flex-wrap: nowrap;
}
.hdr-line > * {
  flex-shrink: 0;
}
.hdr-line .badge {
  white-space: nowrap;
}

/* 7×7 weekly grid styles */
.tt7-wrapper {
  display: block;
  width: 100%;
  padding: 12px;
}
.tt7-scroller {
  width: 100%;
  max-width: 100%;
  margin-inline: auto;
  overflow: auto;
}
.tt7-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 8px 6px;
  background: #fff;
  table-layout: fixed;
}
.tt7-th {
  background: linear-gradient(135deg, #f8f9fa 0%, #edf1f5 100%);
  color: #333;
  font-weight: 700;
  text-align: center;
  vertical-align: middle;
  padding: 0.75rem;
  border-bottom: 2px solid #e0e6ef;
  white-space: nowrap;
}
.tt7-th-period {
  text-align: center;
  position: sticky;
  inset-inline-start: 0;
  background: #fafbfc;
  border-inline-end: 1px solid #eef2f7;
  min-width: 180px;
  z-index: 2;
}
.tt7-th-sticky {
  position: sticky;
  inset-inline-start: 0;
  z-index: 3;
  background: #f8f9fb;
}
.tt7-td {
  vertical-align: middle;
  padding: 0.5rem;
  border-bottom: 1px solid #f0f2f5;
  border-inline-start: 1px solid #f6f7f9;
  height: 72px; /* contained height to reduce excessive tall rows */
  max-height: 72px;
  text-align: center;
}
.tt7-table tr:hover td {
  background: #fafbff;
}
.tt7-cell {
  display: flex;
  flex-direction: column;
  align-items: center; /* center horizontally */
  justify-content: center; /* center vertically within td height */
  gap: 6px;
  max-height: 100%;
  overflow: hidden; /* prevent inner scrollbars; let content wrap/truncate */
  padding: 2px;
}
.mini-cell {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 2px;
  padding: 0.35rem 0.5rem;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: #f5f7fb;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.mini-subj {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.1;
  max-width: 100%;
  overflow: hidden;
}
.mini-subj .subject-icon {
  font-size: 16px;
  color: var(--maron-primary, #8a1538);
  flex-shrink: 0;
}
.mini-teacher {
  font-size: 0.82rem;
  color: #6b7280;
  line-height: 1.1;
  text-align: center;
}
@media (max-width: 768px) {
  .tt7-th-period {
    position: static;
  }
  .mini-cell {
    flex-basis: 140px;
  }
}

/* New single-row daily layout */
.period-line {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  white-space: nowrap;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}
/* Make the items container fill the remaining row width and distribute cells across available space */
.period-line .items-inline {
  flex: 1;
  width: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  align-items: stretch;
  gap: 0.5rem;
}
.period-line .countdown {
  font-weight: 600;
}
/* Professional inline cells for each class in the period */
.period-cell {
  display: inline-flex;
  flex-direction: column;
  justify-content: center;
  align-items: center; /* center content horizontally within the cell */
  text-align: center; /* center text inside lines */
  width: 100%;
  min-width: 0; /* allow grid to control width via minmax */
  height: auto; /* allow the cell to grow to fit its content */
  min-height: 84px; /* ensure time line is always visible (fixes P7 clipping) */
  padding: 0.5rem 0.6rem;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: #f5f7fb;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.cell-subject {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  font-weight: 700;
  color: #1f2937; /* dark slate */
  line-height: 1.1;
  max-width: 100%;
  overflow: hidden;
}
.cell-subject .subject-icon {
  font-size: 16px;
  color: var(--maron-primary, #8a1538);
  flex-shrink: 0;
}
.cell-teacher {
  font-size: 0.82rem;
  color: #6b7280; /* muted */
  line-height: 1.1;
  text-align: center;
}
/* Ensure subject text can ellipsize within flex containers */
.subject-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.mini-teacher,
.cell-teacher {
  overflow-wrap: anywhere;
  word-break: break-word;
}
@media (max-width: 576px) {
  .period-cell {
    min-width: 120px;
    max-width: 180px;
  }
}
/* Column resizer (weekly 7×7) */
.resizable-th {
  position: relative;
}
.col-resizer {
  position: absolute;
  top: 0;
  bottom: 0;
  inset-inline-start: 0; /* works in RTL/LTR */
  width: 8px;
  cursor: col-resize;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.resizable-th:hover .col-resizer {
  opacity: 0.6;
}
.resizable-th .col-resizer::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  inset-inline-start: 3px;
  width: 2px;
  background: rgba(0, 0, 0, 0.1);
}
body.resizing {
  cursor: col-resize !important;
  user-select: none !important;
}

/* Print: ensure readable high-contrast */
@media print {
  .period-cell {
    background: #fff !important;
    border-color: #ccc !important;
    box-shadow: none !important;
  }
  .cell-subject {
    color: #000 !important;
  }
  .cell-teacher {
    color: #333 !important;
  }
  .col-resizer {
    display: none !important;
  }
}
</style>

<style>
@media print {
  @page {
    size: A4 portrait;
    margin: 10mm;
  }
  body {
    background: #fff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .navbar-maronia,
  .page-footer {
    display: none !important;
  }
  .toolbar-card,
  .days-tabs {
    display: none !important;
  }
  .print-header {
    display: block !important;
  }
  .auto-card {
    box-shadow: none !important;
    border: none !important;
  }
  .slot-card {
    box-shadow: none !important;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .full-bleed,
  section.full-bleed > * {
    width: 100% !important;
    margin: 0 !important;
  }
}
/* Hide print header on screen */
.print-header {
  display: none;
}
</style>

<style scoped>
/* Daily view cell spacing and readability */
.period-line { gap: 10px; padding-block: 6px; }
.period-line .items-inline { display: flex; flex-wrap: wrap; gap: 8px; }
.period-cell { padding: 8px 10px; border-radius: 8px; min-height: 56px; line-height: 1.3; display: flex; flex-direction: column; justify-content: center; }
.cell-subject { font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
.cell-teacher { color: #333; font-size: 0.95rem; }
.subject-icon { font-size: 16px; }

/* Weekly view: periods column styling */
.tt7-td-periods { vertical-align: top; }
.tt7-td-periods .periods-col { display: flex; flex-direction: column; gap: 6px; align-items: center; padding: 6px 4px; }

/* Weekly mini cells spacing between subject and teacher */
.mini-cell { padding: 4px 6px; border-radius: 8px; line-height: 1.2; }
.mini-cell .mini-subj { margin-bottom: 4px; display: flex; align-items: center; gap: 6px; font-weight: 600; }

/* Integrated daily table styles */
.tt-daily-scroller { overflow-x: hidden; overflow-y: auto; }
.tt-daily-table { width: 100%; border-collapse: separate; border-spacing: 0; table-layout: fixed; }
.tt-daily-table thead th { position: sticky; top: 0; background: linear-gradient(135deg, #fff7ed 0%, #ffefd9 100%); z-index: 1; text-align: center; vertical-align: middle; padding: 8px; border-bottom: 1px solid #f3d2a9; }
/* Ensure the sticky first-column header cell also uses the same header tone */
.tt-daily-table thead .tt-daily-th-sticky { background: linear-gradient(135deg, #fff7ed 0%, #ffefd9 100%); }
/* Weekly header row tone */
.tt7-table thead .tt7-th { background: linear-gradient(135deg, #fff7ed 0%, #ffefd9 100%); }
.tt-daily-th-sticky { position: sticky; right: 0; background: #fff; z-index: 2; box-shadow: -1px 0 0 #e5e7eb inset; }
.tt-daily-td, .tt-daily-th { padding: 8px; vertical-align: middle; border-bottom: 1px solid #f0f2f5; text-align: center; }
/* Ensure the first sticky header cell (الحصة) content is centered horizontally */
.tt-daily-th-sticky .d-flex { justify-content: center; }
.tt-daily-td { min-width: 120px; }
.tt-daily-td .period-cell { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 88px; }

/* Maroon separator between classes (applies to daily and weekly) */
tr.class-separator > th,
tr.class-separator > td { border-top: 3px solid #8a1538 !important; }

/* Enlarge class name to 3x current size */
.tt7-table .class-name-badge {
  font-size: 2.4rem; /* approx 3x default badge size */
  line-height: 1.1;
  padding: 8px 12px;
}
/* Daily: enlarge class name to 2x default size */
.tt-daily-table .class-name-badge {
  font-size: 1.6rem; /* approx 2x default badge size */
  line-height: 1.15;
  padding: 6px 10px;
}

/* Header row for classes in daily view (old strip) no longer used */
.classes-header { display: none; }
</style>

<style scoped>
/* Center content and add slight spacing between cells */
.tt-daily-table th,
.tt-daily-table td,
.tt7-table th,
.tt7-table td {
  vertical-align: middle;
  text-align: center;
}

/* Increase padding to create visual separation between cells */
.tt-daily-table td,
.tt7-table td {
  padding: 8px;
}

/* Daily view inner cells: center and increase height */
.period-cell,
.slot-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80px; /* slightly taller cells */
  gap: 4px; /* small space between lines inside the cell */
  border-radius: 10px;
  margin: 2px; /* small separation from adjacent cells */
}

/* Weekly view inner cells: center and increase height */
.mini-cell,
.tt7-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 66px; /* slightly taller than before */
  gap: 4px;
  border-radius: 8px;
}

/* Keep sticky header cells centered as well */
.th-sticky,
.tt7-th-sticky {
  text-align: center;
}

/* Add a subtle separation between table rows (visual breathing room) */
.tt-daily-table tbody tr + tr,
.tt7-table tbody tr + tr {
  border-top: 6px solid transparent;
}

/* Softer background for non-lesson slots to distinguish them */
.slot-cell {
  background-color: #f8f9fb;
}

/* Slightly larger header cell padding for better readability */
.resizable-th {
  padding: 10px 8px;
}
</style>