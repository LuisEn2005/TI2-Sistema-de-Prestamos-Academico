// Contratos JSON de la API (DTO). Reflejan api/serializadores.py.

export type Estado =
  | 'DISPONIBLE' | 'PRESTADO' | 'EN_MANTENIMIENTO' | 'DADO_DE_BAJA' | 'EXTRAVIADO';
export type Rol =
  | 'ESTUDIANTE' | 'DOCENTE' | 'ADMINISTRATIVO'
  | 'GESTOR_INVENTARIO' | 'ADMINISTRADOR_SISTEMA';
export type EspacioTrabajo = 'PERSONAL' | 'INVENTARIO' | 'ADMINISTRACION';

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
  espacio_activo: EspacioTrabajo; espacios_disponibles: EspacioTrabajo[];
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
  modalidad: string | null; dias_plazo: number | null;
  items: ItemPrestamoDTO[];
  fecha_prestamo: string; fecha_limite: string | null; fecha_devolucion: string | null;
  estado: 'activo' | 'devuelto'; vencido: boolean; dias_atraso: number;
  sancion_generada_id?: number;
};
export type PaginaPrestamosDTO = { prestamos: PrestamoDTO[]; total: number; pagina: number; limite: number };
export type ModalidadDTO = { id: number; nombre: string; activo: boolean };
export type CondicionesPrestamoDTO = {
  usuario_id: number; fecha_inicio?: string;
  rol_solicitante: RolPrestatario | null; roles_posibles: RolPrestatario[];
  modalidad?: string; dias_plazo?: number; fecha_limite?: string;
  max_items_simultaneos?: number; items_en_prestamo?: number; cupo_restante?: number;
  reservas_activas?: number; cupo_ocupado?: number;
  tipos_permitidos?: string[];
};
export type PoliticaDTO = {
  id: number; rol: Rol; modalidad_id: number; modalidad: string;
  max_items_simultaneos: number; dias_prestamo: number;
  dias_sancion_por_dia_atraso: number;
  tipos_recurso_permitidos: string[];
};
export type PoliticaRolDTO = {
  rol: RolPrestatario; max_items_simultaneos: number;
  dias_sancion_por_dia_atraso: number;
};
export type SancionDTO = {
  id: number; usuario_id: number; usuario: string; prestamo_id: number | null;
  origen: 'RETRASO' | 'DANO' | 'PERDIDA'; motivo: string;
  monto: string | null; moneda: string | null;
  fecha_inicio: string; fecha_fin: string | null; estado: 'ACTIVA' | 'CERRADA';
  resolucion: string | null;
};
export type EstadoReserva =
  | 'PENDIENTE' | 'CONFIRMADA' | 'EXPIRADA' | 'CANCELADA' | 'CONVERTIDA'
  | 'RECHAZADA' | 'RETIRADA';
export type ReservaDTO = {
  id: number; usuario_id: number; usuario: string; item_id: number;
  codigo: string; item: string; rol_solicitante: RolPrestatario;
  modalidad_id: number | null; modalidad: string | null;
  fecha_solicitud: string; fecha_inicio: string; fecha_fin: string;
  fecha_reserva: string; estado: EstadoReserva; motivo_resolucion: string | null;
};
export type PaginaReservasDTO = {
  reservas: ReservaDTO[]; total: number; pagina: number; limite: number;
};

export const ETIQUETA_ESTADO: Record<Estado, string> = {
  DISPONIBLE: 'Disponible', PRESTADO: 'Prestado',
  EN_MANTENIMIENTO: 'En mantenimiento', DADO_DE_BAJA: 'Dado de baja', EXTRAVIADO: 'Extraviado',
};
export const ETIQUETA_ROL: Record<Rol, string> = {
  ESTUDIANTE: 'Estudiante', DOCENTE: 'Docente', ADMINISTRATIVO: 'Administrativo',
  GESTOR_INVENTARIO: 'Gestor de inventario',
  ADMINISTRADOR_SISTEMA: 'Administrador del sistema',
};
export const ETIQUETA_ESPACIO: Record<EspacioTrabajo, string> = {
  PERSONAL: 'Personal', INVENTARIO: 'Inventario', ADMINISTRACION: 'Administración',
};
export const ETIQUETA_CONDICION: Record<CondicionDevolucion, string> = {
  BUEN_ESTADO: 'Buen estado', DANADO: 'Dañado', PERDIDO: 'Perdido',
};
export const ETIQUETA_RESERVA: Record<EstadoReserva, string> = {
  PENDIENTE: 'Pendiente', CONFIRMADA: 'Confirmada', EXPIRADA: 'Expirada',
  CANCELADA: 'Cancelada', CONVERTIDA: 'Entregada · préstamo creado',
  RECHAZADA: 'Rechazada', RETIRADA: 'Retirada',
};

export type EstadoCalendario = 'DISPONIBLE' | 'RESERVADO' | 'NO_DISPONIBLE';
export type CalendarioItemDTO = {
  item_id: number; codigo: string; item: string;
  dias: { fecha: string; estado: EstadoCalendario }[];
};
export type SolicitudCalendarioDTO = {
  id: number; usuario_id: number; usuario: string; rol_solicitante: RolPrestatario;
  fecha_inicio: string; fecha_fin: string; fecha_solicitud: string;
};
export type DiaNoLaborableDTO = {
  id: number; fecha_inicio: string; fecha_fin: string;
  tipo: 'FERIADO' | 'HUELGA' | 'OTRO'; motivo: string; activo: boolean;
};
export type FechaSistemaDTO = { fecha: string; siguiente_laborable: string };

export type EventoReservaDTO = {
  id: number; tipo: string; actor: string; actor_tipo: 'USUARIO' | 'SISTEMA';
  motivo: string | null; creado_en: string;
  fecha_inicio_anterior: string | null; fecha_fin_anterior: string | null;
  fecha_inicio_nueva: string | null; fecha_fin_nueva: string | null;
};
export type DetalleReservaDTO = ReservaDTO & { eventos: EventoReservaDTO[]; prestamo_id: number | null };
export type EstadoFechaItem = 'DISPONIBLE' | 'RESERVADO' | 'PRESTADO' | 'NO_DISPONIBLE';
export type ItemInventarioDTO = {
  id: number; codigo: string; nombre: string; categoria: string; tipo: string;
  estado_fisico: Estado; estado_fecha: EstadoFechaItem;
  solicitudes_pendientes: number; atributos: Record<string, string>;
  asignacion: null | {
    tipo: 'PRESTAMO' | 'RESERVA'; usuario: string;
    fecha_inicio: string; fecha_fin: string;
    prestamo_id?: number; reserva_id?: number;
  };
};
export type PaginaInventarioDTO = {
  items: ItemInventarioDTO[]; total: number; pagina: number; limite: number; fecha: string;
};
