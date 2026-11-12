import { api, descargar } from '../compartido/api';
import {
  ETIQUETA_RESERVA, ETIQUETA_TIPO_MOVIMIENTO,
  type EstadoReserva, type MovimientoHistorialDTO, type PaginaHistorialDTO,
  type PaginaItemsDTO, type TipoMovimiento,
} from '../compartido/contratos';
import { exigirSesion, tienePermiso } from '../compartido/sesion';
import { $, avisar, el, mensajeDe, opciones, soloFecha } from '../compartido/ui';

const LIMITE = 20;
const usuario = await exigirSesion();
const global = tienePermiso(usuario, 'CONSULTAR_HISTORIAL_GLOBAL');
let pagina = 1;
let listaItems: { id: number; nombre: string; codigo: string }[] = [];
let listaUsuarios: { id: number; nombre: string }[] = [];

const ESTADOS_PRESTAMO: [string, string][] = [
  ['activo', 'Activo'], ['vencido', 'Vencido'], ['devuelto', 'Devuelto']];
const ESTADOS_SANCION: [string, string][] = [['ACTIVA', 'Activa'], ['CERRADA', 'Cerrada']];
const ESTADOS_RESERVA = Object.entries(ETIQUETA_RESERVA) as [string, string][];
const ETIQUETA_PRESTAMO_SANCION: Record<string, string> = {
  activo: 'Activo', vencido: 'Vencido', devuelto: 'Devuelto',
  ACTIVA: 'Activa', CERRADA: 'Cerrada',
};

function etiquetaEstado(tipo: TipoMovimiento, estado: string) {
  if (tipo === 'RESERVA') return ETIQUETA_RESERVA[estado as EstadoReserva] ?? estado;
  return ETIQUETA_PRESTAMO_SANCION[estado] ?? estado;
}

function claseEstado(estado: string) {
  if (['devuelto', 'CERRADA', 'CONFIRMADA', 'CONVERTIDA'].includes(estado)) return 'ok';
  if (['activo', 'PENDIENTE'].includes(estado)) return 'aviso';
  return 'malo';
}

function refrescarEstados() {
  const tipo = $<HTMLSelectElement>('#tipo').value;
  const valores = tipo === 'PRESTAMO' ? ESTADOS_PRESTAMO
    : tipo === 'RESERVA' ? ESTADOS_RESERVA
      : tipo === 'SANCION' ? ESTADOS_SANCION : [];
  const select = $<HTMLSelectElement>('#estado');
  opciones(select, valores, 'Todos');
  select.disabled = valores.length === 0;
}

function filaDe(m: MovimientoHistorialDTO) {
  const clase = claseEstado(m.estado);
  const meta = [global ? m.usuario : null, soloFecha(m.fecha), m.detalle]
    .filter(Boolean).join(' · ');
  return el('li', { class: 'prestamo' },
    el('span', { class: `marcador ${clase}` }),
    el('div', {},
      el('h3', {}, ETIQUETA_TIPO_MOVIMIENTO[m.tipo], m.item ? ` · ${m.item}` : '', ' ',
        m.codigo ? el('span', { class: 'codigo' }, m.codigo) : null),
      el('div', { class: 'meta' }, meta)),
    el('div', {}, el('div', { class: `estado ${clase}` }, etiquetaEstado(m.tipo, m.estado))));
}

async function cargar() {
  const filtros: Record<string, string | number | undefined> = {
    tipo: $<HTMLSelectElement>('#tipo').value || undefined,
    estado: $<HTMLSelectElement>('#estado').value || undefined,
    item_id: Number($<HTMLSelectElement>('#item').value) || undefined,
    desde: $<HTMLInputElement>('#desde').value || undefined,
    hasta: $<HTMLInputElement>('#hasta').value || undefined,
    pagina, limite: LIMITE,
  };
  if (global) filtros.usuario_id = Number($<HTMLSelectElement>('#usuario').value) || undefined;
  try {
    const r = await api.get<PaginaHistorialDTO>('/api/historial', filtros);
    const lista = $('#lista');
    lista.replaceChildren(...r.movimientos.map(filaDe));
    if (!r.movimientos.length) lista.append(el('li', { class: 'vacio' },
      el('span'), 'No hay movimientos con estos filtros.'));
    const paginas = Math.max(1, Math.ceil(r.total / r.limite));
    $('#pagina').textContent = `Página ${r.pagina} de ${paginas} · ${r.total} movimientos`;
    $<HTMLButtonElement>('#anterior').disabled = r.pagina <= 1;
    $<HTMLButtonElement>('#siguiente').disabled = r.pagina >= paginas;
  } catch (error) { avisar(mensajeDe(error), true); }
}

async function cargarItems() {
  const r = await api.get<PaginaItemsDTO>('/api/items', { limite: 100 });
  listaItems = r.items.map((i) => ({ id: i.id, nombre: i.nombre, codigo: i.codigo }));
  opciones($<HTMLSelectElement>('#item'),
    listaItems.map((i) => [String(i.id), `${i.nombre} (${i.codigo})`]), 'Todos');
}

async function cargarUsuarios() {
  const ruta = tienePermiso(usuario, 'CONSULTAR_PRESTATARIOS')
    ? '/api/usuarios/prestatarios' : '/api/usuarios';
  listaUsuarios = await api.get<{ id: number; nombre: string }[]>(ruta);
  opciones($<HTMLSelectElement>('#usuario'),
    listaUsuarios.map((u) => [String(u.id), u.nombre]), 'Todos');
}

function validarRango(desde: string, hasta: string): string | null {
  if (!desde || !hasta) return 'Indique la fecha inicial y la final.';
  if (hasta < desde) return 'La fecha final no puede ser anterior a la inicial.';
  if ((Date.parse(hasta) - Date.parse(desde)) / 86_400_000 > 90) {
    return 'El rango del reporte no puede superar 90 días.';
  }
  return null;
}

function poblarObjetivo() {
  const ambito = $<HTMLSelectElement>('#rep-ambito').value;
  const valores: [string, string][] = ambito === 'item'
    ? listaItems.map((i) => [String(i.id), `${i.nombre} (${i.codigo})`])
    : listaUsuarios.map((u) => [String(u.id), u.nombre]);
  opciones($<HTMLSelectElement>('#rep-objetivo'), valores, 'Seleccione…');
}

async function descargarReporte() {
  const desde = $<HTMLInputElement>('#rep-desde').value;
  const hasta = $<HTMLInputElement>('#rep-hasta').value;
  const error = validarRango(desde, hasta);
  if (error) { avisar(error, true); return; }
  let ruta: string;
  let nombre: string;
  if (global) {
    const ambito = $<HTMLSelectElement>('#rep-ambito').value === 'item' ? 'item' : 'usuario';
    const objetivo = $<HTMLSelectElement>('#rep-objetivo').value;
    if (!objetivo) { avisar('Elija un usuario o recurso para el reporte.', true); return; }
    ruta = `/api/reportes/${ambito}/${objetivo}?desde=${desde}&hasta=${hasta}`;
    nombre = `reporte-${ambito}-${objetivo}-${desde}-a-${hasta}.pdf`;
  } else {
    ruta = `/api/reportes/usuario/${usuario!.id}?desde=${desde}&hasta=${hasta}`;
    nombre = `mi-reporte-${desde}-a-${hasta}.pdf`;
  }
  const boton = $<HTMLButtonElement>('#rep-descargar');
  boton.disabled = true;
  try {
    await descargar(ruta, nombre);
    avisar('Reporte generado.');
  } catch (e) { avisar(mensajeDe(e), true); }
  finally { boton.disabled = false; }
}

if (usuario) {
  if (global) $('#zona-usuario').hidden = false;
  refrescarEstados();
  $('#tipo').addEventListener('change', () => { refrescarEstados(); pagina = 1; void cargar(); });
  for (const id of ['#estado', '#item', '#usuario']) {
    document.querySelector(id)?.addEventListener('change', () => { pagina = 1; void cargar(); });
  }
  $('#actualizar').addEventListener('click', () => { pagina = 1; void cargar(); });
  $('#anterior').addEventListener('click', () => { pagina -= 1; void cargar(); });
  $('#siguiente').addEventListener('click', () => { pagina += 1; void cargar(); });
  $('#rep-descargar').addEventListener('click', () => void descargarReporte());
  try {
    await Promise.all([cargarItems(), global ? cargarUsuarios() : Promise.resolve()]);
  } catch (error) { avisar(mensajeDe(error), true); }
  if (global) {
    $('#rep-zona-ambito').hidden = false;
    $('#rep-zona-objetivo').hidden = false;
    poblarObjetivo();
    $('#rep-ambito').addEventListener('change', poblarObjetivo);
  }
  void cargar();
}
