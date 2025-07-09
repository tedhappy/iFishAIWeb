import fs from "fs";
import path from "path";
import { CN_MASKS } from "./cn";
import { logger } from "@/app/utils/logger";

import { type BuiltinMask } from "./typing";

// 移除英文面具支持
const BUILTIN_MASKS: Record<string, BuiltinMask[]> = {
  cn: CN_MASKS,
};

const dirname = path.dirname(__filename);

fs.writeFile(
  dirname + "/../../public/masks.json",
  JSON.stringify(BUILTIN_MASKS, null, 4),
  function (error) {
    if (error) {
      logger.error("[Build] failed to build masks", error);
    }
  },
);
