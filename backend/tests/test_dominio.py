"""Reglas del dominio sin ningún framework."""

import unittest
from datetime import date, datetime, timezone

from prestamos_academicos.compartido import (
    ErrorDominio, ItemId, ModalidadId, PoliticaServicioId, RolUsuario,
    TransicionInvalida, UsuarioId,
)
from prestamos_academicos.identidad import (
    PerfilDocente, PerfilEstudiante, PerfilGestorInventario, Permiso, ServicioAutorizacionRol,
    Usuario,
)
from prestamos_academicos.inventario import EstadoItem, Libro, listar_tipos, obtener_tipo
from prestamos_academicos.reservas import EstadoReserva, Reserva
from prestamos_academicos.configuracion_servicio import Modalidad, PoliticaServicio
from prestamos_academicos.prestamos import (
    CondicionDevolucion, EstadoPrestamo, Prestamo, PrestamoDevueltoTarde,
)


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

    def test_gestor_solo_tiene_permisos_operativos(self):
        permisos = self.servicio.permisosDe(RolUsuario.GESTOR_INVENTARIO)
        self.assertIn(Permiso.REGISTRAR_ENTREGA_PRESTAMO, permisos)
        self.assertIn(Permiso.REGISTRAR_ITEM_INVENTARIO, permisos)
        self.assertNotIn(Permiso.GESTIONAR_USUARIOS_Y_ROLES, permisos)
        self.assertNotIn(Permiso.CONFIGURAR_POLITICAS, permisos)

    def test_administrador_tiene_todos_los_permisos(self):
        self.assertEqual(self.servicio.permisosDe(RolUsuario.ADMINISTRADOR_SISTEMA), set(Permiso))

    def test_varios_roles_unen_permisos(self):
        self.assertTrue(self.servicio.rolesTienenPermiso(
            [RolUsuario.ESTUDIANTE, RolUsuario.ADMINISTRADOR_SISTEMA],
            Permiso.CONFIGURAR_POLITICAS))


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
    HOY = date(2026, 10, 19)
    AHORA = datetime(2026, 10, 19, 20, 0, tzinfo=timezone.utc)

    def _prestamo(self, items=(1, 2), dias=7, rol=RolUsuario.ESTUDIANTE):
        return Prestamo.entregar(
            usuarioId=UsuarioId(1), politicaId=PoliticaServicioId(1), rol=rol,
            modalidadId=ModalidadId(1), modalidadNombre="Externa", diasPlazo=dias,
            items=[ItemId(i) for i in items], ahora=self.AHORA, hoy=self.HOY)

    def test_plazo_proviene_de_la_politica_aplicada(self):
        self.assertEqual(self._prestamo(dias=7).fechaDevolucionEsperada, date(2026, 10, 26))
        self.assertEqual(self._prestamo(dias=15).fechaDevolucionEsperada, date(2026, 11, 3))
        self.assertEqual(self._prestamo(dias=1).fechaDevolucionEsperada, date(2026, 10, 19))

    def test_entregar_valida_items_y_plazos(self):
        with self.assertRaises(ErrorDominio):
            self._prestamo(items=())
        with self.assertRaises(ErrorDominio):
            self._prestamo(items=(1, 1))
        with self.assertRaises(ErrorDominio):
            self._prestamo(dias=0)
        p = self._prestamo()
        self.assertEqual((p.estado, p.rolSolicitante), (EstadoPrestamo.ACTIVO, RolUsuario.ESTUDIANTE))
        self.assertEqual([d.itemId.valor for d in p.detalles], [1, 2])
        self.assertTrue(all(d.condicion is None for d in p.detalles))

    def test_atraso_y_vencimiento(self):
        p = self._prestamo()                                  # vence el 26-oct
        self.assertEqual((p.diasAtraso(date(2026, 10, 26)), p.estaVencido(date(2026, 10, 26))), (0, False))
        self.assertEqual((p.diasAtraso(date(2026, 10, 29)), p.estaVencido(date(2026, 10, 29))), (3, True))
        self.assertEqual(Prestamo().diasAtraso(self.HOY), 0)  # préstamo anterior: sin fecha límite

    def test_renovacion_extiende_el_plazo_efectivo(self):
        p = self._prestamo()
        p.renovar(self.HOY)
        self.assertEqual((p.fechaDevolucionEsperada, p.numeroRenovaciones),
                         (date(2026, 11, 2), 1))
        with self.assertRaisesRegex(ErrorDominio, "vencido"):
            p.renovar(date(2026, 11, 3))
        p.estado = EstadoPrestamo.DEVUELTO
        with self.assertRaisesRegex(ErrorDominio, "activo"):
            p.renovar(self.HOY)

    def test_devolucion_registra_condicion_por_item_y_eventos(self):
        p = self._prestamo()
        p.registrarDevolucion(
            {1: CondicionDevolucion.BUEN_ESTADO, 2: CondicionDevolucion.DANADO},
            hoy=date(2026, 10, 25), fecha=self.AHORA, observaciones={2: "Pantalla rota"})
        self.assertEqual(p.estado, EstadoPrestamo.DEVUELTO)
        self.assertEqual([d.condicion for d in p.detalles],
                         [CondicionDevolucion.BUEN_ESTADO, CondicionDevolucion.DANADO])
        self.assertEqual(p.detalles[1].observacion, "Pantalla rota")
        self.assertEqual([type(e).__name__ for e in p.eventos], ["PrestamoDevuelto"] * 2)

    def test_devolucion_tardia_publica_el_evento_con_los_dias_de_atraso(self):
        p = self._prestamo()
        p.registrarDevolucion({1: CondicionDevolucion.BUEN_ESTADO, 2: CondicionDevolucion.PERDIDO},
                              hoy=date(2026, 10, 30), fecha=self.AHORA)
        tarde = [e for e in p.eventos if isinstance(e, PrestamoDevueltoTarde)]
        self.assertEqual([(e.diasAtraso, e.usuarioId.valor) for e in tarde], [(4, 1)])

    def test_devolucion_exige_los_items_exactos_y_es_unica(self):
        p = self._prestamo()
        for condiciones in ({}, {1: CondicionDevolucion.BUEN_ESTADO},
                            {1: CondicionDevolucion.BUEN_ESTADO, 2: CondicionDevolucion.BUEN_ESTADO,
                             3: CondicionDevolucion.BUEN_ESTADO}):
            with self.assertRaises(ErrorDominio):
                p.registrarDevolucion(condiciones, hoy=self.HOY)
        self.assertEqual(p.estado, EstadoPrestamo.ACTIVO)       # un intento fallido no cierra nada
        self.assertTrue(all(d.condicion is None for d in p.detalles))
        buenas = {1: CondicionDevolucion.BUEN_ESTADO, 2: CondicionDevolucion.BUEN_ESTADO}
        p.registrarDevolucion(buenas, hoy=self.HOY)
        with self.assertRaisesRegex(ErrorDominio, "ya fue devuelto"):
            p.registrarDevolucion(buenas, hoy=self.HOY)


class ReservaTest(unittest.TestCase):
    def test_ciclo_y_expiracion(self):
        reserva = Reserva.solicitar(
            usuario_id=UsuarioId(1), item_id=ItemId(2), rol=RolUsuario.ESTUDIANTE,
            fecha_solicitud=datetime(2026, 10, 19, tzinfo=timezone.utc),
            fecha_reserva=date(2026, 10, 20), hoy=date(2026, 10, 19))
        self.assertEqual(reserva.estado, EstadoReserva.PENDIENTE)
        self.assertFalse(reserva.estaVencida(date(2026, 10, 20)))
        self.assertTrue(reserva.estaVencida(date(2026, 10, 21)))
        reserva.confirmar()
        self.assertEqual(reserva.estado, EstadoReserva.CONFIRMADA)
        reserva.convertir()
        self.assertEqual(reserva.estado, EstadoReserva.CONVERTIDA)
        with self.assertRaises(ErrorDominio):
            reserva.cancelar()

    def test_rechaza_fecha_pasada_y_transiciones_invalidas(self):
        with self.assertRaises(ErrorDominio):
            Reserva.solicitar(
                usuario_id=UsuarioId(1), item_id=ItemId(2), rol=RolUsuario.ESTUDIANTE,
                fecha_solicitud=datetime.now(timezone.utc), fecha_reserva=date(2026, 10, 18),
                hoy=date(2026, 10, 19))
        reserva = Reserva(estado=EstadoReserva.PENDIENTE)
        reserva.cancelar()
        with self.assertRaises(ErrorDominio):
            reserva.confirmar()


class ReglasDePrestamoTest(unittest.TestCase):
    def test_politica_aplica_cupo_y_tipos(self):
        politica = PoliticaServicio(
            maxItemsSimultaneos=3, diasPrestamo=7,
            tiposRecursoPermitidos=["LIBRO", "equipo"])
        self.assertEqual([politica.cupoRestante(n) for n in (0, 2, 3, 5)], [3, 1, 0, 0])
        self.assertTrue(politica.permiteTipo("libro") and politica.permiteTipo("EQUIPO"))
        self.assertFalse(politica.permiteTipo("MOBILIARIO"))
        self.assertEqual(politica.tiposPermitidos(), ["LIBRO", "EQUIPO"])

    def test_modalidad_es_un_catalogo_sin_reglas_de_plazo(self):
        m = Modalidad(id=ModalidadId(2), nombre="Externa", activo=True)
        self.assertEqual((m.id.valor, m.nombre, m.activo), (2, "Externa", True))
        self.assertNotIn("diasPlazoDefault", vars(m))

    def test_usuario_presta_con_el_perfil_que_elige(self):
        u = Usuario(
            activo=True,
            perfilEstudiante=PerfilEstudiante("E1", True),
            perfilDocente=PerfilDocente("D1", "Contratado", False),
            perfilGestorInventario=PerfilGestorInventario("G1", "Lab", date(2026, 1, 1)))
        u.sincronizarRoles()
        self.assertEqual(u.rolesPrestatarios(), [RolUsuario.ESTUDIANTE, RolUsuario.DOCENTE])
        self.assertTrue(u.vinculacionVigentePara(RolUsuario.ESTUDIANTE))
        self.assertFalse(u.vinculacionVigentePara(RolUsuario.DOCENTE))
        self.assertFalse(u.vinculacionVigentePara(RolUsuario.ADMINISTRATIVO))


if __name__ == "__main__":
    unittest.main()
