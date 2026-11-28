import { expect, test } from "@playwright/test";

/** En-têtes de sécurité (PLAN D49) : CSP stricte à nonce, sans `unsafe-inline` pour les scripts. */
const PAGES = ["/", "/comparateur", "/positions", "/explorer", "/methodologie", "/accessibilite"];

function directive(csp: string, name: string): string {
  return (
    csp
      .split(";")
      .map((d) => d.trim())
      .find((d) => d.startsWith(`${name} `)) ?? ""
  );
}

for (const path of PAGES) {
  test(`${path} : CSP stricte, aucune violation, page fonctionnelle`, async ({ page }) => {
    const violations: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error" && /Content Security Policy|Content-Security-Policy/i.test(m.text()))
        violations.push(m.text());
    });
    const res = await page.goto(path);
    const csp = res!.headers()["content-security-policy"] ?? "";
    const scripts = directive(csp, "script-src");
    expect(scripts).toMatch(/'nonce-[A-Za-z0-9+/=]+'/);
    expect(scripts).toContain("'strict-dynamic'");
    expect(scripts).not.toContain("unsafe-inline");
    expect(scripts).not.toContain("unsafe-eval");
    for (const d of [
      "object-src 'none'",
      "base-uri 'none'",
      "frame-ancestors 'none'",
      "connect-src 'self'",
    ])
      expect(csp).toContain(d);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(violations).toEqual([]);
  });
}

test("nonce renouvelé à chaque requête", async ({ request }) => {
  const nonce = async () =>
    /'nonce-([^']+)'/.exec(
      (await request.get("/")).headers()["content-security-policy"] ?? "",
    )?.[1];
  const [a, b] = [await nonce(), await nonce()];
  expect(a).toBeTruthy();
  expect(a).not.toBe(b);
});

test("boussole hydratée sous CSP : le questionnaire démarre", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Commencer le questionnaire" }).click();
  await expect(page.locator("fieldset").first()).toBeVisible();
});
