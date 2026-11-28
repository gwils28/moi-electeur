import { readFileSync } from "node:fs";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const dir = join(import.meta.dirname, "..", "public", "data", "demo-fictive");
const config = JSON.parse(readFileSync(join(dir, "election_config.json"), "utf-8")) as {
  themes: { id: string; label: string }[];
  candidates: { name: string; party: string; color: string; blind_alias: string }[];
};

async function expectNoAxeViolations(page: Page) {
  const r = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}

const picker = (page: Page) => page.getByRole("group", { name: /Candidats comparés/ });

test("face-à-face, divergences et radar, sans requête après le chargement", async ({ page }) => {
  await page.goto("/positions/comparateur");
  await page.waitForLoadState("networkidle");
  const requests: string[] = [];
  page.on("request", (r) => requests.push(r.url()));

  await expect(
    page.getByRole("heading", { level: 1, name: "Comparateur des programmes" }),
  ).toBeVisible();
  // Deux candidats présélectionnés (les deux premiers de l'ordre aléatoire de session).
  await expect(picker(page).getByRole("checkbox", { checked: true })).toHaveCount(2);
  const face = page.getByTestId("face-to-face");
  await expect(face.locator("tbody tr")).toHaveCount(config.themes.length);
  await expect(face.locator("thead th")).toHaveCount(3);
  await expect(page.getByRole("heading", { name: /Divergences/ })).toBeVisible();

  // Trois au plus : les autres cases se désactivent.
  const unchecked = picker(page).getByRole("checkbox", { checked: false });
  await unchecked.first().check();
  await expect(face.locator("thead th")).toHaveCount(4);
  await expect(picker(page).getByRole("checkbox", { disabled: true })).toHaveCount(
    config.candidates.length - 3,
  );
  await expect(picker(page).getByRole("status")).toContainText("Trois candidats au plus");

  // Moins de deux : le face-à-face disparaît, un message le dit.
  const checked = picker(page).getByRole("checkbox", { checked: true });
  await checked.first().uncheck();
  await checked.first().uncheck();
  await expect(face).toHaveCount(0);
  await expect(picker(page).getByRole("status")).toContainText("au moins deux");

  // Radar : thèmes en lignes, tous les candidats en colonnes, pictogramme et libellé.
  const radar = page.getByTestId("radar");
  await expect(radar.locator("tbody tr")).toHaveCount(config.themes.length);
  await expect(radar.locator("thead th")).toHaveCount(config.candidates.length + 1);
  const cells = radar.locator("tbody button");
  await expect(cells).toHaveCount(config.themes.length * config.candidates.length);
  const chiffre = radar.getByRole("button", { name: /: chiffré\./ }).first();
  await chiffre.click();
  await expect(chiffre).toHaveAttribute("aria-expanded", "true");
  const details = page.getByTestId("radar-details");
  await expect(details.getByRole("heading", { name: /Mesures de/ })).toBeVisible();
  await expect(details).toContainText("d'euros");
  await chiffre.click();
  await expect(details).toHaveCount(0);

  expect(requests).toEqual([]);
});

test("mode aveugle : ni nom, ni parti, ni couleur, ni citation", async ({ page }) => {
  await page.goto("/positions/comparateur");
  await page.getByLabel("Mode aveugle").check();
  await page
    .getByTestId("radar")
    .getByRole("button", { name: /: chiffré\./ })
    .first()
    .click();
  const html = await page.locator("main").innerHTML();
  for (const c of config.candidates) {
    expect(html).not.toContain(c.name);
    expect(html).not.toContain(c.party);
    expect(html.toLowerCase()).not.toContain(c.color.toLowerCase());
    expect(html).toContain(c.blind_alias);
  }
  await expect(page.getByTestId("radar-details")).toContainText("Citation masquée");
});

test("accessibilité (axe) : comparateur, sélection et détail du radar", async ({ page }) => {
  await page.goto("/positions/comparateur");
  await expect(page.getByTestId("radar")).toBeVisible();
  await expectNoAxeViolations(page);
  await page.getByTestId("radar").locator("tbody button").first().click();
  await expectNoAxeViolations(page);
});

test("sous-onglets de Positions (PLAN D55) : tableau complet et comparateur", async ({ page }) => {
  await page.goto("/");
  const main = page.getByRole("navigation", { name: "Navigation principale" });
  await expect(main.getByRole("link", { name: "Comparateur" })).toHaveCount(0);
  await main.getByRole("link", { name: "Positions" }).click();
  await expect(page).toHaveURL(/\/positions$/);
  const tabs = page.getByRole("navigation", { name: "Vues des positions" });
  await expect(tabs.getByRole("link", { name: "Tableau complet" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await tabs.getByRole("link", { name: "Comparateur" }).click();
  await expect(page).toHaveURL(/\/positions\/comparateur$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Comparateur des programmes");
  await expect(tabs.getByRole("link", { name: "Comparateur" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  // L'onglet Positions de l'en-tête reste la page courante.
  await expect(main.getByRole("link", { name: "Positions" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  // Ancienne adresse redirigée.
  await page.goto("/comparateur");
  await expect(page).toHaveURL(/\/positions\/comparateur$/);
});
