import { api } from '../compartido/api';
import {
  ETIQUETA_ESTADO, type Estado, type FechaSistemaDTO, type ItemDTO,
  type ItemInventarioDTO, type PaginaInventarioDTO, type TipoDTO,
} from '../compartido/contratos';
import { exigirSesion } from '../compartido/sesion';
import { $, avisar, el, mensajeDe, opciones, retardo } from '../compartido/ui';

const LIMITE = 15;
const MANUALES: Estado[] = ['DISPONIBLE', 'EN_MANTENIMIENTO', 'EXTRAVIADO', 'DADO_DE_BAJA'];
let pagina = 1;
let tipos: TipoDTO[] = [];
let editando: ItemDTO | null = null;
let ultimaCarga = 0;

const dialogo = $<HTMLDialogElement>('#dialogo');
const campoTipo = $<HTMLSelectElement>('#f-tipo');

function dibujarAtributos(tipo: string, valores: Record<string, string> = {}) {
  const definicion = tipos.find((t) => t.tipo === tipo);
  $('#f-atributos').replaceChildren(
    ...(definicion?.campos ?? []).map((campo) => {
      const entrada = el('input', { id: `a-${campo.clave}`, 'data-clave': campo.clave, maxlength: '120' });
      if (campo.obligatorio) entrada.required = true;
      entrada.value = valores[campo.clave] ?? '';
      return el('div', {}, el('label', { for: `a-${campo.clave}` }, campo.etiqueta), entrada);
    }),
  );
}

function abrirFormulario(item: ItemDTO | null) {
  editando = item;
  $('#titulo-dialogo').textContent = item ? `Editar ${item.codigo}` : 'Nuevo recurso';
  $('#f-error').textContent = '';
  campoTipo.value = item?.tipo ?? tipos[0].tipo;
  campoTipo.disabled = item !== null; // el tipo no cambia una vez registrado
  $<HTMLInputElement>('#f-codigo').value = item?.codigo ?? '';
  $<HTMLInputElement>('#f-categoria').value = item?.categoria ?? '';
  $<HTMLInputElement>('#f-nombre').value = item?.nombre ?? '';
  dibujarAtributos(campoTipo.value, item?.atributos);
  dialogo.showModal();
}

const ETIQUETA_FECHA = {
  DISPONIBLE: 'Disponible', RESERVADO: 'Reservado', PRESTADO: 'Prestado',
  NO_DISPONIBLE: 'No disponible',
};

function itemFisico(item: ItemInventarioDTO): ItemDTO {
  return { ...item, estado: item.estado_fisico,
    disponible: item.estado_fisico === 'DISPONIBLE' };
}

function filaDe(item: ItemInventarioDTO) {
  const fisico = itemFisico(item);
  const editar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Editar');
  editar.addEventListener('click', () => abrirFormulario(fisico));

  const bloqueado = item.estado_fisico === 'PRESTADO';
  const selector = el('select', { 'aria-label': `Estado de ${item.codigo}` });
  opciones(selector, (bloqueado ? [item.estado_fisico] : MANUALES)
    .map((e) => [e, ETIQUETA_ESTADO[e]]));
  selector.value = item.estado_fisico;
  selector.disabled = bloqueado || item.estado_fisico === 'DADO_DE_BAJA';
  selector.title = bloqueado ? 'Registre la devolución antes de cambiar el estado.' : '';
  selector.addEventListener('change', async () => {
    try {
      await api.post(`/api/items/${item.id}/estado`, { estado: selector.value });
      avisar(`${item.codigo}: ahora está ${ETIQUETA_ESTADO[selector.value as Estado].toLowerCase()}.`);
    } catch (error) {
      avisar(mensajeDe(error), true);
    }
    await cargar();
  });

  const asignacion = item.asignacion
    ? `${item.asignacion.usuario} · ${item.asignacion.fecha_inicio} al ${item.asignacion.fecha_fin}`
    : '—';
  const pendientes = item.solicitudes_pendientes
    ? el('a', { href: '/reservas' }, `${item.solicitudes_pendientes} pendiente${item.solicitudes_pendientes === 1 ? '' : 's'}`)
    : el('span', {}, '0');
  return el('tr', {},
    el('td', {}, el('span', { class: 'codigo' }, item.codigo)),
    el('td', {}, item.nombre),
    el('td', {}, tipos.find((t) => t.tipo === item.tipo)?.etiqueta ?? item.tipo),
    el('td', {}, ETIQUETA_FECHA[item.estado_fecha]),
    el('td', {}, asignacion),
    el('td', {}, pendientes),
    el('td', {}, selector),
    el('td', {}, el('div', { class: 'acciones' }, editar)));
}

async function cargar() {
  const carga = ++ultimaCarga;
  try {
    const datos = await api.get<PaginaInventarioDTO>('/api/inventario', {
      q: $<HTMLInputElement>('#q').value.trim(), tipo: $<HTMLSelectElement>('#tipo').value,
      estado: $<HTMLSelectElement>('#estado').value,
      fecha: $<HTMLInputElement>('#fecha').value, pagina, limite: LIMITE,
    });
    // Una respuesta anterior no debe reemplazar resultados de filtros más recientes.
    if (carga !== ultimaCarga) return;
    const cuerpo = $('#filas');
    cuerpo.replaceChildren(...datos.items.map(filaDe));
    if (datos.items.length === 0) {
      cuerpo.append(el('tr', {}, el('td', { colspan: '8', class: 'vacio' }, 'No hay recursos con estos filtros.')));
    }
    const paginas = Math.max(1, Math.ceil(datos.total / datos.limite));
    $('#pagina').textContent = `Página ${datos.pagina} de ${paginas} · ${datos.total} recursos`;
    $<HTMLButtonElement>('#anterior').disabled = datos.pagina <= 1;
    $<HTMLButtonElement>('#siguiente').disabled = datos.pagina >= paginas;
  } catch (error) {
    if (carga !== ultimaCarga) return;
    avisar(mensajeDe(error), true);
  }
}

const usuario = await exigirSesion('REGISTRAR_ITEM_INVENTARIO');
if (usuario) {
  try {
    tipos = await api.get<TipoDTO[]>('/api/items/tipos');
    if (tipos.length === 0) throw new Error('No hay tipos de recursos configurados.');
  } catch (error) {
    avisar(mensajeDe(error), true);
    $<HTMLButtonElement>('#nuevo').disabled = true;
  }
  if (tipos.length > 0) {
    opciones(campoTipo, tipos.map((t) => [t.tipo, t.etiqueta]));
    opciones($('#tipo'), tipos.map((t) => [t.tipo, t.etiqueta]), 'Todos');
    opciones($('#estado'), Object.entries(ETIQUETA_FECHA), 'Cualquiera');
    const fechas = await api.get<FechaSistemaDTO>('/api/calendario/hoy');
    $<HTMLInputElement>('#fecha').value = fechas.fecha;

    const reiniciar = () => { pagina = 1; cargar(); };
    $('#q').addEventListener('input', retardo(reiniciar));
    $('#tipo').addEventListener('change', reiniciar);
    $('#estado').addEventListener('change', reiniciar);
    $('#fecha').addEventListener('change', reiniciar);
    $('#anterior').addEventListener('click', () => { pagina -= 1; cargar(); });
    $('#siguiente').addEventListener('click', () => { pagina += 1; cargar(); });
    $('#nuevo').addEventListener('click', () => abrirFormulario(null));
    $('#cancelar').addEventListener('click', () => dialogo.close());
    campoTipo.addEventListener('change', () => dibujarAtributos(campoTipo.value));

    $('#formulario').addEventListener('submit', async (evento) => {
      evento.preventDefault();
      const atributos: Record<string, string> = {};
      document.querySelectorAll<HTMLInputElement>('#f-atributos input').forEach((i) => {
        atributos[i.dataset.clave!] = i.value;
      });
      const cuerpo = {
        codigo: $<HTMLInputElement>('#f-codigo').value, nombre: $<HTMLInputElement>('#f-nombre').value,
        categoria: $<HTMLInputElement>('#f-categoria').value, atributos,
      };
      try {
        if (editando) await api.patch(`/api/items/${editando.id}`, cuerpo);
        else await api.post('/api/items', { ...cuerpo, tipo: campoTipo.value });
        dialogo.close();
        avisar(editando ? 'Recurso actualizado.' : 'Recurso registrado.');
        await cargar();
      } catch (error) {
        $('#f-error').textContent = mensajeDe(error);
      }
    });
    cargar();
  }
}
