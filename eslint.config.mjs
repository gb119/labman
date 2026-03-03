export default [
  {
    languageOptions: {
      ecmaVersion: 2021,
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        htmx: "readonly",
        bootstrap: "readonly",
        requestAnimationFrame: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        Event: "readonly",
        btoa: "readonly",
      }
    },
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "warn",
      "semi": "warn",
      "eqeqeq": "warn",
      "no-console": "warn",
    }
  }
];
