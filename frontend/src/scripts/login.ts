import { iniciarSesion } from './sesion';
import { $, avisar, mensajeDe } from './ui';

function destino() {
  const siguiente = new URLSearchParams(window.location.search).get('siguiente') ?? '/';
  // Solo rutas internas: evita redirecciones abiertas.
  return siguiente.startsWith('/') && !siguiente.startsWith('//') ? siguiente : '/';
}

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
