---
name: amazon-fba
description: "Amazon FBA business assistant for BFC Marketplace. Covers: product research, listing optimization, SP-API integration, inventory management, PPC campaigns, BSR tracking, keyword research, pricing strategy, supplier sourcing. Builds: dashboards, price trackers, inventory alerts, listing generators, analytics tools, keyword tools, review monitors. Actions: build, create, analyze, optimize, research, track, monitor, generate, automate. Topics: FBA, Amazon Seller Central, SP-API, ASIN, BSR, Buy Box, PPC, A+ Content, Brand Registry, Helium10, Jungle Scout logic."
---

# Amazon FBA Skill — BFC Marketplace

Assistant personnel pour l'aventure Amazon FBA de BFC Marketplace.
Ce skill couvre les aspects **business**, **technique** et **éducatif** du FBA.

---

## Contexte BFC Marketplace

- **Niche**: Beauté, soin personnel, maison, bébés
- **Marché cible**: France + Europe (Amazon.fr, Amazon.de, Amazon.es)
- **Stack tech**: HTML/Tailwind, JavaScript, Node.js
- **Niveau**: Débutant qui apprend — toujours expliquer le POURQUOI

---

## Quand activer ce skill

Activer dès que l'utilisateur mentionne :
- Amazon, FBA, FBM, Seller Central
- ASIN, BSR, Buy Box, listing, PPC
- Produit, sourcing, fournisseur, Alibaba
- Inventaire, stock, expédition, logistique
- Keyword, SEO Amazon, ranking
- Dashboard, tracker, outil Amazon

---

## Règles pédagogiques (IMPORTANT)

L'utilisateur est débutant et veut apprendre. Toujours :

1. **Expliquer les acronymes** la première fois (ex: BSR = Best Seller Rank)
2. **Donner le contexte business** avant le code
3. **Utiliser des analogies simples** pour les concepts complexes
4. **Proposer des étapes progressives** — ne pas tout faire d'un coup
5. **Alerter sur les pièges courants** du FBA (coûts cachés, règles Amazon)

---

## Module 1 — Concepts FBA Essentiels

### Vocabulaire de base

| Terme | Définition | Importance |
|-------|-----------|------------|
| **FBA** | Fulfillment By Amazon — Amazon stocke et expédie | Core |
| **ASIN** | Amazon Standard Identification Number — ID unique produit | Core |
| **BSR** | Best Seller Rank — rang dans la catégorie (plus bas = mieux) | Core |
| **Buy Box** | Le bouton "Ajouter au panier" — crucial pour les ventes | Core |
| **PPC** | Pay Per Click — publicité sponsorisée sur Amazon | Core |
| **MOQ** | Minimum Order Quantity — quantité minimale fournisseur | Sourcing |
| **ROI** | Return on Investment — rentabilité de l'investissement | Finance |
| **COGS** | Cost of Goods Sold — coût de revient produit | Finance |
| **A+ Content** | Pages produit enrichies avec images/tableaux | Listing |
| **Brand Registry** | Protection de marque sur Amazon | Avancé |
| **FBM** | Fulfillment By Merchant — tu expédies toi-même | Alternative |

### Calcul de rentabilité FBA (formule de base)

```
Prix de vente
- Commission Amazon (8-15% selon catégorie)
- Frais FBA (stockage + préparation + expédition)
- Coût produit (COGS)
- Coût publicité PPC (estimer 10-20% au début)
- Autres frais (emballage, étiquettes, retours)
= PROFIT NET
```

**Règle d'or**: Viser minimum 25-30% de marge nette.

### Catégories BFC et commissions Amazon

| Catégorie | Commission Amazon.fr |
|-----------|---------------------|
| Beauté & Soin | 8% |
| Maison | 15% |
| Bébé | 8% |
| Soin personnel | 8% |

---

## Module 2 — Recherche Produit

### Critères d'un bon produit FBA

```
✅ Prix de vente: 20€ - 80€ (sweet spot)
✅ BSR < 50,000 dans la catégorie principale
✅ Moins de 300 avis sur les top 3 concurrents
✅ Poids < 2kg (frais FBA raisonnables)
✅ Pas de saisonnalité forte
✅ Pas de marques dominantes (Nike, L'Oréal...)
✅ Marge nette > 25%
✅ Possibilité d'améliorer le produit existant
```

### Red flags à éviter

```
❌ Produits électroniques complexes
❌ Produits alimentaires / médicaments
❌ Contrefaçons / marques protégées
❌ Produits fragiles (retours élevés)
❌ Marché saturé (1000+ avis sur tous les concurrents)
❌ Prix < 15€ (marges trop faibles après frais)
```

### Workflow de recherche produit

```
1. Identifier une niche (beauté bébé, soin naturel...)
2. Chercher sur Amazon.fr — noter les BSR
3. Analyser les avis négatifs (opportunité d'amélioration)
4. Calculer la rentabilité estimée
5. Vérifier la tendance (Google Trends)
6. Sourcer sur Alibaba.com / 1688.com
7. Commander un échantillon
8. Valider avant de commander en gros
```

---

## Module 3 — Optimisation de Listing

### Structure d'un listing parfait

```
TITRE (200 caractères max):
[Marque] + [Mot-clé principal] + [Bénéfice] + [Caractéristiques] + [Quantité]
Ex: "BFC Lotion Bébé Douce | Hydratation 24h | Peaux Sensibles | Sans Paraben | 200ml"

BULLET POINTS (5 points):
• Point 1: Bénéfice principal (capital letters pour attirer l'oeil)
• Point 2: Caractéristiques techniques
• Point 3: Pour qui c'est fait (target audience)
• Point 4: Différenciation vs concurrents
• Point 5: Garantie / service client

DESCRIPTION:
- Raconte une histoire (problème → solution → bénéfice)
- Inclure mots-clés secondaires naturellement
- 2000 caractères maximum

BACKEND KEYWORDS:
- Mots-clés non visibles, 250 bytes
- Synonymes, fautes courantes, termes alternatifs
```

### Score de listing (checklist)

```
[ ] Titre contient mot-clé principal
[ ] Titre entre 150-200 caractères
[ ] 5 bullet points remplis
[ ] Images: 1 principale blanche + 6 secondaires
[ ] Image lifestyle (produit en utilisation)
[ ] Infographie avec bénéfices
[ ] A+ Content activé (si Brand Registry)
[ ] Prix compétitif vs top 5
[ ] Stock suffisant (éviter rupture)
```

---

## Module 4 — Amazon SP-API (Technique)

### Authentification SP-API

```javascript
// Configuration de base SP-API
const spApiConfig = {
  region: 'eu-west-1', // Europe
  endpoint: 'https://sellingpartnerapi-eu.amazon.com',
  credentials: {
    clientId: process.env.SP_API_CLIENT_ID,
    clientSecret: process.env.SP_API_CLIENT_SECRET,
    refreshToken: process.env.SP_API_REFRESH_TOKEN,
  },
  marketplaceId: {
    'amazon.fr': 'A13V1IB3VIYZZH',
    'amazon.de': 'A1PA6795UKMFR9',
    'amazon.es': 'A1RKKUPIHCS9HS',
    'amazon.it': 'APJ6JRA9NG5V4',
    'amazon.co.uk': 'A1F83G8C2ARO7P',
  }
};
```

### APIs SP-API les plus utiles pour FBA

| API | Usage | Fréquence |
|-----|-------|-----------|
| `Catalog Items` | Infos produit, images, catégories | Recherche produit |
| `Listings Items` | Créer/modifier listings | Gestion catalogue |
| `Orders` | Récupérer commandes | Dashboard ventes |
| `Reports` | Rapports ventes, inventaire, PPC | Analytics |
| `Finances` | Transactions, frais FBA | Comptabilité |
| `FBA Inventory` | Stock en temps réel | Gestion stock |
| `Product Pricing` | Prix compétiteurs, Buy Box | Repricing |
| `Notifications` | Alertes temps réel | Monitoring |

### Rate limits importants

```javascript
// Toujours respecter les rate limits SP-API
const rateLimits = {
  'Catalog Items': { requestsPerSecond: 2, burst: 2 },
  'Orders': { requestsPerSecond: 0.5, burst: 30 },
  'Reports': { requestsPerSecond: 0.0167, burst: 15 }, // 1/min
  'FBA Inventory': { requestsPerSecond: 2, burst: 2 },
};

// Pattern recommandé: retry avec backoff exponentiel
async function apiCallWithRetry(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (err) {
      if (err.status === 429) { // Too Many Requests
        await sleep(Math.pow(2, i) * 1000);
      } else throw err;
    }
  }
}
```

---

## Module 5 — Applications à Construire

### Niveau Débutant

#### 1. Calculateur de rentabilité FBA
```
Input: Prix vente, coût produit, poids, catégorie
Output: Frais FBA estimés, marge nette, ROI
Stack: HTML + JavaScript (pas de backend nécessaire)
Valeur: Utilisé AVANT chaque décision produit
```

#### 2. Générateur de listing optimisé
```
Input: Nom produit, catégories, mots-clés, bénéfices
Output: Titre, bullets, description formatés
Stack: HTML + JS ou Node.js + Claude API
Valeur: Gain de temps énorme sur création de listings
```

#### 3. Tracker de BSR (manuel)
```
Input: ASIN + BSR du jour (saisi manuellement)
Output: Graphique d'évolution sur 30 jours
Stack: HTML + Chart.js + localStorage
Valeur: Comprendre la saisonnalité et tendances
```

### Niveau Intermédiaire

#### 4. Dashboard de ventes SP-API
```
Données: Commandes, revenus, unités vendues
Visualisation: Graphiques jour/semaine/mois
Stack: Node.js + SP-API + Chart.js
Valeur: Vue globale de la performance
```

#### 5. Moniteur Buy Box
```
Fonction: Alerte si tu perds le Buy Box
Fréquence: Check toutes les heures
Stack: Node.js + SP-API + email/SMS alert
Valeur: Réagir vite aux attaques concurrents
```

#### 6. Gestionnaire d'inventaire
```
Fonction: Alertes de réapprovisionnement
Calcul: Jours de stock restants selon vélocité
Stack: Node.js + SP-API + dashboard
Valeur: Éviter les ruptures (pénalité ranking)
```

### Niveau Avancé

#### 7. Outil de recherche produit
```
Fonction: Analyser BSR, estimations ventes, concurrence
Sources: SP-API + scraping Amazon (attention TOS)
Stack: Node.js + SP-API + base de données
Valeur: Remplace partiellement Helium10/Jungle Scout
```

#### 8. Repricer automatique
```
Fonction: Ajuster prix pour gagner le Buy Box
Logique: Si concurrent -0.01€, si marge OK
Stack: Node.js + SP-API + cron job
Valeur: Maximiser Buy Box sans sacrifier marge
```

---

## Module 6 — Stratégie PPC Amazon

### Structure de campagne recommandée

```
CAMPAGNE 1: Auto (découverte de mots-clés)
├── Budget: 10€/jour
├── Bid: Dynamique bas et haut
└── Objectif: Trouver nouveaux keywords

CAMPAGNE 2: Exact (mots-clés performants)
├── Budget: 20€/jour
├── Bid: Manuel, optimiser par keyword
└── Objectif: Ventes rentables

CAMPAGNE 3: Concurrents (ASINs concurrents)
├── Budget: 5€/jour
├── Bid: ASIN targeting
└── Objectif: Voler des clients concurrents
```

### Métriques PPC à surveiller

| Métrique | Formule | Cible |
|----------|---------|-------|
| **ACoS** | Dépenses PPC / Revenus PPC | < 20% |
| **TACoS** | Dépenses PPC / Revenus TOTAUX | < 10% |
| **CTR** | Clics / Impressions | > 0.3% |
| **CVR** | Commandes / Clics | > 10% |
| **CPC** | Dépenses / Clics | Surveiller |

---

## Module 7 — Erreurs de Débutant à Éviter

```
❌ Commander en gros AVANT d'avoir validé le produit
❌ Ignorer les frais FBA dans le calcul de marge
❌ Listing sans optimisation SEO
❌ Pas de photos professionnelles
❌ Ignorer les avis négatifs (y répondre toujours)
❌ Budget PPC sans suivi quotidien
❌ Rupture de stock (perd tout le ranking)
❌ Prix trop bas pour "avoir des ventes" (trap)
❌ Vendre dans une catégorie restreinte sans approval
❌ Ne pas déclarer la TVA européenne (OSS obligatoire)
```

---

## Module 8 — Resources et Outils

### Outils gratuits indispensables

```
• Amazon Seller Central — gestion compte
• Google Trends — saisonnalité produit
• Google Keyword Planner — volume recherche
• Keepa (gratuit limité) — historique prix/BSR
• AMZScout FBA Calculator (extension Chrome) — rentabilité
• SellerApp Free — analyse ASIN basique
```

### Outils payants recommandés (plus tard)

```
• Helium10 — recherche produit + listing + PPC (50€/mois)
• Jungle Scout — recherche produit + fournisseurs (49€/mois)
• Keepa Pro — tracking BSR avancé (17€/mois)
```

### Sites de sourcing

```
• Alibaba.com — fournisseurs internationaux (anglais)
• 1688.com — fournisseurs chinois (moins cher, en chinois)
• Made-in-China.com — alternative Alibaba
• Faire.com — fournisseurs européens
• IndiaMart.com — fournisseurs indiens
```

---

## Workflow complet pour une requête FBA

Quand l'utilisateur demande quelque chose lié au FBA:

### Étape 1: Identifier le besoin
- Business (stratégie, produit, pricing) ?
- Technique (code, API, dashboard) ?
- Éducatif (apprendre, comprendre) ?

### Étape 2: Adapter le niveau
- Toujours commencer par l'explication business
- Puis la solution technique si nécessaire
- Toujours inclure les pièges à éviter

### Étape 3: Livrer avec contexte
- Code commenté et expliqué
- Exemples concrets avec chiffres réels
- Prochaines étapes suggérées

---

## Phrases clés qui activent ce skill

- "produit Amazon", "FBA", "listing", "ASIN"
- "calculer les frais", "marge Amazon"
- "BSR", "Buy Box", "ranking"
- "PPC Amazon", "campagne sponsorisée"
- "SP-API", "Seller Central API"
- "dashboard Amazon", "tracker de ventes"
- "sourcing", "fournisseur", "Alibaba"
- "inventaire", "stock Amazon"
- "avis clients", "review"
- "keyword Amazon", "SEO Amazon"
