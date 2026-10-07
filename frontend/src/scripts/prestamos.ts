import { api } from './api';
import type { ItemDTO, PaginaItemsDTO, PrestamoDTO, UsuarioDTO } from './contratos';
import { exigirSesion, tienePermiso } from './sesion';
import { $, avisar, el, fechaLegible, mensajeDe, opciones } from './ui';

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
  const [usuarios, items] = await Promise.all([
    api.get<UsuarioDTO[]>('/api/usuarios', { habilitado: 'true' }),
    api.get<PaginaItemsDTO>('/api/items', { estado: 'DISPONIBLE', limite: 100 }),
  ]);
  opciones($('#usuario'), usuarios.map((u) => [String(u.id), u.nombre]));
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
    $('#formulario').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api.post('/api/prestamos', {
          usuario_id: Number($<HTMLSelectElement>('#usuario').value),
          item_id: Number($<HTMLSelectElement>('#item').value),
        });
        avisar('Entrega registrada.');
        await cargar();
      } catch (error) {
        avisar(mensajeDe(error), true);
      }
    });
  } else {
    $('#titulo-lista').textContent = 'Mis préstamos activos';
    $('#subtitulo').textContent = 'Las entregas y devoluciones las registra un gestor de inventario.';
  }
  cargar();
}
