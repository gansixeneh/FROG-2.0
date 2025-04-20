module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        frog: {
          light: '#a6e9a6', // Light green
          DEFAULT: '#4ade80', // Medium green
          dark: '#166534', // Dark green
          accent: '#bef264', // Lime accent
          secondary: '#1e293b' // Dark blue-gray for contrast
        }
      },
      backgroundImage: {
        'polka-dots': 'radial-gradient(circle, #166534 10%, transparent 10%), radial-gradient(circle, #166534 10%, transparent 10%)',
      },
      backgroundSize: {
        'polka-size': '30px 30px',
      },
      backgroundPosition: {
        'polka-pos': '0 0, 15px 15px',
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};