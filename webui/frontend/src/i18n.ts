import { createI18n } from "vue-i18n";
import zhCN from "./locales/zh-CN.json";
import enUS from "./locales/en-US.json";

type MessageSchema = typeof zhCN;

const savedLocale = localStorage.getItem("locale") || "zh-CN";

const i18n = createI18n<[MessageSchema], "zh-CN" | "en-US">({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: "zh-CN",
  messages: {
    "zh-CN": zhCN,
    "en-US": enUS,
  },
});

export default i18n;

export function setLocale(locale: "zh-CN" | "en-US") {
  (i18n.global.locale as any).value = locale;
  localStorage.setItem("locale", locale);
}
