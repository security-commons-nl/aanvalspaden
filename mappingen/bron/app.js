/* De crosswalk: drie weergaven op dezelfde data.

   Vanuit het pad   welk bewijs uit dit aanvalspad zegt iets over welke maatregel
   Vanuit de norm   welke barrieres leveren bewijs voor deze maatregel
   Witte vlekken    de maatregelen waar geen enkele barriere bewijs voor levert

   De pagina bestaat uit drie delen. De kop en de bedieningsbalk worden een keer getekend; alleen de
   lijst wordt opnieuw opgebouwd als je filtert. Dat scheelt werk bij elke toetsaanslag en het houdt
   de focus in het zoekveld staan, zonder trucs.

   De bedieningsbalk plakt bovenaan en wordt compact zodra de kop uit beeld is: met vier kaders en
   drie weergaven wil je die keuzes bij de hand houden terwijl je door honderd maatregelen scrolt.

   De data zit in window.__BRON__ en window.__MAPPINGEN__, meegebakken door bouw.py. Geen netwerk,
   geen opslag: deze pagina leest alleen. Het Content-Security-Policy staat op een hash en verbiedt
   inline stijl, dus alles gaat via klassen, nooit via element.style. */

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
  var WEERGAVEN = [
    ["pad", "Vanuit het aanvalspad"],
    ["norm", "Vanuit de maatregel"],
    ["wit", "Witte vlekken"],
    ["hoe", "Hoe pak ik het aan"]
  ];
  var HP = bron.handelingsperspectief;

  var stand = {
    kader: Object.keys(kaders)[0],
    weergave: "pad",
    zoek: ""
  };

  var lijstVak = null;
  var kaderKnoppen = {};
  var weergaveKnoppen = {};
  var tellingRegel = null;

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

  function hardeRegels(regels) {
    return regels.filter(function (r) { return r.sterkte !== "raakvlak"; });
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

  /* De kop van een blok: een soortlabel, dan het nummer en de naam. Het label zegt in een woord
     waar je naar kijkt, zodat een aanvalspad nooit te verwarren is met een maatregel. */
  function blokKop(soort, nummer, naam, vlag) {
    var wrap = document.createElement("div");
    wrap.appendChild(el("p", "soort", soort));
    var kop = el("div", "blokkop");
    var titel = el("h3");
    if (nummer) { titel.appendChild(el("span", "kop-nummer", nummer)); }
    titel.appendChild(document.createTextNode(nummer ? " " + naam : naam));
    kop.appendChild(titel);
    if (vlag) { kop.appendChild(vlag); }
    wrap.appendChild(kop);
    return wrap;
  }

  /* Een maatregel onder een barriere: het nummer in een vaste kolom vooraan, dan de naam. */
  function normItem(sterkte, nummer, naam, reden) {
    var li = el("li");
    var kop = el("div", "regel-kop");
    var titel = el("span", "titel");
    titel.appendChild(el("span", "norm-nummer", nummer));
    // Een spatie hoort in de tekst, niet alleen in de opmaak: anders plakken nummer en naam aan
    // elkaar zodra iemand de regel kopieert of met een schermlezer leest.
    titel.appendChild(document.createTextNode(" " + naam));
    kop.appendChild(titel);
    kop.appendChild(sterkteVlag(sterkte));
    li.appendChild(kop);
    if (reden) { li.appendChild(el("p", "reden", reden)); }
    return li;
  }

  function regelItem(sterkte, titel, nummer, reden, bewijs) {
    var li = el("li");
    var kop = el("div", "regel-kop");
    kop.appendChild(sterkteVlag(sterkte));
    kop.appendChild(el("span", "titel", titel));
    if (nummer) { kop.appendChild(el("span", "nummer", nummer)); }
    li.appendChild(kop);
    if (reden) { li.appendChild(el("p", "reden", reden)); }
    if (bewijs) { li.appendChild(el("p", "bewijs", "Bewijs: " + bewijs)); }
    return li;
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
      var soort = blad.type === "impact" ? "Impact, geen voordeur"
        : blad.type === "randvoorwaarde" ? "Randvoorwaarde" : "Aanvalspad";
      blok.appendChild(blokKop(soort, blad.id === "RV" ? null : blad.id, blad.titel));
      if (blad.scenario) { blok.appendChild(el("p", "uitleg", blad.scenario)); }

      var lijst = el("ul", "regels");
      blad.chokepoints.forEach(function (cp) {
        var item = el("li");
        var regelkop = el("div", "regel-kop");
        regelkop.appendChild(el("span", "titel", cp.titel));
        regelkop.appendChild(el("span", "nummer", cp.id));
        item.appendChild(regelkop);
        if (cp.bewijs) { item.appendChild(el("p", "bewijs", "Bewijs: " + cp.bewijs)); }

        var regels = sorteerOpSterkte(cp.regels || []);
        if (!regels.length) {
          var reden = huidig().ongekoppeld[cp.barriere] || "Geen regel in dit kader.";
          var geen = el("p", "reden");
          geen.appendChild(sterkteVlag("geen", "niet in dit kader"));
          geen.appendChild(document.createTextNode(" " + reden));
          item.appendChild(geen);
        } else {
          var normen = el("ul", "regels");
          regels.forEach(function (r) {
            var m = maatregelVan(r.norm);
            normen.appendChild(normItem(r.sterkte, r.norm, m ? m.titel : "", r.reden));
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
      var zoekbaar = m.id + " " + m.titel + " " + m.thema + " " + (m.kern || "") + " " + regels.map(function (r) {
        var b = barriereVan(r.barriere);
        return (b ? b.titel : r.barriere) + " " + r.reden;
      }).join(" ");
      if (!past(zoekbaar)) { return; }
      gevonden++;

      var hard = hardeRegels(regels);
      var blok = el("section", "blok");
      var vlag = hard.length
        ? sterkteVlag(hard[0].sterkte, hard.length + (hard.length === 1 ? " barriere" : " barrieres"))
        : sterkteVlag("geen", regels.length ? "alleen raakvlak" : "witte vlek");
      blok.appendChild(blokKop("Maatregel", m.id, m.titel, vlag));

      var meta = el("p", "thema", m.thema);
      if (m.overheidsmaatregelen && m.overheidsmaatregelen.length) {
        meta.appendChild(document.createTextNode(" · overheidsmaatregelen " + m.overheidsmaatregelen.join(", ")));
      }
      if (m.artikel) { meta.appendChild(document.createTextNode(" · " + m.artikel)); }
      blok.appendChild(meta);
      if (m.kern) { blok.appendChild(el("p", "uitleg", m.kern)); }

      if (!regels.length) {
        blok.appendChild(el("p", "leeg", "Geen enkele barriere uit de zelfcheck levert hier bewijs voor. Zie de witte vlekken."));
      } else {
        if (!hard.length) {
          blok.appendChild(el("p", "leeg", "Alleen raakvlakken: de zelfcheck komt in de buurt, maar toont deze maatregel niet aan. Dit telt als witte vlek."));
        }
        var lijst = el("ul", "regels");
        regels.forEach(function (r) {
          var b = barriereVan(r.barriere);
          lijst.appendChild(regelItem(
            r.sterkte,
            b ? b.titel : r.barriere,
            b && b.chokepoints.length ? b.chokepoints.join(", ") : null,
            r.reden,
            b ? b.bewijs : null
          ));
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
        var raak = m.raakvlakken || [];
        blok.appendChild(blokKop(
          "Maatregel zonder bewijs", m.id, m.titel,
          sterkteVlag("geen", raak.length ? "alleen raakvlak" : "witte vlek")
        ));
        if (m.artikel) { blok.appendChild(el("p", "thema", m.artikel)); }
        if (m.kern) { blok.appendChild(el("p", "uitleg", m.kern)); }
        if (raak.length) {
          var lijst = el("ul", "regels");
          raak.forEach(function (r) {
            var b = barriereVan(r.barriere);
            lijst.appendChild(regelItem("raakvlak", b ? b.titel : r.barriere, null, r.reden));
          });
          blok.appendChild(lijst);
        }
        wrap.appendChild(blok);
      });
    });

    if (!gevonden) { wrap.appendChild(el("p", "geenresultaat", "Geen witte vlekken voor deze zoekterm.")); }

    if (data.ongekoppeldeLijst.length) {
      wrap.appendChild(el("h3", "themakop", "Barrieres die dit kader niet raakt"));
      var lijst2 = el("ul", "regels");
      data.ongekoppeldeLijst.forEach(function (paar) {
        var b = barriereVan(paar.barriere);
        lijst2.appendChild(regelItem("geen", b ? b.titel : paar.barriere, null, paar.reden));
      });
      wrap.appendChild(lijst2);
    }

    return wrap;
  }

  /* ---------- weergave: hoe pak ik het aan ---------- */

  var NL = String.fromCharCode(10);

  function issueLink(opdracht) {
    var titels = opdracht.barrieres.map(function (b) { return b.titel; });
    var regels = ["Deze handleiding ontbreekt nog in de kennisbank.", ""];

    regels.push("**Barrieres die dit artikel zou dekken**");
    opdracht.barrieres.forEach(function (b) {
      regels.push("- " + b.titel + " (" + b.id + "): " + b.zou_moeten_dekken);
    });

    var metBewijs = opdracht.barrieres.filter(function (b) { return b.bewijs; });
    if (metBewijs.length) {
      regels.push("", "**Bewijs dat de zelfcheck bij deze barrieres vraagt**");
      metBewijs.forEach(function (b) { regels.push("- " + b.id + ": " + b.bewijs); });
    }

    regels.push("", "Gevonden via de normverankering:",
      "https://security-commons-nl.github.io/aanvalspaden/normen/");

    return HP.issue_basis
      + "?title=" + encodeURIComponent("Handleiding gevraagd: " + titels[0])
      + "&body=" + encodeURIComponent(regels.join(NL));
  }

  function toonHoe() {
    var wrap = document.createDocumentFragment();

    var intro = el("section", "kaart");
    intro.appendChild(el("h2", null, "Hoe pak ik het aan"));
    intro.appendChild(el("p", "lead", HP.toelichting));

    var d = HP.dekking;
    var telling = el("div", "telling");
    [
      [d.met_handleiding, "barrieres met een handleiding"],
      [d.gevraagd, "barrieres zonder handleiding"],
      [d.schrijfopdrachten, "artikelen om te schrijven"],
      [d.barrieres, "barrieres in totaal"]
    ].forEach(function (paar) {
      var vak = el("div");
      vak.appendChild(el("div", "groot", paar[0]));
      vak.appendChild(el("div", "wat", paar[1]));
      telling.appendChild(vak);
    });
    intro.appendChild(telling);
    wrap.appendChild(intro);

    /* Wat er wel is. */
    var gevondenA = 0;
    var kopA = el("h3", "themakop", "Hier ligt een handleiding");
    var lijstA = document.createDocumentFragment();
    Object.keys(HP.handleidingen).forEach(function (id) {
      var hl = HP.handleidingen[id];
      var b = barriereVan(id);
      var zoekbaar = id + " " + (b ? b.titel : "") + " " + hl.titel + " " + hl.paragraaf + " " + hl.reden;
      if (!past(zoekbaar)) { return; }
      gevondenA++;

      var blok = el("section", "blok");
      blok.appendChild(blokKop("Barriere", null, b ? b.titel : id,
        sterkteVlag(hl.dekking === "volledig" ? "volledig" : "gedeeltelijk", hl.dekking)));
      var p = el("p", "thema");
      p.appendChild(document.createTextNode(hl.titel + " · " + hl.paragraaf));
      blok.appendChild(p);
      blok.appendChild(el("p", "reden", hl.reden));

      var link = document.createElement("a");
      link.href = HP.kennisbank + hl.item + "/";
      link.rel = "noopener";
      link.textContent = "Lees " + hl.titel;
      var wrapLink = el("p", "bewijs");
      wrapLink.appendChild(link);
      blok.appendChild(wrapLink);
      lijstA.appendChild(blok);
    });
    if (gevondenA) { wrap.appendChild(kopA); wrap.appendChild(lijstA); }

    /* Wat er nog niet is: de uitnodiging. */
    var gevondenB = 0;
    var kopB = el("h3", "themakop", "Hier is nog niets geschreven");
    var lijstB = document.createDocumentFragment();
    HP.opdrachten.forEach(function (o) {
      var zoekbaar = o.cluster + " " + o.barrieres.map(function (b) {
        return b.id + " " + b.titel + " " + b.zou_moeten_dekken;
      }).join(" ");
      if (!past(zoekbaar)) { return; }
      gevondenB++;

      var blok = el("section", "blok gevraagd");
      blok.appendChild(blokKop(
        "Te schrijven artikel", null, o.cluster.replace(/-/g, " "),
        sterkteVlag("geen", o.barrieres.length + (o.barrieres.length === 1 ? " barriere" : " barrieres"))
      ));

      var lijst = el("ul", "regels");
      o.barrieres.forEach(function (b) {
        var li = el("li");
        var kop = el("div", "regel-kop");
        kop.appendChild(el("span", "titel", b.titel));
        kop.appendChild(el("span", "nummer", b.id));
        li.appendChild(kop);
        li.appendChild(el("p", "reden", b.zou_moeten_dekken));
        lijst.appendChild(li);
      });
      blok.appendChild(lijst);

      var oproep = el("p", "oproep");
      oproep.appendChild(document.createTextNode("Weet jij hoe dit moet? "));
      var knop = document.createElement("a");
      knop.className = "knop";
      knop.href = issueLink(o);
      knop.rel = "noopener";
      knop.textContent = "Schrijf mee";
      oproep.appendChild(knop);
      blok.appendChild(oproep);
      lijstB.appendChild(blok);
    });
    if (gevondenB) { wrap.appendChild(kopB); wrap.appendChild(lijstB); }

    if (!gevondenA && !gevondenB) {
      wrap.appendChild(el("p", "geenresultaat", "Niets gevonden voor deze zoekterm."));
    }
    return wrap;
  }

  /* ---------- de vaste kop ---------- */

  function bouwKop() {
    var kaart = el("section", "kaart");
    kaart.appendChild(el("p", "label", "Normverankering"));
    kaart.appendChild(el("h1", null, "Van aanvalspad naar norm"));
    kaart.appendChild(el("p", "lead", bron.inleiding));

    var uitleg = el("details", "uitleg-blok");
    uitleg.appendChild(el("summary", null, "Wat een regel wel en niet zegt"));
    uitleg.appendChild(el("p", "uitleg", bron.belofte));
    var lijst = el("ul", "regels");
    STERKTES.forEach(function (s) {
      var li = el("li");
      var kop = el("div", "regel-kop");
      kop.appendChild(sterkteVlag(s));
      li.appendChild(kop);
      li.appendChild(el("p", "reden", STERKTE_UITLEG[s]));
      lijst.appendChild(li);
    });
    uitleg.appendChild(lijst);
    kaart.appendChild(uitleg);
    return kaart;
  }

  /* ---------- de sticky bedieningsbalk ---------- */

  function bouwBedien() {
    var balk = el("div", "bedien");
    var binnen = el("div", "bedien-binnen");

    var rij1 = el("div", "balk");
    rij1.appendChild(el("span", "balk-label", "Kader"));
    Object.keys(kaders).forEach(function (naam) {
      var knop = el("button", null, kaders[naam].titel);
      knop.type = "button";
      knop.addEventListener("click", function () {
        stand.kader = naam;
        werkKnoppenBij();
        tekenLijst();
      });
      kaderKnoppen[naam] = knop;
      rij1.appendChild(knop);
    });
    binnen.appendChild(rij1);

    var rij2 = el("div", "balk");
    WEERGAVEN.forEach(function (paar) {
      var knop = el("button", null, paar[1]);
      knop.type = "button";
      knop.addEventListener("click", function () {
        stand.weergave = paar[0];
        werkKnoppenBij();
        tekenLijst();
      });
      weergaveKnoppen[paar[0]] = knop;
      rij2.appendChild(knop);
    });

    var rek = el("div", "rek");
    var zoek = el("input");
    zoek.type = "search";
    zoek.placeholder = "Zoek op maatregel, barriere of woord";
    zoek.setAttribute("aria-label", "Zoeken");
    zoek.addEventListener("input", function () {
      stand.zoek = zoek.value.trim().toLowerCase();
      tekenLijst();
    });
    rek.appendChild(zoek);
    rij2.appendChild(rek);
    binnen.appendChild(rij2);

    tellingRegel = el("p", "toelichting");
    binnen.appendChild(tellingRegel);

    balk.appendChild(binnen);
    return balk;
  }

  function werkKnoppenBij() {
    Object.keys(kaderKnoppen).forEach(function (naam) {
      var actief = stand.kader === naam;
      kaderKnoppen[naam].className = actief ? "gekozen" : "";
      kaderKnoppen[naam].setAttribute("aria-pressed", actief ? "true" : "false");
    });
    Object.keys(weergaveKnoppen).forEach(function (naam) {
      var actief = stand.weergave === naam;
      weergaveKnoppen[naam].className = actief ? "gekozen" : "";
      weergaveKnoppen[naam].setAttribute("aria-pressed", actief ? "true" : "false");
    });
    var d = huidig().dekking;
    tellingRegel.textContent = huidig().herkomst + " · " + d.regels + " regels · " +
      d.geraakt + " van " + d.maatregelen + " maatregelen met bewijs · " +
      d.witte_vlekken + " witte vlekken.";
  }

  /* Compact zodra de kop uit beeld is. Een sentinel van 1 pixel boven de balk is betrouwbaarder dan
     meten op scrollpositie: die klopt niet meer zodra het filter de paginahoogte verandert. */
  function volgScroll(sentinel, balk) {
    if (!("IntersectionObserver" in window)) { return; }
    new IntersectionObserver(function (regels) {
      balk.className = regels[0].isIntersecting ? "bedien" : "bedien compact";
    }, { threshold: 0 }).observe(sentinel);
  }

  /* ---------- opbouw ---------- */

  function tekenLijst() {
    lijstVak.textContent = "";
    if (stand.weergave === "pad") { lijstVak.appendChild(toonPaden()); }
    else if (stand.weergave === "norm") { lijstVak.appendChild(toonNormen()); }
    else if (stand.weergave === "hoe") { lijstVak.appendChild(toonHoe()); }
    else { lijstVak.appendChild(toonWitteVlekken()); }
  }

  app.textContent = "";
  app.appendChild(bouwKop());
  var sentinel = el("div", "sentinel");
  app.appendChild(sentinel);
  var balk = bouwBedien();
  app.appendChild(balk);
  lijstVak = el("div", "lijst");
  app.appendChild(lijstVak);

  werkKnoppenBij();
  tekenLijst();
  volgScroll(sentinel, balk);

  var versie = document.getElementById("versie");
  if (versie) { versie.textContent = "versie " + bron.versie; }
})();
