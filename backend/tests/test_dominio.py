"""Reglas del dominio sin ningún framework."""

import unittest

from prestamos_academicos.dominio.errores import ErrorDominio, TransicionInvalida
from prestamos_academicos.dominio.identidad import (
    PerfilDocente, PerfilEstudiante, Permiso, ServicioAutorizacionRol, Usuario,
)
from prestamos_academicos.dominio.inventario import EstadoItem, Libro
from prestamos_academicos.dominio.inventario.TiposItem import listar_tipos, obtener_tipo
from prestamos_academicos.dominio.prestamos import EstadoPrestamo, Prestamo
from prestamos_academicos.dominio.shared_kernel import RolUsuario


class ItemTest(unittest.TestCase):
    def test_ciclo_prestamo_y_devolucion(self):
        libro = Libro(codigo="L1", estado=EstadoItem.DISPONIBLE)
        libro.marcarPrestado()
        self.assertEqual(libro.estado, EstadoItem.PRESTADO)
        with self.assertRaises(TransicionInvalida):
            libro.marcarPrestado()
        libro.marcarDisponible()
        self.assertTrue(libro.estaDisponible())

    def test_dado_de_baja_es_terminal(self):
        libro = Libro(codigo="L1", estado=EstadoItem.DISPONIBLE)
        libro.darDeBaja()
        for accion in (libro.marcarDisponible, libro.marcarPrestado, libro.marcarExtraviado):
            with self.assertRaises(ErrorDominio):
                accion()

    def test_tipos_registrados_y_desconocido(self):
        self.assertEqual({t.nombre for t in listar_tipos()},
                         {"LIBRO", "EQUIPO", "MOBILIARIO", "MATERIAL"})
        with self.assertRaises(ErrorDominio):
            obtener_tipo("DRON")


class AutorizacionTest(unittest.TestCase):
    def setUp(self):
        self.servicio = ServicioAutorizacionRol()

    def test_estudiante_no_administra(self):
        permisos = self.servicio.permisosDe(RolUsuario.ESTUDIANTE)
        self.assertIn(Permiso.SOLICITAR_PRESTAMO, permisos)
        self.assertNotIn(Permiso.REGISTRAR_ITEM_INVENTARIO, permisos)
        self.assertNotIn(Permiso.GESTIONAR_USUARIOS_Y_ROLES, permisos)

    def test_docente_y_administrativo_igualan_al_estudiante_en_permisos(self):
        base = self.servicio.permisosDe(RolUsuario.ESTUDIANTE)
        self.assertEqual(self.servicio.permisosDe(RolUsuario.DOCENTE), base)
        self.assertEqual(self.servicio.permisosDe(RolUsuario.ADMINISTRATIVO), base)

    def test_gestor_tiene_todos_los_permisos(self):
        self.assertEqual(self.servicio.permisosDe(RolUsuario.GESTOR_INVENTARIO), set(Permiso))

    def test_varios_roles_unen_permisos(self):
        self.assertTrue(self.servicio.rolesTienenPermiso(
            [RolUsuario.ESTUDIANTE, RolUsuario.GESTOR_INVENTARIO], Permiso.CONFIGURAR_POLITICAS))


class UsuarioTest(unittest.TestCase):
    def _estudiante(self, matricula):
        u = Usuario(nombre="E", perfilEstudiante=PerfilEstudiante("C1", matricula))
        u.sincronizarRoles()
        return u

    def test_estudiante_con_matricula_vigente_esta_habilitado(self):
        self.assertTrue(self._estudiante(True).estaHabilitado())

    def test_estudiante_sin_matricula_no_esta_habilitado(self):
        u = self._estudiante(False)
        self.assertFalse(u.estaHabilitado())
        self.assertIn("matrícula", u.motivoNoHabilitado())

    def test_sancion_activa_deshabilita(self):
        u = self._estudiante(True)
        u.tieneSancionActivaCache = True
        self.assertFalse(u.estaHabilitado())

    def test_docente_no_necesita_matricula_y_roles_se_deducen(self):
        u = Usuario(perfilDocente=PerfilDocente("D1", "Tiempo completo"))
        u.sincronizarRoles()
        self.assertEqual(u.roles, [RolUsuario.DOCENTE])
        self.assertTrue(u.estaHabilitado())

    def test_desactivado_no_esta_habilitado(self):
        u = self._estudiante(True)
        u.activo = False
        self.assertFalse(u.estaHabilitado())


class PrestamoTest(unittest.TestCase):
    def test_devolucion_unica(self):
        p = Prestamo()
        p.registrarDevolucion()
        self.assertEqual(p.estado, EstadoPrestamo.DEVUELTO)
        with self.assertRaises(ErrorDominio):
            p.registrarDevolucion()


if __name__ == "__main__":
    unittest.main()
