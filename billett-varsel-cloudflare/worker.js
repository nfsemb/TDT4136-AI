// Cloudflare Worker som sjekker om billetter til Frognerstadion er tilgjengelige,
// og sender push (og valgfritt e-post) via ntfy så snart status endrer seg.
//
// Kjører hvert minutt via Cron Trigger (se wrangler.toml) – i motsetning til
// GitHub Actions, som viste seg å strupe planlagte kjøringer til ~1 gang i timen.
//
// Kan også trigges manuelt i nettleser:
//   https://<worker>.workers.dev/         -> kjører en sjekk og viser resultatet
//   https://<worker>.workers.dev/?test=1  -> sender et TEST-varsel

const SITE_URL = "https://www.fotballfesten.no/frognerstadion";

// Tekst som betyr at billetter fortsatt ikke er lagt ut.
const SOON_MARKERS = ["kommer snart"];

// Kjente billettleverandører + generiske kjøpsuttrykk.
const VENDOR_MARKERS = [
  "ticketmaster", "ticketco", "tikkio", "hoopla", "secureticket",
  "billettservice", "billettluka", "ebillett", "checkin.no",
  "venuepoint", "eventim", "billetto",
];
const BUY_MARKERS = [
  "kjøp billett", "kjop billett", "kjøp din billett", "kjøp nå",
  "buy ticket", "bestill billett", "sikre deg billett", "til billettsalg",
];

// Tegn på at forespørselen ble blokkert (bot-beskyttelse).
const BLOCK_MARKERS = ["just a moment", "cf-chl", "attention required", "enable javascript and cookies"];

function evaluate(html) {
  const low = html.toLowerCase();

  if (BLOCK_MARKERS.some((m) => low.includes(m))) {
    return { available: null, reason: "Siden ser ut til å være blokkert (bot-beskyttelse)." };
  }

  const looksLikePage = low.includes("billett") || VENDOR_MARKERS.some((v) => low.includes(v));
  if (!looksLikePage) {
    return { available: null, reason: "Fant ikke forventet billett-innhold. Kan være endret/blokkert." };
  }

  const soon = SOON_MARKERS.some((m) => low.includes(m));
  const vendor = VENDOR_MARKERS.find((v) => low.includes(v));
  const buy = BUY_MARKERS.find((b) => low.includes(b));

  if (vendor) return { available: true, reason: `Fant billettleverandør-lenke: «${vendor}».` };
  if (buy) return { available: true, reason: `Fant kjøpstekst: «${buy}».` };
  if (!soon) return { available: true, reason: "«kommer snart» er borte – billetter kan være lagt ut." };
  return { available: false, reason: "«billetter kommer snart» står fortsatt på siden." };
}

async function fetchPage() {
  const resp = await fetch(SITE_URL, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
      Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "nb-NO,nb;q=0.9,no;q=0.8,en;q=0.7",
    },
    // Ikke bruk Cloudflare sin cache – vi vil ha ferske data hver gang.
    cf: { cacheTtl: 0, cacheEverything: false },
  });
  return { status: resp.status, html: await resp.text() };
}

// ntfy krever ASCII i HTTP-headere (Title/Tags), mens meldingsteksten (body)
// kan være full UTF-8. Derfor holder vi tittelen ren ASCII og legger norsk
// tekst i selve meldingen.
async function sendNtfy(env, { title, message, priority, click }) {
  const topic = env.NTFY_TOPIC || "frognerstadion-billett-9k3mq7zt";
  const headers = {
    Title: title,
    Priority: String(priority),
    Tags: "soccer,ticket,tada",
  };
  if (click) headers["Click"] = click;
  // Valgfri e-post i tillegg til push – sett NTFY_EMAIL i wrangler.toml/secret.
  if (env.NTFY_EMAIL) headers["Email"] = env.NTFY_EMAIL;

  const resp = await fetch(`https://ntfy.sh/${topic}`, {
    method: "POST",
    headers,
    body: message,
  });
  return resp.ok;
}

async function runCheck(env) {
  let page;
  try {
    page = await fetchPage();
  } catch (e) {
    return { ok: false, reason: `Klarte ikke å hente siden: ${e}` };
  }

  const { available, reason } = evaluate(page.html);

  // Dedup via KV: alarmér kun ved overgang til "tilgjengelig", ikke hvert minutt.
  const prev = await env.BILLETT.get("available"); // "1" | "0" | null

  if (available === true) {
    if (prev !== "1") {
      await sendNtfy(env, {
        title: "Billetter til Frognerstadion!",
        message: `${reason} Gå og kjøp nå: ${SITE_URL}`,
        priority: 5,
        click: SITE_URL,
      });
      await env.BILLETT.put("available", "1");
    }
  } else if (available === false) {
    await env.BILLETT.put("available", "0");
  }
  // available === null (blokkert/ukjent): rør ikke lagret status, ikke alarmér.

  return { ok: true, status: page.status, available, reason, alertedBefore: prev === "1" };
}

export default {
  // Kjøres av Cron Trigger (hvert minutt).
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runCheck(env));
  },

  // Manuell trigger / testing i nettleser.
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.searchParams.get("test") === "1") {
      const ok = await sendNtfy(env, {
        title: "TEST - Billettvarsel Frognerstadion",
        message: "Dette er en testmelding. Ser du denne, funker varslene.",
        priority: 3,
        click: SITE_URL,
      });
      return new Response(ok ? "Test-varsel sendt.\n" : "Test-varsel FEILET.\n", {
        status: ok ? 200 : 502,
      });
    }
    const result = await runCheck(env);
    return new Response(JSON.stringify(result, null, 2), {
      headers: { "content-type": "application/json; charset=utf-8" },
    });
  },
};
