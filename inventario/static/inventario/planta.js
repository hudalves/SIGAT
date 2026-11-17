(function () {
  "use strict";
  var plan = document.getElementById("planta");
  if (!plan) return;

  var dados = JSON.parse(document.getElementById("planta-dados").textContent);
  var csrf = document.querySelector("[name=csrfmiddlewaretoken]").value;
  var statusEl = document.getElementById("planta-status");
  var contagemEl = document.getElementById("contagem");
  var painel = document.getElementById("painel");
  var editToggle = document.getElementById("modo-edicao");
  var dica = document.getElementById("dica-edicao");
  var busca = document.getElementById("busca");
  var legenda = document.getElementById("legenda");

  var AMB = dados.ambientes;
  var EQ = dados.equipamentos;
  var editando = false;
  var ocultas = {};
  var selecionado = null; // {tipo: "eq" | "amb", id: n}
  var suprimirClick = false;

  function el(tag, cls, texto) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (texto !== undefined && texto !== null) e.textContent = texto;
    return e;
  }
  function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }
  function ambPorId(id) { return AMB.filter(function (a) { return a.id === id; })[0]; }
  function eqPorId(id) { return EQ.filter(function (e) { return e.id === id; })[0]; }
  function urlDe(chave, id) { return dados.urls[chave].replace("/0/", "/" + id + "/"); }
  function setStatus(msg, erro) { statusEl.textContent = msg; statusEl.className = "status" + (erro ? " erro" : ""); }
  function evitarClickFantasma() {
    suprimirClick = true;
    setTimeout(function () { suprimirClick = false; }, 0);
  }

  function post(url, corpo) {
    setStatus("Salvando…");
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify(corpo)
    }).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    }).then(function (j) {
      setStatus("Salvo ✓");
      return j;
    }).catch(function (err) {
      setStatus("Erro ao salvar. Recarregue a página.", true);
      throw err;
    });
  }

  function selecionar(s) { selecionado = s; render(); }

  // ---------- marcadores (equipamentos)
  function criarMarcador(e) {
    var mk = el("i", "mk cat-" + e.categoria);
    mk.dataset.id = e.id;
    mk.title = e.patrimonio + " — " + (e.nome || e.modelo);
    if (selecionado && selecionado.tipo === "eq" && selecionado.id === e.id) mk.classList.add("sel");
    mk.addEventListener("pointerdown", function (ev) {
      ev.stopPropagation();
      if (editando) arrastarMarcador(mk, e, ev);
    });
    mk.addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (suprimirClick) return;
      selecionar({ tipo: "eq", id: e.id });
    });
    return mk;
  }

  function arrastarMarcador(mk, e, ev) {
    ev.preventDefault();
    mk.setPointerCapture(ev.pointerId);
    var moveu = false;

    function mover(m) {
      if (!moveu && Math.abs(m.clientX - ev.clientX) + Math.abs(m.clientY - ev.clientY) < 4) return;
      moveu = true;
      mk.classList.add("arrastando");
      mk.style.left = m.clientX + "px";
      mk.style.top = m.clientY + "px";
    }

    function soltar(u) {
      mk.removeEventListener("pointermove", mover);
      mk.removeEventListener("pointerup", soltar);
      if (!moveu) return;
      evitarClickFantasma();
      var alvo = document.elementsFromPoint(u.clientX, u.clientY).filter(function (n) {
        return n.classList && n.classList.contains("sala");
      })[0];
      if (!alvo) { render(); setStatus("Solte o equipamento dentro de um ambiente."); return; }
      var amb = ambPorId(parseInt(alvo.dataset.id, 10));
      var r = alvo.getBoundingClientRect();
      var x = clamp(Math.round((u.clientX - r.left) / r.width * 1000) / 10, 3, 97);
      var y = clamp(Math.round((u.clientY - r.top) / r.height * 1000) / 10, 3, 97);
      var mudouAmbiente = amb.id !== e.ambiente;
      if (mudouAmbiente && !confirm("Mover " + e.patrimonio + " para " + amb.nome + "? Isso atualiza a localização no inventário.")) {
        render();
        return;
      }
      var corpo = { x: x, y: y };
      if (mudouAmbiente) corpo.ambiente = amb.id;
      post(urlDe("equipamento", e.id), corpo).then(function () {
        e.x = x; e.y = y; e.ambiente = amb.id;
        render();
      }).catch(function () { render(); });
    }

    mk.addEventListener("pointermove", mover);
    mk.addEventListener("pointerup", soltar);
  }

  // ---------- ambientes
  function ligarSala(sala, a) {
    sala.addEventListener("click", function () {
      if (suprimirClick) return;
      selecionar({ tipo: "amb", id: a.id });
    });

    sala.addEventListener("pointerdown", function (ev) {
      if (!editando) return;
      var redimensionar = ev.target.classList.contains("resize");
      var r = plan.getBoundingClientRect();
      var ini = { x: ev.clientX, y: ev.clientY, ax: a.x, ay: a.y, aw: a.w, ah: a.h };
      var moveu = false;
      sala.setPointerCapture(ev.pointerId);

      function mover(m) {
        var dx = (m.clientX - ini.x) / r.width * 100;
        var dy = (m.clientY - ini.y) / r.height * 100;
        if (Math.abs(dx) + Math.abs(dy) > 0.3) moveu = true;
        if (redimensionar) {
          a.w = clamp(Math.round(ini.aw + dx), 5, 100 - a.x);
          a.h = clamp(Math.round(ini.ah + dy), 5, 100 - a.y);
        } else {
          a.x = clamp(Math.round(ini.ax + dx), 0, 100 - a.w);
          a.y = clamp(Math.round(ini.ay + dy), 0, 100 - a.h);
        }
        sala.style.left = a.x + "%";
        sala.style.top = a.y + "%";
        sala.style.width = a.w + "%";
        sala.style.height = a.h + "%";
      }

      function soltar() {
        sala.removeEventListener("pointermove", mover);
        sala.removeEventListener("pointerup", soltar);
        if (!moveu) return;
        evitarClickFantasma();
        post(urlDe("ambiente", a.id), { x: a.x, y: a.y, largura: a.w, altura: a.h }).catch(function () {});
      }

      sala.addEventListener("pointermove", mover);
      sala.addEventListener("pointerup", soltar);
    });
  }

  // ---------- desenho da planta
  function render() {
    plan.innerHTML = "";
    AMB.forEach(function (a) {
      var sala = el("div", "sala");
      sala.dataset.id = a.id;
      sala.style.left = a.x + "%";
      sala.style.top = a.y + "%";
      sala.style.width = a.w + "%";
      sala.style.height = a.h + "%";
      if (selecionado && selecionado.tipo === "amb" && selecionado.id === a.id) sala.classList.add("sel");

      var itens = EQ.filter(function (e) { return e.ambiente === a.id; });
      sala.appendChild(el("strong", null, a.nome));
      sala.appendChild(el("small", null, itens.length + (itens.length === 1 ? " equipamento" : " equipamentos")));
      var fluxo = el("span", "marcadores");
      sala.appendChild(fluxo);
      itens.forEach(function (e) {
        var mk = criarMarcador(e);
        if (e.x !== null && e.y !== null) {
          mk.classList.add("abs");
          mk.style.left = e.x + "%";
          mk.style.top = e.y + "%";
          sala.appendChild(mk);
        } else {
          fluxo.appendChild(mk);
        }
      });
      sala.appendChild(el("span", "resize"));
      ligarSala(sala, a);
      plan.appendChild(sala);
    });
    if (!AMB.length) plan.appendChild(el("p", "vazio vazio-planta", "Cadastre ambientes para montar a planta."));
    aplicarFiltros();
    renderPainel();
  }

  function aplicarFiltros() {
    var q = busca.value.trim().toLowerCase();
    var acertos = 0;
    var marcadores = plan.querySelectorAll(".mk");
    for (var i = 0; i < marcadores.length; i++) {
      var mk = marcadores[i];
      var e = eqPorId(parseInt(mk.dataset.id, 10));
      var oculto = !!ocultas[e.categoria];
      var texto = (e.patrimonio + " " + e.nome + " " + e.modelo + " " + e.categoria + " " + e.categoria_label).toLowerCase();
      var bate = q !== "" && texto.indexOf(q) !== -1;
      mk.classList.toggle("oculto", oculto);
      mk.classList.toggle("hit", bate && !oculto);
      mk.classList.toggle("dim", q !== "" && !bate);
      if (bate && !oculto) acertos++;
    }
    contagemEl.textContent = q ? acertos + " encontrado(s)" : "";
  }

  function renderPainel() {
    painel.innerHTML = "";
    if (!selecionado) {
      painel.appendChild(el("p", "vazio", "Clique em um ambiente ou em um equipamento da planta para ver os detalhes."));
      return;
    }
    if (selecionado.tipo === "eq") {
      var e = eqPorId(selecionado.id);
      if (!e) { selecionado = null; renderPainel(); return; }
      painel.appendChild(el("h2", null, e.patrimonio + (e.nome ? " — " + e.nome : "")));
      var dl = el("dl");
      [["Categoria", e.categoria_label], ["Modelo", e.modelo], ["Status", e.status_label], ["Ambiente", ambPorId(e.ambiente).nome]].forEach(function (p) {
        dl.appendChild(el("dt", null, p[0]));
        dl.appendChild(el("dd", null, p[1]));
      });
      painel.appendChild(dl);
      var link = el("a", "btn", "Abrir ficha");
      link.href = e.url;
      painel.appendChild(link);
    } else {
      var a = ambPorId(selecionado.id);
      if (!a) { selecionado = null; renderPainel(); return; }
      painel.appendChild(el("h2", null, a.nome + " (" + a.tipo + ")"));
      var itens = EQ.filter(function (x) { return x.ambiente === a.id; });
      if (!itens.length) {
        painel.appendChild(el("p", "vazio", "Nenhum equipamento ativo neste ambiente."));
      } else {
        var tab = el("table");
        var cab = el("tr");
        ["Patrimônio", "Nome / modelo", "Categoria", "Status"].forEach(function (t) { cab.appendChild(el("th", null, t)); });
        tab.appendChild(cab);
        itens.forEach(function (x) {
          var tr = el("tr");
          var td = el("td");
          var l = el("a", null, x.patrimonio);
          l.href = x.url;
          td.appendChild(l);
          tr.appendChild(td);
          tr.appendChild(el("td", null, x.nome || x.modelo));
          tr.appendChild(el("td", null, x.categoria_label));
          tr.appendChild(el("td", null, x.status_label));
          tab.appendChild(tr);
        });
        painel.appendChild(tab);
      }
    }
  }

  // ---------- controles
  dados.categorias.forEach(function (c) {
    var chip = el("button", "chip");
    chip.type = "button";
    var cor = el("i", "mk cat-" + c[0]);
    chip.appendChild(cor);
    chip.appendChild(document.createTextNode(" " + c[1]));
    chip.addEventListener("click", function () {
      ocultas[c[0]] = !ocultas[c[0]];
      chip.classList.toggle("off", !!ocultas[c[0]]);
      aplicarFiltros();
    });
    legenda.appendChild(chip);
  });

  busca.addEventListener("input", aplicarFiltros);
  editToggle.addEventListener("change", function () {
    editando = editToggle.checked;
    plan.classList.toggle("editando", editando);
    dica.hidden = !editando;
  });

  render();
})();
