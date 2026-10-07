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

test('el administrador registra usuario, recurso, entrega y devolución', async ({ page }) => {
  await ingresar(page);

  await page.goto('/admin/usuarios');
  await page.getByRole('button', { name: 'Nuevo usuario' }).click();
  await page.getByLabel('Nombre completo').fill('María Prueba');
  await page.getByLabel('Correo').fill('maria.prueba@escuela.edu');
  await page.getByLabel(/Estudiante$/).check();
  await page.getByLabel('Código de estudiante').fill('EST-E2E-001');
  await page.getByRole('button', { name: 'Guardar usuario' }).click();
  await expect(page.getByRole('cell', { name: /María Prueba/ })).toBeVisible();

  await page.goto('/admin/inventario');
  await page.getByRole('button', { name: 'Nuevo recurso' }).click();
  await page.getByLabel('Tipo de recurso').selectOption('LIBRO');
  await page.getByLabel('Código').fill('lib-e2e');
  await page.getByLabel('Categoría').fill('Pruebas');
  await page.getByLabel('Nombre', { exact: true }).fill('Libro de navegador');
  await page.getByLabel('ISBN').fill('978-0000000003');
  await page.getByLabel('Autor').fill('Autora E2E');
  await page.getByLabel('Editorial').fill('Editorial E2E');
  await page.getByRole('button', { name: 'Guardar recurso' }).click();
  await expect(page.getByRole('cell', { name: 'LIB-E2E' })).toBeVisible();

  await page.goto('/prestamos');
  await page.getByLabel('Usuario habilitado').selectOption({
    label: 'María Prueba (maria.prueba@escuela.edu)',
  });
  await page.getByLabel('Recurso disponible').selectOption({
    label: 'Libro de navegador (LIB-E2E)',
  });
  await page.getByRole('button', { name: 'Registrar entrega' }).click();
  const prestamo = page.getByRole('listitem').filter({ hasText: 'Libro de navegador' });
  await expect(prestamo).toContainText('María Prueba');
  await prestamo.getByRole('button', { name: 'Registrar devolución' }).click();
  await expect(prestamo).toHaveCount(0);
  await expect(page.getByText('No hay préstamos activos.')).toBeVisible();
});

test('el gestor opera inventario y no accede a la administración de usuarios', async ({ page }) => {
  await ingresar(page, 'luis.ramos@escuela.edu');
  await expect(page.getByRole('navigation', { name: 'Principal' })).toContainText('Inventario');
  await expect(page.getByRole('navigation', { name: 'Principal' })).not.toContainText('Usuarios');
  await page.goto('/admin/usuarios');
  await expect(page.getByRole('heading', { name: 'Acceso restringido' })).toBeVisible();
});
