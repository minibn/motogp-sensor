/**
 * motogp-next-race-card.js
 *
 * Carte Lovelace custom pour Home Assistant affichant le prochain
 * Grand Prix MotoGP, à partir des attributs exposés par
 * sensor.motogp_prochaine_course (intégration "motogp").
 *
 * Pas de dépendance de build : simple Web Component (Shadow DOM).
 */

const FONT_IMPORT_ID = "motogp-card-font-import";

function ensureFontLoaded() {
  if (document.getElementById(FONT_IMPORT_ID)) return;
  const link = document.createElement("link");
  link.id = FONT_IMPORT_ID;
  link.rel = "stylesheet";
  link.href =
    "https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&display=swap";
  document.head.appendChild(link);
}

const SESSION_LABELS = {
  FP1: "EL1",
  FP2: "EL2",
  FP3: "EL3",
  P1: "EL1",
  P2: "EL2",
  P3: "EL3",
  PR: "Warm-up",
  Q1: "Q1",
  Q2: "Q2",
  QP: "Qualifs",
  SPR: "Sprint",
  RAC: "Course",
  RACE: "Course",
};

function shortSessionLabel(type) {
  if (!type) return "?";
  const key = String(type).toUpperCase().replace(/\s+/g, "");
  return SESSION_LABELS[key] || type;
}

function isRaceSession(type) {
  const key = String(type || "").toUpperCase();
  return key.includes("RAC");
}

class MotoGPNextRaceCard extends HTMLElement {
  static getStubConfig() {
    return { entity: "sensor.motogp_prochaine_course" };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Vous devez définir 'entity' (le capteur MotoGP).");
    }
    this._config = config;
    ensureFontLoaded();
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._buildStaticShell();
  }

  set hass(hass) {
    this._hass = hass;
    const entityId = this._config.entity;
    const stateObj = hass.states[entityId];

    if (!stateObj) {
      this._renderMissing(entityId);
      return;
    }
    this._renderState(stateObj);
  }

  getCardSize() {
    return 4;
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
        --mgp-bg: #101114;
        --mgp-surface: #1b1d22;
        --mgp-surface-2: #24272e;
        --mgp-accent: #ff4d1c;
        --mgp-accent-2: #ffd166;
        --mgp-text: #f2f1ed;
        --mgp-muted: #9aa0a8;
      }
      ha-card {
        background: var(--mgp-bg);
        color: var(--mgp-text);
        border-radius: 14px;
        overflow: hidden;
        padding: 0;
      }
      .card {
        display: flex;
        flex-direction: column;
        font-family: "Inter", "Segoe UI", system-ui, sans-serif;
      }
      .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        background: linear-gradient(90deg, var(--mgp-surface-2), var(--mgp-surface));
        border-bottom: 2px solid var(--mgp-accent);
      }
      .category {
        font-size: 12px;
        letter-spacing: 0.08em;
        font-weight: 600;
        color: var(--mgp-accent);
      }
      .round {
        font-size: 12px;
        color: var(--mgp-muted);
      }
      .main {
        padding: 16px 18px 6px;
      }
      .country {
        font-size: 13px;
        color: var(--mgp-muted);
        margin-bottom: 2px;
      }
      .circuit {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-weight: 600;
        font-size: 26px;
        line-height: 1.15;
        letter-spacing: 0.01em;
        margin: 0 0 14px 0;
      }
      .countdown {
        display: flex;
        gap: 14px;
        margin-bottom: 6px;
      }
      .countdown .unit {
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 46px;
      }
      .countdown .value {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-variant-numeric: tabular-nums;
        font-size: 30px;
        font-weight: 700;
        color: var(--mgp-accent-2);
        line-height: 1;
      }
      .countdown .label {
        font-size: 10px;
        color: var(--mgp-muted);
        letter-spacing: 0.06em;
        margin-top: 4px;
      }
      .live-banner {
        font-family: "Oswald", "Inter", system-ui, sans-serif;
        font-size: 20px;
        font-weight: 600;
        color: var(--mgp-accent);
        padding: 6px 0 10px;
      }
      .sessions {
        display: flex;
        overflow-x: auto;
        gap: 8px;
        padding: 12px 18px 16px;
        background: var(--mgp-surface);
        border-top: 1px solid rgba(255,255,255,0.06);
      }
      .session {
        flex: 0 0 auto;
        background: var(--mgp-surface-2);
        border-radius: 8px;
        padding: 8px 10px;
        min-width: 78px;
        text-align: center;
      }
      .session .type {
        font-size: 11px;
        font-weight: 600;
        color: var(--mgp-muted);
        letter-spacing: 0.04em;
      }
      .session .time {
        font-size: 13px;
        margin-top: 3px;
        font-variant-numeric: tabular-nums;
      }
      .session.race {
        background: repeating-linear-gradient(
          45deg,
          var(--mgp-surface-2),
          var(--mgp-surface-2) 6px,
          #2c2f36 6px,
          #2c2f36 12px
        );
        border: 1px solid var(--mgp-accent);
      }
      .session.race .type {
        color: var(--mgp-accent-2);
      }
      .empty, .missing {
        padding: 20px 18px;
        color: var(--mgp-muted);
        font-size: 14px;
      }
    `;
  }

  _renderMissing(entityId) {
    const root = this.shadowRoot.querySelector(".card");
    if (!root) return;
    root.innerHTML = `<div class="missing">Entité introuvable : ${entityId}</div>`;
  }

  _renderState(stateObj) {
    this._eventName = stateObj.state;
    this._circuit = stateObj.attributes.circuit || "Circuit inconnu";
    this._country = stateObj.attributes.pays || "";
    this._dateStart = stateObj.attributes.date_debut || null;
    this._sessions = stateObj.attributes.sessions || [];
    this._category = (this._config.title || "MotoGP").toUpperCase();

    const root = this.shadowRoot.querySelector(".card");
    if (!root) return;

    root.innerHTML = `
      <div class="topbar">
        <span class="category">${this._category}</span>
        <span class="round">${this._eventName || ""}</span>
      </div>
      <div class="main">
        <div class="country">${this._country}</div>
        <div class="circuit">${this._circuit}</div>
        <div class="countdown-slot"></div>
      </div>
      <div class="sessions">
        ${this._renderSessions()}
      </div>
    `;

    this._updateCountdown();
  }

  _renderSessions() {
    if (!this._sessions.length) {
      return `<div class="empty">Sessions non encore publiées</div>`;
    }
    return this._sessions
      .map((s) => {
        const label = shortSessionLabel(s.type);
        const raceClass = isRaceSession(s.type) ? "race" : "";
        let timeText = "—";
        if (s.date_start) {
          const d = new Date(s.date_start);
          if (!Number.isNaN(d.getTime())) {
            timeText = d.toLocaleString(undefined, {
              weekday: "short",
              hour: "2-digit",
              minute: "2-digit",
            });
          }
        }
        return `
          <div class="session ${raceClass}">
            <div class="type">${label}</div>
            <div class="time">${timeText}</div>
          </div>
        `;
      })
      .join("");
  }

  _updateCountdown() {
    const slot = this.shadowRoot && this.shadowRoot.querySelector(".countdown-slot");
    if (!slot) return;

    if (!this._dateStart) {
      slot.innerHTML = "";
      return;
    }

    const target = new Date(this._dateStart).getTime();
    const now = Date.now();
    const diff = target - now;

    if (Number.isNaN(target)) {
      slot.innerHTML = "";
      return;
    }

    if (diff <= 0) {
      slot.innerHTML = `<div class="live-banner">🏁 Week-end en cours</div>`;
      return;
    }

    const totalSeconds = Math.floor(diff / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    slot.innerHTML = `
      <div class="countdown">
        <div class="unit"><div class="value">${days}</div><div class="label">JOURS</div></div>
        <div class="unit"><div class="value">${String(hours).padStart(2, "0")}</div><div class="label">H</div></div>
        <div class="unit"><div class="value">${String(minutes).padStart(2, "0")}</div><div class="label">MIN</div></div>
        <div class="unit"><div class="value">${String(seconds).padStart(2, "0")}</div><div class="label">SEC</div></div>
      </div>
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
