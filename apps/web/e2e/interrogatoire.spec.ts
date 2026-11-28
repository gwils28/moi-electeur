// Interrogatoire (ex-explorateur, M2d) : /api/ask simulé dans le navigateur, aucun appel réel à Claude.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const config = JSON.parse(
  readFileSync(
    join(
      import.meta.dirname,
      "..",
      "public",
      "data",
      "fr-presidentielle-2022",
      "election_config.json",
    ),
    "utf-8",
  ),
) as { candidates: { id: string; name: string; blind_alias: string }[] };

const [A, B, C] = config.candidates as [
  (typeof config.candidates)[number],
  (typeof config.candidates)[number],
  (typeof config.candidates)[number],
];
const SILENCE = "Aucune proposition recensée dans le programme officiel sur ce point.";

function sse(mode: "rapide" | "approfondi"): string {
  const events = [
    {
      type: "meta",
      election_id: "fr-presidentielle-2022",
      corpus_version: "v",
      prompt_version: "1",
      model: mode === "rapide" ? "claude-haiku-5-5" : "claude-sonnet-5-5",
      mode,
      cached: false,
      candidates: [
        { token: "c1", candidate_id: A.id, has_excerpts: true },
        { token: "c2", candidate_id: B.id, has_excerpts: true },
        { token: "c3", candidate_id: C.id, has_excerpts: false },
      ],
    },
    { type: "delta", block: 0, text: "### {{c1}}\n\n" },
    {
      type: "citation",
      block: 1,
      verified: true,
      cited_text: "passage cité du premier document",
      chunk_id: "x-1",
      candidate_id: A.id,
      document_title: "Profession de foi, 1er tour",
      source_url: "https://example.org/a.pdf",
      page_number: 2,
      page_end: null,
    },
    { type: "delta", block: 1, text: "Le programme prévoit une mesure." },
    { type: "delta", block: 2, text: "\n\n### {{c2}}\n\n" },
    {
      type: "citation",
      block: 3,
      verified: false,
      cited_text: "passage non retrouvé",
      chunk_id: "y-1",
      candidate_id: B.id,
      document_title: "Programme",
      source_url: "https://example.org/b.pdf",
      page_number: 5,
      page_end: 6,
    },
    { type: "delta", block: 3, text: `Le programme évoque le sujet, comme ${B.name} l'écrit.` },
    { type: "delta", block: 4, text: `\n\n### {{c3}}\n\n${SILENCE}\n` },
    { type: "done", stop_reason: "end_turn", unverified_citations: 1, neutrality_flags: [] },
  ];
  return events.map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`).join("");
}

/** Intercepte /api/ask : garde les corps envoyés et répond par `reply`. */
async function mockAsk(
  page: Page,
  reply?: (body: Record<string, unknown>, route: Route) => Promise<void>,
) {
  const bodies: Record<string, unknown>[] = [];
  await page.route("**/api/ask", async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>;
    bodies.push(body);
    if (reply) return reply(body, route);
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: sse((body.mode as "rapide" | "approfondi") ?? "rapide"),
    });
  });
  return bodies;
}

async function ask(page: Page, q: string) {
  await page.getByLabel("Votre question").fill(q);
  await page.getByLabel("Votre question").press("Enter");
}

test("question, réponse streamée par candidat dans l'ordre de session, citations", async ({
  page,
  baseURL,
}) => {
  const external: string[] = [];
  page.on("request", (r) => {
    if (!r.url().startsWith(baseURL ?? "http://localhost:3000")) external.push(r.url());
  });
  const bodies = await mockAsk(page);
  await page.goto("/interrogatoire");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Interrogatoire des programmes");
  await expect(page.getByTestId("disclaimer")).toContainText("peuvent contenir des erreurs");

  await ask(page, "Que proposent les candidats sur les retraites ?");
  const answer = page.getByTestId("answer");
  await expect(answer.getByTestId("answer-section")).toHaveCount(3);
  await expect(answer).not.toContainText("{{c");

  // Ordre des sections = ordre des cases à cocher (ordre de session), pas celui du serveur.
  const sessionOrder = await page
    .locator("fieldset")
    .filter({ hasText: "Candidats inclus" })
    .locator("label")
    .allTextContents();
  const expected = sessionOrder.filter((n) => [A.name, B.name, C.name].includes(n));
  await expect(answer.locator("h4")).toHaveText(expected);

  await expect(answer).toContainText(SILENCE);
  await expect(answer.getByRole("link", { name: "Citation 1" })).toBeVisible();
  await expect(answer).toContainText("1 citation(s) non vérifiée(s)");
  const details = answer.locator("details");
  for (let i = 0; i < (await details.count()); i++) await details.nth(i).locator("summary").click();
  await expect(answer.getByText("non vérifiée", { exact: true })).toBeVisible();
  const link = answer.getByRole("link", { name: "(ouvrir le document)" }).first();
  await expect(link).toHaveAttribute("href", /^https:\/\/example\.org\/[ab]\.pdf#page=\d$/);

  expect(bodies[0]).toEqual({
    election_id: "fr-presidentielle-2022",
    question: "Que proposent les candidats sur les retraites ?",
    mode: "rapide",
  });

  // Deuxième question : l'historique part avec les jetons et l'ordre des candidats du meta.
  await ask(page, "Et sur la santé ?");
  await expect(page.getByTestId("turn")).toHaveCount(2);
  await expect(page.getByTestId("answer").nth(1).getByTestId("answer-section")).toHaveCount(3);
  const history = bodies[1]!.history as {
    question: string;
    answer: string;
    candidates: string[];
  }[];
  expect(history).toHaveLength(1);
  expect(history[0]!.candidates).toEqual([A.id, B.id, C.id]);
  expect(history[0]!.answer).toContain("### {{c1}}");

  const r = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  expect(external).toEqual([]);
});

test("mode détaillé envoyé ; plafond du mode atteint : reposer en réponse rapide", async ({
  page,
}) => {
  const bodies = await mockAsk(page, async (body, route) => {
    if (body.mode === "approfondi") {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: "mode_budget_exhausted",
          message:
            "Le mode approfondi a atteint son plafond quotidien : le mode rapide reste disponible.",
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: sse("rapide"),
    });
  });
  await page.goto("/interrogatoire");
  await page.getByLabel("Réponse détaillée").check();
  await ask(page, "Que disent-ils du nucléaire ?");
  await expect(page.getByTestId("turn").getByRole("alert")).toContainText("plafond quotidien");
  expect(bodies[0]!.mode).toBe("approfondi");
  await page.getByRole("button", { name: "Reposer la question en réponse rapide" }).click();
  await expect(page.getByTestId("answer").nth(1).getByTestId("answer-section")).toHaveCount(3);
  expect(bodies[1]).toMatchObject({ mode: "rapide", question: "Que disent-ils du nucléaire ?" });
  await expect(page.getByLabel("Réponse rapide")).toBeChecked();
});

test("filtre de candidats et de thème transmis ; mode aveugle : aucun nom ni lien", async ({
  page,
}) => {
  const bodies = await mockAsk(page);
  await page.goto("/interrogatoire");
  await page.getByRole("button", { name: "Aucun", exact: true }).click();
  for (const c of [A, B, C]) await page.getByLabel(c.name, { exact: true }).check();
  await page.getByLabel("Thème").selectOption("economie");
  await page.getByLabel("Mode aveugle").check();
  await ask(page, "Fiscalité ?");
  const answer = page.getByTestId("answer");
  await expect(answer.getByTestId("answer-section")).toHaveCount(3);
  expect(new Set(bodies[0]!.candidate_ids as string[])).toEqual(new Set([A.id, B.id, C.id]));
  expect(bodies[0]!.theme).toBe("economie");

  const text = (await answer.textContent()) ?? "";
  for (const c of config.candidates) {
    expect(text).not.toContain(c.name);
    expect(text).not.toContain(c.name.split(" ").slice(1).join(" "));
  }
  const details = answer.locator("details");
  for (let i = 0; i < (await details.count()); i++) await details.nth(i).locator("summary").click();
  await expect(answer.getByRole("link", { name: "(ouvrir le document)" })).toHaveCount(0);
  await expect(answer).not.toContainText("passage cité du premier document");
});

test("flux coupé sans événement de fin : réponse signalée comme incomplète", async ({ page }) => {
  await mockAsk(page, async (body, route) => {
    const cut = sse("rapide").split("\n\n").slice(0, 5).join("\n\n") + "\n\n";
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: cut,
    });
  });
  await page.goto("/interrogatoire");
  await ask(page, "Question coupée ?");
  await expect(page.getByTestId("turn").getByRole("alert")).toContainText("peut être incomplète");
  await expect(page.getByText(/Contexte de la question suivante/)).toHaveCount(0);
});

test("mise en avant (PLAN D54) : premier lien de la navigation, encart d'accueil, ancienne adresse redirigée", async ({
  page,
}) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  await expect(nav.getByRole("link").first()).toHaveText("Interrogatoire");
  const callout = page.getByRole("region", { name: "Interrogez les programmes" });
  await expect(callout).toBeVisible();
  await callout.getByRole("link", { name: "Lancer l'interrogatoire" }).click();
  await expect(page).toHaveURL(/\/interrogatoire$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Interrogatoire des programmes");

  await page.goto("/explorer");
  await expect(page).toHaveURL(/\/interrogatoire$/);
});
