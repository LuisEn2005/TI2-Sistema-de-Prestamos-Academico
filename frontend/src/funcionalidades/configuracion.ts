import { api } from '../compartido/api';
import { ETIQUETA_ROL, type ModalidadDTO, type PoliticaDTO } from '../compartido/contratos';
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
  const cupo = entradaNumero(p.max_items_simultaneos, `Cupo de ${nombre}`, 50);
  const plazo = entradaNumero(p.dias_prestamo, `Días de préstamo de ${nombre}`, 365);
  const sancion = entradaNumero(
    p.dias_sancion_por_dia_atraso, `Sanción por atraso de ${nombre}`, 30);
  const guardar = el('button', { type: 'button', class: 'pequeno' }, 'Guardar');
  guardar.setAttribute('aria-label', `Guardar política de ${nombre}`);
  guardar.addEventListener('click', async () => {
    try {
      await api.patch(`/api/politicas/${p.id}`, {
        max_items_simultaneos: Number(cupo.value), dias_prestamo: Number(plazo.value),
        dias_sancion_por_dia_atraso: Number(sancion.value),
      });
      avisar(`Política de ${nombre} actualizada.`);
    } catch (error) { avisar(mensajeDe(error), true); }
  });
  return el('tr', {}, el('td', {}, ETIQUETA_ROL[p.rol]), el('td', {}, p.modalidad),
    el('td', {}, cupo), el('td', {}, plazo), el('td', {}, sancion), el('td', {}, guardar));
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

const sesion = await exigirSesion('CONFIGURAR_POLITICAS');
if (sesion) {
  try {
    const [politicas, modalidades] = await Promise.all([
      api.get<PoliticaDTO[]>('/api/politicas'), api.get<ModalidadDTO[]>('/api/modalidades'),
    ]);
    $('#politicas').replaceChildren(...politicas.map(filaPolitica));
    $('#modalidades').replaceChildren(...modalidades.map(filaModalidad));
  } catch (error) { avisar(mensajeDe(error), true); }
}
