import { describe, it, expect, vi, afterEach } from "vitest";
import { getExercises } from "./api";

describe("api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getExercises builds query string and returns JSON", async () => {
    const mockData = [
      { id: 1, name: "Squat", muscle_group: "Legs", equipment: "Barbell", type: "strength" },
    ];

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue({ ok: true, json: async () => mockData } as any);

    const res = await getExercises({ q: "squat", type: "strength" });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const url = fetchSpy.mock.calls[0][0] as string;
    expect(url).toContain("/api/exercises");
    expect(url).toContain("q=squat");
    expect(url).toContain("type=strength");
    expect(res).toEqual(mockData);
  });

  it("getExercises omits empty params and throws on error with detail", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Bad Request" }),
      text: async () => "Bad Request",
    } as any);

    await expect(getExercises({ q: "" as any, type: "strength" })).rejects.toThrow("Bad Request");

    // Verify url doesn't include empty q
    const url = fetchSpy.mock.calls[0][0] as string;
    expect(url).not.toMatch(/[?&]q=/);
    expect(url).toContain("type=strength");
  });

  it("handles non-JSON error body by using text", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 502,
      text: async () => "Upstream error",
    } as any);

    await expect(getExercises({ type: "strength" })).rejects.toThrow("Upstream error");
  });

  it("handles JSON error without 'detail' by keeping raw JSON text", async () => {
    const body = JSON.stringify({ error: "X", message: "no detail field" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => body,
    } as any);

    await expect(getExercises({ type: "strength" })).rejects.toThrow(body);
  });
});
