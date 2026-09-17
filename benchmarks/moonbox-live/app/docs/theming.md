# Theming

Effusion Labs ships with a default dark theme and an optional light mode. Theme colors are driven by CSS custom properties declared in `src/styles/tokens.css` and exposed to Tailwind as design tokens.

## Tokens

```css
html[data-theme="dark"] {
  --color-bg: 0 0 0;
  --color-surface: 26 26 26;
  --color-text: 240 240 240;
}
html[data-theme="light"] {
  --color-bg: 255 255 255;
  --color-surface: 240 240 240;
  --color-text: 26 26 26;
}
```

Utilities like `bg-background`, `bg-surface` and `text-text` resolve to these variables so the same classes work across themes.

## Toggle

The header exposes a keyboard-accessible button that switches between dark and light modes. The choice is saved to `localStorage` and applies on first paint without flashing.

## Extending

Add new variables in `tokens.css` and reference them from `tailwind.config.cjs` to create additional color roles.
