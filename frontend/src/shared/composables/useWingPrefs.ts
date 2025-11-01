import { reactive, toRefs, watch } from "vue";

export type ApprovalsMode = "daily" | "period";
export type ExitsStatus = "pending" | "approved" | "rejected" | "open_now";
export type DateMode = "today" | "remember" | "last";
export type DailyClassBehavior = "none" | "remember" | "default_class";

export interface StudentsColumnsVisibility {
  show_parent: boolean;
  show_parent_phone: boolean;
  show_extra_phone: boolean;
  show_needs: boolean;
  show_active: boolean;
  show_day_state: boolean;
}

export interface StudentsExportColumns {
  parent_name: boolean;
  parent_phone: boolean;
  extra_phone_no: boolean;
  phone_no: boolean;
  active: boolean;
  needs: boolean;
}

export interface WingPrefs {
  version: number;
  default_wing_id: number | null;
  default_class_id: number | null;
  students_search_limit: number; // max students to fetch/show in wing/classes page
  enable_csv_buttons: boolean; // show CSV export buttons where supported
  remember_filters: boolean; // persist per-page filters in localStorage
  // New in v2
  default_date_mode: DateMode; // how pages initialize date pickers
  approvals_default_mode: ApprovalsMode; // default view in approvals page
  exits_default_status: ExitsStatus; // default status filter in exits page
  daily_class_filter_behavior: DailyClassBehavior; // how daily page chooses class filter
  students_columns_visibility: StudentsColumnsVisibility; // columns in wing/classes table (on-screen)
  students_export_columns: StudentsExportColumns; // extra columns to include on export only
  contact_actions_enabled: boolean; // enable tel: and copy buttons
  csv_include_headers: boolean; // include header row in CSV exports
  apply_on_load: {
    classes: boolean;
    approvals: boolean;
    daily: boolean;
    exits: boolean;
  };
  // New in v3: default print options for the centralized print panel
  print_defaults: {
    orientation: 'portrait' | 'landscape';
    margin_cm: number; // 0.5 .. 2 typically
    scale: 50 | 60 | 70 | 80 | 90 | 100 | 110;
    density: 'normal' | 'compact';
    clean: boolean; // clean mode default
    grid: boolean;  // show table borders by default
    one_page: boolean; // clip to one page by default
  };
}

const STORAGE_KEY = "wing.prefs.v2";
const CURRENT_VERSION = 3;

function defaults(): WingPrefs {
  return {
    version: CURRENT_VERSION,
    default_wing_id: null,
    default_class_id: null,
    students_search_limit: 300,
    enable_csv_buttons: true,
    remember_filters: true,
    default_date_mode: "today",
    approvals_default_mode: "period",
    exits_default_status: "pending",
    daily_class_filter_behavior: "remember",
    students_columns_visibility: {
      show_parent: true,
      show_parent_phone: true,
      show_extra_phone: false,
      show_needs: true,
      show_active: true,
      show_day_state: true,
    },
    students_export_columns: {
      parent_name: false,
      parent_phone: true,
      extra_phone_no: false,
      phone_no: false,
      active: false,
      needs: false,
    },
    contact_actions_enabled: true,
    csv_include_headers: true,
    apply_on_load: {
      classes: true,
      approvals: true,
      daily: true,
      exits: true,
    },
    print_defaults: {
      orientation: 'portrait',
      margin_cm: 1,
      scale: 100,
      density: 'normal',
      clean: false,
      grid: true,
      one_page: false,
    },
  };
}

function migrateV1(obj: any): WingPrefs {
  const d = defaults();
  return {
    ...d,
    default_wing_id: typeof obj.default_wing_id === "number" ? obj.default_wing_id : d.default_wing_id,
    default_class_id: typeof obj.default_class_id === "number" ? obj.default_class_id : d.default_class_id,
    students_search_limit:
      typeof obj.students_search_limit === "number" && obj.students_search_limit > 0 ? obj.students_search_limit : d.students_search_limit,
    enable_csv_buttons: typeof obj.enable_csv_buttons === "boolean" ? obj.enable_csv_buttons : d.enable_csv_buttons,
    remember_filters: typeof obj.remember_filters === "boolean" ? obj.remember_filters : d.remember_filters,
  };
}

function safeParse(val: string | null): WingPrefs {
  if (!val) return defaults();
  try {
    const obj = JSON.parse(val);
    const d = defaults();
    // Detect older storage key content (v1)
    if (obj && (obj.version === 1 || !("version" in obj))) {
      return migrateV1(obj);
    }
    // v2 and beyond
    const out: WingPrefs = {
      version: CURRENT_VERSION,
      default_wing_id: typeof obj.default_wing_id === "number" ? obj.default_wing_id : d.default_wing_id,
      default_class_id: typeof obj.default_class_id === "number" ? obj.default_class_id : d.default_class_id,
      students_search_limit:
        typeof obj.students_search_limit === "number" && obj.students_search_limit > 0 ? obj.students_search_limit : d.students_search_limit,
      enable_csv_buttons: typeof obj.enable_csv_buttons === "boolean" ? obj.enable_csv_buttons : d.enable_csv_buttons,
      remember_filters: typeof obj.remember_filters === "boolean" ? obj.remember_filters : d.remember_filters,
      default_date_mode: ["today", "remember", "last"].includes(obj.default_date_mode) ? obj.default_date_mode : d.default_date_mode,
      approvals_default_mode: ["daily", "period"].includes(obj.approvals_default_mode) ? obj.approvals_default_mode : d.approvals_default_mode,
      exits_default_status: ["pending", "approved", "rejected", "open_now"].includes(obj.exits_default_status)
        ? obj.exits_default_status
        : d.exits_default_status,
      daily_class_filter_behavior: ["none", "remember", "default_class"].includes(obj.daily_class_filter_behavior)
        ? obj.daily_class_filter_behavior
        : d.daily_class_filter_behavior,
      students_columns_visibility: {
        show_parent: !!(obj.students_columns_visibility?.show_parent ?? d.students_columns_visibility.show_parent),
        show_parent_phone: !!(obj.students_columns_visibility?.show_parent_phone ?? d.students_columns_visibility.show_parent_phone),
        show_extra_phone: !!(obj.students_columns_visibility?.show_extra_phone ?? d.students_columns_visibility.show_extra_phone),
        show_needs: !!(obj.students_columns_visibility?.show_needs ?? d.students_columns_visibility.show_needs),
        show_active: !!(obj.students_columns_visibility?.show_active ?? d.students_columns_visibility.show_active),
        show_day_state: !!(obj.students_columns_visibility?.show_day_state ?? d.students_columns_visibility.show_day_state),
      },
      students_export_columns: {
        parent_name: !!(obj.students_export_columns?.parent_name ?? d.students_export_columns.parent_name),
        parent_phone: !!(obj.students_export_columns?.parent_phone ?? d.students_export_columns.parent_phone),
        extra_phone_no: !!(obj.students_export_columns?.extra_phone_no ?? d.students_export_columns.extra_phone_no),
        phone_no: !!(obj.students_export_columns?.phone_no ?? d.students_export_columns.phone_no),
        active: !!(obj.students_export_columns?.active ?? d.students_export_columns.active),
        needs: !!(obj.students_export_columns?.needs ?? d.students_export_columns.needs),
      },
      contact_actions_enabled: typeof obj.contact_actions_enabled === "boolean" ? obj.contact_actions_enabled : d.contact_actions_enabled,
      csv_include_headers: typeof obj.csv_include_headers === "boolean" ? obj.csv_include_headers : d.csv_include_headers,
      apply_on_load: {
        classes: !!(obj.apply_on_load?.classes ?? d.apply_on_load.classes),
        approvals: !!(obj.apply_on_load?.approvals ?? d.apply_on_load.approvals),
        daily: !!(obj.apply_on_load?.daily ?? d.apply_on_load.daily),
        exits: !!(obj.apply_on_load?.exits ?? d.apply_on_load.exits),
      },
      print_defaults: {
        orientation: (obj.print_defaults?.orientation === 'landscape' ? 'landscape' : 'portrait'),
        margin_cm: (typeof obj.print_defaults?.margin_cm === 'number' ? Math.max(0.5, Math.min(5, obj.print_defaults.margin_cm)) : d.print_defaults.margin_cm),
        scale: ([50,60,70,80,90,100,110] as number[]).includes(obj.print_defaults?.scale) ? obj.print_defaults.scale : d.print_defaults.scale,
        density: (obj.print_defaults?.density === 'compact' ? 'compact' : 'normal'),
        clean: !!(obj.print_defaults?.clean ?? d.print_defaults.clean),
        grid: !!(obj.print_defaults?.grid ?? d.print_defaults.grid),
        one_page: !!(obj.print_defaults?.one_page ?? d.print_defaults.one_page),
      },
    };
    return out;
  } catch {
    return defaults();
  }
}

let state = reactive<WingPrefs>(safeParse(localStorage.getItem(STORAGE_KEY) || localStorage.getItem("wing.prefs.v1")));

function saveNow() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    // ignore quota errors
  }
}

// Auto-save on change
watch(
  () => ({ ...state }),
  () => saveNow(),
  { deep: true }
);

export function useWingPrefs() {
  function set<K extends keyof WingPrefs>(key: K, value: WingPrefs[K]) {
    if (key === "students_search_limit") {
      const num = Number(value);
      state.students_search_limit = isFinite(num) && num > 0 ? Math.min(Math.max(50, num), 2000) : 300;
    } else {
      // @ts-ignore
      state[key] = value;
    }
    saveNow();
  }

  function reset() {
    const d = defaults();
    Object.assign(state, d);
    saveNow();
  }

  function exportJson(): string {
    try {
      return JSON.stringify(state, null, 2);
    } catch {
      return "{}";
    }
  }

  function importJson(json: string): boolean {
    try {
      const obj = JSON.parse(json);
      const parsed = safeParse(JSON.stringify(obj));
      Object.assign(state, parsed);
      saveNow();
      return true;
    } catch {
      return false;
    }
  }

  return { ...toRefs(state), set, reset, save: saveNow, exportJson, importJson };
}