type Recurso = { id: number; codigo: string; nombre: string; tipo: string; disponible: boolean };
type Usuario = { id: number; nombre: string };
type Prestamo = { id: number; usuario: string; recurso: string; estado: string };

const listaRecursos = document.querySelector<HTMLUListElement>('#recursos')!;
const listaPrestamos = document.querySelector<HTMLUListElement>('#prestamos')!;
const selectorUsuario = document.querySelector<HTMLSelectElement>('#usuario')!;
const selectorRecurso = document.querySelector<HTMLSelectElement>('#recurso')!;
const formulario = document.querySelector<HTMLFormElement>('#formulario-prestamo')!;
const botonPrestar = document.querySelector<HTMLButtonElement>('#boton-prestar')!;
const mensaje = document.querySelector<HTMLParagraphElement>('#mensaje')!;

async function solicitar<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  const respuesta = await fetch(ruta, opciones);
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(datos.error || 'No se pudo completar la operación.');
  return datos as T;
}

function avisar(texto: string, error = false) {
  mensaje.textContent = texto;
  mensaje.classList.toggle('error', error);
}

function textoSecundario(texto: string) {
  const elemento = document.createElement('small');
  elemento.textContent = texto;
  return elemento;
}

function mostrarRecursos(recursos: Recurso[]) {
  listaRecursos.replaceChildren();
  selectorRecurso.replaceChildren();

  for (const recurso of recursos) {
    const fila = document.createElement('li');
    const descripcion = document.createElement('div');
    const nombre = document.createElement('strong');
    nombre.textContent = recurso.nombre;
    descripcion.append(nombre, textoSecundario(`${recurso.tipo} · ${recurso.codigo}`));

    const estado = document.createElement('span');
    estado.className = `estado ${recurso.disponible ? 'disponible' : 'ocupado'}`;
    estado.textContent = recurso.disponible ? 'Disponible' : 'Prestado';
    fila.append(descripcion, estado);
    listaRecursos.append(fila);

    if (recurso.disponible) {
      const opcion = document.createElement('option');
      opcion.value = String(recurso.id);
      opcion.textContent = recurso.nombre;
      selectorRecurso.append(opcion);
    }
  }

  if (recursos.length === 0) {
    const fila = document.createElement('li');
    fila.textContent = 'No hay recursos registrados.';
    listaRecursos.append(fila);
  }
  botonPrestar.disabled = selectorRecurso.options.length === 0 || selectorUsuario.options.length === 0;
}

function mostrarUsuarios(usuarios: Usuario[]) {
  selectorUsuario.replaceChildren();
  for (const usuario of usuarios) {
    const opcion = document.createElement('option');
    opcion.value = String(usuario.id);
    opcion.textContent = usuario.nombre;
    selectorUsuario.append(opcion);
  }
}

function mostrarPrestamos(prestamos: Prestamo[]) {
  listaPrestamos.replaceChildren();
  const activos = prestamos.filter((prestamo) => prestamo.estado === 'activo');
  if (activos.length === 0) {
    const fila = document.createElement('li');
    fila.textContent = 'No hay préstamos activos.';
    listaPrestamos.append(fila);
    return;
  }

  for (const prestamo of activos) {
    const fila = document.createElement('li');
    const descripcion = document.createElement('div');
    const nombre = document.createElement('strong');
    nombre.textContent = prestamo.recurso;
    descripcion.append(nombre, textoSecundario(prestamo.usuario));

    const boton = document.createElement('button');
    boton.type = 'button';
    boton.textContent = 'Devolver';
    boton.addEventListener('click', async () => {
      boton.disabled = true;
      try {
        await solicitar(`/api/prestamos/${prestamo.id}/devolucion`, { method: 'POST' });
        await cargar();
        avisar('Devolución registrada.');
      } catch (error) {
        avisar(error instanceof Error ? error.message : 'Error al devolver.', true);
        boton.disabled = false;
      }
    });
    fila.append(descripcion, boton);
    listaPrestamos.append(fila);
  }
}

async function cargar() {
  const [usuarios, recursos, prestamos] = await Promise.all([
    solicitar<Usuario[]>('/api/usuarios'),
    solicitar<Recurso[]>('/api/recursos'),
    solicitar<Prestamo[]>('/api/prestamos'),
  ]);
  mostrarUsuarios(usuarios);
  mostrarRecursos(recursos);
  mostrarPrestamos(prestamos);
}

formulario.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  botonPrestar.disabled = true;
  try {
    await solicitar('/api/prestamos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usuario_id: Number(selectorUsuario.value),
        recurso_id: Number(selectorRecurso.value),
      }),
    });
    await cargar();
    avisar('Préstamo registrado.');
  } catch (error) {
    avisar(error instanceof Error ? error.message : 'Error al prestar.', true);
    botonPrestar.disabled = false;
  }
});

cargar().catch(() => avisar('No se pudo conectar con el servidor. Comprueba que Flask esté en ejecución.', true));
