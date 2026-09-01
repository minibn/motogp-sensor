/**
 * motogp-next-race-card.js
 *
 * Carte Lovelace custom pour Home Assistant affichant le prochain
 * Grand Prix MotoGP, à partir des attributs exposés par
 * sensor.motogp_prochaine_course (intégration "motogp").
 *
 * Style inspiré de la carte "Next Race" de F1 Sensor : sobre, fond
 * quasi-noir avec des blocs imbriqués légèrement plus clairs, plutôt
 * qu'un habillage très coloré.
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

function formatDateTime(iso, opts) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, opts);
}

class MotoGPNextRaceCard extends HTMLElement {
  static getStubConfig() {
    return { entity: "sensor.motogp_prochaine_course", show_sessions: true, show_circuit_map: true };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Vous devez définir 'entity' (le capteur MotoGP).");
    }
    // show_sessions (optionnel, défaut true) : permet de masquer le
    // programme du week-end en pied de carte, comme F1 Sensor le propose.
    // show_circuit_map (optionnel, défaut true) : affiche le plan du
    // circuit (tracé + virages) quand l'API le fournit.
    this._config = {
      show_sessions: true,
      show_circuit_map: true,
      ...config,
    };
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
    return this._config && this._config.show_sessions === false ? 3 : 4;
  }

  connectedCallback() {
    this._tickInterval = setInterval(() => this._updateCountdown(), 1000);
  }

  disconnectedCallback() {
    if (this._tickInterval) clearInterval(this._tickInterval);
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
        padding: 16px 18px 18px;
      }
      .header {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 4px;
      }
      .flag {
        font-size: 22px;
        line-height: 1.2;
      }
      .title-group {
        display: flex;
        flex-direction: column;
      }
      .event-name {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-weight: 600;
        font-size: 19px;
        line-height: 1.2;
      }
      .subtitle {
        font-size: 11px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--mgp-muted);
        margin-top: 2px;
      }
      .box {
        background: var(--mgp-surface);
        border: 1px solid var(--mgp-border);
        border-radius: 10px;
        padding: 10px 12px;
        margin-top: 12px;
      }
      .label {
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--mgp-muted);
      }
      .countdown-value {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-variant-numeric: tabular-nums;
        font-weight: 600;
        font-size: 24px;
        margin-top: 2px;
      }
      .countdown-sub {
        font-size: 12px;
        color: var(--mgp-muted);
        margin-top: 2px;
      }
      .info-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-top: 12px;
      }
      .info-cell .value {
        font-weight: 600;
        font-size: 14px;
        margin-top: 3px;
      }
      .info-cell .sub {
        font-size: 11px;
        color: var(--mgp-muted);
        margin-top: 1px;
      }
      .footer {
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px solid var(--mgp-border);
      }
      .footer-top {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
      }
      .footer-title {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-weight: 600;
        font-size: 14px;
      }
      .footer-count {
        font-size: 11px;
        color: var(--mgp-muted);
      }
      .session-list {
        margin-top: 8px;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .session-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 4px;
        border-radius: 6px;
        font-size: 12px;
      }
      .session-row:nth-child(odd) {
        background: rgba(255,255,255,0.02);
      }
      .session-row .type {
        color: var(--mgp-text);
      }
      .session-row.race .type {
        color: var(--mgp-accent);
        font-weight: 600;
      }
      .session-row .time {
        color: var(--mgp-muted);
      }
      .circuit-map-box {
        background: #f3f2ee;
        border-radius: 10px;
        margin-top: 12px;
        padding: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
      }
      .circuit-map-box img {
        width: 100%;
        max-height: 180px;
        object-fit: contain;
        display: block;
      }
      .circuit-map-caption {
        display: flex;
        justify-content: space-between;
        width: 100%;
        margin-top: 6px;
        font-size: 10px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #6b6f76;
      }
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

    this._eventName = stateObj.state;
    this._circuit = attrs.circuit || "Circuit inconnu";
    this._country = attrs.pays || "";
    this._countryIso = attrs.pays_iso || "";
    this._weekendStart = attrs.debut_weekend || null;
    this._raceStart = attrs.debut_course || null;
    this._nextSession = attrs.prochaine_session || null;
    this._round = attrs.manche;
    this._roundTotal = attrs.manche_total;
    this._season = attrs.saison;
    this._sessions = attrs.sessions || [];
    this._circuitMapSvg = attrs.circuit_plan_svg || null;
    this._circuitMapPng = attrs.circuit_plan_png || null;
    this._cornersLeft = attrs.circuit_virages_gauche;
    this._cornersRight = attrs.circuit_virages_droite;
    this._countdownTarget = this._nextSession ? this._nextSession.date : this._weekendStart;
    this._countdownLabel = this._nextSession ? this._nextSession.label : "le début du week-end";

    const root = this.shadowRoot.querySelector(".card");
    if (!root) return;

    root.innerHTML = `
      <div class="header">
        <div class="flag">${countryFlagEmoji(this._countryIso)}</div>
        <div class="title-group">
          <div class="event-name">${this._eventName || ""}</div>
          <div class="subtitle">${this._circuit}${this._country ? " · " + this._country : ""}</div>
        </div>
      </div>

      ${this._renderCircuitMap()}

      <div class="box">
        <div class="label">Compte à rebours</div>
        <div class="countdown-slot"></div>
      </div>

      <div class="info-grid">
        <div class="info-cell">
          <div class="label">Prochaine session</div>
          <div class="value">${this._nextSession ? this._nextSession.label : "—"}</div>
          <div class="sub">${formatDateTime(this._nextSession && this._nextSession.date, { weekday: "short", hour: "2-digit", minute: "2-digit" })}</div>
        </div>
        <div class="info-cell">
          <div class="label">Début course</div>
          <div class="value">${formatDateTime(this._raceStart, { day: "2-digit", month: "short" })}</div>
          <div class="sub">${formatDateTime(this._raceStart, { hour: "2-digit", minute: "2-digit" })}</div>
        </div>
        <div class="info-cell">
          <div class="label">Manche</div>
          <div class="value">${this._round ? "Manche " + this._round : "—"}</div>
          <div class="sub">${this._season ? "Saison " + this._season : ""}</div>
        </div>
      </div>

      ${this._config.show_sessions ? `
      <div class="footer">
        <div class="footer-top">
          <div class="footer-title">Programme</div>
          <div class="footer-count">${this._sessions.length} session${this._sessions.length > 1 ? "s" : ""}</div>
        </div>
        <div class="session-list">
          ${this._renderSessionRows()}
        </div>
      </div>
      ` : ""}
    `;

    this._updateCountdown();
  }

  _renderCircuitMap() {
    if (!this._config.show_circuit_map) return "";
    const src = this._circuitMapSvg || this._circuitMapPng;
    if (!src) return "";

    const cornerText =
      this._cornersLeft != null && this._cornersRight != null
        ? `${this._cornersLeft} virages à gauche · ${this._cornersRight} à droite`
        : "";

    return `
      <div class="circuit-map-box">
        <img src="${src}" alt="Plan du circuit" loading="lazy" />
        ${cornerText ? `<div class="circuit-map-caption"><span>${cornerText}</span></div>` : ""}
      </div>
    `;
  }

  _renderSessionRows() {
    if (!this._sessions.length) {
      return `<div class="empty">Sessions non encore publiées</div>`;
    }
    return this._sessions
      .map((s) => {
        const raceClass = s.type && String(s.type).toUpperCase() === "RAC" ? "race" : "";
        return `
          <div class="session-row ${raceClass}">
            <span class="type">${s.label}</span>
            <span class="time">${formatDateTime(s.date, { weekday: "short", hour: "2-digit", minute: "2-digit" })}</span>
          </div>
        `;
      })
      .join("");
  }

  _updateCountdown() {
    const slot = this.shadowRoot && this.shadowRoot.querySelector(".countdown-slot");
    if (!slot) return;

    if (!this._countdownTarget) {
      slot.innerHTML = `<div class="countdown-value">—</div>`;
      return;
    }

    const target = new Date(this._countdownTarget).getTime();
    const now = Date.now();
    const diff = target - now;

    if (Number.isNaN(target)) {
      slot.innerHTML = `<div class="countdown-value">—</div>`;
      return;
    }

    if (diff <= 0) {
      slot.innerHTML = `
        <div class="countdown-value">🏁 En cours</div>
        <div class="countdown-sub">Session en cours ou terminée</div>
      `;
      return;
    }

    const totalSeconds = Math.floor(diff / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);

    slot.innerHTML = `
      <div class="countdown-value">J-${days} ${String(hours).padStart(2, "0")}h ${String(minutes).padStart(2, "0")}m</div>
      <div class="countdown-sub">Avant ${this._countdownLabel}</div>
    `;
  }
}

customElements.define("motogp-next-race-card", MotoGPNextRaceCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "motogp-next-race-card",
  name: "MotoGP - Prochaine course",
  description: "Affiche le prochain Grand Prix MotoGP avec countdown et sessions.",
});
