from celery import shared_task
from .models import MessageLog
from .services import detect_intent, select_template


@shared_task(bind=True, max_retries=3)
def process_incoming_message(self, message_id):
    try:
        msg = MessageLog.objects.get(id=message_id)
        intent, conf = detect_intent(msg.content)
        template = select_template(intent)
        reply_text = (
            template.text_template.format(name=msg.person.name if msg.person else "")
            if template
            else "نعتذر، لم أفهم طلبك."
        )
        MessageLog.objects.create(
            person=msg.person, phone=msg.phone, direction="outgoing", content=reply_text, intent=intent, confidence=conf
        )
    except Exception as e:
        raise self.retry(exc=e, countdown=5)
