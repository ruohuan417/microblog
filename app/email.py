import logging
from threading import Thread

from flask import current_app
from flask_mail import Message

from app import mail

logger = logging.getLogger(__name__)


def _send(app, subject, sender, recipients, text_body, html_body):
    with app.app_context():
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = text_body
        msg.html = html_body
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    app = current_app._get_current_object()
    queue = app.task_queue
    if queue is not None:
        try:
            queue.enqueue('app.email._task_send_email', subject, sender,
                          recipients, text_body, html_body)
            return None
        except Exception:
            app.logger.warning('Redis unavailable, '
                               'falling back to thread email delivery')
    thr = Thread(target=_send, args=(app, subject, sender, recipients,
                                     text_body, html_body))
    thr.start()
    return thr


def _task_send_email(subject, sender, recipients, text_body, html_body):
    from app import create_app
    app = create_app()
    _send(app, subject, sender, recipients, text_body, html_body)
