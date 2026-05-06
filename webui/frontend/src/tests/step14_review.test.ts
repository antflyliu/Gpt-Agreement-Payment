import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import Step14Review from "../components/steps/Step14_Review.vue";
import { useWizardStore } from "../stores/wizard";

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("naive-ui", () => ({
  useMessage: () => ({ success: vi.fn(), error: vi.fn() }),
}));

describe("Step14_Review", () => {
  it("redacts sensitive GoPay fields in the review snapshot", () => {
    setActivePinia(createPinia());
    const store = useWizardStore();
    store.setAnswer("gopay", {
      country_code: "86",
      phone_number: "FAKE_GOPAY_PHONE_FROM_WIZARD",
      pin: "FAKE_GOPAY_PIN_FROM_WIZARD",
      otp_timeout: 300,
    });

    const wrapper = mount(Step14Review, {
      global: {
        stubs: {
          TermBtn: { template: "<button><slot /></button>" },
        },
      },
    });

    const text = wrapper.find(".review-pre").text();
    expect(text).toContain("phone_number");
    expect(text).toContain("pin");
    expect(text).toContain("YOUR_PHONE_NUMBER");
    expect(text).toContain("YOUR_6_DIGIT_GOPAY_PIN");
    expect(text).not.toContain("FAKE_GOPAY_PHONE_FROM_WIZARD");
    expect(text).not.toContain("FAKE_GOPAY_PIN_FROM_WIZARD");
  });

  it("keeps GoPay placeholder keys visible when credentials are not stored", () => {
    setActivePinia(createPinia());
    const store = useWizardStore();
    store.setAnswer("gopay", {
      country_code: "86",
      otp_timeout: 300,
    });

    const wrapper = mount(Step14Review, {
      global: {
        stubs: {
          TermBtn: { template: "<button><slot /></button>" },
        },
      },
    });

    const text = wrapper.find(".review-pre").text();
    expect(text).toContain("phone_number");
    expect(text).toContain("pin");
    expect(text).toContain("YOUR_PHONE_NUMBER");
    expect(text).toContain("YOUR_6_DIGIT_GOPAY_PIN");
  });
});
