/* De AI-hulp van de meting: zeven stappen, van sleutel tot voorstel.
 *
 * Overgenomen uit procescheck (ai/bron/ai.js); kern.js is er byte-identiek aan, dit bestand wijkt op
 * vier punten af. Je kiest hier eerst een bron: het kolomcontract waar je naartoe omzet. Daaruit
 * bouwt deze pagina de systeemprompt en het schema, want dertig contracten in opdrachten.json zetten
 * zou dezelfde tabel twee keer onderhouden. Het samenvoegen van stukken gaat hier zonder sleutelveld,
 * want een omgezette tabel heeft geen code: de vololgorde van de rijen is de identiteit.
 *
 * Dit is het enige bestand dat naar buiten praat. De sleutel staat in sessionStorage en nergens anders;
 * het voorstel bevat de sha256 van de invoer, niet de invoer zelf en niet de sleutel. Het model krijgt
 * de systeemprompt plus de vaste regels en een stuk invoer; nooit je dossier en nooit de meetregels.
 */
(function () {
  'use strict';

  var OPDRACHTEN = window.__OPDRACHTEN__;
  var kern = window.kern;
  var SLEUTEL_OPSLAG = 'meting-ai-sleutel';
  var LEVERANCIER_OPSLAG = 'meting-ai-leverancier';
  // De bronnen (het kolomcontract per meetregel) komen uit meting/regels.json en gaan mee in de pagina.
  var BRONNEN = window.__BRONNEN__ || [];

  function el(id) { return document.getElementById(id); }
  function maak(tag, tekst, attributen) {
    var knoop = document.createElement(tag);
    if (tekst !== null && tekst !== undefined) knoop.textContent = String(tekst);
    if (attributen) Object.keys(attributen).forEach(function (n) { knoop.setAttribute(n, String(attributen[n])); });
    return knoop;
  }
  function leegMaken(knoop) { while (knoop.firstChild) knoop.removeChild(knoop.firstChild); return knoop; }
  function vandaag() {
    var nu = new Date();
    return nu.getFullYear() + '-' + String(nu.getMonth() + 1).padStart(2, '0') + '-' + String(nu.getDate()).padStart(2, '0');
  }
  function sha256(tekst) {
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(tekst)).then(function (buf) {
      return Array.prototype.map.call(new Uint8Array(buf), function (b) { return b.toString(16).padStart(2, '0'); }).join('');
    });
  }

  var stand = {
    leverancier: null, basis: '', model: '', sleutel: '', verbonden: false,
    opdracht: null, bron: null, invoerNaam: '', invoerTekst: '', toestemming: false,
    bezig: false, stoppen: false, voorstel: null
  };

  // ── Sleutel ───────────────────────────────────────────────────────────────

  function leesSleutel() {
    try { return window.sessionStorage.getItem(SLEUTEL_OPSLAG) || ''; } catch (f) { return ''; }
  }
  function bewaarSleutel(sleutel) {
    try {
      if (sleutel) window.sessionStorage.setItem(SLEUTEL_OPSLAG, sleutel);
      else window.sessionStorage.removeItem(SLEUTEL_OPSLAG);
    } catch (f) { /* privémodus: dan alleen in het geheugen */ }
  }

  // ── Stappen aan en uit ────────────────────────────────────────────────────

  function zetStap(id, actief) {
    el(id).setAttribute('data-actief', actief ? 'ja' : 'nee');
  }

  function werkStappenBij() {
    // Zonder gekozen bron valt er niets om te zetten: het contract bepaalt de kolommen en het schema.
    var gekozen = !!stand.opdracht && !!stand.bron;
    zetStap('stap-opdracht', stand.verbonden);
    zetStap('stap-invoer', stand.verbonden && gekozen);
    var heeftInvoer = stand.invoerTekst.trim().length > 0;
    zetStap('stap-toestemming', stand.verbonden && gekozen && heeftInvoer);
    zetStap('stap-uitvoeren', stand.verbonden && gekozen && heeftInvoer && stand.toestemming);
    el('knop-uitvoeren').disabled = !(stand.verbonden && gekozen && heeftInvoer && stand.toestemming) || stand.bezig;
    zetStap('stap-voorstel', !!stand.voorstel);
    zetStap('stap-verder', !!stand.voorstel);
    el('knop-verbinding').disabled = !stand.sleutel || !stand.basis;
    tekenToestemming();
  }

  // ── Stap 1: leverancier ───────────────────────────────────────────────────

  function kiesLeverancier(id, behoudVelden) {
    var lev = OPDRACHTEN.leveranciers.filter(function (l) { return l.id === id; })[0] || OPDRACHTEN.leveranciers[0];
    stand.leverancier = lev.id;
    if (!behoudVelden) {
      stand.basis = lev.basis;
      stand.model = lev.model;
      el('lev-basis').value = lev.basis;
      el('lev-model').value = lev.model;
    }
    el('lev-uitleg').textContent = lev.uitleg;
    try { window.localStorage.setItem(LEVERANCIER_OPSLAG, lev.id); } catch (f) { /* niets */ }
    stand.verbonden = false;
    el('lev-status').textContent = '';
    werkStappenBij();
  }

  function tekenLeveranciers() {
    var doel = leegMaken(el('lev-keuzes'));
    OPDRACHTEN.leveranciers.forEach(function (lev) {
      var label = maak('label', null, { 'class': 'vink' });
      var radio = maak('input', null, { type: 'radio', name: 'leverancier', value: lev.id, 'data-leverancier': lev.id });
      radio.addEventListener('change', function () { kiesLeverancier(lev.id, false); });
      label.appendChild(radio);
      label.appendChild(document.createTextNode(' ' + lev.naam));
      doel.appendChild(label);
    });
  }

  function testVerbinding() {
    var status = el('lev-status');
    status.textContent = 'verbinden...';
    status.className = '';
    stand.verbonden = false;
    return fetch(stand.basis.replace(/\/+$/, '') + '/v1/models', {
      method: 'GET', headers: { Authorization: 'Bearer ' + stand.sleutel }
    }).then(function (antwoord) {
      if (antwoord.status === 401 || antwoord.status === 403) throw new Error('sleutel geweigerd (HTTP ' + antwoord.status + ')');
      if (!antwoord.ok) throw new Error('HTTP ' + antwoord.status);
      stand.verbonden = true;
      status.textContent = 'verbonden';
      status.className = 'status-ok';
    }).catch(function (fout) {
      status.textContent = 'niet verbonden: ' + fout.message +
        (fout.message === 'Failed to fetch' ? ' (geen verbinding; bij Ollama: staat OLLAMA_ORIGINS goed?)' : '');
      status.className = 'status-fout';
    }).then(werkStappenBij);
  }

  // ── Stap 2 en 3: opdracht en invoer ───────────────────────────────────────

  function tekenOpdrachten() {
    var keuze = el('opdracht-keuze');
    keuze.appendChild(maak('option', 'kies een opdracht', { value: '' }));
    OPDRACHTEN.opdrachten.forEach(function (o) { keuze.appendChild(maak('option', o.titel, { value: o.id })); });
  }

  function opdrachtVan(id) {
    return OPDRACHTEN.opdrachten.filter(function (o) { return o.id === id; })[0] || null;
  }

  function bronVan(id) {
    return BRONNEN.filter(function (b) { return b.id === id; })[0] || null;
  }

  function tekenBronnen() {
    var keuze = el('bron-keuze');
    keuze.appendChild(maak('option', 'kies een bron', { value: '' }));
    BRONNEN.forEach(function (b) {
      keuze.appendChild(maak('option', b.titel + ' (' + b.items.join(', ') + ')', { value: b.id }));
    });
  }

  /* Het schema van de omzetting: precies de kolommen van het gekozen contract, plus het citaat.
     additionalProperties staat uit, zodat een model geen kolommen kan verzinnen. */
  function schemaVoor(bron) {
    var velden = {};
    bron.kolommen.concat(bron.optioneel).forEach(function (k) { velden[k] = { type: 'string' }; });
    velden.bronregel = { type: 'string' };
    return {
      type: 'object', additionalProperties: false, required: ['items', 'onzeker'],
      properties: {
        items: {
          type: 'array',
          items: {
            type: 'object', additionalProperties: false,
            required: bron.kolommen.concat(bron.optioneel).concat(['bronregel']),
            properties: velden
          }
        },
        onzeker: { type: 'array', items: { type: 'string' } }
      }
    };
  }

  function promptVoor(bron) {
    var regels = ['', 'Het contract heet ' + bron.id + ' (' + bron.titel + ').',
      'Verplichte kolommen: ' + bron.kolommen.join(', ') + '.'];
    if (bron.optioneel.length) {
      regels.push('Kolommen die meetellen als je ze kunt vullen: ' + bron.optioneel.join(', ') + '.');
    }
    if (bron.uitleg) regels.push('Wat het contract betekent: ' + bron.uitleg);
    regels.push('Gebruik precies deze kolomnamen, ook als de invoer ze anders noemt.');
    return regels.join('\n');
  }

  function kiesBron(id) {
    stand.bron = bronVan(id);
    var uitleg = leegMaken(el('bron-uitleg'));
    if (stand.bron) {
      uitleg.appendChild(maak('p', stand.bron.uitleg));
      var kolommen = maak('p', 'Kolommen: ', { 'class': 'klein' });
      kolommen.appendChild(maak('code', stand.bron.kolommen.join(', ')));
      if (stand.bron.optioneel.length) {
        kolommen.appendChild(maak('span', ' en, als je ze hebt: '));
        kolommen.appendChild(maak('code', stand.bron.optioneel.join(', ')));
      }
      uitleg.appendChild(kolommen);
      uitleg.appendChild(maak('p', 'Meet: ' + stand.bron.items.join(', '), { 'class': 'klein' }));
    }
    werkStappenBij();
  }

  function kiesOpdracht(id) {
    stand.opdracht = opdrachtVan(id);
    el('opdracht-uitleg').textContent = stand.opdracht ? stand.opdracht.uitleg : '';
    el('invoer-soorten').textContent = stand.opdracht ? stand.opdracht.invoer.filter(function (s) { return s !== 'tekst'; })
      .map(function (s) { return '.' + s; }).join(', ') : '';
    el('invoer-bestand').setAttribute('accept', stand.opdracht ? stand.opdracht.invoer
      .filter(function (s) { return s !== 'tekst'; }).map(function (s) { return '.' + s; }).join(',') : '');
    werkStappenBij();
  }

  function zetInvoer(naam, tekst) {
    stand.invoerNaam = naam;
    stand.invoerTekst = tekst;
    el('invoer-tekst').value = tekst;
    var stukken = kern.chunk(tekst, OPDRACHTEN.grenzen.max_tekens_per_aanroep);
    el('invoer-info').textContent = tekst.trim() ? (naam ? naam + ': ' : '') + tekst.length + ' tekens, ' +
      stukken.length + ' aanroep' + (stukken.length === 1 ? '' : 'en') : '';
    stand.toestemming = false;
    el('toestemming').checked = false;
    werkStappenBij();
  }

  function leesBestand(bestand) {
    var naam = bestand.name;
    if (/\.xlsx$/i.test(naam)) {
      return bestand.arrayBuffer().then(kern.xlsx_naar_tekst).then(function (tekst) { zetInvoer(naam, tekst); });
    }
    return bestand.text().then(function (tekst) {
      zetInvoer(naam, /\.csv$/i.test(naam) ? kern.csv_naar_tekst(tekst) : tekst);
    });
  }

  // ── Stap 4: toestemming ───────────────────────────────────────────────────

  function tekenToestemming() {
    var doel = leegMaken(el('toestemming-tekst'));
    if (!stand.opdracht || !stand.bron || !stand.invoerTekst.trim()) return;
    var stukken = kern.chunk(stand.invoerTekst, OPDRACHTEN.grenzen.max_tekens_per_aanroep);
    doel.appendChild(maak('p', 'Wat er verstuurd wordt: ' + (stand.invoerNaam ? 'het bestand ' + stand.invoerNaam :
      'de geplakte tekst') + ' (' + stand.invoerTekst.length + ' tekens, in ' + stukken.length + ' aanroep' +
      (stukken.length === 1 ? '' : 'en') + '), met de vraag om er ' + stand.bron.id + ' van te maken.'));
    doel.appendChild(maak('p', 'Waarheen: ' + stand.basis + ' (model ' + stand.model + '), onder de voorwaarden van die leverancier.'));
    doel.appendChild(maak('p', 'Wat er niet gaat: je dossier, je sleutel in een bestand, en de meetregels zelf. Het model zet alleen kolommen om; toetsen doet de tool.'));
  }

  // ── Stap 5: uitvoeren ─────────────────────────────────────────────────────

  function wacht(ms) { return new Promise(function (klaar) { setTimeout(klaar, ms); }); }

  function roepAan(berichten, schema, vorm) {
    var body = { model: stand.model, messages: berichten, temperature: 0, response_format: vorm };
    return fetch(stand.basis.replace(/\/+$/, '') + '/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + stand.sleutel },
      body: JSON.stringify(body)
    });
  }

  /* Eerst json_schema; bij een 400 daarover terugvallen op json_object. Bij 429 wachten en opnieuw. */
  function vraagModel(berichten, schema, meld) {
    var vormen = [
      { type: 'json_schema', json_schema: { name: 'voorstel', schema: schema, strict: true } },
      { type: 'json_object' }
    ];
    var wachttijden = OPDRACHTEN.grenzen.wachttijden_bij_429_seconden;
    function probeer(vormIndex, poging) {
      if (stand.stoppen) return Promise.reject(new Error('gestopt'));
      return roepAan(berichten, schema, vormen[vormIndex]).then(function (antwoord) {
        if (antwoord.status === 400 && vormIndex === 0) {
          meld('json_schema niet geaccepteerd, opnieuw met json_object');
          return probeer(1, 0);
        }
        if (antwoord.status === 429 && poging < wachttijden.length) {
          meld('te veel verzoeken, wachten ' + wachttijden[poging] + ' s');
          return wacht(wachttijden[poging] * 1000).then(function () { return probeer(vormIndex, poging + 1); });
        }
        if (antwoord.status === 401 || antwoord.status === 403) throw new Error('sleutel geweigerd (HTTP ' + antwoord.status + ')');
        if (!antwoord.ok) throw new Error('HTTP ' + antwoord.status);
        return antwoord.json().then(function (data) {
          return data.choices[0].message.content;
        });
      });
    }
    return probeer(0, 0);
  }

  function voerUit() {
    if (stand.bezig) return;
    stand.bezig = true;
    stand.stoppen = false;
    stand.voorstel = null;
    el('knop-stoppen').disabled = false;
    werkStappenBij();
    var voortgang = el('voortgang');
    var opdracht = stand.opdracht;
    var stukken = kern.chunk(stand.invoerTekst, OPDRACHTEN.grenzen.max_tekens_per_aanroep)
      .slice(0, OPDRACHTEN.grenzen.max_aanroepen_per_opdracht);
    var schema = schemaVoor(stand.bron);
    var systeem = opdracht.systeemprompt + promptVoor(stand.bron) + '\n\n' + OPDRACHTEN.vaste_regels;
    var delen = [], waarschuwingen = [];
    var teller = 0;

    function meld(tekst) { voortgang.textContent = 'aanroep ' + (teller + 1) + ' van ' + stukken.length + ': ' + tekst; }

    function volgende() {
      if (teller >= stukken.length) return Promise.resolve();
      meld('bezig');
      var berichten = [{ role: 'system', content: systeem }, { role: 'user', content: stukken[teller] }];
      return vraagModel(berichten, schema, meld).then(function (ruw) {
        var uitkomst = kern.parse_antwoord(schema, ruw);
        if (uitkomst.fouten.length) {
          meld('antwoord voldeed niet aan het schema, een keer opnieuw');
          berichten.push({ role: 'assistant', content: ruw });
          berichten.push({ role: 'user', content: 'Je antwoord voldeed niet aan het schema: ' +
            uitkomst.fouten.slice(0, 5).join('; ') + '. Antwoord opnieuw, alleen JSON.' });
          return vraagModel(berichten, schema, meld).then(function (ruw2) {
            var tweede = kern.parse_antwoord(schema, ruw2);
            if (tweede.fouten.length) {
              waarschuwingen.push('Aanroep ' + (teller + 1) + ' gaf twee keer een ongeldig antwoord en is overgeslagen: ' + tweede.fouten[0]);
            } else {
              waarschuwingen.push('Aanroep ' + (teller + 1) + ' gaf eerst ongeldige JSON en is een keer opnieuw gedaan.');
              delen.push(tweede.data);
            }
          });
        }
        delen.push(uitkomst.data);
      }).then(function () { teller += 1; return volgende(); });
    }

    volgende().then(function () {
      return sha256(stand.invoerTekst);
    }).then(function (hash) {
      var samen = voegSamen(delen);
      var voorstel = {
        formaat: OPDRACHTEN.voorstel_formaat, versie: 1, tool: OPDRACHTEN.tool,
        opdrachten_versie: OPDRACHTEN.versie, tool_vingerafdruk: OPDRACHTEN.tool_vingerafdruk,
        opdracht: opdracht.id, bron: stand.bron.id, gemaakt: vandaag(),
        leverancier: stand.leverancier, model: stand.model,
        invoer: { naam: stand.invoerNaam || 'geplakte tekst', sha256: hash, tekens: stand.invoerTekst.length, aanroepen: stukken.length },
        onzeker: samen.onzeker, waarschuwingen: waarschuwingen.concat(samen.waarschuwingen)
      };
      // Het citaat toetsen kan alleen hier: de tool krijgt de invoer niet, alleen zijn sha256.
      voorstel.items = samen.items.map(function (rij) {
        var kopie = {};
        Object.keys(rij).forEach(function (k) { kopie[k] = rij[k]; });
        kopie.bronregel_klopt = kern.bronregel_klopt(rij, stand.invoerTekst);
        return kopie;
      });
      stand.voorstel = voorstel;
      voortgang.textContent = 'klaar: ' + stukken.length + ' aanroep' + (stukken.length === 1 ? '' : 'en') + '.';
      tekenVoorstel();
    }).catch(function (fout) {
      voortgang.textContent = fout.message === 'gestopt' ? 'gestopt' : 'mislukt: ' + fout.message +
        (fout.message === 'Failed to fetch' ? ' (geen verbinding; staat de endpoint in de CSP van deze pagina, en bij Ollama OLLAMA_ORIGINS?)' : '');
    }).then(function () {
      stand.bezig = false;
      el('knop-stoppen').disabled = true;
      werkStappenBij();
    });
  }

  /* kern.voeg_stukken_samen ontdubbelt op een sleutelveld (code of id). Een omgezette tabel heeft dat
     niet: twee rijen mogen identiek zijn, en de volgorde is de identiteit. Daarom hier gewoon achter
     elkaar plakken, met de meldingen samengevoegd. */
  function voegSamen(delen) {
    var uit = { items: [], onzeker: [], waarschuwingen: [] };
    delen.forEach(function (deel) {
      (deel.items || []).forEach(function (rij) { uit.items.push(rij); });
      (deel.onzeker || []).forEach(function (regel) {
        if (uit.onzeker.indexOf(regel) < 0) uit.onzeker.push(regel);
      });
    });
    return uit;
  }

  // ── Stap 6: voorstel ──────────────────────────────────────────────────────

  function tekenVoorstel() {
    var v = stand.voorstel;
    var tabel = leegMaken(el('tabel-voorstel'));
    var records = v.items || v.nodes || [];
    var kolommen = records.length ? Object.keys(records[0]).filter(function (k) { return k !== 'bronregel'; }) : [];
    var thead = maak('thead'), kop = maak('tr');
    kolommen.concat(['citaat uit de bron']).forEach(function (k) { kop.appendChild(maak('th', k, { scope: 'col' })); });
    thead.appendChild(kop);
    tabel.appendChild(thead);
    var tbody = maak('tbody');
    var nietInBron = 0;
    records.forEach(function (r) {
      var klopt = kern.bronregel_klopt(r, stand.invoerTekst);
      if (!klopt) nietInBron += 1;
      var tr = maak('tr', null, { 'data-item': r.code || r.id, 'class': klopt ? '' : 'niet-in-bron' });
      kolommen.forEach(function (k) {
        tr.appendChild(maak('td', typeof r[k] === 'boolean' ? (r[k] ? 'ja' : 'nee') : r[k]));
      });
      tr.appendChild(maak('td', (klopt ? '' : 'niet in de bron: ') + r.bronregel, { 'class': 'tekst' }));
      tbody.appendChild(tr);
    });
    tabel.appendChild(tbody);
    el('voorstel-samenvatting').textContent = records.length + ' ' + (v.nodes ? 'nodes en ' + v.edges.length + ' relaties' : 'items') +
      (nietInBron ? ', waarvan ' + nietInBron + ' met een citaat dat niet in de bron staat (die staan standaard op overslaan)' : '') + '.';
    var onzeker = leegMaken(el('onzeker'));
    (v.onzeker.length ? v.onzeker : ['niets gemeld']).forEach(function (t) { onzeker.appendChild(maak('li', t)); });
    var waarschuwingen = leegMaken(el('waarschuwingen'));
    v.waarschuwingen.forEach(function (t) { waarschuwingen.appendChild(maak('p', t, { 'class': 'waarschuwing' })); });
  }

  function slaVoorstelOp() {
    var v = stand.voorstel;
    var blob = new Blob([JSON.stringify(v, null, 1)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = 'meting-voorstel-' + v.bron + '-' + v.gemaakt + '.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  }

  // ── Opstarten ─────────────────────────────────────────────────────────────

  function start() {
    el('versie').textContent = 'opdrachten ' + OPDRACHTEN.versie + ' · tool ' + String(OPDRACHTEN.tool_vingerafdruk).slice(0, 12);
    tekenLeveranciers();
    tekenOpdrachten();
    tekenBronnen();

    var onthouden = null;
    try { onthouden = window.localStorage.getItem(LEVERANCIER_OPSLAG); } catch (f) { onthouden = null; }
    var eerste = onthouden || OPDRACHTEN.leveranciers[0].id;
    document.querySelector('[data-leverancier="' + eerste + '"]').checked = true;
    kiesLeverancier(eerste, false);
    stand.sleutel = leesSleutel();
    el('lev-sleutel').value = stand.sleutel;

    el('lev-basis').addEventListener('input', function () { stand.basis = el('lev-basis').value.trim(); stand.verbonden = false; werkStappenBij(); });
    el('lev-model').addEventListener('input', function () { stand.model = el('lev-model').value.trim(); });
    el('lev-sleutel').addEventListener('input', function () {
      stand.sleutel = el('lev-sleutel').value.trim();
      bewaarSleutel(stand.sleutel);
      stand.verbonden = false;
      werkStappenBij();
    });
    el('knop-verbinding').addEventListener('click', testVerbinding);
    el('knop-sleutel-vergeten').addEventListener('click', function () {
      stand.sleutel = '';
      el('lev-sleutel').value = '';
      bewaarSleutel('');
      stand.verbonden = false;
      el('lev-status').textContent = 'sleutel vergeten';
      el('lev-status').className = '';
      werkStappenBij();
    });

    el('opdracht-keuze').addEventListener('change', function () { kiesOpdracht(el('opdracht-keuze').value); });
    el('bron-keuze').addEventListener('change', function () { kiesBron(el('bron-keuze').value); });
    el('invoer-tekst').addEventListener('input', function () { zetInvoer('', el('invoer-tekst').value); });
    el('knop-invoer-bestand').addEventListener('click', function () { el('invoer-bestand').click(); });
    el('invoer-bestand').addEventListener('change', function (g) {
      var bestand = g.target.files[0];
      if (bestand) leesBestand(bestand).catch(function (fout) { el('invoer-info').textContent = 'niet te lezen: ' + fout.message; });
      g.target.value = '';
    });
    el('toestemming').addEventListener('change', function () { stand.toestemming = el('toestemming').checked; werkStappenBij(); });
    el('knop-uitvoeren').addEventListener('click', voerUit);
    el('knop-stoppen').addEventListener('click', function () { stand.stoppen = true; });
    el('knop-voorstel-opslaan').addEventListener('click', slaVoorstelOp);

    werkStappenBij();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
