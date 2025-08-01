import { Mask } from "../store/mask";
import { logger } from "@/app/utils/logger";

import { type BuiltinMask } from "./typing";
export { type BuiltinMask } from "./typing";

export const BUILTIN_MASK_ID = 100000;

export const BUILTIN_MASK_STORE = {
  buildinId: BUILTIN_MASK_ID,
  masks: {} as Record<string, BuiltinMask>,
  get(id?: string) {
    if (!id) return undefined;
    return this.masks[id] as Mask | undefined;
  },
  add(m: BuiltinMask) {
    const mask = { ...m, id: this.buildinId++, builtin: true };
    this.masks[mask.id] = mask;
    return mask;
  },
};

export const BUILTIN_MASKS: BuiltinMask[] = [];

if (typeof window != "undefined") {
  // run in browser skip in next server
  fetch("/masks.json")
    .then((res) => res.json())
    .catch((error) => {
      logger.error("[Fetch] failed to fetch masks", error);
      return { cn: [], en: [] };
    })
    .then((masks) => {
      const { cn = [], en = [] } = masks;
      return [...cn, ...en].map((m) => {
        BUILTIN_MASKS.push(BUILTIN_MASK_STORE.add(m));
      });
    });
}
