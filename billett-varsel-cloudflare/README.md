# Billettvarsel Frognerstadion – Cloudflare Worker

Sjekker `https://www.fotballfesten.no/frognerstadion` **hvert minutt** og sender
push (og valgfritt e-post) via [ntfy](https://ntfy.sh) så snart «billetter kommer
snart» forsvinner eller en billettlenke/kjøp-knapp dukker opp.

## Hvorfor Cloudflare og ikke GitHub Actions?

GitHub Actions sine planlagte workflows er *best effort* og ble i praksis strupet
til omtrent **én kjøring i timen** (målt snitt ~100 min mellom kjøringer, verste
tilfelle 3,6 t) – selv om cron sa hvert 5. minutt. Det ga varsel opptil en time
for sent. Cloudflare Cron Triggers kjører derimot punktlig hvert minutt.

## Oppsett (engangs, ~5 min)

Krever en gratis Cloudflare-konto og [Node.js](https://nodejs.org).

```bash
# 1. Installer Wrangler (Cloudflare sitt CLI)
npm install -g wrangler

# 2. Logg inn (åpner nettleseren)
wrangler login

# 3. Opprett KV-lageret som husker forrige status
wrangler kv namespace create BILLETT
#    -> kopier "id"-verdien du får og lim den inn i wrangler.toml
#       (erstatt FYLL_INN_KV_NAMESPACE_ID)

# 4. (Valgfritt) vil du ha e-post i tillegg til push?
#    Fjern kommentaren på NTFY_EMAIL i wrangler.toml og sett inn e-posten din.

# 5. Deploy
wrangler deploy
```

## Få varselet på mobilen

1. Installer **ntfy**-appen (App Store / Google Play).
2. Abonner på emnet: `frognerstadion-billett-9k3mq7zt`
   (eller ditt eget – endre `NTFY_TOPIC` i `wrangler.toml` før deploy).

## Test at det virker

Etter deploy får du en URL som `https://billett-varsel-frognerstadion.<konto>.workers.dev`.

- `…/` – kjører en sjekk nå og viser JSON-resultat (status, tilgjengelig, begrunnelse).
- `…/?test=1` – sender et TEST-varsel til ntfy (push + evt. e-post).

## Følg med / logg

```bash
wrangler tail          # sanntidslogg fra kjøringene
```

## Slå av

```bash
wrangler delete        # fjerner workeren og cron-triggeren
```
