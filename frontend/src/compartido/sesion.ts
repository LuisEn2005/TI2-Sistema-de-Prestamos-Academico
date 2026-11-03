// Sesión del usuario y navegación según permisos.
import {
  api, ApiError, EVENTO_SESION_INVALIDADA, guardarToken, olvidarToken, token,
} from './api';
import { ETIQUETA_ESPACIO, type EspacioTrabajo, type UsuarioDTO } from './contratos';
import { el } from './ui';

const CLAVE_ESPACIO = 'prestamos.espacio';
const INICIO_ESPACIO: Record<EspacioTrabajo, string> = {
  PERSONAL: '/prestamos', INVENTARIO: '/admin/inventario', ADMINISTRACION: '/admin/usuarios',
};
let actual: UsuarioDTO | null | undefined;
window.addEventListener(EVENTO_SESION_INVALIDADA, () => { actual = null; });

export async function usuarioActual(): Promise<UsuarioDTO | null> {
  if (actual !== undefined) return actual;
  if (!token()) return (actual = null);
  try {
    actual = await api.get<UsuarioDTO>('/api/auth/yo');
    localStorage.setItem(CLAVE_ESPACIO, actual.espacio_activo);
  } catch (error) {
    if (error instanceof ApiError && error.estado === 401) {
      olvidarToken();
      actual = null;
      return actual;
    }
    throw error;
  }
  return actual;
}

export const tienePermiso = (u: UsuarioDTO | null, permiso: string) =>
  !!u && (u.permisos ?? []).includes(permiso);

export async function iniciarSesion(correo: string, password: string) {
  const r = await api.post<{ token: string; usuario: UsuarioDTO }>('/api/auth/login', {
    correo, password, espacio: localStorage.getItem(CLAVE_ESPACIO) ?? undefined,
  });
  guardarToken(r.token);
  actual = r.usuario;
  localStorage.setItem(CLAVE_ESPACIO, r.usuario.espacio_activo);
  return r.usuario;
}

export async function cambiarEspacio(espacio: EspacioTrabajo) {
  const r = await api.post<{ token: string; usuario: UsuarioDTO }>('/api/auth/espacio', { espacio });
  guardarToken(r.token);
  actual = r.usuario;
  localStorage.setItem(CLAVE_ESPACIO, espacio);
  window.location.href = INICIO_ESPACIO[espacio];
}

export function cerrarSesion() {
  olvidarToken();
  actual = null;
  window.location.href = '/';
}

/** Redirige al acceso si no hay sesión; devuelve null si falta el permiso. */
export async function exigirSesion(permiso?: string): Promise<UsuarioDTO | null> {
  let usuario: UsuarioDTO | null;
  try {
    usuario = await usuarioActual();
  } catch (error) {
    document.querySelector('main')?.replaceChildren(
      el('h1', {}, 'Servidor no disponible'),
      el('p', {}, error instanceof Error ? error.message : 'No se pudo validar la sesión.'),
      el('a', { href: window.location.pathname }, 'Reintentar'),
    );
    return null;
  }
  if (!usuario) {
    const destino = encodeURIComponent(window.location.pathname);
    window.location.href = `/?siguiente=${destino}`;
    return null;
  }
  if (permiso && !tienePermiso(usuario, permiso)) {
    document.querySelector('main')?.replaceChildren(
      el('h1', {}, 'Acceso restringido'),
      el('p', {}, 'Su perfil no incluye permisos para esta sección.'),
      el('a', { href: '/catalogo' }, 'Volver al catálogo'),
    );
    return null;
  }
  return usuario;
}

export async function dibujarNavegacion() {
  const nav = document.querySelector('#navegacion');
  if (!nav) return;

  let usuario: UsuarioDTO | null;
  try {
    usuario = await usuarioActual();
  } catch {
    nav.replaceChildren(el('a', { href: '/catalogo' }, 'Catálogo'));
    const zona = document.querySelector('#zona-sesion');
    zona?.replaceChildren(el('span', { class: 'meta' }, 'Servidor no disponible'));
    return;
  }
  const generales: [string, string][] = [['/catalogo', 'Catálogo']];
  if (usuario?.espacio_activo === 'PERSONAL') {
    generales.push(['/prestamos', 'Mis préstamos'], ['/reservas', 'Mis reservas'],
      ['/sanciones', 'Mis sanciones']);
  }
  if (usuario?.espacio_activo === 'INVENTARIO') {
    generales.push(['/admin/inventario', 'Inventario'], ['/prestamos', 'Préstamos'],
      ['/reservas', 'Reservas'], ['/sanciones', 'Sanciones']);
  }
  if (usuario?.espacio_activo === 'ADMINISTRACION') {
    generales.push(['/admin/usuarios', 'Usuarios'], ['/admin/configuracion', 'Configuración'],
      ['/sanciones', 'Sanciones']);
  }

  const crearEnlaces = (enlaces: [string, string][]) => enlaces.map(([ruta, texto]) => {
      const activo = window.location.pathname.startsWith(ruta);
      const a = el('a', { href: ruta }, texto);
      if (activo) a.setAttribute('aria-current', 'page');
      return a;
    });
  nav.replaceChildren(el('span', { class: 'grupo-navegacion' }, 'Principal'), ...crearEnlaces(generales));

  const zonaEspacio = document.querySelector('#zona-espacio');
  if (zonaEspacio && usuario) {
    if (usuario.espacios_disponibles.length > 1) {
      const selector = el('select', { 'aria-label': 'Espacio de trabajo' });
      selector.replaceChildren(...usuario.espacios_disponibles.map((espacio) =>
        el('option', { value: espacio }, ETIQUETA_ESPACIO[espacio])));
      selector.value = usuario.espacio_activo;
      selector.addEventListener('change', () => {
        selector.disabled = true;
        void cambiarEspacio(selector.value as EspacioTrabajo).catch(() => { selector.disabled = false; });
      });
      zonaEspacio.replaceChildren(el('label', { for: 'selector-espacio' }, 'Espacio de trabajo'), selector);
      selector.id = 'selector-espacio';
    } else {
      zonaEspacio.replaceChildren(
        el('span', { class: 'etiqueta-espacio' }, ETIQUETA_ESPACIO[usuario.espacio_activo]));
    }
  }

  const zona = document.querySelector('#zona-sesion');
  if (!zona) return;
  if (usuario) {
    const salir = el('button', { type: 'button', class: 'enlace' }, 'Cerrar sesión');
    salir.addEventListener('click', cerrarSesion);
    zona.replaceChildren(el('a', { href: '/cuenta' }, usuario.nombre), salir);
  } else {
    zona.replaceChildren(el('a', { href: '/' }, 'Iniciar sesión'));
  }

  const marca = document.querySelector<HTMLAnchorElement>('#marca');
  if (marca) marca.href = usuario ? '/prestamos' : '/';
}

void dibujarNavegacion();
