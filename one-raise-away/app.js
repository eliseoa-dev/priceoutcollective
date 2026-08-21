// One Raise Away — Building for Good Hackathon · 2026-08-21
const APP_VERSION = '1.0.1';
const STAGE = 'Alpha';

/* ---------- model ---------- */
const SHOCKS = [0, 5, 10, 15, 20, 25, 30, 40, 50];
const SI = (r) => SHOCKS.indexOf(r) + 1;            // index into the per-tract lens arrays ([n, v0, v5, …])
const LENS = { a: 'All households', s: 'Living alone', k: 'With kids', r: 'Retiree on Social Security' };
const SS_DEFAULT = 1907;                            // SSA average retired-worker benefit, Jan 2024 — editable in the UI
const S = { raise: 10, lens: 'a', ss: SS_DEFAULT, sel: null, snap: {} };
try { Object.assign(S, JSON.parse(localStorage.getItem('ora.state') || '{}')); } catch (e) {}
S.sel = null; S.snap = S.snap || {};
const save = () => { try { localStorage.setItem('ora.state', JSON.stringify({ raise: S.raise, lens: S.lens, ss: S.ss })); } catch (e) {} };

const IDS = Object.keys(TRACTS);
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const money = (n) => '$' + fmt(n);
const pct = (x, d) => (x * 100).toFixed(d == null ? 0 : d) + '%';

// How many households in tract t earn less than their living budget once rent is r% higher.
const under = (t, r, lens) => { const a = t[lens === 'r' ? 's' : lens]; return a ? a[SI(r)] : 0; };
const nOf = (t, lens) => { const a = t[lens === 'r' ? 's' : lens]; return a ? a[0] : 0; };
// Retiree lens: monthly gap between a one-person living budget in this tract and a Social Security check.
// The raise lands on the studio rent; "other essentials" are 20% of food+housing, so the increment carries 1.2×.
const gap = (t, r, ss) => (t.hlb1 == null ? null : t.hlb1 / 12 + t.studio * (r / 100) * 1.2 - ss);
const totals = (r, lens) => {
  let n = 0, v0 = 0, vr = 0;
  IDS.forEach((id) => { const t = TRACTS[id]; n += nOf(t, lens); v0 += under(t, 0, lens); vr += under(t, r, lens); });
  return { n, v0, vr, tipped: vr - v0 };
};
const retireeTotals = (r, ss) => {
  let tracts = 0, afford = 0, sumGap = 0, worst = 0;
  IDS.forEach((id) => { const g = gap(TRACTS[id], r, ss); if (g == null) return; tracts++; if (g <= 0) afford++; sumGap += g; if (g > worst) worst = g; });
  return { tracts, afford, avgGap: sumGap / tracts, worst };
};

/* ---------- colour ---------- */
const lerp = (a, b, t) => a + (b - a) * t;
const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
const mix = (c1, c2, t) => { const a = hex(c1), b = hex(c2); return 'rgb(' + a.map((x, i) => Math.round(lerp(x, b[i], t))).join(',') + ')'; };
const ramp = (t) => { t = Math.max(0, Math.min(1, t)); return t < .5 ? mix('#f6ead3', '#d9784f', t * 2) : mix('#d9784f', '#7a2512', (t - .5) * 2); };
const shareColor = (t, r, lens) => { const n = nOf(t, lens); return n < 30 ? '#ebe4d6' : ramp(under(t, r, lens) / n); };
const gapColor = (t, r, ss) => { const g = gap(t, r, ss); return g == null ? '#ebe4d6' : ramp((g - 1000) / 3500); };
const fillFor = (t) => (S.lens === 'r' ? gapColor(t, S.raise, S.ss) : shareColor(t, S.raise, S.lens));

/* ---------- map ---------- */
function mapSVG(opts) {
  opts = opts || {};
  let paths = '';
  IDS.forEach((id) => {
    const t = TRACTS[id];
    paths += '<path id="t' + id + '" d="' + t.p + '" fill="' + (opts.fill ? opts.fill(t) : fillFor(t)) + '" data-fn="tract:' + id + '"></path>';
  });
  let dots = '';
  if (opts.dots) {
    const mx = Math.max.apply(null, STORAGE.map((z) => z.n));
    STORAGE.slice().sort((a, b) => b.n - a.n).forEach((z) => {
      const rr = 4 + 22 * Math.sqrt(z.n / mx);
      dots += '<circle class="dot" cx="' + z.x + '" cy="' + z.y + '" r="' + rr.toFixed(1) + '" data-fn="zip:' + z.zip + '"><title>' + z.zip + ' ' + z.city + ' — ' + z.n + ' units</title></circle>';
      if (z.n >= 30) dots += '<text class="dotlab" x="' + (z.x + rr + 2) + '" y="' + (z.y + 3) + '">' + z.city + ' ' + z.n + '</text>';
    });
  }
  return '<div class="mapwrap"><svg viewBox="' + MAP.vb.join(' ') + '" role="img" aria-label="San Diego County census tracts">' + paths + dots + '</svg>' +
    (opts.legend || '') + '<div class="hint">' + (opts.hint || 'Tap a tract') + '</div></div>';
}
function legendHTML() {
  const g = 'linear-gradient(90deg,' + [0, .25, .5, .75, 1].map((t) => ramp(t)).join(',') + ')';
  if (S.lens === 'r') return '<div class="legend"><b>Monthly gap, retiree alone</b><div class="bar" style="background:' + g + '"></div><div class="lr"><span>$1,000</span><span>$2,750</span><span>$4,500+</span></div></div>';
  return '<div class="legend"><b>Share earning less than their budget</b><div class="bar" style="background:' + g + '"></div><div class="lr"><span>0%</span><span>50%</span><span>100%</span></div></div>';
}
function repaint() {
  IDS.forEach((id) => { const el = document.getElementById('t' + id); if (el) el.setAttribute('fill', fillFor(TRACTS[id])); });
  const lg = document.querySelector('.mapwrap .legend'); if (lg) lg.outerHTML = legendHTML();
}

/* ---------- views ---------- */
const C = COUNTY;
const VIEWS = {
  '#/home': () => {
    setTop({ wordmark: true });
    const t10 = totals(10, 'a');
    return '<section class="screen">' +
      '<div class="hero"><div class="eyebrow">San Diego County · Affordability</div>' +
      '<div class="big">Housed is not the same as <em>safe.</em></div>' +
      '<p class="lede">Getting someone into a home is counted as the win. Then the rent goes up, the income does not, and nobody is watching anymore. This is the story of that gap — and the early warning that nobody tracks.</p></div>' +
      '<div class="tiles">' +
      '<div class="tile wide"><div class="n acc">' + pct(C.shocks['0'] / C.n) + '</div><div class="l"><b>' + fmt(C.shocks['0']) + ' of ' + fmt(C.n) + ' San Diego households</b> earn less than the basic living budget for where they live — before any rent raise.</div></div>' +
      '<div class="tile"><div class="n">' + fmt(C.within10) + '</div><div class="l">households are <b>within 10%</b> of their budget line — one raise away</div></div>' +
      '<div class="tile"><div class="n acc">+' + fmt(t10.tipped) + '</div><div class="l">more households tip under their budget if rent rises <b>10%</b></div></div>' +
      '</div>' +
      '<div class="person"><div class="who">User research · one interview · 72 · San Diego</div>' +
      '<p>They were homeless. A caseworker got them housed. Social Security pays the rent; a subsidy covers the balance. That was the success — case closed.</p>' +
      '<p>Now the rent has gone up. The check has not. They are trying to find a cheaper place alone, on a fixed income, without a smartphone, without the caseworker. They are about to be homeless again.</p>' +
      '<p><em>“The project isn’t complete once they’re housed. It’s ongoing as long as they are on a subsidy.”</em></p></div>' +
      '<h3 class="sh">How the cliff works</h3>' +
      '<div class="chain">' +
      '<div class="step"><div class="num">1</div><div class="t"><b>Fixed income.</b> Social Security averaged <b>$1,907 a month</b> for a retired worker in 2024. A one-person living budget in the median San Diego tract is <b>' + money(C.hlb1_med / 12) + ' a month</b> in gross income.</div></div>' +
      '<div class="step"><div class="num">2</div><div class="t"><b>The subsidy fills the gap</b> — at the rent on the day they moved in.</div></div>' +
      '<div class="step"><div class="num hot">3</div><div class="t"><b>Rent rises.</b> The subsidy does not follow. The increase comes straight out of a check that cannot grow.</div></div>' +
      '<div class="step"><div class="num hot">4</div><div class="t"><b>Nobody is watching.</b> The case closed at move-in. The person is back on the edge with no one assigned to them.</div></div>' +
      '</div>' +
      '<div class="ctas"><button class="btn" data-fn="nav:#/cliff">Run a rent raise across the county →</button>' +
      '<button class="btn ghost" data-fn="nav:#/signal">See the early warning nobody tracks →</button></div>' +
      '<p class="fine">Budget data: San Diego County Household Living Budget, 1,171,123 synthetic households in 732 tracts, 2024 dollars (hackathon dataset). Social Security figure: SSA average monthly benefit, retired workers, 2024.</p>' +
      '</section>';
  },

  '#/cliff': () => {
    setTop({ title: 'The cliff', back: false });
    const isR = S.lens === 'r';
    const T = totals(S.raise, S.lens);
    const R = isR ? retireeTotals(S.raise, S.ss) : null;
    const seg = Object.keys(LENS).map((k) => '<button class="' + (S.lens === k ? 'on' : '') + '" data-fn="lens:' + k + '">' + ({ a: 'All', s: 'Alone', k: 'With kids', r: 'Retiree' })[k] + '</button>').join('');
    const counters = isR ?
      '<div class="counter"><div class="c"><div class="n acc">' + money(R.avgGap) + '</div><div class="l">average monthly gap between a one-person budget and the check</div></div>' +
      '<div class="c"><div class="n">' + R.afford + '<small style="font-size:14px;color:var(--dim)"> / ' + R.tracts + '</small></div><div class="l">tracts where the check covers the budget</div></div>' +
      '<div class="c"><div class="n">' + money(R.worst) + '</div><div class="l">worst monthly gap in the county</div></div></div>' :
      '<div class="counter"><div class="c"><div class="n">' + fmt(T.v0) + '</div><div class="l">under their budget today</div></div>' +
      '<div class="c"><div class="n acc">+' + fmt(T.tipped) + '</div><div class="l">tipped under by this raise</div></div>' +
      '<div class="c"><div class="n">' + pct(T.vr / T.n) + '</div><div class="l">of ' + fmt(T.n) + ' ' + LENS[S.lens].toLowerCase() + ' after the raise</div></div></div>';
    return '<section class="screen">' +
      '<div class="eyebrow">Working model · rent-raise simulator</div>' +
      '<h2 class="h">Raise the rent. <em>Watch who falls.</em></h2>' +
      '<p class="body">Every household below has a living budget built for its tract — rent, food, childcare, transport, health care, broadband, taxes. Slide the rent up and the model recounts who no longer earns enough to cover it.</p>' +
      '<div class="panel">' +
      '<div class="slider"><div class="row"><span class="lab">Rent increase</span><span class="val" id="raiseVal">' + S.raise + '<small>%</small></span></div>' +
      '<input type="range" id="raise" min="0" max="8" step="1" value="' + SHOCKS.indexOf(S.raise) + '" style="--pct:' + (SHOCKS.indexOf(S.raise) / 8 * 100) + '%">' +
      '<div class="ticks">' + SHOCKS.map((s) => '<span>' + s + '</span>').join('') + '</div></div>' +
      '<div class="seg">' + seg + '</div>' +
      (isR ? '<div class="field"><label>Social Security check per month</label><div class="in"><span>$</span><input id="ss" inputmode="numeric" value="' + fmt(S.ss) + '"></div></div>' : '') +
      '<div id="counters">' + counters + '</div>' +
      '</div>' +
      mapSVG({ legend: legendHTML() }) +
      '<div id="tractCard"></div>' +
      '<div class="ctas"><button class="btn ghost" data-fn="nav:#/snap">📷 Snap a rent-increase notice → see what it does</button></div>' +
      '<details class="src"><summary>How the model works</summary>' +
      '<p>A household is “under its budget” when gross income is below the gross income its living budget requires (the dataset’s <i>economically_vulnerable</i> test). A rent raise of r% adds 12 × housing × r to the budget, plus the 20% “other essentials” that scale with housing, grossed up by the tract’s budget tax rate. Tracts with fewer than 30 households in the chosen lens are left grey.</p>' +
      '<p>“Living alone” = one adult, household of one. “With kids” = anyone under 19 in the home. “Retiree” uses the one-person budget in each tract against a Social Security check — the dataset cannot tell age, so this is the budget a 72-year-old living alone would face.</p></details>' +
      '</section>';
  },

  '#/snap': () => {
    setTop({ title: 'Snap the notice', back: true });
    const cfg = eyepopCfg();
    const sn = S.snap;
    return '<section class="screen">' +
      '<div class="eyebrow">EyePop.ai · read the letter, run the model</div>' +
      '<h2 class="h">Point the camera at the <em>rent-increase letter.</em></h2>' +
      '<p class="body">A caseworker, a neighbor, or the tenant photographs the notice. The text is read by EyePop.ai vision, the new rent is pulled out, and the model answers the only question that matters: does this raise push them over?</p>' +
      '<label class="drop" for="snapFile"><svg class="ico" viewBox="0 0 24 24"><path d="M4 7h3l2-3h6l2 3h3v12H4z"/><circle cx="12" cy="13" r="3.5"/></svg><p><b>Take a photo</b> or choose one</p><input id="snapFile" type="file" accept="image/*" capture="environment"></label>' +
      (sn.img ? '<img class="preview" src="' + sn.img + '" alt="notice">' : '') +
      '<div id="snapStatus"></div>' +
      (sn.text != null ? '<div class="ocr" id="ocr">' + esc(sn.text || '(no text found)') + '</div>' : '') +
      '<div class="field"><label>Or type what the notice says</label></div>' +
      '<textarea id="snapText" rows="3" style="width:100%;border:1px solid var(--border);border-radius:10px;padding:10px;background:var(--card);font-size:15px" placeholder="e.g. Effective October 1, 2026 your monthly rent will increase from $1,850 to $2,035">' + esc(sn.typed || '') + '</textarea>' +
      '<button class="btn ghost sm" style="margin-top:8px" data-fn="snapParse">Read the numbers</button>' +
      '<div id="snapFound">' + foundHTML() + '</div>' +
      '<div id="snapVerdict">' + verdictHTML() + '</div>' +
      '<details class="src"><summary>EyePop.ai connection' + (cfg.key ? ' · connected' : ' · not set') + '</summary>' +
      '<p>Runs in the browser with the EyePop.ai web SDK. Create a Pop in the EyePop dashboard with a text-recognition ability (hackathon code <b>DSA2026</b>), then paste its id and API key here. Nothing is stored outside this phone.</p>' +
      '<div class="field"><label>Pop ID</label><div class="in"><input class="wide" id="epPop" value="' + esc(cfg.pop || '') + '" placeholder="pop id"></div></div>' +
      '<div class="field"><label>API key</label><div class="in"><input class="wide" id="epKey" type="password" value="' + esc(cfg.key || '') + '" placeholder="secret key"></div></div>' +
      '<button class="btn ghost sm" data-fn="epSave">Save connection</button></details>' +
      '</section>';
  },

  '#/signal': () => {
    setTop({ title: 'Early signal', back: false });
    const ss = STORAGE_SUM;
    const top = STORAGE.slice().sort((a, b) => b.n - a.n).slice(0, 8);
    return '<section class="screen">' +
      '<div class="eyebrow">Other data · storage lien auctions · team-collected</div>' +
      '<h2 class="h">The earliest public sign of a household in freefall is a <em>storage unit going to auction.</em></h2>' +
      '<p class="body">When a home shrinks or disappears, the belongings go into storage. When the storage bill is missed, the law lets the facility sell the unit. That sale is public, it is dated, and it happens <b class="k">months before</b> anyone is counted on a sidewalk. Nobody tracks it as a homelessness signal. We did.</p>' +
      '<div class="tiles">' +
      '<div class="tile"><div class="n acc">' + fmt(ss.n) + '</div><div class="l"><b>lien-sale units</b> listed at San Diego County facilities</div></div>' +
      '<div class="tile"><div class="n">' + ss.facilities + '</div><div class="l">facilities · <b>' + ss.zips + ' ZIP codes</b></div></div>' +
      '<div class="tile wide"><div class="n">3<small> weeks</small></div><div class="l">capture window 2026-06-12 → 2026-07-02 · storagetreasures.com · one listing = one household that stopped paying for what it owns</div></div>' +
      '</div>' +
      mapSVG({ dots: true, fill: (t) => (nOf(t, 'a') < 30 ? '#ebe4d6' : mix('#f6ead3', '#c99b7a', under(t, 0, 'a') / nOf(t, 'a'))), hint: 'Dot = units to auction by ZIP', legend: '<div class="legend"><b>Units to auction, by ZIP</b><div class="lr"><span>● small</span><span>⬤ ' + Math.max.apply(null, STORAGE.map((z) => z.n)) + ' units</span></div><div style="margin-top:4px">Shading: share under budget today</div></div>' }) +
      '<div class="list">' + top.map((z) => '<div class="li" data-fn="zip:' + z.zip + '"><div><div class="t">' + z.city + ' · ' + z.zip + '</div><div class="s">' + z.f + ' facilit' + (z.f === 1 ? 'y' : 'ies') + '</div></div><div class="n">' + z.n + '</div></div>').join('') + '</div>' +
      '<div class="chips">' + Object.keys(ss.chains).map((c) => '<span class="chip">' + c + ' <b>' + ss.chains[c] + '</b></span>').join('') + '</div>' +
      '<h3 class="sh">The storage <em>conundrum</em></h3>' +
      '<p class="body">A home is a 12-month lease. Storage is month to month. A family that downsized in a hurry is paying for both — and the storage rent is the one that moves. Operators in this market raise a new tenant’s rate a few months in. If the $300 unit becomes $600, that extra $300 was the difference between the small place and the right-sized one. They cannot give up the unit (everything they own is in it) and cannot break the lease to get a bigger home. So the storage bill is the first one missed.</p>' +
      '<p class="body">Pre-sale notices are already required by law (California Business & Professions Code §§21700–21716). The signal exists. It is just not connected to anyone who could help.</p>' +
      '<h3 class="sh">Where it ends up — the only place it gets <em>measured</em></h3>' +
      downtownChart() +
      '<p class="fine">Downtown series: Downtown San Diego Partnership Clean &amp; Safe monthly Unsheltered Sleep Count, six core neighborhoods (East Village, City Center, Columbia, Cortez, Gaslamp, Marina), published totals. Outside Perimeter joined the count in April 2021 and is drawn separately. Reports were not published for Jul, Aug, Oct and Nov 2025.</p>' +
      '</section>';
  },

  '#/ask': () => {
    setTop({ title: 'The ask', back: false });
    const t10 = totals(10, 'a');
    return '<section class="screen">' +
      '<div class="eyebrow">Actionable insights · for policy makers, housing agencies, storage operators</div>' +
      '<h2 class="h">Four things that would <em>close the gap.</em></h2>' +
      '<div class="ask"><div class="who">Housing agencies · caseworkers</div><h4>Placement is not the finish line. Make a rent-increase notice a trigger.</h4>' +
      '<p>Any rent increase on a subsidized tenant re-opens the case automatically: one caseworker touch, a subsidy recalculation, and help finding the next place if one is needed. Today the case closes the day the key is handed over.</p>' +
      '<div class="ev">Evidence: <b>' + fmt(C.within10) + '</b> San Diego households sit within 10% of their living budget. A 10% raise tips <b>' + fmt(t10.tipped) + '</b> of them under it. Nobody is assigned to any of them.</div></div>' +
      '<div class="ask"><div class="who">Policy makers</div><h4>Index the subsidy to the rent, not to the move-in day.</h4>' +
      '<p>A subsidy fixed at move-in is a countdown. For a retiree the raise comes straight out of a Social Security check that cannot grow. Re-base the subsidy whenever the rent changes, or cap the tenant share at a fixed percentage of income.</p>' +
      '<div class="ev">Evidence: the one-person living budget in the median tract is <b>' + money(C.hlb1_med / 12) + '/month</b>; the average retired-worker check was <b>$1,907</b>. Every dollar of a raise is a dollar the subsidy has to follow.</div></div>' +
      '<div class="ask"><div class="who">Storage operators · outreach · 2-1-1</div><h4>Treat a pre-lien notice as an outreach moment.</h4>' +
      '<p>Facilities already send a pre-lien notice by law. Add one line and a QR code: “If you are going through a hard time, here is who can help.” Opt-in, no data shared, no cost. The earliest signal in the whole pipeline becomes the earliest offer of help.</p>' +
      '<div class="ev">Evidence: <b>' + fmt(STORAGE_SUM.n) + '</b> San Diego County units went to lien auction in three weeks of June 2026 across <b>' + STORAGE_SUM.facilities + '</b> facilities. Downtown’s street count on the worst month (May 2023) was 1,527. The storage signal is bigger, earlier, and dated.</div></div>' +
      '<div class="ask"><div class="who">Legislators · industry</div><h4>A storage rent-stability rule for the first 12 months.</h4>' +
      '<p>Residential leases lock the rent for a year; storage can move every month. Proposal: a storage rental that begins within 90 days of a residential move keeps its opening rate for 12 months. Operators who adopt it voluntarily get out ahead of the bill that is otherwise coming.</p>' +
      '<div class="ev">Evidence: the month-to-month / 12-month mismatch is structural — the household cannot drop either bill. Rent stability on the smaller bill is the cheapest intervention on this page.</div></div>' +
      '<h3 class="sh">Analysis &amp; sources</h3>' +
      '<details class="src" open><summary>What we used and how</summary>' +
      '<p><b>Affordability (hackathon dataset):</b> San Diego County Household Living Budget — 1,171,123 synthetic households, 732 tracts, 25 columns, 2024 dollars. Used as distributions only, never as individual households; rows are not deduplicated (they are intentional clones). Five tracts under 100 households are shown but greyed under 30 per lens.</p>' +
      '<p><b>Rent-shock model:</b> for each household, budget after a raise = hlb_year + 12 × housing_cost_month × r × 1.2 × (1 + hlb_taxes_year ÷ hlb_no_tax_year). Household is under budget when hh_income is below that. Precomputed at 0–50% for three lenses (all, living alone, with children), per tract.</p>' +
      '<p><b>Other data 1 — storage lien auctions (team-collected):</b> storagetreasures.com listings captured 2026-06-12 → 2026-07-02 (88,683 US auctions; 10,039 California lien units; 820 in San Diego County by ZIP). Placed by ZIP centroid (Census ZCTA 2020). Facility addresses are not in the feed, so dots are ZIP-level.</p>' +
      '<p><b>Other data 2 — Downtown San Diego Partnership Clean &amp; Safe monthly unsheltered count (hackathon dataset, Homelessness track):</b> published neighborhood totals 2017–2025; core six neighborhoods summed, Outside Perimeter shown separately (joined April 2021).</p>' +
      '<p><b>Tract geometry:</b> Census TIGERweb 2020 tracts, San Diego County. <b>Social Security:</b> SSA average monthly benefit for retired workers, 2024, editable in the model.</p>' +
      '<p><b>EyePop.ai:</b> web SDK text recognition on a photographed rent-increase notice feeds the new rent into the model (The cliff → Snap the notice).</p>' +
      '<p><b>Limits we know about:</b> the budget data cannot identify retirees (age bands stop at 19+), so the retiree lens is a one-person budget, not a senior-specific one. The storage capture is three weeks, not a year. The 72-year-old’s account comes from one user-research interview; it is the reason, not the sample.</p></details>' +
      '</section>';
  },
};

/* ---------- pieces ---------- */
function tractCard(id) {
  const t = TRACTS[id]; if (!t) return '';
  const r = S.raise, lens = S.lens;
  const name = 'Tract ' + id.slice(5).replace(/^0+/, '').replace(/(\d{2})$/, '.$1');
  let rows = '';
  if (lens === 'r') {
    const g0 = gap(t, 0, S.ss), g1 = gap(t, r, S.ss);
    rows = '<div class="kv"><span class="k">Studio rent (fair market)</span><span class="v">' + money(t.studio) + '/mo</span>' +
      '<span class="k">One-person living budget</span><span class="v">' + money(t.hlb1 / 12) + '/mo</span>' +
      '<span class="k">Social Security check</span><span class="v">' + money(S.ss) + '/mo</span><span class="sep"></span>' +
      '<span class="k">Gap the subsidy must cover today</span><span class="v acc">' + money(g0) + '/mo</span>' +
      '<span class="k">Gap after a ' + r + '% raise</span><span class="v acc">' + money(g1) + '/mo</span>' +
      '<span class="k">What the raise adds — and the subsidy does not</span><span class="v acc">+' + money(g1 - g0) + '/mo</span></div>';
  } else {
    const n = nOf(t, lens), v0 = under(t, 0, lens), vr = under(t, r, lens);
    rows = '<div class="kv"><span class="k">Households (' + LENS[lens].toLowerCase() + ')</span><span class="v">' + fmt(n) + '</span>' +
      '<span class="k">Median income</span><span class="v">' + money(t.med_inc) + '</span>' +
      '<span class="k">Median living budget</span><span class="v">' + money(t.med_hlb) + '</span>' +
      '<span class="k">Median required rent</span><span class="v">' + money(t.med_rent) + '/mo</span><span class="sep"></span>' +
      '<span class="k">Under budget today</span><span class="v">' + fmt(v0) + ' · ' + pct(v0 / (n || 1)) + '</span>' +
      '<span class="k">Tipped by a ' + r + '% raise</span><span class="v acc">+' + fmt(vr - v0) + '</span>' +
      '<span class="k">Under budget after</span><span class="v acc">' + fmt(vr) + ' · ' + pct(vr / (n || 1)) + '</span></div>' +
      '<div class="bars">' + SHOCKS.map((s) => { const v = under(t, s, lens); return '<div class="bar"><span>rent +' + s + '%</span><div class="tr"><div class="fl' + (s > r ? ' dim' : '') + '" style="width:' + (100 * v / (n || 1)).toFixed(1) + '%"></div></div><span class="v">' + pct(v / (n || 1)) + '</span></div>'; }).join('') + '</div>';
  }
  return '<div class="panel card"><h4>' + name + '</h4><div class="sub">GEOID ' + id + ' · PUMA ' + t.puma + '</div>' + rows + '</div>';
}
function downtownChart() {
  const W = 640, H = 230, L = 40, R = 10, T = 14, B = 30;
  const pts = DOWNTOWN; const n = pts.length;
  const mx = Math.max.apply(null, pts.map((p) => Math.max(p.core, p.op || 0)));
  const ymax = Math.ceil(mx / 250) * 250;
  const x = (i) => L + (W - L - R) * i / (n - 1);
  const y = (v) => T + (H - T - B) * (1 - v / ymax);
  const line = pts.map((p, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(p.core).toFixed(1)).join('');
  let op = '', started = false;
  pts.forEach((p, i) => { if (p.op == null) return; op += (started ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(p.op).toFixed(1); started = true; });
  let grid = '';
  for (let v = 0; v <= ymax; v += 250) grid += '<line class="gr" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '"/><text class="ax" x="' + (L - 6) + '" y="' + (y(v) + 3) + '" text-anchor="end">' + v + '</text>';
  let xs = '';
  pts.forEach((p, i) => { if (p.d.endsWith('-01')) xs += '<text class="ax" x="' + x(i) + '" y="' + (H - 10) + '" text-anchor="middle">' + p.d.slice(0, 4) + '</text>'; });
  const peak = pts.reduce((a, p, i) => (p.core > pts[a].core ? i : a), 0);
  return '<div class="chart"><svg viewBox="0 0 ' + W + ' ' + H + '">' + grid + xs +
    '<path class="ln2" d="' + op + '"/><path class="ln" d="' + line + '"/>' +
    '<circle cx="' + x(peak) + '" cy="' + y(pts[peak].core) + '" r="4" fill="#b5412a"/><text class="note" x="' + (x(peak) - 8) + '" y="' + (y(pts[peak].core) - 8) + '" text-anchor="end">' + pts[peak].d + ' · ' + fmt(pts[peak].core) + ' people</text>' +
    '<text class="note" x="' + (W - R) + '" y="' + (y(pts[n - 1].core) - 8) + '" text-anchor="end">' + pts[n - 1].d + ' · ' + fmt(pts[n - 1].core) + '</text>' +
    '</svg><div class="cap"><span style="color:var(--accent);font-weight:600">—</span> people sleeping unsheltered, downtown core, monthly &nbsp; <span style="color:var(--mute)">- -</span> Outside Perimeter (from Apr 2021)</div></div>';
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ---------- snap: EyePop + number extraction ---------- */
const eyepopCfg = () => { try { return JSON.parse(localStorage.getItem('ora.eyepop') || '{}'); } catch (e) { return {}; } };
function extractNumbers(text) {
  const dollars = []; const re = /\$\s?(\d{1,3}(?:,\d{3})+|\d{3,5})(?:\.\d{2})?/g; let m;
  while ((m = re.exec(text))) { const v = parseInt(m[1].replace(/,/g, ''), 10); if (v >= 200 && v <= 20000 && !dollars.includes(v)) dollars.push(v); }
  const dm = text.match(/\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/i);
  return { dollars, date: dm ? dm[0] : null };
}
function foundHTML() {
  const f = S.snap.found; if (!f) return '';
  if (!f.dollars.length) return '<p class="fine">No dollar amounts found in the text. Type the numbers above and tap “Read the numbers”.</p>';
  const pick = S.snap.newRent || Math.max.apply(null, f.dollars);
  const cur = S.snap.curRent || (f.dollars.length > 1 ? Math.min.apply(null, f.dollars) : '');
  return '<p class="fine">Amounts found' + (f.date ? ' · effective ' + esc(f.date) : '') + '. Tap the <b>new</b> rent:</p>' +
    '<div class="found">' + f.dollars.map((d) => '<button class="' + (d === pick ? 'on' : '') + '" data-fn="pickRent:' + d + '">' + money(d) + '</button>').join('') + '</div>' +
    '<div class="field"><label>Rent before the notice</label><div class="in"><span>$</span><input id="curRent" inputmode="numeric" value="' + (cur ? fmt(cur) : '') + '" placeholder="1,850"></div></div>' +
    '<div class="field"><label>Tract (tap one on the map, or leave blank for the county)</label><div class="in"><input class="wide" id="snapTract" value="' + esc(S.snap.tract || '') + '" placeholder="06073…"></div></div>' +
    '<button class="btn" data-fn="snapRun">What does this raise do?</button>';
}
function verdictHTML() {
  const v = S.snap.verdict; if (!v) return '';
  return '<div class="verdict"><div class="n">+' + v.pctRaise.toFixed(0) + '% rent · ' + fmt(v.tipped) + ' households tipped</div><div class="l">' + esc(v.line) + '</div></div>';
}
let EP = null;
async function runEyePop(file) {
  const cfg = eyepopCfg();
  const st = document.getElementById('snapStatus');
  if (!cfg.key || !cfg.pop) { st.innerHTML = '<div class="status">EyePop.ai is not connected on this phone yet — open “EyePop.ai connection” below, or type the notice text.</div>'; return; }
  st.innerHTML = '<div class="status"><span class="sp"></span>Reading the notice with EyePop.ai…</div>';
  try {
    if (!window.EyePop) await new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/@eyepop.ai/eyepop/dist/eyepop.min.js'; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
    if (!EP) EP = await window.EyePop.workerEndpoint({ auth: { secretKey: cfg.key }, popId: cfg.pop }).connect();
    const results = await EP.process({ file: file, mimeType: file.type });
    const texts = [];
    const walk = (o) => { if (!o || typeof o !== 'object') return; if (typeof o.text === 'string') texts.push(o.text); if (typeof o.classLabel === 'string' && /\d/.test(o.classLabel)) texts.push(o.classLabel); Object.keys(o).forEach((k) => { const v = o[k]; if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v); }); };
    for await (const r of results) walk(r);
    S.snap.text = texts.join(' ');
    S.snap.found = extractNumbers(S.snap.text);
    st.innerHTML = '<div class="status">Read ' + texts.length + ' text block' + (texts.length === 1 ? '' : 's') + '.</div>';
    route(true);
  } catch (e) {
    st.innerHTML = '<div class="status">EyePop.ai call failed: ' + esc(e && e.message ? e.message : e) + '. Type the notice text below instead.</div>';
  }
}

/* ---------- actions ---------- */
FN.nav = (h) => go(h);
FN.lens = (k) => { S.lens = k; save(); route(true); };
FN.tract = (id) => {
  S.sel = id;
  document.querySelectorAll('.mapwrap path.sel').forEach((p) => p.classList.remove('sel'));
  const el = document.getElementById('t' + id); if (el) { el.classList.add('sel'); el.parentNode.appendChild(el); }
  if (location.hash.startsWith('#/cliff')) { const c = document.getElementById('tractCard'); if (c) { c.innerHTML = tractCard(id); c.scrollIntoView({ behavior: 'smooth', block: 'start' }); } }
  else if (location.hash.startsWith('#/signal')) sheet(tractCard(id));
  if (S.snap) S.snap.tract = id;
};
FN.zip = (z) => {
  const d = STORAGE.find((s) => s.zip === z); if (!d) return;
  const tops = STORAGE_SUM.top.filter((f) => f.zip === z);
  sheet('<div class="card"><h4>' + d.city + ' · ' + z + '</h4><div class="sub">' + d.n + ' lien-sale units · ' + d.f + ' facilities · 2026-06-12 → 07-02</div>' +
    (tops.length ? '<div class="list">' + tops.map((f) => '<div class="li"><div><div class="t">' + esc(f.name) + '</div><div class="s">' + f.chain + '</div></div><div class="n">' + f.n + '</div></div>').join('') + '</div>' : '') +
    '<p class="fine">Each unit is one household that stopped paying for what it owns. Facility locations are ZIP-level (addresses are not in the feed).</p></div>');
};
FN.epSave = () => { const pop = document.getElementById('epPop').value.trim(), key = document.getElementById('epKey').value.trim(); localStorage.setItem('ora.eyepop', JSON.stringify({ pop, key })); EP = null; toast(key ? 'EyePop.ai connected' : 'EyePop.ai cleared'); route(true); };
FN.snapParse = () => { const t = document.getElementById('snapText').value; S.snap.typed = t; S.snap.found = extractNumbers(t); S.snap.newRent = null; S.snap.verdict = null; route(true); };
FN.pickRent = (d) => { S.snap.newRent = +d; const cur = document.getElementById('curRent'); if (cur) S.snap.curRent = parseInt(cur.value.replace(/[^\d]/g, ''), 10) || null; route(true); };
FN.snapRun = () => {
  const f = S.snap.found; if (!f) return;
  const nw = S.snap.newRent || Math.max.apply(null, f.dollars);
  const cur = parseInt((document.getElementById('curRent').value || '').replace(/[^\d]/g, ''), 10);
  const tid = (document.getElementById('snapTract').value || '').trim();
  if (!cur || cur >= nw) { toast('Enter the rent before the notice (lower than the new rent)'); return; }
  const p = (nw / cur - 1) * 100;
  const r = SHOCKS.reduce((a, s) => (Math.abs(s - p) < Math.abs(a - p) ? s : a), 0);
  let tipped, line;
  if (tid && TRACTS[tid]) { const t = TRACTS[tid]; tipped = under(t, r, 'a') - under(t, 0, 'a'); line = 'In tract ' + tid + ', a raise like this one (modelled at +' + r + '%) pushes ' + fmt(tipped) + ' more households under their living budget — ' + fmt(under(t, r, 'a')) + ' of ' + fmt(nOf(t, 'a')) + ' after.'; }
  else { const T = totals(r, 'a'); tipped = T.tipped; line = 'County-wide, a raise like this one (modelled at +' + r + '%) pushes ' + fmt(tipped) + ' more households under their living budget. The notice adds ' + money(nw - cur) + ' a month to a bill the subsidy will not follow.'; }
  S.snap.verdict = { pctRaise: p, tipped, line }; S.raise = r; save(); route(true);
};

/* ---------- render ---------- */
function render(r) {
  const view = VIEWS[r.path] || VIEWS['#/home'];
  document.getElementById('app').innerHTML = view(r);
  const rg = document.getElementById('raise');
  if (rg) rg.addEventListener('input', () => {
    S.raise = SHOCKS[+rg.value]; rg.style.setProperty('--pct', (+rg.value / 8 * 100) + '%');
    document.getElementById('raiseVal').innerHTML = S.raise + '<small>%</small>';
    save(); repaint();
    const T = totals(S.raise, S.lens);
    const cc = document.getElementById('counters');
    if (S.lens === 'r') { const R = retireeTotals(S.raise, S.ss); cc.querySelectorAll('.n')[0].textContent = money(R.avgGap); cc.querySelectorAll('.n')[2].textContent = money(R.worst); }
    else { const ns = cc.querySelectorAll('.n'); ns[1].textContent = '+' + fmt(T.tipped); ns[2].textContent = pct(T.vr / T.n); }
    if (S.sel) document.getElementById('tractCard').innerHTML = tractCard(S.sel);
  });
  const ss = document.getElementById('ss');
  if (ss) ss.addEventListener('input', () => { const v = parseInt(ss.value.replace(/[^\d]/g, ''), 10); if (v > 0) { S.ss = v; save(); repaint(); const R = retireeTotals(S.raise, S.ss); const ns = document.querySelectorAll('#counters .n'); ns[0].textContent = money(R.avgGap); ns[1].innerHTML = R.afford + '<small style="font-size:14px;color:var(--dim)"> / ' + R.tracts + '</small>'; ns[2].textContent = money(R.worst); if (S.sel) document.getElementById('tractCard').innerHTML = tractCard(S.sel); } });
  const sf = document.getElementById('snapFile');
  if (sf) sf.addEventListener('change', () => { const f = sf.files && sf.files[0]; if (!f) return; const rd = new FileReader(); rd.onload = () => { S.snap.img = rd.result; S.snap.text = null; S.snap.found = null; S.snap.verdict = null; route(true); runEyePop(f); }; rd.readAsDataURL(f); });
  if (S.sel && document.getElementById('t' + S.sel)) { const el = document.getElementById('t' + S.sel); el.classList.add('sel'); el.parentNode.appendChild(el); if (r.path === '#/cliff') document.getElementById('tractCard').innerHTML = tractCard(S.sel); }
}

document.getElementById('appVersion').textContent = 'v' + APP_VERSION + ' · ' + STAGE;
