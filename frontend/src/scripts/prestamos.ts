import { api } from './api';
import type { ItemDTO, PaginaItemsDTO, PrestamoDTO } from './contratos';
import { exigirSesion, tienePermiso } from './sesion';
import { $, avisar, el, fechaLegible, mensajeDe, opciones, retardo } from './ui';

const usuario = await exigirSesion();
const gestiona = tienePermiso(usuario, 'REGISTRAR_ENTREGA_PRESTAMO');

function dibujar(prestamos: PrestamoDTO[]) {
  const lista = $<HTMLUListElement>('#lista');
  lista.replaceChildren();
  const activos = prestamos.filter((p) => p.estado === 'activo');
  if (activos.length === 0) {
    lista.append(el('li', { class: 'vacio' }, el('span'), 'No hay préstamos activos.'));
  }
  for (const p of activos) {
    const accion = el('div', {});
    if (gestiona) {
      const boton = el('button', { type: 'button', class: 'pequeno secundario' }, 'Registrar devolución');
      boton.addEventListener('click', async () => {
        boton.disabled = true;
        try {
          await api.post(`/api/prestamos/${p.id}/devolucion`);
          avisar('Devolución registrada.');
          await cargar();
        } catch (error) {
          avisar(mensajeDe(error), true);
          boton.disabled = false;
        }
      });
      accion.append(boton);
    }
    lista.append(el('li', {},
      el('span', { class: 'marcador aviso' }),
      el('div', {}, el('h3', {}, p.item),
        el('div', { class: 'meta' }, el('span', { class: 'codigo' }, p.codigo), ` · ${p.usuario} · desde ${fechaLegible(p.fecha_prestamo)}`)),
      accion));
  }
}

async function cargarFormulario() {
  const consultaUsuario = $<HTMLInputElement>('#buscar-usuario').value.trim();
  const [usuarios, items] = await Promise.all([
    api.get<{ id: number; nombre: string; correo: string }[]>('/api/usuarios/prestatarios', {
      q: consultaUsuario,
    }),
    api.get<PaginaItemsDTO>('/api/items', {
      estado: 'DISPONIBLE', limite: 50,
      q: $<HTMLInputElement>('#buscar-item').value.trim(),
    }),
  ]);
  opciones($('#usuario'), usuarios.map((u) => [String(u.id), `${u.nombre} (${u.correo})`]));
  opciones($('#item'), items.items.map((i: ItemDTO) => [String(i.id), `${i.nombre} (${i.codigo})`]));
  $<HTMLButtonElement>('#prestar').disabled = usuarios.length === 0 || items.items.length === 0;
}

async function cargar() {
  try {
    dibujar(await api.get<PrestamoDTO[]>('/api/prestamos'));
    if (gestiona) await cargarFormulario();
  } catch (error) {
    avisar(mensajeDe(error), true);
  }
}

if (usuario) {
  if (gestiona) {
    $('#nuevo').hidden = false;
    $('#subtitulo').textContent = 'Registre entregas y devoluciones de todos los usuarios.';
    const buscarOpciones = retardo(async () => {
      try {
        await cargarFormulario();
      } catch (error) {
        avisar(mensajeDe(error), true);
      }
    });
    $('#buscar-usuario').addEventListener('input', buscarOpciones);
    $('#buscar-item').addEventListener('input', buscarOpciones);
    $('#formulario').addEventListener('submit', async (e) => {
      e.preventDefault();
      const boton = $<HTMLButtonElement>('#prestar');
      boton.disabled = true;
      try {
        await api.post('/api/prestamos', {
          usuario_id: Number($<HTMLSelectElement>('#usuario').value),
          item_id: Number($<HTMLSelectElement>('#item').value),
        });
        avisar('Entrega registrada.');
        await cargar();
      } catch (error) {
        avisar(mensajeDe(error), true);
        boton.disabled = false;
      }
    });
  } else {
    $('#titulo-lista').textContent = 'Mis préstamos activos';
    $('#subtitulo').textContent = 'Las entregas y devoluciones las registra un gestor de inventario.';
  }
  cargar();
}
