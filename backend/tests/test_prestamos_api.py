"""Préstamos completos (Sprint 3): varios ítems, modalidades, plazo, cupos y devolución."""

from datetime import date, datetime, timedelta, timezone

from prestamos_academicos.infraestructura.persistencia.modelos import ModalidadDB

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR_DOCENTE, IN_SITU, ApiBase

BUEN = "BUEN_ESTADO"


class PrestamosBase(ApiBase):
    def entregar(self, h, correo=ESTUDIANTE, codigos=("LIB-CLRS",), modalidad=EXTERNA, **extra):
        cuerpo = {"usuario_id": self.usuario_id(correo), "modalidad_id": self.modalidad_id(modalidad),
                  "item_ids": [self.item_id(c) for c in codigos], **extra}
        return self.cliente.post("/api/prestamos", headers=h, json=cuerpo)

    def condiciones(self, prestamo, condicion=BUEN, **por_item):
        return {"condiciones": [
            {"item_id": i["item_id"], "condicion": por_item.get(i["codigo"], condicion)}
            for i in prestamo["items"]]}

    def devolver(self, h, prestamo, cuerpo=None):
        return self.cliente.post(f"/api/prestamos/{prestamo['id']}/devolucion", headers=h,
                                 json=cuerpo if cuerpo is not None else self.condiciones(prestamo))

    def crear_item(self, h, codigo, tipo="LIBRO"):
        atributos = {"LIBRO": {"isbn": "1", "autor": "A"}, "MOBILIARIO": {"tipoMobiliario": "Mesa"},
                     "MATERIAL": {"tipoMaterial": "Cable"}}[tipo]
        r = self.cliente.post("/api/items", headers=h, json={
            "tipo": tipo, "codigo": codigo, "nombre": f"Recurso {codigo}",
            "categoria": "Pruebas", "atributos": atributos})
        self.assertEqual(r.status_code, 201, r.json)
        return r.json["id"]


class PermisosTest(PrestamosBase):
    def test_requiere_autenticacion_y_permiso_de_gestor(self):
        self.assertEqual(self.cliente.get("/api/prestamos").status_code, 401)
        self.assertEqual(self.cliente.post("/api/prestamos", json={}).status_code, 401)
        h = self.ingresar(ESTUDIANTE)
        self.assertEqual(self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": 1, "item_ids": [1], "modalidad_id": 1}).status_code, 403)
        self.assertEqual(self.cliente.post("/api/prestamos/1/devolucion", headers=h,
                                           json={"condiciones": []}).status_code, 403)
        self.assertEqual(self.cliente.get("/api/prestamos/condiciones?usuario_id=1&modalidad_id=1",
                                          headers=h).status_code, 403)

    def test_gestor_opera_prestamos_sin_administrar_usuarios(self):
        gestor = self.ingresar(GESTOR_DOCENTE)
        prestatarios = self.cliente.get("/api/usuarios/prestatarios", headers=gestor).json
        jesus = next(u for u in prestatarios if u["nombre"] == "Jesus Perez")
        entrega = self.cliente.post("/api/prestamos", headers=gestor, json={
            "usuario_id": jesus["id"], "item_ids": [self.item_id("LIB-CLRS")],
            "modalidad_id": self.modalidad_id()})
        self.assertEqual(entrega.status_code, 201, entrega.json)
        self.assertEqual(self.cliente.get("/api/usuarios", headers=gestor).status_code, 403)

    def test_modalidades_exigen_sesion(self):
        self.assertEqual(self.cliente.get("/api/modalidades").status_code, 401)
        lista = self.cliente.get("/api/modalidades", headers=self.ingresar(ESTUDIANTE)).json
        self.assertEqual([(m["nombre"], m["dias_plazo_default"]) for m in lista],
                         [(IN_SITU, 1), (EXTERNA, 15)])


class EntregaTest(PrestamosBase):
    def test_entrega_con_varios_items_calcula_plazo_y_marca_prestados(self):
        h = self.ingresar()
        r = self.entregar(h, codigos=("LIB-CLRS", "LIB-CLEAN"))
        self.assertEqual(r.status_code, 201, r.json)
        p = r.json
        self.assertEqual([i["codigo"] for i in p["items"]], ["LIB-CLRS", "LIB-CLEAN"])
        self.assertEqual((p["estado"], p["vencido"], p["dias_atraso"]), ("activo", False, 0))
        self.assertEqual((p["modalidad"], p["rol_solicitante"]), (EXTERNA, "ESTUDIANTE"))
        # Externa permite 15 días, pero la política de estudiante solo 7: gana el menor (RN2).
        self.assertEqual(p["fecha_limite"], "2026-10-26")
        for codigo in ("LIB-CLRS", "LIB-CLEAN"):
            self.assertEqual(self.estado_item(codigo), "PRESTADO")

    def test_el_plazo_depende_de_la_modalidad_y_del_perfil(self):
        h = self.ingresar()
        en_sala = self.entregar(h, ESTUDIANTE, ("LIB-CLRS",), IN_SITU).json
        self.assertEqual(en_sala["fecha_limite"], "2026-10-20")      # modalidad: 1 día
        docente = self.entregar(h, GESTOR_DOCENTE, ("EQ-META",), EXTERNA).json
        self.assertEqual(docente["fecha_limite"], "2026-11-03")      # docente: 15 días
        self.assertEqual(docente["rol_solicitante"], "DOCENTE")

    def test_el_dia_se_mide_en_hora_de_lima_no_en_utc(self):
        # 20-oct 02:00 UTC = 19-oct 21:00 en Lima: el plazo cuenta desde el 19.
        self.reloj.instante = datetime(2026, 10, 20, 2, 0, tzinfo=timezone.utc)
        p = self.entregar(self.ingresar(), codigos=("LIB-CLRS",), modalidad=IN_SITU).json
        self.assertEqual(p["fecha_limite"], "2026-10-20")

    def test_previsualizacion_coincide_con_la_entrega_y_muestra_el_cupo(self):
        h = self.ingresar()
        uid, mid = self.usuario_id(ESTUDIANTE), self.modalidad_id()
        url = f"/api/prestamos/condiciones?usuario_id={uid}&modalidad_id={mid}"
        antes = self.cliente.get(url, headers=h).json
        self.assertEqual((antes["dias_plazo"], antes["fecha_limite"], antes["cupo_restante"]),
                         (7, "2026-10-26", 3))
        self.assertEqual(antes["tipos_permitidos"], ["LIBRO", "EQUIPO", "MATERIAL"])
        entrega = self.entregar(h, codigos=("LIB-CLRS", "LIB-CLEAN")).json
        despues = self.cliente.get(url, headers=h).json
        self.assertEqual((despues["items_en_prestamo"], despues["cupo_restante"]), (2, 1))
        self.assertEqual(despues["fecha_limite"], entrega["fecha_limite"])
        self.assertEqual(self.cliente.get(url + "&rol_solicitante=DOCENTE", headers=h).status_code, 422)
        self.assertEqual(self.cliente.get("/api/prestamos/condiciones?usuario_id=x&modalidad_id=1",
                                          headers=h).status_code, 400)

    def test_previsualizacion_pide_el_perfil_si_el_usuario_tiene_varios(self):
        h = self.ingresar()
        self.cliente.post("/api/usuarios", headers=h, json={
            "nombre": "Doble Perfil", "correo": "doble@escuela.edu", "password": "clave-larga-1",
            "perfiles": {"ESTUDIANTE": {"codigo_estudiante": "EST-DOB"},
                         "DOCENTE": {"codigo_empleado": "DOC-DOB", "tipo_contrato": "Contratado"}}})
        uid, mid = self.usuario_id("doble@escuela.edu", h), self.modalidad_id()
        base = f"/api/prestamos/condiciones?usuario_id={uid}&modalidad_id={mid}"
        sin_rol = self.cliente.get(base, headers=h).json
        self.assertIsNone(sin_rol["rol_solicitante"])
        self.assertEqual(sin_rol["roles_posibles"], ["ESTUDIANTE", "DOCENTE"])
        self.assertNotIn("fecha_limite", sin_rol)
        docente = self.cliente.get(base + "&rol_solicitante=DOCENTE", headers=h).json
        self.assertEqual((docente["dias_plazo"], docente["cupo_restante"]), (15, 5))

    def test_cupo_por_perfil_se_aplica_y_se_libera_al_devolver(self):
        h = self.ingresar()
        for n in range(3):
            self.crear_item(h, f"LIB-X{n}")
        cuatro = self.entregar(h, codigos=("LIB-CLRS", "LIB-CLEAN", "LIB-X0", "LIB-X1"))
        self.assertEqual(cuatro.status_code, 422)
        self.assertIn("máximo 3", cuatro.json["error"])
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")   # nada quedó prestado

        tres = self.entregar(h, codigos=("LIB-CLRS", "LIB-CLEAN", "LIB-X0"))
        self.assertEqual(tres.status_code, 201)
        extra = self.entregar(h, codigos=("LIB-X1",))
        self.assertEqual(extra.status_code, 422)
        self.assertIn("tiene 3 en préstamo", extra.json["error"])

        self.assertEqual(self.devolver(h, tres.json).status_code, 200)
        self.assertEqual(self.entregar(h, codigos=("LIB-X1",)).status_code, 201)

    def test_el_cupo_depende_de_la_politica_del_perfil(self):
        h = self.ingresar()
        for n in range(5):
            self.crear_item(h, f"LIB-D{n}")
        cinco = self.entregar(h, GESTOR_DOCENTE, tuple(f"LIB-D{n}" for n in range(5)))
        self.assertEqual(cinco.status_code, 201, cinco.json)   # docente: hasta 5

    def test_la_politica_restringe_los_tipos_de_recurso(self):
        h = self.ingresar()
        self.crear_item(h, "MOB-1", "MOBILIARIO")
        estudiante = self.entregar(h, ESTUDIANTE, ("MOB-1",))
        self.assertEqual(estudiante.status_code, 422)
        self.assertIn("MOB-1", estudiante.json["error"])
        self.assertEqual(self.entregar(h, GESTOR_DOCENTE, ("MOB-1",)).status_code, 201)

    def test_un_item_no_se_presta_dos_veces_ni_en_otro_estado(self):
        h = self.ingresar()
        self.assertEqual(self.entregar(h).status_code, 201)
        repetido = self.entregar(h, GESTOR_DOCENTE)
        self.assertEqual(repetido.status_code, 409)
        self.assertIn("LIB-CLRS (PRESTADO)", repetido.json["error"])
        self.cliente.post(f"/api/items/{self.item_id('EQ-META')}/estado", headers=h,
                          json={"estado": "EN_MANTENIMIENTO"})
        mant = self.entregar(h, ESTUDIANTE, ("EQ-META",))
        self.assertEqual(mant.status_code, 409)
        self.assertIn("EN_MANTENIMIENTO", mant.json["error"])

    def test_la_entrega_es_todo_o_nada(self):
        h = self.ingresar()
        self.cliente.post(f"/api/items/{self.item_id('EQ-META')}/estado", headers=h,
                          json={"estado": "EN_MANTENIMIENTO"})
        r = self.entregar(h, codigos=("LIB-CLRS", "EQ-META"))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")
        self.assertEqual(self.cliente.get("/api/prestamos", headers=h).json["total"], 0)

    def test_modalidad_inexistente_o_inactiva(self):
        h = self.ingresar()
        uid, iid = self.usuario_id(ESTUDIANTE), self.item_id("LIB-CLRS")
        post = lambda mid: self.cliente.post("/api/prestamos", headers=h, json={  # noqa: E731
            "usuario_id": uid, "item_ids": [iid], "modalidad_id": mid})
        self.assertEqual(post(999).status_code, 404)
        with self.app.extensions["fabrica_sesiones"].begin() as sesion:
            sesion.get(ModalidadDB, self.modalidad_id(IN_SITU)).activo = False
        r = post(self.modalidad_id(IN_SITU))
        self.assertEqual(r.status_code, 422)
        self.assertIn("no está activa", r.json["error"])
        self.assertEqual(post(self.modalidad_id(EXTERNA)).status_code, 201)

    def test_no_se_presta_a_usuarios_no_habilitados(self):
        h = self.ingresar()
        uid = self.usuario_id(ESTUDIANTE, h)
        self.cliente.patch(f"/api/usuarios/{uid}", headers=h,
                           json={"perfiles": {"ESTUDIANTE": {"matricula_vigente": False}}})
        r = self.entregar(h)
        self.assertEqual(r.status_code, 422)
        self.assertIn("vinculación", r.json["error"])
        # un administrador sin rol prestatario tampoco recibe recursos
        self.assertEqual(self.entregar(h, ADMIN).status_code, 422)

    def test_validacion_de_datos(self):
        h = self.ingresar()
        uid, iid, mid = self.usuario_id(ESTUDIANTE, h), self.item_id("LIB-CLRS"), self.modalidad_id()
        post = lambda cuerpo: self.cliente.post("/api/prestamos", headers=h, json=cuerpo)  # noqa: E731
        base = {"usuario_id": uid, "item_ids": [iid], "modalidad_id": mid}
        self.assertEqual(post({}).status_code, 400)
        self.assertEqual(post({**base, "item_ids": []}).status_code, 400)
        self.assertEqual(post({**base, "item_ids": iid}).status_code, 400)
        self.assertEqual(post({**base, "item_ids": ["1"]}).status_code, 400)
        self.assertEqual(post({**base, "item_ids": [iid, iid]}).status_code, 400)
        self.assertEqual(post({**base, "item_ids": list(range(1, 52))}).status_code, 400)
        self.assertEqual(post({**base, "item_id": iid}).status_code, 400)       # campo antiguo
        self.assertEqual(post({**base, "forzar": True}).status_code, 400)
        self.assertEqual(post({**base, "modalidad_id": None}).status_code, 400)
        self.assertEqual(post({**base, "rol_solicitante": 5}).status_code, 400)
        self.assertEqual(post({**base, "rol_solicitante": "REY"}).status_code, 400)
        self.assertEqual(post({**base, "usuario_id": 2 ** 63}).status_code, 400)
        self.assertEqual(post({**base, "usuario_id": 999}).status_code, 404)
        self.assertEqual(post({**base, "item_ids": [999]}).status_code, 404)

    def test_usuario_con_varios_perfiles_debe_indicar_con_cual_presta(self):
        h = self.ingresar()
        alta = self.cliente.post("/api/usuarios", headers=h, json={
            "nombre": "Doble Perfil", "correo": "doble@escuela.edu", "password": "clave-larga-1",
            "perfiles": {"ESTUDIANTE": {"codigo_estudiante": "EST-DOB"},
                         "DOCENTE": {"codigo_empleado": "DOC-DOB", "tipo_contrato": "Contratado"}}})
        self.assertEqual(alta.status_code, 201, alta.json)
        sin_rol = self.entregar(h, "doble@escuela.edu")
        self.assertEqual(sin_rol.status_code, 400)
        self.assertIn("varios perfiles", sin_rol.json["error"])
        como_docente = self.entregar(h, "doble@escuela.edu", rol_solicitante="DOCENTE")
        self.assertEqual(como_docente.status_code, 201, como_docente.json)
        self.assertEqual(como_docente.json["rol_solicitante"], "DOCENTE")
        self.assertEqual(como_docente.json["fecha_limite"], "2026-11-03")
        ajeno = self.entregar(h, "doble@escuela.edu", ("EQ-META",), rol_solicitante="ADMINISTRATIVO")
        self.assertEqual(ajeno.status_code, 422)

    def test_se_exige_vinculacion_vigente_en_el_perfil_elegido(self):
        h = self.ingresar()
        self.cliente.post("/api/usuarios", headers=h, json={
            "nombre": "Doble Perfil", "correo": "doble@escuela.edu", "password": "clave-larga-1",
            "perfiles": {"ESTUDIANTE": {"codigo_estudiante": "EST-DOB"},
                         "DOCENTE": {"codigo_empleado": "DOC-DOB", "tipo_contrato": "Contratado"}}})
        uid = self.usuario_id("doble@escuela.edu", h)
        self.cliente.patch(f"/api/usuarios/{uid}", headers=h, json={
            "perfiles": {"DOCENTE": {"vinculacion_vigente": False}}})
        como_docente = self.entregar(h, "doble@escuela.edu", rol_solicitante="DOCENTE")
        self.assertEqual(como_docente.status_code, 422)
        self.assertIn("DOCENTE", como_docente.json["error"])
        como_estudiante = self.entregar(h, "doble@escuela.edu", rol_solicitante="ESTUDIANTE")
        self.assertEqual(como_estudiante.status_code, 201, como_estudiante.json)


class DevolucionTest(PrestamosBase):
    def test_devolucion_deja_cada_item_segun_su_condicion(self):
        h = self.ingresar()
        self.crear_item(h, "LIB-X0")
        p = self.entregar(h, codigos=("LIB-CLRS", "LIB-CLEAN", "LIB-X0")).json
        cuerpo = {"condiciones": [
            {"item_id": self.item_id("LIB-CLRS"), "condicion": BUEN},
            {"item_id": self.item_id("LIB-CLEAN"), "condicion": "DANADO",
             "observacion": "Páginas arrancadas"},
            {"item_id": self.item_id("LIB-X0"), "condicion": "perdido"},
        ]}
        r = self.devolver(h, p, cuerpo)
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(r.json["estado"], "devuelto")
        self.assertIsNotNone(r.json["fecha_devolucion"])
        self.assertEqual({i["codigo"]: i["condicion"] for i in r.json["items"]},
                         {"LIB-CLRS": BUEN, "LIB-CLEAN": "DANADO", "LIB-X0": "PERDIDO"})
        self.assertEqual(next(i for i in r.json["items"] if i["codigo"] == "LIB-CLEAN")["observacion"],
                         "Páginas arrancadas")
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")
        self.assertEqual(self.estado_item("LIB-CLEAN"), "EN_MANTENIMIENTO")
        self.assertEqual(self.estado_item("LIB-X0"), "EXTRAVIADO")
        # un recurso dañado no se vuelve a prestar hasta que el gestor lo habilite
        self.assertEqual(self.entregar(h, codigos=("LIB-CLEAN",)).status_code, 409)
        self.cliente.post(f"/api/items/{self.item_id('LIB-CLEAN')}/estado", headers=h,
                          json={"estado": "DISPONIBLE"})
        self.assertEqual(self.entregar(h, codigos=("LIB-CLEAN",)).status_code, 201)

    def test_la_devolucion_exige_la_condicion_de_todos_los_items(self):
        h = self.ingresar()
        p = self.entregar(h, codigos=("LIB-CLRS", "LIB-CLEAN")).json
        uno, otro = self.item_id("LIB-CLRS"), self.item_id("LIB-CLEAN")
        casos = [
            ({"condiciones": [{"item_id": uno, "condicion": BUEN}]}, 422),              # falta uno
            ({"condiciones": [{"item_id": uno, "condicion": BUEN},
                              {"item_id": otro, "condicion": BUEN},
                              {"item_id": 999, "condicion": BUEN}]}, 422),               # sobra uno
            ({"condiciones": [{"item_id": uno, "condicion": BUEN},
                              {"item_id": uno, "condicion": BUEN}]}, 400),               # repetido
            ({"condiciones": [{"item_id": uno, "condicion": "ROTO"}]}, 400),
            ({"condiciones": [{"item_id": uno, "condicion": BUEN, "nota": "x"}]}, 400),
            ({"condiciones": [{"item_id": "1", "condicion": BUEN}]}, 400),
            ({"condiciones": [{"item_id": uno, "condicion": BUEN, "observacion": "x" * 301}]}, 400),
            ({"condiciones": []}, 400), ({"condiciones": "todo bien"}, 400), ({}, 400),
            ({"condiciones": [], "otro": 1}, 400),
        ]
        for cuerpo, esperado in casos:
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.devolver(h, p, cuerpo).status_code, esperado)
        # ninguna devolución fallida cambió el estado de los recursos
        self.assertEqual(self.estado_item("LIB-CLRS"), "PRESTADO")
        self.assertEqual(self.cliente.get(f"/api/prestamos/{p['id']}", headers=h).json["estado"], "activo")

    def test_un_prestamo_se_devuelve_una_sola_vez(self):
        h = self.ingresar()
        p = self.entregar(h).json
        self.assertEqual(self.devolver(h, p).status_code, 200)
        self.assertEqual(self.devolver(h, p).status_code, 409)
        self.assertEqual(self.cliente.post("/api/prestamos/999/devolucion", headers=h, json={
            "condiciones": [{"item_id": 1, "condicion": BUEN}]}).status_code, 404)

    def test_el_atraso_se_mide_contra_la_fecha_limite(self):
        h = self.ingresar()
        p = self.entregar(h, codigos=("LIB-CLRS",), modalidad=IN_SITU).json     # vence el 20-oct
        self.reloj.instante += timedelta(days=1)                                # 20-oct: aún a tiempo
        hoy = self.cliente.get(f"/api/prestamos/{p['id']}", headers=h).json
        self.assertEqual((hoy["vencido"], hoy["dias_atraso"]), (False, 0))
        self.reloj.instante += timedelta(days=3)                                # 23-oct: 3 días tarde
        tarde = self.cliente.get(f"/api/prestamos/{p['id']}", headers=h).json
        self.assertEqual((tarde["vencido"], tarde["dias_atraso"], tarde["estado"]), (True, 3, "activo"))
        vencidos = self.cliente.get("/api/prestamos?estado=vencido", headers=h).json
        self.assertEqual([x["id"] for x in vencidos["prestamos"]], [p["id"]])

        devuelto = self.devolver(h, p).json
        self.assertEqual((devuelto["estado"], devuelto["vencido"], devuelto["dias_atraso"]),
                         ("devuelto", False, 3))
        self.assertEqual(self.cliente.get("/api/prestamos?estado=vencido", headers=h).json["total"], 0)

    def test_devolver_a_tiempo_no_registra_atraso(self):
        h = self.ingresar()
        p = self.entregar(h).json
        self.reloj.instante += timedelta(days=7)                  # justo el día límite
        self.assertEqual(self.devolver(h, p).json["dias_atraso"], 0)


class ConsultaTest(PrestamosBase):
    def test_cada_usuario_ve_solo_sus_prestamos_y_el_gestor_todos(self):
        h = self.ingresar()
        propio = self.entregar(h, ESTUDIANTE, ("LIB-CLRS",)).json
        ajeno = self.entregar(h, GESTOR_DOCENTE, ("EQ-META",)).json
        est = self.ingresar(ESTUDIANTE)
        propios = self.cliente.get("/api/prestamos", headers=est).json
        self.assertEqual([p["id"] for p in propios["prestamos"]], [propio["id"]])
        self.assertEqual(self.cliente.get("/api/prestamos", headers=h).json["total"], 2)
        self.assertEqual(self.cliente.get(f"/api/prestamos/{propio['id']}", headers=est).status_code, 200)
        self.assertEqual(self.cliente.get(f"/api/prestamos/{ajeno['id']}", headers=est).status_code, 404)
        self.assertEqual(self.cliente.get(f"/api/prestamos/{ajeno['id']}", headers=h).status_code, 200)

    def test_filtro_por_estado_y_paginacion(self):
        h = self.ingresar()
        a = self.entregar(h, ESTUDIANTE, ("LIB-CLRS",)).json
        self.entregar(h, GESTOR_DOCENTE, ("EQ-META",))
        self.devolver(h, a)
        listar = lambda q: self.cliente.get(f"/api/prestamos{q}", headers=h).json  # noqa: E731
        self.assertEqual([p["estado"] for p in listar("?estado=activo")["prestamos"]], ["activo"])
        self.assertEqual([p["id"] for p in listar("?estado=devuelto")["prestamos"]], [a["id"]])
        pagina = listar("?limite=1&pagina=2")
        self.assertEqual((pagina["total"], len(pagina["prestamos"]), pagina["pagina"]), (2, 1, 2))
        for q in ("?estado=roto", "?pagina=0", "?limite=101", "?otro=1"):
            self.assertEqual(self.cliente.get(f"/api/prestamos{q}", headers=h).status_code, 400, q)
        self.assertEqual(self.cliente.get("/api/prestamos/999", headers=h).status_code, 404)

    def test_un_item_prestado_no_admite_cambio_manual_de_estado(self):
        h = self.ingresar()
        self.entregar(h)
        r = self.cliente.post(f"/api/items/{self.item_id('LIB-CLRS')}/estado", headers=h,
                              json={"estado": "DADO_DE_BAJA"})
        self.assertEqual(r.status_code, 409)
