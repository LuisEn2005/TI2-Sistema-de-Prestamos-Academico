// Utilidades de DOM. Todo el texto se inserta con textContent (sin innerHTML).

export function el<K extends keyof HTMLElementTagNameMap>(
  etiqueta: K,
  atributos: Record<string, string> = {},
  ...hijos: (Node | string | null | undefined)[]
): HTMLElementTagNameMap[K] {
  const nodo = document.createElement(etiqueta);
  for (const [k, v] of Object.entries(atributos)) nodo.setAttribute(k, v);
  for (const hijo of hijos) {
    if (hijo === null || hijo === undefined) continue;
    nodo.append(typeof hijo === 'string' ? document.createTextNode(hijo) : hijo);
  }
  return nodo;
}

export function $<T extends HTMLElement>(selector: string): T {
  const nodo = document.querySelector<T>(selector);
  if (!nodo) throw new Error(`Falta el elemento ${selector}`);
  return nodo;
}

export function avisar(texto: string, error = false) {
  const zona = $<HTMLParagraphElement>('#mensaje');
  zona.textContent = texto;
  zona.classList.toggle('error', error);
  if (texto) zona.scrollIntoView({ block: 'nearest' });
}

export function mensajeDe(error: unknown, defecto = 'Ocurrió un error inesperado.') {
  return error instanceof Error ? error.message : defecto;
}

export function opciones(select: HTMLSelectElement, valores: [string, string][], vacio?: string) {
  select.replaceChildren();
  if (vacio !== undefined) select.append(el('option', { value: '' }, vacio));
  for (const [valor, texto] of valores) select.append(el('option', { value: valor }, texto));
}

export function fechaLegible(iso: string | null) {
  if (!iso) return '';
  return new Date(iso).toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' });
}

export function retardo<A extends unknown[]>(funcion: (...a: A) => void, ms = 250) {
  let temporizador: number | undefined;
  return (...args: A) => {
    window.clearTimeout(temporizador);
    temporizador = window.setTimeout(() => funcion(...args), ms);
  };
}
