/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class', // Prepare for dark mode
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1A73E8", // Google Blue
          hover: "#174EA6",
          light: "#E8F0FE",
        },
        secondary: "#FFFFFF",
        success: {
          DEFAULT: "#0F9D58", // Google Green
          light: "#E6F4EA",
        },
        warning: {
          DEFAULT: "#F4B400", // Google Yellow
          light: "#FEF7E0",
        },
        danger: {
          DEFAULT: "#D93025", // Google Red
          light: "#FCE8E6",
        },
        background: {
          DEFAULT: "#F8F9FA",
          dark: "#202124",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          dark: "#303134",
        }
      },
      fontFamily: {
        sans: ['Inter', 'Roboto', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'soft': '0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15)',
        'float': '0 4px 6px 0 rgba(60,64,67,0.3), 0 8px 24px 3px rgba(60,64,67,0.15)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}
