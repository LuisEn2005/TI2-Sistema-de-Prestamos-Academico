from .ayudas import ESTUDIANTE, ApiBase

LIBRO = {
    "tipo": "LIBRO", "codigo": "LIB-DDD", "nombre": "Domain-Driven Design",
    "categoria": "Arquitectura",
    "atributos": {"isbn": "978-0321125217", "autor": "Eric Evans", "editorial": "Addison-Wesley"},
}


class CatalogoPublicoTest(ApiBase):
    def test_catalogo_se_consulta_sin_autenticacion(self):
        r = self.cliente.get("/api/items")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["total"], 3)
        self.assertEqual({"id", "codigo", "nombre", "categoria", "tipo", "estado", "disponible",
                          "atributos"}, set(r.json["items"][0]))

    def test_busqueda_por_texto_incluye_atributos(self):
        buscar = lambda q: [i["codigo"] for i in self.cliente.get(f"/api/items?q={q}").json["items"]]  # noqa: E731
        self.assertEqual(buscar("clean"), ["LIB-CLEAN"])
        self.assertEqual(buscar("robert martin"), ["LIB-CLEAN"])
        self.assertEqual(buscar("quest 3"), ["EQ-META"])
        self.assertEqual(buscar("inexistente"), [])

    def test_busqueda_trata_comodines_como_texto(self):
        self.assertEqual(self.cliente.get("/api/items?q=%25").json["total"], 0)
        self.assertEqual(self.cliente.get("/api/items?q=_").json["total"], 0)

    def test_filtros_por_tipo_categoria_y_estado(self):
        self.assertEqual(self.cliente.get("/api/items?tipo=libro").json["total"], 2)
        self.assertEqual(self.cliente.get("/api/items?tipo=EQUIPO&categoria=realidad virtual").json["total"], 1)
        self.assertEqual(self.cliente.get("/api/items?estado=DISPONIBLE").json["total"], 3)
        self.assertEqual(self.cliente.get("/api/items?estado=PRESTADO").json["total"], 0)
        self.assertEqual(self.cliente.get("/api/items?tipo=DRON").status_code, 400)
        self.assertEqual(self.cliente.get("/api/items?estado=ROTO").status_code, 400)

    def test_paginacion(self):
        p1 = self.cliente.get("/api/items?limite=2&pagina=1").json
        p2 = self.cliente.get("/api/items?limite=2&pagina=2").json
        self.assertEqual((len(p1["items"]), len(p2["items"]), p1["total"]), (2, 1, 3))
        self.assertFalse({i["id"] for i in p1["items"]} & {i["id"] for i in p2["items"]})
        self.assertEqual(self.cliente.get("/api/items?limite=abc").status_code, 400)
        self.assertEqual(self.cliente.get("/api/items?limite=100000").status_code, 400)
        self.assertEqual(self.cliente.get("/api/items?pagina=999999999999999999").status_code, 400)
        self.assertEqual(self.cliente.get("/api/items?pagina=0").status_code, 400)
        self.assertEqual(self.cliente.get(f"/api/items?q={'x' * 121}").status_code, 400)
        self.assertEqual(self.cliente.get("/api/items?orden=nombre").status_code, 400)

    def test_detalle_tipos_y_categorias(self):
        self.assertEqual(self.cliente.get("/api/items/999").status_code, 404)
        detalle = self.cliente.get(f"/api/items/{self.item_id('EQ-META')}").json
        self.assertEqual(detalle["atributos"]["marcaModelo"], "Meta Quest 3")
        tipos = self.cliente.get("/api/items/tipos").json
        libro = next(t for t in tipos if t["tipo"] == "LIBRO")
        self.assertIn("isbn", [c["clave"] for c in libro["campos"]])
        self.assertIn("Realidad virtual", self.cliente.get("/api/items/categorias").json)


class AdministracionInventarioTest(ApiBase):
    def test_estudiante_no_puede_modificar_el_inventario(self):
        h = self.ingresar(ESTUDIANTE)
        self.assertEqual(self.cliente.post("/api/items", headers=h, json=LIBRO).status_code, 403)
        iid = self.item_id("EQ-META")
        self.assertEqual(self.cliente.post(f"/api/items/{iid}/estado", headers=h,
                                           json={"estado": "EN_MANTENIMIENTO"}).status_code, 403)
        self.assertEqual(self.cliente.post("/api/items", json=LIBRO).status_code, 401)

    def test_registrar_item_con_atributos_del_tipo(self):
        h = self.ingresar()
        r = self.cliente.post("/api/items", headers=h, json=LIBRO)
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual(r.json["estado"], "DISPONIBLE")
        self.assertEqual(self.cliente.get("/api/items?q=evans").json["total"], 1)

    def test_registrar_material_y_mobiliario_sin_datos_demo_adicionales(self):
        h = self.ingresar()
        ejemplos = (
            {"tipo": "MATERIAL", "codigo": "MAT-001", "nombre": "Cable HDMI",
             "categoria": "Accesorios", "atributos": {
                 "tipoMaterial": "Cable", "unidadMedida": "unidad"}},
            {"tipo": "MOBILIARIO", "codigo": "MOB-001", "nombre": "Silla de laboratorio",
             "categoria": "Aulas", "atributos": {
                 "tipoMobiliario": "Silla", "ubicacionHabitual": "Laboratorio 1"}},
        )
        for ejemplo in ejemplos:
            respuesta = self.cliente.post("/api/items", headers=h, json=ejemplo)
            self.assertEqual(respuesta.status_code, 201, respuesta.json)
            self.assertEqual(respuesta.json["atributos"], ejemplo["atributos"])

    def test_validaciones_de_registro(self):
        h = self.ingresar()
        sin_isbn = dict(LIBRO, atributos={"autor": "X"})
        extra = dict(LIBRO, atributos=dict(LIBRO["atributos"], color="rojo"))
        casos = {
            "falta atributo obligatorio": sin_isbn,
            "atributo ajeno al tipo": extra,
            "tipo inexistente": dict(LIBRO, tipo="DRON"),
            "sin nombre": dict(LIBRO, nombre=""),
            "código muy largo": dict(LIBRO, codigo="X" * 31),
            "atributos no es objeto": dict(LIBRO, atributos=[1]),
        }
        for nombre, cuerpo in casos.items():
            self.assertEqual(self.cliente.post("/api/items", headers=h, json=cuerpo).status_code,
                             400, nombre)

    def test_codigo_duplicado_sin_distinguir_mayusculas(self):
        h = self.ingresar()
        self.assertEqual(self.cliente.post("/api/items", headers=h, json=LIBRO).status_code, 201)
        r = self.cliente.post("/api/items", headers=h, json=dict(LIBRO, codigo="lib-ddd"))
        self.assertEqual(r.status_code, 409)

    def test_codigo_se_guarda_en_formato_canonico(self):
        h = self.ingresar()
        r = self.cliente.post("/api/items", headers=h, json=dict(LIBRO, codigo=" lib-ddd "))
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual(r.json["codigo"], "LIB-DDD")

    def test_el_estado_inicial_no_se_puede_forzar(self):
        h = self.ingresar()
        r = self.cliente.post("/api/items", headers=h, json=dict(LIBRO, estado="PRESTADO"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("estado", r.json["error"])

    def test_rechaza_campos_desconocidos(self):
        h = self.ingresar()
        self.assertEqual(self.cliente.post(
            "/api/items", headers=h, json=dict(LIBRO, nombre_item="otro")).status_code, 400)
        iid = self.item_id("LIB-CLRS")
        self.assertEqual(self.cliente.post(
            f"/api/items/{iid}/estado", headers=h,
            json={"estado": "EN_MANTENIMIENTO", "forzar": True}).status_code, 400)

    def test_actualizar_item(self):
        h = self.ingresar()
        iid = self.item_id("LIB-CLRS")
        r = self.cliente.patch(f"/api/items/{iid}", headers=h, json={
            "nombre": "CLRS 4.ª ed.", "atributos": {"editorial": "MIT"}})
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(r.json["atributos"]["editorial"], "MIT")
        self.assertIn("Cormen", r.json["atributos"]["autor"])
        self.assertEqual(self.cliente.get("/api/items?q=mit").json["total"], 1)
        self.assertEqual(self.cliente.patch(f"/api/items/{iid}", headers=h,
                                            json={"tipo": "EQUIPO"}).status_code, 400)
        self.assertEqual(self.cliente.patch(f"/api/items/{iid}", headers=h,
                                            json={"codigo": "LIB-CLEAN"}).status_code, 409)
        self.assertEqual(self.cliente.patch(f"/api/items/{iid}", headers=h,
                                            json={"atributos": {"autor": ""}}).status_code, 400)
        self.assertEqual(self.cliente.patch("/api/items/999", headers=h, json={}).status_code, 404)

    def test_cambios_de_estado_manuales(self):
        h = self.ingresar()
        iid = self.item_id("EQ-META")
        cambiar = lambda e: self.cliente.post(f"/api/items/{iid}/estado", headers=h, json={"estado": e})  # noqa: E731
        self.assertEqual(cambiar("EN_MANTENIMIENTO").json["estado"], "EN_MANTENIMIENTO")
        self.assertEqual(cambiar("EN_MANTENIMIENTO").status_code, 409)
        self.assertEqual(cambiar("PRESTADO").status_code, 422)
        self.assertEqual(cambiar("RESERVADO").status_code, 422)
        self.assertEqual(cambiar("NO_EXISTE").status_code, 400)
        self.assertEqual(cambiar("DISPONIBLE").json["disponible"], True)
        self.assertEqual(cambiar("DADO_DE_BAJA").status_code, 200)
        self.assertEqual(cambiar("DISPONIBLE").status_code, 409)  # estado terminal

    def test_nuevo_tipo_de_recurso_no_cambia_el_esquema(self):
        """RNF06: basta registrar el tipo; la tabla y la API siguen igual."""
        from dataclasses import dataclass
        from typing import Optional

        from prestamos_academicos.dominio.inventario import Item
        from prestamos_academicos.dominio.inventario import TiposItem as t

        @dataclass
        class Dron(Item):
            modelo: Optional[str] = None
            TIPO = "DRON"

            def atributosEspecificos(self):
                return {"modelo": self.modelo}

        t.registrar_tipo(t.TipoItem("DRON", "Dron", Dron, (t.Campo("modelo", "Modelo", True),)))
        try:
            h = self.ingresar()
            r = self.cliente.post("/api/items", headers=h, json={
                "tipo": "DRON", "codigo": "DR-1", "nombre": "Dron de mapeo",
                "categoria": "Topografía", "atributos": {"modelo": "Mavic 3"}})
            self.assertEqual(r.status_code, 201, r.json)
            self.assertEqual(self.cliente.get("/api/items?tipo=DRON").json["total"], 1)
        finally:
            t._TIPOS.pop("DRON")
