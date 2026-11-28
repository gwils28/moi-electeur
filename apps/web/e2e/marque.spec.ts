import { expect, test } from "@playwright/test";

/** Logo dans l'en-tête et favicon (docs/notes-implementation.md, section logo). */
test("en-tête : logo cliquable vers l'accueil, alternative textuelle explicite", async ({
  page,
}) => {
  await page.goto("/methodologie");
  const banner = page.getByRole("banner");
  const logo = banner.getByRole("link", { name: "Moi Électeur, accueil" });
  await expect(logo).toBeVisible();
  // Symbole et logotype réellement chargés (pas d'icône cassée).
  const images = logo.locator("img");
  await expect(images).toHaveCount(2);
  for (const img of await images.all()) {
    const loaded = await img.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth > 0);
    expect(loaded).toBe(true);
  }
  // La navigation principale reste dans l'en-tête.
  await expect(banner.getByRole("navigation", { name: "Navigation principale" })).toBeVisible();
  await logo.click();
  await expect(page).toHaveURL(/\/$/);
});

test("favicons déclarés et servis (PNG, ICO, Apple)", async ({ page, request }) => {
  await page.goto("/");
  const checks: [string, string][] = [
    ['link[rel="icon"][type="image/png"]', "image/png"],
    ['link[rel="icon"][href*="favicon.ico"]', "image/x-icon"],
    ['link[rel="apple-touch-icon"]', "image/png"],
  ];
  for (const [selector, type] of checks) {
    const href = await page.locator(selector).first().getAttribute("href");
    expect(href, selector).toBeTruthy();
    const res = await request.get(href!);
    expect(res.status(), selector).toBe(200);
    expect(res.headers()["content-type"], selector).toContain(type);
  }
});
