# Mobile App Roadmap

Recommended production architecture:

```text
Sofmap / Janpara / IOSYS / Official MSRP
            ↓
      Python ingestion
            ↓
    PostgreSQL / Supabase
            ↓
         FastAPI
            ↓
 React Native + Expo mobile app
       ↙             ↘
   iOS App Store    Google Play
```

## Why not package Streamlit directly?

Streamlit is excellent for a prototype and dashboard, but a store app will benefit from native navigation, push notifications, watchlists, smoother animations, caching, and deep links.

## Suggested phases

1. Validate data-source stability with the web MVP.
2. Add tourist tax-free pricing and watchlists.
3. Move local SQLite data to hosted PostgreSQL/Supabase.
4. Expose product / price / deal endpoints with FastAPI.
5. Build mobile UI with React Native + Expo + TypeScript.
6. Add push alerts for price thresholds / stock changes.
7. Prepare App Store / Google Play listing and privacy documents.

The current Python adapters and comparison logic can be reused.
