// ApiClient: único punto de comunicación del frontend con la API Flask (HTTP/JSON).

const CLAVE_TOKEN = 'prestamos.token';

export class ApiError extends Error {
  constructor(mensaje: string, public estado: number) {
    super(mensaje);
  }
}

export const token = () => sessionStorage.getItem(CLAVE_TOKEN);
export const guardarToken = (valor: string) => sessionStorage.setItem(CLAVE_TOKEN, valor);
export const olvidarToken = () => sessionStorage.removeItem(CLAVE_TOKEN);

type Opciones = { metodo?: string; cuerpo?: unknown };

async function solicitar<T>(ruta: string, { metodo = 'GET', cuerpo }: Opciones = {}): Promise<T> {
  const cabeceras: Record<string, string> = {};
  const actual = token();
  if (actual) cabeceras['Authorization'] = `Bearer ${actual}`;
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';

  let respuesta: Response;
  try {
    respuesta = await fetch(ruta, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
  } catch {
    throw new ApiError('No se pudo conectar con el servidor. Compruebe que Flask esté en ejecución.', 0);
  }
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    throw new ApiError(datos.error || 'No se pudo completar la operación.', respuesta.status);
  }
  return datos as T;
}

export const api = {
  get: <T>(ruta: string, consulta?: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(consulta ?? {})) {
      if (v !== undefined && v !== '') params.set(k, String(v));
    }
    const texto = params.toString();
    return solicitar<T>(texto ? `${ruta}?${texto}` : ruta);
  },
  post: <T>(ruta: string, cuerpo?: unknown) => solicitar<T>(ruta, { metodo: 'POST', cuerpo: cuerpo ?? {} }),
  patch: <T>(ruta: string, cuerpo: unknown) => solicitar<T>(ruta, { metodo: 'PATCH', cuerpo }),
};
