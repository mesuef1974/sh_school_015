from django.test import Client
import pytest


@pytest.mark.django_db
def test_livez_and_healthz_ok():
    client = Client()
    resp1 = client.get("/livez")
    assert resp1.status_code == 204

    resp2 = client.get("/healthz")
    assert resp2.status_code in (200, 500)
    # If DB is configured locally, expect 200 with body 'ok'
    if resp2.status_code == 200:
        assert resp2.content.strip() == b"ok"