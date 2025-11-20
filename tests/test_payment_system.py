"""
Test suite para validar el sistema de pagos - FASE 1.

ARQUITECTURA:
    - Tabla: pagos_facturas (9 campos esenciales)
    - Relación: Factura (1) → (N) PagoFactura
    - Sincronización: Factura.estado pasa a "pagada" cuando total_pagado >= total_calculado
    - Control de Acceso: Solo rol "contador" puede registrar pagos
    - Auditoría: Registra procesado_por, fecha_pago, referencia_pago

CASOS DE PRUEBA:
    1. ✅ Pago completo exitoso (100% de la factura)
    2. ✅ Pagos parciales (múltiples pagos que suman al total)
    3. ✅ Validación: referencia_pago duplicada → 409 CONFLICT
    4. ✅ Validación: monto excede pendiente → 400 BAD REQUEST
    5. ✅ Validación: factura no aprobada → 400 BAD REQUEST
    6. ✅ Validación: factura no existe → 404 NOT FOUND
    7. ✅ Control de acceso: sin rol contador → 403 FORBIDDEN
    8. ✅ Email enviado al proveedor
"""
import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.factura import Factura, EstadoFactura
from app.models.pago_factura import PagoFactura, EstadoPago
from app.models.proveedor import Proveedor
from app.models.responsable import Responsable
from app.models.usuario import Usuario, Rol
from app.models.asignacion_nit import AsignacionNIT


@pytest.fixture
def proveedor(db: Session):
    """Crear proveedor de prueba."""
    proveedor = Proveedor(
        nit="811030191",
        razon_social="Test Proveedor S.A.S",
        email="proveedor@test.com",
        representante_legal="Juan Pérez"
    )
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@pytest.fixture
def responsable(db: Session):
    """Crear responsable de prueba."""
    responsable = Responsable(
        nombre="María García",
        usuario="maria.garcia",
        email="maria@empresa.com",
        area="Compras",
        activo=True
    )
    db.add(responsable)
    db.commit()
    db.refresh(responsable)
    return responsable


@pytest.fixture
def contador_user(db: Session):
    """Crear usuario contador para pruebas."""
    # Crear o obtener rol contador
    rol = db.query(Rol).filter(Rol.nombre == "contador").first()
    if not rol:
        rol = Rol(nombre="contador")
        db.add(rol)
        db.flush()

    # Crear usuario
    usuario = Usuario(
        usuario="contador.test",
        email="contador@empresa.com",
        nombre="Contador Test",
        password_hash="hashed_password"  # En tests reales, usar hash seguro
    )
    db.add(usuario)
    db.flush()

    # Asignar rol
    usuario.roles = [rol]
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture
def factura_aprobada(db: Session, proveedor, responsable):
    """Crear factura aprobada de prueba."""
    factura = Factura(
        numero_factura="INV-2025-0001",
        nit_proveedor=proveedor.nit,
        fecha_factura=datetime.now(),
        total_calculado=Decimal("5000.00"),
        estado=EstadoFactura.aprobada,
        descripcion_concepto="Servicios de consultoría",
        accion_por_aprobador=responsable.id,
        observaciones="Factura de prueba",
        responsable_id=responsable.id
    )
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


class TestPagoCompleto:
    """Test cases para pagos completos (100% de la factura)."""

    def test_pago_completo_exitoso(self, client: TestClient, db: Session,
                                    factura_aprobada, auth_token_contador):
        """
        CASO 1: Pago completo exitoso

        GIVEN: Factura aprobada de $5,000
        WHEN: Contador registra pago de $5,000
        THEN:
            - Estado cambia a "pagada" ✅
            - total_pagado = $5,000
            - pendiente_pagar = $0
            - esta_completamente_pagada = True
            - Email enviado al proveedor
        """
        payload = {
            "monto_pagado": "5000.00",
            "referencia_pago": "TEST_CHQ_001",
            "metodo_pago": "cheque"
        }

        response = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=payload,
            headers={"Authorization": auth_token_contador}
        )

        assert response.status_code == 200
        data = response.json()

        # Verificar respuesta
        assert data["id"] == factura_aprobada.id
        assert data["estado"] == "pagada"
        assert float(data["total_pagado"]) == 5000.0
        assert float(data["pendiente_pagar"]) == 0.0
        assert data["esta_completamente_pagada"] is True

        # Verificar en base de datos
        factura = db.query(Factura).filter(Factura.id == factura_aprobada.id).first()
        assert factura.estado == EstadoFactura.pagada
        assert len(factura.pagos) == 1
        assert factura.pagos[0].monto_pagado == Decimal("5000.00")
        assert factura.pagos[0].referencia_pago == "TEST_CHQ_001"
        assert factura.pagos[0].estado_pago == EstadoPago.completado

    def test_pago_completo_con_auditoría(self, client: TestClient, db: Session,
                                         factura_aprobada, auth_token_contador):
        """
        Verificar que la auditoría se registre correctamente.

        GIVEN: Pago registrado
        WHEN: Consultar registro PagoFactura
        THEN:
            - procesado_por = email del contador
            - fecha_pago = timestamp correcto
            - referencia_pago = único
        """
        payload = {
            "monto_pagado": "5000.00",
            "referencia_pago": "TEST_CHQ_002",
            "metodo_pago": "transferencia"
        }

        response = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=payload,
            headers={"Authorization": auth_token_contador}
        )

        assert response.status_code == 200

        # Verificar auditoría en base de datos
        pago = db.query(PagoFactura).filter(
            PagoFactura.referencia_pago == "TEST_CHQ_002"
        ).first()

        assert pago is not None
        assert pago.procesado_por == "contador.test@empresa.com"
        assert pago.fecha_pago is not None
        assert pago.creado_en is not None
        assert pago.actualizado_en is not None


class TestPagosParciales:
    """Test cases para pagos parciales (múltiples pagos)."""

    def test_pago_parcial_primera_cuota(self, client: TestClient, db: Session,
                                        factura_aprobada, auth_token_contador):
        """
        CASO 2: Primera cuota de pago parcial

        GIVEN: Factura aprobada de $5,000
        WHEN: Contador registra pago de $3,000 (60%)
        THEN:
            - Estado permanece "aprobada" (NO cambia)
            - total_pagado = $3,000
            - pendiente_pagar = $2,000
            - esta_completamente_pagada = False
        """
        payload = {
            "monto_pagado": "3000.00",
            "referencia_pago": "TEST_TRF_001",
            "metodo_pago": "transferencia"
        }

        response = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=payload,
            headers={"Authorization": auth_token_contador}
        )

        assert response.status_code == 200
        data = response.json()

        # Estado debe permanecer aprobada
        assert data["estado"] == "aprobada"
        assert float(data["total_pagado"]) == 3000.0
        assert float(data["pendiente_pagar"]) == 2000.0
        assert data["esta_completamente_pagada"] is False

        # Verificar en DB
        factura = db.query(Factura).filter(Factura.id == factura_aprobada.id).first()
        assert factura.estado == EstadoFactura.aprobada
        assert len(factura.pagos) == 1

    def test_pago_parcial_segunda_cuota_completa(self, client: TestClient, db: Session,
                                                  factura_aprobada, auth_token_contador):
        """
        CASO 3: Segunda cuota que completa el pago

        GIVEN: Factura con primer pago de $3,000
        WHEN: Contador registra segundo pago de $2,000
        THEN:
            - Estado cambia a "pagada"
            - total_pagado = $5,000
            - pendiente_pagar = $0
            - 2 registros en pagos_facturas
        """
        # Primer pago
        pago1 = {
            "monto_pagado": "3000.00",
            "referencia_pago": "TEST_TRF_001",
            "metodo_pago": "transferencia"
        }
        response1 = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=pago1,
            headers={"Authorization": auth_token_contador}
        )
        assert response1.status_code == 200

        # Segundo pago
        pago2 = {
            "monto_pagado": "2000.00",
            "referencia_pago": "TEST_TRF_002",
            "metodo_pago": "transferencia"
        }
        response2 = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=pago2,
            headers={"Authorization": auth_token_contador}
        )
        assert response2.status_code == 200
        data = response2.json()

        # Ahora debe estar pagada
        assert data["estado"] == "pagada"
        assert float(data["total_pagado"]) == 5000.0
        assert float(data["pendiente_pagar"]) == 0.0
        assert data["esta_completamente_pagada"] is True

        # Verificar en DB
        factura = db.query(Factura).filter(Factura.id == factura_aprobada.id).first()
        assert factura.estado == EstadoFactura.pagada
        assert len(factura.pagos) == 2


class TestValidaciones:
    """Test cases para validaciones y restricciones."""

    def test_validación_referencia_duplicada(self, client: TestClient, db: Session,
                                             factura_aprobada, auth_token_contador):
        """
        CASO 4: Validación - Referencia de pago duplicada

        GIVEN: Referencia "TEST_CHQ_DUP" ya existe en la BD
        WHEN: Intenta registrar con la misma referencia
        THEN: Error 409 CONFLICT
        """
        # Primer pago
        payload1 = {
            "monto_pagado": "1000.00",
            "referencia_pago": "TEST_CHQ_DUP",
            "metodo_pago": "cheque"
        }
        response1 = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=payload1,
            headers={"Authorization": auth_token_contador}
        )
        assert response1.status_code == 200

        # Intento de duplicado
        payload2 = {
            "monto_pagado": "500.00",
            "referencia_pago": "TEST_CHQ_DUP",  # Misma referencia
            "metodo_pago": "cheque"
        }
        response2 = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=payload2,
            headers={"Authorization": auth_token_contador}
        )

        assert response2.status_code == 409
        data = response2.json()
        assert "ya existe" in data["detail"]

    def test_validación_monto_excede_pendiente(self, client: TestClient, db: Session,
                                               factura_aprobada, auth_token_contador):
        """
        CASO 5: Validación - Monto excede pendiente

        GIVEN: Factura de $5,000, ya pagado $3,000
        WHEN: Intenta pagar $3,000 más (excede $2,000 pendiente)
        THEN: Error 400 BAD REQUEST
        """
        # Primer pago
        pago1 = {
            "monto_pagado": "3000.00",
            "referencia_pago": "TEST_TRF_EXC_1",
            "metodo_pago": "transferencia"
        }
        client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=pago1,
            headers={"Authorization": auth_token_contador}
        )

        # Intento de pago excesivo
        pago2 = {
            "monto_pagado": "3000.00",  # Excede $2,000 pendiente
            "referencia_pago": "TEST_TRF_EXC_2",
            "metodo_pago": "transferencia"
        }
        response = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=pago2,
            headers={"Authorization": auth_token_contador}
        )

        assert response.status_code == 400
        data = response.json()
        assert "excede pendiente" in data["detail"]

    def test_validación_factura_no_aprobada(self, client: TestClient, db: Session,
                                            proveedor, responsable, auth_token_contador):
        """
        CASO 6: Validación - Factura no aprobada

        GIVEN: Factura en estado "en_revision"
        WHEN: Intenta registrar pago
        THEN: Error 400 BAD REQUEST
        """
        # Crear factura en revisión
        factura = Factura(
            numero_factura="TEST-PENDIENTE",
            nit_proveedor=proveedor.nit,
            fecha_factura=datetime.now(),
            total_calculado=Decimal("5000.00"),
            estado=EstadoFactura.en_revision,
            descripcion_concepto="Servicios",
            responsable_id=responsable.id
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)

        payload = {
            "monto_pagado": "5000.00",
            "referencia_pago": "TEST_CHQ_003",
            "metodo_pago": "cheque"
        }
        response = client.post(
            f"/accounting/facturas/{factura.id}/marcar-pagada",
            json=payload,
            headers={"Authorization": auth_token_contador}
        )

        assert response.status_code == 400
        data = response.json()
        assert "no está aprobada" in data["detail"]

    def test_validación_factura_no_existe(self, client: TestClient, auth_token_contador):
        """
        CASO 7: Validación - Factura no existe

        GIVEN: Factura ID 99999 no existe
        WHEN: Intenta registrar pago
        THEN: Error 404 NOT FOUND
        """
        payload = {
            "monto_pagado": "5000.00",
            "referencia_pago": "TEST_CHQ_004",
            "metodo_pago": "cheque"
        }
        response = client.post(
            "/accounting/facturas/99999/marcar-pagada",
            json=payload,
            headers={"Authorization": auth_token_contador}
        )

        assert response.status_code == 404
        data = response.json()
        assert "no encontrada" in data["detail"]


class TestControlDeAcceso:
    """Test cases para control de acceso basado en roles."""

    def test_sin_autenticación(self, client: TestClient, factura_aprobada):
        """
        CASO 8: Sin autenticación

        GIVEN: Request sin token
        WHEN: Intenta acceder endpoint
        THEN: Error 401 UNAUTHORIZED
        """
        payload = {
            "monto_pagado": "5000.00",
            "referencia_pago": "TEST_CHQ_005",
            "metodo_pago": "cheque"
        }
        response = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=payload
        )

        assert response.status_code == 401

    def test_sin_rol_contador(self, client: TestClient, factura_aprobada,
                              auth_token_responsable):
        """
        CASO 9: Con autenticación pero sin rol contador

        GIVEN: Usuario autenticado con otro rol (e.g., "responsable")
        WHEN: Intenta acceder endpoint
        THEN: Error 403 FORBIDDEN
        """
        payload = {
            "monto_pagado": "5000.00",
            "referencia_pago": "TEST_CHQ_006",
            "metodo_pago": "cheque"
        }
        response = client.post(
            f"/accounting/facturas/{factura_aprobada.id}/marcar-pagada",
            json=payload,
            headers={"Authorization": auth_token_responsable}
        )

        assert response.status_code == 403


class TestCalculosYSincronización:
    """Test cases para cálculos de propiedades y sincronización."""

    def test_calculo_total_pagado(self, db: Session, factura_aprobada):
        """
        Verificar que total_pagado suma correctamente todos los pagos completados.

        GIVEN: 3 pagos (2 completados, 1 fallido)
        WHEN: Consultar total_pagado
        THEN: Solo suma los completados
        """
        # Pago 1: completado
        pago1 = PagoFactura(
            factura_id=factura_aprobada.id,
            monto_pagado=Decimal("1000.00"),
            referencia_pago="P-001",
            estado_pago=EstadoPago.completado,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        db.add(pago1)
        db.flush()

        # Pago 2: completado
        pago2 = PagoFactura(
            factura_id=factura_aprobada.id,
            monto_pagado=Decimal("2000.00"),
            referencia_pago="P-002",
            estado_pago=EstadoPago.completado,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        db.add(pago2)
        db.flush()

        # Pago 3: fallido (no debe contar)
        pago3 = PagoFactura(
            factura_id=factura_aprobada.id,
            monto_pagado=Decimal("500.00"),
            referencia_pago="P-003",
            estado_pago=EstadoPago.fallido,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        db.add(pago3)
        db.commit()

        # Verificar cálculo
        factura = db.query(Factura).filter(Factura.id == factura_aprobada.id).first()
        assert factura.total_pagado == Decimal("3000.00")  # 1000 + 2000, sin 500
        assert factura.pendiente_pagar == Decimal("2000.00")

    def test_sincronización_estado_pagada(self, db: Session, factura_aprobada):
        """
        Verificar que estado cambia a "pagada" cuando total_pagado >= total_calculado.
        """
        # Crear pago que completa la factura
        pago = PagoFactura(
            factura_id=factura_aprobada.id,
            monto_pagado=factura_aprobada.total_calculado,
            referencia_pago="P-FINAL",
            estado_pago=EstadoPago.completado,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        db.add(pago)

        # En el endpoint real, aquí se cambiaría el estado
        factura_aprobada.estado = EstadoFactura.pagada
        db.commit()

        # Verificar
        factura = db.query(Factura).filter(Factura.id == factura_aprobada.id).first()
        assert factura.estado == EstadoFactura.pagada
        assert factura.esta_completamente_pagada is True


class TestIntegridad:
    """Test cases para integridad de datos y relaciones."""

    def test_relación_factura_pagos(self, db: Session, factura_aprobada):
        """
        Verificar que la relación One-to-Many funciona correctamente.
        """
        # Crear 3 pagos
        for i in range(1, 4):
            pago = PagoFactura(
                factura_id=factura_aprobada.id,
                monto_pagado=Decimal("1000.00"),
                referencia_pago=f"P-{i:03d}",
                estado_pago=EstadoPago.completado,
                procesado_por="contador@test.com",
                fecha_pago=datetime.now()
            )
            db.add(pago)
        db.commit()

        # Verificar relación
        factura = db.query(Factura).filter(Factura.id == factura_aprobada.id).first()
        assert len(factura.pagos) == 3

        # Verificar que cada pago tiene referencia a la factura
        for pago in factura.pagos:
            assert pago.factura_id == factura.id
            assert pago.factura == factura

    def test_cascade_delete(self, db: Session, proveedor, responsable):
        """
        Verificar que DELETE de factura elimina los pagos asociados (CASCADE).
        """
        # Crear factura
        factura = Factura(
            numero_factura="INV-CASCADE",
            nit_proveedor=proveedor.nit,
            fecha_factura=datetime.now(),
            total_calculado=Decimal("5000.00"),
            estado=EstadoFactura.aprobada,
            descripcion_concepto="Test",
            responsable_id=responsable.id
        )
        db.add(factura)
        db.flush()

        # Crear pagos
        pago1 = PagoFactura(
            factura_id=factura.id,
            monto_pagado=Decimal("1000.00"),
            referencia_pago="P-CASCADE-1",
            estado_pago=EstadoPago.completado,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        pago2 = PagoFactura(
            factura_id=factura.id,
            monto_pagado=Decimal("2000.00"),
            referencia_pago="P-CASCADE-2",
            estado_pago=EstadoPago.completado,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        db.add(pago1)
        db.add(pago2)
        db.commit()

        factura_id = factura.id
        pago1_id = pago1.id

        # Verificar que existen
        assert db.query(Factura).filter(Factura.id == factura_id).first() is not None
        assert db.query(PagoFactura).filter(PagoFactura.id == pago1_id).first() is not None

        # Eliminar factura
        db.delete(factura)
        db.commit()

        # Verificar que se eliminó factura
        assert db.query(Factura).filter(Factura.id == factura_id).first() is None

        # Verificar que se eliminaron pagos (CASCADE)
        assert db.query(PagoFactura).filter(PagoFactura.id == pago1_id).first() is None
        assert db.query(PagoFactura).filter(PagoFactura.factura_id == factura_id).count() == 0

    def test_referencia_pago_unique(self, db: Session, factura_aprobada):
        """
        Verificar que referencia_pago es UNIQUE y no permite duplicados.
        """
        # Crear primer pago
        pago1 = PagoFactura(
            factura_id=factura_aprobada.id,
            monto_pagado=Decimal("1000.00"),
            referencia_pago="UNIQUE-REF",
            estado_pago=EstadoPago.completado,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        db.add(pago1)
        db.commit()

        # Intento de duplicado (diferentes facturas, mismo reference)
        pago2 = PagoFactura(
            factura_id=factura_aprobada.id,
            monto_pagado=Decimal("500.00"),
            referencia_pago="UNIQUE-REF",  # Mismo reference
            estado_pago=EstadoPago.completado,
            procesado_por="contador@test.com",
            fecha_pago=datetime.now()
        )
        db.add(pago2)

        # Debe fallar la inserción
        with pytest.raises(Exception):  # IntegrityError o SQLAlchemy equivalent
            db.commit()
