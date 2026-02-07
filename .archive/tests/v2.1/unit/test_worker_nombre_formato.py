"""
Tests unitarios para validar el formato de nombre_completo en Worker.

Prueba el nuevo formato v2.1: "INICIALES(ID)"
- Primera letra del primer nombre + Primera letra del primer apellido
- Siempre en MAYÚSCULAS
- Sin espacios
- ID entre paréntesis

Coverage objetivo: 100% del computed_field nombre_completo
"""
import pytest
from backend.models.worker import Worker
from backend.models.role import RolTrabajador


class TestNombreCompletoFormato:
    """Tests para validar el formato INICIALES(ID) del nombre_completo."""

    def test_nombres_simples(self):
        """Nombres simples de una palabra: 'Mauricio Rodriguez' → 'MR(93)'."""
        worker = Worker(
            id=93,
            nombre="Mauricio",
            apellido="Rodriguez",
            rol=RolTrabajador.ARMADOR,
            activo=True
        )
        assert worker.nombre_completo == "MR(93)"

    def test_nombres_compuestos_toma_solo_primeras_palabras(self):
        """Nombres compuestos: solo primera palabra de cada campo."""
        # "Juan Carlos Pérez López" → "JP(94)"
        worker = Worker(
            id=94,
            nombre="Juan Carlos",
            apellido="Pérez López",
            rol=RolTrabajador.SOLDADOR,
            activo=True
        )
        assert worker.nombre_completo == "JP(94)"

    def test_nombres_con_acentos(self):
        """Nombres con acentos: 'María José García' → 'MG(95)'."""
        worker = Worker(
            id=95,
            nombre="María José",
            apellido="García",
            rol=RolTrabajador.METROLOGIA,
            activo=True
        )
        assert worker.nombre_completo == "MG(95)"

    def test_nombres_con_espacios_extras(self):
        """Nombres con espacios extras son trimmed correctamente."""
        worker = Worker(
            id=96,
            nombre="  Juan   Carlos  ",
            apellido="  Pérez  ",
            rol=RolTrabajador.ARMADOR,
            activo=True
        )
        # Espacios eliminados, solo toma primera palabra: "JP(96)"
        assert worker.nombre_completo == "JP(96)"

    def test_formato_siempre_mayusculas(self):
        """Iniciales siempre en MAYÚSCULAS sin importar entrada."""
        worker = Worker(
            id=97,
            nombre="juan",  # minúsculas
            apellido="pérez",  # minúsculas
            rol=RolTrabajador.SOLDADOR,
            activo=True
        )
        assert worker.nombre_completo == "JP(97)"

    def test_sin_espacios_en_formato(self):
        """El formato no contiene espacios: 'MR(93)', no 'MR (93)'."""
        worker = Worker(
            id=98,
            nombre="Maria",
            apellido="Rodriguez",
            rol=RolTrabajador.AYUDANTE,
            activo=True
        )
        resultado = worker.nombre_completo
        # Verificar que no haya espacios en el formato
        assert " " not in resultado
        assert resultado == "MR(98)"

    def test_diferentes_ids(self):
        """IDs diferentes producen formatos diferentes para mismo nombre."""
        worker1 = Worker(id=1, nombre="Juan", apellido="Pérez", rol=RolTrabajador.ARMADOR, activo=True)
        worker2 = Worker(id=999, nombre="Juan", apellido="Pérez", rol=RolTrabajador.ARMADOR, activo=True)

        assert worker1.nombre_completo == "JP(1)"
        assert worker2.nombre_completo == "JP(999)"
        assert worker1.nombre_completo != worker2.nombre_completo

    def test_nombres_con_enie(self):
        """Nombres con ñ se manejan correctamente."""
        worker = Worker(
            id=100,
            nombre="Niño",
            apellido="Núñez",
            rol=RolTrabajador.PINTURA,
            activo=True
        )
        assert worker.nombre_completo == "NN(100)"

    def test_nombres_con_dieresis(self):
        """Nombres con ü/ï se manejan correctamente."""
        worker = Worker(
            id=101,
            nombre="Raúl",
            apellido="Güell",
            rol=RolTrabajador.DESPACHO,
            activo=True
        )
        assert worker.nombre_completo == "RG(101)"

    def test_iniciales_extraidas_correctamente(self):
        """Verificar que solo se toma la primera letra de cada palabra."""
        worker = Worker(
            id=102,
            nombre="Carlos Alberto",
            apellido="Rodríguez García",
            rol=RolTrabajador.REVESTIMIENTO,
            activo=True
        )
        # Solo "C" de Carlos y "R" de Rodríguez
        assert worker.nombre_completo == "CR(102)"

    def test_parentesis_correctamente_cerrados(self):
        """El formato incluye paréntesis correctamente: (ID)."""
        worker = Worker(
            id=103,
            nombre="Test",
            apellido="Worker",
            rol=RolTrabajador.ARMADOR,
            activo=True
        )
        resultado = worker.nombre_completo
        assert "(" in resultado
        assert ")" in resultado
        assert resultado.endswith(")")
        assert resultado == "TW(103)"

    def test_formato_estructura_general(self):
        """Validar estructura general del formato."""
        worker = Worker(
            id=104,
            nombre="Example",
            apellido="Test",
            rol=RolTrabajador.SOLDADOR,
            activo=True
        )
        resultado = worker.nombre_completo

        # Formato debe ser: 2 letras + "(" + números + ")"
        assert len(resultado) >= 5  # Mínimo "XX(N)"
        assert resultado[2] == "("
        assert resultado[-1] == ")"
        assert resultado[:2].isupper()  # Primeras 2 letras en mayúsculas
        assert resultado[3:-1].isdigit()  # Entre paréntesis solo dígitos
