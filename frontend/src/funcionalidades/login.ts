import { iniciarSesion, usuarioActual } from '../compartido/sesion';
import { $, avisar, mensajeDe } from '../compartido/ui';

function destino() {
  const siguiente = new URLSearchParams(window.location.search).get('siguiente') ?? '/prestamos';
  try {
    const url = new URL(siguiente, window.location.origin);
    if (url.origin !== window.location.origin) return '/prestamos';
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return '/prestamos';
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
    await iniciarSesion($<HTMLInputElement>('#correo').value, $<HTMLInputElement>('#password').value);
    window.location.href = destino();
  } catch (error) {
    avisar(mensajeDe(error), true);
    boton.disabled = false;
  }
});

void usuarioActual().then((usuario) => {
  if (usuario) window.location.replace(destino());
}).catch(() => {
  // El formulario permanece disponible si el servidor aún no responde.
});
