"""
Utilidades de normalización de datos - Nivel Enterprise.

Este módulo proporciona funciones para normalizar datos críticos como NITs,
asegurando consistencia en toda la aplicación.
"""

import re
from typing import Optional


def normalizar_nit(nit: Optional[str]) -> Optional[str]:
    """
    Normaliza un NIT colombiano eliminando el dígito de verificación (DV).

    REGLA ENTERPRISE: El DV está DESPUÉS del guión. Solo eliminamos el guión y lo que sigue.
    TODOS los NITs en la BD se almacenan SIN DV.

    Casos manejados:
    - "830122566-1" -> "830122566" (elimina -1 solamente)
    - "811030191-9" -> "811030191" (elimina -9 solamente)
    - "890.903.938-4" -> "890903938" (elimina puntos y -4)
    - "890903938" -> "890903938" (sin cambios, ya está sin DV)

    Args:
        nit: NIT en cualquier formato

    Returns:
        NIT normalizado (solo dígitos, SIN DV) o None si inválido

    Examples:
        >>> normalizar_nit("830122566-1")
        "830122566"

        >>> normalizar_nit("811030191-9")
        "811030191"

        >>> normalizar_nit("890.903.938-4")
        "890903938"
    """
    if not nit:
        return None

    # Limpiar espacios
    nit = nit.strip()

    # Validar que no sea "0" (sin NIT)
    if nit == "0":
        return None

    # PASO 1: Si tiene guión, tomar solo ANTES del guión
    # El DV está DESPUÉS del guión, así que al hacer split, lo eliminamos
    if '-' in nit:
        nit = nit.split('-')[0]

    # PASO 2: Remover puntos y espacios (formato: "830.122.566" -> "830122566")
    nit_limpio = re.sub(r'[.\s]', '', nit)

    # Validar solo dígitos
    if not nit_limpio.isdigit():
        return None

    # Validar longitud (NITs colombianos: 6-10 dígitos)
    if len(nit_limpio) < 6 or len(nit_limpio) > 10:
        return None

    return nit_limpio


def calcular_digito_verificacion(nit: str) -> str:
    """
    Calcula el dígito de verificación de un NIT colombiano.

    Algoritmo estándar de la DIAN para cálculo de DV.

    Args:
        nit: NIT sin DV (solo dígitos)

    Returns:
        Dígito de verificación (0-9)

    Examples:
        >>> calcular_digito_verificacion("830122566")
        "1"

        >>> calcular_digito_verificacion("811030191")
        "9"
    """
    if not nit or not nit.isdigit():
        return "0"

    # Secuencia de factores para el cálculo
    factores = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]

    # Tomar los últimos 15 dígitos del NIT (rellenando con ceros a la izquierda si es necesario)
    nit_padded = nit.zfill(15)

    # Calcular suma ponderada
    suma = 0
    for i, digito in enumerate(nit_padded):
        suma += int(digito) * factores[i]

    # Calcular residuo
    residuo = suma % 11

    # Calcular DV
    if residuo == 0:
        dv = 0
    elif residuo == 1:
        dv = 1
    else:
        dv = 11 - residuo

    return str(dv)


def formatear_nit_con_dv(nit: str) -> str:
    """
    Formatea un NIT para presentación visual con puntos y DV.

    Args:
        nit: NIT sin DV (solo dígitos)

    Returns:
        NIT formateado (ej: "830.122.566-1")

    Examples:
        >>> formatear_nit_con_dv("830122566")
        "830.122.566-1"

        >>> formatear_nit_con_dv("811030191")
        "811.030.191-9"
    """
    if not nit or not nit.isdigit():
        return nit

    # Calcular DV
    dv = calcular_digito_verificacion(nit)

    # Agregar puntos cada 3 dígitos (desde la derecha)
    nit_reverso = nit[::-1]
    nit_con_puntos = '.'.join([nit_reverso[i:i+3] for i in range(0, len(nit_reverso), 3)])
    nit_formateado = nit_con_puntos[::-1]

    # Agregar DV
    return f"{nit_formateado}-{dv}"


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


def son_nits_equivalentes(nit1: Optional[str], nit2: Optional[str]) -> bool:
    """
    Verifica si dos NITs son equivalentes (mismo NIT, diferente formato).

    Args:
        nit1: Primer NIT
        nit2: Segundo NIT

    Returns:
        True si son equivalentes, False en caso contrario

    Examples:
        >>> son_nits_equivalentes("890903938", "890.903.938-4")
        True

        >>> son_nits_equivalentes("890903938", "890903939")
        False
    """
    nit1_norm = normalizar_nit(nit1)
    nit2_norm = normalizar_nit(nit2)

    if not nit1_norm or not nit2_norm:
        return False

    return nit1_norm == nit2_norm
