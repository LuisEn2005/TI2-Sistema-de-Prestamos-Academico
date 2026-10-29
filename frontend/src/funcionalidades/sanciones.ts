import { api } from '../compartido/api';
import type { SancionDTO, UsuarioDTO } from '../compartido/contratos';
import { exigirSesion, tienePermiso } from '../compartido/sesion';
import { $, avisar, el, mensajeDe, opciones, soloFecha } from '../compartido/ui';

let puedeCerrar = false;

const origen = (valor: SancionDTO['origen']) => ({
  RETRASO: 'Retraso', DANO: 'Daño', PERDIDA: 'Pérdida',
})[valor];

function fila(s: SancionDTO) {
  const acciones = el('div', { class: 'acciones' });
  if (puedeCerrar && s.estado === 'ACTIVA') {
    const cerrar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Cerrar');
    cerrar.addEventListener('click', async () => {
      const resolucion = window.prompt('Indique cómo se resolvió la sanción:');
      if (!resolucion?.trim()) return;
      try {
        await api.post(`/api/sanciones/${s.id}/cierre`, { resolucion });
        avisar('Sanción cerrada.');
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
    acciones.append(cerrar);
  }
  const vigencia = s.fecha_fin
    ? `${soloFecha(s.fecha_inicio)} al ${soloFecha(s.fecha_fin)}`
    : `Desde ${soloFecha(s.fecha_inicio)} hasta su resolución`;
  const detalle = [s.motivo, s.monto ? `${s.moneda} ${s.monto}` : null, s.resolucion]
    .filter(Boolean).join(' · ');
  return el('tr', {},
    el('td', {}, s.usuario), el('td', {}, origen(s.origen)),
    el('td', {}, detalle), el('td', {}, vigencia),
    el('td', {}, el('span', { class: `estado ${s.estado === 'ACTIVA' ? 'malo' : 'ok'}` },
      s.estado === 'ACTIVA' ? 'Activa' : 'Cerrada')),
    el('td', {}, acciones));
}

async function cargar() {
  try {
    const sanciones = await api.get<SancionDTO[]>('/api/sanciones', {
      estado: $<HTMLSelectElement>('#estado').value,
    });
    const filas = $('#filas');
    filas.replaceChildren(...sanciones.map(fila));
    if (!sanciones.length) filas.append(el('tr', {},
      el('td', { colspan: '6', class: 'vacio' }, 'No hay sanciones con este estado.')));
  } catch (error) { avisar(mensajeDe(error), true); }
}

const sesion = await exigirSesion();
if (sesion) {
  const puedeRegistrar = tienePermiso(sesion, 'GENERAR_SANCION_MANUAL');
  puedeCerrar = tienePermiso(sesion, 'LEVANTAR_SANCION');
  if (puedeRegistrar) {
    $('#registro').hidden = false;
    try {
      const usuarios = await api.get<UsuarioDTO[]>('/api/usuarios/prestatarios');
      opciones($<HTMLSelectElement>('#usuario'),
        usuarios.map((u) => [String(u.id), `${u.nombre} (${u.correo})`]));
    } catch (error) { avisar(mensajeDe(error), true); }
    $('#formulario').addEventListener('submit', async (evento) => {
      evento.preventDefault();
      const dias = $<HTMLInputElement>('#dias').value;
      const monto = $<HTMLInputElement>('#monto').value;
      if (!dias && !monto) return avisar('Indique una duración o un monto.', true);
      try {
        await api.post('/api/sanciones', {
          usuario_id: Number($<HTMLSelectElement>('#usuario').value),
          origen: $<HTMLSelectElement>('#origen').value,
          motivo: $<HTMLInputElement>('#motivo').value,
          dias: dias ? Number(dias) : undefined,
          monto: monto || undefined,
        });
        $<HTMLFormElement>('#formulario').reset();
        avisar('Sanción registrada.');
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
  }
  $('#estado').addEventListener('change', cargar);
  cargar();
}
