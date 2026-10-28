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
export type CondicionDevolucion = 'BUEN_ESTADO' | 'DANADO' | 'PERDIDO';
export type RolPrestatario = 'ESTUDIANTE' | 'DOCENTE' | 'ADMINISTRATIVO';
export type ItemPrestamoDTO = {
  item_id: number; codigo: string; nombre: string; tipo: string;
  condicion: CondicionDevolucion | null; observacion: string | null;
};
export type PrestamoDTO = {
  id: number; reserva_id: number | null; usuario_id: number; usuario: string;
  rol_solicitante: RolPrestatario | null;       // null en préstamos anteriores al Sprint 3
  modalidad: string | null; dias_plazo: number | null; numero_renovaciones: number;
  items: ItemPrestamoDTO[];
  fecha_prestamo: string; fecha_limite: string | null; fecha_devolucion: string | null;
  estado: 'activo' | 'devuelto'; vencido: boolean; dias_atraso: number;
};
export type PaginaPrestamosDTO = { prestamos: PrestamoDTO[]; total: number; pagina: number; limite: number };
export type ModalidadDTO = { id: number; nombre: string; activo: boolean };
export type CondicionesPrestamoDTO = {
  usuario_id: number; rol_solicitante: RolPrestatario | null; roles_posibles: RolPrestatario[];
  modalidad?: string; dias_plazo?: number; fecha_limite?: string;
  max_items_simultaneos?: number; items_en_prestamo?: number; cupo_restante?: number;
  tipos_permitidos?: string[];
};
export type PoliticaDTO = {
  id: number; rol: Rol; modalidad_id: number; modalidad: string;
  max_items_simultaneos: number; dias_prestamo: number;
  dias_gracia_reserva: number; tipos_recurso_permitidos: string[];
};
export type EstadoReserva = 'PENDIENTE' | 'CONFIRMADA' | 'EXPIRADA' | 'CANCELADA' | 'CONVERTIDA';
export type ReservaDTO = {
  id: number; usuario_id: number; usuario: string; item_id: number;
  codigo: string; item: string; rol_solicitante: RolPrestatario;
  fecha_solicitud: string; fecha_reserva: string; fecha_expiracion: string;
  estado: EstadoReserva;
};
export type PaginaReservasDTO = {
  reservas: ReservaDTO[]; total: number; pagina: number; limite: number;
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
export const ETIQUETA_CONDICION: Record<CondicionDevolucion, string> = {
  BUEN_ESTADO: 'Buen estado', DANADO: 'Dañado', PERDIDO: 'Perdido',
};
export const ETIQUETA_RESERVA: Record<EstadoReserva, string> = {
  PENDIENTE: 'Pendiente', CONFIRMADA: 'Confirmada', EXPIRADA: 'Expirada',
  CANCELADA: 'Cancelada', CONVERTIDA: 'Convertida en préstamo',
};
