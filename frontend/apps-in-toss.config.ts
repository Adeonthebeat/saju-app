import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'ade20260906',
  brand: {
    primaryColor: '#7C3AED', // 앱 브랜드 색(보라/자주 계열) — src/styles/tokens.css의 --brand-primary와 맞춤
  },
  permissions: [],
  webBundleDir: 'dist',
});
