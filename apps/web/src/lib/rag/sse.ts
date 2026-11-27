import type { AskEvent } from "@moi-electeur/schemas-ts";

/** Une trame SSE : `event: <type>` puis le JSON de l'événement sur une seule ligne. */
export function encodeEvent(event: AskEvent): string {
  return `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
}
