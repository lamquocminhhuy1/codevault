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

  var cy = cytoscape({
    container: container,
    elements: elements,
    minZoom: 0.2,
    maxZoom: 2.5,
    style: [
      {
        selector: "node",
        style: {
          "background-color": "data(color)",
          "label": "data(label)",
          "color": "#e8e8ee",
          "text-outline-color": "#1a1b21",
          "text-outline-width": 2,
          "font-size": 11,
          "text-valign": "bottom",
          "text-margin-y": 6,
          "width": 26,
          "height": 26,
          "border-width": 2,
          "border-color": "#1a1b21"
        }
      },
      {
        selector: "edge",
        style: {
          "width": 1.6,
          "line-color": "#5a5c6e",
          "target-arrow-color": "#5a5c6e",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.9,
          "curve-style": "bezier"
        }
      },
      {
        selector: "node:active",
        style: { "overlay-opacity": 0.15 }
      }
    ],
    layout: {
      name: "breadthfirst",
      directed: true,
      spacingFactor: 1.4,
      padding: 30
    }
  });

  cy.on("tap", "node", function (evt) {
    var url = evt.target.data("url");
    if (url) {
      window.location.href = url;
    }
  });

  cy.on("mouseover", "node", function (evt) {
    container.style.cursor = "pointer";
    evt.target.style("border-color", "#fff");
  });
  cy.on("mouseout", "node", function (evt) {
    container.style.cursor = "default";
    evt.target.style("border-color", "#1a1b21");
  });
})();
