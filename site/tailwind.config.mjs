/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,ts,md,mdx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        // Bold, bright tomato brand palette.
        tomato: {
          50: '#fff1ef',
          100: '#ffe0db',
          200: '#ffc5bd',
          300: '#ff9c8d',
          400: '#ff6a54',
          500: '#f5402a', // primary accent
          600: '#e02412',
          700: '#bd1a0c',
          800: '#9c1a10',
          900: '#7f1c15',
        },
        leaf: {
          400: '#4caf50',
          500: '#3d9142',
          600: '#2f7434',
        },
      },
      fontFamily: {
        // JetBrains Mono — house display face for big bold headings.
        display: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        // Body copy: system stack (self-hosting only the display face).
        sans: [
          'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"',
          'Roboto', 'Helvetica', 'Arial', 'sans-serif',
        ],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      maxWidth: {
        content: '1400px', // §3 desktop content max-width
      },
    },
  },
  plugins: [],
};
