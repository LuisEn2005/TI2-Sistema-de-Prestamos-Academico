import { api } from '../compartido/api';
import {
  ETIQUETA_ROL, type DiaNoLaborableDTO, type FechaSistemaDTO,
  type ModalidadDTO, type PoliticaDTO, type PoliticaRolDTO,
} from '../compartido/contratos';
import { exigirSesion } from '../compartido/sesion';
import { $, avisar, el, mensajeDe } from '../compartido/ui';

function entradaNumero(valor: number, etiqueta: string, maximo: number) {
  return el('input', {
    type: 'number', min: '1', max: String(maximo), value: String(valor),
    'aria-label': etiqueta,
  });
}

function filaPolitica(p: PoliticaDTO) {
  const nombre = `${ETIQUETA_ROL[p.rol]} · ${p.modalidad}`;
  const plazo = entradaNumero(p.dias_prestamo, `Días de préstamo de ${nombre}`, 365);
  const guardar = el('button', { type: 'button', class: 'pequeno' }, 'Guardar');
  const inSitu = p.modalidad.startsWith('In situ');
  plazo.disabled = inSitu;
  guardar.disabled = inSitu;
  if (inSitu) guardar.title = 'El préstamo in situ siempre termina el mismo día.';
  guardar.setAttribute('aria-label', `Guardar política de ${nombre}`);
  guardar.addEventListener('click', async () => {
    try {
      await api.patch(`/api/politicas/${p.id}`, {
        dias_prestamo: Number(plazo.value),
      });
      avisar(`Política de ${nombre} actualizada.`);
    } catch (error) { avisar(mensajeDe(error), true); }
  });
  return el('tr', {}, el('td', {}, ETIQUETA_ROL[p.rol]), el('td', {}, p.modalidad),
    el('td', {}, plazo), el('td', {}, guardar));
}

function filaPoliticaRol(p: PoliticaRolDTO) {
  const nombre = ETIQUETA_ROL[p.rol];
  const cupo = entradaNumero(p.max_items_simultaneos, `Cupo de ${nombre}`, 50);
  const sancion = entradaNumero(
    p.dias_sancion_por_dia_atraso, `Sanción por atraso de ${nombre}`, 30);
  const guardar = el('button', { type: 'button', class: 'pequeno' }, 'Guardar');
  guardar.setAttribute('aria-label', `Guardar reglas de ${nombre}`);
  guardar.addEventListener('click', async () => {
    try {
      await api.patch(`/api/politicas-rol/${p.rol}`, {
        max_items_simultaneos: Number(cupo.value),
        dias_sancion_por_dia_atraso: Number(sancion.value),
      });
      avisar(`Reglas de ${nombre.toLowerCase()} actualizadas.`);
    } catch (error) { avisar(mensajeDe(error), true); }
  });
  return el('tr', {}, el('td', {}, nombre), el('td', {}, cupo),
    el('td', {}, sancion), el('td', {}, guardar));
}

function filaModalidad(m: ModalidadDTO) {
  const activa = el('input', { type: 'checkbox', 'aria-label': `Activar ${m.nombre}` });
  activa.checked = m.activo;
  const guardar = el('button', { type: 'button', class: 'pequeno' }, 'Guardar');
  guardar.setAttribute('aria-label', `Guardar modalidad ${m.nombre}`);
  guardar.addEventListener('click', async () => {
    try {
      await api.patch(`/api/modalidades/${m.id}`, { activo: activa.checked });
      avisar(`Modalidad ${m.nombre} actualizada.`);
    } catch (error) { avisar(mensajeDe(error), true); }
  });
  return el('tr', {}, el('td', {}, m.nombre), el('td', {}, activa), el('td', {}, guardar));
}

const etiquetaCierre = { FERIADO: 'Feriado', HUELGA: 'Huelga', OTRO: 'Otro' };
let cierreEditando: number | null = null;

function limpiarEdicionCierre() {
  cierreEditando = null;
  $<HTMLButtonElement>('#guardar-cierre').textContent = 'Registrar cierre';
  $<HTMLButtonElement>('#cancelar-edicion-cierre').hidden = true;
  $<HTMLInputElement>('#cierre-motivo').value = '';
}

function editarCierre(c: DiaNoLaborableDTO) {
  cierreEditando = c.id;
  $<HTMLInputElement>('#cierre-inicio').value = c.fecha_inicio;
  $<HTMLInputElement>('#cierre-fin').value = c.fecha_fin;
  $<HTMLSelectElement>('#cierre-tipo').value = c.tipo;
  $<HTMLInputElement>('#cierre-motivo').value = c.motivo;
  $<HTMLButtonElement>('#guardar-cierre').textContent = 'Guardar cambios';
  $<HTMLButtonElement>('#cancelar-edicion-cierre').hidden = false;
}

function filaCierre(c: DiaNoLaborableDTO) {
  const editar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Editar');
  editar.addEventListener('click', () => editarCierre(c));
  const alternar = el('button', { type: 'button', class: 'pequeno secundario' },
    c.activo ? 'Desactivar' : 'Activar');
  alternar.addEventListener('click', async () => {
    try {
      await api.patch(`/api/dias-no-laborables/${c.id}`, { activo: !c.activo });
      avisar(`Periodo ${c.activo ? 'desactivado' : 'activado'}.`);
      await cargarCierres();
    } catch (error) { avisar(mensajeDe(error), true); }
  });
  return el('tr', {}, el('td', {}, `${c.fecha_inicio} al ${c.fecha_fin}`),
    el('td', {}, etiquetaCierre[c.tipo]), el('td', {}, c.motivo),
    el('td', {}, c.activo ? 'Activo' : 'Inactivo'),
    el('td', {}, el('div', { class: 'acciones' }, editar, alternar)));
}

async function cargarCierres() {
  const cierres = await api.get<DiaNoLaborableDTO[]>('/api/dias-no-laborables');
  const cuerpo = $('#cierres');
  cuerpo.replaceChildren(...cierres.map(filaCierre));
  if (!cierres.length) cuerpo.append(el('tr', {},
    el('td', { colspan: '5', class: 'vacio' }, 'No hay cierres registrados.')));
}

const sesion = await exigirSesion('CONFIGURAR_POLITICAS');
if (sesion) {
  try {
    const [politicas, reglasRol, modalidades] = await Promise.all([
      api.get<PoliticaDTO[]>('/api/politicas'),
      api.get<PoliticaRolDTO[]>('/api/politicas-rol'),
      api.get<ModalidadDTO[]>('/api/modalidades'),
    ]);
    $('#politicas').replaceChildren(...politicas.map(filaPolitica));
    $('#politicas-rol').replaceChildren(...reglasRol.map(filaPoliticaRol));
    $('#modalidades').replaceChildren(...modalidades.map(filaModalidad));
    await cargarCierres();
  } catch (error) { avisar(mensajeDe(error), true); }
  const hoy = (await api.get<FechaSistemaDTO>('/api/calendario/hoy')).fecha;
  $<HTMLInputElement>('#cierre-inicio').min = hoy;
  $<HTMLInputElement>('#cierre-fin').min = hoy;
  $<HTMLInputElement>('#cierre-inicio').value = hoy;
  $<HTMLInputElement>('#cierre-fin').value = hoy;
  $('#cierre-inicio').addEventListener('change', () => {
    const inicio = $<HTMLInputElement>('#cierre-inicio').value;
    $<HTMLInputElement>('#cierre-fin').min = inicio;
    if ($<HTMLInputElement>('#cierre-fin').value < inicio) {
      $<HTMLInputElement>('#cierre-fin').value = inicio;
    }
  });
  $('#cancelar-edicion-cierre').addEventListener('click', limpiarEdicionCierre);
  $('#formulario-cierre').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    try {
      const datos = {
        fecha_inicio: $<HTMLInputElement>('#cierre-inicio').value,
        fecha_fin: $<HTMLInputElement>('#cierre-fin').value,
        tipo: $<HTMLSelectElement>('#cierre-tipo').value,
        motivo: $<HTMLInputElement>('#cierre-motivo').value,
      };
      if (cierreEditando === null) await api.post('/api/dias-no-laborables', datos);
      else await api.patch(`/api/dias-no-laborables/${cierreEditando}`, datos);
      avisar(cierreEditando === null
        ? 'Periodo no laborable registrado y operaciones reprogramadas.'
        : 'Periodo no laborable actualizado.');
      limpiarEdicionCierre();
      await cargarCierres();
    } catch (error) { avisar(mensajeDe(error), true); }
  });
}
