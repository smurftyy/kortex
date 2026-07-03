/**
 * The 7 boards the Phase 2 scraper actually monitors — slugs must match
 * SCHEMA_kortex.md's `preferences.boards_enabled` default exactly. (The
 * design file showed placeholder boards — LinkedIn/Handshake/Indeed/… —
 * that don't exist in the backend; flagged as a design/contract gap.)
 */
export const BOARDS = [
  { slug: "greenhouse", label: "Greenhouse" },
  { slug: "lever", label: "Lever" },
  { slug: "workable", label: "Workable" },
  { slug: "remoteok", label: "RemoteOK" },
  { slug: "web3career", label: "Web3.career" },
  { slug: "cryptojobslist", label: "CryptoJobsList" },
  { slug: "linkedin", label: "LinkedIn" },
] as const;

export type BoardSlug = (typeof BOARDS)[number]["slug"];

export function boardLabel(slug: string): string {
  return BOARDS.find((b) => b.slug === slug)?.label ?? slug;
}
