import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import Step06GoPay from "../components/steps/Step06_GoPay.vue";
import { useWizardStore } from "../stores/wizard";

const { apiGet, apiPost } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    get: apiGet,
    post: apiPost,
  },
}));

vi.mock("vue-router", () => ({
  RouterLink: { template: "<a><slot /></a>" },
}));

vi.mock("naive-ui", () => ({
  useMessage: () => ({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  }),
}));

describe("Step06_GoPay", () => {
  it("persists default 429 checkout retry settings for review and export", async () => {
    setActivePinia(createPinia());
    apiGet.mockResolvedValue({
      data: {
        path: "/whatsapp/ingest",
        method: "POST",
        token: "test-token",
        header_name: "X-WA-Relay-Token",
        query_name: "token",
        active: false,
      },
    });
    apiPost.mockResolvedValue({ data: { ok: true } });

    const store = useWizardStore();
    store.setAnswer("gopay", {
      country_code: "86",
      otp_timeout: 300,
      whatsapp_engine: "baileys",
    });

    mount(Step06GoPay, {
      global: {
        stubs: {
          TermBtn: { template: "<button><slot /></button>" },
          TermField: { template: "<label />" },
          TermSelect: { template: "<label />" },
        },
      },
    });
    await flushPromises();

    expect(store.answers.gopay.checkout_429_retry_limit).toBe(3);
    expect(store.answers.gopay.checkout_429_retry_sleep_s).toBe(5);
    expect(apiPost).toHaveBeenCalledWith("/wizard/state", expect.objectContaining({
      answers: expect.objectContaining({
        gopay: expect.objectContaining({
          checkout_429_retry_limit: 3,
          checkout_429_retry_sleep_s: 5,
        }),
      }),
    }));
  });
});
