"""Verifica que cada modulo funcional exponga su dominio."""

import unittest

from prestamos_academicos import (
    auditoria, compartido, configuracion_servicio, identidad, inventario,
    prestamos, reservas, sanciones,
)


class ImportacionesDelDominioTest(unittest.TestCase):
    def test_contextos_exponen_sus_clases(self):
        self.assertIsNotNone(auditoria.HistorialMovimiento)
        self.assertIsNotNone(configuracion_servicio.PoliticaSancion)
        self.assertIsNotNone(identidad.Usuario)
        self.assertIsNotNone(inventario.Item)
        self.assertIsNotNone(prestamos.Prestamo)
        self.assertIsNotNone(reservas.Reserva)
        self.assertIsNotNone(sanciones.Sancion)
        self.assertIsNotNone(compartido.UsuarioId)


if __name__ == "__main__":
    unittest.main()
