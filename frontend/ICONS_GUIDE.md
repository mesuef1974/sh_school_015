# 🎨 دليل الأيقونات الاحترافية

## المكتبات المتاحة عبر Iconify

المنصة تستخدم **@iconify/vue** التي توفر وصول لأكثر من **200,000 أيقونة** من مجموعات احترافية.

---

## 🌟 أفضل المجموعات الموصى بها

### 1. **Solar Icons** ⭐ (الأكثر عصرية)
- **العدد**: 1000+ أيقونة
- **الأنماط**: Linear, Bold, Bold Duotone
- **الاستخدام**: `solar:icon-name-bold-duotone`
- **مميزات**: تصميم عصري، duotone رائع، مثالي للتطبيقات الحديثة

```vue
<Icon icon="solar:user-bold-duotone" />
<Icon icon="solar:calendar-bold-duotone" />
<Icon icon="solar:chart-2-bold-duotone" />
<Icon icon="solar:home-smile-bold-duotone" />
<Icon icon="solar:bookmark-bold-duotone" />
```

**أمثلة للمنصة التعليمية:**
```vue
<!-- الطلبة -->
<Icon icon="solar:users-group-rounded-bold-duotone" />
<!-- الحضور -->
<Icon icon="solar:check-circle-bold-duotone" />
<!-- الغياب -->
<Icon icon="solar:close-circle-bold-duotone" />
<!-- التأخر -->
<Icon icon="solar:clock-circle-bold-duotone" />
<!-- الجدول -->
<Icon icon="solar:calendar-mark-bold-duotone" />
<!-- الإحصائيات -->
<Icon icon="solar:chart-bold-duotone" />
<!-- الإعدادات -->
<Icon icon="solar:settings-bold-duotone" />
<!-- الإشعارات -->
<Icon icon="solar:bell-bold-duotone" />
```

---

### 2. **Material Design Icons (MDI)**
- **العدد**: 7000+ أيقونة
- **الاستخدام**: `mdi:icon-name`
- **مميزات**: شامل جداً، كل الأيقونات التي تحتاجها

```vue
<Icon icon="mdi:account" />
<Icon icon="mdi:school" />
<Icon icon="mdi:calendar" />
<Icon icon="mdi:chart-line" />
```

---

### 3. **Heroicons** (Tailwind)
- **العدد**: 292 أيقونة
- **الأنماط**: Outline, Solid, Mini
- **الاستخدام**: `heroicons:icon-name`
- **مميزات**: نظيف، minimalist، مناسب للواجهات البسيطة

```vue
<Icon icon="heroicons:user-solid" />
<Icon icon="heroicons:calendar-solid" />
<Icon icon="heroicons:chart-bar-solid" />
```

---

### 4. **Lucide** (Modern Feather)
- **العدد**: 1400+ أيقونة
- **الاستخدام**: `lucide:icon-name`
- **مميزات**: خطوط نظيفة، حديث، مفتوح المصدر

```vue
<Icon icon="lucide:users" />
<Icon icon="lucide:calendar" />
<Icon icon="lucide:bar-chart-2" />
```

---

### 5. **Phosphor**
- **العدد**: 6000+ أيقونة
- **الأوزان**: Thin, Light, Regular, Bold, Fill, Duotone
- **الاستخدام**: `ph:icon-name-duotone`
- **مميزات**: أوزان متعددة، مرونة عالية

```vue
<Icon icon="ph:user-duotone" />
<Icon icon="ph:calendar-duotone" />
<Icon icon="ph:chart-line-duotone" />
```

---

### 6. **Tabler Icons**
- **العدد**: 4800+ أيقونة
- **الاستخدام**: `tabler:icon-name`
- **مميزات**: stroke consistent، نظيف جداً

```vue
<Icon icon="tabler:user" />
<Icon icon="tabler:calendar" />
<Icon icon="tabler:chart-line" />
```

---

## 📚 أيقونات خاصة بالمنصة التعليمية

### حالات الحضور والغياب

```vue
<!-- حاضر -->
<Icon icon="solar:check-circle-bold-duotone" class="text-success" />

<!-- غياب -->
<Icon icon="solar:close-circle-bold-duotone" class="text-danger" />

<!-- تأخر -->
<Icon icon="solar:clock-circle-bold-duotone" class="text-warning" />

<!-- إذن خروج -->
<Icon icon="solar:shield-check-bold-duotone" class="text-secondary" />

<!-- هروب -->
<Icon icon="solar:running-bold-duotone" class="text-danger" />

<!-- انصراف مبكر -->
<Icon icon="solar:exit-bold-duotone" class="text-warning" />
```

### الإدارة والتحكم

```vue
<!-- لوحة التحكم -->
<Icon icon="solar:widget-5-bold-duotone" />

<!-- الطلبة -->
<Icon icon="solar:users-group-rounded-bold-duotone" />

<!-- المعلمين -->
<Icon icon="solar:user-id-bold-duotone" />

<!-- الصفوف -->
<Icon icon="solar:layers-minimalistic-bold-duotone" />

<!-- الجدول الدراسي -->
<Icon icon="solar:calendar-mark-bold-duotone" />

<!-- المواد -->
<Icon icon="solar:book-2-bold-duotone" />
```

### التقارير والإحصائيات

```vue
<!-- الإحصائيات -->
<Icon icon="solar:chart-2-bold-duotone" />

<!-- التقارير -->
<Icon icon="solar:document-text-bold-duotone" />

<!-- الرسوم البيانية -->
<Icon icon="solar:graph-up-bold-duotone" />

<!-- التحليلات -->
<Icon icon="solar:pie-chart-2-bold-duotone" />
```

### الإجراءات الشائعة

```vue
<!-- حفظ -->
<Icon icon="solar:diskette-bold-duotone" />

<!-- تحديث -->
<Icon icon="solar:refresh-bold-duotone" />

<!-- حذف -->
<Icon icon="solar:trash-bin-trash-bold-duotone" />

<!-- تحرير -->
<Icon icon="solar:pen-bold-duotone" />

<!-- بحث -->
<Icon icon="solar:magnifer-bold-duotone" />

<!-- إضافة -->
<Icon icon="solar:add-circle-bold-duotone" />

<!-- طباعة -->
<Icon icon="solar:printer-bold-duotone" />

<!-- تصدير -->
<Icon icon="solar:export-bold-duotone" />

<!-- تحميل -->
<Icon icon="solar:download-bold-duotone" />

<!-- رفع -->
<Icon icon="solar:upload-bold-duotone" />
```

### الإشعارات والتنبيهات

```vue
<!-- إشعارات -->
<Icon icon="solar:bell-bold-duotone" />

<!-- تحذير -->
<Icon icon="solar:danger-triangle-bold-duotone" />

<!-- معلومات -->
<Icon icon="solar:info-circle-bold-duotone" />

<!-- نجاح -->
<Icon icon="solar:check-circle-bold-duotone" />

<!-- خطأ -->
<Icon icon="solar:close-circle-bold-duotone" />
```

---

## 🎨 استخدام الأيقونات في المكونات

### في DsButton
```vue
<DsButton icon="solar:diskette-bold-duotone" variant="primary">
  حفظ
</DsButton>
```

### في DsBadge
```vue
<DsBadge icon="solar:check-circle-bold-duotone" variant="success">
  حاضر
</DsBadge>
```

### مستقلة
```vue
<Icon icon="solar:user-bold-duotone" class="text-primary" width="24" height="24" />
```

### مع التحريك
```vue
<Icon icon="solar:refresh-bold-duotone" class="animate-spin" />
```

---

## 🔍 البحث عن الأيقونات

### المواقع الرسمية:
1. **Iconify**: https://icon-sets.iconify.design/
2. **Solar Icons**: https://icon-sets.iconify.design/solar/
3. **MDI**: https://icon-sets.iconify.design/mdi/
4. **Heroicons**: https://heroicons.com/
5. **Lucide**: https://lucide.dev/icons/
6. **Phosphor**: https://phosphoricons.com/

### نصائح البحث:
- ابحث باللغة الإنجليزية (user, calendar, chart)
- جرب مرادفات (people = users = accounts)
- استخدم المعاينة المباشرة في الموقع

---

## 🚀 الخلاصة والتوصيات

### للمنصة التعليمية:
✅ **Solar Icons** - الخيار الأفضل للواجهة الرئيسية (bold-duotone)
✅ **MDI** - للحالات الخاصة والأيقونات النادرة
✅ **Heroicons** - للعناصر البسيطة والأيقونات الصغيرة

### قواعد الاستخدام:
1. استخدم نمط واحد في الصفحة الواحدة (لا تخلط بين المجموعات)
2. فضّل `bold-duotone` من Solar للأيقونات الكبيرة
3. استخدم MDI للأيقونات الصغيرة أو النادرة
4. احتفظ بألوان دلالية (أخضر=نجاح، أحمر=خطر، أصفر=تحذير)

---

## 📦 التثبيت

الأيقونات مثبتة بالفعل عبر:

```json
{
  "@iconify/vue": "^4.1.2"
}
```

لا تحتاج لتثبيت أي شيء إضافي! جميع المجموعات تُحمّل عند الطلب.
