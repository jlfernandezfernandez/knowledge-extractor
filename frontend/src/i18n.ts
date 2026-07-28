import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import { en } from "./locales/en";
import { es } from "./locales/es";

export const LANGUAGES = { en: "English", es: "Español" } as const;
export type Language = keyof typeof LANGUAGES;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, es: { translation: es } },
    supportedLngs: Object.keys(LANGUAGES),
    fallbackLng: "en",
    // The browser's own language is the right first guess; the explicit choice
    // is remembered so it survives a reload.
    detection: { order: ["localStorage", "navigator"], caches: ["localStorage"] },
    interpolation: { escapeValue: false }, // React escapes already
  });

// Keep the document in sync so screen readers and `:lang()` styling are correct.
const applyLanguage = (language: string) => {
  document.documentElement.lang = language;
};
applyLanguage(i18n.resolvedLanguage ?? "en");
i18n.on("languageChanged", applyLanguage);

export default i18n;

/** The language to answer in. The backend is told to reply in the question's
 *  language, but stating it explicitly removes the guesswork on short queries. */
export const currentLanguage = () => (i18n.resolvedLanguage ?? "en") as Language;
