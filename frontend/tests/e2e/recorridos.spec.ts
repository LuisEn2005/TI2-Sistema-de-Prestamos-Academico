import { expect, test, type Page } from '@playwright/test';

const CLAVE = 'demo1234';

async function ingresar(page: Page, correo = 'admin@escuela.edu') {
  await page.goto('/login');
  await page.getByLabel('Correo').fill(correo);
  await page.getByLabel('Contraseña').fill(CLAVE);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL('/');
}

test('el catálogo público permite buscar y consultar un recurso', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Buscar').fill('clean code');
  await expect(page.getByRole('button', {
    name: 'Clean Code: A Handbook of Agile Software Craftsmanship',
  })).toBeVisible();
  await page.getByRole('button', {
    name: 'Clean Code: A Handbook of Agile Software Craftsmanship',
  }).click();
  await expect(page.getByRole('dialog')).toContainText('Robert C. Martin');
  await expect(page.getByRole('dialog')).toContainText('LIB-CLEAN');
});

test('el login descarta destinos externos escritos con barras invertidas', async ({ page }) => {
  await page.goto('/login?siguiente=%2F%5Cevil.example');
  await page.getByLabel('Correo').fill('admin@escuela.edu');
  await page.getByLabel('Contraseña').fill(CLAVE);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL('http://127.0.0.1:44321/');
});

test('el administrador registra usuario, recurso, entrega y devolución', async ({ page }, testInfo) => {
  // Cada reintento usa datos distintos porque Playwright conserva el mismo servidor
  // y la misma base durante todo el job.
  const marca = `${testInfo.repeatEachIndex}-${testInfo.retry}`;
  const nombreUsuario = `María Prueba ${marca}`;
  const correoUsuario = `maria.prueba.${marca}@escuela.edu`;
  const codigoItem = `LIB-E2E-${marca}`;
  const nombreItem = `Libro de navegador ${marca}`;

  await ingresar(page);

  await page.goto('/admin/usuarios');
  await page.getByRole('button', { name: 'Nuevo usuario' }).click();
  await page.getByLabel('Nombre completo').fill(nombreUsuario);
  await page.getByLabel('Correo').fill(correoUsuario);
  await page.getByLabel(/Estudiante$/).check();
  await page.getByLabel('Código de estudiante').fill(`EST-E2E-${marca}`);
  await page.getByRole('button', { name: 'Guardar usuario' }).click();
  await expect(page.locator('#mensaje')).toContainText('Usuario registrado.');
  await expect(page.getByRole('cell', { name: new RegExp(nombreUsuario) })).toBeVisible();

  await page.goto('/admin/inventario');
  await page.getByRole('button', { name: 'Nuevo recurso' }).click();
  await page.getByLabel('Tipo de recurso').selectOption('LIBRO');
  await page.getByLabel('Código').fill(codigoItem.toLowerCase());
  await page.getByLabel('Categoría').fill('Pruebas');
  await page.getByLabel('Nombre', { exact: true }).fill(nombreItem);
  await page.getByLabel('ISBN').fill('978-0000000003');
  await page.getByLabel('Autor').fill('Autora E2E');
  await page.getByLabel('Editorial').fill('Editorial E2E');
  await page.getByRole('button', { name: 'Guardar recurso' }).click();
  await expect(page.locator('#mensaje')).toContainText('Recurso registrado.');
  const respuestaBusqueda = page.waitForResponse((respuesta) => {
    const url = new URL(respuesta.url());
    return url.pathname === '/api/items' && url.searchParams.get('q') === codigoItem
      && respuesta.ok();
  });
  await page.getByLabel('Buscar').fill(codigoItem);
  await respuestaBusqueda;
  await expect(page.getByRole('cell', { name: codigoItem })).toBeVisible();

  await page.goto('/prestamos');
  await page.getByLabel('Usuario habilitado').selectOption({
    label: `${nombreUsuario} (${correoUsuario})`,
  });
  await page.getByLabel('Recurso disponible').selectOption({
    label: `${nombreItem} (${codigoItem})`,
  });
  await page.getByRole('button', { name: 'Agregar' }).click();
  await expect(page.getByRole('list', { name: 'Recursos seleccionados' })).toContainText(codigoItem);
  await page.getByRole('button', { name: 'Registrar entrega' }).click();
  const prestamo = page.locator('#lista > li.prestamo').filter({ hasText: nombreItem });
  await expect(prestamo).toContainText(nombreUsuario);
  await expect(prestamo).toContainText('límite');
  await prestamo.getByRole('button', { name: 'Registrar devolución' }).click();
  await page.getByRole('button', { name: 'Confirmar devolución' }).click();
  await expect(prestamo).toHaveCount(0);
  await expect(page.getByText('No hay préstamos activos.')).toBeVisible();
});

test('el gestor entrega varios recursos y devuelve cada uno con su condición', async ({ page }) => {
  await ingresar(page, 'luis.ramos@escuela.edu');
  await page.goto('/prestamos');
  await page.getByLabel('Usuario habilitado').selectOption({
    label: 'Jesus Perez (jesus.perez@escuela.edu)',
  });
  await page.getByLabel('Modalidad').selectOption({ index: 1 }); // externa
  await expect(page.getByText('plazo de 7 días')).toBeVisible();   // el menor entre 15 y 7

  for (const etiqueta of ['Meta Quest (EQ-META)', 'Introduction to Algorithms (CLRS) (LIB-CLRS)']) {
    await page.getByLabel('Recurso disponible').selectOption({ label: etiqueta });
    await page.getByRole('button', { name: 'Agregar' }).click();
  }
  await page.getByRole('button', { name: 'Registrar entrega' }).click();
  await expect(page.locator('#mensaje')).toContainText('Entrega registrada. Fecha límite:');

  const prestamo = page.locator('#lista > li.prestamo').filter({ hasText: 'Meta Quest' });
  await expect(prestamo).toContainText('Introduction to Algorithms');
  await prestamo.getByRole('button', { name: 'Registrar devolución' }).click();
  await page.getByLabel('Condición de EQ-META').selectOption('DANADO');
  await page.getByLabel('Observación de EQ-META').fill('Lente rayado');
  await page.getByRole('button', { name: 'Confirmar devolución' }).click();
  await expect(page.locator('#mensaje')).toContainText('En mantenimiento: EQ-META');

  await page.getByLabel('Mostrar').selectOption('devuelto');
  const devuelto = page.locator('#lista > li.prestamo').filter({ hasText: 'Lente rayado' });
  await expect(devuelto).toContainText('Dañado');
  await expect(devuelto).toContainText('Buen estado');
});

test('el gestor opera inventario y no accede a la administración de usuarios', async ({ page }) => {
  await ingresar(page, 'luis.ramos@escuela.edu');
  await expect(page.getByRole('navigation', { name: 'Principal' })).toContainText('Inventario');
  await expect(page.getByRole('navigation', { name: 'Principal' })).not.toContainText('Usuarios');
  await page.goto('/admin/usuarios');
  await expect(page.getByRole('heading', { name: 'Acceso restringido' })).toBeVisible();
});
