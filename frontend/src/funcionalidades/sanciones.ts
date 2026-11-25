import { api } from '../compartido/api';
import type { RecursoSancionableDTO, SancionDTO, UsuarioDTO } from '../compartido/contratos';
import { exigirSesion, tienePermiso } from '../compartido/sesion';
import { $, avisar, el, mensajeDe, opciones, soloFecha } from '../compartido/ui';

let puedeCerrar = false;

const origen = (valor: SancionDTO['origen']) => ({
  RETRASO: 'Retraso', DANO: 'Daño', PERDIDA: 'Pérdida',
})[valor];

function fila(s: SancionDTO) {
  const acciones = el('div', { class: 'acciones' });
  if (s.estado === 'ACTIVA') {
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
  const detalle = [s.recurso, s.motivo, s.monto ? `${s.moneda} ${s.monto}` : null, s.resolucion]
    .filter(Boolean).join(' · ');
  return el('tr', {},
    el('td', {}, s.usuario), el('td', {}, origen(s.origen)),
    el('td', {}, detalle), el('td', {}, vigencia),
    el('td', {}, el('span', { class: `estado ${s.estado === 'ACTIVA' ? 'malo' : 'ok'}` },
      s.estado === 'ACTIVA' ? 'Activa' : 'Cerrada')),
    ...(puedeCerrar ? [el('td', {}, acciones)] : []));
}

const CONDICION = { DANADO: 'Dañado', PERDIDO: 'Perdido' } as const;
let recursos: RecursoSancionableDTO[] = [];

async function cargarRecursos() {
  const usuario = $<HTMLSelectElement>('#usuario').value;
  recursos = usuario
    ? await api.get<RecursoSancionableDTO[]>('/api/sanciones/recursos', { usuario_id: usuario })
    : [];
  opciones($<HTMLSelectElement>('#recurso'), recursos.map((r, i) => [String(i),
    `${r.codigo} · ${r.nombre} · ${CONDICION[r.condicion]} · préstamo #${r.prestamo_id}`]),
  recursos.length ? 'Elija el recurso' : 'Este usuario no tiene recursos devueltos dañados o perdidos');
  $<HTMLButtonElement>('#formulario button[type="submit"]').disabled = !recursos.length;
  elegirRecurso();
}

/** El origen (daño o pérdida) lo fija la condición con que volvió el recurso: no se pregunta. */
function elegirRecurso() {
  const recurso = recursos[Number($<HTMLSelectElement>('#recurso').value || NaN)];
  const resumen = $('#resumen-recurso');
  resumen.hidden = !recurso;
  if (!recurso) return undefined;
  const fecha = recurso.fecha_devolucion ? ` el ${soloFecha(recurso.fecha_devolucion)}` : '';
  resumen.textContent = `Sanción por ${recurso.origen === 'DANO' ? 'daño' : 'pérdida'}: `
    + `se devolvió ${CONDICION[recurso.condicion].toLowerCase()}${fecha} (préstamo #${recurso.prestamo_id}).`;
  const motivo = $<HTMLInputElement>('#motivo');
  if (!motivo.value.trim() && recurso.observacion) motivo.value = recurso.observacion;
  return recurso;
}

async function cargar() {
  try {
    const sanciones = await api.get<SancionDTO[]>('/api/sanciones', {
      estado: $<HTMLSelectElement>('#estado').value,
    });
    const filas = $('#filas');
    filas.replaceChildren(...sanciones.map(fila));
    if (!sanciones.length) filas.append(el('tr', {},
      el('td', { colspan: puedeCerrar ? '6' : '5', class: 'vacio' }, 'No hay sanciones con este estado.')));
  } catch (error) { avisar(mensajeDe(error), true); }
}

const sesion = await exigirSesion();
if (sesion) {
  const puedeRegistrar = tienePermiso(sesion, 'GENERAR_SANCION_MANUAL');
  puedeCerrar = tienePermiso(sesion, 'LEVANTAR_SANCION');
  $('#col-acciones').hidden = !puedeCerrar;
  if (puedeRegistrar) {
    $('#registro').hidden = false;
    try {
      const usuarios = await api.get<UsuarioDTO[]>('/api/usuarios/prestatarios');
      opciones($<HTMLSelectElement>('#usuario'),
        usuarios.map((u) => [String(u.id), `${u.nombre} (${u.correo})`]));
      await cargarRecursos();
    } catch (error) { avisar(mensajeDe(error), true); }
    $('#usuario').addEventListener('change', () => {
      cargarRecursos().catch((error) => avisar(mensajeDe(error), true));
    });
    $('#recurso').addEventListener('change', elegirRecurso);
    $('#formulario').addEventListener('submit', async (evento) => {
      evento.preventDefault();
      const dias = $<HTMLInputElement>('#dias').value;
      const monto = $<HTMLInputElement>('#monto').value;
      if (!dias && !monto) return avisar('Indique una duración o un monto.', true);
      const recurso = elegirRecurso();
      if (!recurso) return avisar('Elija el recurso dañado o perdido.', true);
      try {
        await api.post('/api/sanciones', {
          usuario_id: Number($<HTMLSelectElement>('#usuario').value),
          prestamo_id: recurso.prestamo_id,
          item_id: recurso.item_id,
          motivo: $<HTMLInputElement>('#motivo').value,
          dias: dias ? Number(dias) : undefined,
          monto: monto || undefined,
        });
        const usuario = $<HTMLSelectElement>('#usuario').value;
        $<HTMLFormElement>('#formulario').reset();
        $<HTMLSelectElement>('#usuario').value = usuario;
        avisar('Sanción registrada.');
        await Promise.all([cargar(), cargarRecursos()]);
      } catch (error) { avisar(mensajeDe(error), true); }
    });
  }
  $('#estado').addEventListener('change', cargar);
  cargar();
}
