#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de concurrencia para detectar problemas con el singleton.

Si hay problemas de threading con el UnifiedEmailService,
este test lo detectará.
"""

import sys
import io
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='[%(threadName)-10s] %(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("TEST: Concurrencia en UnifiedEmailService")
print("=" * 80)

def send_email_test(email_id: int):
    """Simula envío de email desde un thread diferente."""
    try:
        from app.services.unified_email_service import get_unified_email_service

        service = get_unified_email_service()

        result = service.send_email(
            to_email=f'test{email_id}@example.com',
            subject=f'Test {email_id}',
            body_html=f'<h1>Email {email_id}</h1>',
            importance='normal'
        )

        status = "OK" if result.get('success') else "FAIL"
        provider = result.get('provider', 'unknown')
        return {
            'email_id': email_id,
            'status': status,
            'provider': provider,
            'error': result.get('error') if not result.get('success') else None
        }
    except Exception as e:
        return {
            'email_id': email_id,
            'status': 'EXCEPTION',
            'error': str(e)
        }

print("\n[TEST] Enviando 10 emails en paralelo (threads concurrentes)...\n")

results = []
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(send_email_test, i) for i in range(10)]

    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        print(f"Email {result['email_id']}: {result['status']} "
              f"({result.get('provider', 'N/A')}) "
              f"- Error: {result.get('error', 'None')}")

# Analizar resultados
print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)

successful = sum(1 for r in results if r['status'] == 'OK')
failed = sum(1 for r in results if r['status'] == 'FAIL')
exceptions = sum(1 for r in results if r['status'] == 'EXCEPTION')

print(f"Total: {len(results)}")
print(f"Exitosos: {successful}")
print(f"Fallidos: {failed}")
print(f"Excepciones: {exceptions}")

if failed > 0 or exceptions > 0:
    print("\nERRORES DETECTADOS:")
    for r in results:
        if r['status'] != 'OK':
            print(f"  Email {r['email_id']}: {r.get('error', 'Sin error')}")
else:
    print("\nTodo funcionando correctamente bajo concurrencia")

print("=" * 80)
