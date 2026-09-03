/* De zelfcheck. Alle inhoud en alle regels komen uit BRON (paden.json); deze code bevat geen
   eigen lijst met vragen, paden of drempels. Wijzigt de bron, dan wijzigt de app mee.

   De beoordeling is een letterlijke tegenhanger van tools/score.py. Een test vergelijkt beide op
   dezelfde antwoorden, en op een echte doorloop van de zelfcheck waar de bron uit komt. */
(function () {
  "use strict";

  var BRON = window.__BRON__;
  var OPSLAG = "aanvalspaden-zelfcheck-v1";
  var ONBEKEND = "unknown";

  /* ---------- staat ---------- */

  var staat = { antwoorden: {}, notities: {}, scherm: "start", onderdeel: 0 };

  function bewaar() {
    try {
      localStorage.setItem(OPSLAG, JSON.stringify({
        versie: BRON.versie, antwoorden: staat.antwoorden, notities: staat.notities
      }));
    } catch (e) { /* privevenster of geblokkeerde opslag: de check werkt gewoon door */ }
  }

  function laad() {
    try {
      var rauw = localStorage.getItem(OPSLAG);
      if (!rauw) return;
      var d = JSON.parse(rauw);
      staat.antwoorden = d.antwoorden || {};
      staat.notities = d.notities || {};
    } catch (e) { staat.antwoorden = {}; staat.notities = {}; }
  }

  function wis() {
    staat.antwoorden = {}; staat.notities = {};
    try { localStorage.removeItem(OPSLAG); } catch (e) {}
  }

  /* ---------- antwoorden uit de meting ---------- */

  /* De meting (aanvalspaden/meting) exporteert afgeleide antwoorden met bewijs erbij. Die vullen
     alleen de gaten: een antwoord dat de mens zelf gaf blijft staan, want de check blijft van de mens. */

  var metingMelding = null;

  function neemMetingOver(tekst) {
    var data = null;
    try { data = JSON.parse(tekst); } catch (e) { data = null; }
    if (!data || data.formaat !== "zelfcheck-antwoorden") {
      metingMelding = { fout: true, tekst: "Dit is geen exportbestand van de meting. Verwacht een " +
        "bestand met formaat zelfcheck-antwoorden." };
      teken();
      return;
    }
    var antwoorden = data.antwoorden || {};
    var herkomst = data.herkomst || {};
    var datum = data.gemaakt || "onbekende datum";
    var over = 0, gehouden = 0, zonder = 0;
    Object.keys(antwoorden).forEach(function (vid) {
      if (!VRAGEN[vid]) return;
      var waarde = antwoorden[vid];
      if (!waarde || waarde === ONBEKEND) { zonder++; return; }
      var nu = staat.antwoorden[vid];
      if (nu && nu !== ONBEKEND) { gehouden++; return; }
      staat.antwoorden[vid] = waarde;
      var items = ((herkomst[vid] || {}).items || []).join(", ");
      staat.notities[vid] = "uit meting " + datum + (items ? ": " + items : "");
      over++;
    });
    bewaar();
    metingMelding = { fout: false, tekst: over + (over === 1 ? " antwoord" : " antwoorden") +
      " overgenomen, " + gehouden + " overgeslagen (al ingevuld), " + zonder +
      " zonder meetbaar bewijs. Je eigen antwoorden zijn niet overschreven." };
    teken();
  }

  /* ---------- de vragen, afgeleid uit de bron ---------- */

  var VRAGEN = (function () {
    var uit = {};
    BRON.bladeren.forEach(function (blad) {
      blad.chokepoints.forEach(function (cp) {
        if (!uit[cp.vraag_id]) {
          uit[cp.vraag_id] = {
            id: cp.vraag_id, onderdeel: cp.onderdeel, titel: cp.titel, vraag: cp.vraag,
            letter: cp.drp[0], bewijs: cp.bewijs,
            negatief: !!cp.negatief, opties: cp.opties || null, alleen_als: cp.alleen_als || null,
            paden: []
          };
        }
        uit[cp.vraag_id].paden.push(blad.id);
      });
    });
    (BRON.randvoorwaarden || []).forEach(function (rv) {
      if (!uit[rv.vraag_id]) {
        uit[rv.vraag_id] = {
          id: rv.vraag_id, onderdeel: rv.onderdeel, titel: rv.titel, vraag: rv.vraag,
          letter: "R", bewijs: "", negatief: false, opties: null, alleen_als: null,
          paden: [], randvoorwaarde: true, werking: rv.werking
        };
      }
    });
    return uit;
  })();

  var BLAD = {};
  BRON.bladeren.forEach(function (b) { BLAD[b.id] = b; });

  var STATUS = {};
  BRON.regels.statussen.forEach(function (s) { STATUS[s.id] = s; });
  var VOLGORDE = BRON.regels.statussen.map(function (s) { return s.id; });

  function zichtbaar(vraag) {
    return !vraag.alleen_als || staat.antwoorden[vraag.alleen_als] !== "no";
  }

  function vragenVan(onderdeel) {
    return onderdeel.vragen.map(function (id) { return VRAGEN[id]; }).filter(Boolean).filter(zichtbaar);
  }

  function beantwoord() {
    var n = 0, t = 0;
    BRON.onderdelen.forEach(function (o) {
      vragenVan(o).forEach(function (v) { t++; if (staat.antwoorden[v.id]) n++; });
    });
    return { gedaan: n, totaal: t };
  }

  /* ---------- de beoordeling (tegenhanger van tools/score.py) ---------- */

  function antwoordVan(vid) {
    var a = staat.antwoorden[vid] || ONBEKEND;
    var v = VRAGEN[vid];
    if (v && v.negatief) { return a === "yes" ? "no" : a === "no" ? "yes" : a; }
    return a;
  }

  function isJa(vid) {
    var v = VRAGEN[vid];
    if (v && v.opties) {
      return BRON.regels.uitzonderingen.AP05.model_telt_als_ja.indexOf(staat.antwoorden[vid]) !== -1;
    }
    return BRON.regels.telt_als_ja.indexOf(antwoordVan(vid)) !== -1;
  }

  function isOnbekend(vid) { return antwoordVan(vid) === ONBEKEND; }

  function ap05(ontbrekend, concreet) {
    var model = staat.antwoorden.model;
    if (!model || model === ONBEKEND) return "unknown";
    if (model === "permanent" || model === "separate" || staat.antwoorden.jit === "no") return "open";
    var sterkModel = model === "dedicated" || model === "hardened";
    if (sterkModel && !ontbrekend.length) return "strong";
    if (!concreet) return "unknown";
    if (sterkModel && ["adminhard", "jit", "elevation"].every(isJa)) return "limited";
    if (isJa("jit") && ["elevation", "adminhard"].some(function (v) { return !isJa(v) && !isOnbekend(v); })) {
      return "reactive";
    }
    return "open";
  }

  function herstel() {
    var a = staat.antwoorden;
    if (a.backup === "no") return "open";
    if (["backup", "restore", "crisis"].every(function (v) { return a[v] === "yes"; })) return "strong";
    if (a.backup === "yes" && a.restore === "yes") return "limited";
    if (["backup", "restore"].some(function (v) { return !a[v] || a[v] === ONBEKEND; })) return "unknown";
    return "open";
  }

  function beoordeel() {
    var uit = {};
    BRON.bladeren.forEach(function (blad) {
      var r = blad.regels;
      var ontbrekend = r.vereist.filter(function (v) { return !isJa(v); });
      var concreet = ontbrekend.some(function (v) { return !isOnbekend(v); });
      var reactiefAanwezig = r.reactief.filter(isJa);
      var status;
      if (!ontbrekend.length) { status = r.plafond || "strong"; }
      else if (!concreet) { status = "unknown"; }
      else if (r.beperkt.length && r.beperkt.every(isJa)) { status = "limited"; }
      else if (reactiefAanwezig.length && isJa(BRON.regels.randvoorwaarde)) { status = "reactive"; }
      else { status = "open"; }
      if (blad.id === "AP05") { status = ap05(ontbrekend, concreet); }
      uit[blad.id] = { status: status, ontbrekend: ontbrekend, reactief_aanwezig: reactiefAanwezig };
    });

    var ap17 = BRON.regels.uitzonderingen.AP17;
    var statussen = ap17.toegangspaden.map(function (p) { return uit[p].status; });
    var slechtste = VOLGORDE.filter(function (s) { return statussen.indexOf(s) !== -1; })[0];
    var h = herstel();
    var gezien = [];
    uit.AP17.ontbrekend.concat(ap17.toegangspaden.reduce(function (acc, p) {
      return acc.concat(uit[p].ontbrekend);
    }, [])).forEach(function (v) { if (gezien.indexOf(v) === -1) gezien.push(v); });
    uit.AP17.status = VOLGORDE[Math.min(VOLGORDE.indexOf(slechtste), VOLGORDE.indexOf(h))];
    uit.AP17.ontbrekend = gezien;
    uit.AP17.toegang = slechtste;
    uit.AP17.herstel = h;
    return uit;
  }

  function acties(uitslag) {
    var r = BRON.regels.acties;
    var kandidaten = [];
    Object.keys(VRAGEN).forEach(function (vid) {
      var v = VRAGEN[vid];
      var nietJa = v.opties
        ? BRON.regels.uitzonderingen.AP05.model_telt_als_ja.indexOf(staat.antwoorden[vid]) === -1
        : antwoordVan(vid) !== "yes";
      if (!nietJa) return;
      if (v.alleen_als && staat.antwoorden[v.alleen_als] === "no") return;
      var helpt = Object.keys(uitslag).filter(function (p) {
        return uitslag[p].ontbrekend.indexOf(vid) !== -1 && uitslag[p].status !== "strong";
      });
      var gewicht = helpt.reduce(function (som, p) { return som + r.gewicht[uitslag[p].status]; }, 0);
      if (v.letter === "P") { gewicht *= r.factor_preventief; }
      if (gewicht > 0) {
        kandidaten.push({ vraag_id: vid, vraag: v, gewicht: gewicht, helpt: helpt,
                          verifieer: antwoordVan(vid) === ONBEKEND });
      }
    });
    kandidaten.sort(function (a, b) { return b.gewicht - a.gewicht; });
    return kandidaten.slice(0, r.aantal);
  }

  /* ---------- opbouw van het scherm ---------- */

  var app = document.getElementById("app");

  function el(tag, attrs, kinderen) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "tekst") { e.textContent = attrs[k]; }
      else if (k.slice(0, 2) === "on") { e.addEventListener(k.slice(2), attrs[k]); }
      else { e.setAttribute(k, attrs[k]); }
    });
    (kinderen || []).forEach(function (k) { if (k) e.appendChild(k); });
    return e;
  }

  function ga(scherm, onderdeel) {
    staat.scherm = scherm;
    if (typeof onderdeel === "number") staat.onderdeel = onderdeel;
    teken();
    window.scrollTo(0, 0);
  }

  function statusVlag(id) {
    return el("span", { class: "vlag " + id }, [
      el("b", { "aria-hidden": "true", tekst: { strong: "✓", limited: "◐", reactive: "↻", open: "!", unknown: "?" }[id] }),
      el("span", { tekst: STATUS[id].label })
    ]);
  }

  function startScherm() {
    var voortgang = beantwoord();
    return el("section", { class: "kaart intro" }, [
      el("p", { class: "label", tekst: "VAN DREIGING NAAR ACTIE" }),
      el("h1", { tekst: "Welke aanvalspaden staan bij jullie open?" }),
      el("p", { class: "lead", tekst: "Achttien realistische aanvalsroutes, van een gestolen wachtwoord " +
        "tot een leveranciersincident. Je beantwoordt per route wat er technisch is afgedwongen, en ziet " +
        "waar een aanvaller nog ruimte heeft." }),
      el("p", { tekst: "Ongeveer " + voortgang.totaal + " vragen in " + BRON.onderdelen.length +
                       " onderdelen, samen goed voor " + BRON.bladeren.length +
                       " aanvalspaden. Weet je iets niet? Onbekend is een bruikbaar antwoord." }),
      el("div", { class: "knoppen" }, [
        el("button", { class: "primair", tekst: voortgang.gedaan ? "Verder met je check" : "Start de check",
                       onclick: function () { ga("vragen", 0); } }),
        el("button", { id: "knop-meting-laden", tekst: "Antwoorden uit meting laden",
                       onclick: function () {
                         var invoer = document.getElementById("bestand-meting");
                         if (invoer) invoer.click();
                       } }),
        el("a", { href: "#beoordeling", tekst: "Hoe werkt de beoordeling?" })
      ]),
      metingMelding ? el("p", { id: "meting-status", role: "status",
        class: "melding" + (metingMelding.fout ? " fout" : ""), tekst: metingMelding.tekst }) : null,
      voortgang.gedaan ? el("p", { class: "voortgang",
        tekst: voortgang.gedaan + " van de " + voortgang.totaal + " vragen beantwoord." }) : null,
      el("p", { class: "privacy", tekst: "Je antwoorden blijven in de opslag van deze browser. Er is geen " +
        "account, geen server en geen telemetrie: er wordt niets verstuurd." })
    ]);
  }

  function vraagBlok(v) {
    var opties = v.opties || BRON.regels.antwoorden;
    var gekozen = staat.antwoorden[v.id];
    var groep = el("div", { class: "vraag", id: "vraag-" + v.id, "data-vraag": v.id });
    groep.appendChild(el("h3", { tekst: v.vraag.claim }));
    if (v.vraag.toelichting) groep.appendChild(el("p", { class: "uitleg", tekst: v.vraag.toelichting }));
    if (v.vraag.telt_niet) {
      groep.appendChild(el("p", { class: "telt-niet" }, [
        el("strong", { tekst: "Telt niet mee: " }), el("span", { tekst: v.vraag.telt_niet })
      ]));
    }
    if (v.negatief) {
      // Omgekeerd geformuleerde vraag: zonder dit zetje leest een gebruiker ja als iets goeds.
      groep.appendChild(el("p", { class: "omgekeerd",
        tekst: "Let op: bij deze vraag is ja het ongunstige antwoord." }));
    }
    var rij = el("div", { class: "opties", role: "radiogroup", "aria-label": v.vraag.claim });
    opties.forEach(function (o) {
      var knop = el("button", {
        type: "button", class: "optie" + (gekozen === o.id ? " gekozen" : ""),
        role: "radio", "aria-checked": gekozen === o.id ? "true" : "false",
        "data-antwoord": o.id,
        onclick: function () { staat.antwoorden[v.id] = o.id; bewaar(); teken(); }
      }, [el("b", { tekst: o.label }), el("span", { tekst: o.uitleg })]);
      rij.appendChild(knop);
    });
    groep.appendChild(rij);
    if (staat.notities[v.id]) {
      groep.appendChild(el("p", { class: "notitie", tekst: staat.notities[v.id] }));
    }
    if (v.paden.length) {
      groep.appendChild(el("p", { class: "raakt", tekst: "Telt mee bij " + v.paden.length +
        (v.paden.length === 1 ? " aanvalspad" : " aanvalspaden") + ": " + v.paden.join(", ") }));
    } else if (v.werking) {
      groep.appendChild(el("p", { class: "raakt", tekst: v.werking }));
    }
    return groep;
  }

  function vragenScherm() {
    var onderdeel = BRON.onderdelen[staat.onderdeel];
    var vragen = vragenVan(onderdeel);
    var voortgang = beantwoord();
    var laatste = staat.onderdeel === BRON.onderdelen.length - 1;
    var open = vragen.filter(function (v) { return !staat.antwoorden[v.id]; }).length;

    var sectie = el("section", { class: "kaart" }, [
      el("p", { class: "label", tekst: "ONDERDEEL " + (staat.onderdeel + 1) + " VAN " + BRON.onderdelen.length }),
      el("h2", { tekst: onderdeel.titel }),
      el("progress", { class: "balk", max: String(voortgang.totaal), value: String(voortgang.gedaan),
                       "aria-label": "Voortgang" }),
      el("p", { class: "voortgang", tekst: voortgang.gedaan + " van de " + voortgang.totaal + " beantwoord" })
    ]);
    vragen.forEach(function (v) { sectie.appendChild(vraagBlok(v)); });
    sectie.appendChild(el("div", { class: "knoppen onder" }, [
      staat.onderdeel > 0 ? el("button", { tekst: "Vorige", onclick: function () { ga("vragen", staat.onderdeel - 1); } }) : null,
      el("button", {
        class: "primair",
        tekst: laatste ? "Naar het resultaat" : "Volgende onderdeel",
        onclick: function () { laatste ? ga("resultaat") : ga("vragen", staat.onderdeel + 1); }
      }),
      laatste ? null : el("button", { tekst: "Direct naar het resultaat", onclick: function () { ga("resultaat"); } })
    ]));
    if (open) {
      sectie.appendChild(el("p", { class: "voortgang", tekst: open + (open === 1 ? " vraag" : " vragen") +
        " in dit onderdeel nog onbeantwoord; die tellen als onbekend." }));
    }
    return sectie;
  }

  function padKaart(blad, uitslag) {
    var u = uitslag[blad.id];
    var kaart = el("article", { class: "pad", "data-pad": blad.id, "data-status": u.status }, [
      el("div", { class: "padkop" }, [
        el("h3", { tekst: blad.titel }),
        statusVlag(u.status)
      ]),
      el("p", { tekst: blad.scenario })
    ]);
    if (u.ontbrekend.length) {
      var lijst = el("ul", { class: "ontbreekt" });
      u.ontbrekend.forEach(function (vid) {
        var v = VRAGEN[vid];
        var a = antwoordVan(vid);
        var hoe = a === ONBEKEND ? "onbekend" : a === "partial" ? "gedeeltelijk" : "ontbreekt";
        lijst.appendChild(el("li", { tekst: (v ? v.vraag.actie : vid) + " (" + hoe + ")" }));
      });
      kaart.appendChild(el("p", { class: "kopje", tekst: "Ontbrekend, gedeeltelijk of onbekend" }));
      kaart.appendChild(lijst);
    }
    if (u.reactief_aanwezig && u.reactief_aanwezig.length) {
      kaart.appendChild(el("p", { class: "detectie", tekst: "Aanwezige detectie of response: " +
        u.reactief_aanwezig.map(function (vid) { return VRAGEN[vid] ? VRAGEN[vid].vraag.actie : vid; }).join(" ") }));
    }
    if (blad.nuance) kaart.appendChild(el("p", { class: "nuance", tekst: blad.nuance }));
    return kaart;
  }

  /* De uitslag zegt wat je moet doen en welk bewijs erbij hoort, maar niet hoe. Dat staat in de
     kennisbank, gekoppeld aan dezelfde barriere. Zonder deze links moet de lezer zelf zoeken, en dan
     is de kans groot dat hij het niet doet.

     Meer dan een handleiding mag: bij monitoring is de keuze tussen zelf doen, uitbesteden of een
     MDR-dienst juist het advies. De rol zegt waar je begint (fundering) en wat ernaast kan. */
  var ROL_VOLGORDE = ["fundering", "alternatief", "verdieping"];

  function handleidingenBlok(barriere) {
    var alle = (BRON.handelingsperspectief || {})[barriere];
    if (!alle || !alle.length) { return null; }
    var lijst = alle.slice().sort(function (a, b) {
      return ROL_VOLGORDE.indexOf(a.rol) - ROL_VOLGORDE.indexOf(b.rol);
    });
    var items = lijst.map(function (h) {
      return el("li", {}, [
        el("a", { href: h.url, rel: "noopener", target: "_blank", tekst: h.titel }),
        el("span", { class: "rol", tekst: " " + h.rol })
      ]);
    });
    return el("div", { class: "handleidingen" }, [
      el("p", { class: "label", tekst: lijst.length === 1 ? "ZO PAK JE HET AAN" : "ZO PAK JE HET AAN · KIES EEN ROUTE" })
    ].concat([el("ul", {}, items)]));
  }

  function resultaatScherm() {
    var uitslag = beoordeel();
    var top = acties(uitslag);
    var wrap = el("div", {});

    var open = BRON.bladeren.filter(function (b) {
      return uitslag[b.id].status === "open" || uitslag[b.id].status === "reactive";
    });
    var sectie1 = el("section", { class: "kaart" }, [
      el("p", { class: "label", tekst: "01 / WAAR ZIT DE RUIMTE VOOR EEN AANVALLER?" }),
      el("h2", { id: "open-paden", tekst: open.length
        ? "Dit zijn jullie belangrijkste open aanvalspaden"
        : "Geen open aanvalspaden volgens je antwoorden" })
    ]);
    (open.length ? open : BRON.bladeren.slice(0, 3)).forEach(function (b) {
      sectie1.appendChild(padKaart(b, uitslag));
    });
    wrap.appendChild(sectie1);

    var sectie2 = el("section", { class: "kaart" }, [
      el("p", { class: "label", tekst: "02 / JOUW VOLGENDE STAPPEN" }),
      el("h2", { tekst: top.length ? "Als je morgen maar drie dingen kunt doen" : "Geen openstaande acties" })
    ]);
    top.forEach(function (a, i) {
      sectie2.appendChild(el("article", { class: "actie", "data-actie": a.vraag_id }, [
        el("span", { class: "nummer", tekst: String(i + 1).padStart(2, "0") }),
        el("p", { class: "label", tekst: { P: "PREVENTIE", D: "DETECTIE", R: "RESPONSE" }[a.vraag.letter] || "MAATREGEL" }),
        el("h3", { tekst: a.vraag.vraag.actie }),
        el("p", { tekst: a.vraag.vraag.toelichting || "" }),
        el("p", { class: "raakt", tekst: "Helpt bij " + a.helpt.length +
          (a.helpt.length === 1 ? " aanvalspad" : " aanvalspaden") + ": " + a.helpt.join(", ") }),
        a.vraag.bewijs ? el("p", { class: "bewijs", tekst: "Bewijs: " + a.vraag.bewijs }) : null,
        a.verifieer ? el("p", { class: "verifieer", tekst: "Je antwoord was onbekend: zoek dit eerst uit." }) : null,
        handleidingenBlok(a.vraag_id)
      ]));
    });
    wrap.appendChild(sectie2);

    var sectie3 = el("section", { class: "kaart" }, [
      el("p", { class: "label", tekst: "03 / HET VOLLEDIGE BEELD" }),
      el("h2", { tekst: "Alle " + BRON.bladeren.length + " aanvalspaden" }),
      el("p", { tekst: "Sterk beheerst is geen garantie. Een goed beschermd aanvalspad sluit een ander risico niet uit." })
    ]);
    BRON.clusters.forEach(function (c) {
      sectie3.appendChild(el("h3", { class: "clusterkop", tekst: c.titel }));
      sectie3.appendChild(el("p", { class: "uitleg", tekst: c.kern }));
      c.bladeren.forEach(function (id) { sectie3.appendChild(padKaart(BLAD[id], uitslag)); });
    });
    var impact = BRON.bladeren.filter(function (b) { return b.type === "impact"; });
    if (impact.length) {
      sectie3.appendChild(el("h3", { class: "clusterkop", tekst: "Samengesteld gevolg" }));
      impact.forEach(function (b) {
        sectie3.appendChild(padKaart(b, uitslag));
        sectie3.appendChild(el("p", { class: "uitleg", tekst: BRON.regels.uitzonderingen.AP17.toelichting }));
      });
    }
    wrap.appendChild(sectie3);

    wrap.appendChild(el("section", { class: "kaart" }, [
      el("h2", { tekst: "Verder met de risicoanalyse" }),
      el("p", { tekst: "Deze uitslag zegt welke aanvalspaden openstaan. De volgende stap zet ze af tegen " +
        "jullie kroonjuwelen en levert een risicolijst met maatregel, eigenaar en termijn. Daar telt een " +
        "antwoord niet meer als bewijs: een cel wordt pas groen met een artefact eronder." }),
      el("p", {}, [el("a", { href: "https://security-commons-nl.github.io/kennisbank/security/risicoanalyse-aanvalspaden/",
                             rel: "noopener", tekst: "De methode in de kennisbank" })]),
      el("div", { class: "knoppen" }, [
        el("button", { tekst: "Terug naar de vragen", onclick: function () { ga("vragen", 0); } }),
        el("button", { class: "gevaar", tekst: "Wis alle antwoorden", onclick: function () {
          if (window.confirm("Alle antwoorden op dit apparaat wissen?")) { wis(); ga("start"); }
        } })
      ])
    ]));
    return wrap;
  }

  function beoordelingUitleg() {
    var sectie = el("section", { class: "kaart", id: "beoordeling" }, [
      el("p", { class: "label", tekst: "DE BEOORDELING" }),
      el("h2", { tekst: "Geen score, wel een eerlijk beeld" }),
      el("p", { tekst: "Geen percentage en geen volwassenheidsniveau. Per aanvalspad kijken we of de " +
        "noodzakelijke barrières er zijn. Een positief antwoord betekent: technisch afgedwongen en de " +
        "dekking is gecontroleerd." })
    ]);
    var lijst = el("dl", { class: "statussen" });
    BRON.regels.statussen.forEach(function (s) {
      lijst.appendChild(el("dt", {}, [statusVlag(s.id)]));
      lijst.appendChild(el("dd", { tekst: s.uitleg }));
    });
    sectie.appendChild(lijst);
    var stappen = el("ol", { class: "bepaling" });
    BRON.regels.bepaling.forEach(function (r) { stappen.appendChild(el("li", { tekst: r })); });
    sectie.appendChild(el("p", { class: "kopje", tekst: "Zo bepalen we de status van een pad" }));
    sectie.appendChild(stappen);
    sectie.appendChild(el("p", { tekst: "Preventie gaat voor detectie. Een SOC maakt zwakke authenticatie niet " +
      "phishingbestendig. Alle uitkomsten komen uit je eigen antwoorden, niet uit technische verificatie." }));
    sectie.appendChild(el("p", { class: "uitleg", tekst: "P = preventief, D = detecterend, R = reactief. " +
      "Deze check is dreigingsgedreven en is geen audit tegen een normenkader." }));
    return sectie;
  }

  function teken() {
    while (app.firstChild) { app.removeChild(app.firstChild); }
    if (staat.scherm === "start") { app.appendChild(startScherm()); app.appendChild(beoordelingUitleg()); }
    else if (staat.scherm === "vragen") { app.appendChild(vragenScherm()); }
    else { app.appendChild(resultaatScherm()); app.appendChild(beoordelingUitleg()); }
    document.getElementById("versie").textContent = "bron " + BRON.versie;
  }

  /* Haakje voor de tests: dezelfde beoordeling, zonder door de schermen te klikken. */
  window.zelfcheck = {
    bron: BRON,
    vragen: VRAGEN,
    zet: function (antwoorden) { staat.antwoorden = antwoorden; bewaar(); teken(); },
    beoordeel: function () { return beoordeel(); },
    acties: function () { return acties(beoordeel()); },
    ga: ga
  };

  var metingInvoer = document.getElementById("bestand-meting");
  if (metingInvoer) {
    metingInvoer.addEventListener("change", function (gebeurtenis) {
      var bestand = gebeurtenis.target.files[0];
      gebeurtenis.target.value = "";
      if (!bestand) return;
      bestand.text().then(neemMetingOver).catch(function () {
        metingMelding = { fout: true, tekst: "Dit bestand is niet te lezen." };
        teken();
      });
    });
  }

  laad();
  teken();
})();
