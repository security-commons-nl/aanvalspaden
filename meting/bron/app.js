/* Meting in de browser.
 *
 * De rekenregels staan hieronder in het object `reken`, met dezelfde namen en dezelfde uitkomsten als
 * meting/reken.py. Die spiegeling is de controle: een test vergelijkt beide kanten op dezelfde
 * fixtures, zodat de pagina niet stil iets anders gaat toetsen dan de referentie. En de referentie
 * komt zelf uit de applicatie: security-posture-tool en iamscan op tag v0-applicatie.
 *
 * Er is geen fetch in dit bestand en er is geen server. Je exports worden hier gelezen, getoetst en
 * daarna vergeten; alleen de uitkomst gaat het dossier in. Alle termijnen rekenen vanaf de peildatum
 * uit het dossier, nooit vanaf de klok van je computer.
 */
(function () {
  'use strict';

  var BRON = window.__BRON__;
  var REGELS = BRON.regels;
  var PADEN = BRON.paden;
  var SLEUTEL = 'aanvalspaden-meting-v1';

  var VERDICTS = ['pass', 'fail', 'stale', 'unparsed', 'geen_bewijs'];
  var VERDICT_LABEL = {
    pass: 'voldoet', fail: 'voldoet niet', stale: 'te oud', unparsed: 'niet te lezen',
    geen_bewijs: 'nog geen bewijs'
  };
  var TRUTHY = ['true', 'yes', 'ja', '1', 'enabled', 'on', 'y', 't'];
  var FALSY = ['false', 'no', 'nee', '0', 'disabled', 'off', 'n', 'f'];
  var DATUM_PATROON = /\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b/;
  var ERNST = ['hoog', 'midden', 'laag', 'info'];

  // ── reken: spiegel van meting/reken.py ─────────────────────────────────────

  var reken = {};

  // Getallen en tijd

  reken.rond_half_omhoog = function (x) {
    return Math.floor(x + 0.5);
  };

  reken.procent = function (gedekt, totaal) {
    return totaal <= 0 ? 0 : reken.rond_half_omhoog(gedekt / totaal * 100);
  };

  function geldigeDatum(jaar, maand, dag, uur, minuut, seconde, verschuiving) {
    var ms = Date.UTC(jaar, maand - 1, dag, uur || 0, minuut || 0, seconde || 0);
    var stamp = new Date(ms);
    if (stamp.getUTCFullYear() !== jaar || stamp.getUTCMonth() !== maand - 1 || stamp.getUTCDate() !== dag) {
      return null;
    }
    return new Date(ms - (verschuiving || 0) * 60000);
  }

  reken.lees_datum = function (waarde) {
    if (waarde === null || waarde === undefined) return null;
    var tekst = String(waarde).trim();
    if (!tekst) return null;
    var kaal = tekst.replace('Z', '+00:00');
    var iso = /^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ](\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(?:([+-])(\d{2}):?(\d{2}))?$/
      .exec(kaal);
    if (iso) {
      var verschuiving = 0;
      if (iso[7]) {
        verschuiving = (Number(iso[8]) * 60 + Number(iso[9])) * (iso[7] === '-' ? -1 : 1);
      }
      var uit = geldigeDatum(Number(iso[1]), Number(iso[2]), Number(iso[3]),
        Number(iso[4] || 0), Number(iso[5] || 0), Number(iso[6] || 0), verschuiving);
      if (uit) return uit;
    }
    var treffer = DATUM_PATROON.exec(tekst);
    if (treffer) {
      return geldigeDatum(Number(treffer[1]), Number(treffer[2]), Number(treffer[3]), 0, 0, 0, 0);
    }
    return null;
  };

  reken.peil = function (peildatum) {
    var stamp = reken.lees_datum(peildatum) || new Date(Date.UTC(2000, 0, 1));
    return new Date(Date.UTC(stamp.getUTCFullYear(), stamp.getUTCMonth(), stamp.getUTCDate(), 23, 59, 59));
  };

  reken.dagen_tussen = function (waarde, peildatum) {
    var stamp = reken.lees_datum(waarde);
    if (stamp === null) return null;
    return Math.max(0, Math.floor((reken.peil(peildatum).getTime() - stamp.getTime()) / 86400000));
  };

  reken.uren_tussen = function (waarde, peildatum) {
    var stamp = reken.lees_datum(waarde);
    if (stamp === null) return null;
    return Math.max(0, (reken.peil(peildatum).getTime() - stamp.getTime()) / 3600000);
  };

  // Lezen

  function splitsCsvRegel(regel, scheider) {
    var uit = [], huidig = '', inAanhaling = false, i = 0;
    while (i < regel.length) {
      var teken = regel.charAt(i);
      if (inAanhaling) {
        if (teken === '"' && i + 1 < regel.length && regel.charAt(i + 1) === '"') {
          huidig += '"';
          i += 1;
        } else if (teken === '"') {
          inAanhaling = false;
        } else {
          huidig += teken;
        }
      } else if (teken === '"') {
        inAanhaling = true;
      } else if (teken === scheider) {
        uit.push(huidig);
        huidig = '';
      } else {
        huidig += teken;
      }
      i += 1;
    }
    uit.push(huidig);
    return uit;
  }

  function zonderBom(tekst) {
    return String(tekst || '').replace(/^﻿+/, '');
  }

  reken.lees_csv = function (tekst) {
    tekst = zonderBom(tekst).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    var regels = tekst.split('\n').filter(function (r) { return r.trim() !== ''; });
    if (!regels.length) return { koppen: [], rijen: [] };
    var scheider = ',';
    if (splitsCsvRegel(regels[0], ',').length === 1 && splitsCsvRegel(regels[0], ';').length > 1) {
      scheider = ';';
    }
    var koppen = splitsCsvRegel(regels[0], scheider).map(function (k) {
      return zonderBom(k.trim()).toLowerCase();
    });
    var rijen = [];
    for (var i = 1; i < regels.length; i++) {
      var cellen = splitsCsvRegel(regels[i], scheider);
      var rij = {};
      for (var k = 0; k < koppen.length; k++) rij[koppen[k]] = k < cellen.length ? cellen[k] : '';
      rijen.push(rij);
    }
    return { koppen: koppen, rijen: rijen };
  };

  reken.truthy = function (waarde) {
    return TRUTHY.indexOf(String(waarde === null || waarde === undefined ? '' : waarde).trim().toLowerCase()) >= 0;
  };

  reken.falsy = function (waarde) {
    return FALSY.indexOf(String(waarde === null || waarde === undefined ? '' : waarde).trim().toLowerCase()) >= 0;
  };

  reken.ontbrekende_kolommen = function (vereist, koppen) {
    return vereist.filter(function (k) { return koppen.indexOf(k) < 0; }).sort();
  };

  reken.dekking = function (rijen, voorwaarde) {
    var gedekt = 0;
    rijen.forEach(function (r) { if (voorwaarde(r)) gedekt += 1; });
    return { totaal: rijen.length, gedekt: gedekt };
  };

  reken.lees_xml = function (tekst) {
    var doc = new DOMParser().parseFromString(zonderBom(tekst), 'application/xml');
    if (doc.getElementsByTagName('parsererror').length) return null;
    return doc.documentElement || null;
  };

  function naamVan(element) {
    return String(element.tagName || '').split(':').pop().split('}').pop();
  }

  function alleElementen(wortel) {
    var uit = [wortel];
    var lijst = wortel.getElementsByTagName('*');
    for (var i = 0; i < lijst.length; i++) uit.push(lijst[i]);
    return uit;
  }

  function kinderen(element) {
    var uit = [];
    for (var i = 0; i < element.childNodes.length; i++) {
      if (element.childNodes[i].nodeType === 1) uit.push(element.childNodes[i]);
    }
    return uit;
  }

  function veld(rij, naam) {
    var waarde = rij[naam];
    return String(waarde === null || waarde === undefined ? '' : waarde).trim();
  }

  function voorbeeldVan(rijen, velden, maximaal) {
    return rijen.slice(0, maximaal || 10).map(function (rij) {
      return velden.map(function (v) {
        var waarde = rij[v];
        return String(waarde === null || waarde === undefined ? '' : waarde);
      }).join(' | ');
    });
  }

  function uitkomst(verdicts, samenvatting, voorbeeld, artefactDatum, fouten) {
    return {
      verdicts: verdicts, samenvatting: samenvatting || {}, voorbeeld: voorbeeld || [],
      artefact_datum: artefactDatum === undefined ? null : artefactDatum, fouten: fouten || []
    };
  }

  function unparsed(items, fouten) {
    var verdicts = {};
    items.forEach(function (i) { verdicts[i] = 'unparsed'; });
    return uitkomst(verdicts, {}, [], null, fouten);
  }

  function param(regels, itemId) {
    for (var i = 0; i < regels.items.length; i++) {
      if (regels.items[i].id === itemId) return regels.items[i].regel.parameters;
    }
    return {};
  }

  function dekkingsuitkomst(itemId, totaal, gedekt, minimaalEen, extra, voorbeeld) {
    var verdict;
    if (minimaalEen && totaal === 0) verdict = 'fail';
    else verdict = gedekt === totaal ? 'pass' : 'fail';
    var samenvatting = { totaal: totaal, gedekt: gedekt, pct: reken.procent(gedekt, totaal) };
    Object.keys(extra || {}).forEach(function (k) { samenvatting[k] = extra[k]; });
    var verdicts = {};
    verdicts[itemId] = verdict;
    return uitkomst(verdicts, samenvatting, voorbeeld);
  }

  function kolommenFout(mist) {
    return ['kolom ontbreekt: ' + mist.join(', ')];
  }

  // Toetsen per bron

  reken.toets_crown_jewels_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['name'], gelezen.koppen);
    if (mist.length) return unparsed(['1.1', '1.2'], kolommenFout(mist));
    var genoemd = gelezen.rijen.filter(function (r) { return veld(r, 'name') !== ''; });
    var totaal = genoemd.length;
    var metEigenaar = genoemd.filter(function (r) { return veld(r, 'owner') !== ''; }).length;
    var detail = param(regels, '1.2').velden;
    var compleet = genoemd.filter(function (r) {
      return detail.every(function (c) { return veld(r, c) !== ''; });
    }).length;
    return uitkomst({
      '1.1': totaal === 0 ? 'fail' : (metEigenaar === totaal ? 'pass' : 'fail'),
      '1.2': totaal === 0 ? 'fail' : (compleet === totaal ? 'pass' : 'fail')
    }, {
      totaal: totaal, met_eigenaar: metEigenaar, compleet: compleet,
      pct: reken.procent(compleet, totaal)
    }, voorbeeldVan(genoemd, ['name', 'owner']));
  };

  reken.toets_asset_inventory_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['source', 'ip'], gelezen.koppen);
    if (mist.length) return unparsed(['1.3'], kolommenFout(mist));
    var parameters = param(regels, '1.3');
    var perBron = {};
    parameters.bronnen.forEach(function (b) { perBron[b] = {}; });
    var perIp = {};
    gelezen.rijen.forEach(function (rij) {
      var bron = veld(rij, 'source').toLowerCase();
      var ip = veld(rij, 'ip');
      if (!bron || !ip) return;
      if (Object.prototype.hasOwnProperty.call(perBron, bron)) perBron[bron][ip] = true;
      if (!perIp[ip]) perIp[ip] = {};
      perIp[ip][bron] = true;
    });
    var tellingen = {};
    parameters.bronnen.forEach(function (b) { tellingen[b] = Object.keys(perBron[b]).length; });
    var totaalUniek = Object.keys(perIp).length;
    var inMeer = Object.keys(perIp).filter(function (ip) {
      return Object.keys(perIp[ip]).length >= 2;
    }).length;
    var pctMeer = reken.procent(inMeer, totaalUniek);
    var waarden = parameters.bronnen.map(function (b) { return tellingen[b]; });
    var verdict;
    if (waarden.some(function (t) { return t === 0; })) {
      verdict = 'fail';
    } else {
      var hoog = Math.max.apply(null, waarden);
      var laag = Math.min.apply(null, waarden);
      var spreidingOk = hoog ? (hoog - laag) / hoog * 100 <= parameters.maximale_spreiding_pct : false;
      verdict = pctMeer >= parameters.minimaal_pct_multi && spreidingOk ? 'pass' : 'fail';
    }
    return uitkomst({ '1.3': verdict },
      { totaal: totaalUniek, gedekt: inMeer, pct: pctMeer, per_bron: tellingen });
  };

  var FW_ITEMS = ['2.1', '2.2', '2.3', '2.4'];
  var MGMT_WOORDEN = ['mgmt', 'oob', 'tooling', 'aaa'];

  function legeKenmerken() {
    return {
      jump_naar_ilo: false, directe_rdp_user_naar_server: false, any_any_in_mgmt: 0,
      guest_naar_internal: 0, regels: 0
    };
  }

  function bevat(tekst, woorden) {
    return woorden.some(function (w) { return tekst.indexOf(w) >= 0; });
  }

  function fwKenmerkenFortigate(tekst) {
    var kenmerken = legeKenmerken();
    var blokken = /edit\s+\d+\s*\n([\s\S]*?)\n\s*next/g;
    var blok;
    while ((blok = blokken.exec(tekst)) !== null) {
      var velden = {};
      var zetter = /set\s+(\S+)\s+(.+)/g;
      var zet;
      while ((zet = zetter.exec(blok[1])) !== null) {
        velden[zet[1]] = zet[2].trim().replace(/^"|"$/g, '').trim();
      }
      kenmerken.regels += 1;
      var src = String(velden.srcintf || '').toLowerCase();
      var dst = String(velden.dstintf || '').toLowerCase();
      var srcAddr = String(velden.srcaddr || '').split(/\s+/).map(function (t) {
        return t.replace(/"/g, '').toLowerCase();
      });
      var dstAddr = String(velden.dstaddr || '').split(/\s+/).map(function (t) {
        return t.replace(/"/g, '').toLowerCase();
      });
      var dienst = String(velden.service || '').toLowerCase();
      var actie = String(velden.action === undefined ? 'accept' : velden.action).toLowerCase();
      var zones = src + ' ' + dst;
      if (actie === 'accept' && bevat(zones, MGMT_WOORDEN) && srcAddr.indexOf('all') >= 0 &&
        dstAddr.indexOf('all') >= 0) {
        kenmerken.any_any_in_mgmt += 1;
      }
      if (src.indexOf('guest') >= 0 && (dst.indexOf('internal') >= 0 ||
        dstAddr.some(function (a) { return a.indexOf('internal') >= 0; })) && actie === 'accept') {
        kenmerken.guest_naar_internal += 1;
      }
      if (src.indexOf('jump') >= 0 && (dst.indexOf('ilo') >= 0 || dst.indexOf('ipmi') >= 0)) {
        kenmerken.jump_naar_ilo = true;
      }
      if (src.indexOf('user') >= 0 && dst.indexOf('server') >= 0 &&
        (dienst.indexOf('rdp') >= 0 || dienst.indexOf('3389') >= 0) && actie === 'accept') {
        kenmerken.directe_rdp_user_naar_server = true;
      }
    }
    return kenmerken;
  }

  function fwKenmerkenCisco(tekst) {
    var kenmerken = legeKenmerken();
    var patroon = /access-list\s+(\S+)\s+(?:extended\s+)?(permit|deny)\s+(\S+)\s+(.+)/g;
    var treffer;
    while ((treffer = patroon.exec(tekst)) !== null) {
      var acl = treffer[1].toLowerCase();
      var actie = treffer[2].toLowerCase();
      var proto = treffer[3].toLowerCase();
      var rest = treffer[4].toLowerCase();
      kenmerken.regels += 1;
      if (acl.indexOf('mgmt') >= 0 && rest.indexOf('any any') >= 0 &&
        (proto === 'ip' || proto === 'any')) {
        kenmerken.any_any_in_mgmt += 1;
      }
      if (acl.indexOf('guest') >= 0 && rest.indexOf('any any') < 0 && actie === 'permit' &&
        bevat(rest, ['10.', '172.16.', '192.168.', 'internal'])) {
        kenmerken.guest_naar_internal += 1;
      }
      if (acl.indexOf('jump') >= 0 && rest.indexOf('ilo') >= 0) kenmerken.jump_naar_ilo = true;
      if (acl.indexOf('user') >= 0 && (rest.indexOf('eq 3389') >= 0 || rest.indexOf('rdp') >= 0)) {
        kenmerken.directe_rdp_user_naar_server = true;
      }
    }
    return kenmerken;
  }

  function fwKenmerkenPalo(tekst) {
    var kenmerken = legeKenmerken();
    var regels = {};
    var volgorde = [];
    var patroon = /set rulebase security rules (\S+) (\S+) (.+)/g;
    var treffer;
    while ((treffer = patroon.exec(tekst)) !== null) {
      var naam = treffer[1];
      if (!regels[naam]) { regels[naam] = {}; volgorde.push(naam); }
      regels[naam][treffer[2]] = treffer[3].trim().replace(/^\[|\]$/g, '').trim().toLowerCase();
    }
    volgorde.forEach(function (naam) {
      var velden = regels[naam];
      kenmerken.regels += 1;
      var van = String(velden.from || '');
      var naar = String(velden.to || '');
      var bron = String(velden.source || '');
      var doel = String(velden.destination || '');
      var dienst = String(velden.service || '') + ' ' + String(velden.application || '');
      var actie = velden.action === undefined ? 'allow' : velden.action;
      var zones = van + ' ' + naar;
      if (actie === 'allow' && bevat(zones, MGMT_WOORDEN) && bron.indexOf('any') >= 0 &&
        doel.indexOf('any') >= 0) {
        kenmerken.any_any_in_mgmt += 1;
      }
      if (van.indexOf('guest') >= 0 && (naar.indexOf('internal') >= 0 || doel.indexOf('internal') >= 0) &&
        actie === 'allow') {
        kenmerken.guest_naar_internal += 1;
      }
      if (van.indexOf('jump') >= 0 && (naar.indexOf('ilo') >= 0 || naar.indexOf('ipmi') >= 0)) {
        kenmerken.jump_naar_ilo = true;
      }
      if (van.indexOf('user') >= 0 && naar.indexOf('server') >= 0 &&
        (dienst.indexOf('rdp') >= 0 || dienst.indexOf('3389') >= 0) && actie === 'allow') {
        kenmerken.directe_rdp_user_naar_server = true;
      }
    });
    return kenmerken;
  }

  reken.herken_fw = function (tekst) {
    var laag = String(tekst).toLowerCase();
    if (laag.indexOf('config firewall policy') >= 0) return 'fortigate';
    if (laag.indexOf('access-list') >= 0) return 'cisco';
    if (laag.indexOf('set rulebase security rules') >= 0) return 'palo';
    return null;
  };

  reken.toets_fw_config = function (inhoud, peildatum, regels) {
    var soort = reken.herken_fw(inhoud);
    if (soort === null) {
      return unparsed(FW_ITEMS, ['formaat niet herkend; verwacht FortiGate, Cisco of Palo Alto']);
    }
    var lezers = { fortigate: fwKenmerkenFortigate, cisco: fwKenmerkenCisco, palo: fwKenmerkenPalo };
    var kenmerken = lezers[soort](inhoud);
    var verdicts = {};
    FW_ITEMS.forEach(function (item) {
      var parameters = param(regels, item);
      var waarde = kenmerken[parameters.kenmerk];
      var gevonden = typeof waarde === 'boolean' ? waarde : waarde > 0;
      verdicts[item] = gevonden === parameters.verwacht ? 'pass' : 'fail';
    });
    var samenvatting = { formaat: soort };
    Object.keys(kenmerken).forEach(function (k) { samenvatting[k] = kenmerken[k]; });
    return uitkomst(verdicts, samenvatting);
  };

  reken.toets_vpn_inventory_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['peer', 'dst_subnet'], gelezen.koppen);
    if (mist.length) return unparsed(['2.5'], kolommenFout(mist));
    var uit = reken.dekking(gelezen.rijen, function (rij) {
      var subnet = veld(rij, 'dst_subnet');
      return subnet !== '' && ['0.0.0.0/0', '::/0', 'any'].indexOf(subnet) < 0;
    });
    return dekkingsuitkomst('2.5', uit.totaal, uit.gedekt, true, null,
      voorbeeldVan(gelezen.rijen, ['peer', 'dst_subnet']));
  };

  function waarVeld(itemId, kolommen, naam, inhoud, regels, voorbeeldvelden) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(kolommen, gelezen.koppen);
    if (mist.length) return unparsed([itemId], kolommenFout(mist));
    var uit = reken.dekking(gelezen.rijen, function (rij) { return reken.truthy(rij[naam]); });
    return dekkingsuitkomst(itemId, uit.totaal, uit.gedekt, true, null,
      voorbeeldVan(gelezen.rijen, voorbeeldvelden));
  }

  reken.toets_entra_privileged_csv = function (inhoud, peildatum, regels) {
    return waarVeld('3.1', ['upn', 'mfa_registered'], 'mfa_registered', inhoud, regels,
      ['upn', 'mfa_registered']);
  };

  reken.toets_ad_tier0_csv = function (inhoud, peildatum, regels) {
    return waarVeld('3.2', ['account', 'logon_workstations_set'], 'logon_workstations_set', inhoud,
      regels, ['account', 'logon_workstations_set']);
  };

  reken.toets_gpo_export_xml = function (inhoud, peildatum, regels) {
    var wortel = reken.lees_xml(inhoud);
    if (wortel === null) return unparsed(['3.2'], ['XML niet te lezen']);
    var gevonden = String(inhoud).toLowerCase().indexOf('logonworkstations') >= 0;
    return uitkomst({ '3.2': gevonden ? 'pass' : 'fail' },
      { kenmerk: 'LogonWorkstations', gevonden: gevonden });
  };

  reken.toets_ad_svc_accounts_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['sam', 'in_da', 'auth_type', 'pw_len'], gelezen.koppen);
    if (mist.length) return unparsed(['3.3'], kolommenFout(mist));
    var minimaal = param(regels, '3.3').minimale_lengte;
    var uit = reken.dekking(gelezen.rijen, function (rij) {
      if (reken.truthy(rij.in_da)) return false;
      if (veld(rij, 'auth_type').toLowerCase() === 'gmsa') return true;
      var ruw = veld(rij, 'pw_len');
      if (!/^\d+$/.test(ruw)) return false;
      return parseInt(ruw, 10) >= minimaal;
    });
    var inDa = gelezen.rijen.filter(function (r) { return reken.truthy(r.in_da); }).length;
    var verdict = uit.totaal && uit.gedekt === uit.totaal && inDa === 0 ? 'pass' : 'fail';
    return uitkomst({ '3.3': verdict },
      {
        totaal: uit.totaal, gedekt: uit.gedekt, pct: reken.procent(uit.gedekt, uit.totaal),
        in_da: inDa
      },
      voorbeeldVan(gelezen.rijen, ['sam', 'auth_type', 'pw_len']));
  };

  reken.toets_laps_csv = function (inhoud, peildatum, regels) {
    return waarVeld('3.4', ['device_name', 'laps_configured'], 'laps_configured', inhoud, regels,
      ['device_name', 'laps_configured']);
  };

  reken.toets_entra_users_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['upn', 'enabled', 'last_signin'], gelezen.koppen);
    if (mist.length) return unparsed(['3.5'], kolommenFout(mist));
    var grens = param(regels, '3.5').dagen;
    var slapend = gelezen.rijen.filter(function (rij) {
      if (!reken.truthy(rij.enabled)) return false;
      var dagen = reken.dagen_tussen(rij.last_signin, peildatum);
      return dagen === null || dagen > grens;
    });
    return uitkomst({ '3.5': slapend.length ? 'fail' : 'pass' },
      { totaal: gelezen.rijen.length, inactief: slapend.length, dagen: grens },
      voorbeeldVan(slapend, ['upn', 'last_signin']));
  };

  reken.toets_siem_flow_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['timestamp', 'src_vlan', 'dst_vlan'], gelezen.koppen);
    if (mist.length) return unparsed(['4.1', '4.6'], kolommenFout(mist));
    var venster = param(regels, '4.1').venster_uren;
    var extern = param(regels, '4.6').externe_zones;
    var recent = 0, eastWest = 0;
    gelezen.rijen.forEach(function (rij) {
      var uren = reken.uren_tussen(rij.timestamp, peildatum);
      if (uren !== null && uren <= venster) recent += 1;
      var bron = veld(rij, 'src_vlan').toLowerCase();
      var doel = veld(rij, 'dst_vlan').toLowerCase();
      if (bron && doel && bron !== doel && extern.indexOf(bron) < 0 && extern.indexOf(doel) < 0) {
        eastWest += 1;
      }
    });
    return uitkomst({ '4.1': recent > 0 ? 'pass' : 'fail', '4.6': eastWest > 0 ? 'pass' : 'fail' },
      {
        totaal: gelezen.rijen.length, in_venster: recent, east_west: eastWest,
        venster_uren: venster
      });
  };

  var SYSMON_VINGERAFDRUKKEN = ['swiftonsecurity', 'sysmon-modular', 'olaf hartong', 'hartong',
    'sysmonconfig-export'];

  reken.toets_sysmon_config_xml = function (inhoud, peildatum, regels) {
    var wortel = reken.lees_xml(inhoud);
    if (wortel === null) return unparsed(['4.2'], ['XML niet te lezen']);
    if (naamVan(wortel).toLowerCase() !== 'sysmon') {
      return unparsed(['4.2'], ['dit is geen Sysmon-configuratie']);
    }
    var minimaal = param(regels, '4.2').minimaal_rulegroups;
    var groepen = alleElementen(wortel).filter(function (e) {
      return naamVan(e) === 'RuleGroup';
    }).length;
    var laag = String(inhoud).toLowerCase();
    var gevonden = SYSMON_VINGERAFDRUKKEN.filter(function (v) { return laag.indexOf(v) >= 0; });
    var verdict;
    if (groepen < minimaal) verdict = 'fail';
    else if (gevonden.length) verdict = 'pass';
    else verdict = 'unparsed';
    return uitkomst({ '4.2': verdict },
      {
        vingerafdruk: gevonden.length ? gevonden[0] : null, rulegroups: groepen,
        minimaal_rulegroups: minimaal
      }, [], null,
      gevonden.length || groepen < minimaal ? [] : ['onbekende configuratie; beoordeel hem zelf']);
  };

  reken.toets_entra_risky_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['user', 'risk_level', 'datum'], gelezen.koppen);
    if (mist.length) return unparsed(['4.3'], kolommenFout(mist));
    var venster = param(regels, '4.3').venster_dagen;
    var risky = gelezen.rijen.filter(function (rij) {
      var niveau = veld(rij, 'risk_level').toLowerCase();
      if (niveau === '' || niveau === 'none') return false;
      var dagen = reken.dagen_tussen(rij.datum, peildatum);
      return dagen !== null && dagen <= venster;
    });
    return uitkomst({ '4.3': risky.length ? 'fail' : 'pass' },
      { totaal: gelezen.rijen.length, risky: risky.length, venster_dagen: venster },
      voorbeeldVan(risky, ['user', 'risk_level', 'datum']));
  };

  reken.toets_fw_flow_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['fqdn'], gelezen.koppen);
    if (mist.length) return unparsed(['4.4'], kolommenFout(mist));
    var drempel = param(regels, '4.4').minimaal_pct;
    var uit = reken.dekking(gelezen.rijen, function (rij) { return veld(rij, 'fqdn') !== ''; });
    var pct = reken.procent(uit.gedekt, uit.totaal);
    return uitkomst({ '4.4': uit.totaal > 0 && pct >= drempel ? 'pass' : 'fail' },
      { totaal: uit.totaal, gedekt: uit.gedekt, pct: pct, drempel_pct: drempel });
  };

  function jsonLijst(inhoud, sleutel) {
    var data;
    try {
      data = JSON.parse(zonderBom(inhoud));
    } catch (fout) {
      return { lijst: null, fout: 'JSON niet te lezen: ' + fout.message };
    }
    var lijst = Array.isArray(data) ? data : (data && data[sleutel]);
    if (!Array.isArray(lijst)) {
      return { lijst: null, fout: 'verwacht een lijst of een object met de sleutel ' + sleutel };
    }
    return { lijst: lijst, fout: null };
  }

  function regelnaam(regel) {
    return regel.id || regel.name || '?';
  }

  reken.toets_siem_rules_json = function (inhoud, peildatum, regels) {
    var gelezen = jsonLijst(inhoud, 'rules');
    if (gelezen.lijst === null) return unparsed(['4.5'], [gelezen.fout]);
    var parameters = param(regels, '4.5');
    var tag = String(parameters.tag).toLowerCase();
    var treffers = gelezen.lijst.filter(function (r) {
      return r && typeof r === 'object' && (r.tags || []).some(function (t) {
        return String(t).toLowerCase().indexOf(tag) >= 0;
      });
    }).map(regelnaam);
    return uitkomst({ '4.5': treffers.length >= parameters.minimaal ? 'pass' : 'fail' },
      { totaal: gelezen.lijst.length, gedekt: treffers.length, drempel: parameters.minimaal },
      treffers.slice(0, 10).map(String));
  };

  reken.toets_siem_behavior_rules_json = function (inhoud, peildatum, regels) {
    var gelezen = jsonLijst(inhoud, 'rules');
    if (gelezen.lijst === null) return unparsed(['8.2'], [gelezen.fout]);
    var parameters = param(regels, '8.2');
    var treffers = gelezen.lijst.filter(function (r) {
      return r && typeof r === 'object' &&
        String(r.type === null || r.type === undefined ? '' : r.type).toLowerCase() === parameters.waarde;
    }).map(regelnaam);
    return uitkomst({ '8.2': treffers.length >= parameters.minimaal ? 'pass' : 'fail' },
      { totaal: gelezen.lijst.length, gedekt: treffers.length, drempel: parameters.minimaal },
      treffers.slice(0, 10).map(String));
  };

  function isoTekst(datum) {
    if (!datum) return null;
    return datum.toISOString().replace(/\.\d{3}Z$/, '+00:00');
  }

  reken.toets_nessus_xml = function (inhoud, peildatum, regels) {
    var wortel = reken.lees_xml(inhoud);
    if (wortel === null) return unparsed(['5.1'], ['XML niet te lezen']);
    var parameters = param(regels, '5.1');
    var kritiek = [];
    var scanDatum = null;
    alleElementen(wortel).forEach(function (item) {
      if (naamVan(item) === 'ReportItem' &&
        String(item.getAttribute('severity')) === String(parameters.severity)) {
        kritiek.push(item.getAttribute('pluginName') || item.getAttribute('port') || '?');
      }
      if (naamVan(item) === 'tag' && ['HOST_START', 'HOST_END'].indexOf(item.getAttribute('name')) >= 0) {
        scanDatum = scanDatum || reken.lees_datum(item.textContent);
      }
    });
    var dagen = reken.dagen_tussen(isoTekst(scanDatum), peildatum);
    var verdict;
    if (dagen !== null && dagen > parameters.stale_na_dagen) verdict = 'stale';
    else verdict = kritiek.length ? 'fail' : 'pass';
    return uitkomst({ '5.1': verdict },
      { kritiek: kritiek.length, dagen_oud: dagen, stale_na_dagen: parameters.stale_na_dagen },
      kritiek.slice(0, 10).map(String), isoTekst(scanDatum));
  };

  reken.toets_edge_devices_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['device', 'last_patched_at'], gelezen.koppen);
    if (mist.length) return unparsed(['5.2'], kolommenFout(mist));
    var maximaal = param(regels, '5.2').maximale_uren;
    var uit = reken.dekking(gelezen.rijen, function (rij) {
      var uren = reken.uren_tussen(rij.last_patched_at, peildatum);
      return uren !== null && uren <= maximaal;
    });
    return dekkingsuitkomst('5.2', uit.totaal, uit.gedekt, true, { maximale_uren: maximaal },
      voorbeeldVan(gelezen.rijen, ['device', 'last_patched_at']));
  };

  reken.toets_eol_inventory_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['system', 'eol_date', 'migration_date'], gelezen.koppen);
    if (mist.length) return unparsed(['5.3'], kolommenFout(mist));
    var uit = reken.dekking(gelezen.rijen, function (rij) {
      return veld(rij, 'migration_date') !== '';
    });
    return dekkingsuitkomst('5.3', uit.totaal, uit.gedekt, true, null,
      voorbeeldVan(gelezen.rijen, ['system', 'migration_date']));
  };

  reken.toets_nmap_xml = function (inhoud, peildatum, regels) {
    var wortel = reken.lees_xml(inhoud);
    if (wortel === null) return unparsed(['5.4'], ['XML niet te lezen']);
    var parameters = param(regels, '5.4');
    var start = wortel.getAttribute('start');
    var scanDatum = null;
    if (start && /^\d+$/.test(String(start))) scanDatum = new Date(parseInt(start, 10) * 1000);
    var hosts = kinderen(wortel).filter(function (h) { return naamVan(h) === 'host'; });
    var openPoorten = [];
    hosts.forEach(function (host) {
      var adresknoop = kinderen(host).filter(function (a) { return naamVan(a) === 'address'; })[0];
      var adres = adresknoop ? adresknoop.getAttribute('addr') : '?';
      alleElementen(host).forEach(function (poort) {
        if (naamVan(poort) !== 'port') return;
        var staat = kinderen(poort).filter(function (s) { return naamVan(s) === 'state'; })[0];
        if (staat && staat.getAttribute('state') === 'open') {
          openPoorten.push(adres + ':' + poort.getAttribute('portid'));
        }
      });
    });
    var dagen = reken.dagen_tussen(isoTekst(scanDatum), peildatum);
    var verdict;
    if (scanDatum === null) verdict = 'unparsed';
    else if (dagen !== null && dagen > parameters.maximale_dagen) verdict = 'stale';
    else verdict = hosts.length ? 'pass' : 'fail';
    return uitkomst({ '5.4': verdict },
      {
        hosts: hosts.length, open_poorten: openPoorten.length, dagen_oud: dagen,
        maximale_dagen: parameters.maximale_dagen
      },
      openPoorten.slice(0, 10), isoTekst(scanDatum));
  };

  reken.toets_veeam_report_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['job_name', 'last_success', 'immutable', 'errors'],
      gelezen.koppen);
    if (mist.length) return unparsed(['6.1'], kolommenFout(mist));
    var maximaal = param(regels, '6.1').maximale_uren;
    var uit = reken.dekking(gelezen.rijen, function (rij) {
      if (!reken.truthy(rij.immutable)) return false;
      var fouten = veld(rij, 'errors');
      if (fouten === '') fouten = '0';
      if (!/^-?\d+$/.test(fouten)) return false;
      if (parseInt(fouten, 10) !== 0) return false;
      var uren = reken.uren_tussen(rij.last_success, peildatum);
      return uren !== null && uren <= maximaal;
    });
    return dekkingsuitkomst('6.1', uit.totaal, uit.gedekt, true, { maximale_uren: maximaal },
      voorbeeldVan(gelezen.rijen, ['job_name', 'last_success', 'immutable', 'errors']));
  };

  reken.toets_backup_ad_audit_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['backup_system', 'prod_ad_trust'], gelezen.koppen);
    if (mist.length) return unparsed(['6.2'], kolommenFout(mist));
    var uit = reken.dekking(gelezen.rijen, function (rij) { return !reken.truthy(rij.prod_ad_trust); });
    return dekkingsuitkomst('6.2', uit.totaal, uit.gedekt, true, null,
      voorbeeldVan(gelezen.rijen, ['backup_system', 'prod_ad_trust']));
  };

  var WDAC_REGELTAGS = ['Allow', 'Deny', 'FileRule', 'FileAttrib', 'Signer', 'FilePathRule',
    'FilePublisherRule', 'FileHashRule'];

  reken.toets_wdac_policy_xml = function (inhoud, peildatum, regels) {
    var wortel = reken.lees_xml(inhoud);
    if (wortel === null) return unparsed(['7.1'], ['XML niet te lezen']);
    var naam = naamVan(wortel).toLowerCase();
    if (naam !== 'sipolicy' && naam !== 'applockerpolicy') {
      return unparsed(['7.1'], ['geen WDAC- of AppLocker-policy']);
    }
    var audit = String(inhoud).indexOf('Enabled:Audit Mode') >= 0;
    var afgedwongen = alleElementen(wortel).filter(function (e) {
      return naamVan(e) === 'RuleCollection' &&
        String(e.getAttribute('EnforcementMode') || '').toLowerCase() === 'enabled';
    });
    var aantal = alleElementen(wortel).filter(function (e) {
      return WDAC_REGELTAGS.indexOf(naamVan(e)) >= 0;
    }).length;
    var verdict;
    if (audit && !afgedwongen.length) verdict = 'fail';
    else verdict = aantal > 0 ? 'pass' : 'fail';
    return uitkomst({ '7.1': verdict }, {
      formaat: naam === 'applockerpolicy' ? 'applocker' : 'wdac', audit_mode: audit,
      afgedwongen: afgedwongen.length, regels: aantal
    });
  };

  reken.toets_asr_csv = function (inhoud, peildatum, regels) {
    return waarVeld('7.2', ['device_name', 'asr_office_macros_blocked'], 'asr_office_macros_blocked',
      inhoud, regels, ['device_name', 'asr_office_macros_blocked']);
  };

  reken.toets_local_admins_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['device', 'user_count_in_admins'], gelezen.koppen);
    if (mist.length) return unparsed(['7.3'], kolommenFout(mist));
    var uit = reken.dekking(gelezen.rijen, function (rij) {
      var ruw = veld(rij, 'user_count_in_admins');
      if (ruw === '') return false;
      if (!/^-?\d+$/.test(ruw)) return false;
      return parseInt(ruw, 10) === 0;
    });
    return dekkingsuitkomst('7.3', uit.totaal, uit.gedekt, true, null,
      voorbeeldVan(gelezen.rijen, ['device', 'user_count_in_admins']));
  };

  reken.toets_intune_usb_csv = function (inhoud, peildatum, regels) {
    return waarVeld('7.4', ['device', 'usb_blocked_default'], 'usb_blocked_default', inhoud, regels,
      ['device', 'usb_blocked_default']);
  };

  reken.toets_entra_admins_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['upn', 'auth_methods'], gelezen.koppen);
    if (mist.length) return unparsed(['8.1'], kolommenFout(mist));
    var methoden = param(regels, '8.1').methoden.map(function (m) { return m.toLowerCase(); });
    var uit = reken.dekking(gelezen.rijen, function (rij) {
      var waarde = String(rij.auth_methods === undefined || rij.auth_methods === null ? '' : rij.auth_methods)
        .toLowerCase();
      return methoden.some(function (m) { return waarde.indexOf(m) >= 0; });
    });
    return dekkingsuitkomst('8.1', uit.totaal, uit.gedekt, true, null,
      voorbeeldVan(gelezen.rijen, ['upn', 'auth_methods']));
  };

  reken.toets_fw_category_csv = function (inhoud, peildatum, regels) {
    var gelezen = reken.lees_csv(inhoud);
    var mist = reken.ontbrekende_kolommen(['category', 'action', 'logged'], gelezen.koppen);
    if (mist.length) return unparsed(['8.4'], kolommenFout(mist));
    var treffers = gelezen.rijen.filter(function (rij) {
      return veld(rij, 'category').toLowerCase().indexOf('ai') >= 0 && reken.truthy(rij.logged);
    });
    var drempel = param(regels, '8.4').minimaal;
    return uitkomst({ '8.4': treffers.length >= drempel ? 'pass' : 'fail' },
      { totaal: gelezen.rijen.length, gedekt: treffers.length, drempel: drempel },
      voorbeeldVan(treffers, ['category', 'action', 'logged']));
  };

  reken.toets_document = function (inhoud, peildatum, regels, itemId) {
    if (itemId === null || itemId === undefined) {
      return unparsed(['?'], ['geen item gekozen voor dit document']);
    }
    var parameters = param(regels, itemId);
    var dagenPerMaand = regels.tijd.document_dagen_per_maand;
    var ontbreekt = parameters.trefwoorden.filter(function (t) {
      return !(new RegExp(t, 'is')).test(String(inhoud));
    });
    var datum = reken.lees_datum(inhoud);
    var dagen = reken.dagen_tussen(isoTekst(datum), peildatum);
    var maximaal = parameters.maximale_maanden * dagenPerMaand;
    var samenvatting = {
      trefwoorden: parameters.trefwoorden.slice(),
      gevonden: parameters.trefwoorden.length - ontbreekt.length,
      dagen_oud: dagen, maximale_maanden: parameters.maximale_maanden, parser: parameters.parser
    };
    var verdicts = {};
    if (ontbreekt.length) {
      verdicts[itemId] = 'unparsed';
      return uitkomst(verdicts, samenvatting, [], null, ontbreekt.map(function (t) {
        return 'trefwoord niet gevonden: ' + t;
      }));
    }
    if (dagen === null) {
      verdicts[itemId] = 'unparsed';
      return uitkomst(verdicts, samenvatting, [], null,
        ['geen datum gevonden in de tekst (verwacht bijvoorbeeld 2026-03-12)']);
    }
    verdicts[itemId] = dagen > maximaal ? 'stale' : 'pass';
    return uitkomst(verdicts, samenvatting, [], isoTekst(datum));
  };

  // ── iamscan: de Linux-dump ─────────────────────────────────────────────────

  var PASSWD = 'etc/passwd';
  var GROUP = 'etc/group';
  var SUDOERS = 'etc/sudoers';
  var SUDOERS_D = 'etc/sudoers.d';
  var SSHD = 'etc/ssh/sshd_config';
  var SUDO_TAGS = ['NOPASSWD:', 'PASSWD:', 'NOEXEC:', 'EXEC:', 'SETENV:', 'NOSETENV:', 'LOG_INPUT:',
    'LOG_OUTPUT:'];
  var SKIP = ['Defaults', 'User_Alias', 'Runas_Alias', 'Host_Alias', 'Cmnd_Alias', '@include'];

  function regelsVan(tekst) {
    return String(tekst === null || tekst === undefined ? '' : tekst).split(/\r\n|\r|\n/);
  }

  reken.parse_passwd = function (tekst) {
    var uit = [];
    regelsVan(tekst).forEach(function (ruw) {
      var regel = ruw.trim();
      if (!regel || regel.charAt(0) === '#') return;
      var delen = regel.split(':');
      if (delen.length < 7) return;
      if (!/^-?\d+$/.test(delen[2]) || !/^-?\d+$/.test(delen[3])) return;
      uit.push({
        naam: delen[0], uid: parseInt(delen[2], 10), gid: parseInt(delen[3], 10),
        gecos: delen[4], home: delen[5], shell: delen[6]
      });
    });
    return uit;
  };

  reken.parse_group = function (tekst) {
    var uit = [];
    regelsVan(tekst).forEach(function (ruw) {
      var regel = ruw.trim();
      if (!regel || regel.charAt(0) === '#') return;
      var delen = regel.split(':');
      if (delen.length < 4) return;
      if (!/^-?\d+$/.test(delen[2])) return;
      uit.push({
        naam: delen[0], gid: parseInt(delen[2], 10),
        leden: delen[3].split(',').filter(function (m) { return m !== ''; })
      });
    });
    return uit;
  };

  reken.parse_sudoers = function (tekst, herkomst) {
    var uit = [];
    regelsVan(tekst).forEach(function (ruw) {
      var regel = ruw.split('#')[0].trim();
      if (!regel) return;
      if (SKIP.some(function (s) { return regel.indexOf(s) === 0; })) return;
      var treffer = /^([%+\w.\-]+)\s+(\S+)\s*=\s*(.*)$/.exec(regel);
      if (!treffer) return;
      var rest = treffer[3].trim();
      var runas = 'ALL';
      var alsWie = /^\(([^)]*)\)\s*(.*)$/.exec(rest);
      if (alsWie) {
        runas = alsWie[1].trim() || 'ALL';
        rest = alsWie[2].trim();
      }
      var nopasswd = false;
      for (;;) {
        var boven = rest.toUpperCase();
        var tag = null;
        for (var i = 0; i < SUDO_TAGS.length; i++) {
          if (boven.indexOf(SUDO_TAGS[i]) === 0) { tag = SUDO_TAGS[i]; break; }
        }
        if (tag === null) break;
        if (tag === 'NOPASSWD:') nopasswd = true;
        rest = rest.slice(tag.length).trim();
      }
      var commandos = rest.split(',').map(function (c) { return c.trim(); })
        .filter(function (c) { return c !== ''; });
      if (!commandos.length) return;
      uit.push({
        wie: treffer[1], runas: runas, commandos: commandos, nopasswd: nopasswd,
        herkomst: herkomst
      });
    });
    return uit;
  };

  reken.parse_authorized_keys = function (tekst, account, herkomst) {
    var uit = [];
    regelsVan(tekst).forEach(function (ruw) {
      var regel = ruw.trim();
      if (!regel || regel.charAt(0) === '#') return;
      var patroon = /(?<![\w-])(ssh-[\w-]+|ecdsa-[\w@.-]+|sk-[\w@.-]+)\s/;
      var treffer = patroon.exec(regel);
      if (treffer === null) return;
      var opties = treffer.index > 0 ? regel.slice(0, treffer.index).trim().replace(/,+$/, '') : '';
      var delen = regel.slice(treffer.index).split(/\s+/);
      if (delen.length < 2) return;
      uit.push({
        account: account, type: delen[0], vingerafdruk: delen[1],
        comment: delen.slice(2).join(' '), opties: opties, herkomst: herkomst
      });
    });
    return uit;
  };

  reken.parse_sshd_config = function (tekst) {
    var uit = {};
    regelsVan(tekst).forEach(function (ruw) {
      var regel = ruw.split('#')[0].trim();
      if (!regel) return;
      var treffer = /^(\S+)\s+([\s\S]+)$/.exec(regel);
      if (!treffer) return;
      var sleutel = treffer[1].toLowerCase();
      if (!Object.prototype.hasOwnProperty.call(uit, sleutel)) uit[sleutel] = treffer[2].trim();
    });
    return uit;
  };

  reken.lees_dump = function (bestanden) {
    var perHost = {};
    var hostVolgorde = [];
    Object.keys(bestanden).forEach(function (pad) {
      var schoon = pad.replace(/\\/g, '/').replace(/^[.\/]+/, '');
      var delen = schoon.split('/');
      if (delen.length < 2) return;
      if (delen[0] === 'hosts' && delen.length > 2) delen = delen.slice(1);
      if (!perHost[delen[0]]) { perHost[delen[0]] = {}; hostVolgorde.push(delen[0]); }
      perHost[delen[0]][delen.slice(1).join('/')] = bestanden[pad];
    });

    var hosts = [];
    hostVolgorde.slice().sort().forEach(function (naam) {
      var inhoud = perHost[naam];
      var host = {
        naam: naam, accounts: [], groepen: [], sudo: [], sleutels: [], sshd: {}, ontbreekt: []
      };
      [[PASSWD, reken.parse_passwd, 'accounts'], [GROUP, reken.parse_group, 'groepen']]
        .forEach(function (paar) {
          if (Object.prototype.hasOwnProperty.call(inhoud, paar[0])) {
            host[paar[2]] = paar[1](inhoud[paar[0]]);
          } else {
            host.ontbreekt.push(paar[0]);
          }
        });
      if (Object.prototype.hasOwnProperty.call(inhoud, SUDOERS)) {
        host.sudo = host.sudo.concat(reken.parse_sudoers(inhoud[SUDOERS], SUDOERS));
      } else {
        host.ontbreekt.push(SUDOERS);
      }
      Object.keys(inhoud).filter(function (p) { return p.indexOf(SUDOERS_D + '/') === 0; }).sort()
        .forEach(function (pad) {
          host.sudo = host.sudo.concat(reken.parse_sudoers(inhoud[pad], pad));
        });
      if (Object.prototype.hasOwnProperty.call(inhoud, SSHD)) {
        host.sshd = reken.parse_sshd_config(inhoud[SSHD]);
      } else {
        host.ontbreekt.push(SSHD);
      }
      var staart = '.ssh/authorized_keys';
      Object.keys(inhoud).filter(function (p) {
        return p.length >= staart.length && p.slice(-staart.length) === staart;
      }).sort().forEach(function (pad) {
        var delen = pad.split('/');
        var account = delen[0] === 'root' ? 'root' : (delen.length > 2 ? delen[1] : delen[0]);
        host.sleutels = host.sleutels.concat(reken.parse_authorized_keys(inhoud[pad], account, pad));
      });
      hosts.push(host);
    });
    return hosts;
  };

  function ledenVan(host, groep) {
    var gevonden = host.groepen.filter(function (g) { return g.naam === groep; })[0];
    if (!gevonden) return [];
    var leden = gevonden.leden.slice();
    host.accounts.forEach(function (account) {
      if (account.gid === gevonden.gid && leden.indexOf(account.naam) < 0) leden.push(account.naam);
    });
    return leden;
  }

  function principalsVan(host, regel) {
    if (regel.wie.charAt(0) !== '%') return [regel.wie];
    var leden = ledenVan(host, regel.wie.slice(1));
    return leden.length ? leden : [regel.wie];
  }

  function basisnaam(commando) {
    var delen = commando.split(/\s+/);
    var eerste = delen.length ? delen[0] : commando;
    return eerste.split('/').pop();
  }

  reken.routes_naar_root = function (host, shellEscape) {
    var routes = [];
    var gezien = {};

    function voegToe(principal, route, via, nopasswd) {
      var sleutel = principal + '|' + via;
      if (gezien[sleutel]) return;
      gezien[sleutel] = true;
      routes.push({
        host: host.naam, principal: principal, route: route, via: via, nopasswd: !!nopasswd
      });
    }

    host.accounts.forEach(function (account) {
      if (account.uid === 0 && account.naam !== 'root') {
        voegToe(account.naam, 'account heeft UID 0 (naast root)', 'uid0', false);
      }
    });
    host.sudo.forEach(function (regel) {
      principalsVan(host, regel).forEach(function (principal) {
        if (principal === 'root') return;
        if (regel.commandos.some(function (c) { return c.toUpperCase() === 'ALL'; })) {
          voegToe(principal, 'sudo ALL via ' + regel.wie + ' (' + regel.herkomst + ')', 'sudo-all',
            regel.nopasswd);
          return;
        }
        var escapes = regel.commandos.filter(function (c) {
          return shellEscape.indexOf(basisnaam(c)) >= 0;
        });
        if (escapes.length) {
          voegToe(principal, 'sudo op ' + escapes.join(', ') + ' via ' + regel.wie + ' (' +
            regel.herkomst + ')', 'shell-escape', regel.nopasswd);
        }
      });
    });
    return routes.sort(function (a, b) {
      if (a.principal !== b.principal) return a.principal < b.principal ? -1 : 1;
      if (a.via !== b.via) return a.via < b.via ? -1 : 1;
      return 0;
    });
  };

  function gedeeldeSleutels(hosts, routes, bevindingen) {
    var perVingerafdruk = {};
    var volgorde = [];
    hosts.forEach(function (host) {
      host.sleutels.forEach(function (sleutel) {
        if (!perVingerafdruk[sleutel.vingerafdruk]) {
          perVingerafdruk[sleutel.vingerafdruk] = [];
          volgorde.push(sleutel.vingerafdruk);
        }
        perVingerafdruk[sleutel.vingerafdruk].push([host.naam, sleutel.account]);
      });
    });
    var rootPerHost = {};
    routes.forEach(function (route) {
      if (!rootPerHost[route.host]) rootPerHost[route.host] = {};
      rootPerHost[route.host][route.principal] = true;
    });

    function bereiktRoot(host, account) {
      return account === 'root' || !!(rootPerHost[host] && rootPerHost[host][account]);
    }

    volgorde.forEach(function (vingerafdruk) {
      var plekken = perVingerafdruk[vingerafdruk];
      if (plekken.length < 2) return;
      var hostsGeraakt = uniekGesorteerd(plekken.map(function (p) { return p[0]; }));
      var accounts = uniekGesorteerd(plekken.map(function (p) { return p[1]; }));
      var label = vingerafdruk;
      var gevonden = false;
      hosts.forEach(function (h) {
        h.sleutels.forEach(function (s) {
          if (!gevonden && s.vingerafdruk === vingerafdruk) {
            gevonden = true;
            label = s.comment || ('(zonder comment, ...' + vingerafdruk.slice(-12) + ')');
          }
        });
      });
      var rootOp = uniekGesorteerd(plekken.filter(function (p) { return bereiktRoot(p[0], p[1]); })
        .map(function (p) { return p[0]; }));
      var bewijs = plekken.slice().sort(function (a, b) {
        if (a[0] !== b[0]) return a[0] < b[0] ? -1 : 1;
        if (a[1] !== b[1]) return a[1] < b[1] ? -1 : 1;
        return 0;
      }).map(function (p) { return p[0] + ':' + p[1]; }).join('; ');
      if (accounts.length > 1) {
        var detail = 'Dezelfde sleutel opent ' + accounts.length + ' verschillende accounts (' +
          accounts.join(', ') + ')';
        detail += rootOp.length
          ? ', en bereikt root op ' + rootOp.join(', ') +
            '. Achteraf is niet vast te stellen wie er handelde.'
          : '. Dat vermengt identiteiten en maakt laterale beweging triviaal.';
        bevindingen.push({
          check: 'sleutel-meerdere-accounts', ernst: rootOp.length ? 'hoog' : 'midden',
          host: hostsGeraakt.join(', '),
          titel: 'Sleutel ' + label + ' opent ' + accounts.length + ' accounts op ' +
            hostsGeraakt.length + ' hosts',
          detail: detail, bewijs: bewijs, principals: accounts
        });
        return;
      }
      if (rootOp.length > 1) {
        bevindingen.push({
          check: 'sleutel-breed-rootbereik', ernst: 'midden', host: hostsGeraakt.join(', '),
          titel: 'Sleutel ' + label + ' geeft root op ' + rootOp.length + ' hosts',
          detail: 'Een persoonlijke sleutel op meerdere hosts is normaal beheer, maar deze geeft ' +
            'root op ' + rootOp.join(', ') + '.',
          bewijs: bewijs, principals: accounts
        });
      }
    });
  }

  function uniekGesorteerd(waarden) {
    var gezien = {};
    var uit = [];
    waarden.forEach(function (w) {
      if (!gezien[w]) { gezien[w] = true; uit.push(w); }
    });
    return uit.sort();
  }

  reken.analyseer = function (hosts, iamscanRegels) {
    var shellEscape = iamscanRegels.shell_escape;
    var grens = iamscanRegels.uid_grens_systeem;
    var bevindingen = [];
    var routes = [];

    function melden(check, ernst, host, titel, detail, bewijs, principals) {
      bevindingen.push({
        check: check, ernst: ernst, host: host, titel: titel, detail: detail,
        bewijs: bewijs || '', principals: principals || []
      });
    }

    hosts.forEach(function (host) {
      routes = routes.concat(reken.routes_naar_root(host, shellEscape));
      host.ontbreekt.forEach(function (ontbreekt) {
        melden('bron-ontbreekt', 'info', host.naam,
          'Bronbestand niet aangetroffen: ' + ontbreekt,
          'De dump is onvolledig; over dit onderdeel is geen conclusie te trekken. Afwezigheid van ' +
          'bewijs is hier geen bewijs van afwezigheid.', ontbreekt);
      });
      host.accounts.forEach(function (account) {
        var interactief = !['nologin', 'false', 'sync', 'shutdown', 'halt'].some(function (s) {
          return account.shell.length >= s.length && account.shell.slice(-s.length) === s;
        });
        if (account.uid === 0 && account.naam !== 'root') {
          melden('uid0-naast-root', 'hoog', host.naam,
            'Account ' + account.naam + ' heeft UID 0',
            'Een tweede account met UID 0 is technisch root, maar valt buiten alles wat op de naam ' +
            'root is ingeregeld.',
            'etc/passwd: ' + account.naam + ':x:' + account.uid + ':' + account.gid, [account.naam]);
        }
        if (account.uid < grens && account.uid !== 0 && interactief) {
          melden('serviceaccount-met-shell', 'midden', host.naam,
            'Serviceaccount ' + account.naam + ' heeft een interactieve shell',
            'Serviceaccounts horen niet interactief te zijn. Wie het account overneemt, krijgt nu ' +
            'meteen een werkbare shell.',
            'etc/passwd: ' + account.naam + ' shell=' + account.shell, [account.naam]);
        }
      });
      host.sudo.forEach(function (regel) {
        var principals = principalsVan(host, regel).filter(function (p) { return p !== 'root'; });
        if (!principals.length) return;
        var alles = regel.commandos.some(function (c) { return c.toUpperCase() === 'ALL'; });
        if (alles && regel.nopasswd) {
          melden('sudo-all-nopasswd', 'hoog', host.naam,
            regel.wie + ' mag alles als root, zonder wachtwoord',
            'Volledige rootrechten zonder wachtwoordbevestiging. Een overgenomen sessie of sleutel ' +
            'is daarmee direct root, zonder tweede horde.',
            regel.herkomst + ': ' + regel.wie + ' ... NOPASSWD: ' + regel.commandos.join(', '),
            principals);
        } else if (alles) {
          melden('sudo-all', 'midden', host.naam, regel.wie + ' mag alles als root',
            'Volledige rootrechten. Verwacht bij beheerders, te toetsen bij de rest.',
            regel.herkomst + ': ' + regel.wie + ' (' + regel.runas + ') ' + regel.commandos.join(', '),
            principals);
        } else {
          var escapes = regel.commandos.filter(function (c) {
            return shellEscape.indexOf(basisnaam(c)) >= 0;
          });
          if (escapes.length) {
            melden('sudo-shell-escape', 'hoog', host.naam,
              regel.wie + ' kan via ' + escapes.map(basisnaam).join(', ') + ' root worden',
              "De regel oogt beperkt, maar deze commando's geven als root een shell terug of laten " +
              'willekeurig schrijven toe.',
              regel.herkomst + ': ' + regel.wie + ' ... ' + escapes.join(', '), principals);
          }
        }
      });
      var sshd = host.sshd;
      if (String(sshd.permitrootlogin || '').toLowerCase() === 'yes') {
        melden('permitrootlogin', 'hoog', host.naam, 'SSH staat rechtstreeks inloggen als root toe',
          'Directe rootlogin maakt niet herleidbaar wie er handelde en omzeilt sudo-logging.',
          'etc/ssh/sshd_config: PermitRootLogin yes');
      }
      if (String(sshd.passwordauthentication || '').toLowerCase() === 'yes') {
        melden('passwordauth', 'midden', host.naam, 'SSH accepteert wachtwoorden',
          'Wachtwoordauthenticatie maakt de host een bruikbaar doelwit voor brute force en voor ' +
          'wachtwoorden die elders al gelekt zijn.',
          'etc/ssh/sshd_config: PasswordAuthentication yes');
      }
      host.sleutels.forEach(function (sleutel) {
        if (!sleutel.comment) {
          melden('sleutel-zonder-eigenaar', 'laag', host.naam,
            'Sleutel zonder comment op account ' + sleutel.account,
            'Zonder comment is niet vast te stellen van wie de sleutel is; bij uitdiensttreding ' +
            'wordt zo een sleutel niet ingetrokken.',
            sleutel.herkomst + ': ' + sleutel.type + ' ...' + sleutel.vingerafdruk.slice(-12),
            [sleutel.account]);
        }
      });
    });

    gedeeldeSleutels(hosts, routes, bevindingen);
    var telling = {};
    ERNST.forEach(function (e) {
      telling[e] = bevindingen.filter(function (b) { return b.ernst === e; }).length;
    });
    bevindingen.sort(function (a, b) {
      if (a.ernst !== b.ernst) return ERNST.indexOf(a.ernst) - ERNST.indexOf(b.ernst);
      if (a.host !== b.host) return a.host < b.host ? -1 : 1;
      if (a.check !== b.check) return a.check < b.check ? -1 : 1;
      return 0;
    });
    return {
      hosts: hosts.map(function (h) { return h.naam; }), routes: routes,
      bevindingen: bevindingen, telling: telling
    };
  };

  reken.verdicts_iamscan = function (analyse, regels) {
    var aanwezig = {};
    analyse.bevindingen.forEach(function (b) { aanwezig[b.check] = true; });
    var uit = {};
    regels.items.forEach(function (item) {
      if (item.regel.type !== 'iamscan') return;
      uit[item.id] = item.regel.parameters.checks.some(function (c) { return aanwezig[c]; })
        ? 'fail' : 'pass';
    });
    return uit;
  };

  function dumpItems(regels) {
    return regels.items.filter(function (i) { return i.bron === 'iamscan_dump'; })
      .map(function (i) { return i.id; });
  }

  reken.toets_iamscan_dump = function (inhoud, peildatum, regels) {
    if (!inhoud || typeof inhoud !== 'object' || !Object.keys(inhoud).length) {
      return unparsed(dumpItems(regels), ['geen leesbare bestanden in de dump']);
    }
    var hosts = reken.lees_dump(inhoud);
    if (!hosts.length) {
      return unparsed(dumpItems(regels),
        ['geen host gevonden; verwacht een map per host met etc/passwd erin']);
    }
    var analyse = reken.analyseer(hosts, regels.iamscan);
    var uit = uitkomst(reken.verdicts_iamscan(analyse, regels),
      { hosts: hosts.length, routes: analyse.routes.length, bevindingen: analyse.telling },
      analyse.routes.slice(0, 10).map(function (r) {
        return r.host + ' ' + r.principal + ' via ' + r.via;
      }));
    uit.analyse = analyse;
    return uit;
  };

  var TOETSEN = {
    crown_jewels_csv: reken.toets_crown_jewels_csv,
    asset_inventory_csv: reken.toets_asset_inventory_csv,
    fw_config: reken.toets_fw_config,
    vpn_inventory_csv: reken.toets_vpn_inventory_csv,
    entra_privileged_csv: reken.toets_entra_privileged_csv,
    ad_tier0_csv: reken.toets_ad_tier0_csv,
    gpo_export_xml: reken.toets_gpo_export_xml,
    ad_svc_accounts_csv: reken.toets_ad_svc_accounts_csv,
    laps_csv: reken.toets_laps_csv,
    entra_users_csv: reken.toets_entra_users_csv,
    siem_flow_csv: reken.toets_siem_flow_csv,
    sysmon_config_xml: reken.toets_sysmon_config_xml,
    entra_risky_csv: reken.toets_entra_risky_csv,
    fw_flow_csv: reken.toets_fw_flow_csv,
    siem_rules_json: reken.toets_siem_rules_json,
    nessus_xml: reken.toets_nessus_xml,
    edge_devices_csv: reken.toets_edge_devices_csv,
    eol_inventory_csv: reken.toets_eol_inventory_csv,
    nmap_xml: reken.toets_nmap_xml,
    veeam_report_csv: reken.toets_veeam_report_csv,
    backup_ad_audit_csv: reken.toets_backup_ad_audit_csv,
    document: reken.toets_document,
    wdac_policy_xml: reken.toets_wdac_policy_xml,
    asr_csv: reken.toets_asr_csv,
    local_admins_csv: reken.toets_local_admins_csv,
    intune_usb_csv: reken.toets_intune_usb_csv,
    entra_admins_csv: reken.toets_entra_admins_csv,
    siem_behavior_rules_json: reken.toets_siem_behavior_rules_json,
    fw_category_csv: reken.toets_fw_category_csv,
    iamscan_dump: reken.toets_iamscan_dump
  };

  reken.toets = function (bronId, inhoud, peildatum, regels, itemId) {
    var functie = TOETSEN[bronId];
    if (!functie) return uitkomst({}, {}, [], null, ['onbekende bron: ' + bronId]);
    if (bronId === 'document') return functie(inhoud, peildatum, regels, itemId);
    return functie(inhoud, peildatum, regels);
  };

  // De dump uitpakken. Python leest tar en tar.gz met tarfile; de browser doet het hier zelf:
  // gzip via DecompressionStream, daarna de tarblokken van 512 bytes. Dat is asynchroon, dus deze
  // functie geeft een belofte terug waar de Python-kant een dict teruggeeft.

  function octaal(bytes, van, lengte) {
    var tekst = '';
    for (var i = van; i < van + lengte; i++) {
      var teken = bytes[i];
      if (teken === 0 || teken === 32) break;
      tekst += String.fromCharCode(teken);
    }
    return tekst ? parseInt(tekst, 8) || 0 : 0;
  }

  function tekstVeld(bytes, van, lengte) {
    var einde = van;
    while (einde < van + lengte && bytes[einde] !== 0) einde += 1;
    return new TextDecoder('utf-8').decode(bytes.subarray(van, einde));
  }

  function tarBestanden(bytes) {
    var uit = {};
    var decoder = new TextDecoder('utf-8');
    var offset = 0;
    var langeNaam = null;
    while (offset + 512 <= bytes.length) {
      var naam = tekstVeld(bytes, offset, 100);
      if (!naam && !langeNaam) { offset += 512; continue; }
      var grootte = octaal(bytes, offset + 124, 12);
      var soortByte = bytes[offset + 156] || 0;
      var soort = String.fromCharCode(soortByte);
      var prefix = tekstVeld(bytes, offset + 345, 155);
      var start = offset + 512;
      var einde = start + grootte;
      if (soort === 'L') {
        langeNaam = decoder.decode(bytes.subarray(start, einde)).replace(/\0+$/, '');
      } else if (soortByte === 48 || soortByte === 0 || soortByte === 32) {
        // '0' is een gewoon bestand; een lege of nulbyte betekent hetzelfde (oude tars).
        var pad = langeNaam || (prefix ? prefix + '/' + naam : naam);
        uit[pad] = decoder.decode(bytes.subarray(start, einde));
        langeNaam = null;
      } else {
        langeNaam = null;
      }
      offset = start + Math.ceil(grootte / 512) * 512;
    }
    return uit;
  }

  reken.dump_uit_tar = function (ruw) {
    var bytes = ruw instanceof Uint8Array ? ruw : new Uint8Array(ruw);
    if (bytes.length > 2 && bytes[0] === 0x1f && bytes[1] === 0x8b) {
      var stroom = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
      return new Response(stroom).arrayBuffer().then(function (buffer) {
        return tarBestanden(new Uint8Array(buffer));
      });
    }
    return Promise.resolve(tarBestanden(bytes));
  };

  // ── Van metingen naar de aanvalspaden ──────────────────────────────────────

  reken.items_per_chokepoint = function (regels) {
    var uit = {};
    regels.items.forEach(function (item) {
      if (!item.chokepoint) return;
      if (!uit[item.chokepoint]) uit[item.chokepoint] = [];
      uit[item.chokepoint].push(item.id);
    });
    Object.keys(uit).forEach(function (k) { uit[k] = uit[k].slice().sort(); });
    return uit;
  };

  reken.verdict_van = function (dossier, itemId) {
    var meting = (dossier.metingen || {})[itemId];
    return meting ? meting.verdict : 'geen_bewijs';
  };

  reken.per_chokepoint = function (regels, paden, dossier) {
    var perItem = reken.items_per_chokepoint(regels);
    var uit = {};
    paden.bladeren.forEach(function (blad) {
      (blad.chokepoints || []).forEach(function (cp) {
        var items = perItem[cp.id] || [];
        var metingen = items.map(function (i) {
          return { id: i, verdict: reken.verdict_van(dossier, i) };
        });
        var gemeten = metingen.filter(function (m) { return m.verdict !== 'geen_bewijs'; });
        var afgeleid;
        if (!items.length) afgeleid = 'geen_meting';
        else if (!gemeten.length) afgeleid = 'unknown';
        else if (gemeten.some(function (m) { return m.verdict === 'fail'; })) afgeleid = 'no';
        else if (gemeten.every(function (m) { return m.verdict === 'pass'; })) afgeleid = 'yes';
        else afgeleid = 'unknown';
        uit[cp.id] = {
          pad: blad.id, vraag_id: cp.vraag_id, titel: cp.titel, drp: cp.drp, bewijs: cp.bewijs,
          items: metingen, afgeleid: afgeleid
        };
      });
    });
    return uit;
  };

  var STRENGSTE = { no: 0, unknown: 1, yes: 2 };

  reken.afgeleide_antwoorden = function (regels, paden, dossier) {
    var uit = {};
    var cps = reken.per_chokepoint(regels, paden, dossier);
    Object.keys(cps).forEach(function (id) {
      var cp = cps[id];
      if (cp.afgeleid === 'geen_meting' || cp.afgeleid === 'unknown') return;
      if (cp.vraag_id === 'model') return;
      var huidig = uit[cp.vraag_id];
      if (huidig === undefined || STRENGSTE[cp.afgeleid] < STRENGSTE[huidig]) {
        uit[cp.vraag_id] = cp.afgeleid;
      }
    });
    return uit;
  };

  reken.witte_vlekken = function (regels, paden) {
    var perItem = reken.items_per_chokepoint(regels);
    var uit = [];
    paden.bladeren.forEach(function (blad) {
      (blad.chokepoints || []).forEach(function (cp) {
        if (perItem[cp.id] && perItem[cp.id].length) return;
        uit.push({
          pad: blad.id, pad_titel: blad.titel, chokepoint: cp.id, titel: cp.titel, drp: cp.drp,
          bewijs: cp.bewijs
        });
      });
    });
    return uit;
  };

  reken.dashboard = function (regels, paden, dossier) {
    var items = regels.items;
    var verdicts = {};
    items.forEach(function (i) { verdicts[i.id] = reken.verdict_van(dossier, i.id); });
    var telVerdict = {};
    VERDICTS.forEach(function (v) {
      telVerdict[v] = items.filter(function (i) { return verdicts[i.id] === v; }).length;
    });
    var telSoort = {};
    ['A', 'B', 'C', 'D'].forEach(function (s) {
      telSoort[s] = items.filter(function (i) { return i.soort === s; }).length;
    });
    var perCategorie = {};
    regels.categorieen.forEach(function (categorie) {
      var eigen = items.filter(function (i) { return i.categorie === categorie.nummer; });
      var telling = {};
      VERDICTS.forEach(function (v) {
        telling[v] = eigen.filter(function (i) { return verdicts[i.id] === v; }).length;
      });
      perCategorie[String(categorie.nummer)] = telling;
    });
    var cps = reken.per_chokepoint(regels, paden, dossier);
    var ids = Object.keys(cps);
    return {
      items: {
        totaal: items.length,
        gemeten: items.filter(function (i) { return verdicts[i.id] !== 'geen_bewijs'; }).length
      },
      verdict: telVerdict,
      soort: telSoort,
      categorie: perCategorie,
      chokepoints: {
        totaal: ids.length,
        gemeten: ids.filter(function (id) {
          return cps[id].items.some(function (m) { return m.verdict !== 'geen_bewijs'; });
        }).length,
        witte_vlekken: reken.witte_vlekken(regels, paden).length
      }
    };
  };

  reken.zelfcheck_export = function (regels, paden, dossier, vandaagTekst) {
    var antwoorden = reken.afgeleide_antwoorden(regels, paden, dossier);
    var herkomst = {};
    var cps = reken.per_chokepoint(regels, paden, dossier);
    Object.keys(cps).forEach(function (id) {
      var cp = cps[id];
      if (!Object.prototype.hasOwnProperty.call(antwoorden, cp.vraag_id)) return;
      if (!herkomst[cp.vraag_id]) herkomst[cp.vraag_id] = { items: [], verdicts: [] };
      var regel = herkomst[cp.vraag_id];
      cp.items.forEach(function (meting) {
        if (meting.verdict !== 'geen_bewijs' && regel.items.indexOf(meting.id) < 0) {
          regel.items.push(meting.id);
          regel.verdicts.push(meting.verdict);
        }
      });
    });
    return {
      formaat: 'zelfcheck-antwoorden', versie: 1, bron: 'meting', gemaakt: vandaagTekst,
      paden_versie: paden.versie, antwoorden: antwoorden, herkomst: herkomst
    };
  };

  // ── Dossier ────────────────────────────────────────────────────────────────

  function canoniek(waarde) {
    if (waarde === null || waarde === undefined) return 'null';
    if (Array.isArray(waarde)) return '[' + waarde.map(canoniek).join(',') + ']';
    if (typeof waarde === 'object') {
      return '{' + Object.keys(waarde).sort().map(function (sleutel) {
        return JSON.stringify(sleutel) + ':' + canoniek(waarde[sleutel]);
      }).join(',') + '}';
    }
    if (typeof waarde === 'boolean') return waarde ? 'true' : 'false';
    return JSON.stringify(waarde);
  }

  function hexVan(buffer) {
    return Array.prototype.map.call(new Uint8Array(buffer), function (b) {
      return b.toString(16).padStart(2, '0');
    }).join('');
  }

  reken.sha256_tekst = function (inhoud) {
    var bytes = inhoud instanceof Uint8Array ? inhoud
      : (inhoud instanceof ArrayBuffer ? new Uint8Array(inhoud)
        : new TextEncoder().encode(String(inhoud)));
    return crypto.subtle.digest('SHA-256', bytes).then(hexVan);
  };

  reken.vingerafdruk = function (regels) {
    var kern = {};
    ['items', 'bronnen', 'tijd', 'iamscan', 'soorten'].forEach(function (s) { kern[s] = regels[s]; });
    return reken.sha256_tekst(canoniek(kern));
  };

  reken.slug = function (tekst) {
    var laag = String(tekst === null || tekst === undefined ? '' : tekst).toLowerCase();
    var schoon = '';
    for (var i = 0; i < laag.length; i++) {
      var teken = laag.charAt(i);
      schoon += (teken >= 'a' && teken <= 'z') || (teken >= '0' && teken <= '9') ? teken : '-';
    }
    var uit = schoon.split('-').filter(function (d) { return d !== ''; }).join('-')
      .slice(0, 40).replace(/^-+|-+$/g, '');
    return uit || 'organisatie';
  };

  reken.bestandsnaam = function (dossier, vandaagTekst) {
    return 'meting-dossier-' + reken.slug((dossier.organisatie || {}).naam) + '-' + vandaagTekst +
      '.json';
  };

  reken.nieuw_dossier = function (regels, paden, peildatum) {
    return {
      formaat: 'meting-dossier', versie: 1, regels_versie: regels.versie,
      regels_sha256: BRON.vingerafdruk, paden_versie: paden.versie, bijgewerkt: '',
      organisatie: { naam: '', peildatum: peildatum },
      metingen: {}, documenten: {}
    };
  };

  // ── De pagina ──────────────────────────────────────────────────────────────

  function el(id) { return document.getElementById(id); }

  function maak(tag, tekst, attributen) {
    var knoop = document.createElement(tag);
    if (tekst !== null && tekst !== undefined) knoop.textContent = String(tekst);
    if (attributen) {
      Object.keys(attributen).forEach(function (naam) {
        knoop.setAttribute(naam, String(attributen[naam]));
      });
    }
    return knoop;
  }

  function leegMaken(knoop) {
    while (knoop && knoop.firstChild) knoop.removeChild(knoop.firstChild);
    return knoop;
  }

  function vandaag() {
    var nu = new Date();
    return nu.getFullYear() + '-' + String(nu.getMonth() + 1).padStart(2, '0') + '-' +
      String(nu.getDate()).padStart(2, '0');
  }

  function rij(cellen, soort) {
    var tr = maak('tr');
    cellen.forEach(function (cel) {
      var td = maak(soort || 'td');
      if (cel && cel.nodeType === 1) td.appendChild(cel);
      else td.textContent = cel === null || cel === undefined ? '' : String(cel);
      tr.appendChild(td);
    });
    return tr;
  }

  function tabel(doel, koppen, rijen) {
    leegMaken(doel);
    var kop = maak('thead');
    kop.appendChild(rij(koppen, 'th'));
    doel.appendChild(kop);
    var lijf = maak('tbody');
    rijen.forEach(function (r) { lijf.appendChild(r); });
    doel.appendChild(lijf);
    return doel;
  }

  function vlag(verdict) {
    return maak('span', VERDICT_LABEL[verdict] || verdict, {
      class: 'vlag verdict v-' + verdict
    });
  }

  function bronVan(bronId) {
    return REGELS.bronnen.filter(function (b) { return b.id === bronId; })[0] || { id: bronId };
  }

  var ACCEPT = {
    csv: '.csv,.txt,text/csv', xml: '.xml,.nessus,text/xml', json: '.json,application/json',
    tekst: '.txt,.md,.log,text/plain'
  };

  var dossier = null;
  var documentTeksten = {};
  var bronmeldingen = {};
  var statusMelding = null;
  var statusLetOp = false;

  // Dossier

  function leesLokaal() {
    try {
      var ruw = window.localStorage.getItem(SLEUTEL);
      return ruw ? JSON.parse(ruw) : null;
    } catch (fout) {
      return null;
    }
  }

  function bewaarLokaal() {
    dossier.bijgewerkt = vandaag();
    try {
      window.localStorage.setItem(SLEUTEL, JSON.stringify(dossier));
    } catch (fout) {
      /* privacymodus of vol geheugen: het dossier blijft in deze sessie werken */
    }
  }

  function peildatum() {
    return (dossier.organisatie || {}).peildatum || '';
  }

  function magMeten() {
    return peildatum() !== '';
  }

  function meld(tekst, letOp) {
    statusMelding = tekst;
    statusLetOp = !!letOp;
    status();
  }

  function status() {
    var regel = el('dossier-status');
    var letOp = statusLetOp;
    var tekst;
    if (statusMelding) {
      tekst = statusMelding;
    } else if (!magMeten()) {
      tekst = 'Vul eerst een peildatum in; zonder peildatum is niet te zeggen of een artefact vers ' +
        'genoeg is.';
      letOp = true;
    } else {
      var stand = reken.dashboard(REGELS, PADEN, dossier);
      tekst = stand.items.gemeten + ' van ' + stand.items.totaal + ' gemeten · ' +
        stand.chokepoints.gemeten + ' van ' + stand.chokepoints.totaal + ' chokepoints geraakt' +
        (dossier.bijgewerkt ? ' · bijgewerkt ' + dossier.bijgewerkt : '');
    }
    regel.textContent = tekst;
    regel.className = letOp ? 'let-op' : '';
  }

  // Metingen wegschrijven

  function schrijfMeting(bronId, gemeten, bestandsnaam, hash) {
    Object.keys(gemeten.verdicts).forEach(function (itemId) {
      dossier.metingen[itemId] = {
        bron: bronId, bestand: bestandsnaam, sha256: hash, gemeten: vandaag(),
        artefact_datum: gemeten.artefact_datum, verdict: gemeten.verdicts[itemId],
        samenvatting: gemeten.samenvatting, voorbeeld: gemeten.voorbeeld, fouten: gemeten.fouten,
        notitie: (dossier.metingen[itemId] || {}).notitie || ''
      };
    });
    if (gemeten.analyse) dossier.iamscan = gemeten.analyse;
    statusMelding = null;
    statusLetOp = false;
    bewaarLokaal();
    werkBij();
  }

  function bronmelding(sleutel, tekst) {
    bronmeldingen[sleutel] = tekst;
    var regel = document.querySelector('[data-bronstatus="' + sleutel + '"]');
    if (regel) regel.textContent = tekst;
  }

  function meetBestand(bronId, bestand) {
    if (!magMeten()) return;
    bronmelding(bronId, 'Bezig met lezen van ' + bestand.name + '...');
    if (bronId === 'iamscan_dump') {
      bestand.arrayBuffer().then(function (buffer) {
        return reken.sha256_tekst(new Uint8Array(buffer)).then(function (hash) {
          return reken.dump_uit_tar(buffer).then(function (bestanden) {
            var uit = reken.toets('iamscan_dump', bestanden, peildatum(), REGELS);
            schrijfMeting(bronId, uit, bestand.name, hash);
            bronmelding(bronId, bestand.name + ': ' + Object.keys(bestanden).length +
              ' bestanden, ' + (uit.samenvatting.hosts || 0) + ' hosts.');
          });
        });
      }).catch(function (fout) {
        bronmelding(bronId, 'Lezen mislukt: ' + fout.message + ' (verwacht een tar of tar.gz)');
      });
      return;
    }
    bestand.text().then(function (tekst) {
      return reken.sha256_tekst(tekst).then(function (hash) {
        var uit = reken.toets(bronId, tekst, peildatum(), REGELS);
        schrijfMeting(bronId, uit, bestand.name, hash);
        bronmelding(bronId, bestand.name + ' gelezen (sha256 ' + hash.slice(0, 12) + ').' +
          (uit.fouten.length ? ' ' + uit.fouten.join('; ') : ''));
      });
    }).catch(function (fout) {
      bronmelding(bronId, 'Lezen mislukt: ' + fout.message);
    });
  }

  function meetMap(bestanden) {
    if (!magMeten() || !bestanden.length) return;
    var lezers = [];
    for (var i = 0; i < bestanden.length; i++) {
      (function (bestand) {
        lezers.push(bestand.text().then(function (tekst) {
          return { pad: bestand.webkitRelativePath || bestand.name, tekst: tekst };
        }));
      })(bestanden[i]);
    }
    bronmelding('iamscan_dump', 'Bezig met lezen van ' + bestanden.length + ' bestanden...');
    Promise.all(lezers).then(function (gelezen) {
      var kaart = {};
      gelezen.forEach(function (g) { kaart[g.pad] = g.tekst; });
      return reken.sha256_tekst(canoniek(kaart)).then(function (hash) {
        var uit = reken.toets('iamscan_dump', kaart, peildatum(), REGELS);
        var naam = (gelezen[0].pad.split('/')[0] || 'map') + ' (map)';
        schrijfMeting('iamscan_dump', uit, naam, hash);
        bronmelding('iamscan_dump', naam + ': ' + gelezen.length + ' bestanden, ' +
          (uit.samenvatting.hosts || 0) + ' hosts.');
      });
    }).catch(function (fout) {
      bronmelding('iamscan_dump', 'Lezen mislukt: ' + fout.message);
    });
  }

  function toetsDocument(itemId) {
    if (!magMeten()) return;
    var tekst = documentTeksten[itemId] || '';
    if (!tekst.trim()) {
      bronmelding('document-' + itemId, 'Plak eerst de tekst van het rapport.');
      return;
    }
    reken.sha256_tekst(tekst).then(function (hash) {
      var uit = reken.toets('document', tekst, peildatum(), REGELS, itemId);
      var gevonden = uit.samenvatting.trefwoorden.filter(function (t) {
        return uit.fouten.indexOf('trefwoord niet gevonden: ' + t) < 0;
      });
      schrijfMeting('document', uit, 'geplakte tekst', hash);
      dossier.documenten[itemId] = {
        tekst_sha256: hash, datum_gevonden: uit.artefact_datum, trefwoorden_gevonden: gevonden
      };
      bewaarLokaal();
      bronmelding('document-' + itemId, uit.fouten.length ? uit.fouten.join('; ')
        : 'Getoetst (sha256 ' + hash.slice(0, 12) + '). De tekst zelf gaat niet mee in het dossier.');
    });
  }

  // Een voorstel van de AI-hulp: een omgezette tabel, nog geen meting.
  //
  // De AI-pagina schrijft nooit in het dossier. Hier legt de gebruiker het voorstel naast het contract,
  // ziet per rij of het citaat in zijn eigen invoer voorkomt, en pas bij Overnemen wordt er getoetst.
  // Dat toetsen gebeurt met exact dezelfde regels als bij een gekozen bestand; het enige verschil is
  // dat de meting daarna herkomst_ai draagt, want omgezet bewijs is zwakker bewijs.

  var voorstel = null;

  function bronVanVoorstel(data) {
    return REGELS.bronnen.filter(function (b) { return b.id === data.bron; })[0] || null;
  }

  function laadVoorstel(data) {
    if (!data || data.formaat !== 'meting-voorstel') {
      meld('Dit is geen voorstel van de AI-hulp van de meting.', true);
      return;
    }
    if (data.tool !== 'meting') {
      meld('Dit voorstel hoort bij een andere tool (' + data.tool + ').', true);
      return;
    }
    if (!bronVanVoorstel(data)) {
      meld('Dit voorstel gaat over een bron die deze versie niet kent (' + data.bron + ').', true);
      return;
    }
    if (data.tool_vingerafdruk && data.tool_vingerafdruk !== BRON.vingerafdruk) {
      meld('Let op: dit voorstel is gemaakt met een andere versie van de meetregels; loop de rijen na.',
        true);
    }
    voorstel = data;
    tekenVoorstel();
    el('voorstel-blok').hidden = false;
    naarScherm('scherm-items');
    el('voorstel-blok').scrollIntoView({ block: 'start' });
  }

  /* De kolommen van het contract, in de volgorde van het contract; wat het model extra verzon, blijft
     buiten de tabel en dus buiten de meting. */
  function kolommenVan(bron) {
    return bron.kolommen.concat(bron.optioneel);
  }

  /* De AI-pagina heeft het citaat al getoetst tegen de invoer; die invoer zit niet in het voorstel,
     dus die toets is hier niet over te doen. Staat het oordeel er niet in (een ouder voorstel), dan
     telt de rij mee: afwezigheid van het oordeel is geen afkeuring. */
  function citaatKlopt(rij) {
    return rij.bronregel_klopt !== false;
  }

  function bruikbareRijen() {
    return (voorstel.items || []).filter(citaatKlopt);
  }

  function tekenVoorstel() {
    var bron = bronVanVoorstel(voorstel);
    var kolommen = kolommenVan(bron);
    el('voorstel-kop').textContent = 'Naar ' + bron.titel + ' (' + bron.id + ') · ' +
      (voorstel.items || []).length + ' rijen · ' + voorstel.leverancier + ' (' + voorstel.model +
      ') · ' + voorstel.gemaakt + ' · invoer ' + ((voorstel.invoer || {}).naam || '') + ' (' +
      String((voorstel.invoer || {}).sha256 || '').slice(0, 12) + ')';
    var afgekeurd = 0;
    tabel(el('tabel-voorstel'), kolommen.concat(['citaat uit de invoer']),
      (voorstel.items || []).map(function (r, index) {
        var klopt = citaatKlopt(r);
        if (!klopt) afgekeurd += 1;
        var cellen = kolommen.map(function (k) { return r[k] === undefined ? '' : r[k]; });
        var tr = rij(cellen.concat([(klopt ? '' : 'niet in de invoer: ') + (r.bronregel || '')]));
        tr.setAttribute('data-voorstel', String(index));
        if (!klopt) tr.className = 'witte-vlek';
        return tr;
      }));
    el('voorstel-afgekeurd').textContent = afgekeurd
      ? afgekeurd + ' van de ' + (voorstel.items || []).length + ' rijen dragen een citaat dat niet ' +
        'woordelijk in je invoer stond. Die gaan niet mee in de toets; het model heeft ze vermoedelijk ' +
        'zelf aangevuld.'
      : '';
    var onzeker = (voorstel.onzeker || []).concat(voorstel.waarschuwingen || []);
    el('voorstel-onzeker').textContent = onzeker.length
      ? 'Het model meldde: ' + onzeker.join(' · ') : 'Het model meldde geen twijfels.';
  }

  /* De omgezette tabel terug naar csv, zodat hij door dezelfde toets gaat als een gekozen bestand.
     Een waarde met een komma, een aanhalingsteken of een regeleinde wordt geciteerd. */
  function naarCsv(kolommen, rijen) {
    function cel(waarde) {
      var tekst = waarde === undefined || waarde === null ? '' : String(waarde);
      return /[",\n]/.test(tekst) ? '"' + tekst.replace(/"/g, '""') + '"' : tekst;
    }
    return [kolommen.join(',')].concat(rijen.map(function (r) {
      return kolommen.map(function (k) { return cel(r[k]); }).join(',');
    })).join('\n') + '\n';
  }

  function neemVoorstelOver() {
    if (!voorstel || !magMeten()) return;
    var bron = bronVanVoorstel(voorstel);
    var rijen = bruikbareRijen();
    if (!rijen.length) {
      meld('Geen enkele rij uit dit voorstel is te herleiden tot je invoer; er valt niets te toetsen.',
        true);
      return;
    }
    var tekst = naarCsv(kolommenVan(bron), rijen);
    reken.sha256_tekst(tekst).then(function (hash) {
      var uit = reken.toets(bron.id, tekst, peildatum(), REGELS);
      var naam = 'AI-voorstel: ' + ((voorstel.invoer || {}).naam || 'geplakte tekst');
      schrijfMeting(bron.id, uit, naam, hash);
      Object.keys(uit.verdicts).forEach(function (itemId) {
        dossier.metingen[itemId].herkomst_ai = {
          leverancier: voorstel.leverancier, model: voorstel.model, gemaakt: voorstel.gemaakt,
          opdrachten_versie: voorstel.opdrachten_versie,
          invoer_sha256: (voorstel.invoer || {}).sha256 || '', rijen: rijen.length,
          rijen_zonder_citaat: (voorstel.items || []).length - rijen.length
        };
      });
      bewaarLokaal();
      voorstel = null;
      el('voorstel-blok').hidden = true;
      werkBij();
      meld(Object.keys(uit.verdicts).length + ' meetregels getoetst op de omgezette tabel. In de ' +
        'uitdraai staat dat de invoer met AI is omgezet.', false);
    });
  }

  // Scherm 1: de meetregels

  var WIE_LABEL = { zelf: 'zelf te trekken', beheer: 'vraag aan beheer', afspraak: 'aparte afspraak' };

  function wieVan(item) {
    var bron = bronVan(item.bron === 'document' ? 'document' : item.bron);
    return bron.wie || '';
  }

  /* Het uitklapveld bij elke plek waar je data aanlevert: waar moet je zijn, wat klik je aan, welke
     query kun je draaien, en hoe heten de kolommen daar tegenover het contract. Wat er niet is, komt er
     ook niet als lege kop in te staan. */
  function receptblok(bron) {
    var recept = bron.recept;
    var blok = maak('details', null, { class: 'recept' });
    blok.appendChild(maak('summary', recept ? 'Waar vind ik dit, en hoe trek ik het?'
      : 'Wat moet ik aanleveren?'));

    if (bron.uitleg) blok.appendChild(maak('p', bron.uitleg, { class: 'klein' }));

    if (recept && recept.waar) {
      var waar = maak('p', null, { class: 'klein' });
      waar.appendChild(maak('strong', 'Waar: '));
      waar.appendChild(maak('span', recept.waar));
      blok.appendChild(waar);
    }

    if (recept && (recept.stappen || []).length) {
      var lijst = maak('ol', null, { class: 'stappen' });
      recept.stappen.forEach(function (stap) { lijst.appendChild(maak('li', stap)); });
      blok.appendChild(lijst);
    }

    if (recept && recept.query) {
      var kop = maak('p', null, { class: 'klein' });
      kop.appendChild(maak('strong', recept.query.taal + ': '));
      blok.appendChild(kop);
      var pre = maak('pre', recept.query.tekst, { class: 'query' });
      blok.appendChild(pre);
    }

    if (bron.kolommen && bron.kolommen.length) {
      var kolommen = maak('p', 'Het contract vraagt: ', { class: 'klein' });
      kolommen.appendChild(maak('code', bron.kolommen.join(', ')));
      if (bron.optioneel && bron.optioneel.length) {
        kolommen.appendChild(maak('span', ' · en als je ze hebt: '));
        kolommen.appendChild(maak('code', bron.optioneel.join(', ')));
      }
      blok.appendChild(kolommen);
    }

    if (recept && recept.kolommen) {
      var tabel = maak('table', null, { class: 'regels kolomkoppeling' });
      var kop2 = maak('thead');
      kop2.appendChild(rij(['Kolom in de export', 'Hernoem naar'], 'th'));
      tabel.appendChild(kop2);
      var lijf = maak('tbody');
      Object.keys(recept.kolommen).forEach(function (van) {
        lijf.appendChild(rij([van, recept.kolommen[van]]));
      });
      tabel.appendChild(lijf);
      blok.appendChild(tabel);
    }

    if (recept && recept.let_op) {
      blok.appendChild(maak('p', recept.let_op, { class: 'let-op-regel' }));
    }

    if (!recept && bron.hoe) blok.appendChild(maak('p', bron.hoe, { class: 'klein' }));

    var voet = maak('p', null, { class: 'klein voetnoot' });
    voet.appendChild(maak('span', recept && recept.gecontroleerd
      ? 'Menupaden nagelopen in ' + recept.gecontroleerd + '; portalen hernoemen hun schermen, dus '
        + 'wijkt het af, dan is de stap meestal dezelfde onder een andere naam.'
      : 'Voor deze bron staat er nog geen uitgeschreven recept; wat hierboven staat is wat we weten.'));
    blok.appendChild(voet);
    return blok;
  }

  function kiezer(item) {
    var bronId = item.bron;
    var bron = bronVan(bronId);
    var blok = maak('div', null, { class: 'kiezer nietprint' });
    var kop = maak('p', null, { class: 'klein' });
    kop.appendChild(maak('strong', bron.titel));
    kop.appendChild(maak('span', ' (' + bron.formaat + ')'));
    if (bron.wie) {
      kop.appendChild(maak('span', ' '));
      kop.appendChild(maak('span', WIE_LABEL[bron.wie] || bron.wie, {
        class: 'vlag w-' + bron.wie, title: (REGELS.wie || {})[bron.wie] || ''
      }));
    }
    if (bron.kolommen && bron.kolommen.length) {
      kop.appendChild(maak('span', ' · verplichte kolommen: '));
      kop.appendChild(maak('code', bron.kolommen.join(', ')));
    }
    if (bron.optioneel && bron.optioneel.length) {
      kop.appendChild(maak('span', ' · gebruikt indien aanwezig: '));
      kop.appendChild(maak('code', bron.optioneel.join(', ')));
    }
    blok.appendChild(kop);
    if (bron.hoe) blok.appendChild(maak('p', bron.hoe, { class: 'klein' }));
    blok.appendChild(receptblok(bron));

    var invoer = maak('input', null, {
      type: 'file', 'data-bron': bronId, accept: ACCEPT[bron.formaat] || ''
    });
    invoer.addEventListener('change', function () {
      if (invoer.files && invoer.files[0]) meetBestand(bronId, invoer.files[0]);
    });
    if (bronId === 'iamscan_dump') invoer.setAttribute('accept', '.tar,.gz,.tgz');
    blok.appendChild(invoer);

    if (bronId === 'iamscan_dump') {
      blok.appendChild(maak('span', ' of een uitgepakte map: ', { class: 'klein' }));
      var map = maak('input', null, { type: 'file', 'data-bron': bronId });
      map.setAttribute('webkitdirectory', '');
      map.addEventListener('change', function () { meetMap(map.files); });
      blok.appendChild(map);
    }
    blok.appendChild(maak('p', bronmeldingen[bronId] || '', {
      class: 'klein', 'data-bronstatus': bronId
    }));
    return blok;
  }

  function documentkiezer(item) {
    var blok = maak('div', null, { class: 'kiezer nietprint' });
    var wie = bronVan('document').wie;
    if (wie) {
      var kop = maak('p', null, { class: 'klein' });
      kop.appendChild(maak('strong', 'Rapport of verslag'));
      kop.appendChild(maak('span', ' '));
      kop.appendChild(maak('span', WIE_LABEL[wie] || wie, {
        class: 'vlag w-' + wie, title: (REGELS.wie || {})[wie] || ''
      }));
      blok.appendChild(kop);
    }
    var uitleg = maak('p', null, { class: 'klein' });
    uitleg.appendChild(maak('span', bronVan('document').uitleg + ' Gezocht wordt op: '));
    uitleg.appendChild(maak('code', item.regel.parameters.trefwoorden.join('  ·  ')));
    uitleg.appendChild(maak('span', ' · niet ouder dan ' + item.regel.parameters.maximale_maanden +
      ' maanden.'));
    blok.appendChild(uitleg);
    blok.appendChild(receptblok(bronVan('document')));
    var vak = maak('textarea', documentTeksten[item.id] || '', {
      'data-document': item.id, rows: '4'
    });
    vak.addEventListener('input', function () { documentTeksten[item.id] = vak.value; });
    blok.appendChild(vak);
    var knop = maak('button', 'Toets document', { type: 'button', class: 'toets' });
    knop.addEventListener('click', function () { toetsDocument(item.id); });
    blok.appendChild(knop);
    blok.appendChild(maak('p', bronmeldingen['document-' + item.id] || '', {
      class: 'klein', 'data-bronstatus': 'document-' + item.id
    }));
    return blok;
  }

  function samenvattingTekst(itemId, meting) {
    var s = meting.samenvatting || {};
    var delen = [];
    if (itemId === '1.1' && s.met_eigenaar !== undefined) {
      delen.push(s.met_eigenaar + ' van ' + s.totaal + ' (' +
        reken.procent(s.met_eigenaar, s.totaal) + '%)');
    } else if (itemId === '1.2' && s.compleet !== undefined) {
      delen.push(s.compleet + ' van ' + s.totaal + ' (' + s.pct + '%)');
    } else if (s.totaal !== undefined && s.gedekt !== undefined) {
      delen.push(s.gedekt + ' van ' + s.totaal + ' (' + s.pct + '%)');
    }
    if (s.hosts !== undefined) delen.push(s.hosts + ' hosts, ' + s.routes + ' routes naar root');
    if (s.bevindingen) {
      delen.push(ERNST.map(function (e) { return s.bevindingen[e] + ' ' + e; }).join(', '));
    }
    if (s.dagen_oud !== undefined && s.dagen_oud !== null) {
      delen.push('artefact ' + s.dagen_oud + ' dagen oud');
    }
    if (s.in_venster !== undefined) delen.push(s.in_venster + ' regels in het venster');
    if (s.east_west !== undefined) delen.push(s.east_west + ' east-west');
    if (s.inactief !== undefined) delen.push(s.inactief + ' inactief');
    if (s.risky !== undefined) delen.push(s.risky + ' met risico');
    if (s.rulegroups !== undefined) delen.push(s.rulegroups + ' rulegroups');
    if (s.kritiek !== undefined) delen.push(s.kritiek + ' kritieke bevindingen');
    if (s.open_poorten !== undefined) delen.push(s.open_poorten + ' open poorten');
    if (s.drempel !== undefined) delen.push('drempel ' + s.drempel);
    if (s.gevonden !== undefined && s.trefwoorden) {
      delen.push(s.gevonden + ' van ' + s.trefwoorden.length + ' trefwoorden');
    }
    if (s.formaat !== undefined) delen.push(s.formaat);
    if (s.per_bron) {
      delen.push(Object.keys(s.per_bron).map(function (b) {
        return b + ': ' + s.per_bron[b];
      }).join(', '));
    }
    return delen.join(' · ');
  }

  function itemblok(item, metKiezer) {
    var meting = dossier.metingen[item.id];
    var verdict = meting ? meting.verdict : 'geen_bewijs';
    var blok = maak('div', null, {
      class: 'item', 'data-item': item.id, 'data-soort': item.soort, 'data-verdict': verdict
    });
    var kop = maak('h3');
    kop.appendChild(maak('span', item.id + ' ' + item.label));
    kop.appendChild(maak('span', ' '));
    kop.appendChild(maak('span', item.soort, {
      class: 'vlag s-' + item.soort, title: REGELS.soorten[item.soort]
    }));
    blok.appendChild(kop);
    blok.appendChild(maak('p', 'Doel: ' + item.doel, { class: 'doel' }));
    blok.appendChild(maak('p', item.regel.uitleg, { class: 'bronregel' }));
    if (metKiezer) {
      blok.appendChild(item.bron === 'document' ? documentkiezer(item) : kiezer(item));
    }

    var uitkomst = maak('div', null, { class: 'uitkomst' });
    uitkomst.appendChild(vlag(verdict));
    uitkomst.appendChild(maak('span', meting ? samenvattingTekst(item.id, meting) : '',
      { class: 'samenvatting' }));
    var bestandregel = '';
    if (meting) {
      bestandregel = meting.bestand + ' · sha256 ' + String(meting.sha256 || '').slice(0, 12) +
        ' · gemeten ' + meting.gemeten +
        (meting.artefact_datum ? ' · artefact ' + String(meting.artefact_datum).slice(0, 10) : '');
    }
    uitkomst.appendChild(maak('span', bestandregel, { class: 'bestand' }));
    blok.appendChild(uitkomst);

    var bewijs = maak('div', null, { class: 'bewijs' });
    if (meting && ((meting.fouten || []).length || (meting.voorbeeld || []).length)) {
      var details = maak('details');
      details.appendChild(maak('summary', 'Wat is er gelezen?'));
      var lijst = maak('ul');
      (meting.fouten || []).forEach(function (f) { lijst.appendChild(maak('li', f)); });
      (meting.voorbeeld || []).forEach(function (v) { lijst.appendChild(maak('li', v)); });
      details.appendChild(lijst);
      bewijs.appendChild(details);
    }
    blok.appendChild(bewijs);

    var notitie = maak('textarea', meting ? meting.notitie || '' : '', {
      'data-notitie': item.id, rows: '1', placeholder: 'Notitie (gaat mee in de uitdraai)',
      class: 'nietprint'
    });
    notitie.addEventListener('input', function () {
      if (!dossier.metingen[item.id]) return;
      dossier.metingen[item.id].notitie = notitie.value;
      bewaarLokaal();
    });
    blok.appendChild(notitie);
    return blok;
  }

  function tekenItems() {
    var doel = leegMaken(el('items-inhoud'));
    var filterVerdict = el('filter-verdict').value;
    var filterSoort = el('filter-soort').value;
    var filterWie = el('filter-wie').value;
    var zichtbaar = 0;

    REGELS.categorieen.forEach(function (categorie) {
      var eigen = REGELS.items.filter(function (item) {
        if (item.categorie !== categorie.nummer) return false;
        if (filterSoort && item.soort !== filterSoort) return false;
        if (filterWie && wieVan(item) !== filterWie) return false;
        if (filterVerdict && reken.verdict_van(dossier, item.id) !== filterVerdict) return false;
        return true;
      });
      if (!eigen.length) return;
      var kaart = maak('div', null, { class: 'kaart', 'data-categorie': categorie.nummer });
      kaart.appendChild(maak('h2', categorie.nummer + ' · ' + categorie.titel));
      var gezien = {};
      eigen.forEach(function (item) {
        var sleutel = item.bron === 'document' ? 'document-' + item.id : item.bron;
        var eerste = !gezien[sleutel];
        gezien[sleutel] = true;
        kaart.appendChild(itemblok(item, eerste));
        zichtbaar += 1;
      });
      doel.appendChild(kaart);
    });
    el('teller-items').textContent = zichtbaar + ' van ' + REGELS.items.length +
      ' meetregels zichtbaar';
    knoppenBij();
  }

  function knoppenBij() {
    var uit = !magMeten();
    var invoer = document.querySelectorAll('#items-inhoud input, #items-inhoud button, ' +
      '#items-inhoud textarea');
    for (var i = 0; i < invoer.length; i++) invoer[i].disabled = uit;
  }

  // Scherm 2: de aanvalspaden

  var AFGELEID_LABEL = { yes: 'ja', no: 'nee', unknown: 'onbekend', geen_meting: 'geen meetregel' };

  function tekenPaden() {
    var doel = leegMaken(el('paden-inhoud'));
    var cps = reken.per_chokepoint(REGELS, PADEN, dossier);
    var stand = reken.dashboard(REGELS, PADEN, dossier);
    el('paden-samenvatting').textContent = stand.chokepoints.gemeten + ' van de ' +
      stand.chokepoints.totaal + ' chokepoints gemeten; ' + stand.chokepoints.witte_vlekken +
      ' witte vlekken (daar zegt geen enkele export iets over).';
    PADEN.bladeren.forEach(function (blad) {
      var kaart = maak('div', null, { class: 'kaart', 'data-pad': blad.id });
      kaart.appendChild(maak('h2', blad.id + ' · ' + blad.titel));
      if (blad.type !== 'pad') {
        kaart.appendChild(maak('p', 'Impact, geen pad: hier meet dit instrument niet aan.',
          { class: 'klein' }));
      }
      var rijen = (blad.chokepoints || []).map(function (cp) {
        var gegevens = cps[cp.id];
        var metingcel = maak('span');
        if (!gegevens.items.length) {
          metingcel.appendChild(maak('span', 'geen meetregel · aanleveren: ' + cp.bewijs));
        } else {
          gegevens.items.forEach(function (meting, index) {
            if (index) metingcel.appendChild(maak('span', ' '));
            metingcel.appendChild(maak('span', meting.id + ' ', { class: 'klein' }));
            metingcel.appendChild(vlag(meting.verdict));
          });
        }
        var tr = rij([cp.id, cp.titel, cp.drp, metingcel,
          AFGELEID_LABEL[gegevens.afgeleid] || gegevens.afgeleid]);
        tr.setAttribute('data-chokepoint', cp.id);
        tr.cells[1].className = 'titel';
        tr.cells[4].className = 'afgeleid';
        if (!gegevens.items.length) tr.className = 'witte-vlek';
        return tr;
      });
      var houder = maak('div', null, { class: 'rol', tabindex: '0' });
      var tabelknoop = maak('table', null, { class: 'regels' });
      tabel(tabelknoop, ['Chokepoint', 'Wat het is', 'DRP', 'Meting', 'Afgeleid antwoord'], rijen);
      houder.appendChild(tabelknoop);
      kaart.appendChild(houder);
      doel.appendChild(kaart);
    });
  }

  // Scherm 3: de Linux-hosts

  function tekenHosts() {
    var analyse = dossier.iamscan;
    var routesKaart = el('hosts-routes');
    var bevindingenKaart = el('hosts-bevindingen');
    var matrixKaart = el('hosts-matrix');
    if (!analyse) {
      el('hosts-samenvatting').textContent = 'Nog geen dump geladen. Kies bij meetregel 10.1 een ' +
        'tar.gz of een uitgepakte map.';
      routesKaart.hidden = true;
      bevindingenKaart.hidden = true;
      matrixKaart.hidden = true;
      return;
    }
    el('hosts-samenvatting').textContent = analyse.hosts.length + ' hosts (' +
      analyse.hosts.join(', ') + ') · ' + analyse.routes.length + ' routes naar root · ' +
      ERNST.map(function (e) { return analyse.telling[e] + ' ' + e; }).join(', ') + '.';
    routesKaart.hidden = false;
    bevindingenKaart.hidden = false;
    matrixKaart.hidden = false;
    tabel(el('tabel-routes'), ['Host', 'Principal', 'Route', 'Via', 'Zonder wachtwoord'],
      analyse.routes.map(function (route) {
        var tr = rij([route.host, route.principal, route.route, route.via,
          route.nopasswd ? 'ja' : 'nee']);
        tr.setAttribute('data-route', route.host + '|' + route.principal + '|' + route.via);
        return tr;
      }));
    tabel(el('tabel-bevindingen'), ['Ernst', 'Host', 'Controle', 'Bevinding', 'Bewijs'],
      analyse.bevindingen.map(function (bevinding) {
        var ernst = maak('span', bevinding.ernst, { class: 'vlag e-' + bevinding.ernst });
        var titel = maak('span');
        titel.appendChild(maak('strong', bevinding.titel));
        titel.appendChild(maak('br'));
        titel.appendChild(maak('span', bevinding.detail, { class: 'klein' }));
        var tr = rij([ernst, bevinding.host, bevinding.check, titel, bevinding.bewijs]);
        tr.setAttribute('data-bevinding', bevinding.host + '|' + bevinding.check);
        return tr;
      }));
    tekenMatrix(analyse);
  }

  function tekenMatrix(analyse) {
    var doel = leegMaken(el('matrix-root'));
    var principals = uniekGesorteerd(analyse.routes.map(function (r) { return r.principal; }));
    if (!principals.length) {
      doel.appendChild(maak('p', 'Geen enkele route naar root gevonden in deze dump.',
        { class: 'klein' }));
      return;
    }
    var rijen = principals.map(function (principal) {
      var cellen = [principal].concat(analyse.hosts.map(function (host) {
        var route = analyse.routes.filter(function (r) {
          return r.host === host && r.principal === principal;
        })[0];
        return route ? route.via : '';
      }));
      var tr = rij(cellen);
      tr.setAttribute('data-principal', principal);
      return tr;
    });
    var tabelknoop = maak('table', null, { class: 'regels' });
    tabel(tabelknoop, ['Principal'].concat(analyse.hosts), rijen);
    doel.appendChild(tabelknoop);
  }

  // Scherm 4: het dashboard

  function cel(getal, naam, sleutel) {
    var knoop = maak('div', null, { class: 'cel' });
    knoop.appendChild(maak('span', getal, { class: 'getal', 'data-teller': sleutel }));
    knoop.appendChild(maak('span', naam, { class: 'naam' }));
    return knoop;
  }

  function tekenDashboard() {
    var doel = leegMaken(el('dashboard-inhoud'));
    var stand = reken.dashboard(REGELS, PADEN, dossier);

    var eerste = maak('div', null, { class: 'tellerraster' });
    eerste.appendChild(cel(stand.items.gemeten, 'meetregels gemeten', 'items.gemeten'));
    eerste.appendChild(cel(stand.items.totaal, 'meetregels totaal', 'items.totaal'));
    eerste.appendChild(cel(stand.chokepoints.gemeten, 'chokepoints geraakt', 'chokepoints.gemeten'));
    eerste.appendChild(cel(stand.chokepoints.totaal, 'chokepoints totaal', 'chokepoints.totaal'));
    eerste.appendChild(cel(stand.chokepoints.witte_vlekken, 'witte vlekken',
      'chokepoints.witte_vlekken'));
    doel.appendChild(eerste);

    var uitkomsten = maak('div', null, { class: 'tellerraster' });
    VERDICTS.forEach(function (v) {
      uitkomsten.appendChild(cel(stand.verdict[v], VERDICT_LABEL[v], 'verdict.' + v));
    });
    doel.appendChild(uitkomsten);

    var soorten = maak('div', null, { class: 'tellerraster' });
    ['A', 'B', 'C', 'D'].forEach(function (s) {
      soorten.appendChild(cel(stand.soort[s], 'bewijssoort ' + s, 'soort.' + s));
    });
    doel.appendChild(soorten);

    var kaart = maak('div', null, { class: 'kaart' });
    kaart.appendChild(maak('h2', 'Per categorie'));
    var houder = maak('div', null, { class: 'rol', tabindex: '0' });
    var tabelknoop = maak('table', null, { class: 'regels' });
    tabel(tabelknoop, ['Categorie'].concat(VERDICTS.map(function (v) { return VERDICT_LABEL[v]; })),
      REGELS.categorieen.map(function (categorie) {
        var nummer = String(categorie.nummer);
        var tr = rij([nummer + ' · ' + categorie.titel].concat(VERDICTS.map(function (v) {
          return stand.categorie[nummer][v];
        })));
        VERDICTS.forEach(function (v, index) {
          tr.cells[index + 1].setAttribute('data-teller', 'categorie.' + nummer + '.' + v);
        });
        return tr;
      }));
    houder.appendChild(tabelknoop);
    kaart.appendChild(houder);
    doel.appendChild(kaart);
  }

  // Scherm 5: de uitdraai

  function uitdraaiTabel(kop, koppen, rijen) {
    var stuk = document.createDocumentFragment();
    stuk.appendChild(maak('h2', kop));
    if (!rijen.length) {
      stuk.appendChild(maak('p', 'Niets vastgelegd.', { class: 'leeg' }));
      return stuk;
    }
    var tabelknoop = maak('table');
    tabel(tabelknoop, koppen, rijen);
    stuk.appendChild(tabelknoop);
    return stuk;
  }

  function tekenUitdraai() {
    var doel = leegMaken(el('uitdraai-inhoud'));
    var organisatie = dossier.organisatie || {};
    var stand = reken.dashboard(REGELS, PADEN, dossier);

    doel.appendChild(maak('h2', '1 Organisatie en peildatum'));
    doel.appendChild(maak('p', (organisatie.naam || 'Organisatie niet ingevuld') + ' · peildatum ' +
      (organisatie.peildatum || 'niet ingevuld') + ' · uitdraai gemaakt op ' + vandaag()));

    doel.appendChild(uitdraaiTabel('2 Dashboard', ['Teller', 'Waarde'], [
      rij(['Meetregels gemeten', stand.items.gemeten + ' van ' + stand.items.totaal]),
      rij(['Chokepoints geraakt', stand.chokepoints.gemeten + ' van ' + stand.chokepoints.totaal]),
      rij(['Witte vlekken', stand.chokepoints.witte_vlekken])
    ].concat(VERDICTS.map(function (v) { return rij([VERDICT_LABEL[v], stand.verdict[v]]); }))));

    var cps = reken.per_chokepoint(REGELS, PADEN, dossier);
    var padrijen = [];
    PADEN.bladeren.forEach(function (blad) {
      (blad.chokepoints || []).forEach(function (cp) {
        var gegevens = cps[cp.id];
        padrijen.push(rij([blad.id, cp.id, cp.titel,
          gegevens.items.length
            ? gegevens.items.map(function (m) { return m.id + ': ' + m.verdict; }).join(', ')
            : 'geen meetregel · aanleveren: ' + cp.bewijs,
          AFGELEID_LABEL[gegevens.afgeleid] || gegevens.afgeleid]));
      });
    });
    doel.appendChild(uitdraaiTabel('3 Bewijs per aanvalspad',
      ['Pad', 'Chokepoint', 'Wat het is', 'Meting', 'Afgeleid antwoord'], padrijen));

    doel.appendChild(uitdraaiTabel('4 Per meetregel',
      ['Item', 'Label', 'Bron', 'Wie levert het', 'Bestand', 'sha256', 'Artefact', 'Uitkomst',
        'Samenvatting', 'Notitie'],
      REGELS.items.map(function (item) {
        var meting = dossier.metingen[item.id];
        return rij([item.id, item.label, item.bron, WIE_LABEL[wieVan(item)] || '',
          meting ? meting.bestand : '',
          meting ? String(meting.sha256 || '').slice(0, 12) : '',
          meting && meting.artefact_datum ? String(meting.artefact_datum).slice(0, 10) : '',
          meting ? meting.verdict : 'geen_bewijs',
          meting ? samenvattingTekst(item.id, meting) : '',
          meting && meting.herkomst_ai
            ? 'omgezet met AI (' + meting.herkomst_ai.leverancier + ', ' + meting.herkomst_ai.model +
              ', ' + meting.herkomst_ai.gemaakt + '); ' + (meting.notitie || '')
            : (meting ? meting.notitie || '' : '')]);
      })));

    if (dossier.iamscan) {
      doel.appendChild(uitdraaiTabel('5 Linux-hosts',
        ['Ernst', 'Host', 'Controle', 'Bevinding', 'Bewijs'],
        dossier.iamscan.bevindingen.map(function (b) {
          return rij([b.ernst, b.host, b.check, b.titel, b.bewijs]);
        })));
    } else {
      doel.appendChild(maak('h2', '5 Linux-hosts'));
      doel.appendChild(maak('p', 'Geen dump gemeten.', { class: 'leeg' }));
    }

    doel.appendChild(uitdraaiTabel('6 Niet uit data te halen',
      ['Pad', 'Chokepoint', 'Wat het is', 'Wat je zou moeten aanleveren'],
      reken.witte_vlekken(REGELS, PADEN).map(function (vlek) {
        return rij([vlek.pad, vlek.chokepoint, vlek.titel, vlek.bewijs]);
      })));

    doel.appendChild(maak('h2', '7 Verantwoording'));
    var verantwoording = maak('ul');
    [['Meetregels', REGELS.versie],
      ['Vingerafdruk meetregels', BRON.vingerafdruk],
      ['Aanvalspaden', PADEN.versie],
      ['Dossier bijgewerkt', dossier.bijgewerkt || 'nog niet opgeslagen'],
      ['Rekenwijze', 'Alle termijnen rekenen vanaf de peildatum. Wat hier voldoet heet, betekent ' +
        'dat de export aan de regel voldoet, niet dat de maatregel deugt.']].forEach(function (paar) {
      var punt = maak('li');
      punt.appendChild(maak('strong', paar[0] + ': '));
      punt.appendChild(maak('span', paar[1]));
      verantwoording.appendChild(punt);
    });
    doel.appendChild(verantwoording);
  }

  // Tabs, dossierknoppen en start

  function werkBij() {
    status();
    tekenItems();
    tekenPaden();
    tekenHosts();
    tekenDashboard();
    tekenUitdraai();
  }

  function naarScherm(schermId) {
    var knoppen = document.querySelectorAll('.tabs button');
    for (var i = 0; i < knoppen.length; i++) {
      var actief = knoppen[i].getAttribute('data-scherm') === schermId;
      knoppen[i].setAttribute('aria-selected', actief ? 'true' : 'false');
      el(knoppen[i].getAttribute('data-scherm')).hidden = !actief;
    }
  }

  function download(naam, inhoud) {
    var blob = new Blob([inhoud], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var koppeling = maak('a', null, { href: url, download: naam });
    document.body.appendChild(koppeling);
    koppeling.click();
    document.body.removeChild(koppeling);
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  }

  function laadDossier(data) {
    if (!data || data.formaat !== 'meting-dossier' || data.versie !== 1) {
      meld('Dit is geen meting-dossier (versie 1); er is niets geladen.', true);
      return false;
    }
    dossier = data;
    dossier.metingen = dossier.metingen || {};
    dossier.documenten = dossier.documenten || {};
    dossier.organisatie = dossier.organisatie || { naam: '', peildatum: '' };
    documentTeksten = {};
    bronmeldingen = {};
    el('org-naam').value = dossier.organisatie.naam || '';
    el('org-peildatum').value = dossier.organisatie.peildatum || '';
    bewaarLokaal();
    statusMelding = null;
    statusLetOp = false;
    werkBij();
    if (data.regels_sha256 && data.regels_sha256 !== BRON.vingerafdruk) {
      meld('Dit dossier is gemaakt met een andere versie van de meetregels (' +
        String(data.regels_sha256).slice(0, 12) + ' tegen ' + BRON.vingerafdruk.slice(0, 12) +
        '); het is geladen, maar toets je exports opnieuw.', true);
    }
    return true;
  }

  function start() {
    el('versie').textContent = 'meetregels ' + REGELS.versie + ' · aanvalspaden ' + PADEN.versie +
      ' · vingerafdruk ' + BRON.vingerafdruk.slice(0, 12);
    dossier = leesLokaal() || reken.nieuw_dossier(REGELS, PADEN, '');
    dossier.metingen = dossier.metingen || {};
    dossier.documenten = dossier.documenten || {};
    dossier.organisatie = dossier.organisatie || { naam: '', peildatum: '' };

    el('org-naam').value = dossier.organisatie.naam || '';
    el('org-peildatum').value = dossier.organisatie.peildatum || '';
    ['input', 'change'].forEach(function (gebeurtenis) {
      el('org-naam').addEventListener(gebeurtenis, function () {
        dossier.organisatie.naam = el('org-naam').value;
        bewaarLokaal();
      });
    });
    el('org-peildatum').addEventListener('change', function () {
      var oud = dossier.organisatie.peildatum;
      if (el('org-peildatum').value === oud) return;   // fill en change vuren allebei
      dossier.organisatie.peildatum = el('org-peildatum').value;
      bewaarLokaal();
      statusMelding = null;
      statusLetOp = false;
      werkBij();
      if (oud && oud !== dossier.organisatie.peildatum && Object.keys(dossier.metingen).length) {
        meld('De peildatum is gewijzigd. De uitkomsten hieronder zijn nog met ' + oud +
          ' berekend; kies je bestanden opnieuw om ze op de nieuwe peildatum te toetsen.', true);
      }
    });

    el('filter-verdict').addEventListener('change', tekenItems);
    el('filter-soort').addEventListener('change', tekenItems);
    el('filter-wie').addEventListener('change', tekenItems);

    var tabknoppen = document.querySelectorAll('.tabs button');
    for (var i = 0; i < tabknoppen.length; i++) {
      (function (knop) {
        knop.addEventListener('click', function () { naarScherm(knop.getAttribute('data-scherm')); });
      })(tabknoppen[i]);
    }

    el('knop-opslaan').addEventListener('click', function () {
      bewaarLokaal();
      download(reken.bestandsnaam(dossier, vandaag()), JSON.stringify(dossier, null, 1));
    });
    el('knop-laden').addEventListener('click', function () { el('bestand-laden').click(); });
    el('bestand-laden').addEventListener('change', function () {
      var bestand = el('bestand-laden').files[0];
      if (!bestand) return;
      bestand.text().then(function (tekst) {
        try {
          laadDossier(JSON.parse(tekst));
        } catch (fout) {
          meld('Dit bestand is geen leesbare JSON; er is niets geladen.', true);
        }
      });
    });
    el('knop-zelfcheck-export').addEventListener('click', function () {
      var uit = reken.zelfcheck_export(REGELS, PADEN, dossier, vandaag());
      var aantal = Object.keys(uit.antwoorden).length;
      if (!aantal) {
        meld('Nog geen afgeleide antwoorden: meet eerst iets, dan valt er wat te exporteren.', true);
        return;
      }
      download('zelfcheck-antwoorden-uit-meting-' + vandaag() + '.json',
        JSON.stringify(uit, null, 1));
      meld(aantal + ' afgeleide antwoorden geëxporteerd; laad dit bestand in de zelfcheck.', false);
    });
    el('knop-voorstel-laden').addEventListener('click', function () { el('bestand-voorstel').click(); });
    el('bestand-voorstel').addEventListener('change', function () {
      var bestand = el('bestand-voorstel').files[0];
      if (!bestand) return;
      bestand.text().then(function (tekst) {
        try {
          var data = JSON.parse(tekst);
          // De invoertekst zit niet in het voorstel (alleen de sha256); zonder die tekst kan de
          // citaatcontrole hier niets zeggen. Dat is geen fout, wel iets om te melden.
          laadVoorstel(data);
        } catch (fout) {
          meld('Dit bestand is geen leesbare JSON.', true);
        }
      });
      el('bestand-voorstel').value = '';
    });
    el('knop-voorstel-overnemen').addEventListener('click', neemVoorstelOver);
    el('knop-voorstel-sluiten').addEventListener('click', function () {
      voorstel = null;
      el('voorstel-blok').hidden = true;
    });
    el('knop-afdrukken').addEventListener('click', function () {
      naarScherm('scherm-uitdraai');
      window.print();
    });
    el('knop-wissen').addEventListener('click', function () {
      if (!window.confirm('Alle metingen wissen? Het dossier in deze browser verdwijnt; de ' +
        'peildatum blijft staan.')) return;
      var peil = peildatum();
      dossier = reken.nieuw_dossier(REGELS, PADEN, peil);
      dossier.organisatie.naam = el('org-naam').value;
      documentTeksten = {};
      bronmeldingen = {};
      statusMelding = null;
      statusLetOp = false;
      bewaarLokaal();
      werkBij();
    });

    naarScherm('scherm-items');
    werkBij();
  }

  // De rekenkant staat ook op window, zodat een test hem naast reken.py kan leggen.
  window.reken = reken;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
}());
