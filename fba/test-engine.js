// Rulează: node fba/test-engine.js
const E = require("./engine.js");
const assert = require("assert");
const today = new Date(2026, 10, 23);
const S = { capital: 200, account: "individual" };

// Verde: ROI >= 25%, profit >= 3 €, Amazon absent, beauty cu FDS și expirare bună
const green = E.evaluate({ sell: 29.9, buy: 11.5, refPct: 15, fba: 3.2, sales: 90, sellers: 3, amzAbsent: 80,
  category: "beauty", hazmatOk: true, expiry: "2028-06-01", listingOk: true, isNew: true }, S, today);
console.log("verde net", green.eco.net.toFixed(2), "roi", green.eco.roi.toFixed(3), "qty", green.qty, "limit", green.limits.cap);
assert.ok(green.green, "exemplul verde trebuie să fie verde: " + JSON.stringify(green.fails));
assert.strictEqual(green.limits.cap, 40);        // 20% din 200 €
assert.strictEqual(green.qty, 3);                // floor(40/11.5)

// Roșu: FDS neverificată + Amazon pe listare
const red = E.evaluate({ sell: 19.9, buy: 12.4, refPct: 15, fba: 3.1, sales: 60, sellers: 7, amzAbsent: 30,
  category: "beauty", hazmatOk: false, expiry: "2028-06-01", listingOk: true, isNew: true }, S, today);
assert.ok(!red.green);
assert.ok(red.fails.some(f => f.id === "hazmat") && red.fails.some(f => f.id === "amazon"));

// Plafonul de 300 € și prima comandă de 200 €
assert.strictEqual(E.moneyLimits({ capital: 5000 }, false).cap, 300);
assert.strictEqual(E.moneyLimits({ capital: 5000 }, true).cap, 200);
assert.strictEqual(E.moneyLimits({ capital: 200 }, true).cap, 40);

// Cont Pro: taxa de clôture dispare, apar costurile fixe
const pro = E.evaluate({ sell: 29.9, buy: 11.5, refPct: 15, fba: 3.2, sales: 90, sellers: 3, amzAbsent: 80, category: "toys", listingOk: true, isNew: true }, { capital: 200, account: "pro" }, today);
assert.strictEqual(pro.eco.close, 0);
assert.strictEqual(pro.fixed.total, 46.8);
assert.ok(!pro.coversFixed);                      // 3 buc. × ~5 € nu acoperă 46,80 €

// Categorie blocată
assert.ok(!E.evaluate({ sell: 30, buy: 10, refPct: 15, fba: 3, sales: 90, sellers: 3, amzAbsent: 90, category: "other", listingOk: true, isNew: true }, S, today).green);
console.log("OK: toate testele au trecut");
