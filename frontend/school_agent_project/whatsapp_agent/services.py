from .models import Person, ReplyTemplate

INTENT_KEYWORDS = {
    "check_result": ["نتيجة", "درجات", "result", "grade", "mark"],
    "attendance": ["دوام", "حضور", "غياب", "attendance", "absence", "late"],
    "contact_teacher": ["معلم", "تواصل مع", "contact teacher", "teacher"],
    "behavior": ["سلوك", "انضباط", "behavior", "discipline"],
    "request_file": ["جدول", "ملف", "table", "pdf", "file"],
}


def detect_intent(text: str) -> (str, float):
    t = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return intent, 0.9
    return "unknown", 0.0


def select_template(intent: str):
    tpl = ReplyTemplate.objects.filter(intent=intent, is_active=True).order_by("-created_at").first()
    if tpl:
        return tpl
    return ReplyTemplate.objects.filter(intent="unknown", is_active=True).first()


def ensure_person_by_phone(phone: str):
    p = Person.objects.filter(phone=phone).first()
    return p
