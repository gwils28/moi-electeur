import { readFileSync } from "node:fs";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const config = JSON.parse(
  readFileSync(
    join(import.meta.dirname, "..", "public", "data", "demo-fictive", "election_config.json"),
    "utf-8",
  ),
) as {
  themes: { id: string }[];
  candidates: { name: string; party: string; color: string; blind_alias: string }[];
};

const LIKERT = [
  "Pas du tout d'accord",
  "Plutôt pas d'accord",
  "Neutre",
  "Plutôt d'accord",
  "Tout à fait d'accord",
];

/** Répond à tout le questionnaire (réponses variées, une « Sans avis ») et affiche les résultats. */
async function answerAll(page: Page) {
  await page.getByRole("button", { name: "Commencer le questionnaire" }).click();
  let k = 0;
  for (let t = 0; t < config.themes.length; t++) {
    const groups = page.locator("fieldset");
    const n = await groups.count();
    for (let i = 0; i < n; i++) {
      const label = k === 3 ? "Sans avis" : LIKERT[(k * 3) % 5]!;
      await groups.nth(i).getByText(label, { exact: true }).click();
      k++;
    }
    const last = t === config.themes.length - 1;
    await page.getByRole("button", { name: last ? "Voir les résultats" : "Thème suivant" }).click();
  }
  await expect(page.getByRole("heading", { name: "Vos résultats" })).toBeVisible();
}

async function expectNoAxeViolations(page: Page) {
  const r = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}

test("parcours complet sans aucune requête réseau après le chargement", async ({ page }) => {
  await page.goto("/boussole");
  await page.waitForLoadState("networkidle");
  const requests: string[] = [];
  page.on("request", (r) => requests.push(r.url()));

  await answerAll(page);
  const items = page.getByTestId("proximity-list").locator("li");
  await expect(items).toHaveCount(config.candidates.length);
  await expect(page.getByTestId("user-point")).toBeVisible();
  // Couverture explicite (backtest M4 : proximité moins fiable sur peu d'affirmations communes).
  await expect(page.getByTestId("coverage").first()).toContainText(
    /calculée sur \d+ de vos \d+ réponses/,
  );
  await expect(page.getByTestId("position-text")).toContainText("Votre position");

  await items.first().getByRole("button").click();
  await expect(page.getByRole("heading", { name: /Comparaison avec/ })).toBeVisible();
  await expect(page.getByTestId("agreements")).toBeVisible();

  await page.getByLabel("Analyse factorielle (B)").check();
  await expect(page.getByTestId("pca-info")).toContainText("variance");

  expect(requests).toEqual([]);
});

test("mode aveugle : aucun nom ni parti dans la page", async ({ page }) => {
  await page.goto("/boussole");
  await answerAll(page);
  await page.getByLabel("Mode aveugle").check();
  await page.getByTestId("proximity-list").locator("li").first().getByRole("button").click();
  const html = await page.locator("main").innerHTML();
  for (const c of config.candidates) {
    expect(html).not.toContain(c.name);
    expect(html).not.toContain(c.party);
    expect(html.toLowerCase()).not.toContain(c.color.toLowerCase());
    expect(html).toContain(c.blind_alias);
  }
  expect(html).not.toContain("Extrait fictif");
  await expect(page.getByText(/Citation masquée en mode aveugle/).first()).toBeVisible();
  await page.getByRole("button", { name: "Révéler les candidats" }).click();
  await expect(page.locator("main")).toContainText(config.candidates[0]!.name);
});

test("« Et si » : trace animée et variation de proximité", async ({ page }) => {
  await page.goto("/boussole");
  await answerAll(page);
  await page.getByText("Et si… ?").click();
  await page.getByTestId("whatif-s01").selectOption("-2");
  await page.getByTestId("whatif-s02").selectOption("2");
  await expect(page.getByTestId("whatif-trace")).toBeAttached();
  await expect(page.getByTestId("delta").first()).toBeVisible();
});

test("lien #r= : reprise des résultats, fragment jamais envoyé au serveur", async ({
  page,
  context,
}) => {
  await page.goto("/boussole");
  await answerAll(page);
  const url = await page.getByTestId("share-url").inputValue();
  expect(url).toMatch(/#r=1[a-en]+\.[1-3]+$/);
  const first = await page.getByTestId("proximity-list").innerText();

  const other = await context.newPage();
  const sent: string[] = [];
  other.on("request", (r) => sent.push(r.url()));
  await other.goto(url);
  await expect(other.getByRole("heading", { name: "Vos résultats" })).toBeVisible();
  // Même ensemble de scores (l'ordre aléatoire peut différer entre pages).
  const scores = (t: string) => (t.match(/\d+ %/g) ?? []).sort();
  expect(scores(await other.getByTestId("proximity-list").innerText())).toEqual(scores(first));
  for (const u of sent) expect(u).not.toContain("r=1");
});

test("lien #r= invalide : questionnaire vierge et message", async ({ page }) => {
  await page.goto("/boussole#r=9zz");
  await expect(page.getByRole("status")).toContainText("invalide");
  await expect(page.getByRole("button", { name: "Commencer le questionnaire" })).toBeVisible();
});

test("sauvegarde locale désactivée par défaut, active sur demande", async ({ page }) => {
  await page.goto("/boussole");
  await answerAll(page);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  await page.getByLabel("Sauvegarder mes réponses sur cet appareil").check();
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual(["moi-electeur:reponses"]);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Vos résultats" })).toBeVisible();
});

test("accessibilité (axe) : accueil, questionnaire, résultats, panneau, mode aveugle", async ({
  page,
}) => {
  await page.goto("/boussole");
  await expectNoAxeViolations(page);
  await page.getByRole("button", { name: "Commencer le questionnaire" }).click();
  await expectNoAxeViolations(page);
  await page.getByRole("button", { name: "Thème précédent" }).isDisabled();
  await page.goto("/boussole");
  await answerAll(page);
  await expectNoAxeViolations(page);
  await page.getByTestId("proximity-list").locator("li").first().getByRole("button").click();
  await page.getByLabel("Mode aveugle").check();
  await expectNoAxeViolations(page);
});

test("questionnaire utilisable au clavier", async ({ page }) => {
  await page.goto("/boussole");
  await page.getByRole("button", { name: "Commencer le questionnaire" }).focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab"); // sélecteur de poids
  await page.keyboard.press("Tab"); // premier groupe radio
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("fieldset").first().locator("input:checked")).toHaveCount(1);
});

test("mode aveugle : alias non liés à l'ordre du fichier de configuration", async ({ browser }) => {
  // Sur plusieurs sessions, l'alias « A » ne désigne pas toujours le même candidat.
  const seen = new Set<string>();
  for (let i = 0; i < 6; i++) {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto("/boussole");
    await answerAll(page);
    await page.getByLabel("Mode aveugle").check();
    await page.getByRole("button", { name: config.candidates[0]!.blind_alias }).first().click();
    await page.getByRole("button", { name: "Révéler les candidats" }).click();
    seen.add(await page.locator("#panel-title").innerText());
    await ctx.close();
  }
  expect(seen.size).toBeGreaterThan(1);
});
