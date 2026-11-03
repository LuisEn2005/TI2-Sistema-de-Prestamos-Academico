import { iniciarSesion, usuarioActual } from '../compartido/sesion';
import type { UsuarioDTO } from '../compartido/contratos';
import { $, avisar, mensajeDe } from '../compartido/ui';

const INICIO = { PERSONAL: '/prestamos', INVENTARIO: '/admin/inventario', ADMINISTRACION: '/admin/usuarios' };

function destino(usuario: UsuarioDTO) {
  const inicio = INICIO[usuario.espacio_activo];
  const siguiente = new URLSearchParams(window.location.search).get('siguiente') ?? inicio;
  try {
    const url = new URL(siguiente, window.location.origin);
    if (url.origin !== window.location.origin) return inicio;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return inicio;
  }
}

const password = $<HTMLInputElement>('#password');
const mostrar = $<HTMLButtonElement>('#mostrar-password');
mostrar.addEventListener('click', () => {
  const visible = password.type === 'text';
  password.type = visible ? 'password' : 'text';
  mostrar.textContent = visible ? 'Mostrar' : 'Ocultar';
  mostrar.setAttribute('aria-pressed', String(!visible));
  password.focus();
});

$('#formulario').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const boton = $<HTMLButtonElement>('#entrar');
  boton.disabled = true;
  try {
    const usuario = await iniciarSesion(
      $<HTMLInputElement>('#correo').value, $<HTMLInputElement>('#password').value);
    window.location.href = destino(usuario);
  } catch (error) {
    avisar(mensajeDe(error), true);
    boton.disabled = false;
  }
});

void usuarioActual().then((usuario) => {
  if (usuario) window.location.replace(destino(usuario));
}).catch(() => {
  // El formulario permanece disponible si el servidor aún no responde.
});
