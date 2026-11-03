// Sesión del usuario y navegación según permisos.
import {
  api, ApiError, EVENTO_SESION_INVALIDADA, guardarToken, olvidarToken, token,
} from './api';
import type { UsuarioDTO } from './contratos';
import { el } from './ui';

let actual: UsuarioDTO | null | undefined;
window.addEventListener(EVENTO_SESION_INVALIDADA, () => { actual = null; });

export async function usuarioActual(): Promise<UsuarioDTO | null> {
  if (actual !== undefined) return actual;
  if (!token()) return (actual = null);
  try {
    actual = await api.get<UsuarioDTO>('/api/auth/yo');
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
  const r = await api.post<{ token: string; usuario: UsuarioDTO }>('/api/auth/login', { correo, password });
  guardarToken(r.token);
  actual = r.usuario;
  return r.usuario;
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
  const gestion: [string, string][] = [];
  if (usuario) generales.push(['/prestamos', 'Préstamos']);
  if (usuario) generales.push(['/sanciones', 'Sanciones']);
  if (tienePermiso(usuario, 'RESERVAR_ITEM') || tienePermiso(usuario, 'CONFIRMAR_RESERVA')) {
    generales.push(['/reservas', 'Reservas']);
  }
  if (tienePermiso(usuario, 'REGISTRAR_ITEM_INVENTARIO')) gestion.push(['/admin/inventario', 'Inventario']);
  if (tienePermiso(usuario, 'GESTIONAR_USUARIOS_Y_ROLES')) gestion.push(['/admin/usuarios', 'Usuarios']);
  if (tienePermiso(usuario, 'CONFIGURAR_POLITICAS')) gestion.push(['/admin/configuracion', 'Configuración']);

  const crearEnlaces = (enlaces: [string, string][]) => enlaces.map(([ruta, texto]) => {
      const activo = window.location.pathname.startsWith(ruta);
      const a = el('a', { href: ruta }, texto);
      if (activo) a.setAttribute('aria-current', 'page');
      return a;
    });
  nav.replaceChildren(el('span', { class: 'grupo-navegacion' }, 'Principal'), ...crearEnlaces(generales));
  if (gestion.length) nav.append(el('span', { class: 'grupo-navegacion' }, 'Gestión'), ...crearEnlaces(gestion));

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
