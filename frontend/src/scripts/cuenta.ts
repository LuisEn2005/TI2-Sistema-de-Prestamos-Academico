import { api } from './api';
import { ETIQUETA_ROL, type PoliticaDTO } from './contratos';
import { exigirSesion } from './sesion';
import { $, avisar, el, mensajeDe } from './ui';

const usuario = await exigirSesion();
if (usuario) {
  $('#datos').replaceChildren(
    el('p', {}, el('strong', {}, usuario.nombre), ` · ${usuario.correo}`),
    el('p', {}, ...usuario.roles.map((r) => el('span', { class: 'etiqueta-rol' }, ETIQUETA_ROL[r]))),
    usuario.habilitado
      ? el('p', { class: 'tenue' }, 'Su cuenta está habilitada para solicitar préstamos.')
      : el('p', { class: 'tenue' }, usuario.motivo_no_habilitado ?? ''),
  );

  try {
    const propias = (await api.get<PoliticaDTO[]>('/api/politicas')).filter((p) => usuario.roles.includes(p.rol));
    $('#politicas').replaceChildren(
      propias.length === 0
        ? el('p', { class: 'vacio' }, 'Su perfil no tiene una política de préstamo.')
        : el('table', {},
            el('thead', {}, el('tr', {}, ...['Perfil', 'Ítems simultáneos', 'Días de préstamo', 'Recursos permitidos'].map((t) => el('th', {}, t)))),
            el('tbody', {}, ...propias.map((p) => el('tr', {},
              el('td', {}, ETIQUETA_ROL[p.rol]), el('td', {}, String(p.max_items_simultaneos)),
              el('td', {}, String(p.dias_prestamo_default)), el('td', {}, p.tipos_recurso_permitidos.join(', ').toLowerCase()))))));
  } catch (error) {
    avisar(mensajeDe(error), true);
  }

  $('#formulario').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/auth/cambiar-password', {
        password_actual: $<HTMLInputElement>('#actual').value,
        password_nueva: $<HTMLInputElement>('#nueva').value,
      });
      ($('#formulario') as HTMLFormElement).reset();
      avisar('Contraseña actualizada.');
    } catch (error) {
      avisar(mensajeDe(error), true);
    }
  });
}
