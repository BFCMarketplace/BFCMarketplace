import { z } from "zod";

export const CATEGORIES = ["saas", "ecommerce", "services", "content", "local", "other"] as const;
export const STATUSES = ["active", "paused", "archived"] as const;

const list = (v: unknown) =>
  String(v ?? "").split(",").map((s) => s.trim()).filter(Boolean);

export const projectSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(120),
  url: z.string().trim().transform((v) => (/^https?:\/\//i.test(v) ? v : `https://${v}`))
    .pipe(z.url("Enter a valid URL"))
    .transform((v) => new URL(v).origin),
  description: z.string().trim().max(2000).default(""),
  category: z.enum(CATEGORIES),
  market: z.string().trim().max(200).default(""),
  languages: z.preprocess(list, z.array(z.string().regex(/^[a-z]{2}(-[A-Za-z]{2})?$/, "Languages must be codes like fr, en, ro-RO")).max(20)),
  countries: z.preprocess(list, z.array(z.string().regex(/^[A-Za-z]{2}$/, "Countries must be 2-letter codes like FR")).max(50))
    .transform((a) => a.map((c) => c.toUpperCase())),
  monthly_budget_eur: z.coerce.number().min(0).max(100000),
});

export type ProjectInput = z.infer<typeof projectSchema>;
