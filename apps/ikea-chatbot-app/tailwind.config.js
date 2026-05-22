/** @type {import('tailwindcss').Config} */
module.exports = {
  mode: 'jit',  
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {},
  },
  plugins: [],
}