# Docly design system — increment 1

Status: partial foundation, not whole-app replacement.

## Brand
Calm independent document assistant. Neutral surfaces, one blue accent, explicit limits, readable type. No government symbols, seals, guaranteed acceptance or decorative motion. Auth uses a text Docly wordmark; favicon/app icon and full brand assets remain unchanged.

## Implemented tokens
`packages/ui/src/styles/auth-foundation.css` scopes color, spacing, radii, motion, width and focus roles to `.docly-auth`, mapping existing --dar-* primitives. Legacy token values/tests remain unchanged.

Light surface #FFFFFF, ink #172338, muted #48566B, primary #2457C5. Dark surface #172338, ink #F2F5FA, muted #BDC9DC, primary #ADC8FF. Dark follows OS preferences only inside auth, not the existing MarketingShell or every app screen.

Base text 16px/1.6, hints14px, headings26–38px; system sans, no new font download. Existing Onest is untouched; license audit pending. Spacing4/8/12/16/24/32/48/64px; controls44–48px minimum; control radius12px; panel24px; subtle shadow.

## Components and rules
PasswordInput: native label/input, toggle, Caps Lock, linked hints/errors, password-manager autocomplete. Stepper: ordered list with aria-current=step, not fake tabs. Reuse existing Button/Input/FormErrorSummary. Story source covers default/error/disabled/long-content/English labels and steps; Storybook execution is pending.

Visible 3px focus outline; error-summary focus; heading focus on forward steps; no status by color alone. Local reduced-motion/forced-colors rules. Not WCAG certification: screen-reader, full keyboard/back-step focus, zoom and whole-screen contrast still need review.

## Remaining system work
Complete source/document status palette, full token taxonomy/typed layer, app localization, shell/sidebar/drawer, complete component states, brand asset family and legacy style consolidation. Do not apply scoped colors globally without regression testing.
