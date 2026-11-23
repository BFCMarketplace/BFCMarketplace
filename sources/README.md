# Surse vechi (doar referință)

- `actoriosuppliers/index.html` — SOURCER, terminal de sourcing FBA (copie a paginii publicate pe Netlify).
  Conține modelul de taxe Amazon.fr (computeMargin) preluat în `fba/engine.js`, plus integrarea Keepa prin
  funcții Netlify (`/.netlify/functions/keepa`, `/seller`, `/find-suppliers`) și istoric în Supabase.
  Funcțiile Netlify NU sunt în această copie: lipsesc din repo.
- `amazontool` (Vite, build compilat) nu are sursă utilă în pagina publicată; sursa trebuie luată de pe laptop.
- Atenție: dacă Netlify publică rădăcina acestui repo, `sources/` devine public. Mută-l în afara folderului publicat sau exclude-l.
