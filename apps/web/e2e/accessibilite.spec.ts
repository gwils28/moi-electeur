import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** Audit RGAA (PLAN D46) : points qu'axe-core ne couvre pas, vérifiés sur chaque page. */
const PAGES = [
  { path: "/", h1: "Interrogatoire des programmes", nav: "Interrogatoire" },
  { path: "/boussole", h1: "Boussole électorale", nav: "Boussole" },
  { path: "/positions/comparateur", h1: "Comparateur des programmes", nav: "Positions" },
  { path: "/positions", h1: "Positions des candidats", nav: "Positions" },
  // Méthodologie : dans le pied de page seulement (PLAN D53), aucune entrée courante en tête.
  { path: "/methodologie", h1: "Méthodologie", nav: null },
];

for (const p of PAGES) {
  test(`${p.path} : lien d'évitement, page courante, titre et h1 uniques`, async ({ page }) => {
    await page.goto(p.path);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(p.h1);
    await expect(page.locator("h1")).toHaveCount(1);
    expect(await page.title()).toContain("Moi Électeur");
    // RGAA 12.7 : premier élément atteint au clavier, il mène au contenu.
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Aller au contenu" });
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#contenu")).toBeFocused();
    // RGAA 12.x : page courante signalée dans la navigation.
    const nav = page.getByRole("navigation", { name: "Navigation principale" });
    if (p.nav === null) {
      await expect(nav.locator('[aria-current="page"]')).toHaveCount(0);
      return;
    }
    await expect(nav.getByRole("link", { name: p.nav })).toHaveAttribute("aria-current", "page");
    await expect(nav.locator('[aria-current="page"]')).toHaveCount(1);
  });

  test(`${p.path} : contenu redistribué à 320 px (zoom 400 %), sans défilement horizontal`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto(p.path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("méthodologie publiée : validation en bloc, limites, lien vers la déclaration", async ({
  page,
}) => {
  await page.goto("/methodologie");
  const main = page.locator("main");
  await expect(main).toContainText("validées en bloc");
  await expect(main.getByRole("heading", { name: /Limites et biais connus/ })).toBeVisible();
  await expect(main.locator("table, ul").first()).toBeVisible();
  // PLAN D53 : la méthodologie se trouve dans le pied de page, plus dans l'en-tête.
  await expect(
    page.getByRole("navigation", { name: "Navigation principale" }).getByRole("link", {
      name: "Méthodologie",
    }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("contentinfo").getByRole("link", { name: "Méthodologie" }),
  ).toBeVisible();
  await page.getByRole("contentinfo").getByRole("link", { name: "Accessibilité" }).click();
  await expect(page).toHaveURL(/\/accessibilite$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Accessibilité de Moi Électeur");
  await expect(page.locator("main")).toContainText("Auto-évaluation, non certifiée");
});

for (const path of ["/methodologie", "/accessibilite"]) {
  test(`${path} : axe sans violation`, async ({ page }) => {
    await page.goto(path);
    const r = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  });
}

/** Thème sombre (spec de design G5) : axe, contrastes compris, sur chaque page. */
test.describe("thème sombre", () => {
  test.use({ colorScheme: "dark" });
  for (const path of [
    "/",
    "/boussole",
    "/positions",
    "/positions/comparateur",
    "/methodologie",
    "/accessibilite",
  ]) {
    test(`${path} : axe sans violation en thème sombre`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      const r = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
    });
  }
});
