import { readFileSync } from "node:fs";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** Matrice des positions (PLAN D52), sur la démo fictive (élection par défaut des tests). */
const dir = join(import.meta.dirname, "..", "public", "data", "demo-fictive");
const read = (f: string) => JSON.parse(readFileSync(join(dir, f), "utf-8"));
const config = read("election_config.json") as {
  themes: { id: string; label: string }[];
  candidates: { name: string; party: string }[];
};
const statements = (read("statements.json") as { statements: { id: string; theme: string }[] })
  .statements;

test("matrice complète, filtre par thème, détail avec citations, sans requête", async ({
  page,
}) => {
  await page.goto("/positions");
  await page.waitForLoadState("networkidle");
  const requests: string[] = [];
  page.on("request", (r) => requests.push(r.url()));

  await expect(
    page.getByRole("heading", { level: 1, name: "Positions des candidats" }),
  ).toBeVisible();
  const table = page.getByTestId("positions");
  // Une colonne par candidat, une ligne par affirmation, un intertitre par thème.
  await expect(table.locator("thead th")).toHaveCount(config.candidates.length + 1);
  await expect(table.locator('tbody th[scope="row"]')).toHaveCount(statements.length);
  await expect(table.locator('tbody th[scope="colgroup"]')).toHaveCount(config.themes.length);
  await expect(table.locator("tbody button")).toHaveCount(
    statements.length * config.candidates.length,
  );

  // Filtre : un seul thème.
  const theme = config.themes[1]!;
  await page.getByLabel("Thème affiché").selectOption(theme.id);
  await expect(table.locator('tbody th[scope="colgroup"]')).toHaveText([theme.label]);
  await expect(table.locator('tbody th[scope="row"]')).toHaveCount(
    statements.filter((s) => s.theme === theme.id).length,
  );

  // Détail : libellé complet et citation attribuée au programme.
  const cell = table.getByRole("button", { name: /Plutôt pour \(\+1\)|S'engage pour/ }).first();
  await cell.click();
  await expect(cell).toHaveAttribute("aria-expanded", "true");
  const details = page.getByTestId("position-details");
  await expect(details).toBeVisible();
  await expect(details.locator("blockquote").first()).toContainText("Programme de");
  await details.getByRole("button", { name: "Fermer le détail" }).click();
  await expect(details).toHaveCount(0);

  expect(requests).toEqual([]);
});

test("sélection des candidats : un, plusieurs, tous ou aucun", async ({ page }) => {
  await page.goto("/positions");
  const table = page.getByTestId("positions");
  const picker = page.getByRole("group", { name: "Candidats affichés" });
  const status = picker.getByRole("status");
  const n = config.candidates.length;
  await expect(picker.getByRole("checkbox", { checked: true })).toHaveCount(n);
  await expect(status).toContainText(`Tous les candidats affichés (${n})`);

  // Aucun : le tableau disparaît, un message le dit.
  await picker.getByRole("button", { name: "Aucun" }).click();
  await expect(table).toHaveCount(0);
  await expect(status).toContainText("au moins un candidat");

  // Un seul candidat, puis deux : une colonne par candidat coché.
  const boxes = picker.getByRole("checkbox");
  await boxes.nth(0).check();
  await expect(status).toContainText(`1 candidat affiché sur ${n}`);
  await expect(table.locator("thead th")).toHaveCount(2);
  await expect(table.locator("tbody button")).toHaveCount(statements.length);
  await boxes.nth(3).check();
  await expect(table.locator("thead th")).toHaveCount(3);
  await expect(status).toContainText(`2 candidats affichés sur ${n}`);

  // Le détail d'un candidat retiré se ferme.
  await table.locator("tbody button").first().click();
  await expect(page.getByTestId("position-details")).toBeVisible();
  await boxes.nth(0).uncheck();
  await expect(page.getByTestId("position-details")).toHaveCount(0);

  // Tous : retour au tableau complet.
  await picker.getByRole("button", { name: "Tous" }).click();
  await expect(table.locator("thead th")).toHaveCount(n + 1);
});

test("mode aveugle : ni nom, ni parti, ni citation", async ({ page }) => {
  await page.goto("/positions");
  const table = page.getByTestId("positions");
  await expect(table.locator("thead")).toContainText(config.candidates[0]!.name);
  await page.getByLabel(/Mode aveugle/).check();
  const header = table.locator("thead");
  for (const c of config.candidates) {
    await expect(header).not.toContainText(c.name);
    await expect(header).not.toContainText(c.party);
  }
  await table.locator("tbody button").first().click();
  const details = page.getByTestId("position-details");
  await expect(details.locator("blockquote")).toHaveCount(0);
});

test("accessibilité (axe) : matrice et détail ouvert", async ({ page }) => {
  await page.goto("/positions");
  await page.getByTestId("positions").locator("tbody button").first().click();
  await expect(page.getByTestId("position-details")).toBeVisible();
  const r = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
});

test("cellule utilisable au clavier", async ({ page }) => {
  await page.goto("/positions");
  const first = page.getByTestId("positions").locator("tbody button").first();
  await first.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("position-details")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("position-details")).toHaveCount(0);
});
