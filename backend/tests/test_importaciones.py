"""Verifica que los contextos se puedan importar como un único paquete."""

import unittest

from prestamos_academicos.dominio import (
    auditoria,
    configuracion,
    identidad,
    inventario,
    prestamos,
    reservas,
    sanciones,
    shared_kernel,
)


class ImportacionesDelDominioTest(unittest.TestCase):
    def test_contextos_exponen_sus_clases(self):
        self.assertIsNotNone(auditoria.HistorialMovimiento)
        self.assertIsNotNone(configuracion.PoliticaSancion)
        self.assertIsNotNone(identidad.Usuario)
        self.assertIsNotNone(inventario.Item)
        self.assertIsNotNone(prestamos.Prestamo)
        self.assertIsNotNone(reservas.Reserva)
        self.assertIsNotNone(sanciones.Sancion)
        self.assertIsNotNone(shared_kernel.UsuarioId)


if __name__ == "__main__":
    unittest.main()
