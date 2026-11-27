import { expect, test } from "@playwright/test";

/** Audit RGAA (PLAN D46) : points qu'axe-core ne couvre pas, vérifiés sur chaque page. */
const PAGES = [
  { path: "/", h1: "Moi Électeur", nav: "Boussole" },
  { path: "/comparateur", h1: "Comparateur des programmes", nav: "Comparateur" },
  { path: "/explorer", h1: "Explorateur des programmes", nav: "Explorateur" },
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
