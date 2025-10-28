import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AxiosMockAdapter from "axios-mock-adapter";
import axios from "axios";
import { http, provideAuthHooks, setHttpErrorHandler } from "../http";

describe("services/http interceptors", () => {
  let mockInst: AxiosMockAdapter;
  let mockGlobal: AxiosMockAdapter;

  beforeEach(() => {
    // Mock the specific axios instance used by our http client
    mockInst = new AxiosMockAdapter(http);
    // Also mock global axios for fallback refresh (if used)
    mockGlobal = new AxiosMockAdapter(axios);

    provideAuthHooks({
      getAccessToken: () => null,
      refresh: undefined,
      onAuthFail: undefined,
    });
    setHttpErrorHandler(null);
  });

  afterEach(() => {
    mockInst.resetHandlers();
    mockInst.restore();
    mockGlobal.resetHandlers();
    mockGlobal.restore();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("performs single-flight refresh on 401 and replays requests (parallel)", async () => {
    const refreshSpy = vi.fn().mockResolvedValue(undefined);
    provideAuthHooks({ refresh: refreshSpy });

    mockInst.onGet("/v1/data").replyOnce(401);
    mockInst.onGet("/v1/data").replyOnce(401);
    mockInst.onGet("/v1/data").reply(200, { ok: true });

    const p1 = http.get("/v1/data");
    const p2 = http.get("/v1/data");

    const [r1, r2] = await Promise.all([p1, p2]);

    expect(r1.status).toBe(200);
    expect(r2.status).toBe(200);
    expect(refreshSpy).toHaveBeenCalledTimes(1);
  });

  it("calls onAuthFail when refresh fails and rejects the request", async () => {
    const refreshSpy = vi.fn().mockRejectedValue(new Error("refresh failed"));
    const onFail = vi.fn();
    provideAuthHooks({ refresh: refreshSpy, onAuthFail: onFail });

    mockInst.onGet("/secure").replyOnce(401);

    await expect(http.get("/secure")).rejects.toBeTruthy();
    expect(refreshSpy).toHaveBeenCalledTimes(1);
    expect(onFail).toHaveBeenCalledTimes(1);
  });

  it("retries transient 5xx with bounded exponential backoff then succeeds", async () => {
    vi.useFakeTimers();

    mockInst.onGet("/flaky").replyOnce(500);
    mockInst.onGet("/flaky").replyOnce(502);
    mockInst.onGet("/flaky").reply(200, { ok: true });

    const req = http.get("/flaky");

    // Advance timers to pass backoff delays: 1000ms then 2000ms
    await vi.advanceTimersByTimeAsync(1000);
    await vi.advanceTimersByTimeAsync(2000);

    const res = await req;
    expect(res.status).toBe(200);
  });

  it("invokes global error handler on terminal failure (400)", async () => {
    const handler = vi.fn();
    setHttpErrorHandler(handler);

    mockInst.onGet("/bad").reply(400, { error: "bad request" });

    await expect(http.get("/bad")).rejects.toBeTruthy();
    expect(handler).toHaveBeenCalledTimes(1);
  });
});
