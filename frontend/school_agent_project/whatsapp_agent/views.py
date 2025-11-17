from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import MessageLog
from .services import detect_intent, select_template, ensure_person_by_phone


@csrf_exempt
def whatsapp_webhook(request):
    incoming = request.POST.get("Body") or ""
    from_num = request.POST.get("From", "")
    phone = from_num.replace("whatsapp:", "") if from_num else request.POST.get("From")
    person = ensure_person_by_phone(phone)
    msg = MessageLog.objects.create(person=person, phone=phone, direction="incoming", content=incoming)

    intent, conf = detect_intent(incoming)
    template = select_template(intent)
    reply_text = (
        template.text_template.format(name=person.name if person else "أهلًا") if template else "نعتذر لم أفهم طلبك."
    )

    MessageLog.objects.create(
        person=person, phone=phone, direction="outgoing", content=reply_text, intent=intent, confidence=conf
    )

    twiml = f"<Response><Message>{reply_text}</Message></Response>"
    return HttpResponse(twiml, content_type="application/xml")
