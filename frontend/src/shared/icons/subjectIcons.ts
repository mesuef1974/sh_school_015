// Centralized subject icon mapping used across all frontend pages
// Uses Iconify icon sets (solar:, mdi:, etc.). Ensure @iconify/vue is installed (already used globally).
//
// ما هي "القواعد" التي تحدد الأيقونة لكل مادة؟
// - يتم تمرير اسم المادة إلى الدالة subjectIcon(name)
// - قبل المطابقة نطبّع الاسم: نحذف التشكيل والتمطيط، نوحّد الهمزات والتاء المربوطة، نزيل الرموز والزخارف والمسافات الزائدة
// - نمرّ على SUBJECT_ICON_RULES (مصفوفة من تعبيرات منتظمة Regex)، وأول قاعدة تطابق الاسم تُعيد أيقونتها
// - إن لم تطابق أي قاعدة، نعود افتراضيًا إلى أيقونة "صح": solar:check-circle-bold-duotone لضمان وجود أيقونة لكل مادة دائمًا
//
// المجموعات الرئيسية للقواعد (أمثلة كلمات تُطابِق):
// 1) الرياضيات: رياضيات، جبر، هندسة، تفاضل، تكامل، إحصاء، Math
// 2) العلوم: فيزياء، كيمياء، أحياء/بيولوجيا، علوم/بيئة/جيولوجيا، مختبر
// 3) اللغات: عربية (قراءة/نحو/بلاغة)، إنجليزية/English/Eng/انكلش، فرنسي، ألماني، تركي، إسباني، إيطالي، صيني، ياباني، عبري، أردو/فارسي/كردي، "لغات" عامة
// 4) الحاسوب والتقنية: حاسوب/حاسب/كمبيوتر، برمجة/Coding/Software/هندسة برمجيات، AI/روبوتات/شبكات/قواعد بيانات/أمن معلومات/Cloud/ICT/IT
// 5) الدراسات الاجتماعية والوطنية: تاريخ، جغرافيا/جغرافيه، دراسات اجتماعية، مواطنة/وطنية، قانون/ثقافة/مدنيات، اقتصاد سياسي
// 6) الدراسات الإسلامية والأخلاق: دين، تربية إسلامية، قرآن/تجويد/تلاوة، حديث/سيرة، توحيد/فقه/عقيدة
// 7) الفنون والموسيقى والمسرح: فن/رسم/تشكيلي/خط عربي/تربية فنية، موسيقى، مسرح/دراما
// 8) التربية البدنية والصحة: رياضة/بدنية/PE/Health/سلامة/إسعافات
// 9) الأدلة الجنائية والجرائم: جنائي/أدلة جنائية/تحقيق جنائي/طب شرعي/بصمات
// 10) المهني والهندسي والمنزلي: نجارة/كهرباء/ميكانيكا/الكترونيات/ورش/مهنية/هندسة/صيانة/تبريد/تكييف/لحام، واقتصاد منزلي/تربية أسرية/خياطة/تغذية
// 11) الأعمال والاقتصاد: اقتصاد/محاسبة/مالية/تجارة/تسويق/مصارف/بنوك/ريادة/إدارة أعمال
// 12) المهارات الحياتية والمكتبة والإرشاد والخاص: مهارات/حياتية/كفايات، مكتبة/بحث، تعلم/تفكير نقدي/منطق/ابتكار، تربية خاصة/صعوبات تعلم
// 13) علم النفس: علم النفس/نفسي/Psychology
//
// كيفية إضافة/تعديل قاعدة:
// - أضف عنصرًا جديدًا في SUBJECT_ICON_RULES بالشكل { re: /نمط/i, icon: 'prefix:name' }
// - ضع القاعدة قبل قواعد أعمّ قد تلتقطها (مثل وضع "علم النفس" قبل "علوم")
// - لا تغيّر fallback حتى تبقى كل مادة بأيقونة دائمًا

// Light normalization to improve regex matching across Arabic variants and punctuation
function normalizeSubjectName(input: string): string {
  let s = (input || '').toLowerCase();
  // Trim and collapse whitespace
  s = s.trim().replace(/\s+/g, ' ');
  // Remove tatweel and Arabic diacritics (tashkeel)
  s = s.replace(/[\u0640\u064B-\u065F\u0670\u06D6-\u06ED]/g, '');
  // Unify common Arabic letter forms
  s = s
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ؤ/g, 'و')
    .replace(/ئ/g, 'ي')
    .replace(/ة/g, 'ه');
  // Remove common punctuation, brackets, slashes and dots often appended in labels
  s = s.replace(/[\-–—_\(\)\[\]\{\}«»\"'`~:،؛,.!?|\\/]+/g, ' ');
  // Remove emojis and miscellaneous symbols (push pins, music notes, etc.)
  try { s = s.replace(/[^\p{L}\p{N}\s]+/gu, ' '); } catch { /* older engines: ignore */ }
  // Remove decorative words sometimes appended
  s = s.replace(/\b(ماده|الماده|حصة|الحصه|الفصل|الترم|ترم|الفصل الدراسي)\b/g, ' ');
  // Collapse spaces again
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}

export const SUBJECT_ICON_RULES: { re: RegExp; icon: string }[] = [
  // Math & related
  { re: /(رياض|رياضيات|math|جبر|هندسه|مثلثات|تفاضل|تكامل|احصاء|تحليل|احتمالات|قياس)/i, icon: 'solar:calculator-bold-duotone' },
  // Psychology (put before generic "Sciences" so it doesn't get captured by "علوم")
  // Sciences
  { re: /(فيزياء|phys|كهرومغناطيس|ميكانيكا|فلك|فضاء)/i, icon: 'mdi:atom' },
  { re: /(كيمياء|chem|حيويه|عضويه|غير عضويه|تحليليه)/i, icon: 'mdi:flask' },
  { re: /(احياء|biology|bio|احياء دقيقه|علم الاحياء|بيولوجيا)/i, icon: 'mdi:dna' },
  { re: /(علوم|science|بيئه|بيئي|environment|جيولوجيا|علوم الارض|ارض|فضاء|جيولوجي)/i, icon: 'solar:test-tube-bold-duotone' },
  { re: /(مختبر|مختبرات|معمل|لاب|lab)/i, icon: 'mdi:flask-outline' },
  // Languages
  { re: /(لغه عربيه|اللغه العربيه|عربي|عرب|قراءه|كتابه|بلاغه|نحو|قواعد|املاء|تعبير)/i, icon: 'solar:book-line-duotone' },
  { re: /(لغة انجليزية|اللغه الانجليزيه|انجليز|انجليزي|english|eng|انكليزي|انكلش)/i, icon: 'solar:translate-bold-duotone' },
  { re: /(فرنسي|فرنساوي|فرنسيه|french)/i, icon: 'mdi:alpha-f-box' },
  { re: /(الماني|المانيه|german)/i, icon: 'mdi:alpha-g-box' },
  { re: /(تركي|تركيه|turkish)/i, icon: 'mdi:alpha-t-box' },
  { re: /(اسباني|اسبانبه|اسبانب|اسبان|spanish)/i, icon: 'mdi:alpha-s-box' },
  { re: /(ايطالي|ايطاليه|italian)/i, icon: 'mdi:alpha-i-box' },
  { re: /(صيني|صينيه|chinese)/i, icon: 'mdi:ideogram-cjk-variant' },
  { re: /(ياباني|يابانيه|japanese)/i, icon: 'mdi:ideogram-cjk' },
  { re: /(اردو|فارسي|فارسيه|كردي|كرديه|urdu|persian|farsi|kurdish)/i, icon: 'mdi:alphabetical-variant' },
  { re: /(عبري|عبريه|العبرية|hebrew)/i, icon: 'mdi:language-hebrew' },
  { re: /(لغات|لغه)/i, icon: 'solar:chat-square-like-bold-duotone' },
  // Tech/Computing
  { re: /(حاسوب|حاسب|كمبيوتر|تقنيه|تقانة|تكنولوجيا|معلومات|حاسوبيه|مهارات رقميه|برمجه|coding|برمج|ذكاء اصطناعي|ذكاء|ai|روبوت|روبوتات|شبكات|نظم|قواعد بيانات|database|امن معلومات|cyber|سحابي|سحابه|cloud|برمجيات|software|هندسه برمجيات|ict|it|computer science)/i, icon: 'solar:laptop-2-bold-duotone' },
  // Social Studies & National (History/Geography etc.)
  { re: /(تاريخ|جغرافيا|جغرافيه|الدراسات الاجتماعيه|دراسات اجتماعيه|اجتماع|اجتماعيات|علوم اجتماعيه|وطنيه|مواطنه|قانون|ثقافه|تربيه وطنيه|مدنيات|سياسه|اقتصاد سياسي|history|geography|social studies)/i, icon: 'solar:globe-bold-duotone' },
  // Islamic Studies & Ethics
  { re: /(دين|تربيه اسلاميه|اسلاميه|اسلاميات|قران|شرعيه|تفسير|حديث|سيره|تجويد|تلاوه|توحيد|فقه|اخلاق|عقيده|ثقافه دينيه|islamic|quran)/i, icon: 'solar:book-favorite-bold-duotone' },
  // Arts & Music & Theater
  { re: /(فن|رسم|تشكيلي|فنيه|موسيقى|مسرح|دراما|خط عربي|تربيه فنيه)/i, icon: 'solar:palette-bold-duotone' },
  // Physical Education & Health
  { re: /(رياضه|بدنيه|تربية بدنية|تربيه بدنيه وصحيه|pe|p\.e|physical education|health|صحه|سلامه|سلامه مروريه|اسعافات)/i, icon: 'solar:ball-basketball-bold-duotone' },
  // Forensic / Criminology
  { re: /(جنائي|جنائيه|جنائيات|ادله جنائيه|ادلة جنائيه|جرائم|تحقيق جنائي|علوم جنائيه|طب شرعي|بصمات)/i, icon: 'mdi:shield-search' },
  // Vocational, Engineering, Home Economics
  { re: /(تصميم|نجاره|ميكانيكا|كهرباء|الترون|الكترون|الكترونيات|كهروميكانيك|ورش|مهنيه|مهنه|حداده|هندسه|تطبيقيه|صيانه|تبريد|تكييف|لحام)/i, icon: 'mdi:cog' },
  { re: /(اقتصاد منزلي|تربيه اسريه|اسريه|منزليه|خياطه|تغذيه|منزلي|اسريه)/i, icon: 'mdi:silverware-fork-knife' },
  // Business & Economics
  { re: /(اقتصاد|محاسبه|ماليه|تجاره|رياده|مشروع|اداره|تسويق|مصارف|بنوك|ثقافه ماليه|اداره اعمال|business|accounting|finance|marketing|entrepreneurship)/i, icon: 'solar:graph-up-bold-duotone' },
  // Life skills, Library, Guidance, Special Ed
  { re: /(مهارات|حياتيه|كفايات حياتيه|كفاءات حياتيه|life|قيم|سلوك|مرشد|ارشاد|توجيه|قياده|اتصال|تواصل|مكتبه|بحث|بحث علمي|تعلم|تعلم نشط|تفكير نقدي|منطق|ابداع|ابتكار|تربيه خاصه|صعوبات تعلم|دعم تعلم)/i, icon: 'solar:leaf-bold-duotone' },
  // Psychology
  { re: /(علم النفس|علوم النفس|نفسي|نفسيه|psychology)/i, icon: 'mdi:brain' },
];

function isExcludedSubject(name?: string | null): boolean {
  const raw = (name ?? '').toString().trim();
  if (!raw) return true; // empty labels are excluded
  const s = normalizeSubjectName(raw);
  // Exclude the generic placeholder subject "عام" or labels that are just dashes
  if (s === 'عام' || s === '-' || s === 'عامه') return true;
  return false;
}

export function subjectIcon(name?: string | null): string {
  const raw = (name ?? '').toString();
  if (isExcludedSubject(raw)) return '';
  const sNorm = normalizeSubjectName(raw);
  const sRawLower = raw.toLowerCase();
  for (const r of SUBJECT_ICON_RULES) {
    if (r.re.test(sNorm) || r.re.test(sRawLower)) return r.icon;
  }
  // Fallback: show a clear check mark icon as agreed
  return 'solar:check-circle-bold-duotone';
}
