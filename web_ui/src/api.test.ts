import { describe, expect, it } from "vitest";
import { parseSSE } from "./api";

describe("parseSSE", () => {
  it("按空行拆出 data 行", () => {
    const { events, rest } = parseSSE(
      'data: {"a":1}\n\ndata: [DONE]\n\n',
    );
    expect(events).toEqual(['{"a":1}', "[DONE]"]);
    expect(rest).toBe("");
  });

  it("不完整块留在 rest,跨包拼接", () => {
    const first = parseSSE("data: hel");
    expect(first.events).toEqual([]);
    expect(first.rest).toBe("data: hel");
    const second = parseSSE(first.rest + "lo\n\n");
    expect(second.events).toEqual(["data: hel".slice(6) + "lo"]);
  });

  it("忽略非 data 行", () => {
    const { events } = parseSSE(": comment\nevent: x\ndata: ok\n\n");
    expect(events).toEqual(["ok"]);
  });
});
