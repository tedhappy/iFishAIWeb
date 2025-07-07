import { isModelNotavailableInServer } from "../app/utils/model";

describe("isModelNotavailableInServer", () => {
  test("test model will return false, which means the model is available", () => {
    const customModels = "";
    const modelName = "qwen-turbo-latest";
    const providerNames = "Alibaba";
    const result = isModelNotavailableInServer(
      customModels,
      modelName,
      providerNames,
    );
    expect(result).toBe(false);
  });

  test("test model will return true when model is not available in custom models", () => {
    const customModels = "-all,qwen-turbo-latest";
    const modelName = "qwen-plus";
    const providerNames = "Alibaba";
    const result = isModelNotavailableInServer(
      customModels,
      modelName,
      providerNames,
    );
    expect(result).toBe(true);
  });

  test("should respect DISABLE_GPT4 setting", () => {
    process.env.DISABLE_GPT4 = "1";
    const result = isModelNotavailableInServer("", "gpt-4", "Azure");
    expect(result).toBe(true);
  });

  test("should handle empty provider names", () => {
    const result = isModelNotavailableInServer("-all,qwen-turbo-latest", "qwen-turbo-latest", "");
    expect(result).toBe(true);
  });

  test("should be case insensitive for model names", () => {
    const result = isModelNotavailableInServer("-all,QWEN-TURBO-LATEST", "qwen-turbo-latest", "Alibaba");
    expect(result).toBe(true);
  });

  test("support passing multiple providers, model unavailable on one of the providers will return true", () => {
    const customModels = "-all,qwen-turbo-latest@google";
    const modelName = "qwen-turbo-latest";
    const providerNames = ["Alibaba", "Azure"];
    const result = isModelNotavailableInServer(
      customModels,
      modelName,
      providerNames,
    );
    expect(result).toBe(true);
  });

  // FIXME: 这个测试用例有问题，需要修复
  //   test("support passing multiple providers, model available on one of the providers will return false", () => {
  //     const customModels = "-all,gpt-4@google";
  //     const modelName = "gpt-4";
  //     const providerNames = ["OpenAI", "Google"];
  //     const result = isModelNotavailableInServer(
  //       customModels,
  //       modelName,
  //       providerNames,
  //     );
  //     expect(result).toBe(false);
  //   });

  test("test custom model without setting provider", () => {
    const customModels = "-all,mistral-large";
    const modelName = "mistral-large";
    const providerNames = modelName;
    const result = isModelNotavailableInServer(
      customModels,
      modelName,
      providerNames,
    );
    expect(result).toBe(false);
  });
});
