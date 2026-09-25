// Copyright (c) 2026, Dxbitz and contributors

import { render, resolve, RENDERERS, known_types } from "./library/registry.js";
import { renderPage } from "./library/grid.js";

frappe.provide("synapse.library");
synapse.library.render = render;
synapse.library.resolve = resolve;
synapse.library.renderers = RENDERERS;
synapse.library.known_types = known_types;
synapse.library.render_page = renderPage;
