/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: 'var(--primary)',
        accent: 'var(--accent)',
        premium: 'var(--premium)',
        background: 'rgb(111, 143, 42)',
        'background-secondary': 'var(--background-secondary)',
        'text-primary': 'var(--text-primary)',
        'text-technical': 'var(--text-technical)',
        'text-accurate': 'var(--text-accurate)',
      },
      borderColor: {
        DEFAULT: 'var(--border-color)',
      },
      boxShadow: {
        sm: '0 1px 2px var(--shadow-color)',
        DEFAULT: '0 1px 3px var(--shadow-color), 0 1px 2px var(--shadow-color)',
        md: '0 4px 6px var(--shadow-color), 0 1px 3px var(--shadow-color)',
        lg: '0 10px 15px var(--shadow-color), 0 1px 3px var(--shadow-color)',
        xl: '0 20px 25px var(--shadow-color), 0 3px 3px var(--shadow-color)',
      },
    },
  },
  plugins: [],
} 