// Contratos JSON de la API (DTO). Reflejan api/serializadores.py.

export type Estado =
  | 'DISPONIBLE' | 'PRESTADO' | 'RESERVADO' | 'EN_MANTENIMIENTO' | 'DADO_DE_BAJA' | 'EXTRAVIADO';
export type Rol =
  | 'ESTUDIANTE' | 'DOCENTE' | 'ADMINISTRATIVO'
  | 'GESTOR_INVENTARIO' | 'ADMINISTRADOR_SISTEMA';

export type ItemDTO = {
  id: number; codigo: string; nombre: string; categoria: string; tipo: string;
  estado: Estado; disponible: boolean; atributos: Record<string, string>;
};
export type PaginaItemsDTO = { items: ItemDTO[]; total: number; pagina: number; limite: number };
export type TipoDTO = {
  tipo: string; etiqueta: string;
  campos: { clave: string; etiqueta: string; obligatorio: boolean }[];
};

export type PerfilDTO = Record<string, string | boolean | number | null>;
export type UsuarioDTO = {
  id: number; nombre: string; correo: string; activo: boolean; roles: Rol[];
  perfiles: Partial<Record<Rol, PerfilDTO>>; tiene_sancion_activa: boolean;
  habilitado: boolean; motivo_no_habilitado: string | null; permisos?: string[];
};
export type PrestamoDTO = {
  id: number; usuario_id: number; usuario: string; item_id: number; item: string;
  codigo: string; fecha_prestamo: string; fecha_devolucion: string | null;
  estado: 'activo' | 'devuelto';
};
export type PoliticaDTO = {
  id: number; rol: Rol; max_items_simultaneos: number; dias_prestamo_default: number;
  dias_gracia_reserva: number; tipos_recurso_permitidos: string[];
};

export const ETIQUETA_ESTADO: Record<Estado, string> = {
  DISPONIBLE: 'Disponible', PRESTADO: 'Prestado', RESERVADO: 'Reservado',
  EN_MANTENIMIENTO: 'En mantenimiento', DADO_DE_BAJA: 'Dado de baja', EXTRAVIADO: 'Extraviado',
};
export const ETIQUETA_ROL: Record<Rol, string> = {
  ESTUDIANTE: 'Estudiante', DOCENTE: 'Docente', ADMINISTRATIVO: 'Administrativo',
  GESTOR_INVENTARIO: 'Gestor de inventario',
  ADMINISTRADOR_SISTEMA: 'Administrador del sistema',
};
