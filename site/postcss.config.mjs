// Tailwind 3 as a plain PostCSS plugin (replaces the deprecated
// @astrojs/tailwind integration; base styles stay in src/styles/global.css).
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
