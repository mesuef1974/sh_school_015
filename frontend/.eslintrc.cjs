/* ESLint config for Vue 3 + TypeScript + Prettier */
module.exports = {
  root: true,
  env: { browser: true, es2023: true, node: true },
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    sourceType: 'module',
    ecmaVersion: 'latest',
    extraFileExtensions: ['.vue']
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:prettier/recommended'
  ],
  plugins: ['vue', '@typescript-eslint'],
  rules: {
    // This project uses many single-word view files intentionally
    'vue/multi-word-component-names': 'off',
    // Keep console in dev; CI can turn this on later
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off'
  },
  ignorePatterns: ['dist', 'node_modules', '.vite', 'coverage']
};