/**
 * motogp-standings-card.js
 *
 * Carte Lovelace custom pour Home Assistant affichant le classement du
 * championnat MotoGP (pilotes), à partir des attributs exposés par
 * sensor.motogp_classement_pilotes (intégration "motogp").
 */

const FONT_IMPORT_ID = "motogp-card-font-import";

function ensureFontLoaded() {
  if (document.getElementById(FONT_IMPORT_ID)) return;
  const link = document.createElement("link");
  link.id = FONT_IMPORT_ID;
  link.rel = "stylesheet";
  link.href =
    "https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&display=swap";
  document.head.appendChild(link);
}

function countryFlagEmoji(iso) {
  if (!iso || iso.length !== 2) return "";
  const codePoints = [...iso.toUpperCase()].map(
    (c) => 127397 + c.charCodeAt(0)
  );
  return String.fromCodePoint(...codePoints);
}

function positionChangeArrow(change) {
  if (!change) return "";
  if (change > 0) return `<span class="chg up">▲${change}</span>`;
  return `<span class="chg down">▼${Math.abs(change)}</span>`;
}

class MotoGPStandingsCard extends HTMLElement {
  static getStubConfig() {
    return { entity: "sensor.motogp_classement_pilotes", limit: 10 };
  }

  static getConfigElement() {
    return document.createElement("motogp-standings-card-editor");
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Vous devez définir 'entity' (le capteur de classement MotoGP).");
    }
    // limit (optionnel) : nombre de lignes affichées. Absent/0 = toutes.
    // title (optionnel) : titre personnalisé de la carte.
    this._config = { limit: 0, ...config };
    ensureFontLoaded();
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._buildStaticShell();
  }

  set hass(hass) {
    this._hass = hass;
    const stateObj = hass.states[this._config.entity];
    if (!stateObj) {
      this._renderMissing(this._config.entity);
      return;
    }
    this._renderState(stateObj);
  }

  getCardSize() {
    const rows = this._config && this._config.limit ? this._config.limit : 10;
    return Math.max(3, Math.ceil(rows / 2) + 1);
  }

  _buildStaticShell() {
    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <ha-card>
        <div class="card"></div>
      </ha-card>
    `;
  }

  _css() {
    return `
      :host {
        --mgp-bg: #17181c;
        --mgp-surface: #202227;
        --mgp-surface-2: #26282e;
        --mgp-text: #f4f3f0;
        --mgp-muted: #9a9da5;
        --mgp-accent: #ff4f2e;
        --mgp-gold: #ffd166;
        --mgp-silver: #cfd3d8;
        --mgp-bronze: #d99a63;
        --mgp-border: rgba(255,255,255,0.07);
      }
      ha-card {
        background: var(--mgp-bg);
        color: var(--mgp-text);
        border-radius: 16px;
        overflow: hidden;
        padding: 0;
      }
      .card {
        font-family: "Inter", "Segoe UI", system-ui, sans-serif;
        padding: 16px 18px 10px;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 10px;
      }
      .title {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-weight: 600;
        font-size: 18px;
      }
      .subtitle {
        font-size: 11px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--mgp-muted);
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      thead th {
        text-align: left;
        font-size: 10px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--mgp-muted);
        font-weight: 500;
        padding: 4px 6px;
        border-bottom: 1px solid var(--mgp-border);
      }
      thead th.num-col, thead th.points-col {
        text-align: right;
      }
      tbody td {
        padding: 7px 6px;
        font-size: 13px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        vertical-align: middle;
      }
      tbody tr:last-child td {
        border-bottom: none;
      }
      .pos {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-weight: 600;
        width: 26px;
      }
      .pos.p1 { color: var(--mgp-gold); }
      .pos.p2 { color: var(--mgp-silver); }
      .pos.p3 { color: var(--mgp-bronze); }
      .rider-cell {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .bib {
        font-variant-numeric: tabular-nums;
        color: var(--mgp-muted);
        font-size: 11px;
        min-width: 22px;
      }
      .flag {
        font-size: 14px;
      }
      .rider-name {
        font-weight: 500;
      }
      .rider-team {
        display: block;
        font-size: 10px;
        color: var(--mgp-muted);
      }
      .points {
        text-align: right;
        font-variant-numeric: tabular-nums;
        font-weight: 600;
      }
      .chg {
        font-size: 10px;
        margin-left: 4px;
      }
      .chg.up { color: #4caf50; }
      .chg.down { color: var(--mgp-accent); }
      .empty, .missing {
        padding: 12px 4px;
        color: var(--mgp-muted);
        font-size: 13px;
      }
    `;
  }

  _renderMissing(entityId) {
    const root = this.shadowRoot.querySelector(".card");
    if (!root) return;
    root.innerHTML = `<div class="missing">Entité introuvable : ${entityId}</div>`;
  }

  _renderState(stateObj) {
    const attrs = stateObj.attributes;
    const standings = attrs.classement || [];
    const season = attrs.saison;
    const limit = Number(this._config.limit) || 0;
    const rows = limit > 0 ? standings.slice(0, limit) : standings;

    const root = this.shadowRoot.querySelector(".card");
    if (!root) return;

    if (!standings.length) {
      root.innerHTML = `
        <div class="header">
          <div class="title">${this._config.title || "Classement pilotes"}</div>
        </div>
        <div class="empty">Classement non encore disponible</div>
      `;
      return;
    }

    root.innerHTML = `
      <div class="header">
        <div class="title">${this._config.title || "Classement pilotes"}</div>
        <div class="subtitle">${season ? "Saison " + season : ""}</div>
      </div>
      <table>
        <thead>
          <tr>
            <th class="num-col">Pos.</th>
            <th>Pilote</th>
            <th class="points-col">Pts</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => this._renderRow(r)).join("")}
        </tbody>
      </table>
    `;
  }

  _renderRow(r) {
    const posClass = r.position === 1 ? "p1" : r.position === 2 ? "p2" : r.position === 3 ? "p3" : "";
    return `
      <tr>
        <td class="pos ${posClass}">${r.position != null ? r.position : "—"}</td>
        <td>
          <div class="rider-cell">
            <span class="flag">${countryFlagEmoji(r.country_iso)}</span>
            <span class="bib">#${r.number != null ? r.number : "—"}</span>
            <span>
              <span class="rider-name">${r.name || "—"}</span>
              ${r.team ? `<span class="rider-team">${r.team}</span>` : ""}
            </span>
          </div>
        </td>
        <td class="points">${r.points != null ? r.points : "—"}${positionChangeArrow(r.position_change)}</td>
      </tr>
    `;
  }
}

/**
 * Éditeur visuel pour motogp-standings-card, sur le même principe que
 * celui de motogp-next-race-card (via <ha-form>).
 */
class MotoGPStandingsCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _schema() {
    return [
      { name: "entity", required: true, selector: { entity: { domain: "sensor" } } },
      { name: "title", selector: { text: {} } },
      { name: "limit", selector: { number: { min: 0, max: 30, step: 1, mode: "box" } } },
    ];
  }

  _labels(schemaName) {
    const labels = {
      entity: "Entité (capteur de classement MotoGP)",
      title: "Titre (optionnel)",
      limit: "Nombre de lignes (0 = toutes)",
    };
    return labels[schemaName] || schemaName;
  }

  _render() {
    if (!this._hass) return;

    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }

    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = this._schema();
    this._form.computeLabel = (schema) => this._labels(schema.name);
  }
}

customElements.define("motogp-standings-card-editor", MotoGPStandingsCardEditor);

customElements.define("motogp-standings-card", MotoGPStandingsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "motogp-standings-card",
  name: "MotoGP - Classement pilotes",
  description: "Affiche le classement du championnat MotoGP sous forme de tableau.",
});
