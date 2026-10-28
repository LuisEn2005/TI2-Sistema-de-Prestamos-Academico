import { api } from '../compartido/api';
import {
  ETIQUETA_CONDICION, ETIQUETA_ROL, type CondicionDevolucion, type CondicionesPrestamoDTO,
  type ItemDTO, type ModalidadDTO, type PaginaItemsDTO, type PaginaPrestamosDTO, type PrestamoDTO,
  type Rol, type RolPrestatario,
} from '../compartido/contratos';
import { exigirSesion, tienePermiso } from '../compartido/sesion';
import { $, avisar, el, fechaLegible, mensajeDe, opciones, retardo, soloFecha } from '../compartido/ui';

const LIMITE = 15;
const usuario = await exigirSesion();
const gestiona = tienePermiso(usuario, 'REGISTRAR_ENTREGA_PRESTAMO');
const puedeRenovar = tienePermiso(usuario, 'RENOVAR_PRESTAMO');
let pagina = 1;
let seleccion: ItemDTO[] = [];
let condicionesOk = false;
let modalidades: ModalidadDTO[] = [];

/** Descarta respuestas obsoletas: si el usuario cambia un campo antes de que llegue la
 *  respuesta anterior, solo la última petición puede actualizar la pantalla. */
function secuencia() {
  let ultima = 0;
  return { nueva: () => ++ultima, vigente: (n: number) => n === ultima };
}
const pedidoCondiciones = secuencia();
const pedidoUsuarios = secuencia();
const pedidoItems = secuencia();

const plural = (n: number, singular: string, plural_: string) => `${n} ${n === 1 ? singular : plural_}`;

// ---------------------------------------------------------------- lista de préstamos
function estadoDe(p: PrestamoDTO): [string, string, string] {
  if (p.estado === 'devuelto') {
    return p.dias_atraso > 0
      ? ['aviso', 'aviso', `Devuelto con ${plural(p.dias_atraso, 'día', 'días')} de atraso`]
      : ['ok', 'ok', 'Devuelto'];
  }
  return p.vencido
    ? ['malo', 'malo', `Vencido hace ${plural(p.dias_atraso, 'día', 'días')}`]
    : ['aviso', 'aviso', 'Activo'];
}

function itemsDe(p: PrestamoDTO) {
  return el('ul', { class: 'items-prestamo' }, ...p.items.map((i) => {
    const condicion = i.condicion ? ` · ${ETIQUETA_CONDICION[i.condicion]}` : '';
    const nota = i.observacion ? ` («${i.observacion}»)` : '';
    return el('li', {}, el('span', { class: 'codigo' }, i.codigo), ` ${i.nombre}${condicion}${nota}`);
  }));
}

function filaDe(p: PrestamoDTO) {
  const [marcador, claseEstado, textoEstado] = estadoDe(p);
  const partes = [
    gestiona ? p.usuario : null,
    p.modalidad ?? 'Sin modalidad (préstamo anterior)',
    p.rol_solicitante ? `como ${ETIQUETA_ROL[p.rol_solicitante as Rol].toLowerCase()}` : null,
    `desde ${fechaLegible(p.fecha_prestamo)}`,
    p.fecha_limite ? `límite ${soloFecha(p.fecha_limite)}` : 'sin fecha límite',
    p.fecha_devolucion ? `devuelto ${fechaLegible(p.fecha_devolucion)}` : null,
  ].filter(Boolean);

  const acciones = el('div', {}, el('div', { class: `estado ${claseEstado}` }, textoEstado));
  if (p.estado === 'activo' && (gestiona || (puedeRenovar && p.usuario_id === usuario?.id))) {
    const renovar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Renovar préstamo');
    renovar.addEventListener('click', async () => {
      try {
        const renovado = await api.post<PrestamoDTO>(`/api/prestamos/${p.id}/renovacion`);
        avisar(`Préstamo renovado. Nueva fecha límite: ${soloFecha(renovado.fecha_limite)}.`);
        await cargarLista();
      } catch (error) {
        avisar(mensajeDe(error), true);
      }
    });
    acciones.append(renovar);
  }
  if (gestiona && p.estado === 'activo') {
    const boton = el('button', { type: 'button', class: 'pequeno secundario' }, 'Registrar devolución');
    boton.addEventListener('click', () => abrirDevolucion(p));
    acciones.append(boton);
  }
  return el('li', { class: 'prestamo' },
    el('span', { class: `marcador ${marcador}` }),
    el('div', {},
      el('h3', {}, p.items.map((i) => i.nombre).join(' · ')),
      el('div', { class: 'meta' }, partes.join(' · ')),
      itemsDe(p)),
    acciones);
}

async function cargarLista() {
  const estado = $<HTMLSelectElement>('#filtro-estado').value;
  const r = await api.get<PaginaPrestamosDTO>('/api/prestamos', { estado, pagina, limite: LIMITE });
  const lista = $<HTMLUListElement>('#lista');
  lista.replaceChildren();
  if (r.prestamos.length === 0) {
    const vacios: Record<string, string> = {
      activo: 'No hay préstamos activos.', vencido: 'No hay préstamos vencidos.',
      devuelto: 'No hay préstamos devueltos.', '': 'No hay préstamos registrados.',
    };
    lista.append(el('li', { class: 'vacio' }, el('span'), vacios[estado] ?? vacios['']));
  }
  for (const p of r.prestamos) lista.append(filaDe(p));
  const paginas = Math.max(1, Math.ceil(r.total / r.limite));
  $('#pagina').textContent = `Página ${r.pagina} de ${paginas} · ${plural(r.total, 'préstamo', 'préstamos')}`;
  $<HTMLButtonElement>('#anterior').disabled = r.pagina <= 1;
  $<HTMLButtonElement>('#siguiente').disabled = r.pagina >= paginas;
}

// ---------------------------------------------------------------- devolución (RF11)
const dialogoDevolucion = $<HTMLDialogElement>('#dialogo-devolucion');
let devolviendo: PrestamoDTO | null = null;

function abrirDevolucion(p: PrestamoDTO) {
  devolviendo = p;
  $('#devolucion-error').textContent = '';
  $('#devolucion-resumen').textContent =
    `${p.usuario} · ${plural(p.items.length, 'recurso', 'recursos')}. Indique la condición en que vuelve cada uno.`;
  $('#devolucion-items').replaceChildren(...p.items.map((i) => {
    const condicion = el('select', { 'aria-label': `Condición de ${i.codigo}`, 'data-item': String(i.item_id) });
    opciones(condicion, (Object.keys(ETIQUETA_CONDICION) as CondicionDevolucion[])
      .map((c) => [c, ETIQUETA_CONDICION[c]]));
    const nota = el('input', {
      'aria-label': `Observación de ${i.codigo}`, 'data-nota': String(i.item_id),
      maxlength: '300', placeholder: 'Observación (opcional)',
    });
    return el('div', { class: 'devolucion-item' },
      el('strong', {}, i.nombre), ' ', el('span', { class: 'codigo tenue' }, i.codigo),
      el('div', { class: 'dos-columnas' }, el('div', {}, condicion), el('div', {}, nota)));
  }));
  dialogoDevolucion.showModal();
}

function resumenDeDevolucion(p: PrestamoDTO) {
  const partes = ['Devolución registrada.'];
  if (p.dias_atraso > 0) partes.push(`Atraso de ${plural(p.dias_atraso, 'día', 'días')}.`);
  const danados = p.items.filter((i) => i.condicion === 'DANADO').map((i) => i.codigo);
  const perdidos = p.items.filter((i) => i.condicion === 'PERDIDO').map((i) => i.codigo);
  if (danados.length) partes.push(`En mantenimiento: ${danados.join(', ')}.`);
  if (perdidos.length) partes.push(`Marcados como extraviados: ${perdidos.join(', ')}.`);
  return partes.join(' ');
}

$('#devolucion-cancelar').addEventListener('click', () => dialogoDevolucion.close());
$('#formulario-devolucion').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!devolviendo) return;
  const boton = $<HTMLButtonElement>('#devolucion-confirmar');
  boton.disabled = true;
  try {
    const condiciones = devolviendo.items.map((i) => ({
      item_id: i.item_id,
      condicion: $<HTMLSelectElement>(`[data-item="${i.item_id}"]`).value,
      observacion: $<HTMLInputElement>(`[data-nota="${i.item_id}"]`).value.trim() || undefined,
    }));
    const resultado = await api.post<PrestamoDTO>(`/api/prestamos/${devolviendo.id}/devolucion`, { condiciones });
    dialogoDevolucion.close();
    avisar(resumenDeDevolucion(resultado));
    await cargar();
  } catch (error) {
    $('#devolucion-error').textContent = mensajeDe(error);
  } finally {
    boton.disabled = false;
  }
});

// ---------------------------------------------------------------- entrega (RF10, RF13)
const selUsuario = () => $<HTMLSelectElement>('#usuario');
const selModalidad = () => $<HTMLSelectElement>('#modalidad');
const selRol = () => $<HTMLSelectElement>('#rol');

function dibujarSeleccion() {
  $('#seleccion').replaceChildren(...seleccion.map((item) => {
    const quitar = el('button', { type: 'button', class: 'pequeno secundario', 'aria-label': `Quitar ${item.codigo}` }, 'Quitar');
    quitar.addEventListener('click', () => {
      seleccion = seleccion.filter((i) => i.id !== item.id);
      dibujarSeleccion();
      void cargarItems();
    });
    return el('li', {}, el('span', {}, el('span', { class: 'codigo' }, item.codigo), ` ${item.nombre}`), quitar);
  }));
  validarEntrega();
}

function validarEntrega() {
  $<HTMLButtonElement>('#prestar').disabled = !(condicionesOk && seleccion.length > 0);
}

function mostrarResumen(texto: string, error = false) {
  const zona = $('#resumen-condiciones');
  zona.textContent = texto;
  zona.classList.toggle('error', error);
}

function restaurarEtiquetasModalidad() {
  for (const opcion of Array.from(selModalidad().options)) {
    const modalidad = modalidades.find((m) => String(m.id) === opcion.value);
    if (modalidad) opcion.textContent = modalidad.nombre;
  }
}

function mostrarPlazoAplicado(dias: number) {
  const opcion = selModalidad().selectedOptions[0];
  const modalidad = modalidades.find((m) => String(m.id) === opcion?.value);
  if (opcion && modalidad) {
    opcion.textContent = `${modalidad.nombre} · ${plural(dias, 'día', 'días')}`;
  }
}

async function actualizarCondiciones() {
  const mio = pedidoCondiciones.nueva();
  condicionesOk = false;
  restaurarEtiquetasModalidad();
  validarEntrega();
  if (!selUsuario().value || !selModalidad().value) { mostrarResumen(''); return; }
  try {
    const c = await api.get<CondicionesPrestamoDTO>('/api/prestamos/condiciones', {
      usuario_id: selUsuario().value, modalidad_id: selModalidad().value,
      rol_solicitante: $('#zona-rol').hidden ? undefined : selRol().value,
    });
    if (!pedidoCondiciones.vigente(mio)) return;
    const roles = c.roles_posibles;
    $('#zona-rol').hidden = roles.length < 2;
    if (roles.length > 1 && selRol().options.length !== roles.length + 1) {
      opciones(selRol(), roles.map((r: RolPrestatario) => [r, ETIQUETA_ROL[r]]), 'Elija el perfil…');
    }
    if (c.rol_solicitante === null) { mostrarResumen('Elija con qué perfil presta el usuario.'); return; }
    if (roles.length > 1) selRol().value = c.rol_solicitante;
    condicionesOk = (c.cupo_restante ?? 0) > 0;
    mostrarPlazoAplicado(c.dias_plazo ?? 0);
    mostrarResumen(
      `Prestará como ${ETIQUETA_ROL[c.rol_solicitante as Rol].toLowerCase()} · plazo de ${plural(c.dias_plazo ?? 0, 'día', 'días')}, ` +
      `vence el ${soloFecha(c.fecha_limite ?? null)} · cupo: ${c.cupo_restante} de ${c.max_items_simultaneos} ` +
      `(tiene ${c.items_en_prestamo} en préstamo)` +
      (condicionesOk ? '.' : '. Sin cupo disponible: debe devolver recursos antes.'), !condicionesOk);
  } catch (error) {
    if (pedidoCondiciones.vigente(mio)) mostrarResumen(mensajeDe(error), true);
  }
  if (pedidoCondiciones.vigente(mio)) validarEntrega();
}

async function cargarUsuarios() {
  const mio = pedidoUsuarios.nueva();
  const anterior = selUsuario().value;
  const usuarios = await api.get<{ id: number; nombre: string; correo: string }[]>('/api/usuarios/prestatarios', {
    q: $<HTMLInputElement>('#buscar-usuario').value.trim(),
  });
  if (!pedidoUsuarios.vigente(mio)) return;
  opciones(selUsuario(), usuarios.map((u) => [String(u.id), `${u.nombre} (${u.correo})`]));
  if (usuarios.some((u) => String(u.id) === anterior)) selUsuario().value = anterior;
  $('#zona-rol').hidden = true;
  await actualizarCondiciones();
}

async function cargarItems() {
  const mio = pedidoItems.nueva();
  const r = await api.get<PaginaItemsDTO>('/api/items', {
    estado: 'DISPONIBLE', limite: 50, q: $<HTMLInputElement>('#buscar-item').value.trim(),
  });
  if (!pedidoItems.vigente(mio)) return;
  const elegidos = new Set(seleccion.map((i) => i.id));
  const libres = r.items.filter((i) => !elegidos.has(i.id));
  opciones($('#item'), libres.map((i: ItemDTO) => [String(i.id), `${i.nombre} (${i.codigo})`]));
  $<HTMLButtonElement>('#agregar').disabled = libres.length === 0;
  itemsDisponibles = libres;
}
let itemsDisponibles: ItemDTO[] = [];

async function cargarFormulario() {
  modalidades = (await api.get<ModalidadDTO[]>('/api/modalidades')).filter((m) => m.activo);
  opciones(selModalidad(), modalidades.map((m) => [String(m.id), m.nombre]));
  await Promise.all([cargarUsuarios(), cargarItems()]);
}

async function cargar() {
  try {
    await cargarLista();
    if (gestiona) {
      await Promise.all([cargarItems(), actualizarCondiciones()]);
    }
  } catch (error) {
    avisar(mensajeDe(error), true);
  }
}

if (usuario) {
  $('#filtro-estado').addEventListener('change', () => { pagina = 1; void cargar(); });
  $('#anterior').addEventListener('click', () => { pagina -= 1; void cargar(); });
  $('#siguiente').addEventListener('click', () => { pagina += 1; void cargar(); });

  if (gestiona) {
    $('#nuevo').hidden = false;
    $('#subtitulo').textContent = 'Registre entregas con uno o varios recursos y sus devoluciones.';
    const alFallar = (error: unknown) => avisar(mensajeDe(error), true);
    const buscarUsuarios = retardo(() => { cargarUsuarios().catch(alFallar); });
    const buscarItems = retardo(() => { cargarItems().catch(alFallar); });
    $('#buscar-usuario').addEventListener('input', buscarUsuarios);
    $('#buscar-item').addEventListener('input', buscarItems);
    selUsuario().addEventListener('change', () => { $('#zona-rol').hidden = true; void actualizarCondiciones(); });
    selModalidad().addEventListener('change', () => void actualizarCondiciones());
    selRol().addEventListener('change', () => void actualizarCondiciones());

    $('#agregar').addEventListener('click', () => {
      const elegido = itemsDisponibles.find((i) => String(i.id) === $<HTMLSelectElement>('#item').value);
      if (!elegido) return;
      seleccion = [...seleccion, elegido];
      dibujarSeleccion();
      void cargarItems();
    });

    $('#formulario').addEventListener('submit', async (e) => {
      e.preventDefault();
      const boton = $<HTMLButtonElement>('#prestar');
      boton.disabled = true;
      try {
        const rolVisible = !$('#zona-rol').hidden;
        const p = await api.post<PrestamoDTO>('/api/prestamos', {
          usuario_id: Number(selUsuario().value),
          modalidad_id: Number(selModalidad().value),
          item_ids: seleccion.map((i) => i.id),
          rol_solicitante: rolVisible ? selRol().value : undefined,
        });
        seleccion = [];
        dibujarSeleccion();
        avisar(`Entrega registrada. Fecha límite: ${soloFecha(p.fecha_limite)}.`);
        pagina = 1;
        await cargar();
      } catch (error) {
        avisar(mensajeDe(error), true);
        validarEntrega();
      }
    });
    cargarFormulario().catch((error) => avisar(mensajeDe(error), true));
  } else {
    $('#titulo-lista').textContent = 'Mis préstamos';
    $('#subtitulo').textContent = 'Consulte sus fechas límite. Las entregas y devoluciones las registra un gestor de inventario.';
  }
  void cargarLista().catch((error) => avisar(mensajeDe(error), true));
}
