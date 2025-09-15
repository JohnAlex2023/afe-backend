from app.notifications.email import send_email
from app.notifications.sms import send_sms

# Servicio de notificaciones unificado

def notificar_por_email(to: str, subject: str, body: str):
    send_email(to, subject, body)

def notificar_por_sms(to: str, message: str):
    send_sms(to, message)
