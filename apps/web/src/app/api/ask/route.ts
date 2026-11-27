// POST /api/ask : seule route dynamique de l'application (PLAN § 4.5). Flux SSE documenté dans
// schemas/ask_event.schema.json.
import { askHandler } from "@/lib/rag/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function POST(req: Request): Promise<Response> {
  return askHandler(req);
}
