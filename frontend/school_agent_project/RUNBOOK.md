Runbook - Quick Commands

1. Build and start services (dev):
   docker-compose up --build
2. Run migrations:
   docker-compose exec web python manage.py migrate
3. Create superuser:
   docker-compose exec web python manage.py createsuperuser
4. Import reply templates:
   docker-compose exec web python manage.py shell -c "from whatsapp_agent.models import ReplyTemplate; import csv, json; ..."
5. Start Celery worker:
   docker-compose up worker
6. Tail logs:
   docker-compose logs -f web
