from .ayudas import ADMIN, CLAVE, ESTUDIANTE, GESTOR_DOCENTE, ApiBase


class AutenticacionTest(ApiBase):
    def test_salud_publica(self):
        self.assertEqual(self.cliente.get("/api/salud").json, {"estado": "ok"})

    def test_login_devuelve_token_roles_y_permisos(self):
        r = self.cliente.post("/api/auth/login", json={"correo": ESTUDIANTE, "password": CLAVE})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["usuario"]["roles"], ["ESTUDIANTE"])
        self.assertIn("SOLICITAR_PRESTAMO", r.json["usuario"]["permisos"])
        self.assertNotIn("CONFIGURAR_POLITICAS", r.json["usuario"]["permisos"])
        self.assertNotIn("password", str(r.json).lower())

    def test_login_no_distingue_correo_inexistente_de_clave_incorrecta(self):
        a = self.cliente.post("/api/auth/login", json={"correo": ESTUDIANTE, "password": "mala"})
        b = self.cliente.post("/api/auth/login", json={"correo": "nadie@x.edu", "password": "mala"})
        self.assertEqual((a.status_code, b.status_code), (401, 401))
        self.assertEqual(a.json, b.json)

    def test_login_se_bloquea_tras_intentos_fallidos(self):
        for _ in range(5):
            self.cliente.post("/api/auth/login", json={"correo": ESTUDIANTE, "password": "mala"})
        r = self.cliente.post("/api/auth/login", json={"correo": ESTUDIANTE, "password": CLAVE})
        self.assertEqual(r.status_code, 429)

    def test_login_con_cuerpo_invalido(self):
        self.assertEqual(self.cliente.post("/api/auth/login", data="x").status_code, 400)
        self.assertEqual(self.cliente.post(
            "/api/auth/login", json={"correo": 1, "password": 2}).status_code, 401)

    def test_yo_requiere_token_valido(self):
        self.assertEqual(self.cliente.get("/api/auth/yo").status_code, 401)
        r = self.cliente.get("/api/auth/yo", headers={"Authorization": "Bearer basura"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.cliente.get("/api/auth/yo", headers=self.ingresar()).json["correo"], ADMIN)

    def test_cambiar_password(self):
        h = self.ingresar(ESTUDIANTE)
        mala = self.cliente.post("/api/auth/cambiar-password", headers=h,
                                 json={"password_actual": "x", "password_nueva": "nueva-clave-1"})
        self.assertEqual(mala.status_code, 401)
        corta = self.cliente.post("/api/auth/cambiar-password", headers=h,
                                  json={"password_actual": CLAVE, "password_nueva": "corta"})
        self.assertEqual(corta.status_code, 400)
        ok = self.cliente.post("/api/auth/cambiar-password", headers=h,
                               json={"password_actual": CLAVE, "password_nueva": "nueva-clave-1"})
        self.assertEqual(ok.status_code, 200)
        self.ingresar(ESTUDIANTE, "nueva-clave-1")

    def test_usuario_desactivado_pierde_acceso_aunque_tenga_token(self):
        admin = self.ingresar()
        h = self.ingresar(ESTUDIANTE)
        uid = self.usuario_id(ESTUDIANTE, admin)
        self.assertEqual(self.cliente.patch(f"/api/usuarios/{uid}", headers=admin,
                                            json={"activo": False}).status_code, 200)
        self.assertEqual(self.cliente.get("/api/auth/yo", headers=h).status_code, 401)
        r = self.cliente.post("/api/auth/login", json={"correo": ESTUDIANTE, "password": CLAVE})
        self.assertEqual(r.status_code, 401)


class GestionUsuariosTest(ApiBase):
    NUEVO = {
        "nombre": "Ana Quispe", "correo": "Ana.Quispe@escuela.edu", "password": "clave-segura-1",
        "perfiles": {"ESTUDIANTE": {"codigo_estudiante": "EST-2026-050"}},
    }

    def test_solo_el_gestor_gestiona_usuarios(self):
        h = self.ingresar(ESTUDIANTE)
        self.assertEqual(self.cliente.get("/api/usuarios", headers=h).status_code, 403)
        self.assertEqual(self.cliente.post("/api/usuarios", headers=h, json=self.NUEVO).status_code, 403)
        self.assertEqual(self.cliente.get("/api/usuarios").status_code, 401)

    def test_registrar_usuario_asigna_politica_del_perfil(self):
        h = self.ingresar()
        r = self.cliente.post("/api/usuarios", headers=h, json=self.NUEVO)
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual(r.json["correo"], "ana.quispe@escuela.edu")
        self.assertEqual(r.json["roles"], ["ESTUDIANTE"])
        self.assertTrue(r.json["habilitado"])
        politica = r.json["perfiles"]["ESTUDIANTE"]["politica_servicio_id"]
        politicas = self.cliente.get("/api/politicas", headers=h).json
        self.assertEqual(next(p for p in politicas if p["id"] == politica)["rol"], "ESTUDIANTE")
        self.ingresar("ana.quispe@escuela.edu", "clave-segura-1")
        self.assertNotIn("password", str(r.json).lower())

    def test_usuario_con_varios_roles(self):
        h = self.ingresar()
        datos = dict(self.NUEVO, correo="multi@escuela.edu", perfiles={
            "DOCENTE": {"codigo_empleado": "DOC-9", "tipo_contrato": "Parcial"},
            "GESTOR_INVENTARIO": {"codigo_empleado": "DOC-9", "area_responsable": "Biblioteca"}})
        r = self.cliente.post("/api/usuarios", headers=h, json=datos)
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual(sorted(r.json["roles"]), ["DOCENTE", "GESTOR_INVENTARIO"])
        self.assertIsNotNone(r.json["perfiles"]["GESTOR_INVENTARIO"]["fecha_asignacion"])

    def test_validaciones_de_registro(self):
        h = self.ingresar()
        casos = {
            "sin perfiles": dict(self.NUEVO, perfiles={}),
            "rol desconocido": dict(self.NUEVO, perfiles={"ALUMNO": {}}),
            "perfil incompleto": dict(self.NUEVO, perfiles={"ESTUDIANTE": {}}),
            "correo inválido": dict(self.NUEVO, correo="no-es-correo"),
            "clave corta": dict(self.NUEVO, password="abc"),
            "sin nombre": dict(self.NUEVO, nombre="  "),
        }
        for nombre, cuerpo in casos.items():
            r = self.cliente.post("/api/usuarios", headers=h, json=cuerpo)
            self.assertEqual(r.status_code, 400, nombre)

    def test_correo_y_codigo_duplicados(self):
        h = self.ingresar()
        self.assertEqual(self.cliente.post("/api/usuarios", headers=h, json=self.NUEVO).status_code, 201)
        r = self.cliente.post("/api/usuarios", headers=h, json=self.NUEVO)
        self.assertEqual(r.status_code, 409)
        otro = dict(self.NUEVO, correo="otra@escuela.edu")  # mismo código de estudiante
        self.assertEqual(self.cliente.post("/api/usuarios", headers=h, json=otro).status_code, 409)

    def test_usuario_sin_password_no_puede_ingresar_hasta_que_se_asigne(self):
        h = self.ingresar()
        datos = {k: v for k, v in self.NUEVO.items() if k != "password"}
        uid = self.cliente.post("/api/usuarios", headers=h, json=datos).json["id"]
        r = self.cliente.post("/api/auth/login", json={"correo": datos["correo"], "password": "x" * 10})
        self.assertEqual(r.status_code, 401)
        self.cliente.patch(f"/api/usuarios/{uid}", headers=h, json={"password": "asignada-123"})
        self.ingresar(datos["correo"].lower(), "asignada-123")

    def test_actualizar_matricula_deshabilita_al_estudiante(self):
        h = self.ingresar()
        uid = self.usuario_id(ESTUDIANTE, h)
        r = self.cliente.patch(f"/api/usuarios/{uid}", headers=h,
                               json={"perfiles": {"ESTUDIANTE": {"matricula_vigente": False}}})
        self.assertEqual(r.status_code, 200, r.json)
        self.assertFalse(r.json["habilitado"])
        self.assertEqual(r.json["perfiles"]["ESTUDIANTE"]["codigo_estudiante"], "EST-2026-001")
        habilitados = self.cliente.get("/api/usuarios?habilitado=true", headers=h).json
        self.assertNotIn(ESTUDIANTE, [u["correo"] for u in habilitados])

    def test_agregar_y_quitar_perfil(self):
        h = self.ingresar()
        uid = self.usuario_id(ESTUDIANTE, h)
        r = self.cliente.patch(f"/api/usuarios/{uid}", headers=h, json={"perfiles": {
            "DOCENTE": {"codigo_empleado": "DOC-77", "tipo_contrato": "Contratado"}}})
        self.assertEqual(sorted(r.json["roles"]), ["DOCENTE", "ESTUDIANTE"])
        r = self.cliente.patch(f"/api/usuarios/{uid}", headers=h, json={"perfiles": {"ESTUDIANTE": None}})
        self.assertEqual(r.json["roles"], ["DOCENTE"])
        r = self.cliente.patch(f"/api/usuarios/{uid}", headers=h, json={"perfiles": {"DOCENTE": None}})
        self.assertEqual(r.status_code, 400)

    def test_filtros_de_listado(self):
        h = self.ingresar()
        gestores = self.cliente.get("/api/usuarios?rol=GESTOR_INVENTARIO", headers=h).json
        self.assertEqual({u["correo"] for u in gestores}, {ADMIN, GESTOR_DOCENTE})
        self.assertEqual([u["correo"] for u in
                          self.cliente.get("/api/usuarios?q=jesus", headers=h).json], [ESTUDIANTE])
        self.assertEqual(self.cliente.get("/api/usuarios?rol=XX", headers=h).status_code, 400)
        self.assertEqual(self.cliente.get("/api/usuarios?activo=quizas", headers=h).status_code, 400)

    def test_no_puede_autodesactivarse_ni_quitarse_el_gestor(self):
        h = self.ingresar()
        yo = self.usuario_id(ADMIN, h)
        self.assertEqual(self.cliente.patch(f"/api/usuarios/{yo}", headers=h,
                                            json={"activo": False}).status_code, 409)
        self.assertEqual(self.cliente.patch(f"/api/usuarios/{yo}", headers=h, json={
            "perfiles": {"GESTOR_INVENTARIO": None}}).status_code, 409)

    def test_siempre_queda_un_gestor_activo(self):
        h = self.ingresar()
        luis = self.usuario_id(GESTOR_DOCENTE, h)
        self.assertEqual(self.cliente.patch(f"/api/usuarios/{luis}", headers=h,
                                            json={"activo": False}).status_code, 200)
        h_luis = None  # Luis ya no puede entrar; el admin es el último gestor activo
        admin = self.usuario_id(ADMIN, h)
        otro = self.cliente.post("/api/usuarios", headers=h, json=dict(
            self.NUEVO, correo="g2@escuela.edu", perfiles={"GESTOR_INVENTARIO": {
                "codigo_empleado": "G-2", "area_responsable": "X"}})).json["id"]
        h2 = self.ingresar("g2@escuela.edu", "clave-segura-1")
        # g2 intenta desactivar al último otro gestor mientras existen dos: permitido
        self.assertEqual(self.cliente.patch(f"/api/usuarios/{admin}", headers=h2,
                                            json={"activo": False}).status_code, 200)
        # ahora g2 es el único gestor activo: nadie puede quitarle el rol
        self.assertEqual(self.cliente.patch(f"/api/usuarios/{otro}", headers=h2,
                                            json={"perfiles": {"GESTOR_INVENTARIO": None,
                                                               "DOCENTE": {"codigo_empleado": "X",
                                                                           "tipo_contrato": "Y"}}}
                                            ).status_code, 409)
        self.assertIsNone(h_luis)

    def test_usuario_inexistente(self):
        h = self.ingresar()
        self.assertEqual(self.cliente.get("/api/usuarios/9999", headers=h).status_code, 404)
        self.assertEqual(self.cliente.patch("/api/usuarios/9999", headers=h, json={}).status_code, 404)

    def test_politicas_por_perfil(self):
        politicas = self.cliente.get("/api/politicas", headers=self.ingresar(ESTUDIANTE)).json
        por_rol = {p["rol"]: p for p in politicas}
        self.assertEqual(set(por_rol), {"ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO"})
        self.assertLess(por_rol["ESTUDIANTE"]["max_items_simultaneos"],
                        por_rol["DOCENTE"]["max_items_simultaneos"])
        self.assertNotIn("MOBILIARIO", por_rol["ESTUDIANTE"]["tipos_recurso_permitidos"])
        self.assertEqual(self.cliente.get("/api/politicas").status_code, 401)
