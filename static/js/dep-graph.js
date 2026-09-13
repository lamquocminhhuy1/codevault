/* Dependency graph rendering (project_deps.html, layout=graph only).
   Separate from app.js so pages that don't view the graph never load
   Cytoscape - only this page's <script extra_head> block pulls it in. */
(function () {
  "use strict";

  if (typeof cytoscape === "undefined") {
    return;
  }

  var container = document.getElementById("dep-graph");
  var dataEl = document.getElementById("dep-graph-data");
  if (!container || !dataEl) {
    return;
  }

  var data;
  try {
    data = JSON.parse(dataEl.textContent);
  } catch (err) {
    return;
  }

  // Same hue family as the .badge.<script_type> colors in style.css, so a
  // node reads as the same "kind of thing" whether you're looking at the
  // item table or the graph. Cytoscape draws to <canvas>, so these have to
  // be literal colors - they can't reference the page's CSS custom
  // properties the way the rest of the UI does.
  var TYPE_COLORS = {
    script_include: "#9b7bd8",
    business_rule: "#3f8fc0",
    client_script: "#c9a23a",
    ui_page: "#c96fa8",
    ui_action: "#c96fa8",
    ui_macro: "#c96fa8",
    scheduled_job: "#c47a4a",
    fix_script: "#c47a4a",
    rest_api: "#3fa896",
    widget: "#6b87c4",
    xml: "#7691a3",
    other: "#8a8a99"
  };
  var DEFAULT_COLOR = TYPE_COLORS.other;

  function colorFor(type) {
    return TYPE_COLORS[type] || DEFAULT_COLOR;
  }

  var elements = [];
  var i;
  for (i = 0; i < data.nodes.length; i++) {
    var node = data.nodes[i];
    elements.push({
      data: {
        id: "n" + node.id,
        label: node.title,
        url: node.url,
        type: node.type,
        typeLabel: node.type_label,
        color: colorFor(node.type)
      }
    });
  }
  for (i = 0; i < data.edges.length; i++) {
    var edge = data.edges[i];
    elements.push({
      data: {
        id: "e" + i,
        source: "n" + edge.from,
        target: "n" + edge.to
      }
    });
  }

  // Below this zoom level, node labels stop being comfortably readable -
  // large graphs that don't fit at this zoom stay pannable instead of
  // shrinking further, the way Miro/Figma/Excalidraw handle "fit all".
  var COMFORTABLE_MIN_ZOOM = 0.55;

  var cy = cytoscape({
    container: container,
    elements: elements,
    minZoom: 0.08,
    maxZoom: 3.5,
    wheelSensitivity: 0.25,
    style: [
      {
        selector: "node",
        style: {
          "shape": "round-rectangle",
          "background-color": "data(color)",
          "label": "data(label)",
          "color": "#ffffff",
          "font-size": 14,
          "font-weight": 600,
          "text-valign": "center",
          "text-halign": "center",
          "text-wrap": "ellipsis",
          "text-max-width": "160px",
          "padding": "11px",
          "width": "label",
          "height": "label",
          "border-width": 2,
          "border-color": "rgba(255, 255, 255, 0.18)"
        }
      },
      {
        selector: "edge",
        style: {
          "width": 1.8,
          "line-color": "#565866",
          "target-arrow-color": "#565866",
          "target-arrow-shape": "triangle",
          "arrow-scale": 1,
          "curve-style": "bezier"
        }
      },
      {
        selector: "node, edge",
        style: {
          "transition-property": "opacity, border-color, line-color, target-arrow-color, width",
          "transition-duration": 150
        }
      },
      {
        selector: ".cy-faded",
        style: { "opacity": 0.12 }
      },
      {
        selector: "node.cy-highlighted",
        style: { "border-color": "#ffffff", "border-width": 3 }
      },
      {
        selector: "edge.cy-highlighted",
        style: { "line-color": "#ffffff", "target-arrow-color": "#ffffff", "width": 2.6 }
      }
    ],
    layout: { name: "preset" }
  });

  /* ---- Zoom: fit but never past the point labels get unreadable -------- */

  function centerPoint() {
    return { x: container.clientWidth / 2, y: container.clientHeight / 2 };
  }

  function updateZoomLabel() {
    var el = document.getElementById("graph-zoom-level");
    if (el) { el.textContent = Math.round(cy.zoom() * 100) + "%"; }
  }

  function smartFit() {
    cy.fit(cy.elements(), 48);
    if (cy.zoom() < COMFORTABLE_MIN_ZOOM) {
      cy.zoom({ level: COMFORTABLE_MIN_ZOOM, renderedPosition: centerPoint() });
      cy.center();
    }
  }

  // Built and run explicitly (rather than via the constructor's `layout`
  // option) so the layoutstop listener is guaranteed to be attached before
  // the layout can possibly finish and fire it.
  var initialLayout = cy.layout({
    name: "breadthfirst",
    directed: true,
    spacingFactor: 1.6,
    padding: 48,
    animate: false,
    fit: false
  });
  initialLayout.one("layoutstop", smartFit);
  initialLayout.run();

  cy.on("zoom", updateZoomLabel);
  updateZoomLabel();

  cy.on("tap", "node", function (evt) {
    var url = evt.target.data("url");
    if (url) {
      window.location.href = url;
    }
  });

  /* ---- Hover: trace what a node touches, fade everything else --------- */

  var searchInput = document.getElementById("graph-search");

  function searchActive() {
    return !!(searchInput && searchInput.value.trim());
  }

  function clearHighlight() {
    cy.elements().removeClass("cy-faded cy-highlighted");
  }

  function highlightNeighborhood(node) {
    var neighborhood = node.closedNeighborhood();
    cy.elements().addClass("cy-faded").removeClass("cy-highlighted");
    neighborhood.removeClass("cy-faded").addClass("cy-highlighted");
  }

  cy.on("mouseover", "node", function (evt) {
    container.style.cursor = "pointer";
    if (!searchActive()) {
      highlightNeighborhood(evt.target);
    }
  });
  cy.on("mouseout", "node", function () {
    container.style.cursor = "grab";
    if (!searchActive()) {
      clearHighlight();
    }
  });

  /* ---- Search: highlight matching nodes, fade the rest ----------------- */

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      var q = searchInput.value.trim().toLowerCase();
      if (!q) {
        clearHighlight();
        return;
      }
      var matches = cy.nodes().filter(function (n) {
        return n.data("label").toLowerCase().indexOf(q) !== -1;
      });
      cy.elements().addClass("cy-faded").removeClass("cy-highlighted");
      matches.removeClass("cy-faded").addClass("cy-highlighted");
    });
  }

  /* ---- Zoom controls ---------------------------------------------------- */

  function zoomBy(factor) {
    var next = Math.max(cy.minZoom(), Math.min(cy.maxZoom(), cy.zoom() * factor));
    cy.zoom({ level: next, renderedPosition: centerPoint() });
  }

  var zoomInBtn = document.getElementById("graph-zoom-in");
  var zoomOutBtn = document.getElementById("graph-zoom-out");
  var fitBtn = document.getElementById("graph-fit");
  if (zoomInBtn) { zoomInBtn.addEventListener("click", function () { zoomBy(1.25); }); }
  if (zoomOutBtn) { zoomOutBtn.addEventListener("click", function () { zoomBy(0.8); }); }
  if (fitBtn) { fitBtn.addEventListener("click", smartFit); }

  /* ---- Full screen: maximize canvas real estate on any screen size ----- */

  var wrap = document.querySelector(".dep-graph-wrap");
  var fullscreenBtn = document.getElementById("graph-fullscreen");

  function setFullscreen(on) {
    wrap.classList.toggle("graph-fullscreen", on);
    document.body.classList.toggle("graph-fullscreen-active", on);
    if (fullscreenBtn) {
      fullscreenBtn.textContent = on ? "✕ Exit full screen" : "⛶ Full screen";
      fullscreenBtn.title = on ? "Exit full screen (Esc)" : "Full screen";
    }
    cy.resize();
    smartFit();
  }

  if (fullscreenBtn) {
    fullscreenBtn.addEventListener("click", function () {
      setFullscreen(!wrap.classList.contains("graph-fullscreen"));
    });
  }
  document.addEventListener("keydown", function (evt) {
    if (evt.key === "Escape" && wrap.classList.contains("graph-fullscreen")) {
      setFullscreen(false);
    }
  });

  var resizeTimer = null;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () { cy.resize(); }, 150);
  });

  /* ---- Legend: only the types actually present in this graph ----------- */

  var legendEl = document.getElementById("graph-legend");
  if (legendEl) {
    var seen = {};
    var rows = [];
    for (i = 0; i < data.nodes.length; i++) {
      var n = data.nodes[i];
      if (seen[n.type]) { continue; }
      seen[n.type] = true;
      rows.push({ color: colorFor(n.type), label: n.type_label || n.type });
    }
    rows.sort(function (a, b) { return a.label < b.label ? -1 : a.label > b.label ? 1 : 0; });
    var html = '<div class="legend-title">Type</div>';
    for (i = 0; i < rows.length; i++) {
      html += '<div class="legend-row"><span class="legend-dot" style="background:' + rows[i].color + '"></span>' + rows[i].label + "</div>";
    }
    legendEl.innerHTML = html;
  }
})();
