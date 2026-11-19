import { api } from './api';
import type { CalendarioItemDTO } from './contratos';
import { el } from './ui';

/** Pinta en `zona` el calendario mensual (AAAA-MM) de disponibilidad de un recurso. */
export async function pintarCalendario(itemId: number, mes: string, zona: HTMLElement) {
  const [anio, numeroMes] = mes.split('-').map(Number);
  const ultimo = new Date(anio, numeroMes, 0).getDate();
  const datos = await api.get<CalendarioItemDTO>(`/api/items/${itemId}/calendario`, {
    desde: `${mes}-01`, hasta: `${mes}-${ultimo}`,
  });
  const primerDia = new Date(`${datos.dias[0].fecha}T12:00:00`).getDay();
  const cabeceras = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    .map((dia) => el('div', { class: 'cal-cabecera' }, dia));
  const vacios = Array.from({ length: (primerDia + 6) % 7 }, () =>
    el('div', { class: 'cal-vacio' }));
  const dias = datos.dias.map((dia) => {
    const clase = dia.estado.toLowerCase().replace('_', '-');
    const etiqueta = dia.estado === 'NO_DISPONIBLE' ? 'No disponible'
      : dia.estado === 'RESERVADO' ? 'Reservado' : 'Disponible';
    return el('div', { class: `cal-${clase}`, title: etiqueta },
      el('strong', {}, String(Number(dia.fecha.slice(-2)))),
      el('span', { class: 'pequeno' }, etiqueta));
  });
  zona.replaceChildren(...cabeceras, ...vacios, ...dias);
}

export const leyendaCalendario = () => el('div', { class: 'leyenda-calendario pequeno' },
  el('span', { class: 'cal-disponible' }, 'Disponible'),
  el('span', { class: 'cal-reservado' }, 'Reservado'),
  el('span', { class: 'cal-no-disponible' }, 'No disponible'));
