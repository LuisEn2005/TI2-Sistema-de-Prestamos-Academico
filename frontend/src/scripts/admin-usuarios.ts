import { api } from './api';
import { ETIQUETA_ROL, type PerfilDTO, type Rol, type UsuarioDTO } from './contratos';
import { exigirSesion } from './sesion';
import { $, avisar, el, mensajeDe, opciones, retardo } from './ui';

type CampoPerfil = { clave: string; etiqueta: string; tipo?: 'checkbox' | 'date' };
const CAMPOS: Record<Rol, CampoPerfil[]> = {
  ESTUDIANTE: [
    { clave: 'codigo_estudiante', etiqueta: 'Código de estudiante' },
    { clave: 'matricula_vigente', etiqueta: 'Matrícula vigente', tipo: 'checkbox' },
  ],
  DOCENTE: [
    { clave: 'codigo_empleado', etiqueta: 'Código de empleado' },
    { clave: 'tipo_contrato', etiqueta: 'Tipo de contrato' },
  ],
  ADMINISTRATIVO: [
    { clave: 'codigo_empleado', etiqueta: 'Código de empleado' },
    { clave: 'cargo_administrativo', etiqueta: 'Cargo' },
  ],
  GESTOR_INVENTARIO: [
    { clave: 'codigo_empleado', etiqueta: 'Código de empleado' },
    { clave: 'area_responsable', etiqueta: 'Área responsable' },
    { clave: 'fecha_asignacion', etiqueta: 'Fecha de asignación', tipo: 'date' },
  ],
};
const ROLES = Object.keys(CAMPOS) as Rol[];

let editando: UsuarioDTO | null = null;
let yo: UsuarioDTO;
const dialogo = $<HTMLDialogElement>('#dialogo');

function construirPerfiles(usuario: UsuarioDTO | null) {
  $('#f-perfiles').replaceChildren(...ROLES.map((rol) => {
    const existente = usuario?.perfiles[rol];
    const activar = el('input', { type: 'checkbox', id: `r-${rol}` });
    activar.checked = !!existente;
    const campos = el('div', { class: 'dos-columnas' }, ...CAMPOS[rol].map((c) => {
      const id = `p-${rol}-${c.clave}`;
      const entrada = el('input', { id, 'data-rol': rol, 'data-clave': c.clave, type: c.tipo ?? 'text', maxlength: '80' });
      const valor = existente?.[c.clave];
      if (c.tipo === 'checkbox') {
        entrada.checked = valor === undefined ? true : Boolean(valor);
        return el('label', { class: 'casilla' }, entrada, c.etiqueta);
      }
      entrada.value = typeof valor === 'string' ? valor : '';
      return el('div', {}, el('label', { for: id }, c.etiqueta), entrada);
    }));
    campos.hidden = !activar.checked;
    activar.addEventListener('change', () => {
      campos.hidden = !activar.checked;
      campos.querySelectorAll<HTMLInputElement>('input:not([type=checkbox]):not([type=date])').forEach((i) => { i.required = activar.checked; });
    });
    campos.querySelectorAll<HTMLInputElement>('input:not([type=checkbox]):not([type=date])').forEach((i) => { i.required = activar.checked; });
    return el('fieldset', {}, el('legend', {}, el('label', { class: 'casilla', style: 'margin:0' }, activar, ETIQUETA_ROL[rol])), campos);
  }));
}

function leerPerfil(rol: Rol): PerfilDTO {
  const datos: PerfilDTO = {};
  document.querySelectorAll<HTMLInputElement>(`input[data-rol="${rol}"]`).forEach((i) => {
    if (i.type === 'checkbox') datos[i.dataset.clave!] = i.checked;
    else if (i.value !== '') datos[i.dataset.clave!] = i.value;
  });
  return datos;
}

function abrirFormulario(usuario: UsuarioDTO | null) {
  editando = usuario;
  $('#titulo-dialogo').textContent = usuario ? `Editar a ${usuario.nombre}` : 'Nuevo usuario';
  $('#et-password').textContent = usuario
    ? 'Nueva contraseña (deje en blanco para no cambiarla)'
    : 'Contraseña inicial (opcional; sin ella no podrá ingresar)';
  $('#f-error').textContent = '';
  $<HTMLInputElement>('#f-nombre').value = usuario?.nombre ?? '';
  $<HTMLInputElement>('#f-correo').value = usuario?.correo ?? '';
  $<HTMLInputElement>('#f-password').value = '';
  $<HTMLInputElement>('#f-activo').checked = usuario?.activo ?? true;
  construirPerfiles(usuario);
  dialogo.showModal();
}

function fila(u: UsuarioDTO) {
  const editar = el('button', { type: 'button', class: 'pequeno secundario' }, 'Editar');
  editar.addEventListener('click', () => abrirFormulario(u));
  const situacion = !u.activo ? 'Cuenta desactivada' : u.habilitado ? 'Habilitado' : (u.motivo_no_habilitado ?? 'No habilitado');
  return el('tr', {},
    el('td', {}, el('strong', {}, u.nombre), el('div', { class: 'meta' }, u.correo)),
    el('td', {}, ...u.roles.map((r) => el('span', { class: 'etiqueta-rol' }, ETIQUETA_ROL[r]))),
    el('td', {}, el('span', { class: `estado ${u.activo && u.habilitado ? 'ok' : 'aviso'}` }, situacion)),
    el('td', {}, editar));
}

async function cargar() {
  try {
    const usuarios = await api.get<UsuarioDTO[]>('/api/usuarios', {
      q: $<HTMLInputElement>('#q').value.trim(), rol: $<HTMLSelectElement>('#rol').value,
    });
    const cuerpo = $('#filas');
    cuerpo.replaceChildren(...usuarios.map(fila));
    if (usuarios.length === 0) cuerpo.append(el('tr', {}, el('td', { colspan: '4', class: 'vacio' }, 'No hay usuarios con estos filtros.')));
  } catch (error) {
    avisar(mensajeDe(error), true);
  }
}

const sesion = await exigirSesion('GESTIONAR_USUARIOS_Y_ROLES');
if (sesion) {
  yo = sesion;
  opciones($('#rol'), ROLES.map((r) => [r, ETIQUETA_ROL[r]]), 'Todos');
  $('#q').addEventListener('input', retardo(cargar));
  $('#rol').addEventListener('change', cargar);
  $('#nuevo').addEventListener('click', () => abrirFormulario(null));
  $('#cancelar').addEventListener('click', () => dialogo.close());

  $('#formulario').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const perfiles: Record<string, PerfilDTO | null> = {};
    for (const rol of ROLES) {
      const marcado = $<HTMLInputElement>(`#r-${rol}`).checked;
      if (marcado) perfiles[rol] = leerPerfil(rol);
      else if (editando?.perfiles[rol]) perfiles[rol] = null; // quitar el perfil existente
    }
    const cuerpo: Record<string, unknown> = {
      nombre: $<HTMLInputElement>('#f-nombre').value, correo: $<HTMLInputElement>('#f-correo').value,
      activo: $<HTMLInputElement>('#f-activo').checked, perfiles,
    };
    const clave = $<HTMLInputElement>('#f-password').value;
    if (clave) cuerpo.password = clave;
    try {
      if (editando) await api.patch(`/api/usuarios/${editando.id}`, cuerpo);
      else await api.post('/api/usuarios', cuerpo);
      dialogo.close();
      avisar(editando ? 'Usuario actualizado.' : 'Usuario registrado.');
      await cargar();
    } catch (error) {
      $('#f-error').textContent = mensajeDe(error);
    }
  });
  void yo;
  cargar();
}
