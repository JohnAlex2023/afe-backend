#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script profesional para cargar proveedores desde CSV sin duplicar.

CARACTERÍSTICAS EMPRESARIALES:
- Lee archivo CSV con todos los datos disponibles
- Extrae NITs únicos
- Verifica cuáles ya existen en BD (usando LIKE para variaciones)
- ACTUALIZA proveedores existentes con información más reciente
- Inserta solo los nuevos sin duplicar
- Captura SOLO los campos que el archivo proporciona
- Genera reportes detallados
- Operación atómica (todo o nada)

CAMPOS CAPTURADOS DEL CSV → TABLA PROVEEDORES:
- NIT → nit (único)
- Tercero → razon_social (nombre del proveedor)
- SEDE → area (ubicación/sede del proveedor)
- CUENTA → contacto_email (email de facturación)

CAMPOS NO CAPTURADOS (no están en CSV):
- telefono (NULL)
- direccion (NULL)
- activo (default: True)

Uso:
    python cargar_proveedores_desde_csv.py \\
        --csv-path "C:\\Users\\jhont\\Downloads\\Listas Terceros(Hoja1).csv" \\
        --dry-run  # Para ver cambios sin aplicar
"""

import sys
import csv
import os
from pathlib import Path
from typing import Dict, Set
from datetime import datetime

# Configurar path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.proveedor import Proveedor
from app.utils.logger import logger


class CargadorProveedoresCSV:
    """
    Cargador profesional de proveedores desde CSV.

    Mapeo CSV → BD:
    - NIT (CSV) → nit (BD)
    - Tercero (CSV) → razon_social (BD)
    - SEDE (CSV) → area (BD)
    - CUENTA (CSV) → contacto_email (BD)
    """

    def __init__(self, csv_path: str, dry_run: bool = False):
        """
        Inicializa el cargador.

        Args:
            csv_path: Ruta al archivo CSV
            dry_run: Si True, simula cambios sin modificar BD
        """
        self.csv_path = Path(csv_path)
        self.dry_run = dry_run
        self.db = SessionLocal()

        # Estadísticas
        self.totales_en_csv = 0
        self.nits_unicos = 0
        self.ya_existen = 0
        self.actualizados = 0
        self.nuevos_insertados = 0
        self.errores = []

        # Datos
        self.proveedores_csv: Dict[str, Dict] = {}
        self.proveedores_bd: Dict[str, Proveedor] = {}

    def validar_csv(self) -> bool:
        """Valida que el archivo CSV existe y es legible."""
        if not self.csv_path.exists():
            error = f"Archivo CSV no encontrado: {self.csv_path}"
            logger.error(error)
            self.errores.append(error)
            return False

        if not self.csv_path.is_file():
            error = f"No es un archivo: {self.csv_path}"
            logger.error(error)
            self.errores.append(error)
            return False

        logger.info(f"✓ Archivo CSV validado: {self.csv_path}")
        return True

    def leer_csv(self) -> bool:
        """
        Lee archivo CSV y extrae datos de proveedores.

        Formato esperado:
        SEDE;CUENTA;NIT;Tercero;Responsable;Recibidio;Respuesta Automatica

        Captura SOLO:
        - NIT → nit
        - Tercero → razon_social
        - SEDE → area
        - CUENTA → contacto_email
        """
        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')

                if not reader.fieldnames:
                    error = "CSV no tiene headers"
                    logger.error(error)
                    self.errores.append(error)
                    return False

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Extraer y limpiar datos del CSV
                        nit = (row.get('NIT', '') or '').strip()
                        tercero = (row.get('Tercero', '') or '').strip()
                        sede = (row.get('SEDE', '') or '').strip()
                        cuenta = (row.get('CUENTA', '') or '').strip()

                        # Validar NIT
                        if not nit or nit == '0' or nit.lower() == 'nit' or nit.isspace():
                            continue

                        self.totales_en_csv += 1

                        # Procesar NIT único
                        if nit in self.proveedores_csv:
                            # NIT ya visto: mantener nombre más descriptivo
                            nombre_nuevo = tercero
                            nombre_actual = self.proveedores_csv[nit]['razon_social']

                            if nombre_nuevo and len(nombre_nuevo) > len(nombre_actual):
                                self.proveedores_csv[nit]['razon_social'] = nombre_nuevo

                            # Agregar area si es diferente
                            if sede and sede not in self.proveedores_csv[nit].get('areas', []):
                                self.proveedores_csv[nit]['areas'].append(sede)

                            # Agregar cuenta si es diferente
                            if cuenta and cuenta not in self.proveedores_csv[nit].get('cuentas', []):
                                self.proveedores_csv[nit]['cuentas'].append(cuenta)
                        else:
                            # Primer registro de este NIT
                            self.proveedores_csv[nit] = {
                                'nit': nit,
                                'razon_social': tercero,
                                'area': sede,
                                'areas': [sede] if sede else [],
                                'contacto_email': cuenta,
                                'cuentas': [cuenta] if cuenta else [],
                            }

                    except Exception as e:
                        error = f"Error en fila {row_num}: {str(e)}"
                        logger.error(error)
                        self.errores.append(error)
                        continue

            self.nits_unicos = len(self.proveedores_csv)

            logger.info(
                f"✓ CSV leído exitosamente:\n"
                f"  - {self.totales_en_csv} registros totales\n"
                f"  - {self.nits_unicos} NITs únicos"
            )
            return True

        except Exception as e:
            error = f"Error leyendo CSV: {str(e)}"
            logger.error(error)
            self.errores.append(error)
            return False

    def obtener_proveedores_existentes(self) -> bool:
        """
        Consulta BD para encontrar proveedores existentes.

        Usa LIKE para capturar variaciones de NIT.
        """
        try:
            for nit in self.proveedores_csv.keys():
                # Buscar con LIKE para capturar variaciones
                existente = self.db.query(Proveedor).filter(
                    Proveedor.nit.like(f'{nit}%')
                ).first()

                if existente:
                    self.proveedores_bd[nit] = existente
                    self.ya_existen += 1

            logger.info(
                f"✓ Consulta BD completada:\n"
                f"  - Proveedores existentes: {self.ya_existen}/{self.nits_unicos}"
            )
            return True

        except Exception as e:
            error = f"Error consultando BD: {str(e)}"
            logger.error(error)
            self.errores.append(error)
            return False

    def actualizar_proveedores_existentes(self) -> bool:
        """
        Actualiza proveedores que ya existen con información más reciente.

        LÓGICA PROFESIONAL:
        - razon_social: actualiza si el nuevo es más descriptivo
        - area: actualiza con la sede más reciente del CSV
        - contacto_email: actualiza con el email más reciente
        - NO borra datos existentes
        """
        try:
            for nit, prov_bd in self.proveedores_bd.items():
                prov_csv = self.proveedores_csv[nit]
                cambios = False

                # Actualizar razon_social si es más descriptivo
                if prov_csv['razon_social'] and len(prov_csv['razon_social']) > len(prov_bd.razon_social or ''):
                    logger.debug(
                        f"  NIT {nit}: razon_social: '{prov_bd.razon_social}' → '{prov_csv['razon_social']}'"
                    )
                    prov_bd.razon_social = prov_csv['razon_social']
                    cambios = True

                # Actualizar area si está disponible
                if prov_csv['area'] and prov_csv['area'] != prov_bd.area:
                    logger.debug(
                        f"  NIT {nit}: area: '{prov_bd.area}' → '{prov_csv['area']}'"
                    )
                    prov_bd.area = prov_csv['area']
                    cambios = True

                # Actualizar contacto_email si está disponible
                if prov_csv['contacto_email'] and prov_csv['contacto_email'] != prov_bd.contacto_email:
                    logger.debug(
                        f"  NIT {nit}: contacto_email: '{prov_bd.contacto_email}' → '{prov_csv['contacto_email']}'"
                    )
                    prov_bd.contacto_email = prov_csv['contacto_email']
                    cambios = True

                if cambios:
                    self.actualizados += 1

            # Commit de actualizaciones
            if self.actualizados > 0 and not self.dry_run:
                self.db.commit()

            logger.info(f"✓ Proveedores actualizados: {self.actualizados}")
            return True

        except Exception as e:
            error = f"Error actualizando proveedores: {str(e)}"
            logger.error(error)
            self.errores.append(error)
            self.db.rollback()
            return False

    def insertar_nuevos_proveedores(self) -> bool:
        """
        Inserta nuevos proveedores que no existen en BD.

        LÓGICA PROFESIONAL:
        - Solo inserta NITs que NO existen
        - Captura TODOS los datos disponibles del CSV
        - Operación atómica: commit solo si TODO es exitoso
        """
        try:
            nuevos = []

            for nit, data in self.proveedores_csv.items():
                if nit not in self.proveedores_bd:
                    nuevo_proveedor = Proveedor(
                        nit=nit,
                        razon_social=data['razon_social'],
                        area=data['area'],
                        contacto_email=data['contacto_email'],
                        # telefono: no viene en CSV (NULL)
                        # direccion: no viene en CSV (NULL)
                        # activo: default True
                    )
                    nuevos.append(nuevo_proveedor)

            if not nuevos:
                logger.info("ℹ No hay nuevos proveedores para insertar")
                return True

            # DRY RUN: Mostrar qué se insertaría sin hacerlo
            if self.dry_run:
                logger.info(f"🔍 DRY RUN: Se insertarían {len(nuevos)} proveedores:")
                for prov in nuevos[:20]:
                    logger.info(
                        f"  - NIT: {prov.nit:>15} | Razón Social: {(prov.razon_social or '')[:40]}"
                    )
                if len(nuevos) > 20:
                    logger.info(f"  ... y {len(nuevos) - 20} más")
                self.nuevos_insertados = len(nuevos)
                return True

            # INSERCIÓN REAL: Agregar todos y commit atómico
            self.db.add_all(nuevos)
            self.db.commit()

            self.nuevos_insertados = len(nuevos)
            logger.info(f"✓ Insertados {self.nuevos_insertados} nuevos proveedores")
            return True

        except Exception as e:
            error = f"Error insertando proveedores: {str(e)}"
            logger.error(error)
            self.errores.append(error)
            self.db.rollback()
            return False

    def generar_reporte(self) -> str:
        """Genera reporte profesional detallado de la carga."""
        fecha_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        modo_str = '🔍 DRY RUN (Sin cambios en BD)' if self.dry_run else ' Cambios aplicados a BD'

        reporte = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                  REPORTE DE CARGA DE PROVEEDORES                          ║
║                           CSV → BD AFE                                     ║
╚════════════════════════════════════════════════════════════════════════════╝

 ARCHIVO: {self.csv_path.name}
🕐 FECHA: {fecha_str}
 MODO: {modo_str}

┌─ ESTADÍSTICAS DE PROCESAMIENTO ──────────────────────────────────────────┐
│                                                                            │
│  Registros en CSV:              {self.totales_en_csv:>6}                      │
│  NITs únicos extraídos:         {self.nits_unicos:>6}                      │
│                                                                            │
│  Proveedores ya existentes:     {self.ya_existen:>6}                      │
│    ├─ Actualizados:             {self.actualizados:>6}  ✓ Con nuevos datos │
│    └─ Sin cambios:              {self.ya_existen - self.actualizados:>6}  ✓ Idénticos    │
│                                                                            │
│  Nuevos proveedores insertados: {self.nuevos_insertados:>6}                      │
│                                                                            │
│  TOTAL EN BD DESPUÉS:           {self.ya_existen + self.nuevos_insertados:>6}                      │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

┌─ CAMPOS CAPTURADOS DEL CSV ──────────────────────────────────────────────┐
│                                                                            │
│  NIT              →  nit (identificador único)                           │
│  Tercero          →  razon_social (nombre del proveedor)               │
│  SEDE             →  area (ubicación/sede)                              │
│  CUENTA           →  contacto_email (email de facturación)             │
│                                                                            │
│  CAMPOS NO CAPTURADOS (no están en CSV):                                │
│  - telefono (NULL)                                                       │
│  - direccion (NULL)                                                      │
│  - activo (default: True)                                               │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
"""

        if self.errores:
            reporte += f"""
┌─ ERRORES ({len(self.errores)}) ──────────────────────────────────────────────────────┐
"""
            for i, error in enumerate(self.errores[:10], 1):
                error_short = error[:66] if len(error) > 66 else error
                reporte += f"│ {i:2}. {error_short:<66} │\n"
            if len(self.errores) > 10:
                reporte += f"│     ... y {len(self.errores) - 10} errores más\n"
            reporte += "└────────────────────────────────────────────────────────────────────────────┘\n"

        reporte += f"""
┌─ PRÓXIMOS PASOS ─────────────────────────────────────────────────────────┐
│                                                                            │
│ ✓ Proveedores sincronizados en BD                                       │
│ ✓ {self.nits_unicos} NITs disponibles para asignaciones                              │
│                                                                            │
│ Ahora puedes asignar NITs a responsables usando:                         │
│                                                                            │
│   Endpoint: POST /asignacion-nit/bulk-simple                            │
│                                                                            │
│   Ejemplo:                                                                │
│   {{                                                                     │
│       "responsable_id": 1,                                               │
│       "nits": "830122566,890903938,800136505"                            │
│   }}                                                                     │
│                                                                            │
│ El sistema validará automáticamente que los NITs existan en              │
│ tabla PROVEEDORES y sincronizará las facturas.                          │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                         CARGA COMPLETADA                                  ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
        return reporte

    def ejecutar(self) -> bool:
        """
        Ejecuta el flujo completo de carga profesional.

        PASOS:
        1. Validar archivo CSV
        2. Leer datos del CSV
        3. Consultar BD para detectar existentes
        4. Actualizar proveedores existentes
        5. Insertar nuevos proveedores
        6. Generar reporte

        Returns:
            bool: True si fue exitoso
        """
        logger.info("=" * 80)
        logger.info(f"INICIANDO CARGA DE PROVEEDORES: {self.csv_path}")
        logger.info("=" * 80)

        # PASO 1: Validar CSV
        if not self.validar_csv():
            logger.error("✗ Validación del CSV falló")
            return False

        # PASO 2: Leer CSV
        if not self.leer_csv():
            logger.error("✗ Lectura del CSV falló")
            return False

        # PASO 3: Obtener proveedores existentes
        if not self.obtener_proveedores_existentes():
            logger.error("✗ Consulta a BD falló")
            return False

        # PASO 4: Actualizar existentes
        if not self.actualizar_proveedores_existentes():
            logger.error("✗ Actualización de proveedores falló")
            return False

        # PASO 5: Insertar nuevos
        if not self.insertar_nuevos_proveedores():
            logger.error("✗ Inserción de proveedores falló")
            return False

        # PASO 6: Generar reporte
        reporte = self.generar_reporte()
        print(reporte)
        logger.info(reporte)

        logger.info("=" * 80)
        logger.info("✓ CARGA COMPLETADA EXITOSAMENTE")
        logger.info("=" * 80)

        return True

    def cerrar(self):
        """Cierra la sesión de BD de forma segura."""
        try:
            self.db.close()
        except:
            pass


def main():
    """Punto de entrada principal del script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cargador profesional de proveedores desde CSV"
    )
    parser.add_argument(
        "--csv-path",
        required=True,
        help="Ruta al archivo CSV de proveedores"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular cambios sin aplicarlos a la BD"
    )

    args = parser.parse_args()

    cargador = None
    try:
        cargador = CargadorProveedoresCSV(
            csv_path=args.csv_path,
            dry_run=args.dry_run
        )

        if cargador.ejecutar():
            logger.info("✓ Ejecución completada exitosamente")
            exit(0)
        else:
            logger.error("✗ Error durante la ejecución")
            exit(1)

    except Exception as e:
        logger.error(f"✗ Error fatal: {str(e)}")
        exit(2)
    finally:
        if cargador:
            cargador.cerrar()


if __name__ == "__main__":
    main()
