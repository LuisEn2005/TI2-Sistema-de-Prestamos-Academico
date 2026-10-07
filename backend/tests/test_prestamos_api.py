from .ayudas import ESTUDIANTE, GESTOR_DOCENTE, ApiBase


class PrestamosTest(ApiBase):
    def prestar(self, h, correo=ESTUDIANTE, codigo="LIB-CLRS"):
        return self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": self.usuario_id(correo), "item_id": self.item_id(codigo)})

    def test_requiere_autenticacion_y_permiso_de_gestor(self):
        self.assertEqual(self.cliente.get("/api/prestamos").status_code, 401)
        self.assertEqual(self.cliente.post("/api/prestamos", json={}).status_code, 401)
        h = self.ingresar(ESTUDIANTE)
        self.assertEqual(self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": 1, "item_id": 1}).status_code, 403)
        self.assertEqual(self.cliente.post("/api/prestamos/1/devolucion", headers=h).status_code, 403)

    def test_ciclo_prestar_y_devolver_actualiza_el_estado_del_item(self):
        h = self.ingresar()
        iid = self.item_id("LIB-CLRS")
        p = self.prestar(h)
        self.assertEqual(p.status_code, 201, p.json)
        self.assertEqual(p.json["estado"], "activo")
        self.assertEqual(self.cliente.get(f"/api/items/{iid}").json["estado"], "PRESTADO")

        self.assertEqual(self.prestar(h).status_code, 409)

        d = self.cliente.post(f"/api/prestamos/{p.json['id']}/devolucion", headers=h)
        self.assertEqual((d.status_code, d.json["estado"]), (200, "devuelto"))
        self.assertEqual(self.cliente.get(f"/api/items/{iid}").json["estado"], "DISPONIBLE")
        self.assertEqual(self.cliente.post(f"/api/prestamos/{p.json['id']}/devolucion",
                                           headers=h).status_code, 409)
        self.assertEqual(self.prestar(h).status_code, 201)

    def test_cada_usuario_ve_solo_sus_prestamos_y_el_gestor_todos(self):
        h = self.ingresar()
        self.prestar(h, ESTUDIANTE, "LIB-CLRS")
        self.prestar(h, GESTOR_DOCENTE, "EQ-META")
        propios = self.cliente.get("/api/prestamos", headers=self.ingresar(ESTUDIANTE)).json
        self.assertEqual([p["codigo"] for p in propios], ["LIB-CLRS"])
        self.assertEqual(len(self.cliente.get("/api/prestamos", headers=h).json), 2)

    def test_no_se_presta_a_usuarios_no_habilitados(self):
        h = self.ingresar()
        uid = self.usuario_id(ESTUDIANTE, h)
        self.cliente.patch(f"/api/usuarios/{uid}", headers=h,
                           json={"perfiles": {"ESTUDIANTE": {"matricula_vigente": False}}})
        r = self.prestar(h)
        self.assertEqual(r.status_code, 422)
        self.assertIn("matrícula", r.json["error"])
        # un gestor sin rol prestatario tampoco recibe recursos
        admin = self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": self.usuario_id("admin@escuela.edu", h),
            "item_id": self.item_id("LIB-CLRS")})
        self.assertEqual(admin.status_code, 422)

    def test_no_se_presta_un_item_en_mantenimiento(self):
        h = self.ingresar()
        iid = self.item_id("LIB-CLRS")
        self.cliente.post(f"/api/items/{iid}/estado", headers=h, json={"estado": "EN_MANTENIMIENTO"})
        r = self.prestar(h)
        self.assertEqual(r.status_code, 409)
        self.assertIn("EN_MANTENIMIENTO", r.json["error"])

    def test_un_item_prestado_no_admite_cambio_manual_de_estado(self):
        h = self.ingresar()
        self.prestar(h)
        r = self.cliente.post(f"/api/items/{self.item_id('LIB-CLRS')}/estado", headers=h,
                              json={"estado": "DADO_DE_BAJA"})
        self.assertEqual(r.status_code, 409)

    def test_datos_invalidos(self):
        h = self.ingresar()
        post = lambda cuerpo: self.cliente.post("/api/prestamos", headers=h, json=cuerpo)  # noqa: E731
        self.assertEqual(post({}).status_code, 400)
        self.assertEqual(post({"usuario_id": "1", "item_id": 1}).status_code, 400)
        self.assertEqual(post({"usuario_id": 1, "item_id": 1, "forzar": True}).status_code, 400)
        self.assertEqual(post({"usuario_id": 2 ** 63, "item_id": 1}).status_code, 400)
        self.assertEqual(post({"usuario_id": 999, "item_id": 1}).status_code, 404)
        self.assertEqual(post({"usuario_id": self.usuario_id(ESTUDIANTE, h), "item_id": 999}).status_code, 404)
        self.assertEqual(self.cliente.post("/api/prestamos/999/devolucion", headers=h).status_code, 404)
