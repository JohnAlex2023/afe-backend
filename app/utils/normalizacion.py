"""
Utilidades de normalización de datos - Nivel Enterprise.

Este módulo proporciona funciones para normalizar datos críticos,
asegurando consistencia en toda la aplicación.

NOTA: Las funciones de normalización de NIT han sido movidas a:
      app.utils.nit_validator.NitValidator

      NitValidator proporciona el algoritmo CORRECTO de la DIAN (Modulo 11 con
      multipliers [41, 37, 29, 23, 19, 17, 13, 7, 3]) y MANTIENE el DV en todos
      los NITs (formato "XXXXXXXXX-D").

Funciones activas en este módulo:
- normalizar_email() - Normaliza emails a lowercase
- normalizar_razon_social() - Normaliza razón social (espacios, capitalización)
"""

from typing import Optional


def normalizar_email(email: Optional[str]) -> Optional[str]:
    """
    Normaliza un email a formato estándar (lowercase, sin espacios).

    Args:
        email: Email en cualquier formato

    Returns:
        Email normalizado o None si es inválido

    Examples:
        >>> normalizar_email("  Juan@EXAMPLE.com  ")
        "juan@example.com"
    """
    if not email:
        return None

    email = email.strip().lower()

    # Validación básica de formato email
    if '@' not in email or '.' not in email.split('@')[1]:
        return None

    return email


def normalizar_razon_social(razon_social: Optional[str]) -> Optional[str]:
    """
    Normaliza razón social (elimina espacios extras, capitaliza).

    Args:
        razon_social: Razón social en cualquier formato

    Returns:
        Razón social normalizada o None si es vacía

    Examples:
        >>> normalizar_razon_social("  EMPRESA   S.A.S  ")
        "EMPRESA S.A.S"
    """
    if not razon_social:
        return None

    # Eliminar espacios múltiples y trimear
    razon_social = ' '.join(razon_social.split())

    if not razon_social or razon_social == "":
        return None

    return razon_social.upper()
