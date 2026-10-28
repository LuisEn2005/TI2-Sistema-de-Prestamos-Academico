-- Políticas iniciales del servicio de préstamos.
-- Compatible con SQLite y PostgreSQL sobre el esquema de la migración 0012.
-- El script es idempotente: puede ejecutarse más de una vez.

BEGIN;

INSERT INTO tipos_recurso (codigo, nombre)
SELECT 'LIBRO', 'Libro'
WHERE NOT EXISTS (SELECT 1 FROM tipos_recurso WHERE codigo = 'LIBRO');
INSERT INTO tipos_recurso (codigo, nombre)
SELECT 'EQUIPO', 'Equipo'
WHERE NOT EXISTS (SELECT 1 FROM tipos_recurso WHERE codigo = 'EQUIPO');
INSERT INTO tipos_recurso (codigo, nombre)
SELECT 'MATERIAL', 'Material'
WHERE NOT EXISTS (SELECT 1 FROM tipos_recurso WHERE codigo = 'MATERIAL');
INSERT INTO tipos_recurso (codigo, nombre)
SELECT 'MOBILIARIO', 'Mobiliario'
WHERE NOT EXISTS (SELECT 1 FROM tipos_recurso WHERE codigo = 'MOBILIARIO');

INSERT INTO modalidades (nombre, activo)
SELECT 'In situ (en sala)', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM modalidades WHERE nombre = 'In situ (en sala)'
);
INSERT INTO modalidades (nombre, activo)
SELECT 'Externa (a domicilio)', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM modalidades WHERE nombre = 'Externa (a domicilio)'
);

-- Estudiante: 1 día en sala y 7 días fuera; hasta 3 recursos.
INSERT INTO politicas_servicio
    (rol_aplicable, modalidad_id, max_items_simultaneos, dias_prestamo)
SELECT 'ESTUDIANTE', m.id, 3,
       CASE WHEN m.nombre = 'In situ (en sala)' THEN 1 ELSE 7 END
FROM modalidades AS m
WHERE m.nombre IN ('In situ (en sala)', 'Externa (a domicilio)')
  AND NOT EXISTS (
      SELECT 1
      FROM politicas_servicio AS p
      WHERE p.rol_aplicable = 'ESTUDIANTE' AND p.modalidad_id = m.id
  );

-- Docente y administrativo: 1 día en sala y 15 días fuera; hasta 5 recursos.
INSERT INTO politicas_servicio
    (rol_aplicable, modalidad_id, max_items_simultaneos, dias_prestamo)
SELECT roles.rol, m.id, 5,
       CASE WHEN m.nombre = 'In situ (en sala)' THEN 1 ELSE 15 END
FROM modalidades AS m
CROSS JOIN (
    SELECT 'DOCENTE' AS rol
    UNION ALL
    SELECT 'ADMINISTRATIVO' AS rol
) AS roles
WHERE m.nombre IN ('In situ (en sala)', 'Externa (a domicilio)')
  AND NOT EXISTS (
      SELECT 1
      FROM politicas_servicio AS p
      WHERE p.rol_aplicable = roles.rol AND p.modalidad_id = m.id
  );

-- Los estudiantes acceden a libros, equipos y materiales.
INSERT INTO politica_tipos_recurso
    (politica_servicio_id, tipo_recurso_codigo)
SELECT p.id, t.codigo
FROM politicas_servicio AS p
CROSS JOIN tipos_recurso AS t
WHERE p.rol_aplicable = 'ESTUDIANTE'
  AND t.codigo IN ('LIBRO', 'EQUIPO', 'MATERIAL')
  AND NOT EXISTS (
      SELECT 1
      FROM politica_tipos_recurso AS ptr
      WHERE ptr.politica_servicio_id = p.id
        AND ptr.tipo_recurso_codigo = t.codigo
  );

-- Docentes y administrativos acceden también a mobiliario.
INSERT INTO politica_tipos_recurso
    (politica_servicio_id, tipo_recurso_codigo)
SELECT p.id, t.codigo
FROM politicas_servicio AS p
CROSS JOIN tipos_recurso AS t
WHERE p.rol_aplicable IN ('DOCENTE', 'ADMINISTRATIVO')
  AND t.codigo IN ('LIBRO', 'EQUIPO', 'MATERIAL', 'MOBILIARIO')
  AND NOT EXISTS (
      SELECT 1
      FROM politica_tipos_recurso AS ptr
      WHERE ptr.politica_servicio_id = p.id
        AND ptr.tipo_recurso_codigo = t.codigo
  );

COMMIT;
