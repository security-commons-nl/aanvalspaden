/* De deterministische kern van de AI-hulp, gespiegeld uit ai/kern.py onder dezelfde namen.
 *
 * Dit bestand gaat ook mee in de tool zelf (voor vergelijk en pas_toe) en kent daarom GEEN netwerk:
 * geen fetch, geen XMLHttpRequest. De aanroep van de leverancier zit alleen in ai.js.
 */
(function () {
  'use strict';

  var kern = {};

  // ── Schema-controle ───────────────────────────────────────────────────────

  var TYPEN = {
    object: function (w) { return w !== null && typeof w === 'object' && !Array.isArray(w); },
    array: function (w) { return Array.isArray(w); },
    string: function (w) { return typeof w === 'string'; },
    boolean: function (w) { return typeof w === 'boolean'; },
    number: function (w) { return typeof w === 'number'; },
    integer: function (w) { return typeof w === 'number' && Math.floor(w) === w; },
    'null': function (w) { return w === null; }
  };

  function typeNaam(w) {
    if (w === null) return 'null';
    if (Array.isArray(w)) return 'list';
    return { string: 'str', number: 'float', boolean: 'bool', object: 'dict' }[typeof w] || typeof w;
  }

  kern.valideer = function (schema, data, pad) {
    pad = pad || '';
    var fouten = [];
    var hier = pad || '(wortel)';
    var soort = schema.type;
    if (soort && !TYPEN[soort](data)) {
      return [hier + ': verwacht ' + soort + ', kreeg ' + typeNaam(data)];
    }
    if (schema['enum'] && schema['enum'].indexOf(data) < 0) {
      return [hier + ': waarde ' + JSON.stringify(data) + ' niet uit ' + JSON.stringify(schema['enum'])];
    }
    if (soort === 'object') {
      (schema.required || []).forEach(function (veld) {
        if (!(veld in data)) fouten.push(hier + ": veld '" + veld + "' ontbreekt");
      });
      var eigenschappen = schema.properties || {};
      if (schema.additionalProperties === false) {
        Object.keys(data).forEach(function (veld) {
          if (!(veld in eigenschappen)) fouten.push(hier + ": onbekend veld '" + veld + "'");
        });
      }
      Object.keys(eigenschappen).forEach(function (veld) {
        if (veld in data) {
          fouten = fouten.concat(kern.valideer(eigenschappen[veld], data[veld], pad ? pad + '.' + veld : veld));
        }
      });
    } else if (soort === 'array' && schema.items) {
      data.forEach(function (item, i) {
        fouten = fouten.concat(kern.valideer(schema.items, item, pad + '[' + i + ']'));
      });
    }
    return fouten;
  };

  kern.strip_hekken = function (tekst) {
    var t = String(tekst).trim();
    var m = t.match(/^```[a-zA-Z]*\s*\n([\s\S]*?)\n?```\s*$/);
    return m ? m[1].trim() : t;
  };

  kern.parse_antwoord = function (schema, tekst) {
    var schoon = kern.strip_hekken(tekst);
    var data;
    try {
      data = JSON.parse(schoon);
    } catch (fout) {
      return { data: null, fouten: ['geen geldige JSON: ' + fout.message] };
    }
    var fouten = kern.valideer(schema, data);
    return { data: fouten.length ? null : data, fouten: fouten };
  };

  // ── Chunking en samenvoegen ───────────────────────────────────────────────

  kern.chunk = function (tekst, maxTekens) {
    tekst = String(tekst).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    if (tekst.length <= maxTekens) return tekst.trim() ? [tekst] : [];
    var stukken = [], huidig = '';
    function sluitAf() {
      if (huidig.trim()) stukken.push(huidig.replace(/\n+$/, ''));
      huidig = '';
    }
    tekst.split('\n\n').forEach(function (alinea) {
      var blok = alinea + '\n\n';
      if (blok.length > maxTekens) {
        alinea.split('\n').forEach(function (regel) {
          var r = regel + '\n';
          if (huidig.length + r.length > maxTekens) sluitAf();
          huidig += r;
        });
        huidig += '\n';
        return;
      }
      if (huidig.length + blok.length > maxTekens) sluitAf();
      huidig += blok;
    });
    sluitAf();
    return stukken;
  };

  kern.voeg_stukken_samen = function (opdracht, delen) {
    var uit = { onzeker: [], waarschuwingen: [] };
    var sleutels = ['items', 'nodes', 'edges'].filter(function (k) { return k in opdracht.schema.properties; });
    sleutels.forEach(function (k) { uit[k] = []; });
    var gezien = { items: {}, nodes: {} };
    delen.forEach(function (deel, index) {
      var i = index + 1;
      sleutels.forEach(function (k) {
        (deel[k] || []).forEach(function (record) {
          record = Object.assign({}, record);
          var sleutelveld = k === 'items' ? 'code' : (k === 'nodes' ? 'id' : null);
          if (sleutelveld) {
            var basis = record[sleutelveld] || '', waarde = basis, n = 1;
            while (gezien[k][waarde]) { n += 1; waarde = basis + '-' + n; }
            if (waarde !== basis) {
              uit.waarschuwingen.push(sleutelveld + ' ' + basis + ' kwam vaker voor (stuk ' + i + '); hernoemd naar ' + waarde);
            }
            record[sleutelveld] = waarde;
            gezien[k][waarde] = true;
          }
          uit[k].push(record);
        });
      });
      (deel.onzeker || []).forEach(function (regel) {
        if (uit.onzeker.indexOf(regel) < 0) uit.onzeker.push(regel);
      });
    });
    return uit;
  };

  // ── Invoer lezen ──────────────────────────────────────────────────────────

  function splitsCsvRegel(regel) {
    var uit = [], huidig = '', inAanhaling = false;
    for (var i = 0; i < regel.length; i++) {
      var teken = regel[i];
      if (inAanhaling) {
        if (teken === '"' && regel[i + 1] === '"') { huidig += '"'; i++; }
        else if (teken === '"') inAanhaling = false;
        else huidig += teken;
      } else if (teken === '"') inAanhaling = true;
      else if (teken === ',') { uit.push(huidig); huidig = ''; }
      else huidig += teken;
    }
    uit.push(huidig);
    return uit;
  }

  kern.rijen_naar_tekst = function (rijen) {
    rijen = rijen.filter(function (r) { return r.some(function (c) { return String(c).trim() !== ''; }); });
    if (!rijen.length) return '';
    var breedte = Math.max.apply(null, rijen.map(function (r) { return r.length; }));
    rijen = rijen.map(function (r) {
      var kopie = r.slice();
      while (kopie.length < breedte) kopie.push('');
      return kopie;
    });
    function cel(c) { return String(c).trim().replace(/\|/g, '/'); }
    var kop = '| ' + rijen[0].map(cel).join(' | ') + ' |';
    var lijn = '|' + new Array(breedte + 1).join('---|');
    var lijf = rijen.slice(1).map(function (r) { return '| ' + r.map(cel).join(' | ') + ' |'; });
    return [kop, lijn].concat(lijf).join('\n') + '\n';
  };

  kern.csv_naar_tekst = function (tekst) {
    var regels = String(tekst).replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n')
      .filter(function (r) { return r.trim() !== ''; });
    return kern.rijen_naar_tekst(regels.map(splitsCsvRegel));
  };

  /* Een xlsx is een zip. Zonder bibliotheek: de centrale directory lezen, elk deel inflaten met
     DecompressionStream('deflate-raw'), en de XML met DOMParser lezen. Eerste werkblad, inline strings,
     gedeelde strings en getallen; geen formules of opmaak. Geeft een Promise van rijen. */
  function lees32(bytes, i) { return bytes[i] | (bytes[i + 1] << 8) | (bytes[i + 2] << 16) | ((bytes[i + 3] << 24) >>> 0); }
  function lees16(bytes, i) { return bytes[i] | (bytes[i + 1] << 8); }

  function zipDelen(bytes) {
    var eocd = -1;
    for (var i = bytes.length - 22; i >= 0 && i >= bytes.length - 66000; i--) {
      if (lees32(bytes, i) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error('geen zip-bestand');
    var aantal = lees16(bytes, eocd + 10), start = lees32(bytes, eocd + 16);
    var delen = {}, p = start;
    var decoder = new TextDecoder('utf-8');
    for (var n = 0; n < aantal; n++) {
      if (lees32(bytes, p) !== 0x02014b50) break;
      var methode = lees16(bytes, p + 10), gecomprimeerd = lees32(bytes, p + 20), grootte = lees32(bytes, p + 24);
      var naamLengte = lees16(bytes, p + 28), extraLengte = lees16(bytes, p + 30), commentaarLengte = lees16(bytes, p + 32);
      var lokaal = lees32(bytes, p + 42);
      var naam = decoder.decode(bytes.subarray(p + 46, p + 46 + naamLengte));
      var lokaalNaam = lees16(bytes, lokaal + 26), lokaalExtra = lees16(bytes, lokaal + 28);
      var dataStart = lokaal + 30 + lokaalNaam + lokaalExtra;
      delen[naam] = { methode: methode, data: bytes.subarray(dataStart, dataStart + gecomprimeerd), grootte: grootte };
      p += 46 + naamLengte + extraLengte + commentaarLengte;
    }
    return delen;
  }

  function inflate(deel) {
    if (deel.methode === 0) return Promise.resolve(new TextDecoder('utf-8').decode(deel.data));
    if (deel.methode !== 8) return Promise.reject(new Error('onbekende compressie ' + deel.methode));
    var stroom = new Blob([deel.data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return new Response(stroom).text();
  }

  function kolomIndex(ref) {
    var letters = (ref.match(/^[A-Z]+/) || ['A'])[0], kolom = 0;
    for (var i = 0; i < letters.length; i++) kolom = kolom * 26 + (letters.charCodeAt(i) - 64);
    return kolom - 1;
  }

  kern.xlsx_naar_rijen = function (arrayBuffer) {
    var bytes = new Uint8Array(arrayBuffer);
    var delen = zipDelen(bytes);
    var bladen = Object.keys(delen).filter(function (n) { return /^xl\/worksheets\/sheet\d+\.xml$/.test(n); }).sort();
    if (!bladen.length) return Promise.resolve([]);
    var parser = new DOMParser();
    var gedeeldBelofte = delen['xl/sharedStrings.xml'] ? inflate(delen['xl/sharedStrings.xml']).then(function (xml) {
      var doc = parser.parseFromString(xml, 'application/xml');
      return Array.prototype.map.call(doc.getElementsByTagName('si'), function (si) {
        return Array.prototype.map.call(si.getElementsByTagName('t'), function (t) { return t.textContent; }).join('');
      });
    }) : Promise.resolve([]);
    return Promise.all([gedeeldBelofte, inflate(delen[bladen[0]])]).then(function (uitkomsten) {
      var gedeeld = uitkomsten[0];
      var doc = parser.parseFromString(uitkomsten[1], 'application/xml');
      var rijen = [];
      Array.prototype.forEach.call(doc.getElementsByTagName('row'), function (rij) {
        var cellen = {}, maxKolom = -1;
        Array.prototype.forEach.call(rij.getElementsByTagName('c'), function (c) {
          var kolom = kolomIndex(c.getAttribute('r') || 'A');
          var soort = c.getAttribute('t') || '', waarde = '';
          if (soort === 'inlineStr') {
            waarde = Array.prototype.map.call(c.getElementsByTagName('t'), function (t) { return t.textContent; }).join('');
          } else {
            var v = c.getElementsByTagName('v')[0];
            if (v && v.textContent !== null) {
              waarde = (soort === 's' && /^\d+$/.test(v.textContent)) ? gedeeld[parseInt(v.textContent, 10)] : v.textContent;
            }
          }
          cellen[kolom] = waarde;
          if (kolom > maxKolom) maxKolom = kolom;
        });
        if (maxKolom >= 0) {
          var r = [];
          for (var i = 0; i <= maxKolom; i++) r.push(cellen[i] === undefined ? '' : cellen[i]);
          rijen.push(r);
        }
      });
      return rijen;
    });
  };

  kern.xlsx_naar_tekst = function (arrayBuffer) {
    return kern.xlsx_naar_rijen(arrayBuffer).then(kern.rijen_naar_tekst);
  };

  // ── Vergelijken en toepassen ──────────────────────────────────────────────

  function norm(tekst) {
    return String(tekst === null || tekst === undefined ? '' : tekst)
      .replace(/[*#`|_>]/g, ' ').split(/\s+/).filter(Boolean).join(' ').toLowerCase();
  }

  kern.bronregel_klopt = function (item, invoer) {
    var tekst = norm(invoer);
    var citaat = String(item.bronregel || '');
    var stukken = citaat.split(/(?<=[.;:!?])\s+|\s*\|\s*|\.\.\.|…/).map(norm);
    var lang = stukken.filter(function (s) { return s.length >= 12; });
    if (!lang.length) {
      var heel = norm(citaat);
      return !!heel && tekst.indexOf(heel) >= 0;
    }
    return lang.every(function (s) { return tekst.indexOf(s) >= 0; });
  };

  kern.vergelijk = function (dossier, voorstel, invoer) {
    var opdracht = voorstel.opdracht, uit = [];
    var metBron = invoer !== undefined && invoer !== null;
    if (opdracht === 'processen' || opdracht === 'applicaties') {
      var bestaand = dossier[opdracht] || [];
      var perCode = {}, perNaam = {};
      bestaand.forEach(function (p) { perCode[p.code] = p; if (norm(p.naam)) perNaam[norm(p.naam)] = p; });
      (voorstel.items || []).forEach(function (item) {
        var status = 'nieuw', huidig = null;
        if (item.code in perCode) {
          huidig = perCode[item.code];
          status = (norm(huidig.naam) === norm(item.naam) || !norm(huidig.naam)) ? 'bestaand' : 'conflict';
        } else if (norm(item.naam) in perNaam) {
          huidig = perNaam[norm(item.naam)];
          status = 'bestaand';
        }
        if (metBron && !kern.bronregel_klopt(item, invoer)) status = 'niet_in_bron';
        uit.push({ sleutel: item.code, status: status, item: item, huidig_code: huidig ? huidig.code : null });
      });
    } else if (opdracht === 'landschap') {
      var ci = {}, apps = {}, procs = {};
      (dossier.componenten || []).forEach(function (c) { ci[c.id] = true; });
      (dossier.applicaties || []).forEach(function (a) { apps[a.code] = true; });
      (dossier.processen || []).forEach(function (p) { procs[p.code] = true; });
      (voorstel.nodes || []).forEach(function (node) {
        var bekend = node.type === 'ci' ? ci[node.id] : node.type === 'app' ? apps[node.id] : procs[node.id];
        var status = bekend ? 'bestaand' : 'nieuw';
        if (metBron && !kern.bronregel_klopt(node, invoer)) status = 'niet_in_bron';
        uit.push({ sleutel: node.id, status: status, item: node, huidig_code: bekend ? node.id : null });
      });
      var paren = {};
      (dossier.component_edges || []).forEach(function (e) { paren[e.from + '|' + e.to] = true; });
      (dossier.processen || []).forEach(function (p) {
        (p.applicaties || []).forEach(function (a) { paren[a + '|' + p.code] = true; });
      });
      (voorstel.edges || []).forEach(function (edge) {
        var status = paren[edge.from + '|' + edge.to] ? 'bestaand' : 'nieuw';
        if (metBron && !kern.bronregel_klopt(edge, invoer)) status = 'niet_in_bron';
        uit.push({ sleutel: edge.from + '|' + edge.to, status: status, item: edge, huidig_code: null });
      });
    }
    return uit;
  };

  kern.standaardkeuze = function (status) {
    return { nieuw: 'overnemen', bestaand: 'samenvoegen', conflict: 'overslaan', niet_in_bron: 'overslaan' }[status];
  };

  var PROCESVELDEN = ['naam', 'beschrijving', 'doelstelling', 'eigenaar', 'afdeling', 'reden_kritiek'];
  var APPVELDEN = ['naam', 'beschrijving', 'eigenaar_business', 'eigenaar_technisch', 'soort'];
  var CONTEXTVELDEN = ['partners', 'activiteiten', 'middelen', 'propositie', 'klantrelaties', 'kanalen', 'segmenten',
    'kosten', 'opbrengsten', 'wettelijke_basis', 'stakeholders', 'ketenpositie', 'kernaspecten', 'continuiteitseisen',
    'reviewdatum', 'notities'];

  function leegProces(code) {
    var bia = { onderbouwing: {} };
    ['b1', 'b2', 'b3', 'b4', 'i1', 'v1'].forEach(function (k) { bia[k] = null; bia.onderbouwing[k] = ''; });
    bia.interviewer = ''; bia.interviewdatum = ''; bia.beschrijving = ''; bia.ketenafhankelijkheden = '';
    bia.afwijking_eigenaar = ''; bia.notities = '';
    var context = {};
    CONTEXTVELDEN.forEach(function (v) { context[v] = ''; });
    context.persoonsgegevens = false; context.bijzondere_persoonsgegevens = false;
    return { code: code, naam: '', beschrijving: '', doelstelling: '', eigenaar: '', afdeling: '', kritiek: false,
      reden_kritiek: '', laatste_beoordeling: '', notities: '', applicaties: [], bia: bia,
      rto_rpo: { rto: '', rto_eenheid: '', rpo: '', rpo_eenheid: '', toelichting: '' }, context: context };
  }

  function legeApp(code) {
    return { code: code, naam: '', beschrijving: '', eigenaar_business: '', eigenaar_technisch: '', soort: 'applicatie',
      csir_dossier: { bestand: '', vingerafdruk: '' }, notities: '', reviewdatum: '' };
  }

  function leeg(w) { return String(w === null || w === undefined ? '' : w).trim() === ''; }

  kern.pas_toe = function (dossier, voorstel, keuzes) {
    keuzes = keuzes || {};
    var nieuw = JSON.parse(JSON.stringify(dossier));
    var telling = { overgenomen: 0, samengevoegd: 0, overgeslagen: 0 };
    var opdracht = voorstel.opdracht;
    var vergelijking = kern.vergelijk(dossier, voorstel);

    if (opdracht === 'processen' || opdracht === 'applicaties') {
      if (!nieuw[opdracht]) nieuw[opdracht] = [];
      var lijst = nieuw[opdracht], perCode = {};
      lijst.forEach(function (p) { perCode[p.code] = p; });
      var velden = opdracht === 'processen' ? PROCESVELDEN : APPVELDEN;
      var maak = opdracht === 'processen' ? leegProces : legeApp;
      vergelijking.forEach(function (regel) {
        var keuze = keuzes[regel.sleutel] || kern.standaardkeuze(regel.status);
        var item = regel.item;
        if (keuze === 'overslaan') { telling.overgeslagen += 1; return; }
        if (keuze === 'samenvoegen' && !regel.huidig_code) keuze = 'overnemen';
        if (keuze === 'overnemen') {
          var doel = perCode[item.code];
          if (!doel) { doel = maak(item.code); lijst.push(doel); perCode[item.code] = doel; }
          velden.forEach(function (veld) { doel[veld] = item[veld] !== undefined ? item[veld] : (doel[veld] || ''); });
          if (opdracht === 'processen') doel.kritiek = !!item.kritiek;
          telling.overgenomen += 1;
        } else {
          var bestaand = perCode[regel.huidig_code];
          velden.forEach(function (veld) { if (leeg(bestaand[veld]) && item[veld]) bestaand[veld] = item[veld]; });
          if (opdracht === 'processen' && item.kritiek && !bestaand.kritiek) bestaand.kritiek = true;
          telling.samengevoegd += 1;
        }
      });
    } else if (opdracht === 'landschap') {
      var apps = {}, procs = {}, ci = {}, typen = {};
      (nieuw.applicaties || []).forEach(function (a) { apps[a.code] = true; });
      (nieuw.processen || []).forEach(function (p) { procs[p.code] = p; });
      if (!nieuw.componenten) nieuw.componenten = [];
      nieuw.componenten.forEach(function (c) { ci[c.id] = c; });
      vergelijking.forEach(function (regel) {
        var item = regel.item;
        if ('type' in item) typen[item.id] = item.type;
        var keuze = keuzes[regel.sleutel] || kern.standaardkeuze(regel.status);
        if (keuze === 'overslaan') { telling.overgeslagen += 1; return; }
        if ('type' in item) {
          if (item.type === 'ci') {
            if (!ci[item.id]) {
              ci[item.id] = { id: item.id, label: item.label || item.id, kritiek: !!item.kritiek };
              nieuw.componenten.push(ci[item.id]);
              telling.overgenomen += 1;
            } else { if (item.kritiek) ci[item.id].kritiek = true; telling.samengevoegd += 1; }
          } else if (item.type === 'app') {
            if (!apps[item.id]) {
              var app = legeApp(item.id); app.naam = item.label || item.id;
              if (!nieuw.applicaties) nieuw.applicaties = [];
              nieuw.applicaties.push(app); apps[item.id] = true; telling.overgenomen += 1;
            } else telling.samengevoegd += 1;
          } else {
            if (!procs[item.id]) {
              var proces = leegProces(item.id); proces.naam = item.label || item.id; proces.kritiek = !!item.kritiek;
              if (!nieuw.processen) nieuw.processen = [];
              nieuw.processen.push(proces); procs[item.id] = proces; telling.overgenomen += 1;
            } else { if (item.kritiek) procs[item.id].kritiek = true; telling.samengevoegd += 1; }
          }
        } else {
          var van = item.from, naar = item.to;
          var vanType = typen[van] || (ci[van] ? 'ci' : apps[van] ? 'app' : null);
          var naarType = typen[naar] || (procs[naar] ? 'proces' : apps[naar] ? 'app' : ci[naar] ? 'ci' : null);
          if (vanType === 'app' && naarType === 'proces' && procs[naar]) {
            var lijstA = procs[naar].applicaties || (procs[naar].applicaties = []);
            if (lijstA.indexOf(van) < 0) { lijstA.push(van); telling.overgenomen += 1; } else telling.samengevoegd += 1;
          } else if (vanType === 'ci' && (naarType === 'app' || naarType === 'ci')) {
            var edges = nieuw.component_edges || (nieuw.component_edges = []);
            var dubbel = edges.some(function (e) { return e.from === van && e.to === naar; });
            if (!dubbel) { edges.push({ from: van, to: naar, relatie: item.relatie || 'ondersteunt' }); telling.overgenomen += 1; }
            else telling.samengevoegd += 1;
          } else telling.overgeslagen += 1;
        }
      });
    }

    if (!nieuw.herkomst_ai) nieuw.herkomst_ai = [];
    nieuw.herkomst_ai.push({
      opdracht: opdracht, leverancier: voorstel.leverancier || '', model: voorstel.model || '',
      gemaakt: voorstel.gemaakt || '', invoer_sha256: (voorstel.invoer || {}).sha256 || '',
      overgenomen: telling.overgenomen, samengevoegd: telling.samengevoegd, overgeslagen: telling.overgeslagen
    });
    return { dossier: nieuw, telling: telling };
  };

  window.kern = kern;
})();
