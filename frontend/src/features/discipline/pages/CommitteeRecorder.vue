
              <!-- مُحددات الإجراءات والعقوبات -->
              <div class="row g-3 align-items-end">
                <div class="col-md-6">
                  <label class="form-label">إجراءات من لائحة السلوك</label>
                  <select class="form-select" multiple v-model="form[it.id].actions">
                    <option v-for="a in options(it.id).actions" :key="'a:'+a" :value="a">{{ a }}</option>
                  </select>
                  <div class="form-text" v-if="suggest(it.id).actions.length">
                    اقتراح: {{ suggest(it.id).actions.join('، ') }}
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label">عقوبات (إن لزم)</label>
                  <select class="form-select" multiple v-model="form[it.id].sanctions">
                    <option v-for="s in options(it.id).sanctions" :key="'s:'+s" :value="s">{{ s }}</option>
                  </select>
                  <div class="form-text" v-if="suggest(it.id).sanctions.length">
                    اقتراح: {{ suggest(it.id).sanctions.join('، ') }}
                  </div>
                </div>
              </div>

              <!-- ملاحظة القرار وحفظ المسودة -->
              <div class="row g-3 align-items-end mt-1">
                <div class="col-md-9">
                  <label class="form-label">ملاحظة القرار (اختياري)</label>
                  <input type="text" class="form-control" v-model.trim="notes[it.id]" placeholder="اكتب ملاحظة مختصرة" />
                </div>
                <div class="col-md-3 d-grid">
                  <button class="btn btn-outline-secondary" @click="saveDraft(it.id)" :disabled="busyId===it.id" title="يحفظ الخيارات والملاحظة على متصفحك فقط">حفظ مسودة</button>
                </div>
              </div>

              <!-- أزرار الاعتماد -->
              <div class="d-flex flex-wrap gap-2 mt-3">
                <button class="btn btn-success" :disabled="busyId===it.id" @click="decide(it.id, 'approve', false)" title="اعتماد القرار دون إغلاق الواقعة">
                  اعتماد وإرسال إلى اللجنة
                </button>
                <button class="btn btn-primary" :disabled="busyId===it.id" @click="decide(it.id, 'approve', true)" title="اعتماد القرار وإغلاق الواقعة فورًا">
                  اعتماد وإغلاق
                </button>
                <button class="btn btn-warning text-dark" :disabled="busyId===it.id" @click="decide(it.id, 'return', false)" title="إعادة الواقعة لاستكمال بيانات/إجراءات قبل القرار">
                  إعادة لاستكمال
                </button>
                <button class="btn btn-outline-danger ms-auto" :disabled="busyId===it.id" @click="decide(it.id, 'reject', false)" title="رفض القرار">
                  رفض
                </button>
              </div>

              <!-- ملخص الأصوات -->
              <hr class="my-3" />
              <div v-if="!summaries[it.id]" class="small text-muted">—</div>
              <div v-else>
                <div class="small">النصاب: {{ summaries[it.id].summary.quorum }} · المشاركون: {{ summaries[it.id].summary.participated }}</div>
                <div class="mt-1 small">الأغلبية المقترحة: <strong>{{ decisionLabel(summaries[it.id].summary.majority) }}</strong></div>
                <div class="mt-2">
                  <span class="badge me-1 bg-success">موافقة: {{ summaries[it.id].summary.counts.approve }}</span>
                  <span class="badge me-1 bg-danger">رفض: {{ summaries[it.id].summary.counts.reject }}</span>
                  <span class="badge me-1 bg-warning text-dark">إعادة: {{ summaries[it.id].summary.counts.return }}</span>
                </div>
              </div>
            </div>
          </li>
          <li v-if="items.length===0" class="list-group-item">
            <div class="d-flex align-items-center">
              <span class="text-muted">لا توجد وقائع مجدولة لك كمقرّر في الوقت الحالي.</span>
              <RouterLink class="btn btn-sm btn-link ms-auto" to="/discipline/committee/dashboard">اذهب إلى لوحة الرئيس</RouterLink>
            </div>
          </li>
        </ul>
      </div>

      <div class="alert alert-secondary mt-3 small">
        ملاحظة: يقوم الرئيس باعتماد القرار النهائي من خلال «قرار اللجنة» في بطاقة الواقعة.
        هذه الصفحة تساعد المقرّر على متابعة الأصوات وتوثيق محضر القرار.
      </div>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { getMyCommittee, getCommitteeVotes, postCommitteeVote, getCommitteeCaps, getIncident, addIncidentAction } from '../../discipline/api';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';

const loading = ref(false);
const error = ref('');
const items = ref<any[]>([]);
const summaries = reactive<Record<string, any>>({});
const openId = ref<string>('');
const caps = ref<any>(null);
// تخزين تفصيلي لكل واقعة (للوصول إلى سياسة المخالفة واقتراحات الإجراء)
const fullById = reactive<Record<string, any>>({});
// نماذج اختيار الإجراءات والعقوبات
const form = reactive<Record<string, { actions: string[]; sanctions: string[] }>>({});
// ملاحظات القرار لكل واقعة
const notes = reactive<Record<string, string>>({});
const busyId = ref<string>('');

function sevClass(sev?: number){
  const s = Number(sev||1);
  return s>=4? 'bg-danger': s===3? 'bg-warning text-dark': s===2? 'bg-info text-dark': 'bg-success';
}
function decisionLabel(d?: string|null){
  return d==='approve'?'موافقة': d==='reject'?'رفض': d==='return'?'إعادة':'—';
}

const kpiQuorumMet = computed(()=> Object.values(summaries).filter((s:any)=> s?.summary?.quorum_met).length);
const kpiMajority = computed(()=>{
  const agg = { approve: 0, reject: 0, return: 0 } as Record<'approve'|'reject'|'return', number>;
  for (const s of Object.values(summaries) as any[]){
    const m = s?.summary?.majority as 'approve'|'reject'|'return'|null;
    if (m && agg[m] !== undefined) agg[m]++;
  }
  return agg;
});
function majClass(k: 'approve'|'reject'|'return'){
  if (k==='approve') return 'bg-success';
  if (k==='reject') return 'bg-danger';
  return 'bg-warning text-dark';
}

async function reload(){
  loading.value = true; error.value='';
  try{
    // نفس مصدر بيانات الأعضاء، لكن المقرّر يكون ضمن نفس المجموعة عادةً
    try { const c = await getCommitteeCaps(); caps.value = c?.access_caps || null; } catch {}
    items.value = await getMyCommittee();
    for (const it of items.value){
      // حمّل تمثيلًا كاملاً للوصول إلى Violation.policy والافتراضات
      try { fullById[it.id] = await getIncidentFull(it.id); } catch {}
      // تهيئة نموذج الاختيارات إن لم يكن موجودًا
      if (!form[it.id]) {
        // حاول استعادة مسودة محفوظة محليًا، وإلا استخدم الاقتراحات
        const draft = loadDraft(it.id);
        if (draft) {
          form[it.id] = { actions: [...(draft.actions||[])], sanctions: [...(draft.sanctions||[])] };
          notes[it.id] = draft.note || '';
        } else {
          const sug = suggest(it.id);
          form[it.id] = { actions: [...sug.actions], sanctions: [...sug.sanctions] };
          notes[it.id] = '';
        }
      }
    }
  }catch(e:any){
    error.value = e?.message || 'تعذّر تحميل البيانات';
  }finally{
    loading.value = false;
  }
}

function toggle(id: string){
  // Ensure form model exists before binding to v-model (prevents invalid assignment targets)
  if (!form[id]) {
    const sug = suggest(id);
    form[id] = { actions: [...sug.actions], sanctions: [...sug.sanctions] };
  }
  // حاول أيضًا استعادة ملاحظة أو نموذج من المسودة المحلية
  const d = loadDraft(id);
  if (d) {
    if (d.actions) form[id].actions = [...d.actions];
    if (d.sanctions) form[id].sanctions = [...d.sanctions];
    notes[id] = d.note || notes[id] || '';
  }
  // Lazy-load votes summary on first expand to reduce initial API calls
  if (!summaries[id]) {
    getCommitteeVotes(id).then((res)=> { summaries[id] = res; }).catch(()=>{});
  }
  openId.value = (openId.value===id? '': id);
}

// خيارات من الكتالوج: افتراضيات + سياسة حسب التكرار
function options(id: string){
  const f = fullById[id] || {};
  const viol = f?.violation_obj || {};
  const policy = viol?.policy || {};
  const defaultsA: string[] = Array.isArray(viol?.default_actions) ? viol.default_actions : [];
  const defaultsS: string[] = Array.isArray(viol?.default_sanctions) ? viol.default_sanctions : [];
  // اجمع كل الإجراءات/العقوبات المذكورة في السياسة عبر جميع التكرارات كخيارات متاحة
  const byRepA = (policy?.actions_by_repeat && typeof policy.actions_by_repeat === 'object') ? policy.actions_by_repeat : {};
  const byRepS = (policy?.sanctions_by_repeat && typeof policy.sanctions_by_repeat === 'object') ? policy.sanctions_by_repeat : {};
  const polA: string[] = Object.values(byRepA).flat().filter((x:any)=> typeof x === 'string');
  const polS: string[] = Object.values(byRepS).flat().filter((x:any)=> typeof x === 'string');
  const actions = Array.from(new Set([...(defaultsA||[]), ...polA]));
  const sanctions = Array.from(new Set([...(defaultsS||[]), ...polS]));
  return { actions, sanctions };
}

// اقتراحات حسب عدد التكرار داخل النافذة
function suggest(id: string){
  const base = { actions: [] as string[], sanctions: [] as string[] };
  const f = fullById[id] || {};
  const viol = f?.violation_obj || {};
  const policy = viol?.policy || {};
  const rep = Number((f?.repeat_count_in_window ?? 0) as number);
  try{
    const aMap = (policy?.actions_by_repeat && typeof policy.actions_by_repeat === 'object') ? policy.actions_by_repeat : {};
    const sMap = (policy?.sanctions_by_repeat && typeof policy.sanctions_by_repeat === 'object') ? policy.sanctions_by_repeat : {};
    const a = aMap?.[String(rep)] || aMap?.[rep] || [];
    const s = sMap?.[String(rep)] || sMap?.[rep] || [];
    base.actions = Array.isArray(a) ? a.filter((x:any)=> typeof x === 'string') : [];
    base.sanctions = Array.isArray(s) ? s.filter((x:any)=> typeof x === 'string') : [];
  }catch{}
  // fallback: في أول مرة اقترح أول إجراء افتراضي إن وجد
  if (!base.actions?.length){
    const defA: string[] = Array.isArray(viol?.default_actions) ? viol.default_actions : [];
    if (defA.length) base.actions = [defA[0]];
  }
  return base;
}

// اعتماد القرار وتمرير الإجراءات/العقوبات المختارة
async function decide(id: string, decision: 'approve'|'reject'|'return', closeNow: boolean){
  busyId.value = id;
  try{
    if (decision === 'approve' && closeNow) {
      const ok = window.confirm('هل أنت متأكد من اعتماد القرار وإغلاق الواقعة فورًا؟');
      if (!ok) { busyId.value = ''; return; }
    }
    const sel = form[id] || { actions: [], sanctions: [] };
    const now = new Date().toISOString();
    const mapList = (arr: string[]) => arr.map((name) => ({ name, at: now, from_catalog: true }));
    const payload: any = { decision, note: (notes[id]||'').trim(), close_now: closeNow };
    if (sel.actions?.length) payload.actions = mapList(sel.actions);
    if (sel.sanctions?.length) payload.sanctions = mapList(sel.sanctions);
    await postCommitteeDecision(id, payload);
    alert('تم اعتماد القرار وإرساله إلى رئيس اللجنة والأعضاء لاتخاذ القرار.');
    // تحديث الملخص وربما إخفاء اللوحة
    try { summaries[id] = await getCommitteeVotes(id); } catch {}
    // بعد نجاح الاعتماد، احذف المسودة المحلية
    try { removeDraft(id); } catch {}
  }catch(e:any){
    alert(e?.response?.data?.detail || e?.message || 'تعذّر اعتماد القرار');
  }finally{
    busyId.value = '';
  }
}

onMounted(()=> reload());

// ======================= وظائف الطباعة (HTML — خيار A) =======================
function fmtDate(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s as string; } }

async function printPledgeById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `PLEDG-${y}${m}-${shortId}`;
    const proposed = data.proposed_summary || '—';
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تعهد خطي — ${studentName}</title>
  <style>
    :root{ --fg:#111; --muted:#666; --accent:#0d6efd; }
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; color:var(--fg); margin:0; }
    header, footer{ position: fixed; left: 0; right: 0; }
    header{ top: 0; padding: 12px 24px; border-bottom: 1px solid #ddd; }
    footer{ bottom: 0; padding: 8px 24px; border-top: 1px solid #ddd; color: var(--muted); font-size: 11px; }
    main{ padding: 120px 24px 80px; max-width: 820px; margin: 0 auto; }
    h1{ font-size: 18px; margin: 0 0 12px; }
    .row{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px 16px; }
    .box{ border: 1px solid #ccc; padding: 12px; border-radius: 6px; }
    .muted{ color: var(--muted); font-size: 12px; }
    .sig-grid{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }
    .sig{ border: 1px dashed #999; min-height: 72px; padding: 8px; }
    .qr{ width: 96px; height: 96px; border: 1px solid #ccc; display: inline-block; background:
      repeating-linear-gradient(45deg,#eee 0,#eee 8px,#ddd 8px,#ddd 16px); }
    .meta{ margin-top: 10px; font-size: 12px; color: var(--muted); }
    @media print { @page { size: A4; margin: 2cm; } header, footer { position: fixed; } main{ padding: 0; margin-top: 40px; } .no-print{ display: none !important; } }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div class="muted" style="margin-inline-start:auto">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي · صفحة 1 من 1 · للتحقق امسح رمز QR</footer>
    <main>
      <h1>تعهد خطي بشأن التزام السلوك المدرسي</h1>
      <div class="row box" style="margin-bottom:12px;">
        <div><div class="muted">الطالب</div><div>${studentName}</div></div>
        <div><div class="muted">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class="muted">التاريخ</div><div>${occurred}</div></div>
        <div><div class="muted">المخالفة</div><div>${viol}</div></div>
      </div>
      <div class="box">
        <p>أنا الطالب/ـة المذكور أعلاه، أقرّ بأنني اطّلعت على الواقعة رقم ${shortId} وأتعهد بالالتزام بقواعد السلوك والانضباط المدرسي، والتعاون مع المدرسة خلال فترة المتابعة.</p>
        <ol>
          <li>الالتزام التام بالقواعد وتجنب تكرار المخالفة.</li>
          <li>التعاون مع الهيئتين التعليمية والإرشادية عند الطلب.</li>
          <li>قبول المتابعة الدورية والامتثال للتوجيهات.</li>
          <li>العلم بأن تكرار المخالفة قد يترتب عليه إجراءات أشد وفق اللوائح.</li>
        </ol>
        <div class="muted">ملخص الإجراء/التوصية (إن وُجد):</div>
        <div style="font-weight:600; margin-bottom:8px;">${proposed}</div>
        <div class="sig-grid">
          <div class="sig"><div class="muted">توقيع الطالب/ـة</div></div>
          <div class="sig"><div class="muted">توقيع ولي الأمر</div></div>
          <div class="sig"><div class="muted">ختم المدرسة / موظف الاستلام</div></div>
        </div>
        <div class="meta">رقم الوثيقة: ${docId}</div>
        <div style="margin-top:8px; display:flex; align-items:center; gap:12px;">
          <div class="qr" aria-label="QR placeholder"></div>
          <div class="muted">سيتم توليد رمز QR في الإصدار القادم (خيار B). حالياً يُستخدم رقم الوثيقة للتحقق الداخلي.</div>
        </div>
      </div>
    </main>
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'تعهد خطي (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة التعهد'); }
}

async function printOralById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    if (Number(data.severity||0) > 1) { alert('التنبيه الشفهي مخصص للوقائع البسيطة (مستوى 1)'); return; }
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `ORAL-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const viol = data.violation_display || data.violation_code || '—';
    const occurred = fmtDate(data.occurred_at);
    const html = `<!DOCTYPE html>
<html lang=\"ar\" dir=\"rtl\">
<head>
  <meta charset=\"utf-8\" />
  <title>تنبيه شفهي — ${studentName}</title>
  <style>
    :root{ --fg:#111; --muted:#666; }
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; color:var(--fg); margin:0; }
    header, footer{ position: fixed; left: 0; right: 0; }
    header{ top: 0; padding: 12px 24px; border-bottom: 1px solid #ddd; }
    footer{ bottom: 0; padding: 8px 24px; border-top: 1px solid #ddd; color: var(--muted); font-size: 11px; }
    main{ padding: 100px 24px 80px; max-width: 820px; margin: 0 auto; }
    h1{ font-size: 18px; margin: 0 0 12px; }
    .row{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px 16px; }
    .box{ border: 1px solid #ccc; padding: 12px; border-radius: 6px; }
    .muted{ color: var(--muted); font-size: 12px; }
    .sig{ border: 1px dashed #999; min-height: 64px; padding: 8px; margin-top: 12px; }
    @media print { @page { size: A4; margin: 2cm; } header, footer { position: fixed; } main{ padding: 0; margin-top: 40px; } }
  </style>
  </head>
  <body>
    <header>
      <div style=\"display:flex; align-items:center; gap:12px;\">
        <div style=\"font-weight:700;\">نظام السلوك المدرسي</div>
        <div class=\"muted\" style=\"margin-inline-start:auto\">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي · صفحة 1 من 1</footer>
    <main>
      <h1>تنبيه شفهي للطالب/ـة</h1>
      <div class=\"row box\" style=\"margin-bottom:12px;\">
        <div><div class=\"muted\">الطالب</div><div>${studentName}</div></div>
        <div><div class=\"muted\">رقم الواقعة</div><div>${shortId}</div></div>
        <div><div class=\"muted\">التاريخ</div><div>${occurred}</div></div>
        <div><div class=\"muted\">المخالفة</div><div>${viol}</div></div>
      </div>
      <div class=\"box\">
        <p>تم توجيه <strong>تنبيه شفهي</strong> للطالب/ـة المذكور أعلاه بخصوص الواقعة المشار إليها، مع التأكيد على الالتزام بقواعد السلوك والانضباط وعدم تكرار المخالفة.</p>
        <ul>
          <li>فهم أثر المخالفة على البيئة التعليمية.</li>
          <li>التعهّد بالالتزام مستقبلاً والتعاون مع المعنيين.</li>
        </ul>
        <div class=\"muted\">ملاحظات المبلّغ/المراجع (اختياري): _______________________________</div>
        <div class=\"sig\"><div class=\"muted\">توقيع الموظف</div></div>
      </div>
    </main>
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'تنبيه شفهي (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة التنبيه الشفهي'); }
}

async function printActsById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `ACTS-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const items: any[] = Array.isArray(data.actions_applied)? data.actions_applied : [];
    const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>إجراءات اللجنة — ${studentName}</title>
  <style>
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin:0; }
    header, footer{ position: fixed; left:0; right:0; }
    header{ top:0; padding:12px 24px; border-bottom:1px solid #ddd; }
    footer{ bottom:0; padding:8px 24px; border-top:1px solid #ddd; color:#666; font-size:11px; }
    main{ padding: 90px 24px 70px; max-width: 900px; margin:0 auto; }
    table{ width:100%; border-collapse: collapse; }
    th,td{ border:1px solid #ccc; padding:6px 8px; font-size: 13px; }
    th{ background:#f8f9fa; }
    h1{ font-size: 18px; margin: 0 0 10px; }
    @media print{ @page{ size:A4; margin:2cm; } header,footer{ position: fixed; } }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div style="margin-inline-start:auto; color:#666;">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي</footer>
    <main>
      <h1>إجراءات اللجنة المعتمدة/المقترحة</h1>
      <div style="margin-bottom:8px; color:#555;">الطالب: <strong>${studentName}</strong> · الواقعة: ${shortId}</div>
      <table>
        <thead><tr><th>#</th><th>الإجراء</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد إجراءات —</td></tr>'}</tbody>
      </table>
    </main>
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'إجراءات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة إجراءات اللجنة'); }
}

async function printSancById(incidentId: string){
  try{
    const data:any = await getIncident(incidentId);
    const now = new Date(); const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0');
    const shortId = String(data.id || '').slice(0,8);
    const docId = `SANC-${y}${m}-${shortId}`;
    const studentName = data.student_name || `#${data.student}`;
    const items: any[] = Array.isArray(data.sanctions_applied)? data.sanctions_applied : [];
    const rows = items.map((a:any,idx:number)=> `<tr><td>${idx+1}</td><td>${(a?.name||'').toString()}</td><td>${(a?.notes||'').toString()}</td><td>${a?.at? new Date(a.at).toLocaleString(): ''}</td></tr>`).join('');
    const html = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>عقوبات اللجنة — ${studentName}</title>
  <style>
    body{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin:0; }
    header, footer{ position: fixed; left:0; right:0; }
    header{ top:0; padding:12px 24px; border-bottom:1px solid #ddd; }
    footer{ bottom:0; padding:8px 24px; border-top:1px solid #ddd; color:#666; font-size:11px; }
    main{ padding: 90px 24px 70px; max-width: 900px; margin:0 auto; }
    table{ width:100%; border-collapse: collapse; }
    th,td{ border:1px solid #ccc; padding:6px 8px; font-size: 13px; }
    th{ background:#f8f9fa; }
    h1{ font-size: 18px; margin: 0 0 10px; }
    @media print{ @page{ size:A4; margin:2cm; } header,footer{ position: fixed; } }
  </style>
  </head>
  <body>
    <header>
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="font-weight:700;">نظام السلوك المدرسي</div>
        <div style="margin-inline-start:auto; color:#666;">رقم الوثيقة: ${docId} · تاريخ الإصدار: ${y}-${m}-${d}</div>
      </div>
    </header>
    <footer>سري — للاستخدام المدرسي</footer>
    <main>
      <h1>عقوبات اللجنة المعتمدة/المقترحة</h1>
      <div style="margin-bottom:8px; color:#555;">الطالب: <strong>${studentName}</strong> · الواقعة: ${shortId}</div>
      <table>
        <thead><tr><th>#</th><th>العقوبة</th><th>ملاحظات</th><th>التاريخ/الوقت</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="4" style="text-align:center; color:#888;">— لا توجد عقوبات —</td></tr>'}</tbody>
      </table>
    </main>
    <script>window.onload = function(){ setTimeout(function(){ window.print(); }, 50); };<\/script>
  </body>
</html>`;
    const w = window.open('', '_blank', 'noopener,noreferrer'); if(!w) throw new Error('تعذّر فتح نافذة الطباعة.');
    w.document.open(); w.document.write(html); w.document.close();
    try { await addIncidentAction(incidentId, { name: 'عقوبات اللجنة (طباعة)', notes: 'رقم الوثيقة: '+docId }); } catch {}
  }catch(e:any){ alert(e?.message || 'فشل في طباعة عقوبات اللجنة'); }
}

// ---- مسودات محلية ----
function draftKey(id: string){ return `committeeDraft:${id}`; }
function saveDraft(id: string){
  try{
    const data = { actions: [...(form[id]?.actions||[])], sanctions: [...(form[id]?.sanctions||[])], note: (notes[id]||'').trim() };
    localStorage.setItem(draftKey(id), JSON.stringify(data));
    alert('تم حفظ المسودة محليًا');
  }catch{}
}
function loadDraft(id: string): { actions?: string[]; sanctions?: string[]; note?: string } | null {
  try{
    const raw = localStorage.getItem(draftKey(id));
    if (!raw) return null;
    const obj = JSON.parse(raw);
    if (obj && typeof obj === 'object') return obj;
    return null;
  }catch{ return null; }
}
function removeDraft(id: string){ try{ localStorage.removeItem(draftKey(id)); }catch{} }
</script>

<style scoped>
.committee-page .card { border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
.committee-page .card + .card { margin-top: 1.25rem; }
.committee-page .row { --bs-gutter-x: 3rem; --bs-gutter-y: 2.5rem; }
.list-group-item { padding-top: .9rem; padding-bottom: .9rem; }
.kpi { padding: 12px 14px; }
.kpi-title { font-size: 12px; color: #666; padding: 6px 12px 0; }
.kpi-value { font-size: 24px; font-weight: 700; padding: 0 12px 10px; }
.kpis { --bs-gutter-x: 2.5rem; --bs-gutter-y: 1.5rem; }

.form-text { color: #6c757d; }

@media (max-width: 768px){
  .committee-page .row { --bs-gutter-x: 1.25rem; --bs-gutter-y: 1.25rem; }
}
</style>
