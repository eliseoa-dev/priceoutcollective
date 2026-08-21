# Priceout Collective — interactive web demo

This folder contains the judge-facing interactive prototype for the Building for Good Hackathon.

## What it demonstrates

- A ZIP-level housing-pressure runway
- A selectable San Diego pressure map
- Three transparent policy assumptions
- Before/after comparisons across prototype areas
- A deterministic, reproducible calculation rather than a black-box prediction

The current rows and map topology are intentionally labeled as illustrative. Replace them with the team's validated dataset and official ZIP boundaries before treating the displayed results as findings.

## Run locally

```bash
cd web-demo
npm install
npm run dev
```

Open `http://localhost:3000`.

## Production build

```bash
npm run build
npm start
```

## Live prototype

https://priceout-collective.davielaine-36.chatgpt.site

