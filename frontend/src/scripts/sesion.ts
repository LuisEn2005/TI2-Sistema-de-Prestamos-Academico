// Sesión del usuario y navegación según permisos.
import { api, ApiError, guardarToken, olvidarToken, token } from './api';
import type { UsuarioDTO } from './contratos';
import { el } from './ui';

let actual: UsuarioDTO | null | undefined;

export async function usuarioActual(): Promise<UsuarioDTO | null> {
  if (actual !== undefined) return actual;
  if (!token()) return (actual = null);
  try {
    actual = await api.get<UsuarioDTO>('/api/auth/yo');
  } catch (error) {
    if (error instanceof ApiError && error.estado === 401) olvidarToken();
    actual = null;
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

/** Redirige a /login si no hay sesión; devuelve null si falta el permiso. */
export async function exigirSesion(permiso?: string): Promise<UsuarioDTO | null> {
  const usuario = await usuarioActual();
  if (!usuario) {
    const destino = encodeURIComponent(window.location.pathname);
    window.location.href = `/login?siguiente=${destino}`;
    return null;
  }
  if (permiso && !tienePermiso(usuario, permiso)) {
    document.querySelector('main')?.replaceChildren(
      el('h1', {}, 'Acceso restringido'),
      el('p', {}, 'Su perfil no incluye permisos para esta sección.'),
      el('a', { href: '/' }, 'Volver al catálogo'),
    );
    return null;
  }
  return usuario;
}

export async function dibujarNavegacion() {
  const nav = document.querySelector('#navegacion');
  if (!nav) return;
  const usuario = await usuarioActual();
  const enlaces: [string, string][] = [['/', 'Catálogo']];
  if (usuario) enlaces.push(['/prestamos', 'Préstamos']);
  if (tienePermiso(usuario, 'REGISTRAR_ITEM_INVENTARIO')) enlaces.push(['/admin/inventario', 'Inventario']);
  if (tienePermiso(usuario, 'GESTIONAR_USUARIOS_Y_ROLES')) enlaces.push(['/admin/usuarios', 'Usuarios']);

  nav.replaceChildren(
    ...enlaces.map(([ruta, texto]) => {
      const activo = ruta === '/' ? window.location.pathname === '/' : window.location.pathname.startsWith(ruta);
      const a = el('a', { href: ruta }, texto);
      if (activo) a.setAttribute('aria-current', 'page');
      return a;
    }),
  );

  const zona = document.querySelector('#zona-sesion');
  if (!zona) return;
  if (usuario) {
    const salir = el('button', { type: 'button', class: 'enlace' }, 'Cerrar sesión');
    salir.addEventListener('click', cerrarSesion);
    zona.replaceChildren(el('a', { href: '/cuenta' }, usuario.nombre), salir);
  } else {
    zona.replaceChildren(el('a', { href: '/login' }, 'Iniciar sesión'));
  }
}

dibujarNavegacion();
