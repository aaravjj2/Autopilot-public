# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-flow.spec.ts >> Full User Flow >> no critical page errors
- Location: tests/e2e/full-flow.spec.ts:38:7

# Error details

```
Error: page.goto: Target page, context or browser has been closed
Call log:
  - navigating to "http://127.0.0.1:3000/dashboard", waiting until "load"

```

```
Error: apiRequestContext._wrapApiCall: Target page, context or browser has been closed
```