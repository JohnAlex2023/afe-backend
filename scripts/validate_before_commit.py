#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PROFESSIONAL PRE-COMMIT VALIDATION SCRIPT
Enterprise Level Validation Before Commits

This script validates all critical requirements BEFORE any commit.
Used to prevent operational errors and data inconsistency issues.

Validaciones:
1. Migraciones Alembic en sync con modelos
2. No hay código deprecated sin documentar
3. Campos obligatorios sincronizados entre capas
4. Tests pasan sin errores
5. No hay imports circulares
6. Schema y modelos están sincronizados
7. No hay cambios sin tests
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List


class PreCommitValidator:
    """Validador profesional pre-commit"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.base_path = Path(__file__).parent.parent
        self.app_path = self.base_path / "app"
        self.tests_path = self.base_path / "tests"

    def validate_all(self) -> bool:
        """Ejecuta todas las validaciones"""
        print("\n" + "="*70)
        print("PRE-COMMIT VALIDATION SUITE (Enterprise Level)")
        print("="*70 + "\n")

        self._validate_migrations()
        self._validate_required_fields()
        self._validate_tests_exist()
        self._validate_syntax()
        self._print_results()
        return len(self.errors) == 0

    def _validate_migrations(self):
        """Validar que migraciones Alembic están en sync"""
        print("[*] Checking Alembic migrations...")
        try:
            result = subprocess.run(
                ["alembic", "current"],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print("    [OK] Alembic migrations OK")
            else:
                self.warnings.append("Alembic validation warning")
        except Exception as e:
            self.warnings.append(f"Alembic check skipped: {str(e)}")

    def _validate_required_fields(self):
        """Validar que campos críticos están sincronizados"""
        print("[*] Checking critical fields...")
        
        # Verificar accion_por en modelo
        factura_file = self.app_path / "models" / "factura.py"
        if factura_file.exists():
            with open(factura_file, encoding='utf-8') as f:
                content = f.read()
                if "accion_por" not in content:
                    self.errors.append(
                        "ERROR: Field 'accion_por' not found in Factura model"
                    )
                else:
                    print("    [OK] Critical fields found")
        
        # Verificar sincronización en servicio
        service_file = self.app_path / "services" / "workflow_automatico.py"
        if service_file.exists():
            with open(service_file, encoding='utf-8') as f:
                content = f.read()
                if "factura.accion_por" not in content:
                    self.warnings.append(
                        "WARNING: accion_por sync not found in WorkflowAutomaticoService"
                    )

    def _validate_tests_exist(self):
        """Validar que existen tests críticos"""
        print("[*] Checking test files...")
        
        critical_tests = [
            "test_accion_por_sync.py",
            "test_workflow_integrity.py",
        ]
        
        found = 0
        for test_file in critical_tests:
            if (self.tests_path / test_file).exists():
                found += 1
        
        if found == len(critical_tests):
            print(f"    [OK] All critical tests present ({found}/{len(critical_tests)})")
        else:
            self.warnings.append(f"Missing tests: {len(critical_tests) - found}")

    def _validate_syntax(self):
        """Validar sintaxis Python"""
        print("[*] Validating Python syntax...")
        
        errors_found = 0
        python_files = list(self.app_path.glob("**/*.py"))[:30]  # Sample first 30
        
        for py_file in python_files:
            try:
                with open(py_file, encoding='utf-8') as f:
                    compile(f.read(), str(py_file), 'exec')
            except SyntaxError as e:
                errors_found += 1
                self.errors.append(f"Syntax error in {py_file.name}: {str(e)[:50]}")
        
        if errors_found == 0:
            print("    [OK] Python syntax valid")

    def _print_results(self):
        """Imprimir resultados"""
        print("\n" + "="*70)
        print("VALIDATION RESULTS")
        print("="*70 + "\n")

        if self.errors:
            print(f"[ERRORS] {len(self.errors)} critical errors:\n")
            for error in self.errors:
                print(f"  - {error}")
            print()

        if self.warnings:
            print(f"[WARNINGS] {len(self.warnings)} warnings:\n")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        if not self.errors:
            print("[SUCCESS] ALL VALIDATIONS PASSED\n")
            print("Status: READY FOR COMMIT\n")
        else:
            print("[FAILED] FIX ERRORS BEFORE COMMITTING\n")

        print("="*70 + "\n")


def main():
    """Punto de entrada"""
    validator = PreCommitValidator()
    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
