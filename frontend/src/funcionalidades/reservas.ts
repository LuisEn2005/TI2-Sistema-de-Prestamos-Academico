import { api } from '../compartido/api';
import {
  ETIQUETA_RESERVA, ETIQUETA_ROL, type ItemDTO, type ModalidadDTO,
  type PaginaItemsDTO, type PaginaReservasDTO, type ReservaDTO, type RolPrestatario,
} from '../compartido/contratos';
import { exigirSesion, tienePermiso } from '../compartido/sesion';
import { $, avisar, el, fechaLegible, mensajeDe, opciones, retardo, soloFecha } from '../compartido/ui';

const LIMITE = 15;
const usuario = await exigirSesion();
const gestiona = tienePermiso(usuario, 'CONFIRMAR_RESERVA');
const puedeReservar = tienePermiso(usuario, 'RESERVAR_ITEM');
const roles = (usuario?.roles ?? []).filter((r): r is RolPrestatario =>
  r === 'ESTUDIANTE' || r === 'DOCENTE' || r === 'ADMINISTRATIVO');
const puedeSolicitar = puedeReservar && roles.length > 0;
let pagina = 1;
let items: ItemDTO[] = [];
let modalidades: ModalidadDTO[] = [];

function mananaLocal() {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + 1);
  return [fecha.getFullYear(), String(fecha.getMonth() + 1).padStart(2, '0'),
    String(fecha.getDate()).padStart(2, '0')].join('-');
}

async function cargarItems() {
  const respuesta = await api.get<PaginaItemsDTO>('/api/items', {
    q: $<HTMLInputElement>('#buscar-item').value.trim(), limite: 100,
  });
  items = respuesta.items.filter((i) => i.estado === 'DISPONIBLE' || i.estado === 'PRESTADO');
  opciones($('#item'), items.map((i) => [
    String(i.id), `${i.nombre} (${i.codigo}) · ${i.estado === 'PRESTADO' ? 'prestado' : 'disponible'}`,
  ]));
  $<HTMLButtonElement>('#reservar').disabled = items.length === 0;
}

function accionesDe(reserva: ReservaDTO) {
  const acciones = el('div', { class: 'acciones' });
  const activa = reserva.estado === 'PENDIENTE' || reserva.estado === 'CONFIRMADA';
  if (activa && (gestiona || reserva.usuario_id === usuario?.id)) {
    const cancelar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Cancelar');
    cancelar.addEventListener('click', async () => {
      try {
        await api.post(`/api/reservas/${reserva.id}/cancelacion`);
        avisar('Reserva cancelada; el recurso quedó liberado.');
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
    acciones.append(cancelar);
  }
  if (gestiona && reserva.estado === 'PENDIENTE') {
    const confirmar = el('button', { type: 'button', class: 'pequeno' }, 'Confirmar');
    confirmar.addEventListener('click', async () => {
      try {
        await api.post(`/api/reservas/${reserva.id}/confirmacion`);
        avisar('Reserva confirmada.');
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
    acciones.append(confirmar);
  }
  if (gestiona && reserva.estado === 'CONFIRMADA') {
    const modalidad = el('select', { 'aria-label': `Modalidad para ${reserva.codigo}` });
    opciones(modalidad, modalidades.filter((m) => m.activo)
      .map((m) => [String(m.id), m.nombre]));
    const convertir = el('button', { type: 'button', class: 'pequeno' }, 'Registrar entrega');
    convertir.addEventListener('click', async () => {
      try {
        const prestamo = await api.post<{ fecha_limite: string }>(
          `/api/reservas/${reserva.id}/prestamo`, { modalidad_id: Number(modalidad.value) });
        avisar(`Reserva convertida en préstamo. Fecha límite: ${soloFecha(prestamo.fecha_limite)}.`);
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
    acciones.append(modalidad, convertir);
  }
  return acciones;
}

function filaDe(reserva: ReservaDTO) {
  const clase = reserva.estado === 'CONFIRMADA' || reserva.estado === 'CONVERTIDA'
    ? 'ok' : reserva.estado === 'PENDIENTE' ? 'aviso' : 'malo';
  return el('li', { class: 'prestamo' },
    el('span', { class: `marcador ${clase}` }),
    el('div', {},
      el('h3', {}, reserva.item, ' ', el('span', { class: 'codigo' }, reserva.codigo)),
      el('div', { class: 'meta' },
        `${gestiona ? `${reserva.usuario} · ` : ''}${ETIQUETA_ROL[reserva.rol_solicitante]} · ` +
        `solicitada ${fechaLegible(reserva.fecha_solicitud)} · para ${soloFecha(reserva.fecha_reserva)} · ` +
        `vence ${soloFecha(reserva.fecha_expiracion)}`)),
    el('div', {}, el('div', { class: `estado ${clase}` }, ETIQUETA_RESERVA[reserva.estado]),
      accionesDe(reserva)));
}

async function cargarLista() {
  const respuesta = await api.get<PaginaReservasDTO>('/api/reservas', {
    estado: $<HTMLSelectElement>('#estado').value, pagina, limite: LIMITE,
  });
  const lista = $('#lista');
  lista.replaceChildren(...respuesta.reservas.map(filaDe));
  if (!respuesta.reservas.length) {
    lista.append(el('li', { class: 'vacio' }, el('span'), 'No hay reservas con este estado.'));
  }
  const paginas = Math.max(1, Math.ceil(respuesta.total / respuesta.limite));
  $('#pagina').textContent = `Página ${respuesta.pagina} de ${paginas} · ${respuesta.total} reservas`;
  $<HTMLButtonElement>('#anterior').disabled = respuesta.pagina <= 1;
  $<HTMLButtonElement>('#siguiente').disabled = respuesta.pagina >= paginas;
}

async function cargar() {
  try { await Promise.all([cargarLista(), puedeSolicitar ? cargarItems() : Promise.resolve()]); }
  catch (error) { avisar(mensajeDe(error), true); }
}

if (usuario) {
  modalidades = await api.get<ModalidadDTO[]>('/api/modalidades');
  if (puedeSolicitar) {
    $('#nueva').hidden = false;
    const fecha = $<HTMLInputElement>('#fecha');
    fecha.min = mananaLocal();
    fecha.value = mananaLocal();
    if (roles.length > 1) {
      $('#zona-rol').hidden = false;
      opciones($('#rol'), roles.map((r) => [r, ETIQUETA_ROL[r]]));
    }
    $('#buscar-item').addEventListener('input', retardo(() => void cargarItems()));
    $('#formulario').addEventListener('submit', async (evento) => {
      evento.preventDefault();
      try {
        await api.post('/api/reservas', {
          item_id: Number($<HTMLSelectElement>('#item').value), fecha_reserva: fecha.value,
          rol_solicitante: roles.length > 1 ? $<HTMLSelectElement>('#rol').value : undefined,
        });
        avisar('Reserva solicitada. Consulte aquí su confirmación.');
        pagina = 1;
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
  }
  $('#estado').addEventListener('change', () => { pagina = 1; void cargarLista(); });
  $('#anterior').addEventListener('click', () => { pagina -= 1; void cargarLista(); });
  $('#siguiente').addEventListener('click', () => { pagina += 1; void cargarLista(); });
  void cargar();
}
