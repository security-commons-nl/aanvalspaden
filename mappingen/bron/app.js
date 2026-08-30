/* De crosswalk: drie weergaven op dezelfde data.

   Vanuit het pad   welk bewijs uit dit aanvalspad zegt iets over welke maatregel
   Vanuit de norm   welke barrieres leveren bewijs voor deze maatregel
   Witte vlekken    de maatregelen waar geen enkele barriere iets over zegt

   De data zit in window.__BRON__ en window.__MAPPINGEN__, meegebakken door bouw.py. Geen netwerk,
   geen opslag: deze pagina leest alleen. */

(function () {
  "use strict";

  var bron = window.__BRON__;
  var kaders = window.__MAPPINGEN__;
  var app = document.getElementById("app");

  var STERKTES = ["volledig", "gedeeltelijk", "raakvlak"];
  var STERKTE_UITLEG = {
    volledig: "Wie dit bewijs op tafel legt, heeft het toetsbare deel van de maatregel aangetoond.",
    gedeeltelijk: "Het bewijs toont een deel aan; de maatregel vraagt meer.",
    raakvlak: "Het raakt elkaar, maar dit bewijs toont de maatregel niet aan."
  };

  var stand = {
    kader: Object.keys(kaders)[0],
    weergave: "pad",
    zoek: ""
  };

  /* ---------- hulp ---------- */

  function el(naam, klasse, tekst) {
    var e = document.createElement(naam);
    if (klasse) { e.className = klasse; }
    if (tekst !== undefined && tekst !== null) { e.textContent = String(tekst); }
    return e;
  }

  function huidig() { return kaders[stand.kader]; }

  function barriereVan(id) { return huidig().barrieres[id]; }

  function maatregelVan(id) {
    var lijst = huidig().maatregelen;
    for (var i = 0; i < lijst.length; i++) { if (lijst[i].id === id) { return lijst[i]; } }
    return null;
  }

  function sorteerOpSterkte(regels) {
    return regels.slice().sort(function (a, b) {
      return STERKTES.indexOf(a.sterkte) - STERKTES.indexOf(b.sterkte);
    });
  }

  function past(tekst) {
    if (!stand.zoek) { return true; }
    return String(tekst).toLowerCase().indexOf(stand.zoek) !== -1;
  }

  function sterkteVlag(sterkte, woord) {
    var vlag = el("span", "sterkte " + sterkte);
    vlag.appendChild(el("b"));
    vlag.appendChild(document.createTextNode(woord || sterkte));
    vlag.title = STERKTE_UITLEG[sterkte] || "";
    return vlag;
  }

  /* ---------- weergave: vanuit het pad ---------- */

  function toonPaden() {
    var wrap = document.createDocumentFragment();
    var gevonden = 0;

    huidig().bladeren.forEach(function (blad) {
      var zoekbaar = blad.id + " " + blad.titel + " " + blad.chokepoints.map(function (cp) {
        return cp.titel + " " + (cp.regels || []).map(function (r) {
          var m = maatregelVan(r.norm);
          return r.norm + " " + (m ? m.titel : "") + " " + r.reden;
        }).join(" ");
      }).join(" ");
      if (!past(zoekbaar)) { return; }
      gevonden++;

      var blok = el("section", "blok");
      var kop = el("div", "blokkop");
      var titel = el("h3");
      titel.appendChild(document.createTextNode(blad.id + ". " + blad.titel));
      kop.appendChild(titel);
      if (blad.type === "impact") {
        kop.appendChild(el("span", "chip", "impact, geen voordeur"));
      }
      blok.appendChild(kop);
      blok.appendChild(el("p", "uitleg", blad.scenario));

      var lijst = el("ul", "regels");
      blad.chokepoints.forEach(function (cp) {
        var item = el("li");
        var regelkop = el("div", "regel-kop");
        regelkop.appendChild(el("span", "titel", cp.titel));
        regelkop.appendChild(el("span", "nummer", cp.id));
        item.appendChild(regelkop);
        item.appendChild(el("p", "bewijs", "Bewijs: " + cp.bewijs));

        var regels = sorteerOpSterkte(cp.regels || []);
        if (!regels.length) {
          var reden = (huidig().ongekoppeld[cp.barriere] || "Geen regel in dit kader.");
          var geen = el("p", "reden");
          geen.appendChild(sterkteVlag("geen", "niet in dit kader"));
          geen.appendChild(document.createTextNode(" " + reden));
          item.appendChild(geen);
        } else {
          var normen = el("ul", "regels");
          regels.forEach(function (r) {
            var m = maatregelVan(r.norm);
            var li = el("li");
            var rk = el("div", "regel-kop");
            rk.appendChild(sterkteVlag(r.sterkte));
            rk.appendChild(el("span", "titel", r.norm + " " + (m ? m.titel : "")));
            li.appendChild(rk);
            li.appendChild(el("p", "reden", r.reden));
            normen.appendChild(li);
          });
          item.appendChild(normen);
        }
        lijst.appendChild(item);
      });
      blok.appendChild(lijst);
      wrap.appendChild(blok);
    });

    if (!gevonden) { wrap.appendChild(el("p", "geenresultaat", "Niets gevonden voor deze zoekterm.")); }
    return wrap;
  }

  /* ---------- weergave: vanuit de norm ---------- */

  function toonNormen() {
    var wrap = document.createDocumentFragment();
    var gevonden = 0;

    huidig().maatregelen.forEach(function (m) {
      var regels = sorteerOpSterkte(huidig().perNorm[m.id] || []);
      var zoekbaar = m.id + " " + m.titel + " " + m.thema + " " + regels.map(function (r) {
        var b = barriereVan(r.barriere);
        return (b ? b.titel : r.barriere) + " " + r.reden;
      }).join(" ");
      if (!past(zoekbaar)) { return; }
      gevonden++;

      var blok = el("section", "blok");
      var kop = el("div", "blokkop");
      var titel = el("h3", null, m.id + " " + m.titel);
      kop.appendChild(titel);
      var hard = regels.filter(function (r) { return r.sterkte !== "raakvlak"; });
      if (hard.length) {
        kop.appendChild(sterkteVlag(hard[0].sterkte, hard.length + (hard.length === 1 ? " barriere" : " barrieres")));
      } else {
        kop.appendChild(sterkteVlag("geen", regels.length ? "alleen raakvlak" : "witte vlek"));
      }
      blok.appendChild(kop);

      var meta = el("p", "thema");
      meta.appendChild(document.createTextNode(m.thema));
      if (m.overheidsmaatregelen && m.overheidsmaatregelen.length) {
        meta.appendChild(document.createTextNode(" · overheidsmaatregelen " + m.overheidsmaatregelen.join(", ")));
      }
      if (m.artikel) { meta.appendChild(document.createTextNode(" · " + m.artikel)); }
      blok.appendChild(meta);
      if (m.kern) { blok.appendChild(el("p", "uitleg", m.kern)); }

      if (!regels.length) {
        blok.appendChild(el("p", "leeg", "Geen enkele barriere uit de zelfcheck levert hier bewijs voor. Zie de witte vlekken."));
      } else if (!hard.length) {
        blok.appendChild(el("p", "leeg", "Alleen raakvlakken: de zelfcheck komt in de buurt, maar toont deze maatregel niet aan. Dit telt als witte vlek."));
        var alleenRaak = el("ul", "regels");
        regels.forEach(function (r) {
          var b = barriereVan(r.barriere);
          var li = el("li");
          var rk = el("div", "regel-kop");
          rk.appendChild(sterkteVlag(r.sterkte));
          rk.appendChild(el("span", "titel", b ? b.titel : r.barriere));
          li.appendChild(rk);
          li.appendChild(el("p", "reden", r.reden));
          alleenRaak.appendChild(li);
        });
        blok.appendChild(alleenRaak);
      } else {
        var lijst = el("ul", "regels");
        regels.forEach(function (r) {
          var b = barriereVan(r.barriere);
          var li = el("li");
          var rk = el("div", "regel-kop");
          rk.appendChild(sterkteVlag(r.sterkte));
          rk.appendChild(el("span", "titel", b ? b.titel : r.barriere));
          if (b && b.chokepoints.length) {
            rk.appendChild(el("span", "nummer", b.chokepoints.join(", ")));
          }
          li.appendChild(rk);
          li.appendChild(el("p", "reden", r.reden));
          if (b) { li.appendChild(el("p", "bewijs", "Bewijs: " + b.bewijs)); }
          lijst.appendChild(li);
        });
        blok.appendChild(lijst);
      }
      wrap.appendChild(blok);
    });

    if (!gevonden) { wrap.appendChild(el("p", "geenresultaat", "Niets gevonden voor deze zoekterm.")); }
    return wrap;
  }

  /* ---------- weergave: witte vlekken ---------- */

  function toonWitteVlekken() {
    var wrap = document.createDocumentFragment();
    var data = huidig();

    var intro = el("section", "kaart");
    intro.appendChild(el("h2", null, "Waar de zelfcheck ophoudt"));
    intro.appendChild(el("p", "lead", data.witteVlekkenTekst));

    var telling = el("div", "telling");
    [
      [data.dekking.geraakt, "maatregelen waar bewijs voor is"],
      [data.dekking.witte_vlekken, "maatregelen zonder bewijs"],
      [data.dekking.alleen_raakvlak, "daarvan alleen een raakvlak"],
      [data.dekking.maatregelen, "maatregelen in dit kader"]
    ].forEach(function (paar) {
      var vak = el("div");
      vak.appendChild(el("div", "groot", paar[0]));
      vak.appendChild(el("div", "wat", paar[1]));
      telling.appendChild(vak);
    });
    intro.appendChild(telling);
    wrap.appendChild(intro);

    var perThema = {};
    var volgorde = [];
    data.witteVlekken.forEach(function (m) {
      if (!perThema[m.thema]) { perThema[m.thema] = []; volgorde.push(m.thema); }
      perThema[m.thema].push(m);
    });

    var gevonden = 0;
    volgorde.forEach(function (thema) {
      var items = perThema[thema].filter(function (m) {
        return past(m.id + " " + m.titel + " " + thema + " " + (m.kern || ""));
      });
      if (!items.length) { return; }
      gevonden += items.length;

      wrap.appendChild(el("h3", "themakop", thema));
      items.forEach(function (m) {
        var blok = el("section", "blok");
        var kop = el("div", "blokkop");
        kop.appendChild(el("h3", null, m.id + " " + m.titel));
        kop.appendChild(sterkteVlag("geen", (m.raakvlakken && m.raakvlakken.length) ? "alleen raakvlak" : "witte vlek"));
        blok.appendChild(kop);
        if (m.artikel) { blok.appendChild(el("p", "thema", m.artikel)); }
        if (m.kern) { blok.appendChild(el("p", "uitleg", m.kern)); }
        if (m.raakvlakken && m.raakvlakken.length) {
          var raak = el("ul", "regels");
          m.raakvlakken.forEach(function (r) {
            var b = barriereVan(r.barriere);
            var li = el("li");
            var rk = el("div", "regel-kop");
            rk.appendChild(sterkteVlag("raakvlak"));
            rk.appendChild(el("span", "titel", b ? b.titel : r.barriere));
            li.appendChild(rk);
            li.appendChild(el("p", "reden", r.reden));
            raak.appendChild(li);
          });
          blok.appendChild(raak);
        }
        wrap.appendChild(blok);
      });
    });

    if (!gevonden) {
      wrap.appendChild(el("p", "geenresultaat", "Geen witte vlekken voor deze zoekterm."));
    }

    if (data.ongekoppeldeLijst.length) {
      wrap.appendChild(el("h3", "themakop", "Barrieres die dit kader niet raakt"));
      var lijst = el("ul", "regels");
      data.ongekoppeldeLijst.forEach(function (paar) {
        var b = barriereVan(paar.barriere);
        var li = el("li");
        var rk = el("div", "regel-kop");
        rk.appendChild(sterkteVlag("geen", "geen regel"));
        rk.appendChild(el("span", "titel", b ? b.titel : paar.barriere));
        li.appendChild(rk);
        li.appendChild(el("p", "reden", paar.reden));
        lijst.appendChild(li);
      });
      wrap.appendChild(lijst);
    }

    return wrap;
  }

  /* ---------- opbouw ---------- */

  function kop() {
    var kaart = el("section", "kaart");
    kaart.appendChild(el("p", "label", "Normverankering"));
    kaart.appendChild(el("h1", null, "Van aanvalspad naar norm"));
    kaart.appendChild(el("p", "lead", bron.inleiding));

    var uitleg = el("details", "uitleg-blok");
    uitleg.appendChild(el("summary", null, "Wat een regel wel en niet zegt"));
    var p = el("p", "uitleg", bron.belofte);
    uitleg.appendChild(p);
    var dl = el("ul", "regels");
    STERKTES.forEach(function (s) {
      var li = el("li");
      var rk = el("div", "regel-kop");
      rk.appendChild(sterkteVlag(s));
      li.appendChild(rk);
      li.appendChild(el("p", "reden", STERKTE_UITLEG[s]));
      dl.appendChild(li);
    });
    uitleg.appendChild(dl);
    kaart.appendChild(uitleg);

    var balk = el("div", "balk");
    Object.keys(kaders).forEach(function (naam) {
      var knop = el("button", stand.kader === naam ? "gekozen" : null, kaders[naam].titel);
      knop.type = "button";
      knop.setAttribute("aria-pressed", stand.kader === naam ? "true" : "false");
      knop.addEventListener("click", function () { stand.kader = naam; teken(); });
      balk.appendChild(knop);
    });
    kaart.appendChild(balk);

    var balk2 = el("div", "balk");
    [["pad", "Vanuit het aanvalspad"], ["norm", "Vanuit de maatregel"], ["wit", "Witte vlekken"]].forEach(function (paar) {
      var knop = el("button", stand.weergave === paar[0] ? "gekozen" : null, paar[1]);
      knop.type = "button";
      knop.setAttribute("aria-pressed", stand.weergave === paar[0] ? "true" : "false");
      knop.addEventListener("click", function () { stand.weergave = paar[0]; teken(); });
      balk2.appendChild(knop);
    });
    var rek = el("div", "rek");
    var zoek = el("input");
    zoek.type = "search";
    zoek.placeholder = "Zoek op maatregel, barriere of woord";
    zoek.setAttribute("aria-label", "Zoeken");
    zoek.value = stand.zoek;
    zoek.addEventListener("input", function () {
      stand.zoek = zoek.value.trim().toLowerCase();
      teken({ behoudFocus: true });
    });
    rek.appendChild(zoek);
    balk2.appendChild(rek);
    kaart.appendChild(balk2);

    var d = huidig().dekking;
    kaart.appendChild(el("p", "toelichting",
      huidig().herkomst + " · " + d.regels + " regels · " +
      d.geraakt + " van " + d.maatregelen + " maatregelen geraakt · " +
      d.witte_vlekken + " witte vlekken."));

    return kaart;
  }

  function teken(opties) {
    var focusStand = null;
    if (opties && opties.behoudFocus) {
      var actief = document.activeElement;
      if (actief && actief.type === "search") { focusStand = actief.selectionStart; }
    }

    app.textContent = "";
    app.appendChild(kop());
    if (stand.weergave === "pad") { app.appendChild(toonPaden()); }
    else if (stand.weergave === "norm") { app.appendChild(toonNormen()); }
    else { app.appendChild(toonWitteVlekken()); }

    if (focusStand !== null) {
      var veld = app.querySelector('input[type="search"]');
      if (veld) { veld.focus(); veld.setSelectionRange(focusStand, focusStand); }
    }
  }

  var versie = document.getElementById("versie");
  if (versie) { versie.textContent = "versie " + bron.versie; }
  teken();
})();
