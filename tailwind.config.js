module.exports = {
  prefix: 'tw-',
  content: [
    './fiscallizeon/**/*.html',
    './fiscallizeon/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          100: '#CFFAFE',
          200: '#FFEEE1',
          300: '#FFD6B8',
          400: '#FFBE90',
          500: '#FFA767',
          600: '#FF8F3E',
          700: '#FF6E06',
          800: '#CD5600',
          900: '#953E00',
        },
        'blue': {
          50: '#CBE5FC',
          100: '#B8DCFB',
          200: '#91C9F9',
          300: '#6BB6F7',
          400: '#44A3F5',
          500: '#1D90F3',
          600: '#0C7BDB',
          700: '#095DA6',
          800: '#063F71',
          900: '#03213B',
          950: '#021221'
        },
        'mint': {
          50: '#F6FEF9',
          100: '#ECFDF3',
          200: '#D1FADF',
          300: '#A6F4C5',
          400: '#6CE9A6',
          500: '#32D583',
          600: '#12B76A',
          700: '#039855',
          800: '#027A48',
          900: '#05603A',
          950: '#054F31',
        },
        'poppy': {
          50: '#FFFBFA',
          100: '#FEF3F2',
          200: '#FEE4E2',
          300: '#FECDCA',
          400: '#FDA29B',
          500: '#F97066',
          600: '#F04438',
          700: '#D92D20',
          800: '#B42318',
          900: '#912018',
          950: '#7A271A',
        },
        'honey': {
          50: '#FFFCF5',
          100: '#FFFAEB',
          200: '#FEF0C7',
          300: '#FEDF89',
          400: '#FEC84B',
          500: '#FDB022',
          600: '#F79009',
          700: '#DC6803',
          800: '#B54708',
          900: '#93370D',
          950: '#7A2E0E',
        },
      },
      maxWidth: {
        '8xl': '88rem',
      },
      lineHeight: {
        '4.5': '1.125rem',
        '11': '2.75rem',
      },
      spacing: {
        '1.75': '0.4375rem',
        '2.25': '0.5625rem',
        '10.5': '2.625rem',
        '50': '12.5rem',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
