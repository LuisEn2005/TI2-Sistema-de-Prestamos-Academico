import { api } from '../compartido/api';
import {
  ETIQUETA_ESTADO, type CalendarioItemDTO, type Estado, type ItemDTO,
  type PaginaItemsDTO, type TipoDTO,
} from '../compartido/contratos';
import { $, avisar, el, mensajeDe, opciones, retardo } from '../compartido/ui';

const LIMITE = 10;
let pagina = 1;
let tipos: TipoDTO[] = [];

const campoQ = $<HTMLInputElement>('#q');
const campoTipo = $<HTMLSelectElement>('#tipo');
const campoCategoria = $<HTMLSelectElement>('#categoria');
const campoEstado = $<HTMLSelectElement>('#estado');
const lista = $<HTMLUListElement>('#resultados');
const dialogo = $<HTMLDialogElement>('#detalle');

export const claseEstado = (e: Estado) =>
  e === 'DISPONIBLE' ? 'ok' : e === 'PRESTADO' || e === 'RESERVADO' ? 'aviso' : 'malo';

function etiquetaAtributo(item: ItemDTO, clave: string) {
  const campo = tipos.find((t) => t.tipo === item.tipo)?.campos.find((c) => c.clave === clave);
  return campo?.etiqueta ?? clave;
}

function resumenAtributos(item: ItemDTO) {
  return Object.values(item.atributos).filter(Boolean).slice(0, 2).join(' · ');
}

function mesActual() {
  const ahora = new Date();
  return `${ahora.getFullYear()}-${String(ahora.getMonth() + 1).padStart(2, '0')}`;
}

async function cargarDisponibilidad(item: ItemDTO, mes: string, zona: HTMLElement) {
  const [anio, numeroMes] = mes.split('-').map(Number);
  const ultimo = new Date(anio, numeroMes, 0).getDate();
  const desde = `${mes}-01`;
  const hasta = `${mes}-${ultimo}`;
  const datos = await api.get<CalendarioItemDTO>(`/api/items/${item.id}/calendario`, {
    desde, hasta,
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

function abrirDetalle(item: ItemDTO) {
  const tipo = tipos.find((t) => t.tipo === item.tipo)?.etiqueta ?? item.tipo;
  const filas: [string, string][] = [
    ['Código', item.codigo], ['Tipo', tipo], ['Categoría', item.categoria],
    ['Estado', ETIQUETA_ESTADO[item.estado]],
    ...Object.entries(item.atributos).map(([k, v]): [string, string] => [etiquetaAtributo(item, k), v]),
  ];
  const cerrar = el('button', { type: 'button', class: 'secundario' }, 'Cerrar');
  cerrar.addEventListener('click', () => dialogo.close());
  const mes = el('input', { type: 'month', value: mesActual(), 'aria-label': 'Mes de disponibilidad' });
  const consultar = el('button', { type: 'button', class: 'secundario' }, 'Ver disponibilidad');
  const calendario = el('div', { class: 'calendario', 'aria-label': 'Disponibilidad del recurso' });
  consultar.addEventListener('click', async () => {
    try { await cargarDisponibilidad(item, mes.value, calendario); }
    catch (error) { avisar(mensajeDe(error), true); }
  });
  $('#detalle-contenido').replaceChildren(
    el('h2', {}, item.nombre),
    el('dl', {}, ...filas.flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, v)])),
    el('h3', {}, 'Calendario de disponibilidad'),
    el('div', { class: 'barra' }, el('div', {}, el('label', {}, 'Mes', mes)), consultar),
    el('div', { class: 'leyenda-calendario pequeno' },
      el('span', { class: 'cal-disponible' }, 'Disponible'),
      el('span', { class: 'cal-reservado' }, 'Reservado'),
      el('span', { class: 'cal-no-disponible' }, 'No disponible')),
    calendario,
    el('div', { class: 'pie' }, el('a', { href: '/login?siguiente=/prestamos' }, 'Consultar mis préstamos'), cerrar),
  );
  dialogo.showModal();
}

function dibujar(datos: PaginaItemsDTO) {
  lista.replaceChildren();
  $('#resumen').textContent = datos.total === 1 ? '1 recurso' : `${datos.total} recursos`;
  if (datos.items.length === 0) {
    lista.append(el('li', { class: 'vacio' }, el('span'), 'Ningún recurso coincide con la búsqueda. Pruebe con otros términos o quite filtros.'));
  }
  for (const item of datos.items) {
    const abrir = el('button', { type: 'button' }, item.nombre);
    abrir.addEventListener('click', () => abrirDetalle(item));
    const clase = claseEstado(item.estado);
    lista.append(
      el('li', {},
        el('span', { class: `marcador ${clase === 'malo' ? '' : clase}` }),
        el('div', {},
          el('h3', {}, abrir),
          el('div', { class: 'meta' },
            el('span', { class: 'codigo' }, item.codigo),
            ` · ${tipos.find((t) => t.tipo === item.tipo)?.etiqueta ?? item.tipo} · ${item.categoria}`,
            resumenAtributos(item) ? ` · ${resumenAtributos(item)}` : '')),
        el('span', { class: `estado ${clase}` }, ETIQUETA_ESTADO[item.estado])),
    );
  }
  const paginas = Math.max(1, Math.ceil(datos.total / datos.limite));
  $('#pagina').textContent = `Página ${datos.pagina} de ${paginas}`;
  $<HTMLButtonElement>('#anterior').disabled = datos.pagina <= 1;
  $<HTMLButtonElement>('#siguiente').disabled = datos.pagina >= paginas;
}

async function buscar() {
  try {
    avisar('');
    dibujar(await api.get<PaginaItemsDTO>('/api/items', {
      q: campoQ.value.trim(), tipo: campoTipo.value, categoria: campoCategoria.value,
      estado: campoEstado.value, pagina, limite: LIMITE,
    }));
  } catch (error) {
    avisar(mensajeDe(error), true);
  }
}

async function iniciar() {
  try {
    const [t, categorias] = await Promise.all([
      api.get<TipoDTO[]>('/api/items/tipos'), api.get<string[]>('/api/items/categorias'),
    ]);
    tipos = t;
    opciones(campoTipo, t.map((x) => [x.tipo, x.etiqueta]), 'Todos');
    opciones(campoCategoria, categorias.map((c) => [c, c]), 'Todas');
    opciones(campoEstado, Object.entries(ETIQUETA_ESTADO), 'Cualquiera');
  } catch (error) {
    avisar(mensajeDe(error), true);
  }
  await buscar();
}

const reiniciar = () => { pagina = 1; buscar(); };
campoQ.addEventListener('input', retardo(reiniciar));
for (const campo of [campoTipo, campoCategoria, campoEstado]) campo.addEventListener('change', reiniciar);
$('#filtros').addEventListener('submit', (e) => { e.preventDefault(); reiniciar(); });
$('#anterior').addEventListener('click', () => { pagina -= 1; buscar(); });
$('#siguiente').addEventListener('click', () => { pagina += 1; buscar(); });
iniciar();
