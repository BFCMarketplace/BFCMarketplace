/* Cockpit FBA — motorul de reguli (fără DOM, ușor de testat).
 * Modelul de taxe e preluat din SOURCER (calibrat pe deconturile Amazon.fr):
 * comision % din preț + FBA + frais de clôture (0,99 € la cont Individual)
 * + DSF 3% din (comision + FBA + clôture) + TVA 20% pe taxe (franchise en base).
 * La Urssaf: 12,3% din prețul de vânzare, plus CFP 0,1% și CFE pe bucată.
 */
(function (root) {
  "use strict";

  var RULES = {
    minRoi: 0.25,          // ROI minim
    minProfit: 3,          // profit net minim pe bucată (€)
    maxPctCapital: 0.20,   // maxim din capital pe un produs
    maxPerProduct: 300,    // plafon absolut pe produs (€)
    firstOrderMax: 200,    // prima comandă la produs nou (€)
    minAmazonAbsent: 50,   // % din ultimele 90 zile cu Amazon absent
    minExpiryDays: 180,    // zile rămase până la expirare (beauty); ajustabil
    stressDrop: 0.10,      // scădere de preț la care profitul nu are voie să fie negativ
    urssafPct: 0.123,
    cfpPct: 0.001,
    dsfPct: 0.03,
    vatPct: 0.20,
    individualClosingFee: 0.99
  };

  var CATEGORIES = [
    { id: "beauty", label: "Beauty", strict: true },
    { id: "toys", label: "Jucării", strict: false },
    { id: "home", label: "Casă și bucătărie", strict: false },
    { id: "sport", label: "Sport", strict: false },
    { id: "other", label: "Altă categorie", strict: false, blocked: true }
  ];

  var DEFAULT_SETTINGS = {
    capital: 200,
    account: "individual",   // "individual" | "pro"
    proFee: 46.8,            // 39 € + TVA nerecuperabilă; de verificat în Seller Central
    keepa: 0,
    hosting: 0,
    otherFixed: 0,
    cfeYear: 0,              // CFE anual estimat (prima an de obicei scutit; de verificat)
    unitsYear: 300           // câte bucăți estimezi pe an, ca să împarți CFE
  };

  function num(v) { var n = parseFloat(String(v).replace(",", ".")); return isFinite(n) ? n : 0; }

  /** Taxe și profit pentru un preț de vânzare dat. */
  function economics(p, s, sellPrice) {
    var sell = sellPrice;
    var buy = num(p.buy);
    var close = s.account === "individual" ? RULES.individualClosingFee : 0;
    var referral = sell * num(p.refPct) / 100;
    var fba = num(p.fba);
    var dsf = (referral + fba + close) * RULES.dsfPct;
    var feesBase = referral + fba + close + dsf;
    var feesVat = feesBase * RULES.vatPct;
    var urssaf = sell * RULES.urssafPct;
    var cfp = sell * RULES.cfpPct;
    var cfe = num(s.unitsYear) > 0 ? num(s.cfeYear) / num(s.unitsYear) : 0;
    var net = sell - buy - feesBase - feesVat - urssaf - cfp - cfe;
    return {
      sell: sell, buy: buy, referral: referral, fba: fba, close: close, dsf: dsf,
      feesVat: feesVat, urssaf: urssaf, cfp: cfp, cfe: cfe, net: net,
      roi: buy > 0 ? net / buy : 0
    };
  }

  function fixedCosts(s) {
    var amazon = s.account === "pro" ? num(s.proFee) : 0;
    return {
      amazon: amazon, keepa: num(s.keepa), hosting: num(s.hosting), other: num(s.otherFixed),
      total: amazon + num(s.keepa) + num(s.hosting) + num(s.otherFixed)
    };
  }

  function moneyLimits(s, isNew) {
    var perProduct = Math.min(num(s.capital) * RULES.maxPctCapital, RULES.maxPerProduct);
    var cap = isNew ? Math.min(perProduct, RULES.firstOrderMax) : perProduct;
    return { perProduct: perProduct, cap: cap };
  }

  function daysUntil(dateStr, today) {
    if (!dateStr) return null;
    var d = new Date(dateStr + "T00:00:00");
    if (isNaN(d.getTime())) return null;
    var t = today || new Date();
    var t0 = new Date(t.getFullYear(), t.getMonth(), t.getDate());
    return Math.ceil((d.getTime() - t0.getTime()) / 86400000);
  }

  function evaluate(p, s, today) {
    s = Object.assign({}, DEFAULT_SETTINGS, s || {});
    var sell = num(p.sell), buy = num(p.buy);
    var base = economics(p, s, sell);
    var stress = economics(p, s, sell * (1 - RULES.stressDrop));
    var cat = CATEGORIES.filter(function (c) { return c.id === p.category; })[0] || CATEGORIES[4];

    var share = num(p.sales) / (num(p.sellers) + 1);
    var qtySpeed = Math.floor(share);
    var lim = moneyLimits(s, !!p.isNew);
    var qtyMoney = buy > 0 ? Math.floor(lim.cap / buy) : 0;
    var qty = Math.max(0, Math.min(qtySpeed, qtyMoney));
    var days = daysUntil(p.expiry, today);
    var fixed = fixedCosts(s);

    var checks = [];
    function add(id, label, ok, detail) { checks.push({ id: id, label: label, ok: !!ok, detail: detail }); }

    add("profit", "Profit net minim", base.roi >= RULES.minRoi && base.net >= RULES.minProfit,
      "ROI " + Math.round(base.roi * 100) + "% (minim 25%) și " + base.net.toFixed(2).replace(".", ",") + " € pe bucată (minim 3 €)");
    add("stress", "Rezistă la −10% preț", stress.net >= 0,
      "La " + stress.sell.toFixed(2).replace(".", ",") + " € profitul e " + stress.net.toFixed(2).replace(".", ",") + " €");
    add("speed", "Viteză", qtySpeed >= 1,
      "Partea ta: " + share.toFixed(1).replace(".", ",") + " buc. pe 30 zile (" + num(p.sales) + " vânzări ÷ " + (num(p.sellers) + 1) + ")");
    add("money", "Bani", qtyMoney >= 1,
      "Plafon " + lim.cap.toFixed(2).replace(".", ",") + " €" + (p.isNew ? " (produs nou)" : "") + " = " + qtyMoney + " buc. la " + buy.toFixed(2).replace(".", ",") + " €");
    add("amazon", "Amazon pe listare", num(p.amzAbsent) > RULES.minAmazonAbsent,
      "Absent " + num(p.amzAbsent) + "% din ultimele 90 zile (minim peste 50%)");
    add("category", "Categorie", !cat.blocked,
      cat.blocked ? "În afara beauty, jucării, casă, sport" : cat.label);
    if (cat.strict) {
      add("hazmat", "Hazmat / FDS verificat", !!p.hazmatOk,
        p.hazmatOk ? "Fișa FDS verificată" : "Neverificat: risc de blocare la FBA ca marfă periculoasă");
      add("expiry", "Data de expirare", days !== null && days >= RULES.minExpiryDays,
        days === null ? "Lipsește data de expirare" : days + " zile rămase (minim " + RULES.minExpiryDays + ")");
    }
    add("listing", "Listare curată", !!p.listingOk,
      p.listingOk ? "Titlu, descriere și poze despre același produs" : "Neverificat: titlul, descrierea și pozele trebuie să fie despre același produs");

    var fails = checks.filter(function (c) { return !c.ok; });
    var green = fails.length === 0 && qty >= 1;

    var monthlyProfit = qty * base.net;
    return {
      eco: base, stress: stress, checks: checks, fails: fails, green: green,
      qty: qty, qtySpeed: qtySpeed, qtyMoney: qtyMoney, share: share, limits: lim,
      fixed: fixed,
      breakEvenUnits: base.net > 0 ? Math.ceil(fixed.total / base.net) : null,
      monthlyProfit: monthlyProfit,
      coversFixed: fixed.total === 0 || monthlyProfit >= fixed.total
    };
  }

  var api = { RULES: RULES, CATEGORIES: CATEGORIES, DEFAULT_SETTINGS: DEFAULT_SETTINGS, evaluate: evaluate, economics: economics, fixedCosts: fixedCosts, moneyLimits: moneyLimits, daysUntil: daysUntil, num: num };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FBAEngine = api;
})(typeof window !== "undefined" ? window : this);
