import { describe, expect, it, beforeEach, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import Run from "../views/Run.vue";

const { apiGet, apiPost, messageSuccess, messageError, messageWarning } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  messageSuccess: vi.fn(),
  messageError: vi.fn(),
  messageWarning: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    get: apiGet,
    post: apiPost,
  },
}));

vi.mock("vue-router", () => ({
  RouterLink: { template: "<a><slot /></a>" },
  useRouter: () => ({
    currentRoute: { value: { query: {} } },
    push: vi.fn(),
  }),
}));

vi.mock("naive-ui", () => ({
  useDialog: () => ({ warning: vi.fn() }),
  useMessage: () => ({
    success: messageSuccess,
    error: messageError,
    warning: messageWarning,
  }),
}));

const codexToken = {
  id: 1,
  email_masked: "c***@example.com",
  account_id_masked: "acct_***123",
  has_id_token: true,
  has_access_token: true,
  has_refresh_token: true,
  scope: "openid profile email",
  created_at: 1710000000,
};

function mockApi() {
  apiGet.mockImplementation((url: string) => {
    if (url === "/codex-tokens") {
      return Promise.resolve({ data: { items: [codexToken] } });
    }
    if (url === "/codex-tokens/1/export") {
      return Promise.resolve({
        data: {
          auth_json: '{"id_token":"RAW_ID_TOKEN","access_token":"RAW_ACCESS_TOKEN","refresh_token":"RAW_REFRESH_TOKEN"}',
          filename: "codex-auth-1.json",
        },
      });
    }
    if (url === "/run/status") {
      return Promise.resolve({ data: { running: false, last_returncode: null, started_at: null, finished_at: null } });
    }
    if (url === "/inventory/accounts") {
      return Promise.resolve({
        data: {
          generated_at: "",
          files: {},
          counts: {
            registered_total: 0,
            raw_registered_rows: 0,
            with_auth: 0,
            pay_only_eligible: 0,
            pay_only_consumed: 0,
            pay_only_no_auth: 0,
            with_refresh_token: 0,
            rt_missing: 0,
            rt_processed: 0,
            rt_retryable: 0,
            rt_cooldown: 0,
            rt_dead: 0,
          },
          accounts: [],
        },
      });
    }
    if (url === "/config/health") {
      return Promise.resolve({ data: { status: "ok", message: "ok", checks: [] } });
    }
    if (url === "/wizard/state") {
      return Promise.resolve({ data: { answers: {} } });
    }
    return Promise.resolve({ data: {} });
  });
  apiPost.mockResolvedValue({ data: { cmd: "python run.py" } });
}

async function mountRun() {
  setActivePinia(createPinia());
  const wrapper = mount(Run, {
    global: {
      stubs: {
        TermBtn: { template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>', props: ["disabled", "loading"] },
        TermField: { template: "<label><slot /></label>" },
        TermToggle: { template: "<label><slot /></label>" },
        Teleport: true,
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe("Run Codex token export", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    mockApi();
    vi.stubGlobal("EventSource", vi.fn());
    vi.stubGlobal("confirm", vi.fn());
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("renders masked Codex metadata without full token values", async () => {
    const wrapper = await mountRun();

    const text = wrapper.text();
    expect(text).toContain("Codex 授权导出");
    expect(text).toContain("c***@example.com");
    expect(text).toContain("acct_***123");
    expect(text).not.toContain("RAW_ID_TOKEN");
    expect(text).not.toContain("RAW_ACCESS_TOKEN");
    expect(text).not.toContain("RAW_REFRESH_TOKEN");
    expect(text).not.toContain("auth_json");
  });

  it("does not export or copy Codex auth JSON when confirmation is cancelled", async () => {
    vi.mocked(window.confirm).mockReturnValue(false);
    const wrapper = await mountRun();

    await wrapper.get('[data-testid="codex-copy-1"]').trigger("click");
    await flushPromises();

    expect(window.confirm).toHaveBeenCalledOnce();
    expect(apiGet).not.toHaveBeenCalledWith("/codex-tokens/1/export");
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
  });

  it("copies exported Codex auth JSON after confirmation", async () => {
    vi.mocked(window.confirm).mockReturnValue(true);
    const wrapper = await mountRun();

    await wrapper.get('[data-testid="codex-copy-1"]').trigger("click");
    await flushPromises();

    expect(window.confirm).toHaveBeenCalledOnce();
    expect(apiGet).toHaveBeenCalledWith("/codex-tokens/1/export");
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      '{"id_token":"RAW_ID_TOKEN","access_token":"RAW_ACCESS_TOKEN","refresh_token":"RAW_REFRESH_TOKEN"}'
    );
  });

  it("downloads exported Codex auth JSON with backend filename after confirmation", async () => {
    vi.mocked(window.confirm).mockReturnValue(true);
    const wrapper = await mountRun();
    const click = vi.fn();
    const anchor = document.createElement("a");
    anchor.click = click;
    const createElement = vi.spyOn(document, "createElement").mockReturnValue(anchor);
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:codex");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    await wrapper.get('[data-testid="codex-download-1"]').trigger("click");
    await flushPromises();

    expect(window.confirm).toHaveBeenCalledOnce();
    expect(apiGet).toHaveBeenCalledWith("/codex-tokens/1/export");
    expect(anchor.download).toBe("codex-auth-1.json");
    expect(click).toHaveBeenCalledOnce();
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:codex");
    createElement.mockRestore();
  });
});
