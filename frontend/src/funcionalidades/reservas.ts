import { api } from '../compartido/api';
import {
  ETIQUETA_RESERVA, ETIQUETA_ROL, type CalendarioItemDTO, type ItemDTO,
  type DetalleReservaDTO, type FechaSistemaDTO, type ModalidadDTO, type PaginaItemsDTO,
  type PaginaReservasDTO, type PoliticaDTO,
  type ReservaDTO, type RolPrestatario, type SolicitudCalendarioDTO,
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
let politicas: PoliticaDTO[] = [];
let hoySistema = '';

function fechaLocal(fecha = new Date()) {
  return [fecha.getFullYear(), String(fecha.getMonth() + 1).padStart(2, '0'),
    String(fecha.getDate()).padStart(2, '0')].join('-');
}

function sumarDias(fecha: string, dias: number) {
  const [a, m, d] = fecha.split('-').map(Number);
  const valor = new Date(a, m - 1, d);
  valor.setDate(valor.getDate() + dias);
  return fechaLocal(valor);
}

function rolElegido() {
  return roles.length > 1 ? $<HTMLSelectElement>('#rol').value : roles[0];
}

function politicaElegida() {
  return politicas.find((p) => p.rol === rolElegido()
    && p.modalidad_id === Number($<HTMLSelectElement>('#modalidad').value));
}

function actualizarRango() {
  if (!puedeSolicitar) return;
  const politica = politicaElegida();
  const inicio = $<HTMLInputElement>('#fecha-inicio');
  const fin = $<HTMLInputElement>('#fecha-fin');
  if (!politica || !inicio.value) return;
  fin.min = inicio.value;
  fin.max = sumarDias(inicio.value, politica.dias_prestamo);
  const inSitu = modalidades.find((m) => m.id === politica.modalidad_id)?.nombre.startsWith('In situ');
  fin.value = inSitu ? inicio.value : fin.max;
  fin.disabled = Boolean(inSitu);
  $('#regla-rango').textContent = inSitu
    ? 'La modalidad in situ termina al final del mismo día laborable.'
    : `Puede elegir entre 1 y ${politica.dias_prestamo} días calendario.`;
}

async function cargarItems() {
  const respuesta = await api.get<PaginaItemsDTO>('/api/items', {
    q: $<HTMLInputElement>('#buscar-item').value.trim(), limite: 100,
  });
  items = respuesta.items.filter((i) => i.estado === 'DISPONIBLE' || i.estado === 'PRESTADO');
  const valores = items.map((i) => [String(i.id), `${i.nombre} (${i.codigo})`] as [string, string]);
  opciones($<HTMLSelectElement>('#item'), valores);
  opciones($<HTMLSelectElement>('#cal-item'), valores);
  $<HTMLButtonElement>('#reservar').disabled = items.length === 0;
  if (items.length) void cargarCalendario();
}

async function confirmar(id: number, fechaFin?: string) {
  await api.post(`/api/reservas/${id}/confirmacion`, fechaFin ? { fecha_fin: fechaFin } : {});
  avisar('Reserva confirmada; las solicitudes incompatibles fueron rechazadas.');
  await cargar();
}

async function rechazar(id: number) {
  const motivo = window.prompt('Motivo del rechazo:', 'Se asignó el recurso a otra solicitud.');
  if (!motivo?.trim()) return;
  await api.post(`/api/reservas/${id}/rechazo`, { motivo });
  avisar('Solicitud rechazada.');
  await cargar();
}

function accionesDe(reserva: ReservaDTO) {
  const acciones = el('div', { class: 'acciones' });
  if (reserva.estado === 'PENDIENTE' && reserva.usuario_id === usuario?.id) {
    const retirar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Retirar solicitud');
    retirar.addEventListener('click', async () => {
      const motivo = window.prompt('Motivo del retiro (opcional):', '') ?? '';
      try {
        await api.post(`/api/reservas/${reserva.id}/retiro`, { motivo });
        avisar('Solicitud retirada.');
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
    acciones.append(retirar);
  }
  if (reserva.estado === 'CONFIRMADA' && (gestiona || reserva.usuario_id === usuario?.id)) {
    const cancelar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Cancelar');
    cancelar.addEventListener('click', async () => {
      const motivo = window.prompt(
        gestiona ? 'Motivo obligatorio de la cancelación:' : 'Motivo de la cancelación (opcional):',
        '') ?? '';
      if (gestiona && !motivo.trim()) return;
      try {
        await api.post(`/api/reservas/${reserva.id}/cancelacion`, { motivo });
        avisar('Reserva cancelada.');
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
    acciones.append(cancelar);
  }
  if (gestiona && reserva.estado === 'PENDIENTE') {
    const confirmarBoton = el('button', { type: 'button', class: 'pequeno' }, 'Confirmar');
    confirmarBoton.addEventListener('click', () => confirmar(reserva.id).catch(
      (error) => avisar(mensajeDe(error), true)));
    const rechazarBoton = el('button', { type: 'button', class: 'pequeno secundario' }, 'Rechazar');
    rechazarBoton.addEventListener('click', () => rechazar(reserva.id).catch(
      (error) => avisar(mensajeDe(error), true)));
    acciones.append(confirmarBoton, rechazarBoton);
  }
  if (gestiona && reserva.estado === 'CONFIRMADA') {
    const fin = el('input', {
      type: 'date', value: reserva.fecha_fin, min: reserva.fecha_inicio,
      max: reserva.fecha_fin, 'aria-label': `Fecha final para ${reserva.codigo}`,
    });
    const convertir = el('button', { type: 'button', class: 'pequeno' }, 'Entregar y crear préstamo');
    convertir.disabled = hoySistema !== reserva.fecha_inicio;
    if (convertir.disabled) convertir.title = `Disponible para entregar el ${soloFecha(reserva.fecha_inicio)}.`;
    convertir.addEventListener('click', async () => {
      try {
        const prestamo = await api.post<{ fecha_limite: string }>(
          `/api/reservas/${reserva.id}/prestamo`, {
            modalidad_id: reserva.modalidad_id ?? undefined, fecha_fin: fin.value,
          });
        avisar(`Reserva convertida en préstamo. Fecha límite: ${soloFecha(prestamo.fecha_limite)}.`);
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
    acciones.append(fin, convertir);
  }
  const historial = el('button', { type: 'button', class: 'pequeno secundario' }, 'Ver historial');
  historial.addEventListener('click', async () => {
    try {
      const detalle = await api.get<DetalleReservaDTO>(`/api/reservas/${reserva.id}`);
      const lineas = detalle.eventos.map((evento) => {
        const rango = evento.fecha_inicio_nueva
          ? ` · ${soloFecha(evento.fecha_inicio_nueva)} al ${soloFecha(evento.fecha_fin_nueva)}` : '';
        return `${fechaLegible(evento.creado_en)} · ${evento.tipo} · ${evento.actor}${rango}`
          + (evento.motivo ? ` · ${evento.motivo}` : '');
      });
      if (detalle.prestamo_id) lineas.push(`Préstamo resultante: #${detalle.prestamo_id}`);
      window.alert(lineas.join('\n') || 'No hay eventos registrados.');
    } catch (error) { avisar(mensajeDe(error), true); }
  });
  acciones.append(historial);
  return acciones;
}

function filaDe(reserva: ReservaDTO) {
  const clase = reserva.estado === 'CONFIRMADA' || reserva.estado === 'CONVERTIDA'
    ? 'ok' : reserva.estado === 'PENDIENTE' ? 'aviso' : 'malo';
  const detalle = [
    gestiona ? reserva.usuario : null,
    ETIQUETA_ROL[reserva.rol_solicitante], reserva.modalidad,
    `${soloFecha(reserva.fecha_inicio)} al ${soloFecha(reserva.fecha_fin)}`,
    `solicitada ${fechaLegible(reserva.fecha_solicitud)}`,
    reserva.motivo_resolucion,
  ].filter(Boolean).join(' · ');
  return el('li', { class: 'prestamo' },
    el('span', { class: `marcador ${clase}` }),
    el('div', {}, el('h3', {}, reserva.item, ' ',
      el('span', { class: 'codigo' }, reserva.codigo)),
    el('div', { class: 'meta' }, detalle)),
    el('div', {}, el('div', { class: `estado ${clase}` }, ETIQUETA_RESERVA[reserva.estado]),
      accionesDe(reserva)));
}

async function cargarLista() {
  const filtro = $<HTMLSelectElement>('#estado').value;
  const respuesta = await api.get<PaginaReservasDTO>('/api/reservas', {
    estado: filtro === 'HISTORIAL' ? undefined : filtro,
    historial: filtro === 'HISTORIAL' ? 1 : undefined,
    pagina, limite: LIMITE,
  });
  const lista = $('#lista');
  lista.replaceChildren(...respuesta.reservas.map(filaDe));
  if (!respuesta.reservas.length) lista.append(el('li', { class: 'vacio' },
    el('span'), 'No hay reservas con este estado.'));
  const paginas = Math.max(1, Math.ceil(respuesta.total / respuesta.limite));
  $('#pagina').textContent = `Página ${respuesta.pagina} de ${paginas} · ${respuesta.total} reservas`;
  $<HTMLButtonElement>('#anterior').disabled = respuesta.pagina <= 1;
  $<HTMLButtonElement>('#siguiente').disabled = respuesta.pagina >= paginas;
}

function limitesMes() {
  const [a, m] = $<HTMLInputElement>('#cal-mes').value.split('-').map(Number);
  const inicio = `${a}-${String(m).padStart(2, '0')}-01`;
  const ultimo = new Date(a, m, 0).getDate();
  return { inicio, fin: `${a}-${String(m).padStart(2, '0')}-${ultimo}` };
}

function dibujarCalendario(datos: CalendarioItemDTO) {
  const zona = $('#calendario');
  const cabeceras = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    .map((dia) => el('div', { class: 'cal-cabecera' }, dia));
  const primerDia = new Date(`${datos.dias[0].fecha}T12:00:00`).getDay();
  const blancos = Array.from({ length: (primerDia + 6) % 7 }, () =>
    el('div', { class: 'cal-vacio' }));
  const dias = datos.dias.map((dia) => {
    const clase = dia.estado.toLowerCase().replace('_', '-');
    const etiqueta = dia.estado === 'NO_DISPONIBLE' ? 'No disponible'
      : dia.estado === 'RESERVADO' ? 'Reservado' : 'Disponible';
    return el('div', { class: `cal-${clase}`, title: etiqueta },
      el('strong', {}, String(Number(dia.fecha.slice(-2)))),
      el('span', { class: 'pequeno' }, etiqueta));
  });
  zona.replaceChildren(...cabeceras, ...blancos, ...dias);
}

function dibujarSolicitudes(solicitudes: SolicitudCalendarioDTO[]) {
  const zona = $('#solicitudes');
  if (!solicitudes.length) {
    zona.replaceChildren(el('p', { class: 'vacio' }, 'No hay solicitudes pendientes en este mes.'));
    return;
  }
  const tabla = el('table', {},
    el('thead', {}, el('tr', {}, ...['Usuario', 'Perfil', 'Rango', 'Registrada', 'Acciones']
      .map((texto) => el('th', {}, texto)))),
    el('tbody', {}, ...solicitudes.map((s) => {
      const aceptar = el('button', { type: 'button', class: 'pequeno' }, 'Confirmar');
      aceptar.addEventListener('click', () => confirmar(s.id).catch(
        (error) => avisar(mensajeDe(error), true)));
      const negar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Rechazar');
      negar.addEventListener('click', () => rechazar(s.id).catch(
        (error) => avisar(mensajeDe(error), true)));
      return el('tr', {}, el('td', {}, s.usuario), el('td', {}, ETIQUETA_ROL[s.rol_solicitante]),
        el('td', {}, `${soloFecha(s.fecha_inicio)} al ${soloFecha(s.fecha_fin)}`),
        el('td', {}, fechaLegible(s.fecha_solicitud)),
        el('td', {}, el('div', { class: 'acciones' }, aceptar, negar)));
    })));
  zona.replaceChildren(tabla);
}

async function cargarCalendario() {
  const itemId = Number($<HTMLSelectElement>('#cal-item').value);
  if (!itemId || !$<HTMLInputElement>('#cal-mes').value) return;
  const { inicio, fin } = limitesMes();
  const datos = await api.get<CalendarioItemDTO>(`/api/items/${itemId}/calendario`, {
    desde: inicio, hasta: fin,
  });
  dibujarCalendario(datos);
  if (gestiona) {
    const solicitudes = await api.get<SolicitudCalendarioDTO[]>('/api/reservas/calendario', {
      item_id: itemId, desde: inicio, hasta: fin,
    });
    dibujarSolicitudes(solicitudes);
  }
}

async function cargar() {
  try { await Promise.all([cargarLista(), puedeSolicitar ? cargarItems() : cargarCalendario()]); }
  catch (error) { avisar(mensajeDe(error), true); }
}

if (usuario) {
  const [modalidadesRespuesta, politicasRespuesta, fechaSistema] = await Promise.all([
    api.get<ModalidadDTO[]>('/api/modalidades'), api.get<PoliticaDTO[]>('/api/politicas'),
    api.get<FechaSistemaDTO>('/api/calendario/hoy'),
  ]);
  modalidades = modalidadesRespuesta.filter((m) => m.activo);
  politicas = politicasRespuesta;
  const hoy = fechaSistema.fecha;
  hoySistema = hoy;
  $<HTMLInputElement>('#cal-mes').value = hoy.slice(0, 7);
  $('#solicitudes-calendario').hidden = !gestiona;
  if (puedeSolicitar) {
    $('#nueva').hidden = false;
    opciones($<HTMLSelectElement>('#modalidad'), modalidades.map((m) => [String(m.id), m.nombre]));
    const inicio = $<HTMLInputElement>('#fecha-inicio');
    inicio.min = fechaSistema.siguiente_laborable;
    inicio.max = sumarDias(hoy, 90);
    inicio.value = fechaSistema.siguiente_laborable;
    if (roles.length > 1) {
      $('#zona-rol').hidden = false;
      opciones($<HTMLSelectElement>('#rol'), roles.map((r) => [r, ETIQUETA_ROL[r]]));
    }
    $('#buscar-item').addEventListener('input', retardo(() => void cargarItems()));
    $('#modalidad').addEventListener('change', actualizarRango);
    $('#rol').addEventListener('change', actualizarRango);
    inicio.addEventListener('change', actualizarRango);
    $('#formulario').addEventListener('submit', async (evento) => {
      evento.preventDefault();
      try {
        await api.post('/api/reservas', {
          item_id: Number($<HTMLSelectElement>('#item').value),
          modalidad_id: Number($<HTMLSelectElement>('#modalidad').value),
          fecha_inicio: inicio.value, fecha_fin: $<HTMLInputElement>('#fecha-fin').value,
          rol_solicitante: roles.length > 1 ? $<HTMLSelectElement>('#rol').value : undefined,
        });
        avisar('Solicitud registrada. El gestor elegirá manualmente entre las solicitudes.');
        pagina = 1;
        await cargar();
      } catch (error) { avisar(mensajeDe(error), true); }
    });
  }
  $('#estado').addEventListener('change', () => { pagina = 1; void cargarLista(); });
  $('#anterior').addEventListener('click', () => { pagina -= 1; void cargarLista(); });
  $('#siguiente').addEventListener('click', () => { pagina += 1; void cargarLista(); });
  $('#actualizar-calendario').addEventListener('click', () => void cargarCalendario());
  $('#cal-item').addEventListener('change', () => void cargarCalendario());
  $('#cal-mes').addEventListener('change', () => void cargarCalendario());
  await cargarItems();
  actualizarRango();
  void cargarLista();
}
